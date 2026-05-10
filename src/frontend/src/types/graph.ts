export type GraphViewNode = {
  id: string;
  label: string;
  category: string;
  document_id: string;
  chapter_id: string;
  source_count: number;
  source_documents: string[];
  size: number;
  color_key: string;
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
  mode: "per_document" | "frequency_preview";
  nodes: GraphViewNode[];
  edges: GraphViewEdge[];
  legend: GraphLegend;
};

export type SourceRef = {
  document_id: string;
  chapter_id: string;
  source_id: string;
  page_start: number | null;
  page_end: number | null;
  line_start: number | null;
  line_end: number | null;
  char_start: number | null;
  char_end: number | null;
  match_method: "exact" | "whitespace_normalized" | "punctuation_normalized" | "chapter_fallback";
};

export type KnowledgeNode = {
  id: string;
  name: string;
  aliases: string[];
  definition: string;
  category: string;
  textbook_id: string;
  chapter_id: string;
  page_start: number | null;
  evidence: string;
  confidence: number;
  source_ref: SourceRef | null;
};

export type KnowledgeEdge = {
  id: string;
  source: string;
  target: string;
  relation_type: "prerequisite" | "contains" | "parallel" | "applies_to";
  description: string;
  evidence: string;
  confidence: number;
  source_ref: SourceRef | null;
};

export type NodeDetailResponse = {
  node: KnowledgeNode;
  chapter: {
    document_id: string;
    chapter_id: string;
    title: string;
  };
};

export type EdgeDetailResponse = {
  edge: KnowledgeEdge;
  source_node: { id: string; name: string };
  target_node: { id: string; name: string };
};

export type SearchMatch = {
  node_id: string;
  name: string;
  match_field: string;
  score: number;
};

export type SearchResponse = {
  matches: SearchMatch[];
};

export type DocumentSummary = {
  document_id: string;
  filename: string;
  title: string;
  format: string;
  size_bytes: number;
  status: string;
  chapter_count: number;
  total_chars: number;
  graph_status: string;
};

export type ViewMode = "per_document" | "frequency_preview";
