import React, { createContext, useContext, useState, useCallback, useRef } from "react";
import type { GraphView, WikiNodeDetail, SearchMatch, MergeDecisionDetail, MergeDecisionFilter, MergeDecisionSummary } from "../types/graph";
import { fetchGraphView, fetchNodeDetail, fetchSearch, fetchMergeDecisionDetail, fetchMergeDecisions, scanMergeDecisions } from "../api/client";

type GraphState = {
  graphView: GraphView | null;
  loading: boolean;
  error: string;
  selectedNodeName: string | null;
  nodeDetail: WikiNodeDetail | null;
  nodeDetailLoading: boolean;
  searchQuery: string;
  searchMatches: SearchMatch[];
  mergePanelOpen: boolean;
  mergeDecisionFilter: MergeDecisionFilter;
  mergeDecisions: MergeDecisionSummary[];
  mergeDecisionDetail: MergeDecisionDetail | null;
  mergeDecisionLoading: boolean;
  mergeDecisionError: string;
  setSelectedNodeName: (name: string | null) => void;
  setSearchQuery: (q: string) => void;
  loadGraph: () => void;
  setMergeDecisionFilter: (status: MergeDecisionFilter) => void;
  loadMergeDecisions: (status?: MergeDecisionFilter) => void;
  scanMerges: () => void;
  openMergeDecision: (decisionId: string) => void;
  closeMergePanel: () => void;
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
  const [mergePanelOpen, setMergePanelOpen] = useState(false);
  const [mergeDecisionFilter, setMergeDecisionFilterRaw] = useState<MergeDecisionFilter>("candidate");
  const [mergeDecisions, setMergeDecisions] = useState<MergeDecisionSummary[]>([]);
  const [mergeDecisionDetail, setMergeDecisionDetail] = useState<MergeDecisionDetail | null>(null);
  const [mergeDecisionLoading, setMergeDecisionLoading] = useState(false);
  const [mergeDecisionError, setMergeDecisionError] = useState("");
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const sortDecisions = (items: MergeDecisionSummary[]) =>
    [...items].sort((a, b) => Date.parse(b.updated_at || "") - Date.parse(a.updated_at || ""));

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

  const loadMergeDecisions = useCallback(async (status: MergeDecisionFilter = mergeDecisionFilter) => {
    setMergeDecisionLoading(true);
    setMergeDecisionError("");
    try {
      const res = await fetchMergeDecisions(status);
      setMergeDecisions(sortDecisions(res.decisions));
    } catch (e) {
      setMergeDecisionError(e instanceof Error ? e.message : "Failed to load merge decisions");
      setMergeDecisions([]);
    } finally {
      setMergeDecisionLoading(false);
    }
  }, [mergeDecisionFilter]);

  const setMergeDecisionFilter = useCallback((status: MergeDecisionFilter) => {
    setMergeDecisionFilterRaw(status);
    loadMergeDecisions(status);
  }, [loadMergeDecisions]);

  const openMergeDecision = useCallback((decisionId: string) => {
    setMergePanelOpen(true);
    setMergeDecisionLoading(true);
    setMergeDecisionError("");
    fetchMergeDecisionDetail(decisionId)
      .then((detail) => setMergeDecisionDetail(detail))
      .catch((e) => {
        setMergeDecisionError(e instanceof Error ? e.message : "Failed to load merge decision");
        setMergeDecisionDetail(null);
      })
      .finally(() => setMergeDecisionLoading(false));
  }, []);

  const scanMerges = useCallback(async () => {
    setMergePanelOpen(true);
    setMergeDecisionFilterRaw("candidate");
    setMergeDecisionDetail(null);
    setMergeDecisionLoading(true);
    setMergeDecisionError("");
    try {
      await scanMergeDecisions();
      const res = await fetchMergeDecisions("candidate");
      setMergeDecisions(sortDecisions(res.decisions));
    } catch (e) {
      setMergeDecisionError(e instanceof Error ? e.message : "Failed to scan merge decisions");
    } finally {
      setMergeDecisionLoading(false);
    }
  }, []);

  const closeMergePanel = useCallback(() => {
    setMergePanelOpen(false);
    setMergeDecisionDetail(null);
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
        mergePanelOpen,
        mergeDecisionFilter,
        mergeDecisions,
        mergeDecisionDetail,
        mergeDecisionLoading,
        mergeDecisionError,
        setSelectedNodeName,
        setSearchQuery,
        loadGraph,
        setMergeDecisionFilter,
        loadMergeDecisions,
        scanMerges,
        openMergeDecision,
        closeMergePanel,
      }}
    >
      {children}
    </GraphContext.Provider>
  );
}
