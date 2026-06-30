// Referências aos elementos do DOM
export const statusEl = document.getElementById("status");
export const detailsEl = document.getElementById("nodeDetails");
export const summaryEl = document.getElementById("graphSummary");
export const advancedEl = document.getElementById("advancedStats");
export const egoInput = document.getElementById("egoId");
export const tipoSelect = document.getElementById("tipo");
export const loadBtn = document.getElementById("loadBtn");
const tooltipEl = document.getElementById("tooltip");

export function initCollapsibleSections() {
  const toggles = document.querySelectorAll(".section-toggle");
  for (const toggle of toggles) {
    toggle.addEventListener("click", () => {
      const section = toggle.closest(".panel-section");
      if (!section) return;

      const isCollapsed = section.classList.toggle("is-collapsed");
      toggle.setAttribute("aria-expanded", isCollapsed ? "false" : "true");
    });
  }
}

export function esc(value) {
  const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  return String(value ?? "").replace(/[&<>"']/g, (ch) => map[ch]);
}

export function setStatus(text) {
  statusEl.classList.remove("status-rich");
  statusEl.textContent = text;
}

export function setGraphStatus(_metadata) {
  setStatus("Carregado");
}

function fmtNum(value, digits = 2) {
  if (value === null || value === undefined) return "-";
  return Number(value).toFixed(digits);
}

function fmtPct(value, digits = 1) {
  if (value === null || value === undefined) return "-";
  return (Number(value) * 100).toFixed(digits) + "%";
}

export function renderGraphSummary(metadata, statsSource = null, graphMetadata = null) {
  const stats = metadata?.statistics?.current;
  const clusters = metadata?.clusters ?? [];
  const gm = graphMetadata ?? metadata;

  if (!stats) {
    summaryEl.textContent = "Estatísticas indisponíveis para este grafo.";
    return;
  }

  const perCluster = stats.per_cluster ?? [];
  const clusterColorMap = Object.fromEntries(clusters.map((c) => [c.name, c.color]));

  const clusterRows = perCluster
    .map(
      (c) => {
        const color = clusterColorMap[c.name] ?? "#888888";
        return `
        <tr>
          <td style="white-space:nowrap"><span class="cluster-swatch" style="display:inline-block;vertical-align:middle;margin-right:5px;background:${esc(color)}"></span>${esc(c.name)}</td>
          <td>${esc(c.node_count)}</td>
          <td>${fmtNum(c.internal_density, 3)}</td>
        </tr>`;
      }
    )
    .join("");

  const overall = stats.overall;
  const overallTitle = statsSource === "follows" ? "Visão geral do grafo de Follows" : "Visão geral";
  const overallHtml = overall
    ? `
      <div class="stat-row"><span class="k">Ego</span><span class="v">${esc(gm.ego_id ?? "-")}</span></div>
      <div class="stat-row"><span class="k">Nós</span><span class="v">${esc(overall.node_count)}</span></div>
      <div class="stat-row"><span class="k">Arestas</span><span class="v">${esc(gm.edge_count ?? "-")}</span></div>
      <div class="stat-row"><span class="k">Grau médio</span><span class="v">${fmtNum(overall.mean_degree)}</span></div>
      <div class="stat-row"><span class="k">Grau mediano</span><span class="v">${fmtNum(overall.median_degree)}</span></div>
      <div class="stat-row"><span class="k">Densidade</span><span class="v">${fmtNum(overall.density, 4)}</span></div>`
    : `<span class="v">Indisponível.</span>`;

  const statsTitle = statsSource === "follows"
    ? `Estatísticas do grafo de Follows`
    : `Estatísticas por cluster`;

  summaryEl.innerHTML = `
    ${summaryCollapsible(overallTitle, overallHtml)}
    ${summaryCollapsible(
      statsTitle,
      `<table class="cluster-table">
        <thead>
          <tr>
            <th>Cluster</th><th>Nós</th>
            <th>Densidade interna</th>
          </tr>
        </thead>
        <tbody>${clusterRows}</tbody>
      </table>`,
    )}
  `;
}

function summaryCollapsible(title, contentHtml, open = false) {
  return `
    <details class="summary-details"${open ? " open" : ""}>
      <summary class="summary-summary">${title}</summary>
      <div class="summary-details-content">${contentHtml}</div>
    </details>`;
}

export function clearGraphSummary() {
  summaryEl.textContent = "Carregue um grafo para ver as estatísticas.";
}

// Preenche o painel lateral com os dados do nó clicado
export function renderNodeDetails(data) {
  detailsEl.innerHTML = `
    <div class="stat-row"><span class="k">ID</span><span class="v">${esc(data.id)}</span></div>
    <div class="stat-row"><span class="k">Grau total</span><span class="v">${esc(data.degree)}</span></div>
    <div class="stat-row"><span class="k">Grau de entrada</span><span class="v">${esc(data.in_degree ?? "-")}</span></div>
    <div class="stat-row"><span class="k">Grau de saída</span><span class="v">${esc(data.out_degree ?? "-")}</span></div>
    <div class="stat-row"><span class="k">Clusters (${esc(data.cluster_count)})</span><span class="v">${esc(data.clusters?.join(", ") ?? "-")}</span></div>
  `;
}

export function clearNodeDetails() {
  detailsEl.textContent = "Clique em um nó para ver os detalhes.";
}

// Tooltip flutuante que segue o cursor sobre os nós
export function showTooltip(evt, nodeData) {
  tooltipEl.innerHTML = `<strong>${esc(nodeData.id)}</strong><br>grau: ${esc(nodeData.degree)} | clusters: ${esc(nodeData.cluster_count ?? 0)}`;
  moveTooltip(evt);
  tooltipEl.classList.add("show");
}

export function moveTooltip(evt) {
  tooltipEl.style.left = `${evt.originalEvent.clientX + 12}px`;
  tooltipEl.style.top = `${evt.originalEvent.clientY + 12}px`;
}

export function hideTooltip() {
  tooltipEl.classList.remove("show");
}

// ── Estatísticas avançadas ────────────────────────────────────────────────────

const ADV_ROWS = [
  { key: "clusters", label: "Clusters", hint: null },
  { key: "densidade_global", label: "Densidade global", hint: null },
  { key: "seguir_mesmo_cluster", label: "Probabilidade de seguir no mesmo cluster", hint: null },
  { key: "seguir_outro_cluster", label: "Probabilidade de seguir em outro cluster", hint: null },
  { key: "razao_seguimento", label: "Razão de seguimento", hint: null },
  { key: "embeddedness_medio", label: "Embeddedness médio", hint: "fração de vizinhos no mesmo cluster" },
  { key: "fracao_arestas_intra", label: "Fração intra-cluster", hint: "do total de arestas quantas estão dentro dos clusters" },
  { key: "media_permutacao", label: "Média permutação", hint: null },
  { key: "p_valor_aprox", label: "Prob. Valor Aproximado", hint: "probabilidade de conexões intra-cluster terem sido formadas por acaso" },
];

export function renderAdvancedStats(metadata) {
  const stats = metadata?.advanced_statistics;
  if (!stats) {
    advancedEl.textContent = "Estatísticas avançadas disponíveis apenas para o grafo de Follows.";
    return;
  }

  const rows = ADV_ROWS.map(({ key, label, hint }) => {
    const raw = stats[key];
    const value = raw === undefined || raw === null ? "-" : raw;
    const hintHtml = hint ? `<span class="adv-hint">${esc(hint)}</span>` : "";
    return `
      <div class="stat-row">
        <span class="k">${esc(label)}${hintHtml}</span>
        <span class="v">${esc(String(value))}</span>
      </div>`;
  }).join("");

  advancedEl.innerHTML = rows;
}

export function clearAdvancedStats() {
  advancedEl.textContent = "Carregue um grafo para ver as estatísticas avançadas.";
}
