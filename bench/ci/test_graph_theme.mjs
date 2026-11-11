import assert from "node:assert/strict";
import { createGraph } from "../../skills/compound/assets/map-graph.js";

const noop = () => {};

// What a browser resolves for the page's theme tokens and stage background in each color scheme.
const PAGE = {
  light: { "--text": "rgb(20, 22, 28)", "--dim": "rgb(107, 111, 120)", "--accent": "rgb(20, 122, 67)", background: "rgb(253, 248, 238)" },
  dark: { "--text": "rgb(236, 239, 244)", "--dim": "rgb(140, 148, 160)", "--accent": "rgb(88, 200, 140)", background: "rgb(12, 18, 30)" },
};
// The graph's own tokens, used when the host page gives it nothing to resolve.
const FALLBACK = { text: "#14161c", dim: "#6b6f78", accent: "#147a43", halo: "#fdf8ee", changed: "#d99a2b" };
const DATA = {
  nodes: [
    { id: "file", path: "file.py", group: "src", kind: "file", changed: true },
    { id: "other", path: "other.py", group: "src", kind: "file" },
  ],
  edges: [],
  selected: "file",
};

/** A canvas in a fake page. Reduced motion makes each draw show the settled scene. */
function makeHost({ scheme = "light", styled = true, background, visible = false } = {}) {
  const host = { scheme, labels: [], strokes: [], probes: [], observer: null, observed: null, disconnected: false, frameDone: null };
  const context = {
    globalAlpha: 1, lineWidth: 1, strokeStyle: "", fillStyle: "", font: "",
    measureText: text => ({ width: String(text).length * 6 }),
    setTransform: noop, save: noop, restore: noop, translate: noop, scale: noop, beginPath: noop, moveTo: noop,
    lineTo: noop, closePath: noop, fill: noop, arc: noop, fillRect: noop, strokeText: noop,
    clearRect() { host.labels.length = 0; host.strokes.length = 0; },
    fillText(value) { host.labels.push({ value, color: this.fillStyle, halo: this.strokeStyle, font: this.font }); },
    stroke() { host.strokes.push(this.strokeStyle); },
  };
  const stage = { appendChild: element => host.probes.push(element) };
  const documentElement = {};
  const ownerWindow = {
    devicePixelRatio: 1, addEventListener: noop, removeEventListener: noop,
    matchMedia: () => ({ matches: true, addEventListener: noop, removeEventListener: noop }),
    MutationObserver: class {
      constructor(callback) { host.observer = callback; }
      observe(target, options) { host.observed = { target, options }; }
      disconnect() { host.disconnected = true; }
    },
  };
  const canvas = {
    clientWidth: 500, clientHeight: 400, style: {}, parentElement: styled ? stage : null,
    ownerDocument: {
      visibilityState: visible ? "visible" : "hidden", documentElement, defaultView: ownerWindow,
      createElement: () => ({ style: {}, hidden: false, removed: false, remove() { this.removed = true; } }),
    },
    getContext: () => context, getBoundingClientRect: () => ({ left: 0, top: 0, width: 500, height: 400 }),
    addEventListener: noop, removeEventListener: noop, setAttribute: noop,
    getAttribute: () => null, removeAttribute: noop,
  };
  if (styled) {
    ownerWindow.getComputedStyle = element => {
      if (element === canvas) return { colorScheme: host.scheme, fontFamily: "Test Sans" };
      if (element === stage) return { backgroundColor: background ?? PAGE[host.scheme].background };
      const variable = /^var\((--[a-z]+),/.exec(element.style.color)[1];
      return { color: PAGE[host.scheme][variable] };
    };
  }
  if (visible) {
    ownerWindow.requestAnimationFrame = callback => setTimeout(() => { callback(Date.now()); host.frameDone?.(); }, 0);
    ownerWindow.cancelAnimationFrame = clearTimeout;
  }
  return Object.assign(host, { canvas, documentElement });
}

/** The colors one frame used: selected label, other label, their halo, and the ring strokes. */
function palette(host) {
  const [selected, other] = ["file.py", "other.py"].map(value => host.labels.find(label => label.value === value));
  assert.ok(selected && other, "both file names are drawn");
  assert.equal(selected.halo, other.halo);
  return { text: selected.color, dim: other.color, halo: selected.halo, font: selected.font, strokes: new Set(host.strokes) };
}

function drawOnce(options) {
  const host = makeHost(options);
  const graph = createGraph(host.canvas);
  graph.setData(DATA);
  const colors = palette(host);
  graph.destroy();
  return colors;
}

// Without a page to read, the graph draws with its own tokens.
const bare = drawOnce({ styled: false });
assert.deepEqual({ text: bare.text, dim: bare.dim, halo: bare.halo }, { text: FALLBACK.text, dim: FALLBACK.dim, halo: FALLBACK.halo });
assert.ok(bare.strokes.has(FALLBACK.accent) && bare.strokes.has(FALLBACK.changed));

// On a styled page the labels, halo, selection ring and font follow the page.
for (const scheme of ["light", "dark"]) {
  const themed = drawOnce({ scheme });
  assert.equal(themed.text, PAGE[scheme]["--text"]);
  assert.equal(themed.dim, PAGE[scheme]["--dim"]);
  assert.equal(themed.halo, PAGE[scheme].background);
  assert.ok(themed.strokes.has(PAGE[scheme]["--accent"]));
  assert.ok(themed.font.endsWith("Test Sans"));
  // The changed-file ring has one color per scheme.
  assert.ok(themed.strokes.has(scheme === "dark" ? "#f0c060" : FALLBACK.changed));
  assert.ok(!themed.strokes.has(scheme === "dark" ? FALLBACK.changed : "#f0c060"));
}

// A see-through stage has no color to put behind the text, so the halo keeps its own.
for (const background of ["transparent", "rgba(0, 0, 0, 0)"]) {
  assert.equal(drawOnce({ background }).halo, FALLBACK.halo);
}

// A theme switch on the page repaints with the new tokens on the next frame.
const host = makeHost({ scheme: "light", visible: true });
const graph = createGraph(host.canvas);
graph.setData(DATA);
assert.equal(palette(host).text, PAGE.light["--text"]);
assert.equal(host.observed.target, host.documentElement);
assert.equal(host.observed.options.attributes, true);
for (const attribute of ["class", "style"]) assert.ok(host.observed.options.attributeFilter.includes(attribute));
host.scheme = "dark";
const drawn = new Promise(resolve => { host.frameDone = resolve; });
host.observer();
await drawn;
const switched = palette(host);
assert.equal(switched.text, PAGE.dark["--text"]);
assert.equal(switched.halo, PAGE.dark.background);
assert.ok(switched.strokes.has(PAGE.dark["--accent"]) && !switched.strokes.has(PAGE.light["--accent"]));

// Destroying the graph stops watching the page and removes its measuring element.
assert.equal(host.probes.length, 1);
graph.destroy();
assert.equal(host.disconnected, true);
assert.equal(host.probes[0].removed, true);

console.log("graph theme checks passed");
