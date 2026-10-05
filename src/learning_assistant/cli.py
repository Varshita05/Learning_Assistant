import os

import uvicorn


def main() -> None:
    uvicorn.run(
        "learning_assistant.main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
    )