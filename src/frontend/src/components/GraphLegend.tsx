import { useGraphContext } from "../context/GraphContext";
import { resolveGraphColor } from "../utils/graphColors";

export function GraphLegend() {
  const { graphView } = useGraphContext();

  if (!graphView) return null;

  return (
    <footer className="graph-legend">
      <div className="legend-group">
        <span className="legend-title">Documents</span>
        {graphView.legend.documents.map((doc) => (
          <span key={doc.document_id} className="legend-item">
            <span className="legend-dot" style={{ background: resolveGraphColor(doc.color_key) }} />
            {doc.title}
          </span>
        ))}
      </div>
      <div className="legend-group">
        <span className="legend-title">Relations</span>
        {graphView.legend.relations.map((rel) => (
          <span key={rel.relation_type} className="legend-item">
            <span className="legend-line" style={{ background: resolveGraphColor(rel.color_key) }} />
            {rel.label}
          </span>
        ))}
      </div>
    </footer>
  );
}
