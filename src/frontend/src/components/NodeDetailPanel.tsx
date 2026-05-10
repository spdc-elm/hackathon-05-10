import { useGraphContext } from "../context/GraphContext";
import { MarkdownViewer } from "./MarkdownViewer";

export function NodeDetailPanel() {
  const { selectedNodeName, nodeDetail, nodeDetailLoading, setSelectedNodeName } = useGraphContext();

  return (
    <aside className={`detail-panel ${selectedNodeName ? "open" : ""}`}>
      <div className="detail-panel-header">
        <h3>{nodeDetail?.node.name ?? "Loading..."}</h3>
        <button className="detail-close" type="button" onClick={() => setSelectedNodeName(null)}>
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

          <div className="detail-section detail-markdown">
            <MarkdownViewer
              content={nodeDetail.content_md}
              onLinkClick={(target) => setSelectedNodeName(target)}
            />
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
