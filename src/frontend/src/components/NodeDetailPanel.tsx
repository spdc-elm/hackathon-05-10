import { useGraphContext } from "../context/GraphContext";
import { DOCUMENT_COLORS } from "../mocks/graphViewMock";

export function NodeDetailPanel() {
  const { selectedNodeId, nodeDetail, nodeDetailLoading, setSelectedNodeId } = useGraphContext();

  return (
    <aside className={`detail-panel ${selectedNodeId ? "open" : ""}`}>
      <div className="detail-panel-header">
        <h3>{nodeDetail?.node.name ?? "Loading..."}</h3>
        <button className="detail-close" type="button" onClick={() => setSelectedNodeId(null)}>
          &times;
        </button>
      </div>

      {nodeDetailLoading && (
        <div className="detail-loading">
          <div className="spinner" />
        </div>
      )}

      {nodeDetail && !nodeDetailLoading && (
        <div className="detail-body">
          <div className="detail-section">
            <span className="detail-label">Category</span>
            <span className="detail-badge">{nodeDetail.node.category}</span>
          </div>

          <div className="detail-section">
            <span className="detail-label">Definition</span>
            <p className="detail-text">{nodeDetail.node.definition}</p>
          </div>

          {nodeDetail.node.aliases.length > 0 && (
            <div className="detail-section">
              <span className="detail-label">Aliases</span>
              <div className="detail-aliases">
                {nodeDetail.node.aliases.map((a) => (
                  <span key={a} className="alias-tag">{a}</span>
                ))}
              </div>
            </div>
          )}

          <div className="detail-section">
            <span className="detail-label">Source</span>
            <div className="detail-source">
              <span
                className="source-dot"
                style={{ background: DOCUMENT_COLORS[nodeDetail.node.textbook_id] ?? "#9da697" }}
              />
              <span>{nodeDetail.chapter.title}</span>
              {nodeDetail.node.page_start && <span className="detail-muted"> p.{nodeDetail.node.page_start}</span>}
            </div>
          </div>

          <div className="detail-section">
            <span className="detail-label">Evidence</span>
            <blockquote className="detail-evidence">{nodeDetail.node.evidence}</blockquote>
          </div>

          <div className="detail-section">
            <span className="detail-label">Confidence</span>
            <div className="confidence-bar">
              <div className="confidence-fill" style={{ width: `${nodeDetail.node.confidence * 100}%` }} />
              <span className="confidence-value">{Math.round(nodeDetail.node.confidence * 100)}%</span>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
