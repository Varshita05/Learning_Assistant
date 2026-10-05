import os
import sys
import uuid
import json
import hashlib
import gc
import logfire

from qdrant_client import QdrantClient
from qdrant_client.http import models

from learning_assistant.config import Settings
from learning_assistant.retrieval_services.embeddings import embed_texts, get_embedding_dim, qdrant_collection
from learning_assistant.data_ingestion.loader import parse_html, parse_pdf, parse_text, parse_word_ppt
from learning_assistant.data_ingestion.chunking import chunk_text

logfire.configure(service_name="ingestion-service")

PROCESSED_DATA_DIR = "processed_data" # Local Storage

EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "32"))

qdrant_client = QdrantClient(
    url=Settings.QDRANT_URL,
    api_key=Settings.QDRANT_API_KEY,
    timeout=20
)

stats = {"files_found": 0, "files_processed": 0, "files_failed": 0, "files_skipped": 0, "chunks_created": 0, "chunks_indexed": 0,}

def reset_stats(): 
    """Reset ingestion statistics before a new ingestion run.""" 
    for key in stats: 
        stats[key] = 0


def make_document_id(file_path: str) -> str: 
    """ Create a stable ID based on the file contents. If the contents of a book change, its document ID changes. """ 
    hasher = hashlib.sha256() 
    with open(file_path, "rb") as f: 
        for block in iter(lambda: f.read(1024 * 1024), b""): 
            hasher.update(block) 
    return hasher.hexdigest()


def make_point_id(document_id: str, child_id: str) -> str: 
    """ Create a deterministic Qdrant point ID. Re-ingesting the same document produces the same IDs instead of creating duplicate vectors. """ 
    value = f"{document_id}:{child_id}" 
    return str(uuid.uuid5( uuid.NAMESPACE_URL, value))


def save_processed_locally(data: dict, source_type: str, file_name: str) -> str:
    """ Save parsed chunk metadata as JSON in processed_data/<source_type>/ """
    folder = os.path.join(PROCESSED_DATA_DIR, source_type)
    os.makedirs(folder, exist_ok=True)
    destination = os.path.join(folder, f"{file_name}.json")
    with open(destination, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return destination


def extract_pages(file_path: str, file_name: str):
    """
    Parse files into a common page/slide structure.

    PDF:
        page-by-page records.

    PPTX:
        slide-by-slide records.

    DOCX:
        one logical document record.

    HTML/TXT:
        one logical document record.
    """

    extension = file_name.lower().rsplit(".", 1)[-1]

    if extension == "pdf":
        return parse_pdf(file_path)

    if extension in ("docx", "pptx"):
        return parse_word_ppt(file_path)

    if extension in ("html", "htm"):
        text = parse_html(file_path)

    elif extension == "txt":
        text = parse_text(file_path)

    else:
        logfire.warning(
            f"Skipping unsupported file {file_name}"
        )
        return []

    if not text or not text.strip():
        return []

    return [
        {
            "page_number": 1,
            "text": text,
        }
    ]


def process_file(file_path: str, file_name: str, source_type: str):
    """ Parse -> Chunk -> Save Locally -> Embed -> Index in Qdrant"""
    with logfire.span("Processing File", file=file_name, source=source_type):
        try:
            
            # DOCUMENT ID
            document_id = make_document_id(file_path) 
            logfire.info( f"Document ID: {document_id[:12]}..." )
            
            # PARSE FILE
            pages = extract_pages(file_path, file_name) 
            if not pages: 
                logfire.warning( f"No text extracted from {file_name} - skipped" ) 
                stats["files_skipped"] += 1 
                return
            
            # CHUNK TEXT
            chunks = chunk_text(pages)
            if not chunks:
                stats["files_skipped"] += 1
                logfire.warning( f"No chunks generated for {file_name}" )
                return False

            stats["chunks_created"] += len(chunks) 

            # SAVE PROCESSED DATA LOCALLY
            processed_data = {
                "file_name": file_name,
                "source_type": source_type,
                "chunks": chunks
            }

            local_path = save_processed_locally(processed_data, source_type, file_name)
            logfire.info(f"Save processed data at {local_path}")

            # EMBED AND INDEX IN QDRANT
            with logfire.span("Vectorizing & Indexing", chunks=len(chunks), batch_size=EMBED_BATCH_SIZE):
                for start in range(0, len(chunks), EMBED_BATCH_SIZE):
                    batch = chunks[start:start + EMBED_BATCH_SIZE]
                    batch_texts = [chunk["text"] for chunk in batch]
                    with logfire.span("Embedding Batch", start=start, size=len(batch)):
                        embeddings = embed_texts(batch_texts)
                        if len(embeddings) != len(batch):
                            raise RuntimeError("Embedding count does not match chunk count")
                        points = []
                        for chunk, vector in zip(batch, embeddings):
                            point_id = make_point_id(document_id, chunk["child_id"])
                            payload = {
                                "text": chunk["text"],
                                # Document information
                                "source": file_name,
                                "source_type": source_type,
                                "document_id": document_id,
                                # Parent-child information
                                "child_id": chunk["child_id"],
                                "parent_id": chunk["parent_id"],
                                "child_index": chunk["child_index"],
                                "parent_index": chunk["parent_index"],
                                # Textbook structure
                                "heading": chunk["heading"],
                                "page_start": chunk["page_start"],
                                "page_end": chunk["page_end"]
                            }
                            points.append(models.PointStruct(id=point_id, vector=vector, payload=payload))
                    qdrant_client.upsert(collection_name=qdrant_collection(), points=points)
                    stats["chunks_indexed"] += len(points)
                    logfire.info(f"Indexed batch: {start + 1}-{start + len(points)} / {len(chunks)}")
                    # Release batch memory before next batch
                    del batch
                    del batch_texts
                    del embeddings
                    del points
                    gc.collect()

                stats["files_processed"] += 1
                logfire.info( f"Successfully processed {file_name}")
                return True

        except Exception as e:
            stats["files_failed"] += 1
            logfire.error(f"Failed to process {file_name}: {e}")


def process_directory(dir_path: str, source_type: str):
    """ Process every file in a directory """
    with logfire.span("Scanning Directory", path=dir_path, source=source_type):
        files = [i for i in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, i))]
        logfire.info(f"Found {len(files)} files in {dir_path}")
        for file_name in files:
            process_file(os.path.join(dir_path, file_name), file_name, source_type)


def get_source_type(name):
    name = name.lower()
    return "true" if "true" in name else "noisy" if "noisy" in name else name


def run_ingestion(base_dir: str, explicit_source_type: str = None, wipe_request: bool = False):
    """
    Scan base_dir, map sub-folders to source types, and ingest all documents
    Pass --wipe to drop and recreate the Qdrant collection before ingestion
    """

    reset_stats()

    with logfire.span("Ingestion Started", base_directory=base_dir):

        coll = qdrant_collection()
        if wipe_request:
            with logfire.span("Wiping Collection"):
                if qdrant_client.collection_exists(coll):
                    qdrant_client.delete_collection(coll)
                    logfire.info(f"Collection {coll} deleted")

        if not qdrant_client.collection_exists(coll):
            dimensions = get_embedding_dim()
            qdrant_client.create_collection(
                collection_name=coll,
                vectors_config=models.VectorParams(
                    size=dimensions,
                    distance=models.Distance.COSINE,
                ),
            )
            logfire.info(f"Created collection '{coll}' - {dimensions} dimensions, Cosine")

        # Route to sub-folders or consider whole directory as one source
        sub_dirs = [i for i in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, i))]

        if not sub_dirs:
            source_type = explicit_source_type or get_source_type(os.path.basename(os.path.normpath(base_dir)).lower())
            logfire.info(f"No sub folders found processing {base_dir} as {source_type}")
            process_directory(base_dir, source_type)
        else:
            for sub_dir in sub_dirs:
                source_type = get_source_type(sub_dir)
                process_directory(os.path.join(base_dir, sub_dir), source_type)

        logfire.info( "Ingestion completed", **stats) 
        return { **stats, "collection": coll, "embedding_dimension": get_embedding_dim(), }


if __name__ == "__main__":
    # python -m src.learning_assistant.data_ingestion.processor DATA --wipe
    # python -m src.learning_assistant.data_ingestion.processor DATA/true_data true

    wipe_request = "--wipe" in sys.argv
    clean_args = [i for i in sys.argv if i != "--wipe"]

    target_dir = clean_args[1] if len(clean_args)>1 else "DATA"
    explicit_type = clean_args[2] if len(clean_args)>2 else None

    if not os.path.exists(target_dir):
        print(f"Error: path {target_dir} does not exist")
        sys.exit(1)

    result = run_ingestion(target_dir, explicit_source_type=explicit_type, wipe_request=wipe_request)
    for key, value in result.items():
        print(f"{key}: {value}") 
        
    if result["files_failed"] > 0: 
        sys.exit(1)