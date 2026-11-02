"""
OncoSentinel v2.0 — Clinical Guideline & Literature Ingestion Utility
Extracts text from guideline PDFs and TXT files, applies semantic chunking,
and populates the Vector Store with citation metadata.

Usage:
    py -3.12 scripts/ingest_guidelines.py
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
from typing import List

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

from services.rag.vector_store import get_vector_store, KnowledgeChunk



def clean_text(text: str) -> str:
    """Removes irregular whitespace and normalization artifacts."""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = 350, overlap: int = 50) -> List[str]:
    """Splits text into overlapping word chunks preserving sentence flow."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i : i + chunk_size])
        if len(chunk.split()) > 30:  # omit trivial snippets
            chunks.append(chunk)
    return chunks


def ingest_file(file_path: Path, category: str, citation_id: str, title: str) -> int:
    """Parses, chunks, and writes document embeddings into the vector store."""
    store = get_vector_store()
    print(f"\n[+] Ingesting: {file_path.name}")
    print(f"    Title: {title}")
    print(f"    Category: {category} | Citation ID: {citation_id}")

    full_text = ""
    if file_path.suffix.lower() == ".pdf":
        if fitz is None:
            raise RuntimeError(
                "PyMuPDF is required to parse PDF files. Install with: py -3.12 -m pip install pymupdf"
            )
        doc = fitz.open(str(file_path))
        for page_num in range(len(doc)):
            page_text = doc[page_num].get_text()
            full_text += f"\n[Page {page_num+1}] " + page_text
    else:
        full_text = file_path.read_text(encoding="utf-8")

    clean = clean_text(full_text)
    chunks = chunk_text(clean, chunk_size=350, overlap=50)

    for idx, chunk_content in enumerate(chunks):
        chunk_obj = KnowledgeChunk(
            chunk_id=f"{citation_id}_{idx:04d}",
            source_title=title,
            citation_id=citation_id,
            category=category,
            content=chunk_content,
            metadata={
                "file_name": file_path.name,
                "chunk_index": idx,
                "total_chunks": len(chunks),
            },
        )
        store.add_chunk(chunk_obj)

    print(f"    Indexed {len(chunks)} chunks into Vector Store.")
    return len(chunks)


def main():
    parser = argparse.ArgumentParser(description="Ingest oncology guidelines into OncoSentinel Vector Store")
    parser.add_argument("--file", type=str, help="Path to PDF or TXT guideline file")
    parser.add_argument("--category", type=str, default="general", help="Cancer category (e.g. breast, kidney, brain)")
    parser.add_argument("--citation", type=str, default="GUIDELINE", help="Citation ID (e.g. NCCN-BREAST-2024)")
    parser.add_argument("--title", type=str, default="Clinical Practice Guideline", help="Full guideline title")
    args = parser.parse_args()

    guidelines_dir = Path("data/guidelines")
    guidelines_dir.mkdir(parents=True, exist_ok=True)

    if args.file:
        file_p = Path(args.file)
        if not file_p.exists():
            print(f"File not found: {file_p}")
            return
        ingest_file(file_p, args.category, args.citation, args.title)
    else:
        # Scan data/guidelines directory
        found_files = list(guidelines_dir.glob("*.pdf")) + list(guidelines_dir.glob("*.txt"))
        if not found_files:
            print(f"[!] No guideline files found in {guidelines_dir.resolve()}.")
            print("    Place your oncology guidelines (PDF or TXT) in data/guidelines/ and rerun:")
            print("    py -3.12 scripts/ingest_guidelines.py --file data/guidelines/my_doc.pdf --category breast --citation NCCN-BREAST-2024 --title 'NCCN Breast Cancer Guidelines'")
        else:
            print(f"Found {len(found_files)} guideline file(s) in {guidelines_dir}:")
            for f in found_files:
                stem = f.stem.replace("_", "-").upper()
                ingest_file(f, category="general", citation_id=f"REF-{stem[:12]}", title=f.name)


if __name__ == "__main__":
    main()
