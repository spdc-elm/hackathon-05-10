import React, { useMemo, useState, useRef, DragEvent } from "react";

type AssetReference = {
  kind: string;
  label: string;
  path: string;
  line?: number | null;
};

type ParsedChapter = {
  chapter_id: string;
  title: string;
  content: string;
  char_count: number;
  page_start?: number | null;
  page_end?: number | null;
  level?: number | null;
  line_start?: number | null;
  line_end?: number | null;
  assets?: AssetReference[];
};

type ParsedDocument = {
  textbook_id: string;
  filename: string;
  title: string;
  total_pages?: number | null;
  total_chars: number;
  chapters: ParsedChapter[];
  format?: string;
  source_path?: string | null;
};

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("zh-CN").format(value);
}

function formatRange(start?: number | null, end?: number | null) {
  if (start === null || start === undefined) return "—";
  if (end === null || end === undefined || end === start) return String(start);
  return `${start}–${end}`;
}

type UploadState = "idle" | "uploading" | "done" | "error";

type Props = {
  onViewGraph: () => void;
};

export function UploadPage({ onViewGraph }: Props) {
  const [document, setDocument] = useState<ParsedDocument | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const selectedChapter = useMemo(() => {
    if (!document) return null;
    return document.chapters.find((c) => c.chapter_id === selectedId) ?? document.chapters[0] ?? null;
  }, [document, selectedId]);

  const totals = useMemo(() => {
    if (!document) return { assets: 0, avgChars: 0 };
    const assets = document.chapters.reduce((sum, c) => sum + (c.assets?.length ?? 0), 0);
    const avgChars = document.chapters.length > 0 ? Math.round(document.total_chars / document.chapters.length) : 0;
    return { assets, avgChars };
  }, [document]);

  async function uploadFile(file: File) {
    setUploadState("uploading");
    setError("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch("/api/parse/upload", { method: "POST", body: formData });
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(body.detail ?? `Upload failed: ${res.status}`);
      }
      const parsed: ParsedDocument = await res.json();
      setDocument(parsed);
      setSelectedId(parsed.chapters[0]?.chapter_id ?? "");
      setUploadState("done");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed.");
      setUploadState("error");
    }
  }

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) uploadFile(file);
    e.target.value = "";
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file);
  }

  function handleDragOver(e: DragEvent) {
    e.preventDefault();
    setDragOver(true);
  }

  function handleDragLeave(e: DragEvent) {
    e.preventDefault();
    setDragOver(false);
  }

  function reset() {
    setDocument(null);
    setSelectedId("");
    setUploadState("idle");
    setError("");
  }

  if (!document) {
    return (
      <main className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Knowledge Integrator</p>
            <h1>Document Upload</h1>
          </div>
          <div className="actions">
            <button className="upload-btn" type="button" onClick={onViewGraph}>
              View Graph
            </button>
          </div>
        </header>

        <section
          className={`upload-zone ${dragOver ? "drag-over" : ""} ${uploadState === "uploading" ? "uploading" : ""}`}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.md,.markdown,.txt"
            onChange={handleFileSelect}
            style={{ display: "none" }}
          />
          {uploadState === "uploading" ? (
            <div className="upload-progress">
              <div className="spinner" />
              <p>Parsing document...</p>
            </div>
          ) : (
            <>
              <div className="upload-icon">&#8593;</div>
              <p className="upload-label">Drop a file here or click to browse</p>
              <p className="upload-hint">Supports PDF, Markdown, TXT</p>
            </>
          )}
        </section>

        {error && <div className="error">{error}</div>}
      </main>
    );
  }

  return (
    <main className="workspace">
      <header className="topbar">
        <div>
          <p className="eyebrow">Parse Result</p>
          <h1>{document.title}</h1>
        </div>
        <div className="actions">
          <button className="upload-btn" type="button" onClick={onViewGraph}>
            View Graph
          </button>
          <button className="ghost-button" type="button" onClick={() => fileInputRef.current?.click()}>
            Upload Another
          </button>
          <button className="ghost-button" type="button" onClick={reset}>
            Reset
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.md,.markdown,.txt"
            onChange={handleFileSelect}
            style={{ display: "none" }}
          />
        </div>
      </header>

      {error && <div className="error">{error}</div>}

      <section className="summary" aria-label="Document summary">
        <div>
          <span>Format</span>
          <strong>{document.format ?? "unknown"}</strong>
        </div>
        <div>
          <span>Chapters</span>
          <strong>{formatNumber(document.chapters.length)}</strong>
        </div>
        <div>
          <span>Total Chars</span>
          <strong>{formatNumber(document.total_chars)}</strong>
        </div>
        <div>
          <span>Avg Chars</span>
          <strong>{formatNumber(totals.avgChars)}</strong>
        </div>
        <div>
          <span>Assets</span>
          <strong>{formatNumber(totals.assets)}</strong>
        </div>
      </section>

      <section className="review-grid">
        <aside className="pane chapter-list" aria-label="Chapters">
          <div className="pane-header">
            <h2>Chapters</h2>
            <span>{document.filename}</span>
          </div>
          <div className="chapter-scroll">
            {document.chapters.map((chapter) => (
              <button
                className={chapter.chapter_id === selectedChapter?.chapter_id ? "chapter-row selected" : "chapter-row"}
                key={chapter.chapter_id}
                onClick={() => setSelectedId(chapter.chapter_id)}
                type="button"
              >
                <span className="chapter-title">{chapter.title}</span>
                <span className="chapter-meta">
                  {chapter.chapter_id} &middot; {formatNumber(chapter.char_count)} chars
                </span>
              </button>
            ))}
          </div>
        </aside>

        <section className="pane chapter-detail" aria-label="Selected chapter">
          <div className="pane-header">
            <div>
              <h2>{selectedChapter?.title ?? "No chapter"}</h2>
              <span>
                page {formatRange(selectedChapter?.page_start, selectedChapter?.page_end)} &middot; line{" "}
                {formatRange(selectedChapter?.line_start, selectedChapter?.line_end)}
              </span>
            </div>
          </div>
          <pre className="content-preview">{selectedChapter?.content ?? ""}</pre>
          <div className="asset-strip">
            {(selectedChapter?.assets ?? []).length === 0 ? (
              <span>No asset metadata</span>
            ) : (
              selectedChapter?.assets?.map((asset, index) => (
                <span key={`${asset.path}-${index}`}>
                  {asset.kind}: {asset.label || asset.path}
                  {asset.line ? ` @ line ${asset.line}` : ""}
                </span>
              ))
            )}
          </div>
        </section>

        <aside className="pane raw-json" aria-label="Raw JSON">
          <div className="pane-header">
            <h2>Raw JSON</h2>
            <span>{document.textbook_id}</span>
          </div>
          <pre>{JSON.stringify(document, null, 2)}</pre>
        </aside>
      </section>
    </main>
  );
}
