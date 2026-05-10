import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import { UploadPage } from "./components/UploadPage";
import { GraphPage } from "./components/GraphPage";
import { GraphContextProvider } from "./context/GraphContext";
import "./styles.css";
import "./graph.css";

type View = "upload" | "graph";

function App() {
  const [view, setView] = useState<View>("upload");

  if (view === "graph") {
    return (
      <GraphContextProvider>
        <GraphPage onBack={() => setView("upload")} />
      </GraphContextProvider>
    );
  }

  return <UploadPage onViewGraph={() => setView("graph")} />;
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
