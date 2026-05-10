import React, { createContext, useContext, useState, useCallback, useRef } from "react";
import type { GraphView, NodeDetailResponse, SearchMatch, ViewMode } from "../types/graph";
import { fetchGraphView, fetchNodeDetail, fetchSearch } from "../api/client";

type GraphState = {
  graphView: GraphView | null;
  loading: boolean;
  error: string;
  selectedNodeId: string | null;
  nodeDetail: NodeDetailResponse | null;
  nodeDetailLoading: boolean;
  searchQuery: string;
  searchMatches: SearchMatch[];
  viewMode: ViewMode;
  documentIds: string[];
  setSelectedNodeId: (id: string | null) => void;
  setSearchQuery: (q: string) => void;
  setViewMode: (m: ViewMode) => void;
  setDocumentIds: (ids: string[]) => void;
  loadGraph: () => void;
};

const GraphContext = createContext<GraphState | null>(null);

export function useGraphContext(): GraphState {
  const ctx = useContext(GraphContext);
  if (!ctx) throw new Error("useGraphContext must be used within GraphContextProvider");
  return ctx;
}

export function GraphContextProvider({ children }: { children: React.ReactNode }) {
  const [graphView, setGraphView] = useState<GraphView | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedNodeId, setSelectedNodeIdRaw] = useState<string | null>(null);
  const [nodeDetail, setNodeDetail] = useState<NodeDetailResponse | null>(null);
  const [nodeDetailLoading, setNodeDetailLoading] = useState(false);
  const [searchQuery, setSearchQueryRaw] = useState("");
  const [searchMatches, setSearchMatches] = useState<SearchMatch[]>([]);
  const [viewMode, setViewMode] = useState<ViewMode>("per_document");
  const [documentIds, setDocumentIds] = useState<string[]>(["doc_a", "doc_b"]);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const graphIdRef = useRef("view_mock_001");
  graphIdRef.current = graphView?.view_id ?? "view_mock_001";

  const loadGraph = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const view = await fetchGraphView(documentIds, viewMode);
      setGraphView(view);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load graph");
    } finally {
      setLoading(false);
    }
  }, [documentIds, viewMode]);

  const setSelectedNodeId = useCallback(
    (id: string | null) => {
      setSelectedNodeIdRaw(id);
      if (!id) {
        setNodeDetail(null);
        return;
      }
      setNodeDetailLoading(true);
      fetchNodeDetail(graphIdRef.current, id)
        .then((detail) => setNodeDetail(detail))
        .catch(() => setNodeDetail(null))
        .finally(() => setNodeDetailLoading(false));
    },
    [],
  );

  const setSearchQuery = useCallback(
    (q: string) => {
      setSearchQueryRaw(q);
      if (searchTimer.current) clearTimeout(searchTimer.current);
      if (!q.trim()) {
        setSearchMatches([]);
        return;
      }
      searchTimer.current = setTimeout(() => {
        fetchSearch(graphIdRef.current, q)
          .then((res) => setSearchMatches(res.matches))
          .catch(() => setSearchMatches([]));
      }, 300);
    },
    [],
  );

  return (
    <GraphContext.Provider
      value={{
        graphView,
        loading,
        error,
        selectedNodeId,
        nodeDetail,
        nodeDetailLoading,
        searchQuery,
        searchMatches,
        viewMode,
        documentIds,
        setSelectedNodeId,
        setSearchQuery,
        setViewMode,
        setDocumentIds,
        loadGraph,
      }}
    >
      {children}
    </GraphContext.Provider>
  );
}
