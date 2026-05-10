import type { GraphView, WikiNodeDetail, SearchResponse, VaultPageSummary, VaultPageDetail } from "../types/graph";

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(path, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? `API error: ${res.status}`);
  }
  return res.json();
}

export async function fetchGraphView(): Promise<GraphView> {
  return apiFetch<GraphView>("/api/graph");
}

export async function fetchNodeDetail(name: string): Promise<WikiNodeDetail> {
  return apiFetch<WikiNodeDetail>(`/api/graph/nodes/${encodeURIComponent(name)}`);
}

export async function fetchSearch(query: string): Promise<SearchResponse> {
  return apiFetch<SearchResponse>(`/api/graph/search?q=${encodeURIComponent(query)}`);
}

export async function fetchVaultPages(subdir?: string): Promise<{ pages: VaultPageSummary[] }> {
  const params = subdir ? `?subdir=${encodeURIComponent(subdir)}` : "";
  return apiFetch(`/api/vault/pages${params}`);
}

export async function fetchVaultPage(path: string): Promise<VaultPageDetail> {
  return apiFetch(`/api/vault/pages/${path}`);
}

export async function uploadDocument(file: File): Promise<{ document_id: string; chapter_count: number }> {
  const form = new FormData();
  form.append("file", file);
  return apiFetch("/api/documents/upload", { method: "POST", body: form });
}

export async function runExtraction(documentId: string): Promise<{ concepts_written: number }> {
  return apiFetch("/api/extraction/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_id: documentId }),
  });
}
