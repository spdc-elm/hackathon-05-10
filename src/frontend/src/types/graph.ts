export type GraphViewNode = {
  id: string;
  name: string;
  label: string;
  canonical_name?: string;
  category: string;
  document_id: string;
  chapter_id: string;
  source_count: number;
  source_documents: string[];
  size: number;
  color_key: string;
  merge_decision?: string | null;
};

export type GraphViewEdge = {
  id: string;
  source: string;
  target: string;
  relation_type: "prerequisite" | "contains" | "parallel" | "applies_to";
  label: string;
  color_key: string;
};

export type GraphLegend = {
  documents: Array<{
    document_id: string;
    title: string;
    color_key: string;
  }>;
  relations: Array<{
    relation_type: string;
    label: string;
    color_key: string;
  }>;
};

export type GraphView = {
  view_id: string;
  mode: string;
  nodes: GraphViewNode[];
  edges: GraphViewEdge[];
  legend: GraphLegend;
};

export type WikiNodeDetail = {
  node: {
    id: string;
    name: string;
    canonical_name?: string;
    aliases: string[];
    definition: string;
    category: string;
    textbook_id: string;
    chapter_id: string;
    evidence: string;
    merge_decision?: string | null;
    merged_from?: string[];
  };
  content_md: string;
};

export type MergeDecisionStatus = "candidate" | "applied" | "failed";

export type MergeDecisionFilter = MergeDecisionStatus | "all";

export type MergeDecisionSummary = {
  decision_id: string;
  status: MergeDecisionStatus | string;
  method: string;
  result_name: string;
  result_node?: string | null;
  affected_nodes: string[];
  reason_summary: string;
  updated_at: string;
};

export type MergeDecisionDetail = {
  path: string;
  frontmatter: {
    decision_id?: string;
    status?: MergeDecisionStatus | string;
    method?: string;
    result_name?: string;
    result_node?: string | null;
    affected_nodes?: string[];
    reason_summary?: string;
    updated_at?: string;
    [key: string]: unknown;
  };
  content_md: string;
  wikilinks: string[];
};

export type MergeExecutePayload = {
  decision_id: string;
  affected_nodes: string[];
  result_name: string;
  frontmatter: Record<string, unknown>;
  body: string;
};

export type SearchMatch = {
  name: string;
  match_field: string;
  score: number;
};

export type SearchResponse = {
  matches: SearchMatch[];
};

export type VaultPageSummary = {
  path: string;
  title: string;
  category: string;
};

export type VaultPageDetail = {
  path: string;
  frontmatter: Record<string, unknown>;
  content_md: string;
  wikilinks: string[];
};
