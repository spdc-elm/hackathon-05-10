import { useEffect, useRef } from "react";
import cytoscape from "cytoscape";
import fcose from "cytoscape-fcose";
import { useGraphContext } from "../context/GraphContext";
import type { GraphView } from "../types/graph";
import { resolveGraphColor } from "../utils/graphColors";

cytoscape.use(fcose);

function buildElements(view: GraphView): cytoscape.ElementDefinition[] {
  const nodes: cytoscape.ElementDefinition[] = view.nodes.map((n) => ({
    group: "nodes",
    data: {
      id: n.id,
      name: n.name,
      label: n.label,
      size: n.size,
      color: resolveGraphColor(n.color_key),
      category: n.category,
    },
  }));

  const edges: cytoscape.ElementDefinition[] = view.edges.map((e) => ({
    group: "edges",
    data: {
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.label,
      color: resolveGraphColor(e.color_key),
    },
  }));

  return [...nodes, ...edges];
}

function graphSignature(view: GraphView): string {
  const nodes = view.nodes
    .map((n) => `${n.id}:${n.name}:${n.label}:${n.color_key}:${n.size}`)
    .join("|");
  const edges = view.edges
    .map((e) => `${e.id}:${e.source}>${e.target}:${e.relation_type}`)
    .join("|");
  return `${nodes}::${edges}`;
}

const cytoscapeStyle: cytoscape.StylesheetStyle[] = [
  {
    selector: "node",
    style: {
      "background-color": "data(color)",
      width: "data(size)",
      height: "data(size)",
      label: "data(label)",
      color: "#e9ece5",
      "font-size": "11px",
      "text-valign": "bottom",
      "text-margin-y": 4,
      "text-outline-color": "#0d0f0d",
      "text-outline-width": 2,
      "min-zoomed-font-size": 9,
      "border-width": 0,
      "border-color": "#c7d36f",
      "transition-property": "border-width, border-color, background-color",
      "transition-duration": 150,
    } as unknown as cytoscape.Css.Node,
  },
  {
    selector: "edge",
    style: {
      "line-color": "data(color)",
      "target-arrow-color": "data(color)",
      "target-arrow-shape": "triangle",
      "arrow-scale": 0.8,
      "curve-style": "bezier",
      width: 1.5,
      opacity: 0.7,
      "font-size": "9px",
      color: "#687264",
      "text-outline-color": "#0d0f0d",
      "text-outline-width": 1.5,
      "min-zoomed-font-size": 11,
    } as unknown as cytoscape.Css.Edge,
  },
  {
    selector: "node.highlighted",
    style: {
      "border-width": 3,
      "border-color": "#e0c16a",
    } as unknown as cytoscape.Css.Node,
  },
  {
    selector: "node:selected",
    style: {
      "border-width": 3,
      "border-color": "#c7d36f",
    } as unknown as cytoscape.Css.Node,
  },
  {
    selector: "edge:selected",
    style: {
      width: 3,
      opacity: 1,
    } as unknown as cytoscape.Css.Edge,
  },
  {
    selector: "node.faded",
    style: {
      opacity: 0.25,
    } as unknown as cytoscape.Css.Node,
  },
  {
    selector: "node.outside-focus",
    style: {
      opacity: 0.08,
    } as unknown as cytoscape.Css.Node,
  },
  {
    selector: "edge.faded",
    style: {
      opacity: 0.1,
    } as unknown as cytoscape.Css.Edge,
  },
  {
    selector: "edge.outside-focus",
    style: {
      opacity: 0,
      width: 0.1,
    } as unknown as cytoscape.Css.Edge,
  },
  {
    selector: "node.focused",
    style: {
      opacity: 1,
      "border-width": 4,
      "border-color": "#e0c16a",
    } as unknown as cytoscape.Css.Node,
  },
  {
    selector: "node.focus-neighbor",
    style: {
      opacity: 0.9,
      "border-width": 1.5,
      "border-color": "#9da697",
    } as unknown as cytoscape.Css.Node,
  },
  {
    selector: "edge.focus-edge",
    style: {
      width: 2.4,
      opacity: 0.95,
    } as unknown as cytoscape.Css.Edge,
  },
];

export function GraphCanvas() {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const graphSignatureRef = useRef<string | null>(null);
  const { graphView, setSelectedNodeName, searchMatches, selectedNodeName } = useGraphContext();

  const setSelectedRef = useRef(setSelectedNodeName);
  setSelectedRef.current = setSelectedNodeName;

  const graphViewRef = useRef(graphView);
  graphViewRef.current = graphView;

  useEffect(() => {
    if (!containerRef.current) return;

    const cy = cytoscape({
      container: containerRef.current,
      style: cytoscapeStyle,
      layout: { name: "grid" },
      elements: [],
      minZoom: 0.2,
      maxZoom: 5,
      wheelSensitivity: 1,
    });

    cy.on("tap", "node", (evt) => {
      const nodeId = evt.target.id();
      const view = graphViewRef.current;
      if (view) {
        const found = view.nodes.find((n) => n.id === nodeId);
        setSelectedRef.current(found?.name ?? nodeId);
      }
    });

    cy.on("tap", (evt) => {
      if (evt.target === cy) {
        setSelectedRef.current(null);
      }
    });

    cyRef.current = cy;
    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, []);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || !graphView) return;

    const signature = graphSignature(graphView);
    if (graphSignatureRef.current === signature) return;
    graphSignatureRef.current = signature;

    const elements = buildElements(graphView);
    cy.elements().remove();
    cy.add(elements);
    cy.layout({
      name: "fcose",
      animate: false,
      quality: "default",
      nodeSeparation: 80,
      idealEdgeLength: 120,
      nodeRepulsion: () => 6000,
      randomize: true,
    } as unknown as cytoscape.LayoutOptions).run();
  }, [graphView]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    cy.nodes().removeClass("highlighted faded");
    cy.edges().removeClass("faded");

    if (searchMatches.length > 0) {
      const matchNames = new Set(searchMatches.map((m) => m.name));
      cy.nodes().forEach((node) => {
        if (matchNames.has(node.data("name")) || matchNames.has(node.data("label"))) {
          node.addClass("highlighted");
        } else {
          node.addClass("faded");
        }
      });
      cy.edges().forEach((edge) => {
        const src = edge.source();
        const tgt = edge.target();
        if (
          !matchNames.has(src.data("name")) &&
          !matchNames.has(src.data("label")) &&
          !matchNames.has(tgt.data("name")) &&
          !matchNames.has(tgt.data("label"))
        ) {
          edge.addClass("faded");
        }
      });
    }
  }, [searchMatches]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || !graphView) return;

    cy.batch(() => {
      cy.nodes().unselect();
      cy.nodes().removeClass("focused focus-neighbor outside-focus");
      cy.edges().removeClass("focus-edge outside-focus");
    });

    if (selectedNodeName) {
      const found = graphView.nodes.find(
        (n) => n.name === selectedNodeName || n.label === selectedNodeName
      );
      if (found) {
        const node = cy.getElementById(found.id);
        if (node.length) {
          const connectedEdges = node.connectedEdges();
          const visibleNodeIds = new Set<string>([node.id()]);
          const visibleEdgeIds = new Set<string>();

          connectedEdges.forEach((edge) => {
            visibleEdgeIds.add(edge.id());
          });
          connectedEdges.connectedNodes().forEach((connectedNode) => {
            visibleNodeIds.add(connectedNode.id());
          });

          cy.batch(() => {
            cy.nodes().forEach((graphNode) => {
              if (graphNode.id() === node.id()) {
                graphNode.addClass("focused");
              } else if (visibleNodeIds.has(graphNode.id())) {
                graphNode.addClass("focus-neighbor");
              } else {
                graphNode.addClass("outside-focus");
              }
            });
            cy.edges().forEach((edge) => {
              if (visibleEdgeIds.has(edge.id())) {
                edge.addClass("focus-edge");
              } else {
                edge.addClass("outside-focus");
              }
            });
          });

          node.select();
        }
      }
    }
  }, [selectedNodeName, graphView]);

  return <div ref={containerRef} className="graph-canvas" />;
}
