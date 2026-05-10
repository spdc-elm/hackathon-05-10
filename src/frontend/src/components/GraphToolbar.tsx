import { useGraphContext } from "../context/GraphContext";

type Props = {
  onBack: () => void;
};

export function GraphToolbar({ onBack }: Props) {
  const { searchQuery, setSearchQuery, loadGraph, loading } = useGraphContext();

  return (
    <header className="graph-toolbar">
      <div className="graph-toolbar-left">
        <button className="ghost-button" type="button" onClick={onBack}>
          &larr; Upload
        </button>
        <h2>Knowledge Graph</h2>
      </div>

      <div className="graph-toolbar-center">
        <div className="search-wrapper">
          <input
            type="text"
            className="search-input"
            placeholder="Search concepts..."
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
        <button
          className="ghost-button"
          type="button"
          onClick={loadGraph}
          disabled={loading}
        >
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>
    </header>
  );
}
