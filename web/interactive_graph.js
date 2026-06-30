
import {
  egoInput,
  tipoSelect,
  loadBtn,
  setStatus,
  setGraphStatus,
  initCollapsibleSections,
  renderGraphSummary,
  clearGraphSummary,
  renderNodeDetails,
  clearNodeDetails,
  renderAdvancedStats,
  clearAdvancedStats,
  showTooltip,
  moveTooltip,
  hideTooltip,
} from "./graph_ui_utils.js";

// ── Cytoscape styles ──────────────────────────────────────────────────────────

const NODE_SIZE = 22;
const NODE_SELECTED_SIZE = 28;
const EDGE_WIDTH = 2.2;
const EDGE_ARROW_SCALE = 1.45;

const FIXED_NODE_COLOR = "#9fc4ff"; // azul padrão, pode trocar

const NODE_STYLE = {
  selector: "node",
  style: {
    "background-color": FIXED_NODE_COLOR,
    width: NODE_SIZE,
    height: NODE_SIZE,
    "border-width": 1,
    "border-color": "#2f3d35",
    label: "",
  },
};

const NODE_SELECTED_STYLE = {
  selector: "node:selected",
  style: {
    width: NODE_SELECTED_SIZE,
    height: NODE_SELECTED_SIZE,
    "border-width": 2,
    "border-color": "#d95d39",
  },
};

const buildEdgeStyle = (isDirected) => ({
  selector: "edge",
  style: {
    width: EDGE_WIDTH,
    "line-color": "data(color)",
    "curve-style": "bezier",
    "target-arrow-shape": isDirected ? "triangle" : "none",
    "target-arrow-color": "data(color)",
    "arrow-scale": isDirected ? EDGE_ARROW_SCALE : 1,
    opacity: 0.82,
  },
});

// ── Cytoscape instance ────────────────────────────────────────────────────────

let cy;

// Todos os egos carregados do índice
let allEgos = [];

function normalizeEgoIds(values) {
  const unique = new Set(
    (Array.isArray(values) ? values : [])
      .map((value) => String(value ?? "").trim())
      .filter(Boolean)
  );

  return [...unique].sort((left, right) => Number(left) - Number(right));
}

let egoAwesomplete;
function setEgoOptions(egoIds) {
  const currentValue = egoInput.value;
  if (!egoAwesomplete) {
    egoAwesomplete = new window.Awesomplete(egoInput, {
      minChars: 0,
      autoFirst: true,
      list: egoIds
    });
    egoInput.addEventListener("focus", function() {
      egoAwesomplete.evaluate();
      egoAwesomplete.open();
    });
  } else {
    egoAwesomplete.list = egoIds;
  }
  egoInput.disabled = !egoIds.length;
  egoInput.value = egoIds.includes(currentValue) ? currentValue : (egoIds[0] || "");
}

async function initEgoPicker() {
  try {
    const response = await fetch("../output/graphs/index.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`Indice de egos indisponivel (${response.status})`);

    const payload = await response.json();
    // Suporta formato novo { egos: [...] } e formato legado { ego_ids: [...] }
    if (Array.isArray(payload?.egos)) {
      allEgos = payload.egos.map((e) => ({
        id: String(e.id ?? "").trim(),
      })).filter((e) => e.id);
    } else {
      allEgos = normalizeEgoIds(payload?.ego_ids).map((id) => ({ id }));
    }
  } catch (_error) {
    allEgos = [];
  }

  setEgoOptions(allEgos.map(e => e.id));
}

function initPanelResizer() {
  const appEl = document.querySelector(".app");
  const sideEl = document.querySelector(".side");
  const splitterEl = document.getElementById("panelSplitter");
  if (!appEl || !sideEl || !splitterEl) return;

  const storageKey = "graph-side-width";
  const saved = Number(window.localStorage.getItem(storageKey));
  if (Number.isFinite(saved) && saved >= 240) {
    appEl.style.setProperty("--side-width", `${saved}px`);
  }

  let isDragging = false;
  let startX = 0;
  let startWidth = 0;

  const clampWidth = (candidateWidth) => {
    const appWidth = appEl.getBoundingClientRect().width;
    const minWidth = 260;
    const maxWidth = Math.max(320, Math.min(620, appWidth - 280));
    return Math.max(minWidth, Math.min(maxWidth, candidateWidth));
  };

  const onPointerMove = (evt) => {
    if (!isDragging) return;
    const deltaX = evt.clientX - startX;
    const nextWidth = clampWidth(startWidth - deltaX);
    appEl.style.setProperty("--side-width", `${nextWidth}px`);
  };

  const stopDragging = () => {
    if (!isDragging) return;
    isDragging = false;
    splitterEl.classList.remove("is-dragging");
    document.body.style.userSelect = "";
    const current = Math.round(sideEl.getBoundingClientRect().width);
    window.localStorage.setItem(storageKey, String(current));
  };

  splitterEl.addEventListener("pointerdown", (evt) => {
    if (window.matchMedia("(max-width: 980px)").matches) return;
    isDragging = true;
    startX = evt.clientX;
    startWidth = sideEl.getBoundingClientRect().width;
    splitterEl.classList.add("is-dragging");
    document.body.style.userSelect = "none";
    splitterEl.setPointerCapture(evt.pointerId);
  });

  splitterEl.addEventListener("pointermove", onPointerMove);
  splitterEl.addEventListener("pointerup", stopDragging);
  splitterEl.addEventListener("pointercancel", stopDragging);
}

function buildCy(elements, isDirected, viewport = null) {
  cy?.destroy();

  cy = cytoscape({
    container: document.getElementById("cy"),
    elements,
    style: [NODE_STYLE, NODE_SELECTED_STYLE, buildEdgeStyle(isDirected)],
    layout: { name: "preset", fit: false },
    wheelSensitivity: 0.2,
    minZoom: 0.04,
    maxZoom: 8,
  });

  if (viewport && Number.isFinite(viewport.zoom) && viewport.pan) {
    cy.zoom(viewport.zoom);
    cy.pan(viewport.pan);
  } else {
    cy.center();
  }

  cy.on("mouseover", "node", (evt) => showTooltip(evt, evt.target.data()));
  cy.on("mousemove", "node", (evt) => moveTooltip(evt));
  cy.on("mouseout",  "node", hideTooltip);
  cy.on("tap",       "node", (evt) => renderNodeDetails(evt.target.data()));
  cy.on("tap",       (evt)  => { if (evt.target === cy) clearNodeDetails(); });
}

// ── Graph loading ─────────────────────────────────────────────────────────────

async function loadGraph() {
  const egoId = egoInput.value.trim();
  const tipo = tipoSelect.value;
  if (!egoId) {
    setStatus("Nenhum ego exportado disponível.");
    clearGraphSummary();
    clearNodeDetails();
    return;
  }

  const path  = `../output/graphs/${egoId}/${egoId}_${tipo}_interactive.json`;
  const previousViewport = cy
    ? {
        zoom: cy.zoom(),
        pan: { ...cy.pan() },
      }
    : null;

  setStatus(`Carregando ${path}...`);

  try {
    const response = await fetch(path);
    if (!response.ok) throw new Error(`Arquivo não encontrado (${response.status})`);

    const { elements, metadata } = await response.json();

    let statsMetadata = metadata;
    let statsSource = null;
    if (tipo === "feats") {
      const edgesPath = `../output/graphs/${egoId}/${egoId}_edges_interactive.json`;
      try {
        const edgesResponse = await fetch(edgesPath);
        if (edgesResponse.ok) {
          const edgesData = await edgesResponse.json();
          statsMetadata = edgesData.metadata;
          statsSource = "follows";
        }
      } catch (_) {
        // fallback: usa metadados do próprio grafo de feats
      }
    }

    buildCy(elements, metadata.is_directed, previousViewport);
    setGraphStatus(metadata);
    renderGraphSummary(statsMetadata, statsSource, metadata);
    renderAdvancedStats(statsMetadata);
    clearNodeDetails();
  } catch (err) {
    setStatus(`Erro: ${err.message}`);
    cy?.destroy();
    cy = null;
    clearGraphSummary();
    clearAdvancedStats();
    clearNodeDetails();
  }
}

// ── Event listeners ───────────────────────────────────────────────────────────

initCollapsibleSections();
initPanelResizer();
loadBtn.addEventListener("click", loadGraph);
window.addEventListener("keydown", (evt) => { if (evt.key === "Enter") loadGraph(); });

await initEgoPicker();
loadGraph();
