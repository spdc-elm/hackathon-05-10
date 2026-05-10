import { useGraphContext } from "../context/GraphContext";
import type { ViewMode } from "../types/graph";

type Props = {
  onBack: () => void;
};

export function GraphToolbar({ onBack }: Props) {
  const { searchQuery, setSearchQuery, viewMode, setViewMode, loadGraph, loading } = useGraphContext();

  function handleModeChange(mode: ViewMode) {
    setViewMode(mode);
    setTimeout(loadGraph, 0);
  }

  return (
    <header className="graph-toolbar">
      <div className="graph-toolbar-left">
        <button className="ghost-button" type="button" onClick={onBack}>
          &larr; Documents
        </button>
        <h2>Knowledge Graph</h2>
      </div>

      <div className="graph-toolbar-center">
        <div className="search-wrapper">
          <input
            type="text"
            className="search-input"
            placeholder="Search nodes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          {searchQuery && (
            <button className="search-clear" type="button" onClick={() => setSearchQuery("")}>
              &times;
            </button>
          )}
        </div>
      </div>

      <div className="graph-toolbar-right">
        <div className="mode-toggle">
          <button
            className={`mode-btn ${viewMode === "per_document" ? "active" : ""}`}
            type="button"
            onClick={() => handleModeChange("per_document")}
            disabled={loading}
          >
            Per Document
          </button>
          <button
            className={`mode-btn ${viewMode === "frequency_preview" ? "active" : ""}`}
            type="button"
            onClick={() => handleModeChange("frequency_preview")}
            disabled={loading}
          >
            Frequency
          </button>
        </div>
      </div>
    </header>
  );
}
