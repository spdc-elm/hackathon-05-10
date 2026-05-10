"""FastAPI server - LLM Wiki approach (万物皆MD)."""

from __future__ import annotations

import asyncio
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.parsers import MarkdownParser, PdfParser
from app.parsers.base import ParsedChapter, ParsedDocument
from app.services.concept_writer import ConceptWriter
from app.services.graph_builder import GraphBuilder
from app.services.llm import LLMConfigurationError, LLMError
from app.services.vault import VaultService
from app.storage.repository import RuntimeRepository

app = FastAPI(title="LLM Wiki - Knowledge Integrator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PARSERS = {
    ".pdf": PdfParser(),
    ".md": MarkdownParser(),
    ".markdown": MarkdownParser(),
    ".txt": MarkdownParser(),
}

MAX_FILE_SIZE_MB = 512
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024


def get_vault_service() -> VaultService:
    vault = VaultService(get_settings().vault_dir)
    vault.ensure_structure()
    return vault


def get_runtime_repository() -> RuntimeRepository:
    return RuntimeRepository(get_settings().runtime_dir)


def get_graph_builder(vault: VaultService = Depends(get_vault_service)) -> GraphBuilder:
    return GraphBuilder(vault)


# --- Health ---


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# --- Document Upload & Management ---


@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    repo: RuntimeRepository = Depends(get_runtime_repository),
    vault: VaultService = Depends(get_vault_service),
) -> dict[str, Any]:
    """Upload, parse, write chapters to vault, and trigger async extraction."""
    document, meta = await _parse_and_register_upload(file, repo)

    writer = ConceptWriter(vault)
    writer.write_textbook_chapters(document)

    # Fire extraction in background
    repo.update_document_meta(document.textbook_id, {"extraction_status": "running"})
    background_tasks.add_task(_run_extraction_background, document, repo, vault)

    return {
        "document_id": document.textbook_id,
        "status": "parsed",
        "title": document.title,
        "filename": document.filename,
        "format": document.format,
        "chapter_count": len(document.chapters),
        "total_chars": document.total_chars,
        "extraction_status": "running",
    }


@app.post("/api/parse/upload")
async def parse_upload(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    repo: RuntimeRepository = Depends(get_runtime_repository),
    vault: VaultService = Depends(get_vault_service),
) -> dict[str, Any]:
    """Upload and parse, returning the full ParsedDocument. Also triggers extraction."""
    document, _meta = await _parse_and_register_upload(file, repo)
    writer = ConceptWriter(vault)
    writer.write_textbook_chapters(document)

    repo.update_document_meta(document.textbook_id, {"extraction_status": "running"})
    background_tasks.add_task(_run_extraction_background, document, repo, vault)

    return document.to_dict()


@app.get("/api/documents")
def list_documents(
    repo: RuntimeRepository = Depends(get_runtime_repository),
) -> dict[str, Any]:
    return {"documents": repo.list_documents()}


@app.get("/api/documents/{document_id}")
def get_document(
    document_id: str,
    repo: RuntimeRepository = Depends(get_runtime_repository),
) -> dict[str, Any]:
    document = _load_document_or_404(repo, document_id)
    meta = _get_meta_safe(repo, document_id)
    return {
        "document_id": document_id,
        "title": document.title,
        "filename": document.filename,
        "format": document.format,
        "total_chars": document.total_chars,
        "extraction_status": meta.get("extraction_status", "none"),
        "concept_count": meta.get("concept_count", 0),
        "chapters": [_chapter_summary(ch) for ch in document.chapters],
    }


@app.delete("/api/documents/{document_id}")
def delete_document(
    document_id: str,
    repo: RuntimeRepository = Depends(get_runtime_repository),
    vault: VaultService = Depends(get_vault_service),
) -> dict[str, Any]:
    """Delete a document and its associated vault files."""
    meta = _get_meta_safe(repo, document_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Remove vault textbook files
    title = meta.get("title", "")
    if title:
        safe_title = title.replace("/", "_").replace("\\", "_")
        textbook_dir = Path(vault.root) / "textbooks" / safe_title
        if textbook_dir.exists():
            import shutil
            shutil.rmtree(textbook_dir)

    # Remove concept files linked to this document
    concepts_dir = Path(vault.root) / "concepts"
    if concepts_dir.exists():
        for md_file in list(concepts_dir.glob("*.md")):
            try:
                page = vault.read_page(f"concepts/{md_file.name}")
                if page.frontmatter.get("textbook_id") == document_id:
                    md_file.unlink()
            except Exception:
                continue

    # Remove runtime document data
    doc_dir = repo.documents_dir / document_id
    if doc_dir.exists():
        import shutil
        shutil.rmtree(doc_dir)

    return {"status": "deleted", "document_id": document_id}


# --- Extraction ---


@app.post("/api/extraction/run")
async def run_extraction(
    request: dict[str, Any],
    background_tasks: BackgroundTasks,
    repo: RuntimeRepository = Depends(get_runtime_repository),
    vault: VaultService = Depends(get_vault_service),
) -> dict[str, Any]:
    """Manually trigger extraction for a document."""
    document_id = str(request.get("document_id") or "").strip()
    if not document_id:
        raise HTTPException(status_code=400, detail="document_id is required.")

    document = _load_document_or_404(repo, document_id)
    repo.update_document_meta(document_id, {"extraction_status": "running"})
    background_tasks.add_task(_run_extraction_background, document, repo, vault)

    return {"document_id": document_id, "status": "running"}


@app.get("/api/extraction/status/{document_id}")
def extraction_status(
    document_id: str,
    repo: RuntimeRepository = Depends(get_runtime_repository),
) -> dict[str, Any]:
    """Poll extraction progress for a document."""
    meta = _get_meta_safe(repo, document_id)
    return {
        "document_id": document_id,
        "extraction_status": meta.get("extraction_status", "none"),
        "concept_count": meta.get("concept_count", 0),
        "error": meta.get("extraction_error"),
    }


# --- Vault Browse ---


@app.get("/api/vault/pages")
def list_vault_pages(
    subdir: str | None = None,
    vault: VaultService = Depends(get_vault_service),
) -> dict[str, Any]:
    pages = vault.list_pages(subdir)
    return {"pages": [{"path": p.path, "title": p.title, "category": p.category} for p in pages]}


@app.get("/api/vault/pages/{path:path}")
def read_vault_page(
    path: str,
    vault: VaultService = Depends(get_vault_service),
) -> dict[str, Any]:
    try:
        page = vault.read_page(path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Page not found.") from exc
    return {
        "path": page.path,
        "frontmatter": page.frontmatter,
        "content_md": page.body,
        "wikilinks": page.wikilinks,
    }


# --- Graph (derived from vault wikilinks) ---


@app.get("/api/graph")
def get_graph(
    builder: GraphBuilder = Depends(get_graph_builder),
) -> dict[str, Any]:
    return builder.build_graph_view()


@app.get("/api/graph/nodes/{name}")
def get_node_detail(
    name: str,
    builder: GraphBuilder = Depends(get_graph_builder),
) -> dict[str, Any]:
    detail = builder.get_node_detail(name)
    if detail is None:
        raise HTTPException(status_code=404, detail="Concept not found.")
    return detail


@app.get("/api/graph/search")
def search_graph(
    q: str = "",
    builder: GraphBuilder = Depends(get_graph_builder),
) -> dict[str, Any]:
    if not q.strip():
        raise HTTPException(status_code=400, detail="q is required.")
    matches = builder.search_nodes(q)
    return {"matches": matches}


# --- Background tasks ---


async def _run_extraction_background(
    document: ParsedDocument,
    repo: RuntimeRepository,
    vault: VaultService,
) -> None:
    """Run LLM extraction in background, updating meta on completion."""
    writer = ConceptWriter(vault)
    try:
        paths = await writer.extract_and_write(document)
        repo.update_document_meta(document.textbook_id, {
            "extraction_status": "ready",
            "concept_count": len(paths),
            "updated_at": _now_iso(),
        })
    except (LLMConfigurationError, LLMError) as exc:
        repo.update_document_meta(document.textbook_id, {
            "extraction_status": "error",
            "extraction_error": str(exc),
            "updated_at": _now_iso(),
        })
    except Exception as exc:
        repo.update_document_meta(document.textbook_id, {
            "extraction_status": "error",
            "extraction_error": f"Unexpected: {exc}",
            "updated_at": _now_iso(),
        })


# --- Internal helpers ---


async def _parse_and_register_upload(
    file: UploadFile,
    repo: RuntimeRepository,
) -> tuple[ParsedDocument, dict[str, Any]]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    suffix = Path(file.filename).suffix.lower()
    parser = PARSERS.get(suffix)
    if parser is None:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type: {suffix}. Supported: {', '.join(PARSERS.keys())}",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {MAX_FILE_SIZE_MB} MB).",
        )

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        document_id = f"doc_{uuid.uuid4().hex[:8]}"
        document = parser.parse(tmp_path, textbook_id=document_id)
        document.filename = file.filename
        document.title = Path(file.filename).stem
        document.source_path = None
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Parse error: {exc}") from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    meta = {
        "document_id": document.textbook_id,
        "filename": document.filename,
        "title": document.title,
        "format": document.format,
        "size_bytes": len(content),
        "status": "parsed",
        "chapter_count": len(document.chapters),
        "total_chars": document.total_chars,
        "extraction_status": "none",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    repo.save_document(document, meta)
    return document, meta


def _load_document_or_404(repo: RuntimeRepository, document_id: str) -> ParsedDocument:
    try:
        return repo.load_document(document_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Document not found.") from exc


def _get_meta_safe(repo: RuntimeRepository, document_id: str) -> dict[str, Any]:
    try:
        return repo.get_document_meta(document_id)
    except FileNotFoundError:
        return {}


def _chapter_summary(chapter: ParsedChapter) -> dict[str, Any]:
    return {
        "chapter_id": chapter.chapter_id,
        "title": chapter.title,
        "char_count": chapter.char_count,
        "page_start": chapter.page_start,
        "page_end": chapter.page_end,
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
