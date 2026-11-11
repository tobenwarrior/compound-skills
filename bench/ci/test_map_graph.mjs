import assert from "node:assert/strict";
import { createGraph, FOLDER_PALETTE, groupColor } from "../../skills/compound/assets/map-graph.js";

const noop = () => {};

const LABEL_HEIGHT = 11; // labels are drawn in an 11px face from their top edge

// A hidden canvas draws once per call instead of per animation frame. Reduced motion skips the
// fade-in and camera easing, so that single draw shows the settled scene.
function makeCanvas({ width = 900, height = 600, hidden = true } = {}) {
  const attributes = new Map();
  const strokes = [];
  const labels = []; // text drawn in the latest frame
  const context = {
    globalAlpha: 1,
    lineWidth: 1,
    strokeStyle: "",
    fillStyle: "",
    font: "",
    measureText: value => ({ width: String(value).length * 6 }),
    setTransform: noop,
    clearRect() {
      labels.length = 0;
    },
    save: noop,
    restore: noop,
    translate: noop,
    scale: noop,
    beginPath: noop,
    moveTo: noop,
    lineTo: noop,
    closePath: noop,
    fill: noop,
    arc: noop,
    fillRect: noop,
    strokeText: noop,
    fillText(value, x, y) {
      labels.push({
        value, x, y, width: this.measureText(value).width,
        color: this.fillStyle, halo: this.strokeStyle, alpha: this.globalAlpha, strong: this.font.startsWith("600 "),
      });
    },
    stroke() {
      strokes.push({ alpha: this.globalAlpha, style: this.strokeStyle, width: this.lineWidth });
    },
  };
  const ownerWindow = {
    devicePixelRatio: 1,
    addEventListener: noop,
    removeEventListener: noop,
    requestAnimationFrame: hidden ? undefined : callback => setTimeout(() => callback(Date.now()), 0),
    cancelAnimationFrame: hidden ? undefined : handle => clearTimeout(handle),
    matchMedia: () => ({ matches: hidden, addEventListener: noop, removeEventListener: noop }),
  };
  const canvas = {
    width,
    height,
    clientWidth: width,
    clientHeight: height,
    style: {},
    ownerDocument: { visibilityState: hidden ? "hidden" : "visible", defaultView: ownerWindow },
    getContext: () => context,
    getBoundingClientRect: () => ({ left: 0, top: 0, width, height }),
    addEventListener: noop,
    removeEventListener: noop,
    setAttribute: (name, value) => attributes.set(name, value),
    getAttribute: name => attributes.get(name) || null,
    removeAttribute: name => attributes.delete(name),
  };
  return { canvas, context, strokes, labels };
}

function strokeAlphas(strokes, style) {
  return strokes.filter(stroke => stroke.style === style).map(stroke => stroke.alpha);
}

function makeNodes(count) {
  return Array.from({ length: count }, (_, index) => ({
    id: `f${index}`,
    path: `src/${index % 20}/f${index}.js`,
    group: `src/${index % 20}`,
    kind: "file",
  }));
}

const small = makeCanvas();
small.canvas.setAttribute("aria-label", "Host label");
const graph = createGraph(small.canvas);
const twoNodes = makeNodes(2);
graph.setData({
  nodes: twoNodes,
  edges: [{ source: "f0", target: "f1" }],
  selected: "f1",
});
let stats = graph.getStats();
assert.equal(stats.nodes, 2);
assert.equal(stats.edges, 1);
assert.equal(stats.drawnEdges, 1);
assert.ok(stats.selectedPosition);
assert.equal(small.canvas.getAttribute("role"), "img");
assert.equal(small.canvas.getAttribute("aria-label"), "Dependency graph");
graph.setData({ nodes: twoNodes, edges: [{ source: "f0", target: "f1" }], selected: null });
assert.equal(graph.getStats().selectedPosition, null);
assert.equal(groupColor("src/1"), groupColor("src/1"));
assert.ok(FOLDER_PALETTE.length >= 2);
graph.destroy();
// Destroying the graph hands the canvas back as the host left it.
assert.equal(small.canvas.getAttribute("role"), null);
assert.equal(small.canvas.getAttribute("aria-label"), "Host label");

const sparse = makeCanvas({ width: 631, height: 400 });
const sparseGraph = createGraph(sparse.canvas);
const sparseNodes = Array.from({ length: 19 }, (_, index) => ({
  id: `sparse-${index}`,
  path: `folder-${index}/sparse-file-${index}.js`,
  group: `folder-${index}`,
  kind: "file",
}));
// Zoomed out to fit, file names fade away.
sparseGraph.setData({ nodes: sparseNodes, edges: [] });
let sparseStats = sparseGraph.getStats();
assert.ok(sparseStats.view.scale < 0.2);
assert.equal(sparseStats.visibleLabels, 0);
assert.deepEqual(sparse.labels, []);
// The selected file keeps its name at any zoom, in the strong text color over the halo.
sparseGraph.setData({ nodes: sparseNodes, edges: [], selected: "sparse-0" });
assert.equal(sparseGraph.getStats().visibleLabels, 1);
assert.deepEqual(
  sparse.labels.map(({ value, color, halo, alpha, strong }) => ({ value, color, halo, alpha, strong })),
  [{ value: "sparse-file-0.js", color: "#14161c", halo: "#fdf8ee", alpha: 1, strong: true }],
);
// Zooming in brings the other names back, inside the canvas and clear of each other.
sparseGraph.zoom(0.4 / sparseStats.view.scale);
sparseGraph.setData({ nodes: sparseNodes, edges: [], selected: "sparse-0" });
sparseStats = sparseGraph.getStats();
assert.ok(Math.abs(sparseStats.view.scale - 0.4) < 1e-9);
assert.ok(sparseStats.visibleLabels > 3);
assert.equal(sparse.labels.length, sparseStats.visibleLabels);
assert.equal(sparseStats.labelOverlaps, 0);
assert.ok(sparse.labels.some(label => !label.strong && label.color === "#6b6f78"));
assert.ok(sparse.labels.every(label => (
  label.x >= 0
  && label.y >= 0
  && label.x + label.width <= sparse.canvas.clientWidth
  && label.y + LABEL_HEIGHT <= sparse.canvas.clientHeight
)));
assert.ok(sparse.labels.every((label, index) => sparse.labels.slice(index + 1).every(other => (
  label.x + label.width <= other.x
  || other.x + other.width <= label.x
  || label.y + LABEL_HEIGHT <= other.y
  || other.y + LABEL_HEIGHT <= label.y
))));
sparseGraph.destroy();

const late = makeCanvas();
const lateGraph = createGraph(late.canvas);
const nodes = makeNodes(500);
const edges = [];
for (let source = 1; source < 500 && edges.length < 30000; source += 1) {
  for (let offset = 1; offset < 499 && edges.length < 30000; offset += 1) {
    const target = 1 + ((source - 1 + offset) % 499);
    edges.push({ source: `f${source}`, target: `f${target}` });
  }
}
edges.push({ source: "f0", target: "f1" });
lateGraph.setData({ nodes, edges, selected: "f0" });
stats = lateGraph.getStats();
assert.equal(stats.edges, edges.length);
assert.equal(stats.retainedEdges, edges.length);
assert.ok(stats.drawnEdges <= 20000);
// Links from the selected file use the accent color and stay clearly visible beside the base links.
// The selection rings share that color, so pick the links out by their hairline width.
const baseAlpha = Math.max(...strokeAlphas(late.strokes, "#6b6f78"));
assert.ok(baseAlpha > 0);
const linkWidth = late.strokes.find(stroke => stroke.style === "#6b6f78").width;
const selectedLinks = late.strokes.filter(stroke => stroke.style === "#147a43" && stroke.width === linkWidth);
assert.ok(selectedLinks.length > 0);
assert.ok(selectedLinks.every(stroke => stroke.alpha >= 0.12 && stroke.alpha > baseAlpha));

const activeBeforeQuery = stats.layoutActive;
late.strokes.length = 0;
lateGraph.setData({ nodes, edges, selected: null, query: "f0" });
stats = lateGraph.getStats();
assert.equal(stats.layoutActive, activeBeforeQuery);
// A search dims the base links without hiding them, and nothing is selected any more.
const queryAlpha = Math.max(...strokeAlphas(late.strokes, "#6b6f78"));
assert.ok(queryAlpha > 0 && queryAlpha < baseAlpha);
assert.deepEqual(strokeAlphas(late.strokes, "#147a43"), []);

const oversizedEdges = Array.from({ length: 250000 }, (_, index) => ({
  source: `f${1 + (index % 499)}`,
  target: `f${1 + ((index + 1 + Math.floor(index / 499)) % 499)}`,
}));
lateGraph.setData({ nodes, edges: oversizedEdges });
stats = lateGraph.getStats();
assert.equal(stats.edges, oversizedEdges.length);
assert.equal(stats.scannedEdges, 240000);
assert.equal(stats.scanTruncated, true);
assert.ok(stats.dedupeKeys <= stats.dedupeLimit);
assert.ok(stats.retainedEdges <= 120000);
lateGraph.destroy();

const trackingViews = [];
const tracking = makeCanvas({ hidden: false });
const trackingNodes = [
  { id: "a", path: "one/a.js", group: "one", kind: "file" },
  { id: "b", path: "two/b.js", group: "two", kind: "file" },
  { id: "c", path: "three/c.js", group: "three", kind: "file" },
  { id: "d", path: "four/d.js", group: "four", kind: "file" },
];
const trackingEdges = [
  { source: "a", target: "b" },
  { source: "b", target: "c" },
  { source: "c", target: "d" },
];
const trackingGraph = createGraph(tracking.canvas, {
  layoutBudget: 30,
  onStats: value => trackingViews.push({ ...value.view }),
});
trackingGraph.setData({ nodes: trackingNodes, edges: trackingEdges });
const trackingStart = trackingGraph.getStats();
assert.equal(trackingStart.fitTracking, true);
assert.equal(trackingStart.cameraInteracted, false);
await new Promise(resolve => setTimeout(resolve, 700));
const trackingSettled = trackingGraph.getStats();
assert.equal(trackingSettled.layoutActive, false);
assert.equal(trackingSettled.fitTracking, true);
assert.ok(trackingViews.some((view, index) => index > 0 && (
  Math.abs(view.x - trackingViews[0].x) > 0.01
  || Math.abs(view.y - trackingViews[0].y) > 0.01
  || Math.abs(view.scale - trackingViews[0].scale) > 0.0001
)));
trackingGraph.zoom(1.1);
const afterZoom = trackingGraph.getStats();
assert.equal(afterZoom.fitTracking, false);
assert.equal(afterZoom.cameraInteracted, true);
trackingGraph.fit();
trackingGraph.setData({ nodes: trackingNodes, edges: trackingEdges, selected: "c" });
assert.equal(trackingGraph.getStats().fitTracking, false);
trackingGraph.destroy();

console.log("map-graph regression checks passed");
