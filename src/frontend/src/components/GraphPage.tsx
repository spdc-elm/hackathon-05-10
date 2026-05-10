import { useEffect } from "react";
import { useGraphContext } from "../context/GraphContext";
import { GraphToolbar } from "./GraphToolbar";
import { GraphCanvas } from "./GraphCanvas";
import { NodeDetailPanel } from "./NodeDetailPanel";
import { GraphLegend } from "./GraphLegend";

type Props = {
  onBack: () => void;
};

export function GraphPage({ onBack }: Props) {
  const { loadGraph, loading, error } = useGraphContext();

  useEffect(() => {
    loadGraph();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="graph-page">
      <GraphToolbar onBack={onBack} />

      <div className="graph-canvas-wrapper">
        {loading && (
          <div className="graph-loading">
            <div className="spinner" />
            <p>Loading graph...</p>
          </div>
        )}
        {error && <div className="error graph-error">{error}</div>}
        <GraphCanvas />
        <NodeDetailPanel />
      </div>

      <GraphLegend />
    </div>
  );
}
