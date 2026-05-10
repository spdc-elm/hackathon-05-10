import { useGraphContext } from "../context/GraphContext";
import { DOCUMENT_COLORS, RELATION_COLORS } from "../mocks/graphViewMock";

export function GraphLegend() {
  const { graphView } = useGraphContext();

  if (!graphView) return null;

  return (
    <footer className="graph-legend">
      <div className="legend-group">
        <span className="legend-title">Documents</span>
        {graphView.legend.documents.map((doc) => (
          <span key={doc.document_id} className="legend-item">
            <span className="legend-dot" style={{ background: DOCUMENT_COLORS[doc.color_key] ?? "#9da697" }} />
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
