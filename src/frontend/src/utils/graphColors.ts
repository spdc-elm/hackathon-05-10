const SOURCE_COLORS = [
  "#7ecb9a",
  "#6ab0d4",
  "#d4a06a",
  "#c47ed4",
  "#d47e7e",
  "#b7d46a",
  "#e08d6a",
  "#7e8bd4",
];

const RELATION_COLORS: Record<string, string> = {
  prerequisite: "#e8a838",
  contains: "#38b2e8",
  parallel: "#8ce838",
  applies_to: "#e838b2",
};

const SPECIAL_COLORS: Record<string, string> = {
  merged: "#ff4d5e",
};

export function resolveGraphColor(colorKey: string): string {
  if (SPECIAL_COLORS[colorKey]) return SPECIAL_COLORS[colorKey];
  if (RELATION_COLORS[colorKey]) return RELATION_COLORS[colorKey];
  if (!colorKey) return "#9da697";
  return SOURCE_COLORS[stableHash(colorKey) % SOURCE_COLORS.length];
}

function stableHash(value: string): number {
  let hash = 0;
  for (let i = 0; i < value.length; i += 1) {
    hash = (hash * 31 + value.charCodeAt(i)) >>> 0;
  }
  return hash;
}
