import { useState, useRef, useEffect, useCallback, DragEvent } from "react";
import { uploadDocument, listDocuments, getExtractionStatus, deleteDocument, type DocumentMeta } from "../api/client";
import { useGraphContext } from "../context/GraphContext";
import { GraphCanvas } from "./GraphCanvas";
import { GraphLegend } from "./GraphLegend";
import { NodeDetailPanel } from "./NodeDetailPanel";

type ViewMode = "graph" | "documents";

export function Workspace() {
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>("graph");
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { loadGraph, searchQuery, setSearchQuery, loading } = useGraphContext();
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refreshDocuments = useCallback(async () => {
    try {
      const res = await listDocuments();
      setDocuments(res.documents);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    refreshDocuments();
    loadGraph();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Poll extraction status for documents that are "running"
  useEffect(() => {
    const running = documents.filter((d) => d.extraction_status === "running");
    if (running.length === 0) {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
      return;
    }

    if (pollRef.current) return; // already polling

    pollRef.current = setInterval(async () => {
      let anyChanged = false;
      for (const doc of running) {
        try {
          const status = await getExtractionStatus(doc.document_id);
          if (status.extraction_status !== "running") {
            anyChanged = true;
          }
        } catch { /* ignore */ }
      }
      if (anyChanged) {
        await refreshDocuments();
        loadGraph(); // refresh graph with new concepts
      }
    }, 2000);

    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [documents, refreshDocuments, loadGraph]);

  async function handleUpload(file: File) {
    setUploading(true);
    try {
      const result = await uploadDocument(file);
      await refreshDocuments();
      setSelectedDocId(result.document_id);
      // Graph will update via polling when extraction completes
    } catch (e) {
      console.error("Upload failed:", e);
    } finally {
      setUploading(false);
    }
  }

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (files) {
      Array.from(files).forEach(handleUpload);
    }
    e.target.value = "";
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const files = e.dataTransfer.files;
    Array.from(files).forEach(handleUpload);
  }

  async function handleDelete(docId: string) {
    try {
      await deleteDocument(docId);
      if (selectedDocId === docId) setSelectedDocId(null);
      await refreshDocuments();
      loadGraph();
    } catch (e) {
      console.error("Delete failed:", e);
    }
  }

  const selectedDoc = documents.find((d) => d.document_id === selectedDocId) ?? null;

  return (
    <div className="ws-layout">
      {/* Sidebar */}
      <aside className="ws-sidebar">
        <div className="ws-sidebar-header">
          <h2>Documents</h2>
          <button
            className="ws-upload-btn"
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? "..." : "+"}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.md,.markdown,.txt"
            multiple
            onChange={handleFileSelect}
            style={{ display: "none" }}
          />
        </div>

        <div
          className={`ws-doc-list ${dragOver ? "drag-over" : ""}`}
          onDrop={handleDrop}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
        >
          {documents.length === 0 && !uploading && (
            <div className="ws-empty">Drop files here or click +</div>
          )}
          {uploading && <div className="ws-empty">Uploading...</div>}
          {documents.map((doc) => (
            <div
              key={doc.document_id}
              className={`ws-doc-item ${doc.document_id === selectedDocId ? "selected" : ""}`}
              onClick={() => setSelectedDocId(doc.document_id)}
            >
              <span className="ws-doc-title">{doc.title || doc.filename}</span>
              <span className="ws-doc-meta">
                {doc.format} &middot; {doc.chapter_count} ch
                <ExtractionBadge status={doc.extraction_status} />
                <button
                  className="ws-delete-btn"
                  type="button"
                  title="Delete"
                  onClick={(e) => { e.stopPropagation(); handleDelete(doc.document_id); }}
                >
                  &times;
                </button>
              </span>
            </div>
          ))}
        </div>

        {/* View mode tabs */}
        <div className="ws-sidebar-footer">
          <button
            className={`ws-tab ${viewMode === "graph" ? "active" : ""}`}
            onClick={() => setViewMode("graph")}
            type="button"
          >
            Graph
          </button>
          <button
            className={`ws-tab ${viewMode === "documents" ? "active" : ""}`}
            onClick={() => setViewMode("documents")}
            type="button"
          >
            Preview
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="ws-main">
        {viewMode === "graph" ? (
          <div className="ws-graph-view">
            <header className="ws-graph-toolbar">
              <div className="search-wrapper">
                <input
                  type="text"
                  className="search-input"
                  placeholder="Search concepts..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                {searchQuery && (
                  <button className="search-clear" type="button" onClick={() => setSearchQuery("")}>
                    &times;
                  </button>
                )}
              </div>
              <button
                className="ghost-button"
                type="button"
                onClick={loadGraph}
                disabled={loading}
              >
                {loading ? "..." : "Refresh"}
              </button>
            </header>
            <div className="ws-graph-canvas-area">
              <GraphCanvas />
              <NodeDetailPanel />
            </div>
            <GraphLegend />
          </div>
        ) : (
          <DocumentPreview doc={selectedDoc} />
        )}
      </main>
    </div>
  );
}

function ExtractionBadge({ status }: { status: string }) {
  if (status === "running") return <span className="badge badge-running">extracting</span>;
  if (status === "ready") return <span className="badge badge-ready">ready</span>;
  if (status === "error") return <span className="badge badge-error">error</span>;
  return null;
}

function DocumentPreview({ doc }: { doc: DocumentMeta | null }) {
  const [detail, setDetail] = useState<any>(null);
  const [expandedChapter, setExpandedChapter] = useState<string | null>(null);
  const [chapterContent, setChapterContent] = useState<string>("");
  const [loadingContent, setLoadingContent] = useState(false);

  useEffect(() => {
    setExpandedChapter(null);
    setChapterContent("");
    if (!doc) { setDetail(null); return; }
    fetch(`/api/documents/${doc.document_id}`)
      .then((r) => r.json())
      .then(setDetail)
      .catch(() => setDetail(null));
  }, [doc]);

  function toggleChapter(chapterId: string, title: string) {
    if (expandedChapter === chapterId) {
      setExpandedChapter(null);
      setChapterContent("");
      return;
    }
    setExpandedChapter(chapterId);
    setLoadingContent(true);
    // Read chapter from vault
    const safeTitle = (doc!.title || doc!.filename).replace(/\//g, "_").replace(/\\/g, "_");
    const safeCh = title.replace(/\//g, "_").replace(/\\/g, "_").replace(/ /g, "-");
    const path = `textbooks/${safeTitle}/${safeCh}.md`;
    fetch(`/api/vault/pages/${path}`)
      .then((r) => r.ok ? r.json() : Promise.reject())
      .then((data) => setChapterContent(data.content_md || ""))
      .catch(() => setChapterContent("(content not available)"))
      .finally(() => setLoadingContent(false));
  }

  if (!doc) {
    return (
      <div className="ws-preview-empty">
        <p>Select a document from the sidebar to preview</p>
      </div>
    );
  }

  return (
    <div className="ws-preview">
      <header className="ws-preview-header">
        <h2>{doc.title || doc.filename}</h2>
        <span className="ws-preview-meta">
          {doc.format} &middot; {doc.chapter_count} chapters &middot; {(doc.total_chars / 1000).toFixed(0)}k chars
        </span>
      </header>
      {detail?.chapters && (
        <div className="ws-chapter-list">
          {detail.chapters.map((ch: any) => (
            <div key={ch.chapter_id} className="ws-chapter-group">
              <div
                className={`ws-chapter-item ${expandedChapter === ch.chapter_id ? "expanded" : ""}`}
                onClick={() => toggleChapter(ch.chapter_id, ch.title)}
              >
                <span className="ws-ch-expand">{expandedChapter === ch.chapter_id ? "▼" : "▶"}</span>
                <span className="ws-ch-title">{ch.title}</span>
                <span className="ws-ch-meta">
                  {ch.char_count.toLocaleString()} chars
                  {ch.page_start && ` · p.${ch.page_start}${ch.page_end && ch.page_end !== ch.page_start ? `–${ch.page_end}` : ""}`}
                </span>
              </div>
              {expandedChapter === ch.chapter_id && (
                <div className="ws-chapter-content">
                  {loadingContent ? (
                    <span className="ws-ch-loading">Loading...</span>
                  ) : (
                    <pre>{chapterContent}</pre>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
