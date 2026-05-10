import { useEffect, useRef } from "react";
import cytoscape from "cytoscape";
import fcose from "cytoscape-fcose";
import { useGraphContext } from "../context/GraphContext";
import { DOCUMENT_COLORS, RELATION_COLORS } from "../mocks/graphViewMock";
import type { GraphView } from "../types/graph";

cytoscape.use(fcose);

function resolveColor(colorKey: string): string {
  return DOCUMENT_COLORS[colorKey] ?? RELATION_COLORS[colorKey] ?? "#9da697";
}

function buildElements(view: GraphView): cytoscape.ElementDefinition[] {
  const nodes: cytoscape.ElementDefinition[] = view.nodes.map((n) => ({
    group: "nodes",
    data: {
      id: n.id,
      label: n.label,
      size: n.size,
      color: resolveColor(n.color_key),
      sourceCount: n.source_count,
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
      color: resolveColor(e.color_key),
      relationType: e.relation_type,
    },
  }));

  return [...nodes, ...edges];
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
    selector: "edge.faded",
    style: {
      opacity: 0.1,
    } as unknown as cytoscape.Css.Edge,
  },
];

export function GraphCanvas() {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const { graphView, setSelectedNodeId, searchMatches, selectedNodeId } = useGraphContext();

  const setSelectedNodeIdRef = useRef(setSelectedNodeId);
  setSelectedNodeIdRef.current = setSelectedNodeId;

  useEffect(() => {
    if (!containerRef.current) return;

    const cy = cytoscape({
      container: containerRef.current,
      style: cytoscapeStyle,
      layout: { name: "grid" },
      elements: [],
      minZoom: 0.3,
      maxZoom: 4,
      wheelSensitivity: 0.3,
    });

    cy.on("tap", "node", (evt) => {
      setSelectedNodeIdRef.current(evt.target.id());
    });

    cy.on("tap", (evt) => {
      if (evt.target === cy) {
        setSelectedNodeIdRef.current(null);
      }
    });

    cyRef.current = cy;
    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || !graphView) return;

    const elements = buildElements(graphView);
    cy.elements().remove();
    cy.add(elements);
    cy.layout({
      name: "fcose",
      animate: true,
      animationDuration: 600,
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
      const matchIds = new Set(searchMatches.map((m) => m.node_id));
      cy.nodes().forEach((node) => {
        if (matchIds.has(node.id())) {
          node.addClass("highlighted");
        } else {
          node.addClass("faded");
        }
      });
      cy.edges().forEach((edge) => {
        const src = edge.source().id();
        const tgt = edge.target().id();
        if (!matchIds.has(src) && !matchIds.has(tgt)) {
          edge.addClass("faded");
        }
      });
    }
  }, [searchMatches]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    cy.nodes().unselect();
    if (selectedNodeId) {
      const node = cy.getElementById(selectedNodeId);
      if (node.length) {
        node.select();
        cy.animate({ center: { eles: node }, duration: 300 });
      }
    }
  }, [selectedNodeId]);

  return <div ref={containerRef} className="graph-canvas" />;
}
