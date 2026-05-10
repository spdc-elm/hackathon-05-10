import React from "react";
import { createRoot } from "react-dom/client";
import { Workspace } from "./components/Workspace";
import { GraphContextProvider } from "./context/GraphContext";
import "./styles.css";
import "./graph.css";

function App() {
  return (
    <GraphContextProvider>
      <Workspace />
    </GraphContextProvider>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
