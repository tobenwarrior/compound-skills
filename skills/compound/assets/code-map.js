const SVG_NS = "http://www.w3.org/2000/svg";
const API = Object.freeze({ projects: "/api/projects", map: "/api/map", status: "/api/status" });
const POLL_MS = 2000;
const MAX_FILES = 2000;
const MAX_GRAPH_NODES = 4000;
const MAX_RENDERED_EDGES = 8000;
const SVG_WIDTH = 1000;
let SVG_HEIGHT = 700;
const OVERVIEW_THRESHOLD = 350;
const MAX_NEIGHBORHOOD_NODES = 240;

const refs = {
  rootName: document.getElementById("root-name"),
  projectSelect: document.getElementById("project-select"),
  projectName: document.getElementById("project-name"),
  liveStatus: document.getElementById("live-status"),
  liveStatusText: document.getElementById("live-status-text"),
  refresh: document.getElementById("refresh-button"),
  notice: document.getElementById("notice-strip"),
  noticeMark: document.getElementById("notice-mark"),
  noticeTitle: document.getElementById("notice-title"),
  noticeDetail: document.getElementById("notice-detail"),
  noticeDismiss: document.getElementById("notice-dismiss"),
  sidebar: document.getElementById("sidebar"),
  sidebarButton: document.getElementById("sidebar-button"),
  sidebarClose: document.getElementById("sidebar-close"),
  inspector: document.getElementById("inspector"),
  inspectorButton: document.getElementById("inspector-button"),
  inspectorClose: document.getElementById("inspector-close"),
  fileSearch: document.getElementById("file-search"),
  fileCount: document.getElementById("file-count"),
  edgeCount: document.getElementById("edge-count"),
  treeState: document.getElementById("tree-state"),
  fileTree: document.getElementById("file-tree"),
  treeFooter: document.getElementById("tree-footer"),
  graphMode: document.getElementById("graph-mode"),
  graph: document.getElementById("graph"),
  graphWorld: document.getElementById("graph-world"),
  graphLoading: document.getElementById("graph-loading"),
  loadingDetail: document.getElementById("loading-detail"),
  graphEmpty: document.getElementById("graph-empty"),
  emptyDetail: document.getElementById("empty-detail"),
  graphError: document.getElementById("graph-error"),
  errorDetail: document.getElementById("error-detail"),
  retry: document.getElementById("retry-button"),
  graphTip: document.getElementById("graph-tip"),
  graphSummary: document.getElementById("graph-summary"),
  focusSummary: document.getElementById("focus-summary"),
  zoomOut: document.getElementById("zoom-out"),
  zoomReset: document.getElementById("zoom-reset"),
  zoomIn: document.getElementById("zoom-in"),
  overview: document.getElementById("overview-button"),
  coverageSummary: document.getElementById("coverage-summary"),
  coverageDetail: document.getElementById("coverage-detail"),
  inspectorTitle: document.getElementById("inspector-title"),
  inspectorEmpty: document.getElementById("inspector-empty"),
  fileDetail: document.getElementById("file-detail"),
  detailPath: document.getElementById("detail-path"),
  detailLanguage: document.getElementById("detail-language"),
  detailKind: document.getElementById("detail-kind"),
  detailSymbolCount: document.getElementById("detail-symbol-count"),
  detailImportCount: document.getElementById("detail-import-count"),
  detailImporterCount: document.getElementById("detail-importer-count"),
  symbolNote: document.getElementById("symbol-note"),
  symbolList: document.getElementById("symbol-list"),
  importList: document.getElementById("import-list"),
  importerList: document.getElementById("importer-list"),
};

const safeString = (value, fallback = "") => typeof value === "string" ? value : fallback;
const safeNumber = (value, fallback = 0) => {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
};
const text = (value, fallback = "—") => value === null || value === undefined || value === "" ? fallback : String(value);
const make = (tag, value) => {
  const node = document.createElement(tag);
  if (value !== undefined) node.textContent = String(value);
  return node;
};
const makeSvg = (tag, attributes = {}, value) => {
  const node = document.createElementNS(SVG_NS, tag);
  Object.entries(attributes).forEach(([key, attributeValue]) => node.setAttribute(key, String(attributeValue)));
  if (value !== undefined) node.textContent = String(value);
  return node;
};
const clamp = (value, minimum, maximum) => Math.max(minimum, Math.min(maximum, value));
const unique = values => [...new Set(values)];
const basename = path => {
  const parts = path.split("/");
  return parts[parts.length - 1] || path;
};
const directoryOf = path => {
  const slash = path.lastIndexOf("/");
  return slash < 0 ? "" : path.slice(0, slash);
};
const formatCount = value => Number(value).toLocaleString();
const urlParams = new URLSearchParams(window.location.search);

function normalizeModel(payload) {
  const source = payload && payload.model && typeof payload.model === "object" ? payload.model : payload;
  const raw = source && typeof source === "object" ? source : {};
  const rawCoverage = raw.coverage && typeof raw.coverage === "object" ? raw.coverage : {};
  const files = Array.isArray(raw.files) ? raw.files.map(file => {
    if (!file || typeof file.path !== "string" || !file.path) return null;
    const symbols = Array.isArray(file.symbols) ? file.symbols.map(symbol => {
      if (!symbol || typeof symbol.name !== "string") return null;
      const lineValue = safeNumber(symbol.line, NaN);
      return {
        name: symbol.name,
        kind: safeString(symbol.kind, "symbol"),
        line: Number.isFinite(lineValue) ? Math.max(0, Math.round(lineValue)) : null,
        signature: safeString(symbol.signature).slice(0, 128),
      };
    }).filter(Boolean) : [];
    const dependencies = Array.isArray(file.dependencies)
      ? unique(file.dependencies.filter(dependency => typeof dependency === "string" && dependency))
      : [];
    return { path: file.path, language: safeString(file.language, "unknown"), symbols, dependencies };
  }).filter(Boolean) : [];
  files.sort((left, right) => left.path.localeCompare(right.path));
  return {
    rootName: safeString(raw.root_name, "Code map"),
    generatedAt: safeString(raw.generated_at),
    head: safeString(raw.head),
    coverage: {
      inventory: Math.max(0, Math.round(safeNumber(rawCoverage.inventory, files.length))),
      indexed: Math.max(0, Math.round(safeNumber(rawCoverage.indexed, files.length))),
      truncated: Boolean(rawCoverage.truncated),
      skipped: Math.max(0, Math.round(safeNumber(rawCoverage.skipped))),
      excluded: Math.max(0, Math.round(safeNumber(rawCoverage.excluded))),
      excludedReasons: rawCoverage.excluded_reasons && typeof rawCoverage.excluded_reasons === "object" ? Object.entries(rawCoverage.excluded_reasons).map(([reason, count]) => Math.max(0, Math.round(safeNumber(count))) + " " + reason + (Number(count) === 1 ? "" : "s")) : [],
      notes: Array.isArray(rawCoverage.notes) ? rawCoverage.notes.filter(note => typeof note === "string") : [],
    },
    files,
    focus: Array.isArray(raw.focus) ? raw.focus.filter(path => typeof path === "string") : [],
  };
}

const state = {
  projects: [],
  projectId: urlParams.get("project") || "",
  projectName: "",
  query: urlParams.get("query") || "",
  model: null,
  revision: null,
  status: null,
  lastError: "",
  noticeDismissed: false,
  selectedPath: null,
  collapsedDirs: new Set(),
  fileLimits: new Map(),
  positions: new Map(),
  view: { x: 0, y: 0, scale: 1 },
  didFit: false,
  graphModeKey: "",
  graphData: { nodes: [], edges: [] },
  pollTimer: null,
  statusInFlight: false,
  mapInFlight: false,
  visible: document.visibilityState === "visible",
  drag: null,
  suppressClick: false,
  hoveredId: null,
  captions: [],
  visibleCaptions: [],
  labelFrame: null,
};

function modelFiles() {
  return state.model ? state.model.files.slice(0, MAX_FILES) : [];
}

function allFiles() {
  return state.model ? state.model.files : [];
}

function graphFiles() {
  const files = allFiles();
  if (files.length <= MAX_GRAPH_NODES) return files;
  const priority = [];
  const seen = new Set();
  const add = file => {
    if (file && !seen.has(file.path)) {
      seen.add(file.path);
      priority.push(file);
    }
  };
  if (state.selectedPath) {
    const lookup = new Map(files.map(file => [file.path, file]));
    const selected = lookup.get(state.selectedPath);
    add(selected);
    if (selected) selected.dependencies.forEach(path => add(lookup.get(path)));
    files.filter(file => file.dependencies.includes(state.selectedPath)).forEach(add);
  }
  files.filter(matchesQuery).slice(0, 160).forEach(add);
  if (state.model) state.model.focus.forEach(path => add(files.find(file => file.path === path)));
  files.forEach(add);
  return priority.slice(0, MAX_GRAPH_NODES);
}

function fileLookup() {
  return new Map(allFiles().map(file => [file.path, file]));
}

function reverseLookup(files) {
  const reverse = new Map(files.map(file => [file.path, []]));
  files.forEach(file => file.dependencies.forEach(dependency => {
    if (reverse.has(dependency)) reverse.get(dependency).push(file.path);
  }));
  reverse.forEach(paths => paths.sort());
  return reverse;
}

function edgeTotal(files) {
  return files.reduce((total, file) => total + file.dependencies.length, 0);
}

function updateUrl() {
  const params = new URLSearchParams();
  if (state.projectId) params.set("project", state.projectId);
  if (state.query) params.set("query", state.query);
  const query = params.toString();
  window.history.replaceState(null, "", window.location.pathname + (query ? "?" + query : ""));
}

async function fetchJson(url) {
  const response = await fetch(url, { headers: { Accept: "application/json" }, cache: "no-store" });
  const body = await response.text();
  if (!response.ok) throw new Error("HTTP " + response.status);
  if (!body) throw new Error("Empty response");
  try {
    return JSON.parse(body);
  } catch {
    throw new Error("The map service returned invalid JSON");
  }
}

function setLoading(message = "Connecting to the map service…") {
  refs.loadingDetail.textContent = message;
  refs.graphLoading.hidden = false;
  refs.graphEmpty.hidden = true;
  refs.graphError.hidden = true;
}

function setGraphError(message) {
  refs.errorDetail.textContent = message || "The local map service could not be reached.";
  refs.graphLoading.hidden = true;
  refs.graphEmpty.hidden = true;
  refs.graphError.hidden = false;
}

function setGraphEmpty(message) {
  refs.emptyDetail.textContent = message;
  refs.graphLoading.hidden = true;
  refs.graphError.hidden = true;
  refs.graphEmpty.hidden = false;
}

function renderProjects() {
  const fragment = document.createDocumentFragment();
  if (!state.projects.length) {
    const option = make("option", "No projects available");
    option.value = "";
    fragment.append(option);
  } else {
    state.projects.forEach(project => {
      const option = make("option", project.name);
      option.value = project.id;
      option.selected = project.id === state.projectId;
      fragment.append(option);
    });
  }
  refs.projectSelect.replaceChildren(fragment);
}

function renderStatus() {
  const status = state.status || {};
  const error = state.lastError || safeString(status.error);
  const indexing = Boolean(status.indexing);
  const stateName = error ? "error" : indexing ? "indexing" : state.model ? "live" : "loading";
  refs.liveStatus.dataset.state = stateName;
  let label = "Connecting…";
  if (error) label = "Map unavailable";
  else if (indexing) label = "Indexing…";
  else if (state.model && state.revision !== null) label = "Live · r" + state.revision;
  else if (state.model) label = "Map loaded";
  refs.liveStatusText.textContent = label;
}

function coverageIssues(model) {
  return model.coverage.notes.filter(note => !note.includes("import links are heuristic"));
}

function partialDetail(model) {
  const parts = [];
  if (model.coverage.truncated) parts.push("scan limit reached");
  if (model.coverage.skipped) parts.push(formatCount(model.coverage.skipped) + " source files skipped");
  const notes = coverageIssues(model);
  if (notes.length) parts.push(notes[0]);
  return parts.join(" · ");
}

function renderNotice() {
  const error = state.lastError;
  const model = state.model;
  const partial = model && (model.coverage.truncated || model.coverage.skipped > 0 || coverageIssues(model).length > 0);
  if (state.noticeDismissed && !error) {
    refs.notice.hidden = true;
    return;
  }
  if (error) {
    refs.notice.hidden = false;
    refs.notice.classList.add("error");
    refs.noticeMark.textContent = "!";
    refs.noticeTitle.textContent = "Live map update failed";
    refs.noticeDetail.textContent = error + " The last usable map remains visible.";
  } else if (partial) {
    refs.notice.hidden = false;
    refs.notice.classList.remove("error");
    refs.noticeMark.textContent = "i";
    refs.noticeTitle.textContent = "Incomplete index";
    refs.noticeDetail.textContent = partialDetail(model);
  } else {
    refs.notice.hidden = true;
  }
}

function renderHeader() {
  const model = state.model;
  const title = state.projectName || (model && model.rootName) || "Code map";
  refs.rootName.textContent = title;
  refs.projectName.textContent = title;
  const files = modelFiles();
  const total = model ? model.files.length : 0;
  refs.fileCount.textContent = total > files.length
    ? formatCount(files.length) + " / " + formatCount(total) + " files"
    : formatCount(files.length) + " files";
  refs.edgeCount.textContent = formatCount(edgeTotal(allFiles())) + " imports";
  refs.coverageSummary.textContent = formatCount(total) + " mapped" + (model && model.coverage.excluded ? " · " + formatCount(model.coverage.excluded) + " excluded" : "");
  refs.coverageDetail.textContent = model ? [formatCount(model.coverage.inventory) + " repository files considered.", ...model.coverage.excludedReasons, ...model.coverage.notes].join(" ") : "Waiting for the file index.";
  refs.treeFooter.textContent = total > MAX_FILES
    ? "Browse folders or search all " + formatCount(total) + " files"
    : "Recorded imports only · no source bodies";
}

function matchesQuery(file) {
  const terms = state.query.toLowerCase().split(/\s+/).filter(Boolean);
  if (!terms.length) return true;
  const haystack = [file.path, file.language, ...file.symbols.map(symbol => symbol.name + " " + symbol.signature)].join(" ").toLowerCase();
  return terms.every(term => haystack.includes(term));
}

function chooseFile(path, update = true) {
  if (!fileLookup().has(path)) return;
  state.selectedPath = path;
  state.collapsedDirs.delete(directoryOf(path));
  if (update) updateUrl();
  renderTree();
  renderGraph();
  renderInspector();
  focusSelection();
}

function createTreeFile(file) {
  const button = make("button");
  button.type = "button";
  button.className = "tree-file";
  button.setAttribute("role", "treeitem");
  button.setAttribute("aria-selected", String(file.path === state.selectedPath));
  button.title = file.path;
  const name = make("span", basename(file.path));
  name.className = "file-name";
  const language = make("span", file.language);
  language.className = "file-language";
  button.append(name, language);
  button.addEventListener("click", () => chooseFile(file.path));
  return button;
}

function renderTree() {
  const sourceFiles = allFiles();
  const allMatching = sourceFiles.filter(matchesQuery);
  const groups = new Map();
  allMatching.forEach(file => {
    const directory = directoryOf(file.path);
    if (!groups.has(directory)) groups.set(directory, []);
    groups.get(directory).push(file);
  });
  groups.forEach(group => group.sort((left, right) => left.path.localeCompare(right.path)));
  refs.treeState.textContent = state.model
    ? (state.query
      ? formatCount(allMatching.length) + " matching files"
      : formatCount(sourceFiles.length) + " indexed files")
    : "Loading file index…";
  if (!state.model || !allMatching.length) {
    const empty = make("div", state.model ? "No files match this search." : "No indexed files.");
    empty.className = "detail-empty";
    refs.fileTree.replaceChildren(empty);
    return;
  }
  const fragment = document.createDocumentFragment();
  let renderedFiles = 0;
  [...groups.keys()].sort((left, right) => left.localeCompare(right)).forEach(directory => {
    const group = make("div");
    group.className = "tree-group";
    const filesInDirectory = groups.get(directory);
    const open = Boolean(state.query) || !state.collapsedDirs.has(directory);
    const directoryButton = make("button");
    directoryButton.type = "button";
    directoryButton.className = "tree-dir";
    directoryButton.setAttribute("role", "treeitem");
    directoryButton.setAttribute("aria-expanded", String(open));
    const chevron = make("span", open ? "▾" : "▸");
    chevron.className = "chevron";
    const label = make("span", directory || "(root)");
    const count = make("span", filesInDirectory.length);
    count.className = "dir-count";
    directoryButton.append(chevron, label, count);
    directoryButton.addEventListener("click", () => {
      if (state.collapsedDirs.has(directory)) state.collapsedDirs.delete(directory);
      else state.collapsedDirs.add(directory);
      renderTree();
    });
    group.append(directoryButton);
    if (open) {
      const limit = Math.min(state.fileLimits.get(directory) || 50, MAX_FILES - renderedFiles);
      const shown = filesInDirectory.slice(0, limit);
      const selected = filesInDirectory.find(file => file.path === state.selectedPath);
      if (selected && !shown.includes(selected) && limit > 0) shown[shown.length - 1] = selected;
      shown.forEach(file => group.append(createTreeFile(file)));
      renderedFiles += shown.length;
      if (filesInDirectory.length > shown.length) {
        const more = make("button", renderedFiles < MAX_FILES ? "Show more · " + formatCount(filesInDirectory.length - shown.length) + " remaining" : "Search to find more files");
        more.type = "button";
        more.className = "tree-more";
        more.disabled = renderedFiles >= MAX_FILES;
        more.addEventListener("click", () => { state.fileLimits.set(directory, limit + 50); renderTree(); });
        group.append(more);
      }
    }
    fragment.append(group);
  });
  refs.fileTree.replaceChildren(fragment);
}

function selectedFileAndReverse() {
  const files = allFiles();
  const lookup = new Map(files.map(file => [file.path, file]));
  const reverse = reverseLookup(files);
  return { file: state.selectedPath ? lookup.get(state.selectedPath) : null, lookup, reverse };
}

function renderListEmpty(list, message) {
  const item = make("li", message);
  item.className = "detail-empty";
  list.replaceChildren(item);
}

function createEdgeItem(path, kind, lookup) {
  const item = make("li");
  item.className = "edge-item";
  const button = make("button");
  button.type = "button";
  button.disabled = !lookup.has(path);
  const kindLabel = make("span", kind);
  kindLabel.className = "edge-kind";
  button.append(kindLabel, document.createTextNode(path));
  if (lookup.has(path)) button.addEventListener("click", () => chooseFile(path));
  item.append(button);
  return item;
}

function renderInspector() {
  const selected = selectedFileAndReverse();
  const file = selected.file;
  const lookup = selected.lookup;
  const reverse = selected.reverse;
  if (!file) {
    refs.inspectorTitle.textContent = "No file selected";
    refs.inspectorEmpty.hidden = false;
    refs.fileDetail.hidden = true;
    return;
  }
  const importedBy = reverse.get(file.path) || [];
  refs.inspectorTitle.textContent = basename(file.path);
  refs.inspectorEmpty.hidden = true;
  refs.fileDetail.hidden = false;
  refs.detailPath.textContent = file.path;
  refs.detailLanguage.textContent = file.language;
  refs.detailKind.textContent = state.model && state.model.focus.includes(file.path) ? "focus file" : "indexed file";
  refs.detailSymbolCount.textContent = formatCount(file.symbols.length);
  refs.detailImportCount.textContent = formatCount(file.dependencies.length);
  refs.detailImporterCount.textContent = formatCount(importedBy.length);
  const hasOutline = ["python", "javascript", "typescript"].includes(file.language);
  refs.symbolNote.textContent = file.symbols.length ? "line hints" : hasOutline ? "" : "metadata only";
  if (!file.symbols.length) {
    renderListEmpty(refs.symbolList, hasOutline ? "No symbols recorded." : "Symbol and import analysis is unavailable for this language.");
  } else {
    const symbols = file.symbols.slice(0, 160).map(symbol => {
      const item = make("li");
      item.className = "symbol-item";
      const main = make("span", symbol.signature || symbol.name);
      main.className = "symbol-main";
      const metadata = make("span");
      metadata.className = "symbol-meta";
      metadata.append(make("span", symbol.kind), make("span", symbol.line === null ? "line unknown" : "line " + symbol.line));
      item.append(main, metadata);
      return item;
    });
    if (file.symbols.length > symbols.length) symbols.push(make("li", "+ " + (file.symbols.length - symbols.length) + " more symbols"));
    refs.symbolList.replaceChildren(...symbols);
  }
  if (file.dependencies.length) refs.importList.replaceChildren(...file.dependencies.map(path => createEdgeItem(path, "imports", lookup)));
  else renderListEmpty(refs.importList, "No imports recorded.");
  if (importedBy.length) refs.importerList.replaceChildren(...importedBy.map(path => createEdgeItem(path, "imported by", lookup)));
  else renderListEmpty(refs.importerList, "No importers recorded.");
}

function clusterDirectory(path) {
  const parts = path.split("/").filter(Boolean);
  if (parts.length <= 1) return "(root)";
  return parts.length > 2 ? parts.slice(0, 2).join("/") : parts[0];
}

function addNeighborhood(queue, name, lookup, reverse, names, seen) {
  if (!lookup.has(name) || seen.has(name) || names.length >= MAX_NEIGHBORHOOD_NODES) return;
  seen.add(name);
  names.push(name);
  const file = lookup.get(name);
  const neighbors = unique([...file.dependencies, ...(reverse.get(name) || [])]).sort();
  neighbors.forEach(neighbor => {
    if (!seen.has(neighbor) && names.length < MAX_NEIGHBORHOOD_NODES) queue.push(neighbor);
  });
}

function buildFileGraph(files, lookup, reverse) {
  const queryMatches = state.query ? files.filter(matchesQuery).map(file => file.path) : [];
  const large = files.length > OVERVIEW_THRESHOLD;
  const seeds = unique([
    state.selectedPath,
    ...queryMatches.slice(0, 40),
    ...(state.query || state.selectedPath ? [] : state.model ? state.model.focus : []),
  ].filter(path => lookup.has(path)));
  if (!seeds.length) return null;
  if (!large) {
    const names = files.map(file => file.path);
    if (state.selectedPath && names.includes(state.selectedPath)) {
      names.splice(names.indexOf(state.selectedPath), 1);
      names.unshift(state.selectedPath);
    }
    return { names, mode: state.query ? "repository-search" : "repository" };
  }
  const queue = [];
  const names = [];
  const seen = new Set();
  seeds.forEach(seed => addNeighborhood(queue, seed, lookup, reverse, names, seen));
  while (queue.length && names.length < MAX_NEIGHBORHOOD_NODES) addNeighborhood(queue, queue.shift(), lookup, reverse, names, seen);
  return { names, mode: state.query ? "search" : state.selectedPath ? "neighborhood" : "focus" };
}

function buildDirectoryGraph(files, lookup) {
  const directories = new Map();
  files.forEach(file => {
    const directory = clusterDirectory(file.path);
    if (!directories.has(directory)) directories.set(directory, []);
    directories.get(directory).push(file.path);
  });
  const edges = new Set();
  files.forEach(file => {
    const source = clusterDirectory(file.path);
    file.dependencies.forEach(dependency => {
      if (!lookup.has(dependency)) return;
      const target = clusterDirectory(dependency);
      if (source !== target) edges.add(source + "\u0000" + target);
    });
  });
  return {
    mode: "directories",
    nodes: [...directories.entries()].map(([path, members]) => ({
      id: "dir:" + path,
      path,
      kind: "directory",
      members: members.sort(),
      count: members.length,
    })),
    edges: [...edges].map(edge => {
      const parts = edge.split("\u0000");
      return { source: "dir:" + parts[0], target: "dir:" + parts[1] };
    }),
  };
}

function planPositions(data) {
  const planned = new Map();
  if (data.nodes.length <= 48 && data.mode !== "directories") {
    data.nodes.forEach((node, index) => {
      if (index === 0) planned.set(node.id, { x: SVG_WIDTH / 2, y: SVG_HEIGHT / 2 });
      else {
        const ring = Math.floor((index - 1) / 18);
        const ringIndex = (index - 1) % 18;
        const ringSize = Math.min(18, data.nodes.length - 1 - ring * 18);
        const angle = (ringIndex / Math.max(1, ringSize)) * Math.PI * 2 - Math.PI / 2 + ring * .28;
        planned.set(node.id, {
          x: SVG_WIDTH / 2 + Math.cos(angle) * (150 + ring * 120),
          y: SVG_HEIGHT / 2 + Math.sin(angle) * (105 + ring * 90),
        });
      }
    });
    return planned;
  }
  const clusters = new Map();
  data.nodes.forEach(node => {
    const cluster = node.kind === "directory" ? node.path : clusterDirectory(node.path);
    if (!clusters.has(cluster)) clusters.set(cluster, []);
    clusters.get(cluster).push(node);
  });
  const orderedClusters = [...clusters.keys()].sort();
  const selectedId = state.selectedPath ? "file:" + state.selectedPath : "";
  const selectedCluster = orderedClusters.find(cluster => clusters.get(cluster).some(node => node.id === selectedId));
  const ring = Math.min(310, 110 + orderedClusters.length * 18);
  orderedClusters.forEach((cluster, clusterIndex) => {
    const members = clusters.get(cluster).slice().sort((left, right) => left.id.localeCompare(right.id));
    const hasSelected = cluster === selectedCluster;
    const angle = (clusterIndex / Math.max(1, orderedClusters.length)) * Math.PI * 2 - Math.PI / 2;
    const center = hasSelected
      ? { x: SVG_WIDTH / 2, y: SVG_HEIGHT / 2 }
      : {
        x: SVG_WIDTH / 2 + Math.cos(angle) * ring,
        y: SVG_HEIGHT / 2 + Math.sin(angle) * ring * .72,
      };
    const spread = Math.max(40, Math.sqrt(members.length) * 22);
    members.forEach((node, memberIndex) => {
      if (node.id === selectedId) {
        planned.set(node.id, center);
        return;
      }
      const localAngle = memberIndex * 2.3999632297;
      const localRadius = members.length === 1 ? 0 : spread * Math.sqrt((memberIndex + 1) / members.length);
      planned.set(node.id, {
        x: center.x + Math.cos(localAngle) * localRadius,
        y: center.y + Math.sin(localAngle) * localRadius * .82,
      });
    });
  });
  return planned;
}

function ensurePosition(node, planned) {
  if (state.positions.has(node.id)) return state.positions.get(node.id);
  const position = planned.get(node.id) || { x: SVG_WIDTH / 2, y: SVG_HEIGHT / 2 };
  state.positions.set(node.id, position);
  return position;
}

function applyView() {
  refs.graphWorld.setAttribute("transform", "translate(" + state.view.x + " " + state.view.y + ") scale(" + state.view.scale + ")");
  scheduleLabels();
}

function scheduleLabels() {
  if (state.labelFrame !== null) return;
  state.labelFrame = window.requestAnimationFrame(() => {
    state.labelFrame = null;
    layoutLabels();
  });
}

function layoutLabels() {
  const matrix = refs.graphWorld.getScreenCTM();
  if (!matrix) return;
  const scale = Math.hypot(matrix.a, matrix.b);
  if (!scale) return;
  const stage = refs.graph.getBoundingClientRect();
  const padding = 7;
  const occupied = [];
  const obstacles = state.captions.filter(entry => entry.priority <= 2).map(entry => {
    const point = state.positions.get(entry.id);
    const x = matrix.a * point.x + matrix.c * point.y + matrix.e;
    const y = matrix.b * point.x + matrix.d * point.y + matrix.f;
    const radius = entry.radius * scale + 2;
    return { left: x - radius, right: x + radius, top: y - radius, bottom: y + radius };
  });
  const intersects = (rect, other, gap = 0) => rect.left < other.right + gap && rect.right + gap > other.left && rect.top < other.bottom + gap && rect.bottom + gap > other.top;
  state.visibleCaptions.forEach(entry => entry.caption.setAttribute("display", "none"));
  // Measure only a bounded set, in screen pixels so labels survive zooming.
  const rank = entry => entry.priority === 0 ? 0 : entry.id === state.hoveredId ? .5 : entry.priority;
  const candidates = state.captions.filter(entry => entry.priority < 4 || entry.id === state.hoveredId)
    .sort((left, right) => rank(left) - rank(right))
    .filter(entry => {
      const point = state.positions.get(entry.id);
      const x = matrix.a * point.x + matrix.c * point.y + matrix.e;
      const y = matrix.b * point.x + matrix.d * point.y + matrix.f;
      return x > stage.left && x < stage.right && y > stage.top && y < stage.bottom;
    }).slice(0, 64);
  candidates.forEach(entry => {
    entry.caption.removeAttribute("display");
    entry.caption.setAttribute("transform", "translate(0 " + (-entry.radius - 9 / scale) + ") scale(" + 1 / scale + ")");
  });
  state.visibleCaptions = candidates;
  const measured = candidates.map(entry => ({ entry, box: entry.caption.getBoundingClientRect() }));
  measured.forEach(({ entry, box }) => {
    const placements = [[0, 0], [box.width / 2 + entry.radius * scale + 8, box.height + 7], [-box.width / 2 - entry.radius * scale - 8, box.height + 7], [0, box.height + entry.radius * scale * 2 + 19]];
    if (entry.priority === 0 || entry.id === state.hoveredId) {
      placements.push([clamp(box.left, stage.left + padding, stage.right - box.width - padding) - box.left, clamp(box.top, stage.top + padding, stage.bottom - box.height - padding) - box.top]);
    }
    const placement = placements.find(([dx, dy], index) => {
      const rect = { left: box.left + dx, right: box.right + dx, top: box.top + dy, bottom: box.bottom + dy };
      if (rect.left < stage.left + padding || rect.right > stage.right - padding || rect.top < stage.top + padding || rect.bottom > stage.bottom - padding) return false;
      if (occupied.some(other => intersects(rect, other, padding))) return false;
      if (index < 4 && obstacles.some(other => intersects(rect, other))) return false;
      occupied.push(rect);
      return true;
    });
    if (placement) {
      entry.caption.setAttribute("transform", "translate(" + placement[0] / scale + " " + (-entry.radius + (placement[1] - 9) / scale) + ") scale(" + 1 / scale + ")");
    } else entry.caption.setAttribute("display", "none");
  });
}

function updateGraphPositions() {
  refs.graphWorld.querySelectorAll(".graph-node, .graph-caption-anchor").forEach(node => {
    const position = state.positions.get(node.getAttribute("data-node-id"));
    if (position) node.setAttribute("transform", "translate(" + position.x + " " + position.y + ")");
  });
  refs.graphWorld.querySelectorAll(".graph-edge").forEach(edge => {
    const source = state.positions.get(edge.getAttribute("data-source"));
    const target = state.positions.get(edge.getAttribute("data-target"));
    if (!source || !target) return;
    edge.setAttribute("x1", source.x);
    edge.setAttribute("y1", source.y);
    edge.setAttribute("x2", target.x);
    edge.setAttribute("y2", target.y);
  });
  scheduleLabels();
}

function graphPoint(event) {
  const matrix = refs.graph.getScreenCTM();
  if (!matrix) return { x: 0, y: 0 };
  const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse());
  return { x: point.x, y: point.y };
}

function worldPoint(event) {
  const point = graphPoint(event);
  return { x: (point.x - state.view.x) / state.view.scale, y: (point.y - state.view.y) / state.view.scale };
}

function syncGraphViewport() {
  const rect = refs.graph.getBoundingClientRect();
  const height = rect.width ? SVG_WIDTH * rect.height / rect.width : SVG_HEIGHT;
  if (Math.abs(height - SVG_HEIGHT) < 1) return false;
  SVG_HEIGHT = height;
  refs.graph.setAttribute("viewBox", "0 0 " + SVG_WIDTH + " " + SVG_HEIGHT);
  return true;
}

function focusSelection() {
  const point = state.positions.get("file:" + state.selectedPath);
  if (!point) return;
  state.view.x = SVG_WIDTH / 2 - point.x * state.view.scale;
  state.view.y = SVG_HEIGHT / 2 - point.y * state.view.scale;
  state.didFit = true;
  applyView();
}

function fitGraph() {
  const nodes = state.graphData.nodes;
  if (!nodes.length) return;
  const points = nodes.map(node => state.positions.get(node.id)).filter(Boolean);
  if (!points.length) return;
  const minX = Math.min(...points.map(point => point.x));
  const maxX = Math.max(...points.map(point => point.x));
  const minY = Math.min(...points.map(point => point.y));
  const maxY = Math.max(...points.map(point => point.y));
  const width = Math.max(180, maxX - minX + 150);
  const height = Math.max(150, maxY - minY + 130);
  state.view.scale = clamp(Math.min(SVG_WIDTH / width, SVG_HEIGHT / height), .35, 1.5);
  state.view.x = SVG_WIDTH / 2 - ((minX + maxX) / 2) * state.view.scale;
  state.view.y = SVG_HEIGHT / 2 - ((minY + maxY) / 2) * state.view.scale;
  state.didFit = true;
  applyView();
}

function setZoom(nextScale, event) {
  const scale = clamp(nextScale, .35, 2.5);
  if (event) {
    const screenPoint = graphPoint(event);
    const oldWorld = worldPoint(event);
    state.view.scale = scale;
    state.view.x = screenPoint.x - oldWorld.x * scale;
    state.view.y = screenPoint.y - oldWorld.y * scale;
  } else {
    const centerX = (SVG_WIDTH / 2 - state.view.x) / state.view.scale;
    const centerY = (SVG_HEIGHT / 2 - state.view.y) / state.view.scale;
    state.view.scale = scale;
    state.view.x = SVG_WIDTH / 2 - centerX * scale;
    state.view.y = SVG_HEIGHT / 2 - centerY * scale;
  }
  state.didFit = true;
  applyView();
}

function renderGraph() {
  syncGraphViewport();
  refs.graph.setAttribute("viewBox", "0 0 " + SVG_WIDTH + " " + SVG_HEIGHT);
  refs.graphWorld.replaceChildren();
  state.captions = [];
  state.visibleCaptions = [];
  state.hoveredId = null;
  refs.graphLoading.hidden = true;
  refs.graphError.hidden = true;
  refs.graphEmpty.hidden = true;
  refs.graphTip.hidden = true;
  const model = state.model;
  if (!model) {
    refs.graphMode.textContent = "Waiting for graph";
    refs.graphSummary.textContent = "0 nodes";
    refs.focusSummary.textContent = "Waiting for a map";
    if (state.lastError) setGraphError(state.lastError);
    else setLoading();
    return;
  }
  const sourceFiles = allFiles();
  const files = graphFiles();
  if (state.query && !sourceFiles.some(matchesQuery)) {
    refs.graphMode.textContent = "Search results";
    refs.graphSummary.textContent = "0 matching files";
    refs.focusSummary.textContent = "Try a file, folder, or symbol name";
    refs.overview.hidden = sourceFiles.length <= OVERVIEW_THRESHOLD;
    setGraphEmpty("No files match this search.");
    return;
  }
  if (!sourceFiles.length) {
    refs.graphMode.textContent = "Empty project";
    refs.graphSummary.textContent = "0 nodes";
    refs.focusSummary.textContent = "No indexed files";
    setGraphEmpty("The selected project has no indexed files yet.");
    return;
  }
  const lookup = new Map(files.map(file => [file.path, file]));
  const reverse = reverseLookup(files);
  const directoryMode = sourceFiles.length > OVERVIEW_THRESHOLD && !state.selectedPath && !state.query;
  let data;
  if (directoryMode) {
    const directoryLookup = new Map(sourceFiles.map(file => [file.path, file]));
    data = buildDirectoryGraph(sourceFiles, directoryLookup);
  }
  else {
    const fileGraph = buildFileGraph(files, lookup, reverse);
    if (!fileGraph) data = buildDirectoryGraph(files, lookup);
    else {
      const names = fileGraph.names;
      const nodes = names.map(path => ({ id: "file:" + path, path, kind: "file", file: lookup.get(path) }));
      const visible = new Set(names);
      const edges = [];
      const edgeKeys = new Set();
      names.forEach(path => {
        const file = lookup.get(path);
        file.dependencies.forEach(dependency => {
          if (!visible.has(dependency)) return;
          const key = path + "\u0000" + dependency;
          if (edgeKeys.has(key)) return;
          edgeKeys.add(key);
          edges.push({ source: "file:" + path, target: "file:" + dependency });
        });
      });
      data = { mode: fileGraph.mode, nodes, edges, capped: names.length < files.length };
    }
  }
  data.capped = Boolean(data.capped || data.nodes.length > MAX_GRAPH_NODES);
  if (data.nodes.length > MAX_GRAPH_NODES) {
    data.nodes = data.nodes.slice(0, MAX_GRAPH_NODES);
    const visible = new Set(data.nodes.map(node => node.id));
    data.edges = data.edges.filter(edge => visible.has(edge.source) && visible.has(edge.target));
  }
  state.graphData = data;
  const plannedPositions = planPositions(data);
  data.nodes.forEach(node => ensurePosition(node, plannedPositions));
  const degree = new Map(data.nodes.map(node => [node.id, 0]));
  data.edges.forEach(edge => {
    degree.set(edge.source, (degree.get(edge.source) || 0) + 1);
    degree.set(edge.target, (degree.get(edge.target) || 0) + 1);
  });
  const selectedId = state.selectedPath ? "file:" + state.selectedPath : "";
  const related = new Set();
  if (state.selectedPath && lookup.has(state.selectedPath)) {
    related.add(state.selectedPath);
    lookup.get(state.selectedPath).dependencies.forEach(path => related.add(path));
    (reverse.get(state.selectedPath) || []).forEach(path => related.add(path));
  }
  const hubs = new Set(data.nodes.slice().sort((left, right) => degree.get(right.id) - degree.get(left.id)).slice(0, 12).map(node => node.id));
  const highlightOpacity = Math.min(.8, 3 / Math.sqrt(Math.max(1, degree.get(selectedId) || 1)));
  const selectedEdges = data.edges.filter(edge => edge.source === selectedId || edge.target === selectedId);
  const otherEdges = data.edges.filter(edge => edge.source !== selectedId && edge.target !== selectedId);
  const renderedEdges = selectedEdges.concat(otherEdges.slice(0, Math.max(0, MAX_RENDERED_EDGES - selectedEdges.length))).slice(0, MAX_RENDERED_EDGES);
  renderedEdges.forEach(edge => {
    const line = makeSvg("line", {
      class: "graph-edge" + ((edge.source === selectedId || edge.target === selectedId) ? " highlight" : ""),
      "data-source": edge.source,
      "data-target": edge.target,
      "marker-end": "url(#edge-arrow)",
    });
    if (edge.source === selectedId || edge.target === selectedId) line.setAttribute("stroke-opacity", String(highlightOpacity));
    const source = state.positions.get(edge.source);
    const target = state.positions.get(edge.target);
    if (source && target) {
      line.setAttribute("x1", source.x);
      line.setAttribute("y1", source.y);
      line.setAttribute("x2", target.x);
      line.setAttribute("y2", target.y);
    }
    refs.graphWorld.append(line);
  });
  const nameCounts = new Map();
  data.nodes.forEach(node => nameCounts.set(basename(node.path), (nameCounts.get(basename(node.path)) || 0) + 1));
  data.nodes.forEach(node => {
    const position = state.positions.get(node.id);
    const selected = node.id === selectedId;
    const isRelated = node.kind === "file" && related.has(node.path);
    const group = makeSvg("g", {
      class: "graph-node" + (selected ? " selected" : "") + (isRelated && !selected ? " related" : ""),
      "data-node-id": node.id,
      tabindex: "0",
      role: "button",
      "aria-label": node.kind === "directory" ? node.path + " directory, " + node.count + " files" : node.path,
      transform: "translate(" + position.x + " " + position.y + ")",
    });
    const radius = node.kind === "directory"
      ? clamp(12 + Math.sqrt(node.count || 1) * 2, 14, 28)
      : selected ? 9 : clamp(3 + Math.sqrt(degree.get(node.id) || 0), 3, 8);
    group.append(makeSvg("circle", { r: radius }));
    group.append(makeSvg("title", {}, node.kind === "directory" ? node.path + " · " + node.count + " files" : node.path));
    const caption = makeSvg("g", { class: "node-caption", display: "none" });
    const name = node.kind === "directory" ? node.path : nameCounts.get(basename(node.path)) > 1 ? node.path.split("/").slice(-2).join("/") : basename(node.path);
    caption.append(makeSvg("text", { class: "node-label", "text-anchor": "middle" }, name.length > 44 ? name.slice(0, 41) + "…" : name));
    if (node.kind === "directory") caption.append(makeSvg("text", { class: "node-count", "text-anchor": "middle", y: "13" }, node.count + " files"));
    const priority = selected ? 0 : node.kind === "file" && state.query && matchesQuery(node.file) ? 1 : isRelated || node.kind === "directory" ? 2 : hubs.has(node.id) ? 3 : 4;
    state.captions.push({ id: node.id, caption, radius, priority });
    const reveal = () => { state.hoveredId = node.id; scheduleLabels(); };
    const conceal = () => { if (state.hoveredId === node.id) state.hoveredId = null; scheduleLabels(); };
    group.addEventListener("mouseenter", reveal);
    group.addEventListener("mouseleave", conceal);
    group.addEventListener("focus", reveal);
    group.addEventListener("blur", conceal);
    group.addEventListener("click", () => {
      if (state.suppressClick) return;
      chooseFile(node.kind === "directory" ? node.members[0] : node.path);
    });
    group.addEventListener("keydown", event => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      chooseFile(node.kind === "directory" ? node.members[0] : node.path);
    });
    group.addEventListener("pointerdown", event => beginNodeDrag(event, node.id, group));
    refs.graphWorld.append(group);
  });
  refs.overview.hidden = sourceFiles.length <= OVERVIEW_THRESHOLD || directoryMode;
  state.captions.forEach(entry => {
    const position = state.positions.get(entry.id);
    const anchor = makeSvg("g", { class: "graph-caption-anchor", "data-node-id": entry.id, transform: "translate(" + position.x + " " + position.y + ")" });
    anchor.append(entry.caption);
    refs.graphWorld.append(anchor);
  });
  const modeLabel = data.mode === "directories" ? "Directory overview" : data.mode === "search" ? "Search neighborhood" : data.mode === "neighborhood" ? "Selected neighborhood" : "Repository graph";
  const modeKey = data.mode + ":" + (state.selectedPath || "overview") + ":" + state.query.trim().toLowerCase();
  refs.graphMode.textContent = modeLabel;
  refs.graphSummary.textContent = directoryMode ? formatCount(data.nodes.length) + " folder groups · " + formatCount(sourceFiles.length) + " indexed files" : formatCount(data.nodes.length) + (data.capped ? " / " + formatCount(sourceFiles.length) : "") + " files · " + formatCount(data.edges.length) + " recorded imports" + (data.edges.length > renderedEdges.length ? " · " + formatCount(renderedEdges.length) + " drawn" : "");
  const focusText = model.focus.length
    ? "Focus: " + model.focus.slice(0, 3).join(" · ") + (model.focus.length > 3 ? " · …" : "")
    : "Recorded import metadata · no full call graph";
  refs.focusSummary.textContent = model.head ? focusText + " · " + model.head.slice(0, 12) : focusText;
  if (state.graphModeKey !== modeKey) {
    state.graphModeKey = modeKey;
    state.didFit = false;
  }
  if (!state.didFit) fitGraph();
  else applyView();
}

function beginNodeDrag(event, nodeId, group) {
  if (event.button !== 0) return;
  event.stopPropagation();
  const point = worldPoint(event);
  const position = state.positions.get(nodeId);
  if (!position) return;
  state.drag = {
    type: "node",
    nodeId,
    group,
    offsetX: point.x - position.x,
    offsetY: point.y - position.y,
    startX: event.clientX,
    startY: event.clientY,
    moved: false,
  };
  if (group.setPointerCapture) group.setPointerCapture(event.pointerId);
}

function beginPan(event) {
  if (event.button !== 0) return;
  state.drag = { type: "pan", startX: event.clientX, startY: event.clientY, viewX: state.view.x, viewY: state.view.y, moved: false };
  refs.graph.classList.add("is-panning");
  if (refs.graph.setPointerCapture) refs.graph.setPointerCapture(event.pointerId);
}

function finishPointer(event) {
  if (!state.drag) return;
  if (state.drag.moved) {
    state.suppressClick = true;
    window.setTimeout(() => { state.suppressClick = false; }, 0);
  }
  if (state.drag.type === "node" && state.drag.group.releasePointerCapture) {
    try { state.drag.group.releasePointerCapture(event.pointerId); } catch {}
  }
  state.drag = null;
  refs.graph.classList.remove("is-panning");
}

function handlePointerMove(event) {
  const drag = state.drag;
  if (!drag) return;
  const distance = Math.hypot(event.clientX - drag.startX, event.clientY - drag.startY);
  if (distance > 3) drag.moved = true;
  if (drag.type === "node") {
    const point = worldPoint(event);
    state.positions.set(drag.nodeId, { x: point.x - drag.offsetX, y: point.y - drag.offsetY });
    updateGraphPositions();
  } else {
    const point = graphPoint(event);
    const start = graphPoint({ clientX: drag.startX, clientY: drag.startY });
    const dx = point.x - start.x;
    const dy = point.y - start.y;
    state.view.x = drag.viewX + dx;
    state.view.y = drag.viewY + dy;
    applyView();
  }
  event.preventDefault();
}

function handleWheel(event) {
  event.preventDefault();
  setZoom(state.view.scale * (event.deltaY < 0 ? 1.12 : .89), event);
}

function renderAll() {
  renderHeader();
  renderProjects();
  renderStatus();
  renderNotice();
  renderTree();
  renderGraph();
  renderInspector();
}

async function loadMap(force = false) {
  if (!state.projectId || state.mapInFlight) return;
  state.mapInFlight = true;
  if (!state.model) setLoading("Loading the selected project map…");
  try {
    const payload = await fetchJson(API.map + "?project=" + encodeURIComponent(state.projectId));
    const nextModel = normalizeModel(payload);
    const previousModel = state.model;
    const previousSelection = state.selectedPath;
    state.model = nextModel;
    state.projectName = safeString(payload && payload.project && payload.project.name, state.projectName || nextModel.rootName);
    const currentProject = state.projects.find(project => project.id === state.projectId);
    if (currentProject) currentProject.name = state.projectName;
    const revision = safeNumber(payload && payload.revision, NaN);
    if (Number.isFinite(revision)) state.revision = Math.round(revision);
    if (!previousModel) state.didFit = false;
    const lookup = new Map(nextModel.files.map(file => [file.path, file]));
    const queryMatches = nextModel.files.filter(matchesQuery);
    if (state.query && queryMatches.length === 1) state.selectedPath = queryMatches[0].path;
    else if (previousSelection && lookup.has(previousSelection)) state.selectedPath = previousSelection;
    else state.selectedPath = !state.query && nextModel.files.length > OVERVIEW_THRESHOLD ? null : nextModel.focus.find(path => lookup.has(path)) || nextModel.files[0]?.path || null;
    if (!previousModel && nextModel.files.length > 120) {
      state.collapsedDirs = new Set(nextModel.files.map(file => directoryOf(file.path)));
      if (state.selectedPath) state.collapsedDirs.delete(directoryOf(state.selectedPath));
    }
    state.lastError = "";
    state.noticeDismissed = false;
    renderAll();
  } catch (error) {
    state.lastError = error instanceof Error ? error.message : "Map request failed";
    renderStatus();
    renderNotice();
    if (state.model) renderGraph();
    else setGraphError(state.lastError);
  } finally {
    state.mapInFlight = false;
  }
  return force;
}

function applyStatus(payload) {
  const status = payload && typeof payload === "object" ? payload : {};
  if (status.project && typeof status.project.name === "string") state.projectName = status.project.name;
  const revision = safeNumber(status.revision, NaN);
  state.status = { indexing: Boolean(status.indexing), error: safeString(status.error), updatedAt: safeString(status.updated_at) };
  if (Number.isFinite(revision)) state.status.revision = Math.round(revision);
  renderStatus();
  renderHeader();
}

async function pollStatus(force = false) {
  if (!state.visible || !state.projectId || state.statusInFlight) return;
  state.statusInFlight = true;
  try {
    const payload = await fetchJson(API.status + "?project=" + encodeURIComponent(state.projectId));
    applyStatus(payload);
    const revision = safeNumber(payload && payload.revision, NaN);
    const changed = Number.isFinite(revision) && (state.revision === null || Math.round(revision) !== state.revision);
    const statusError = safeString(payload && payload.error);
    if (statusError) {
      state.lastError = statusError;
      renderNotice();
      if (!state.model) setGraphError(statusError);
    } else if (!state.mapInFlight) {
      state.lastError = "";
      renderNotice();
    }
    if (!state.mapInFlight && (force || !state.model || changed)) await loadMap(force);
  } catch (error) {
    state.lastError = error instanceof Error ? error.message : "Status request failed";
    renderStatus();
    renderNotice();
    if (state.model) renderGraph();
    else setGraphError(state.lastError);
  } finally {
    state.statusInFlight = false;
  }
}

function stopPolling() {
  if (state.pollTimer !== null) {
    window.clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
}

function startPolling() {
  stopPolling();
  if (!state.projectId || !state.visible) return;
  state.pollTimer = window.setInterval(() => pollStatus(false), POLL_MS);
  pollStatus(false);
}

async function activateProject(projectId) {
  if (!projectId) return;
  state.projectId = projectId;
  const project = state.projects.find(candidate => candidate.id === projectId);
  state.projectName = project ? project.name : "";
  state.model = null;
  state.revision = null;
  state.status = null;
  state.lastError = "";
  state.selectedPath = null;
  state.positions.clear();
  state.collapsedDirs.clear();
  state.fileLimits.clear();
  state.view = { x: 0, y: 0, scale: 1 };
  state.didFit = false;
  state.graphModeKey = "";
  state.noticeDismissed = false;
  updateUrl();
  renderAll();
  setLoading("Loading the selected project map…");
  await loadMap(true);
  startPolling();
}

async function loadProjects() {
  try {
    const payload = await fetchJson(API.projects);
    const projects = Array.isArray(payload && payload.projects) ? payload.projects.map(project => {
      if (!project || typeof project.id !== "string" || !project.id) return null;
      return { id: project.id, name: safeString(project.name, project.id) };
    }).filter(Boolean) : [];
    state.projects = unique(projects.map(project => project.id)).map(id => projects.find(project => project.id === id));
    renderProjects();
    const fromUrl = state.projects.find(project => project.id === state.projectId);
    const target = fromUrl || state.projects[0];
    if (target) await activateProject(target.id);
    else {
      state.projectId = "";
      state.projectName = state.model ? state.model.rootName : "No projects available";
      renderAll();
      if (!state.model) setGraphEmpty("The map service has no projects to display.");
    }
  } catch (error) {
    state.lastError = error instanceof Error ? error.message : "Project request failed";
    renderAll();
    if (!state.model) setGraphError(state.lastError);
  }
}

function toggleDrawer(element, button, open) {
  element.classList.toggle("is-open", open);
  button.setAttribute("aria-expanded", String(open));
}

function installInteractions() {
  refs.projectSelect.addEventListener("change", event => activateProject(event.target.value));
  refs.refresh.addEventListener("click", async () => {
    state.lastError = "";
    if (!state.model) setLoading("Refreshing the selected project map…");
    await loadMap(true);
    await pollStatus(false);
  });
  refs.retry.addEventListener("click", async () => {
    state.lastError = "";
    setLoading("Retrying the map service…");
    await loadProjects();
  });
  refs.noticeDismiss.addEventListener("click", () => {
    state.noticeDismissed = true;
    renderNotice();
  });
  refs.fileSearch.value = state.query;
  refs.fileSearch.addEventListener("input", event => {
    state.query = event.target.value;
    const matching = allFiles().filter(matchesQuery);
    if (state.query && matching.length === 1) state.selectedPath = matching[0].path;
    else if (state.query && state.selectedPath && !matching.some(file => file.path === state.selectedPath)) state.selectedPath = null;
    updateUrl();
    renderTree();
    renderGraph();
    renderInspector();
    if (matching.length === 1) focusSelection();
  });
  document.addEventListener("keydown", event => {
    const active = document.activeElement;
    if (event.key === "/" && active !== refs.fileSearch && !["INPUT", "SELECT", "TEXTAREA"].includes(active.tagName)) {
      event.preventDefault();
      refs.fileSearch.focus();
    }
    if (event.key === "Escape") {
      toggleDrawer(refs.sidebar, refs.sidebarButton, false);
      toggleDrawer(refs.inspector, refs.inspectorButton, false);
    }
  });
  refs.sidebarButton.addEventListener("click", () => toggleDrawer(refs.sidebar, refs.sidebarButton, !refs.sidebar.classList.contains("is-open")));
  refs.sidebarClose.addEventListener("click", () => toggleDrawer(refs.sidebar, refs.sidebarButton, false));
  refs.inspectorButton.addEventListener("click", () => toggleDrawer(refs.inspector, refs.inspectorButton, !refs.inspector.classList.contains("is-open")));
  refs.inspectorClose.addEventListener("click", () => toggleDrawer(refs.inspector, refs.inspectorButton, false));
  refs.overview.addEventListener("click", () => {
    state.selectedPath = null;
    state.query = "";
    refs.fileSearch.value = "";
    state.didFit = false;
    updateUrl();
    renderAll();
  });
  refs.zoomIn.addEventListener("click", () => setZoom(state.view.scale * 1.2));
  refs.zoomOut.addEventListener("click", () => setZoom(state.view.scale * .83));
  refs.zoomReset.addEventListener("click", () => fitGraph());
  refs.graph.addEventListener("pointerdown", event => {
    if (event.target.closest && event.target.closest(".graph-node")) return;
    beginPan(event);
  });
  refs.graph.addEventListener("pointermove", handlePointerMove);
  refs.graph.addEventListener("pointerup", finishPointer);
  refs.graph.addEventListener("pointercancel", finishPointer);
  refs.graph.addEventListener("wheel", handleWheel, { passive: false });
  new ResizeObserver(() => { if (syncGraphViewport()) fitGraph(); else scheduleLabels(); }).observe(refs.graph);
  document.addEventListener("visibilitychange", () => {
    state.visible = document.visibilityState === "visible";
    if (state.visible) startPolling();
    else stopPolling();
  });
}

function boot() {
  refs.fileSearch.value = state.query;
  setLoading();
  renderAll();
  installInteractions();
  loadProjects();
}

boot();
