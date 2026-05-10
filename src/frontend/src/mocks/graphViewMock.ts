import type { GraphView, NodeDetailResponse, SearchResponse } from "../types/graph";

export const DOCUMENT_COLORS: Record<string, string> = {
  doc_a: "#7ecb9a",
  doc_b: "#6ab0d4",
  doc_c: "#d4a06a",
  doc_d: "#c47ed4",
  doc_e: "#d47e7e",
};

export const RELATION_COLORS: Record<string, string> = {
  prerequisite: "#e0c16a",
  contains: "#9da697",
  parallel: "#6ab0d4",
  applies_to: "#c7d36f",
};

export const mockGraphView: GraphView = {
  view_id: "view_mock_001",
  mode: "per_document",
  nodes: [
    { id: "a_n01", label: "炎症反应", category: "核心概念", document_id: "doc_a", chapter_id: "ch_04", source_count: 3, source_documents: ["doc_a", "doc_b", "doc_c"], size: 28, color_key: "doc_a" },
    { id: "a_n02", label: "免疫应答", category: "核心概念", document_id: "doc_a", chapter_id: "ch_09", source_count: 2, source_documents: ["doc_a", "doc_b"], size: 24, color_key: "doc_a" },
    { id: "a_n03", label: "细胞凋亡", category: "核心概念", document_id: "doc_a", chapter_id: "ch_02", source_count: 2, source_documents: ["doc_a", "doc_c"], size: 22, color_key: "doc_a" },
    { id: "a_n04", label: "动作电位", category: "核心概念", document_id: "doc_a", chapter_id: "ch_02", source_count: 1, source_documents: ["doc_a"], size: 16, color_key: "doc_a" },
    { id: "a_n05", label: "静息电位", category: "核心概念", document_id: "doc_a", chapter_id: "ch_02", source_count: 1, source_documents: ["doc_a"], size: 14, color_key: "doc_a" },
    { id: "a_n06", label: "T细胞", category: "结构", document_id: "doc_a", chapter_id: "ch_09", source_count: 2, source_documents: ["doc_a", "doc_b"], size: 20, color_key: "doc_a" },
    { id: "a_n07", label: "抗体", category: "物质", document_id: "doc_a", chapter_id: "ch_09", source_count: 1, source_documents: ["doc_a"], size: 16, color_key: "doc_a" },
    { id: "a_n08", label: "体液免疫", category: "过程", document_id: "doc_a", chapter_id: "ch_09", source_count: 1, source_documents: ["doc_a"], size: 18, color_key: "doc_a" },
    { id: "b_n01", label: "白细胞", category: "结构", document_id: "doc_b", chapter_id: "ch_03", source_count: 2, source_documents: ["doc_a", "doc_b"], size: 20, color_key: "doc_b" },
    { id: "b_n02", label: "巨噬细胞", category: "结构", document_id: "doc_b", chapter_id: "ch_03", source_count: 1, source_documents: ["doc_b"], size: 16, color_key: "doc_b" },
    { id: "b_n03", label: "补体系统", category: "过程", document_id: "doc_b", chapter_id: "ch_05", source_count: 1, source_documents: ["doc_b"], size: 18, color_key: "doc_b" },
    { id: "b_n04", label: "细胞因子", category: "物质", document_id: "doc_b", chapter_id: "ch_05", source_count: 2, source_documents: ["doc_a", "doc_b"], size: 20, color_key: "doc_b" },
    { id: "b_n05", label: "有丝分裂", category: "过程", document_id: "doc_b", chapter_id: "ch_02", source_count: 1, source_documents: ["doc_b"], size: 16, color_key: "doc_b" },
    { id: "b_n06", label: "减数分裂", category: "过程", document_id: "doc_b", chapter_id: "ch_02", source_count: 1, source_documents: ["doc_b"], size: 16, color_key: "doc_b" },
    { id: "b_n07", label: "信号转导", category: "过程", document_id: "doc_b", chapter_id: "ch_06", source_count: 1, source_documents: ["doc_b"], size: 18, color_key: "doc_b" },
  ],
  edges: [
    { id: "e01", source: "a_n05", target: "a_n04", relation_type: "prerequisite", label: "前置依赖", color_key: "prerequisite" },
    { id: "e02", source: "a_n02", target: "a_n06", relation_type: "contains", label: "包含", color_key: "contains" },
    { id: "e03", source: "a_n02", target: "a_n08", relation_type: "contains", label: "包含", color_key: "contains" },
    { id: "e04", source: "a_n07", target: "a_n08", relation_type: "applies_to", label: "应用于", color_key: "applies_to" },
    { id: "e05", source: "a_n01", target: "a_n02", relation_type: "prerequisite", label: "前置依赖", color_key: "prerequisite" },
    { id: "e06", source: "a_n03", target: "a_n01", relation_type: "prerequisite", label: "前置依赖", color_key: "prerequisite" },
    { id: "e07", source: "b_n05", target: "b_n06", relation_type: "parallel", label: "并列", color_key: "parallel" },
    { id: "e08", source: "b_n01", target: "b_n02", relation_type: "contains", label: "包含", color_key: "contains" },
    { id: "e09", source: "a_n01", target: "b_n04", relation_type: "applies_to", label: "应用于", color_key: "applies_to" },
    { id: "e10", source: "b_n04", target: "b_n07", relation_type: "prerequisite", label: "前置依赖", color_key: "prerequisite" },
    { id: "e11", source: "a_n06", target: "b_n04", relation_type: "applies_to", label: "应用于", color_key: "applies_to" },
    { id: "e12", source: "b_n01", target: "a_n01", relation_type: "applies_to", label: "应用于", color_key: "applies_to" },
    { id: "e13", source: "b_n03", target: "a_n02", relation_type: "prerequisite", label: "前置依赖", color_key: "prerequisite" },
    { id: "e14", source: "a_n04", target: "b_n07", relation_type: "prerequisite", label: "前置依赖", color_key: "prerequisite" },
  ],
  legend: {
    documents: [
      { document_id: "doc_a", title: "生理学（第9版）", color_key: "doc_a" },
      { document_id: "doc_b", title: "病理学（第8版）", color_key: "doc_b" },
    ],
    relations: [
      { relation_type: "prerequisite", label: "前置依赖", color_key: "prerequisite" },
      { relation_type: "contains", label: "包含", color_key: "contains" },
      { relation_type: "parallel", label: "并列", color_key: "parallel" },
      { relation_type: "applies_to", label: "应用于", color_key: "applies_to" },
    ],
  },
};

export const mockNodeDetails: Record<string, NodeDetailResponse> = {
  a_n01: {
    node: {
      id: "a_n01",
      name: "炎症反应",
      aliases: ["炎症", "inflammatory response"],
      definition: "机体对致炎因子的损伤所发生的以防御为主的局部组织反应，表现为红、肿、热、痛和功能障碍。",
      category: "核心概念",
      textbook_id: "doc_a",
      chapter_id: "ch_04",
      page_start: 78,
      evidence: "炎症(inflammation)是具有血管系统的活体组织对各种损伤因子的刺激所发生的以防御反应为主的基本病理过程。",
      confidence: 0.95,
      source_ref: { document_id: "doc_a", chapter_id: "ch_04", source_id: "doc_a:ch_04:ev_001", page_start: 78, page_end: 78, line_start: null, line_end: null, char_start: 0, char_end: 52, match_method: "exact" },
    },
    chapter: { document_id: "doc_a", chapter_id: "ch_04", title: "第四章 炎症" },
  },
  a_n02: {
    node: {
      id: "a_n02",
      name: "免疫应答",
      aliases: ["immune response", "免疫反应"],
      definition: "机体免疫系统识别和排除抗原性异物的整个过程，包括固有免疫和适应性免疫。",
      category: "核心概念",
      textbook_id: "doc_a",
      chapter_id: "ch_09",
      page_start: 302,
      evidence: "免疫应答是机体免疫系统对抗原刺激所产生的以排除抗原为目的的生理过程。",
      confidence: 0.92,
      source_ref: { document_id: "doc_a", chapter_id: "ch_09", source_id: "doc_a:ch_09:ev_001", page_start: 302, page_end: 302, line_start: null, line_end: null, char_start: 120, char_end: 168, match_method: "exact" },
    },
    chapter: { document_id: "doc_a", chapter_id: "ch_09", title: "第九章 免疫" },
  },
  a_n04: {
    node: {
      id: "a_n04",
      name: "动作电位",
      aliases: ["action potential", "AP"],
      definition: "细胞受到刺激后，膜电位发生的一次快速而可逆的倒转，是可兴奋细胞兴奋的标志。",
      category: "核心概念",
      textbook_id: "doc_a",
      chapter_id: "ch_02",
      page_start: 35,
      evidence: "动作电位是细胞受到有效刺激时，细胞膜在静息电位基础上发生的一次快速、短暂、可逆的电位变化。",
      confidence: 0.97,
      source_ref: { document_id: "doc_a", chapter_id: "ch_02", source_id: "doc_a:ch_02:ev_003", page_start: 35, page_end: 35, line_start: null, line_end: null, char_start: 450, char_end: 510, match_method: "exact" },
    },
    chapter: { document_id: "doc_a", chapter_id: "ch_02", title: "第二章 细胞的基本功能" },
  },
};

export function getMockNodeDetail(nodeId: string): NodeDetailResponse | null {
  if (mockNodeDetails[nodeId]) return mockNodeDetails[nodeId];
  const node = mockGraphView.nodes.find((n) => n.id === nodeId);
  if (!node) return null;
  return {
    node: {
      id: node.id,
      name: node.label,
      aliases: [],
      definition: `${node.label}的定义信息（mock）`,
      category: node.category,
      textbook_id: node.document_id,
      chapter_id: node.chapter_id,
      page_start: null,
      evidence: `关于${node.label}的原文证据（mock）`,
      confidence: 0.85,
      source_ref: null,
    },
    chapter: { document_id: node.document_id, chapter_id: node.chapter_id, title: `章节 ${node.chapter_id}` },
  };
}

export function getMockSearch(query: string): SearchResponse {
  const q = query.toLowerCase();
  const matches = mockGraphView.nodes
    .filter((n) => n.label.toLowerCase().includes(q))
    .map((n) => ({ node_id: n.id, name: n.label, match_field: "name" as const, score: 1.0 }));
  return { matches };
}
