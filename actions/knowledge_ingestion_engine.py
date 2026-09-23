"""
actions/knowledge_ingestion_engine.py — Sovereign Knowledge Ingestion & Vector Feeder
=====================================================================================
Recursively parses, extracts, chunks, and indexes all educational books, documents,
and PDFs from W:\\desktop deta and other storage repositories into J.A.R.V.I.S.
durable SQLite vector memory and knowledge base.
=====================================================================================
"""

import os
import sys
import json
import time
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logger = logging.getLogger("jarvis.knowledge_ingest")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

MEMORY_DB = ROOT / "memory" / "mission_memory.db"
KNOWLEDGE_INDEX_FILE = ROOT / "memory" / "books_knowledge_index.json"

try:
    import pypdf
    _HAS_PYPDF = True
except ImportError:
    _HAS_PYPDF = False

try:
    import docx
    _HAS_DOCX = True
except ImportError:
    _HAS_DOCX = False

from memory.mission_memory import remember_vector, recall_vector, get_embedding


def extract_text_from_pdf(pdf_path: Path, max_pages: int = 80) -> str:
    """Extracts clean text from a PDF file using pypdf."""
    if not _HAS_PYPDF:
        return ""
    text_chunks = []
    try:
        reader = pypdf.PdfReader(str(pdf_path))
        num_pages = min(len(reader.pages), max_pages)
        for i in range(num_pages):
            try:
                page = reader.pages[i]
                txt = page.extract_text()
                if txt and txt.strip():
                    text_chunks.append(txt.strip())
            except Exception:
                continue
    except Exception as e:
        logger.debug(f"Could not extract text from {pdf_path.name}: {e}")
    return "\n\n".join(text_chunks)


def extract_text_from_docx(docx_path: Path) -> str:
    """Extracts text from a DOCX file."""
    if not _HAS_DOCX:
        return ""
    try:
        doc = docx.Document(str(docx_path))
        return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    except Exception as e:
        logger.debug(f"Could not extract text from {docx_path.name}: {e}")
        return ""


def extract_file_content(file_path: Path) -> str:
    """Extracts text content based on file extension."""
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(file_path)
    elif suffix in (".txt", ".md", ".json", ".csv"):
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                return file_path.read_text(encoding=enc, errors="ignore")
            except Exception:
                continue
    elif suffix in (".docx", ".doc"):
        return extract_text_from_docx(file_path)
    return ""


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
    """Splits text into overlapping semantic chunks."""
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if len(chunk) > 60:
            chunks.append(chunk)
        start += (chunk_size - overlap)
    return chunks


def ingest_knowledge_directory(
    source_dir: Path,
    max_files: int = 100,
    max_chunks_per_file: int = 25
) -> Dict[str, Any]:
    """
    Scans, extracts, and feeds books and documents into J.A.R.V.I.S. memory.
    """
    if not source_dir.exists():
        return {"ok": False, "error": f"Directory not found: {source_dir}"}
    
    start_time = time.time()
    files_processed = 0
    total_chunks_indexed = 0
    books_catalog = []

    supported_exts = {".pdf", ".txt", ".md", ".docx", ".json"}
    all_files = [f for f in source_dir.rglob("*") if f.is_file() and f.suffix.lower() in supported_exts]

    logger.info(f"[KnowledgeIngest] Found {len(all_files)} files in {source_dir}. Ingesting up to {max_files} files...")

    for file_path in all_files[:max_files]:
        try:
            rel_name = file_path.relative_to(source_dir)
            logger.info(f"[KnowledgeIngest] Processing: {rel_name}")
            
            raw_text = extract_file_content(file_path)
            if not raw_text or len(raw_text.strip()) < 80:
                continue

            chunks = chunk_text(raw_text, chunk_size=800, overlap=150)[:max_chunks_per_file]
            
            book_entry = {
                "file_name": file_path.name,
                "relative_path": str(rel_name),
                "category": file_path.parent.name or "General",
                "chunks_count": len(chunks),
                "size_kb": round(file_path.stat().st_size / 1024, 1)
            }
            books_catalog.append(book_entry)

            for idx, chunk in enumerate(chunks):
                chunk_key = f"book:{hashlib.sha256((str(rel_name) + str(idx)).encode()).hexdigest()[:16]}"
                
                # Store in dense vector memory
                remember_vector(
                    content=chunk,
                    category="book_knowledge",
                    key=chunk_key,
                    metadata={
                        "book_title": file_path.stem,
                        "category": file_path.parent.name,
                        "source_file": str(file_path),
                        "chunk_index": idx
                    },
                    confidence=1.0
                )
                total_chunks_indexed += 1

            files_processed += 1

        except Exception as e:
            logger.warning(f"Failed to ingest {file_path.name}: {e}")
            continue

    # Save summary catalog to memory index
    summary_data = {
        "ingested_at": time.time(),
        "source_directory": str(source_dir),
        "total_files_processed": files_processed,
        "total_chunks_indexed": total_chunks_indexed,
        "duration_seconds": round(time.time() - start_time, 2),
        "books": books_catalog
    }
    
    KNOWLEDGE_INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    KNOWLEDGE_INDEX_FILE.write_text(json.dumps(summary_data, indent=2), encoding="utf-8")

    logger.info(f"[KnowledgeIngest] Complete! Ingested {files_processed} books ({total_chunks_indexed} vector chunks) in {round(time.time() - start_time, 2)}s.")
    
    return {
        "ok": True,
        "files_processed": files_processed,
        "chunks_indexed": total_chunks_indexed,
        "duration_sec": round(time.time() - start_time, 2),
        "catalog": books_catalog[:20]
    }


def query_book_knowledge(query: str, top_k: int = 4) -> List[Dict[str, Any]]:
    """Retrieves most relevant knowledge chunks across ingested books."""
    matches = recall_vector(query, category="book_knowledge", top_k=top_k, min_similarity=0.45)
    return [m.to_dict() for m in matches]


if __name__ == "__main__":
    src = Path("W:/desktop deta")
    if not src.exists():
        src = Path("W:/books")
    res = ingest_knowledge_directory(src)
    print("Ingestion Result:", json.dumps(res, indent=2))
