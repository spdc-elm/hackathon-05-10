import React, { createContext, useContext, useState, useCallback, useRef } from "react";
import type {
  GraphView,
  WikiNodeDetail,
  SearchMatch,
  MergeDecisionDetail,
  MergeDecisionFilter,
  MergeDecisionSummary,
  MergeExecutePayload,
  VaultPageDetail,
} from "../types/graph";
import {
  executeMergeDecision,
  fetchGraphView,
  fetchNodeDetail,
  fetchSearch,
  fetchMergeDecisionDetail,
  fetchMergeDecisions,
  fetchVaultPage,
  scanMergeDecisions,
} from "../api/client";

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
  mergeApplyLoadingIds: string[];
  mergeApplyAllLoading: boolean;
  setSelectedNodeName: (name: string | null) => void;
  setSearchQuery: (q: string) => void;
  loadGraph: () => void;
  setMergeDecisionFilter: (status: MergeDecisionFilter) => void;
  loadMergeDecisions: (status?: MergeDecisionFilter) => void;
  scanMerges: () => void;
  openMergeDecision: (decisionId: string) => void;
  applyMergeDecision: (decisionId: string) => Promise<void>;
  applyAllMergeDecisions: () => Promise<void>;
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
  const [mergeApplyLoadingIds, setMergeApplyLoadingIds] = useState<string[]>([]);
  const [mergeApplyAllLoading, setMergeApplyAllLoading] = useState(false);
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

  const runMergeExecution = useCallback(async (decisionId: string) => {
    const detail = await fetchMergeDecisionDetail(decisionId);
    const payload = await buildMergeExecutePayload(decisionId, detail);
    await executeMergeDecision(payload);
  }, []);

  const refreshMergeAfterApply = useCallback(async (decisionId?: string) => {
    const res = await fetchMergeDecisions(mergeDecisionFilter);
    setMergeDecisions(sortDecisions(res.decisions));
    if (decisionId && mergeDecisionDetail?.frontmatter.decision_id === decisionId) {
      const detail = await fetchMergeDecisionDetail(decisionId);
      setMergeDecisionDetail(detail);
    }
    await loadGraph();
  }, [loadGraph, mergeDecisionDetail?.frontmatter.decision_id, mergeDecisionFilter]);

  const applyMergeDecision = useCallback(async (decisionId: string) => {
    if (!decisionId) return;
    setMergeApplyLoadingIds((ids) => addUnique(ids, decisionId));
    setMergeDecisionError("");
    try {
      await runMergeExecution(decisionId);
      await refreshMergeAfterApply(decisionId);
    } catch (e) {
      setMergeDecisionError(errorMessage(e, "Failed to apply merge decision"));
    } finally {
      setMergeApplyLoadingIds((ids) => ids.filter((id) => id !== decisionId));
    }
  }, [refreshMergeAfterApply, runMergeExecution]);

  const applyAllMergeDecisions = useCallback(async () => {
    setMergePanelOpen(true);
    setMergeApplyAllLoading(true);
    setMergeDecisionError("");
    try {
      const res = await fetchMergeDecisions("candidate");
      const candidates = sortDecisions(res.decisions).filter((decision) => decision.status === "candidate");
      if (candidates.length === 0) {
        const refreshed = await fetchMergeDecisions(mergeDecisionFilter);
        setMergeDecisions(sortDecisions(refreshed.decisions));
        setMergeDecisionError("No candidate merge decisions to apply.");
        return;
      }

      const failures: string[] = [];
      for (const decision of candidates) {
        setMergeApplyLoadingIds((ids) => addUnique(ids, decision.decision_id));
        try {
          await runMergeExecution(decision.decision_id);
        } catch (e) {
          failures.push(`${decision.decision_id}: ${errorMessage(e, "failed")}`);
        } finally {
          setMergeApplyLoadingIds((ids) => ids.filter((id) => id !== decision.decision_id));
        }
      }

      await refreshMergeAfterApply(mergeDecisionDetail?.frontmatter.decision_id);
      if (failures.length > 0) {
        setMergeDecisionError(
          `Applied ${candidates.length - failures.length}/${candidates.length}. ${failures.slice(0, 3).join("; ")}`
        );
      }
    } catch (e) {
      setMergeDecisionError(errorMessage(e, "Failed to apply merge decisions"));
    } finally {
      setMergeApplyAllLoading(false);
    }
  }, [mergeDecisionDetail?.frontmatter.decision_id, mergeDecisionFilter, refreshMergeAfterApply, runMergeExecution]);

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
        mergeApplyLoadingIds,
        mergeApplyAllLoading,
        setSelectedNodeName,
        setSearchQuery,
        loadGraph,
        setMergeDecisionFilter,
        loadMergeDecisions,
        scanMerges,
        openMergeDecision,
        applyMergeDecision,
        applyAllMergeDecisions,
        closeMergePanel,
      }}
    >
      {children}
    </GraphContext.Provider>
  );
}

async function buildMergeExecutePayload(
  decisionId: string,
  detail: MergeDecisionDetail,
): Promise<MergeExecutePayload> {
  const affectedNodes = stringArray(detail.frontmatter.affected_nodes);
  if (affectedNodes.length === 0) {
    throw new Error("affected_nodes is required.");
  }

  const pages = await Promise.all(affectedNodes.map((path) => fetchVaultPage(path)));
  const resultName = stringValue(detail.frontmatter.result_name)
    || stringValue(pages[0]?.frontmatter.canonical_name)
    || stemFromPath(affectedNodes[0]);
  if (!resultName) {
    throw new Error("result_name is required.");
  }

  const aliases = orderedUnion(
    pages.flatMap((page) => stringArray(page.frontmatter.aliases))
      .filter((alias) => alias !== resultName)
  );
  const frontmatter: Record<string, unknown> = {
    category: pages.map((page) => stringValue(page.frontmatter.category)).find(Boolean) || "核心概念",
  };
  if (aliases.length > 0) {
    frontmatter.aliases = aliases;
  }

  return {
    decision_id: stringValue(detail.frontmatter.decision_id) || decisionId,
    affected_nodes: affectedNodes,
    result_name: resultName,
    frontmatter,
    body: buildMergedBody(resultName, pages),
  };
}

function buildMergedBody(resultName: string, pages: VaultPageDetail[]): string {
  const definition = firstDefinition(pages) || `${resultName}.`;
  const sourceSections = pages.map((page) => {
    const title = stringValue(page.frontmatter.canonical_name) || stemFromPath(page.path);
    const cleaned = stripLeadingH1(stripSections(page.content_md, ["关系", "原文证据"])).trim();
    return `### ${title}\n\n\`${page.path}\`\n\n${cleaned || definition}`;
  });
  const relationLines = orderedUnion(
    pages.flatMap((page) => sectionLines(page.content_md, "关系"))
      .map((line) => line.trim())
      .filter((line) => line.startsWith("- "))
  );
  const evidenceLines = orderedUnion(
    pages.flatMap((page) => sectionLines(page.content_md, "原文证据"))
      .map((line) => line.trim())
      .filter((line) => line.startsWith("> "))
  );

  const parts = [
    `# ${resultName}`,
    definition,
    "## 来源定义",
    sourceSections.join("\n\n"),
  ];
  if (relationLines.length > 0) {
    parts.push("## 关系", relationLines.join("\n"));
  }
  if (evidenceLines.length > 0) {
    parts.push("## 原文证据", evidenceLines.join("\n"));
  }
  return `${parts.join("\n\n").replace(/\n{3,}/g, "\n\n").trim()}\n`;
}

function firstDefinition(pages: VaultPageDetail[]): string {
  for (const page of pages) {
    const definitions = sourceDefinitions(page.frontmatter);
    if (definitions.length > 0) return definitions[0];
  }
  for (const page of pages) {
    const paragraph = firstMarkdownParagraph(stripLeadingH1(stripSections(page.content_md, ["关系", "原文证据"])));
    if (paragraph) return paragraph;
  }
  return "";
}

function sourceDefinitions(frontmatter: Record<string, unknown>): string[] {
  const sources = frontmatter.sources;
  if (!Array.isArray(sources)) return [];
  return sources
    .map((source) => isRecord(source) ? stringValue(source.definition) : "")
    .filter(Boolean);
}

function firstMarkdownParagraph(markdown: string): string {
  return markdown
    .split(/\n\s*\n/)
    .map((part) => part.trim())
    .find((part) => {
      if (!part) return false;
      return !part.startsWith("#")
        && !part.startsWith("- ")
        && !part.startsWith("> ")
        && !part.startsWith("|");
    }) || "";
}

function stripLeadingH1(markdown: string): string {
  const lines = markdown.split("\n");
  if (lines[0]?.startsWith("# ")) {
    return lines.slice(1).join("\n").trim();
  }
  return markdown;
}

function stripSections(markdown: string, headings: string[]): string {
  const skipHeadings = new Set(headings);
  const lines = markdown.split("\n");
  const kept: string[] = [];
  let skipping = false;
  for (const line of lines) {
    const heading = /^##\s+(.+?)\s*$/.exec(line);
    if (heading) {
      skipping = skipHeadings.has(heading[1]);
      if (skipping) continue;
    }
    if (!skipping) kept.push(line);
  }
  return kept.join("\n");
}

function sectionLines(markdown: string, heading: string): string[] {
  const lines = markdown.split("\n");
  const section: string[] = [];
  let inSection = false;
  for (const line of lines) {
    if (line.trim() === `## ${heading}`) {
      inSection = true;
      continue;
    }
    if (inSection && line.startsWith("## ")) break;
    if (inSection) section.push(line);
  }
  return section;
}

function stringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map((item) => stringValue(item)).filter(Boolean);
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function orderedUnion(items: string[]): string[] {
  return Array.from(new Set(items.map((item) => item.trim()).filter(Boolean)));
}

function addUnique(items: string[], item: string): string[] {
  return items.includes(item) ? items : [...items, item];
}

function stemFromPath(path: string): string {
  return (path.split("/").pop() ?? path).replace(/\.md$/i, "");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function errorMessage(value: unknown, fallback: string): string {
  return value instanceof Error ? value.message : fallback;
}
