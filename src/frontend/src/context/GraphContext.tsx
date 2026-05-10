import React, { createContext, useContext, useState, useCallback, useRef } from "react";
import type { GraphView, WikiNodeDetail, SearchMatch } from "../types/graph";
import { fetchGraphView, fetchNodeDetail, fetchSearch } from "../api/client";

type GraphState = {
  graphView: GraphView | null;
  loading: boolean;
  error: string;
  selectedNodeName: string | null;
  nodeDetail: WikiNodeDetail | null;
  nodeDetailLoading: boolean;
  searchQuery: string;
  searchMatches: SearchMatch[];
  setSelectedNodeName: (name: string | null) => void;
  setSearchQuery: (q: string) => void;
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
  const [selectedNodeName, setSelectedNodeNameRaw] = useState<string | null>(null);
  const [nodeDetail, setNodeDetail] = useState<WikiNodeDetail | null>(null);
  const [nodeDetailLoading, setNodeDetailLoading] = useState(false);
  const [searchQuery, setSearchQueryRaw] = useState("");
  const [searchMatches, setSearchMatches] = useState<SearchMatch[]>([]);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadGraph = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const view = await fetchGraphView();
      setGraphView(view);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load graph");
    } finally {
      setLoading(false);
    }
  }, []);

  const setSelectedNodeName = useCallback((name: string | null) => {
    setSelectedNodeNameRaw(name);
    if (!name) {
      setNodeDetail(null);
      return;
    }
    setNodeDetailLoading(true);
    fetchNodeDetail(name)
      .then((detail) => setNodeDetail(detail))
      .catch(() => setNodeDetail(null))
      .finally(() => setNodeDetailLoading(false));
  }, []);

  const setSearchQuery = useCallback((q: string) => {
    setSearchQueryRaw(q);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    if (!q.trim()) {
      setSearchMatches([]);
      return;
    }
    searchTimer.current = setTimeout(() => {
      fetchSearch(q)
        .then((res) => setSearchMatches(res.matches))
        .catch(() => setSearchMatches([]));
    }, 300);
  }, []);

  return (
    <GraphContext.Provider
      value={{
        graphView,
        loading,
        error,
        selectedNodeName,
        nodeDetail,
        nodeDetailLoading,
        searchQuery,
        searchMatches,
        setSelectedNodeName,
        setSearchQuery,
        loadGraph,
      }}
    >
      {children}
    </GraphContext.Provider>
  );
}
