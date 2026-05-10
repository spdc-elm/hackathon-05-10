import { useEffect } from "react";
import { useGraphContext } from "../context/GraphContext";
import type { MergeDecisionFilter, MergeDecisionSummary } from "../types/graph";
import { MarkdownViewer } from "./MarkdownViewer";

const FILTERS: MergeDecisionFilter[] = ["candidate", "applied", "failed", "all"];

export function MergeDecisionPanel() {
  const {
    mergePanelOpen,
    mergeDecisionFilter,
    mergeDecisions,
    mergeDecisionDetail,
    mergeDecisionLoading,
    mergeDecisionError,
    setMergeDecisionFilter,
    loadMergeDecisions,
    openMergeDecision,
    closeMergePanel,
    setSelectedNodeName,
  } = useGraphContext();

  useEffect(() => {
    if (mergePanelOpen && mergeDecisions.length === 0) {
      loadMergeDecisions(mergeDecisionFilter);
    }
  }, [mergePanelOpen]); // eslint-disable-line react-hooks/exhaustive-deps

  const frontmatter = mergeDecisionDetail?.frontmatter;
  const affectedNodes = frontmatter?.affected_nodes ?? [];

  return (
    <aside className={`merge-panel ${mergePanelOpen ? "open" : ""}`}>
      <div className="merge-panel-header">
        <div>
          <h3>Merge Decisions</h3>
          <span>{mergeDecisions.length} records</span>
        </div>
        <button className="detail-close" type="button" onClick={closeMergePanel}>
          &times;
        </button>
      </div>

      <div className="merge-filter-row">
        {FILTERS.map((filter) => (
          <button
            key={filter}
            className={`merge-filter ${mergeDecisionFilter === filter ? "active" : ""}`}
            type="button"
            onClick={() => setMergeDecisionFilter(filter)}
          >
            {filter}
          </button>
        ))}
      </div>

      {mergeDecisionError && <div className="merge-error">{mergeDecisionError}</div>}

      <div className="merge-panel-content">
        <div className="merge-list">
          {mergeDecisionLoading && mergeDecisions.length === 0 && (
            <div className="merge-empty">Loading...</div>
          )}
          {!mergeDecisionLoading && mergeDecisions.length === 0 && (
            <div className="merge-empty">No decisions</div>
          )}
          {mergeDecisions.map((decision) => (
            <DecisionRow
              key={decision.decision_id}
              decision={decision}
              selected={mergeDecisionDetail?.frontmatter.decision_id === decision.decision_id}
              onClick={() => openMergeDecision(decision.decision_id)}
            />
          ))}
        </div>

        <div className="merge-detail">
          {!mergeDecisionDetail && !mergeDecisionLoading && (
            <div className="merge-empty">Select a decision</div>
          )}
          {mergeDecisionLoading && mergeDecisionDetail && (
            <div className="merge-loading-line">Refreshing...</div>
          )}
          {mergeDecisionDetail && (
            <>
              <div className="merge-summary">
                <Meta label="id" value={frontmatter?.decision_id} />
                <Meta label="status" value={frontmatter?.status} />
                <Meta label="method" value={frontmatter?.method} />
                <Meta label="result" value={frontmatter?.result_node ?? frontmatter?.result_name} />
              </div>

              <div className="merge-jump-section">
                <span className="detail-label">Affected Nodes</span>
                <div className="merge-node-list">
                  {affectedNodes.length === 0 && <span className="detail-muted">none</span>}
                  {affectedNodes.map((node) => (
                    <button
                      key={node}
                      className="merge-node-link"
                      type="button"
                      onClick={() => setSelectedNodeName(nodeNameFromPath(node))}
                    >
                      {node}
                    </button>
                  ))}
                </div>
              </div>

              {(frontmatter?.result_node || frontmatter?.result_name) && (
                <div className="merge-jump-section">
                  <span className="detail-label">Result Node</span>
                  <button
                    className="merge-node-link"
                    type="button"
                    onClick={() => setSelectedNodeName(nodeNameFromPath(String(frontmatter.result_node ?? frontmatter.result_name)))}
                  >
                    {String(frontmatter.result_node ?? frontmatter.result_name)}
                  </button>
                </div>
              )}

              <div className="merge-markdown">
                <MarkdownViewer
                  content={mergeDecisionDetail.content_md}
                  onLinkClick={(target) => setSelectedNodeName(target)}
                />
              </div>
            </>
          )}
        </div>
      </div>
    </aside>
  );
}

function DecisionRow({
  decision,
  selected,
  onClick,
}: {
  decision: MergeDecisionSummary;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button className={`merge-row ${selected ? "selected" : ""}`} type="button" onClick={onClick}>
      <div className="merge-row-top">
        <span className={`merge-status status-${decision.status}`}>{decision.status}</span>
        <span className="merge-row-id">{decision.decision_id}</span>
      </div>
      <div className="merge-row-main">
        <strong>{decision.result_name}</strong>
        <span>{decision.method} · {decision.affected_nodes.length} affected</span>
      </div>
      {decision.reason_summary && <p>{decision.reason_summary}</p>}
      <time>{formatUpdatedAt(decision.updated_at)}</time>
    </button>
  );
}

function Meta({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="merge-meta-item">
      <span>{label}</span>
      <strong>{value == null || value === "" ? "-" : String(value)}</strong>
    </div>
  );
}

function nodeNameFromPath(value: string) {
  const last = value.split("/").pop() ?? value;
  const stem = last.replace(/\.md$/i, "");
  return value.includes("/") ? stem : stem.replace(/^concept_/, "");
}

function formatUpdatedAt(value: string) {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}
