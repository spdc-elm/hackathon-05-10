import { useGraphContext } from "../context/GraphContext";

const RELATION_COLORS: Record<string, string> = {
  prerequisite: "#e8a838",
  contains: "#38b2e8",
  parallel: "#8ce838",
  applies_to: "#e838b2",
};

export function GraphLegend() {
  const { graphView } = useGraphContext();

  if (!graphView) return null;

  return (
    <footer className="graph-legend">
      <div className="legend-group">
        <span className="legend-title">Documents</span>
        {graphView.legend.documents.map((doc) => (
          <span key={doc.document_id} className="legend-item">
            <span className="legend-dot" style={{ background: "#7ecb9a" }} />
            {doc.title}
          </span>
        ))}
      </div>
      <div className="legend-group">
        <span className="legend-title">Relations</span>
        {graphView.legend.relations.map((rel) => (
          <span key={rel.relation_type} className="legend-item">
            <span className="legend-line" style={{ background: RELATION_COLORS[rel.color_key] ?? "#9da697" }} />
            {rel.label}
          </span>
        ))}
      </div>
    </footer>
  );
}
