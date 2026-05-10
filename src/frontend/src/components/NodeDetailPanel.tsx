import { useGraphContext } from "../context/GraphContext";
import { MarkdownViewer } from "./MarkdownViewer";

export function NodeDetailPanel() {
  const { selectedNodeName, nodeDetail, nodeDetailLoading, setSelectedNodeName, openMergeDecision } = useGraphContext();

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
          {/* Metadata strip */}
          <div className="detail-meta-strip">
            <span className="detail-badge">{nodeDetail.node.category}</span>
            {nodeDetail.node.textbook_id && (
              <span className="detail-meta-tag">{nodeDetail.node.textbook_id}</span>
            )}
            {nodeDetail.node.chapter_id && (
              <span className="detail-meta-tag">{nodeDetail.node.chapter_id}</span>
            )}
          </div>

          {nodeDetail.node.merge_decision && (
            <button
              className="detail-decision-link"
              type="button"
              onClick={() => openMergeDecision(nodeDetail.node.merge_decision!)}
            >
              Merge decision: {nodeDetail.node.merge_decision}
            </button>
          )}

          {nodeDetail.node.merged_from && nodeDetail.node.merged_from.length > 0 && (
            <div className="detail-aliases">
              {nodeDetail.node.merged_from.map((source) => (
                <span key={source} className="alias-tag">from {source}</span>
              ))}
            </div>
          )}

          {/* Aliases */}
          {nodeDetail.node.aliases.length > 0 && (
            <div className="detail-aliases">
              {nodeDetail.node.aliases.map((a) => (
                <span key={a} className="alias-tag">{a}</span>
              ))}
            </div>
          )}

          {/* Full markdown content */}
          <div className="detail-markdown-full">
            <MarkdownViewer
              content={nodeDetail.content_md}
              onLinkClick={(target) => setSelectedNodeName(target)}
            />
          </div>
        </div>
      )}
    </aside>
  );
}
