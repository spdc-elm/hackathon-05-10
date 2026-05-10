import type { GraphView, WikiNodeDetail, SearchResponse, VaultPageSummary, VaultPageDetail } from "../types/graph";

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(path, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? `API error: ${res.status}`);
  }
  return res.json();
}

// --- Documents ---

export type DocumentMeta = {
  document_id: string;
  filename: string;
  title: string;
  format: string;
  size_bytes: number;
  status: string;
  chapter_count: number;
  total_chars: number;
  extraction_status: string;
  concept_count?: number;
};

export async function uploadDocument(file: File): Promise<{
  document_id: string;
  title: string;
  filename: string;
  format: string;
  chapter_count: number;
  total_chars: number;
  extraction_status: string;
}> {
  const form = new FormData();
  form.append("file", file);
  return apiFetch("/api/documents/upload", { method: "POST", body: form });
}

export async function listDocuments(): Promise<{ documents: DocumentMeta[] }> {
  return apiFetch("/api/documents");
}

export async function getDocument(id: string): Promise<{
  document_id: string;
  title: string;
  format: string;
  total_chars: number;
  extraction_status: string;
  concept_count: number;
  chapters: Array<{ chapter_id: string; title: string; char_count: number; page_start: number | null; page_end: number | null }>;
}> {
  return apiFetch(`/api/documents/${id}`);
}

export async function getExtractionStatus(id: string): Promise<{
  document_id: string;
  extraction_status: string;
  concept_count: number;
  error?: string;
}> {
  return apiFetch(`/api/extraction/status/${id}`);
}

export async function deleteDocument(id: string): Promise<void> {
  await apiFetch(`/api/documents/${id}`, { method: "DELETE" });
}

// --- Graph ---

export async function fetchGraphView(): Promise<GraphView> {
  return apiFetch<GraphView>("/api/graph");
}

export async function fetchNodeDetail(name: string): Promise<WikiNodeDetail> {
  return apiFetch<WikiNodeDetail>(`/api/graph/nodes/${encodeURIComponent(name)}`);
}

export async function fetchSearch(query: string): Promise<SearchResponse> {
  return apiFetch<SearchResponse>(`/api/graph/search?q=${encodeURIComponent(query)}`);
}

// --- Vault ---

export async function fetchVaultPages(subdir?: string): Promise<{ pages: VaultPageSummary[] }> {
  const params = subdir ? `?subdir=${encodeURIComponent(subdir)}` : "";
  return apiFetch(`/api/vault/pages${params}`);
}

export async function fetchVaultPage(path: string): Promise<VaultPageDetail> {
  return apiFetch(`/api/vault/pages/${path}`);
}
