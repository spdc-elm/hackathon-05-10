import { mockGraphView, getMockNodeDetail, getMockSearch } from "../mocks/graphViewMock";
import type { GraphView, NodeDetailResponse, SearchResponse } from "../types/graph";

const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true";

function delay(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  if (USE_MOCK) {
    return getMockResponse<T>(path, options);
  }
  const res = await fetch(path, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? `API error: ${res.status}`);
  }
  return res.json();
}

async function getMockResponse<T>(path: string, _options?: RequestInit): Promise<T> {
  await delay(200 + Math.random() * 300);

  if (path.includes("/api/graphs/view")) {
    return mockGraphView as unknown as T;
  }

  const nodeMatch = path.match(/\/api\/graphs\/[^/]+\/nodes\/([^/?]+)/);
  if (nodeMatch) {
    const detail = getMockNodeDetail(nodeMatch[1]);
    if (!detail) throw new Error("Node not found");
    return detail as unknown as T;
  }

  const searchMatch = path.match(/\/api\/graphs\/[^/]+\/search\?q=(.+)/);
  if (searchMatch) {
    return getMockSearch(decodeURIComponent(searchMatch[1])) as unknown as T;
  }

  if (path.includes("/api/documents")) {
    return {
      documents: [
        { document_id: "doc_a", filename: "生理学.pdf", title: "生理学（第9版）", format: "pdf", size_bytes: 385000, status: "parsed", chapter_count: 12, total_chars: 385000, graph_status: "ready" },
        { document_id: "doc_b", filename: "病理学.pdf", title: "病理学（第8版）", format: "pdf", size_bytes: 420000, status: "parsed", chapter_count: 15, total_chars: 420000, graph_status: "ready" },
      ],
    } as unknown as T;
  }

  throw new Error(`Mock not found for: ${path}`);
}

export async function fetchGraphView(documentIds: string[], mode: "per_document" | "frequency_preview"): Promise<GraphView> {
  return apiFetch<GraphView>("/api/graphs/view", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_ids: documentIds, mode }),
  });
}

export async function fetchNodeDetail(graphId: string, nodeId: string): Promise<NodeDetailResponse> {
  return apiFetch<NodeDetailResponse>(`/api/graphs/${graphId}/nodes/${nodeId}`);
}

export async function fetchSearch(graphId: string, query: string): Promise<SearchResponse> {
  return apiFetch<SearchResponse>(`/api/graphs/${graphId}/search?q=${encodeURIComponent(query)}`);
}
