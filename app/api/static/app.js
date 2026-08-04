"use strict";
/**
 * Portal Vallenato — interfaz sobre la API existente (Sprint 4C: rediseño
 * SaaS/CRM).
 *
 * Sin build step, sin framework: fetch + DOM directo. Todo el estado vive
 * en memoria del navegador y se recarga desde la API en cada acción
 * relevante. Ningún cálculo de negocio vive aquí — vigente/vencido, cupo
 * bajo, estado comercial, ranking, todo llega ya calculado desde
 * AnalyticsService; este archivo solo formatea para pantalla.
 */

const CLIENT_TIPO_LABELS = {
  artista: "Artista",
  manager: "Manager",
  promotor: "Promotor",
  empresario: "Empresario",
};

const ESTADO_COMERCIAL_LABELS = {
  saludable: "Saludable",
  atencion: "Atención",
  renovacion: "Renovación",
  vencido: "Vencido",
};

const STALE_REQUEST_HOURS = 4; // solicitud recibida hace más de N horas, sin atender (solo visual)

let clientsById = new Map();
let pautasById = new Map();
let rankingByClientId = new Map();
let solicitudPautaFiltro = "";
let clientesFiltro = "";

// ---------- utilidades ----------

async function apiFetch(path, options) {
  const response = await fetch(path, options);
  if (response.status === 401) {
    showLogin();
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // el cuerpo no era JSON, se usa response.statusText
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (response.status === 204) return null;
  return response.json();
}

function showStatus(message, isError) {
  const el = document.getElementById("status");
  el.textContent = message;
  el.className = "status " + (isError ? "status-error" : "status-ok");
  el.hidden = false;
  window.clearTimeout(showStatus._timer);
  showStatus._timer = window.setTimeout(() => {
    el.hidden = true;
  }, 4000);
}

function formatFecha(iso) {
  return iso ? iso.slice(0, 10) : "";
}

function formatMoneda(valor) {
  return "$" + Number(valor).toLocaleString("es-CO", { maximumFractionDigits: 0 });
}

function horasEnEspera(fechaRecepcionIso) {
  return (Date.now() - new Date(fechaRecepcionIso).getTime()) / 3_600_000;
}

// ---------- autenticación ----------

function showLogin() {
  document.body.classList.add("login-active");
  document.getElementById("login-screen").hidden = false;
  document.getElementById("app-shell").hidden = true;
}

function showApp() {
  document.body.classList.remove("login-active");
  document.getElementById("login-screen").hidden = true;
  document.getElementById("app-shell").hidden = false;
}

function setupFormLogin() {
  document.getElementById("form-login").addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = {
      email: document.getElementById("login-email").value,
      password: document.getElementById("login-password").value,
    };
    try {
      await apiFetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      event.target.reset();
      showApp();
      await loadClientesYPautas();
      await loadSolicitudes();
      await loadDashboard();
    } catch (error) {
      showStatus(error.message, true);
    }
  });
}

function setupLogout() {
  document.getElementById("btn-logout").addEventListener("click", async () => {
    try {
      await apiFetch("/auth/logout", { method: "POST" });
    } catch {
      // aunque falle la llamada, igual mostramos el login localmente
    }
    showLogin();
  });
}

// ---------- navegación ----------

const TAB_TITLES = { dashboard: "Dashboard", solicitudes: "Solicitudes", clientes: "Clientes" };

function activateTab(name) {
  for (const btn of document.querySelectorAll(".nav-item[data-tab]")) {
    btn.classList.toggle("active", btn.dataset.tab === name);
  }
  for (const panel of document.querySelectorAll(".tab-panel")) {
    panel.classList.toggle("active", panel.id === "tab-" + name);
  }
  document.getElementById("topbar-title").textContent = TAB_TITLES[name] ?? "";
  closeSidebar();
}

function setupTabs() {
  for (const btn of document.querySelectorAll(".nav-item[data-tab]")) {
    btn.addEventListener("click", () => activateTab(btn.dataset.tab));
  }
  activateTab("dashboard"); // Dashboard es la pantalla de inicio (Sprint 4C)
}

function openSidebar() {
  document.getElementById("sidebar").classList.add("open");
  const overlay = document.getElementById("nav-overlay");
  overlay.hidden = false;
  requestAnimationFrame(() => overlay.classList.add("open"));
}

function closeSidebar() {
  document.getElementById("sidebar").classList.remove("open");
  const overlay = document.getElementById("nav-overlay");
  overlay.classList.remove("open");
  window.setTimeout(() => {
    overlay.hidden = true;
  }, 220);
}

function setupMobileNav() {
  document.getElementById("btn-menu").addEventListener("click", openSidebar);
  document.getElementById("nav-overlay").addEventListener("click", closeSidebar);
}

// ---------- drawers (formularios de baja frecuencia) ----------

function openDrawer(id) {
  const drawer = document.getElementById(id);
  const overlay = document.getElementById("drawer-overlay");
  drawer.hidden = false;
  overlay.hidden = false;
  requestAnimationFrame(() => {
    drawer.classList.add("open");
    overlay.style.opacity = "1";
  });
  drawer.setAttribute("aria-hidden", "false");
}

function closeDrawer(drawer) {
  if (!drawer) return;
  drawer.classList.remove("open");
  drawer.setAttribute("aria-hidden", "true");
  document.getElementById("drawer-overlay").style.opacity = "0";
  window.setTimeout(() => {
    drawer.hidden = true;
    document.getElementById("drawer-overlay").hidden = true;
  }, 220);
}

function closeAllDrawers() {
  for (const drawer of document.querySelectorAll(".drawer.open")) {
    closeDrawer(drawer);
  }
}

// Delegado en document: cubre tanto los botones que ya existen al cargar
// (abrir drawer, cerrar drawer) como los que se generan despues, por
// ejemplo el "+ Nueva pauta" de una ficha de cliente sin pauta.
function setupGlobalClicks() {
  document.addEventListener("click", (event) => {
    const openBtn = event.target.closest("[data-open-drawer]");
    if (openBtn) {
      openDrawer(openBtn.dataset.openDrawer);
      return;
    }
    const closeBtn = event.target.closest("[data-close-drawer]");
    if (closeBtn) {
      closeDrawer(closeBtn.closest(".drawer"));
      return;
    }
    const alertToggle = event.target.closest(".alert-card-toggle");
    if (alertToggle) {
      alertToggle.closest(".alert-card").classList.toggle("expanded");
      return;
    }
    if (event.target === document.getElementById("drawer-overlay")) {
      closeAllDrawers();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeAllDrawers();
  });
}

// ---------- carga de datos compartidos (clientes + pautas + ranking) ----------

async function loadClientesYPautas() {
  const [clientes, pautas, ranking] = await Promise.all([
    apiFetch("/clients"),
    apiFetch("/pautas"),
    apiFetch("/dashboard/ranking"),
  ]);
  clientsById = new Map(clientes.map((c) => [c.id, c]));
  pautasById = new Map(pautas.map((p) => [p.id, p]));
  rankingByClientId = new Map(ranking.map((item) => [item.cliente.id, item]));

  renderSelectClientes();
  renderSelectPautas();
  renderListaClientes();
}

function renderSelectClientes() {
  const select = document.getElementById("pauta-cliente");
  select.innerHTML = "";
  for (const client of clientsById.values()) {
    const option = document.createElement("option");
    option.value = client.id;
    option.textContent = `${client.nombre} (${CLIENT_TIPO_LABELS[client.tipo] ?? client.tipo})`;
    select.appendChild(option);
  }
}

function pautaOptionLabel(pauta) {
  const client = clientsById.get(pauta.client_id);
  const nombre = client ? client.nombre : "(cliente desconocido)";
  return (
    `${nombre} — ${formatFecha(pauta.fecha_inicio)} a ${formatFecha(pauta.fecha_fin)}` +
    ` — quedan ${pauta.publicaciones_restantes}/${pauta.publicaciones_contratadas}`
  );
}

function pautaOptionsHtml(pautas) {
  return pautas
    .map((pauta) => `<option value="${pauta.id}">${pautaOptionLabel(pauta)}</option>`)
    .join("");
}

// Una pauta vencida ya no sirve para nada nuevo — no tiene sentido
// ofrecerla para vincular una solicitud, ni la actual ni una futura.
function pautasVigentes() {
  return Array.from(pautasById.values()).filter((p) => p.vigente);
}

function pautasParaSolicitud() {
  const termino = solicitudPautaFiltro.trim().toLowerCase();
  const vigentes = pautasVigentes();
  if (!termino) return vigentes;
  return vigentes.filter((pauta) => pautaOptionLabel(pauta).toLowerCase().includes(termino));
}

function renderSelectPautas() {
  const select = document.getElementById("solicitud-pauta");
  const placeholder = select.querySelector('option[value=""]');
  select.innerHTML = "";
  select.appendChild(placeholder);
  select.insertAdjacentHTML("beforeend", pautaOptionsHtml(pautasParaSolicitud()));
}

// ---------- Clientes: fichas CRM ----------

function clientesFiltrados() {
  const termino = clientesFiltro.trim().toLowerCase();
  const todos = Array.from(clientsById.values());
  if (!termino) return todos;
  return todos.filter((c) => c.nombre.toLowerCase().includes(termino));
}

function renderClientCard(cliente) {
  const item = rankingByClientId.get(cliente.id);
  if (!item) {
    return `
      <div class="client-card">
        <div class="client-card-header">
          <h3>${cliente.nombre}</h3>
          <span class="badge badge-neutral">Sin pauta</span>
        </div>
        <p class="client-card-meta">
          <svg class="icon"><use href="#icon-phone"></use></svg>${cliente.telefono}
        </p>
        <div class="client-card-footer">
          <button type="button" class="btn-link" data-open-drawer="drawer-pauta">
            <svg class="icon"><use href="#icon-plus"></use></svg>Nueva pauta
          </button>
        </div>
      </div>`;
  }

  const pct =
    item.publicaciones_contratadas > 0
      ? Math.round((item.publicaciones_restantes / item.publicaciones_contratadas) * 100)
      : 0;

  return `
    <div class="client-card">
      <div class="client-card-header">
        <h3>${cliente.nombre}</h3>
        <span class="badge badge-${item.estado_comercial}">${ESTADO_COMERCIAL_LABELS[item.estado_comercial]}</span>
      </div>
      <p class="client-card-meta">
        <svg class="icon"><use href="#icon-clock"></use></svg>Hasta ${formatFecha(item.fecha_vencimiento)}
      </p>
      <div class="client-card-progress-track">
        <div class="client-card-progress-fill" style="width:${pct}%"></div>
      </div>
      <div class="client-card-stats">
        <div>
          <span class="client-card-stat-value">${item.publicaciones_restantes}/${item.publicaciones_contratadas}</span>
          <span class="client-card-stat-label">publicaciones</span>
        </div>
        <div>
          <span class="client-card-stat-value">${formatMoneda(item.peso_comercial)}</span>
          <span class="client-card-stat-label">peso comercial</span>
        </div>
      </div>
    </div>`;
}

function renderListaClientes() {
  const el = document.getElementById("lista-clientes");
  const clientes = clientesFiltrados();
  el.innerHTML = clientes.length
    ? clientes.map(renderClientCard).join("")
    : '<p class="muted">No se encontraron clientes.</p>';
}

// ---------- Solicitudes: kanban ----------

function renderKanbanCard(solicitud, esPublicada) {
  const pauta = solicitud.pauta_id ? pautasById.get(solicitud.pauta_id) : null;
  const client = pauta ? clientsById.get(pauta.client_id) : null;
  const nombreCliente = client ? client.nombre : "(sin vincular)";
  const esperandoMucho = !esPublicada && horasEnEspera(solicitud.fecha_recepcion) >= STALE_REQUEST_HOURS;
  const hora = solicitud.fecha_recepcion.slice(0, 16).replace("T", " ");

  let accionHtml = "";
  if (!esPublicada) {
    accionHtml = solicitud.pauta_id
      ? `<button type="button" class="btn btn-primary btn-publicar" data-id="${solicitud.id}">Publicar</button>`
      : `<select class="link-pauta-select" data-id="${solicitud.id}">
           <option value="">Elegir pauta…</option>
           ${pautaOptionsHtml(pautasVigentes())}
         </select>
         <button type="button" class="btn btn-secondary btn-vincular" data-id="${solicitud.id}">Vincular</button>`;
  }

  const claseExtra = esPublicada ? "is-publicada" : esperandoMucho ? "is-urgent" : "";

  return `
    <div class="kanban-card ${claseExtra}">
      <div class="kanban-card-header">
        <span class="kanban-card-cliente">${nombreCliente}${solicitud.prioridad_manual ? " ⚑" : ""}</span>
        <span class="kanban-card-time">${esperandoMucho ? "⏱ " : ""}${hora}</span>
      </div>
      <p class="kanban-card-texto">${solicitud.texto}</p>
      ${accionHtml ? `<div class="kanban-card-footer">${accionHtml}</div>` : ""}
    </div>`;
}

async function loadSolicitudes() {
  const [pendientes, publicadas] = await Promise.all([
    apiFetch("/publication-requests?estado=recibida"),
    apiFetch("/publication-requests?estado=publicada"),
  ]);
  // orden de llegada, con las de prioridad manual primero — regla del negocio
  pendientes.sort((a, b) => {
    if (a.prioridad_manual !== b.prioridad_manual) return a.prioridad_manual ? -1 : 1;
    return a.fecha_recepcion.localeCompare(b.fecha_recepcion);
  });
  publicadas.sort((a, b) => b.fecha_recepcion.localeCompare(a.fecha_recepcion));
  const publicadasRecientes = publicadas.slice(0, 30);

  document.getElementById("kanban-count-pendientes").textContent = pendientes.length;
  document.getElementById("kanban-count-publicadas").textContent = publicadas.length;

  const pendEl = document.getElementById("kanban-pendientes");
  pendEl.innerHTML = pendientes.length
    ? pendientes.map((s) => renderKanbanCard(s, false)).join("")
    : '<div class="kanban-empty">No hay solicitudes pendientes.</div>';

  const pubEl = document.getElementById("kanban-publicadas");
  pubEl.innerHTML = publicadasRecientes.length
    ? publicadasRecientes.map((s) => renderKanbanCard(s, true)).join("")
    : '<div class="kanban-empty">Todavía no hay publicaciones.</div>';

  for (const btn of pendEl.querySelectorAll(".btn-publicar")) {
    btn.addEventListener("click", () => publicarSolicitud(btn.dataset.id));
  }
  for (const btn of pendEl.querySelectorAll(".btn-vincular")) {
    btn.addEventListener("click", () => {
      const select = pendEl.querySelector(`.link-pauta-select[data-id="${btn.dataset.id}"]`);
      vincularPauta(btn.dataset.id, select.value);
    });
  }
}

async function publicarSolicitud(id) {
  try {
    await apiFetch(`/publication-requests/${id}/publish`, { method: "POST" });
    showStatus("Solicitud publicada.", false);
    await Promise.all([loadSolicitudes(), loadClientesYPautas(), loadDashboard()]);
  } catch (error) {
    showStatus(error.message, true);
  }
}

async function vincularPauta(id, pautaId) {
  if (!pautaId) {
    showStatus("Elige una pauta antes de vincular.", true);
    return;
  }
  try {
    await apiFetch(`/publication-requests/${id}/link-pauta`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pauta_id: pautaId }),
    });
    showStatus("Pauta vinculada. Ya se puede publicar.", false);
    await loadSolicitudes();
  } catch (error) {
    showStatus(error.message, true);
  }
}

// ---------- Dashboard comercial ----------
//
// Todo lo que se ve aquí viene tal cual de /dashboard/{resumen,alertas,ranking}
// — esta pantalla no calcula ni reordena nada por su cuenta, solo formatea
// para pantalla (moneda, fechas, iconos) lo que ya entrega el backend.

const DASHBOARD_MONEY = [
  ["ingreso_contratado_activo", "Ingreso activo", "icon-money", true],
  ["ingreso_historico", "Ingreso histórico", "icon-money", true],
  ["peso_comercial_promedio", "Peso comercial promedio", "icon-target", true],
];

const DASHBOARD_ACTIVIDAD = [
  ["clientes_activos", "Clientes activos", "icon-users", false],
  ["pautas_activas", "Pautas activas", "icon-check", false],
  ["pautas_vencidas", "Pautas vencidas", "icon-alert", false],
  ["solicitudes_pendientes", "Solicitudes pendientes", "icon-inbox", false],
  ["publicaciones_este_mes", "Publicaciones este mes", "icon-check", false],
  ["valor_promedio_por_cliente", "Valor promedio/cliente", "icon-money", true],
];

// Categorías operativas — necesitan acción del equipo hoy.
const ALERTAS_ATENCION = [
  {
    id: "cupo-agotado",
    campo: "clientes_cupo_agotado",
    icon: "icon-alert",
    severity: "danger",
    label: "clientes con cupo agotado",
  },
  {
    id: "menos-3",
    campo: "clientes_menos_de_3_restantes",
    icon: "icon-clock",
    severity: "warning",
    label: "clientes por agotar publicaciones",
  },
  {
    id: "por-vencer",
    campo: "clientes_por_vencer",
    icon: "icon-clock",
    severity: "warning",
    label: "clientes por vencer (≤7 días)",
  },
  {
    id: "solicitudes-antiguas",
    campo: "solicitudes_antiguas",
    icon: "icon-inbox",
    severity: "danger",
    label: "solicitudes esperando +4h",
    esSolicitud: true,
  },
];

// Categorías comerciales — oportunidades de venta/renovación, no urgencias.
const ALERTAS_OPORTUNIDAD = [
  {
    id: "individuales",
    campo: "clientes_individuales_pendientes",
    icon: "icon-inbox",
    severity: "info",
    label: "publicaciones individuales pendientes",
  },
  {
    id: "renovar",
    campo: "clientes_contrato_por_renovar",
    icon: "icon-refresh",
    severity: "info",
    label: "contratos próximos a renovar",
  },
  {
    id: "sin-usar",
    campo: "clientes_publicaciones_sin_usar",
    icon: "icon-money",
    severity: "info",
    label: "dejaron publicaciones sin usar",
  },
  {
    id: "premium",
    campo: "clientes_premium",
    icon: "icon-target",
    severity: "success",
    label: "clientes premium (semestral/anual)",
  },
];

function renderStatCard(icon, valor, label) {
  return `
    <div class="stat-card">
      <span class="stat-card-icon"><svg class="icon"><use href="#${icon}"></use></svg></span>
      <span class="stat-card-value">${valor}</span>
      <span class="stat-card-label">${label}</span>
    </div>`;
}

function renderStatRow(containerId, campos, resumen) {
  document.getElementById(containerId).innerHTML = campos
    .map(([campo, label, icon, esMonetario]) =>
      renderStatCard(icon, esMonetario ? formatMoneda(resumen[campo]) : resumen[campo], label)
    )
    .join("");
}

function formatearClienteAlerta(cliente) {
  return cliente.nombre;
}

function formatearSolicitudAlerta(solicitud) {
  const recibida = solicitud.fecha_recepcion.slice(0, 16).replace("T", " ");
  return `${solicitud.texto} — recibida ${recibida}`;
}

function renderAlertCard(config, items) {
  const formatear = config.esSolicitud ? formatearSolicitudAlerta : formatearClienteAlerta;
  const count = items.length;
  const detalle =
    count === 0
      ? '<p class="muted">Sin novedades.</p>'
      : items.map((item) => `<div class="alert-detail-item">${formatear(item)}</div>`).join("");

  return `
    <div class="alert-card" data-severity="${config.severity}">
      <button type="button" class="alert-card-toggle">
        <span class="alert-card-icon"><svg class="icon"><use href="#${config.icon}"></use></svg></span>
        <span class="alert-card-body">
          <span class="alert-card-count">${count}</span>
          <span class="alert-card-label">${config.label}</span>
        </span>
        <svg class="alert-card-chevron"><use href="#icon-chevron"></use></svg>
      </button>
      <div class="alert-card-detail"><div class="alert-card-detail-inner">${detalle}</div></div>
    </div>`;
}

function renderDashboardAlertas(alertas) {
  document.getElementById("dashboard-alertas").innerHTML = ALERTAS_ATENCION.map((cfg) =>
    renderAlertCard(cfg, alertas[cfg.campo])
  ).join("");
  document.getElementById("dashboard-oportunidades").innerHTML = ALERTAS_OPORTUNIDAD.map((cfg) =>
    renderAlertCard(cfg, alertas[cfg.campo])
  ).join("");
}

function renderRankingComercial(ranking) {
  const el = document.getElementById("ranking-comercial");
  if (ranking.length === 0) {
    el.innerHTML = '<p class="muted">Todavía no hay clientes con pautas.</p>';
    return;
  }
  const maxPeso = Math.max(...ranking.map((item) => Number(item.peso_comercial)));
  el.innerHTML = ranking
    .map((item, index) => {
      const pct = maxPeso > 0 ? Math.round((Number(item.peso_comercial) / maxPeso) * 100) : 0;
      return `
      <div class="ranking-row">
        <span class="ranking-pos">${index + 1}</span>
        <div class="ranking-info">
          <div class="ranking-name-row">
            <span class="ranking-name">${item.cliente.nombre}</span>
            <span class="badge badge-${item.estado_comercial}">${ESTADO_COMERCIAL_LABELS[item.estado_comercial]}</span>
          </div>
          <div class="ranking-bar-track"><div class="ranking-bar-fill" style="width:${pct}%"></div></div>
        </div>
        <div class="ranking-value">
          <span class="ranking-money">${formatMoneda(item.valor_contratado)}</span>
          <span class="ranking-peso">Peso ${formatMoneda(item.peso_comercial)}</span>
        </div>
      </div>`;
    })
    .join("");
}

async function loadDashboard() {
  const [resumen, alertas, ranking] = await Promise.all([
    apiFetch("/dashboard/resumen"),
    apiFetch("/dashboard/alertas"),
    apiFetch("/dashboard/ranking"),
  ]);
  renderStatRow("dashboard-money", DASHBOARD_MONEY, resumen);
  renderStatRow("dashboard-actividad", DASHBOARD_ACTIVIDAD, resumen);
  renderDashboardAlertas(alertas);
  renderRankingComercial(ranking);
}

// ---------- formularios ----------

function setupFormSolicitud() {
  document.getElementById("form-solicitud").addEventListener("submit", async (event) => {
    event.preventDefault();
    const pautaId = document.getElementById("solicitud-pauta").value;
    const payload = {
      pauta_id: pautaId || null,
      texto: document.getElementById("solicitud-texto").value,
      prioridad_manual: document.getElementById("solicitud-prioridad").checked,
    };
    try {
      await apiFetch("/publication-requests", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      showStatus("Solicitud registrada.", false);
      event.target.reset();
      document.getElementById("solicitud-pauta-buscar").value = "";
      solicitudPautaFiltro = "";
      renderSelectPautas();
      await loadSolicitudes();
    } catch (error) {
      showStatus(error.message, true);
    }
  });
}

function setupFormCliente() {
  document.getElementById("form-cliente").addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = {
      nombre: document.getElementById("cliente-nombre").value,
      tipo: document.getElementById("cliente-tipo").value,
      telefono: document.getElementById("cliente-telefono").value,
      instagram: document.getElementById("cliente-instagram").value || null,
    };
    try {
      await apiFetch("/clients", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      showStatus("Cliente creado.", false);
      event.target.reset();
      closeDrawer(document.getElementById("drawer-cliente"));
      await loadClientesYPautas();
    } catch (error) {
      showStatus(error.message, true);
    }
  });
}

function setupFormPauta() {
  document.getElementById("form-pauta").addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = {
      client_id: document.getElementById("pauta-cliente").value,
      fecha_inicio: document.getElementById("pauta-fecha-inicio").value,
      fecha_fin: document.getElementById("pauta-fecha-fin").value,
      publicaciones_contratadas: Number(document.getElementById("pauta-cantidad").value),
      valor_pagado: document.getElementById("pauta-valor").value,
      fecha_pago: document.getElementById("pauta-fecha-pago").value,
      observaciones: document.getElementById("pauta-observaciones").value || null,
    };
    try {
      await apiFetch("/pautas", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      showStatus("Pauta creada.", false);
      event.target.reset();
      closeDrawer(document.getElementById("drawer-pauta"));
      await loadClientesYPautas();
      await loadDashboard();
    } catch (error) {
      showStatus(error.message, true);
    }
  });
}

// ---------- arranque ----------

async function init() {
  setupTabs();
  setupMobileNav();
  setupGlobalClicks();
  setupFormSolicitud();
  setupFormCliente();
  setupFormPauta();
  setupFormLogin();
  setupLogout();
  document.getElementById("refrescar-solicitudes").addEventListener("click", loadSolicitudes);
  document.getElementById("refrescar-clientes").addEventListener("click", loadClientesYPautas);
  document.getElementById("refrescar-dashboard").addEventListener("click", loadDashboard);
  document.getElementById("solicitud-pauta-buscar").addEventListener("input", (event) => {
    solicitudPautaFiltro = event.target.value;
    renderSelectPautas();
  });
  document.getElementById("clientes-buscar").addEventListener("input", (event) => {
    clientesFiltro = event.target.value;
    renderListaClientes();
  });

  try {
    await apiFetch("/auth/me");
  } catch {
    // apiFetch ya llamó a showLogin() en el 401 — nada más que hacer.
    return;
  }

  showApp();
  try {
    await loadClientesYPautas();
    await loadSolicitudes();
    await loadDashboard();
  } catch (error) {
    showStatus(error.message, true);
  }
}

init();
