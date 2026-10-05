from bs4 import BeautifulSoup
from pypdf import PdfReader
import pdfplumber
import logfire
import fitz
import re
from docx import Document
from pptx import Presentation
from pathlib import Path

# Unstructured - for extracting text from word doc and ppts
# Beautiful Soup - for extracting html text
# Pypdf - for extracting text from pdfs
# Logfire - logging and observability

def parse_html(file_path: str) -> str:

    """
    Parses HTML content using BeautifulSoup
    Cleans the scripts, styles, and extracts readable text for the RAG Application
    """

    with logfire.span("HTML Parsing", filename=file_path):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            soup = BeautifulSoup(content, "html.parser")

            # Remove unnecessary info such as scripts, styles, metadata
            for script in soup(["script", "style", "meta", "noscript"]):
                script.decompose()

            # Extract text
            text = soup.get_text(separator="\n")

            # Clean whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split(" "))
            text_clean = "\n".join(chunk for chunk in chunks if chunk)

            return text_clean
        
        except Exception as e:
            logfire.error(f"HTML Parser Failed: {e}")
            raise e


def parse_pdf(file_path: str) -> list[dict]:
    """
    Extracts PDF text page by page while preserving page numbers.
    Uses PyMuPDF, with pdfplumber and pypdf as fallbacks for empty pages.
    """

    def clean_pdf_text(text: str) -> str:
        text = re.sub(
            r"(?im)^\s*CHAPTER\s+\d+\s*[•·]?\s*$",
            "",
            text
        )

        text = re.sub(
            r"(?im)^\s*chapter\s*$",
            "",
            text
        )

        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    with logfire.span("PDF Parsing", filename=file_path):
        reader = PdfReader(file_path)
        total_pages = len(reader.pages)

        pages = []
        fallback_pages = []

        try:
            doc = fitz.open(file_path)

            for page_no, page in enumerate(doc, start=1):
                try:
                    text = page.get_text("text") or ""
                    text = clean_pdf_text(text)

                    if text:
                        pages.append({
                            "page_number": page_no,
                            "text": text
                        })
                    else:
                        fallback_pages.append(page_no)

                except Exception as e:
                    logfire.warning(
                        f"PyMuPDF failed on page {page_no}: {e}"
                    )
                    fallback_pages.append(page_no)

            doc.close()

        except Exception as e:
            logfire.warning(f"PyMuPDF failed: {e}")
            fallback_pages = list(range(1, total_pages + 1))

        # pdfplumber fallback
        if fallback_pages:
            try:
                with pdfplumber.open(file_path) as pdf:
                    for page_no in fallback_pages:
                        try:
                            text = pdf.pages[page_no - 1].extract_text() or ""
                            text = clean_pdf_text(text)

                            if text:
                                pages.append({
                                    "page_number": page_no,
                                    "text": text
                                })

                        except Exception as e:
                            logfire.warning(
                                f"pdfplumber failed on page {page_no}: {e}"
                            )

            except Exception as e:
                logfire.warning(f"pdfplumber failed: {e}")

        # pypdf fallback only for pages still missing
        extracted = {page["page_number"] for page in pages}
        remaining_pages = [
            p for p in range(1, total_pages + 1)
            if p not in extracted
        ]

        for page_no in remaining_pages:
            try:
                text = reader.pages[page_no - 1].extract_text() or ""
                text = clean_pdf_text(text)

                if text:
                    pages.append({
                        "page_number": page_no,
                        "text": text
                    })

            except Exception as e:
                logfire.warning(
                    f"pypdf failed on page {page_no}: {e}"
                )

        pages.sort(key=lambda x: x["page_number"])

        extracted = {page["page_number"] for page in pages}
        missing_pages = [
            p for p in range(1, total_pages + 1)
            if p not in extracted
        ]

        logfire.info(
            f"Successfully extracted {len(pages)}/{total_pages} pages"
        )

        if missing_pages:
            logfire.warning(
                f"Missing pages: {missing_pages[:30]}"
            )

        return pages


def parse_text(file_path: str) -> str:

    """
    Parses Plain Text
    """

    with logfire.span("Text Parsing", filename=file_path):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()

        except Exception as e:
            logfire.error(f"Text Parsing Failed: {e}")
            raise e


def parse_word_ppt(file_path: str) -> list[dict]:
    """
    Parses DOCX and PPTX files locally.

    PPTX:
        Returns one record per slide.

    DOCX:
        Returns document text as one record.
        DOCX page numbers are not reliably available from
        python-docx, so no fake page numbers are created.
    """

    path = Path(file_path)
    extension = path.suffix.lower()

    with logfire.span("Office Document Parsing", filename=file_path):
        try:
            if extension == ".pptx":
                presentation = Presentation(file_path)
                pages = []

                for slide_number, slide in enumerate(
                    presentation.slides, start=1
                ):
                    texts = []

                    for shape in slide.shapes:
                        if hasattr(shape, "text"):
                            text = shape.text.strip()
                            if text:
                                texts.append(text)

                    if texts:
                        pages.append({
                            "page_number": slide_number,
                            "text": "\n".join(texts)
                        })

                logfire.info(
                    f"Successfully extracted "
                    f"{len(pages)}/{len(presentation.slides)} slides"
                )

                return pages

            if extension == ".docx":
                document = Document(file_path)
                texts = []

                for paragraph in document.paragraphs:
                    text = paragraph.text.strip()
                    if text:
                        texts.append(text)

                # Extract table content too
                for table in document.tables:
                    for row in table.rows:
                        cells = [
                            cell.text.strip()
                            for cell in row.cells
                            if cell.text.strip()
                        ]

                        if cells:
                            texts.append(" | ".join(cells))

                complete_text = "\n".join(texts).strip()

                if not complete_text:
                    logfire.warning(f"Empty text for {file_path}")
                    return []

                logfire.info(
                    f"Successfully extracted "
                    f"{len(complete_text)} characters from DOCX"
                )

                return [{
                    "page_number": 1,
                    "text": complete_text
                }]

            raise ValueError(
                f"Unsupported Word/PPT file type: {extension}"
            )

        except Exception as e:
            logfire.error(
                f"Office Document Parsing Failed: {e}"
            )
            raise