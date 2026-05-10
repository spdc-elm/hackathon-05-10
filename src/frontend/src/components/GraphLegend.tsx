import { useGraphContext } from "../context/GraphContext";
import { resolveGraphColor } from "../utils/graphColors";

export function GraphLegend() {
  const { graphView } = useGraphContext();

  if (!graphView) return null;

  const documentItems = graphView.legend.documents.filter((doc) => doc.color_key !== "merged");
  const hasMergedNodes = graphView.nodes.some((node) => node.color_key === "merged")
    || graphView.legend.documents.some((doc) => doc.color_key === "merged");

  return (
    <footer className="graph-legend">
      <div className="legend-group">
        <span className="legend-title">Documents</span>
        {documentItems.map((doc) => (
          <span key={doc.document_id} className="legend-item">
            <span className="legend-dot" style={{ background: resolveGraphColor(doc.color_key) }} />
            {doc.title}
          </span>
        ))}
      </div>
      {hasMergedNodes && (
        <div className="legend-group legend-group-merged">
          <span className="legend-title">Merge</span>
          <span className="legend-item">
            <span className="legend-dot legend-dot-merged" style={{ background: resolveGraphColor("merged") }} />
            Merged nodes
          </span>
        </div>
      )}
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
