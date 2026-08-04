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

const PAUTA_TIPO_LABELS = {
  individual: "Individual",
  mensual: "Mensual",
  bimestral: "Bimestral",
  trimestral: "Trimestral",
  semestral: "Semestral",
  anual: "Anual",
};

// Catálogo real de planes de Portal Vallenato (2026-08-05). `dias` es solo
// para sugerir fecha_fin al elegir un plan — la clasificación real de
// core.entities.pauta.Pauta.tipo sigue viniendo del backend según la
// duración exacta que quede, nunca de este valor sugerido.
const PLANES_CATALOGO = [
  { id: "ind-1", label: "1 publicación — $100.000", cantidad: 1, valor: 100000, dias: 1 },
  { id: "ind-2", label: "2 publicaciones — $150.000", cantidad: 2, valor: 150000, dias: 1 },
  { id: "ind-3", label: "3 publicaciones — $190.000", cantidad: 3, valor: 190000, dias: 1 },
  { id: "mes-1", label: "1 mes — $430.000", cantidad: 10, valor: 430000, dias: 30 },
  { id: "mes-2", label: "2 meses — $760.000", cantidad: 20, valor: 760000, dias: 60 },
  { id: "mes-3", label: "3 meses — $1.100.000", cantidad: 30, valor: 1100000, dias: 90 },
  { id: "mes-6", label: "6 meses — $1.780.000", cantidad: 60, valor: 1780000, dias: 180 },
  { id: "mes-12", label: "1 año — $3.050.000", cantidad: 120, valor: 3050000, dias: 365 },
];

const STALE_REQUEST_HOURS = 4; // solicitud recibida hace más de N horas, sin atender (solo visual)

let clientsById = new Map();
let pautasById = new Map();
let rankingByClientId = new Map();
let solicitudPautaFiltro = "";
let clientesFiltro = "";
let contratosFiltro = "";
let editingClientId = null;
// Listas completas (sin el recorte de 30 que usa el kanban de "Publicadas")
// -- la ficha de cliente necesita el historial completo, no solo lo último.
let solicitudesPendientesTodas = [];
let solicitudesPublicadasTodas = [];

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

function formatHoras(horas) {
  if (horas < 1) return `hace ${Math.max(1, Math.round(horas * 60))} min`;
  const h = Math.floor(horas);
  const m = Math.round((horas - h) * 60);
  return m > 0 ? `hace ${h}h ${m}m` : `hace ${h}h`;
}

function diasHasta(fechaIso) {
  const hoy = new Date();
  hoy.setHours(0, 0, 0, 0);
  const fecha = new Date(fechaIso + "T00:00:00");
  return Math.round((fecha - hoy) / 86_400_000);
}

function truncarTexto(texto, maxLen = 60) {
  return texto.length > maxLen ? texto.slice(0, maxLen).trimEnd() + "…" : texto;
}

// Color puramente visual sobre publicaciones_restantes/contratadas -- no
// reemplaza estado_comercial (ese lo calcula AnalyticsService y ya tiene su
// propio significado de negocio), solo colorea barras y bordes según qué
// tan cerca está un contrato de agotar su cupo:
// >40% verde, 15-40% amarillo, <15% naranja, 0 rojo, vencido gris.
function nivelCupo(restantes, contratadas, vigente) {
  if (!vigente) return "vencido";
  if (restantes <= 0) return "agotado";
  const pct = contratadas > 0 ? restantes / contratadas : 0;
  if (pct > 0.4) return "alto";
  if (pct >= 0.15) return "medio";
  return "bajo";
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

const TAB_TITLES = {
  dashboard: "Dashboard",
  solicitudes: "Solicitudes",
  clientes: "Clientes",
  contratos: "Contratos activos",
};

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
    const fichaBtn = event.target.closest("[data-ficha-cliente]");
    if (fichaBtn) {
      cerrarBusquedaGlobal();
      abrirFichaCliente(fichaBtn.dataset.fichaCliente);
      return;
    }
    const goTabBtn = event.target.closest("[data-go-tab]");
    if (goTabBtn) {
      cerrarBusquedaGlobal();
      activateTab(goTabBtn.dataset.goTab);
      return;
    }
    const quickSolicitudBtn = event.target.closest("[data-quick-solicitud]");
    if (quickSolicitudBtn) {
      quickSolicitudParaCliente(quickSolicitudBtn.dataset.quickSolicitud);
      return;
    }
    const verTextoBtn = event.target.closest(".kanban-card-ver");
    if (verTextoBtn) {
      const parrafo = verTextoBtn.previousElementSibling;
      parrafo.classList.toggle("is-truncated");
      verTextoBtn.textContent = parrafo.classList.contains("is-truncated")
        ? "Ver texto completo"
        : "Ocultar";
      return;
    }
    const openBtn = event.target.closest("[data-open-drawer]");
    if (openBtn) {
      // Solo un drawer visible a la vez -- sin esto, abrir "Editar" o
      // "Renovar pauta" desde dentro de la ficha del cliente dejaba dos
      // drawers superpuestos en el mismo lugar de la pantalla.
      closeAllDrawers();
      if (openBtn.dataset.editClient) {
        startEditCliente(openBtn.dataset.editClient);
      } else if (openBtn.dataset.openDrawer === "drawer-cliente") {
        resetFormClienteDrawer();
      } else if (openBtn.dataset.openDrawer === "drawer-pauta") {
        // Si "Nueva pauta"/"Renovar pauta" se abrió desde la ficha de un
        // cliente puntual, preseleccionarlo — sin esto el <select> queda
        // en el primer cliente de la lista si nadie lo toca a mano, y una
        // pauta puede terminar vinculada al cliente equivocado sin que
        // nadie lo note (pasó de verdad: terminó en "Cliente Final",
        // 2026-08-05).
        document.getElementById("pauta-cliente").value = openBtn.dataset.preselectClient ?? "";
      }
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
    if (!event.target.closest(".topbar-search")) {
      cerrarBusquedaGlobal();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeAllDrawers();
      cerrarBusquedaGlobal();
    }
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
  renderListaContratos();
}

function renderSelectClientes() {
  const select = document.getElementById("pauta-cliente");
  // Nunca se borra el placeholder vacío: sin él, el <select> queda
  // silenciosamente en el primer cliente de la lista si nadie lo toca —
  // así fue como una pauta terminó vinculada a "Cliente Final" en vez del
  // cliente real que se pretendía (2026-08-05).
  const placeholder = select.querySelector('option[value=""]');
  select.innerHTML = "";
  if (placeholder) select.appendChild(placeholder);
  for (const client of clientsById.values()) {
    const option = document.createElement("option");
    option.value = client.id;
    option.textContent = `${client.nombre} (${CLIENT_TIPO_LABELS[client.tipo] ?? client.tipo})`;
    select.appendChild(option);
  }
}

// Catálogo estático (no viene de la API) — se puebla una sola vez al arrancar.
function renderSelectPlanes() {
  const select = document.getElementById("pauta-plan");
  for (const plan of PLANES_CATALOGO) {
    const option = document.createElement("option");
    option.value = plan.id;
    option.textContent = plan.label;
    select.appendChild(option);
  }
}

// Autocompleta cantidad/valor/fechas al elegir un plan del catálogo — todo
// queda editable despues, por si el trato real difiere del oficial (ej. 8
// publicaciones en vez de las 10 del tope mensual).
function aplicarPlanSeleccionado(planId) {
  const plan = PLANES_CATALOGO.find((p) => p.id === planId);
  if (!plan) return;

  const inicioInput = document.getElementById("pauta-fecha-inicio");
  if (!inicioInput.value) {
    inicioInput.value = new Date().toISOString().slice(0, 10);
  }
  const inicio = new Date(inicioInput.value + "T00:00:00");
  const fin = new Date(inicio);
  fin.setDate(fin.getDate() + plan.dias);
  document.getElementById("pauta-fecha-fin").value = fin.toISOString().slice(0, 10);
  document.getElementById("pauta-cantidad").value = plan.cantidad;
  document.getElementById("pauta-valor").value = plan.valor;
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

function renderEditClienteButton(clienteId) {
  return `
    <button type="button" class="btn-link" data-open-drawer="drawer-cliente" data-edit-client="${clienteId}">
      <svg class="icon"><use href="#icon-edit"></use></svg>Editar
    </button>`;
}

// Orden de prioridad visual pedido por el negocio (Sprint UX 3): nombre,
// tipo de plan, publicaciones restantes, vencimiento, valor contratado, y
// peso comercial al final y en menor tamaño -- es un dato de uso interno,
// no lo primero que un editor necesita leer de un vistazo.
function renderClientCard(cliente) {
  const item = rankingByClientId.get(cliente.id);
  if (!item) {
    return `
      <div class="client-card">
        <div class="client-card-body" data-ficha-cliente="${cliente.id}">
          <div class="client-card-header">
            <h3>${cliente.nombre}</h3>
            <span class="badge badge-neutral">Sin pauta</span>
          </div>
          <p class="client-card-meta">
            <svg class="icon"><use href="#icon-phone"></use></svg>${cliente.telefono}
          </p>
        </div>
        <div class="client-card-footer">
          <button type="button" class="btn-link" data-ficha-cliente="${cliente.id}">
            <svg class="icon"><use href="#icon-users"></use></svg>Ver detalle
          </button>
          <button type="button" class="btn-link" data-open-drawer="drawer-pauta" data-preselect-client="${cliente.id}">
            <svg class="icon"><use href="#icon-plus"></use></svg>Nueva pauta
          </button>
          ${renderEditClienteButton(cliente.id)}
        </div>
      </div>`;
  }

  // item.publicaciones_restantes/contratadas describen SOLO el contrato de
  // referencia (la pauta vigente actual, o la mas reciente si ninguna lo
  // es) -- nunca una suma entre contratos. Cada pauta es un contrato
  // independiente: lo que no se usa antes de vencer no pasa al siguiente.
  const pct =
    item.publicaciones_contratadas > 0
      ? Math.round((item.publicaciones_restantes / item.publicaciones_contratadas) * 100)
      : 0;
  const nivel = nivelCupo(item.publicaciones_restantes, item.publicaciones_contratadas, item.vigente);

  return `
    <div class="client-card" data-quota="${nivel}">
      <div class="client-card-body" data-ficha-cliente="${cliente.id}">
        <div class="client-card-header">
          <h3>${cliente.nombre}</h3>
          <span class="badge badge-${item.estado_comercial}">${ESTADO_COMERCIAL_LABELS[item.estado_comercial]}</span>
        </div>
        <p class="client-card-plan">Plan: ${PAUTA_TIPO_LABELS[item.tipo] ?? item.tipo}</p>
        <div class="client-card-progress-track">
          <div class="client-card-progress-fill" style="width:${pct}%"></div>
        </div>
        <p class="client-card-restantes">
          <strong>${item.publicaciones_restantes}</strong> de ${item.publicaciones_contratadas} publicaciones disponibles
        </p>
        <p class="client-card-meta">
          <svg class="icon"><use href="#icon-clock"></use></svg>Vence ${formatFecha(item.fecha_vencimiento)}
        </p>
        <p class="client-card-valor">${formatMoneda(item.valor_contratado)} contratados</p>
        <p class="client-card-peso" title="Peso comercial — uso interno">Peso comercial: ${formatMoneda(item.peso_comercial)}</p>
      </div>
      <div class="client-card-footer">
        <button type="button" class="btn-link" data-ficha-cliente="${cliente.id}">
          <svg class="icon"><use href="#icon-users"></use></svg>Ver detalle
        </button>
        <button type="button" class="btn-link" data-quick-solicitud="${cliente.id}">
          <svg class="icon"><use href="#icon-inbox"></use></svg>Registrar publicación
        </button>
        <button type="button" class="btn-link" data-open-drawer="drawer-pauta" data-preselect-client="${cliente.id}">
          <svg class="icon"><use href="#icon-plus"></use></svg>Renovar pauta
        </button>
        ${renderEditClienteButton(cliente.id)}
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

// Cada Pauta de un cliente es un contrato independiente — el historial
// muestra cada una con su propio saldo y estado, nunca sumados entre si.
function renderHistorialItem(pauta) {
  const estadoTexto = pauta.vigente ? "Vigente" : "Vencido";
  const estadoClase = pauta.vigente ? "saludable" : "vencido";
  return `
    <div class="historial-item">
      <div class="historial-item-fechas">
        ${formatFecha(pauta.fecha_inicio)} – ${formatFecha(pauta.fecha_fin)}
      </div>
      <div class="historial-item-detalle">
        <span>${PAUTA_TIPO_LABELS[pauta.tipo] ?? pauta.tipo}</span>
        <span>${pauta.publicaciones_restantes}/${pauta.publicaciones_contratadas}</span>
        <span class="badge badge-${estadoClase}">${estadoTexto}</span>
      </div>
    </div>`;
}

// ---------- Contratos activos ----------
//
// Cada Pauta vigente se lista como su propio contrato independiente -- un
// cliente con varios contratos activos aparece varias veces, una tarjeta
// por contrato, cada una con su propio saldo (nunca sumados entre sí, ver
// renderHistorialItem más arriba para la misma regla aplicada al
// historial).

function renderContractCard(pauta) {
  const cliente = clientsById.get(pauta.client_id);
  const nombre = cliente ? cliente.nombre : "(cliente desconocido)";
  const nivel = nivelCupo(pauta.publicaciones_restantes, pauta.publicaciones_contratadas, pauta.vigente);
  const pct =
    pauta.publicaciones_contratadas > 0
      ? Math.round((pauta.publicaciones_restantes / pauta.publicaciones_contratadas) * 100)
      : 0;

  return `
    <div class="contract-card" data-quota="${nivel}">
      <div class="contract-card-header">
        <h3 data-ficha-cliente="${pauta.client_id}">${nombre}</h3>
        <span class="badge badge-neutral">${PAUTA_TIPO_LABELS[pauta.tipo] ?? pauta.tipo}</span>
      </div>
      <p class="contract-card-meta">
        <svg class="icon"><use href="#icon-calendar"></use></svg>${formatFecha(pauta.fecha_inicio)} – ${formatFecha(pauta.fecha_fin)}
      </p>
      <div class="client-card-progress-track">
        <div class="client-card-progress-fill" style="width:${pct}%"></div>
      </div>
      <p class="client-card-restantes">
        <strong>${pauta.publicaciones_restantes}</strong> de ${pauta.publicaciones_contratadas} publicaciones disponibles
      </p>
      <div class="contract-card-footer">
        <span class="contract-card-valor">${formatMoneda(pauta.valor_pagado)}</span>
        <span class="contract-card-peso" title="Peso comercial — uso interno">Peso ${formatMoneda(pauta.peso_comercial)}</span>
      </div>
    </div>`;
}

function contratosActivos() {
  return Array.from(pautasById.values())
    .filter((p) => p.vigente)
    .sort((a, b) => a.fecha_fin.localeCompare(b.fecha_fin));
}

function contratosFiltrados() {
  const termino = contratosFiltro.trim().toLowerCase();
  const activos = contratosActivos();
  if (!termino) return activos;
  return activos.filter((pauta) => {
    const cliente = clientsById.get(pauta.client_id);
    return cliente && cliente.nombre.toLowerCase().includes(termino);
  });
}

function renderListaContratos() {
  const el = document.getElementById("lista-contratos");
  if (!el) return;
  const contratos = contratosFiltrados();
  el.innerHTML = contratos.length
    ? contratos.map(renderContractCard).join("")
    : '<p class="muted">No hay contratos vigentes.</p>';
}

// ---------- Ficha completa del cliente (CRM) ----------

function quickSolicitudParaCliente(clientId) {
  const cliente = clientsById.get(clientId);
  if (!cliente) return;
  activateTab("solicitudes");
  const buscar = document.getElementById("solicitud-pauta-buscar");
  buscar.value = cliente.nombre;
  solicitudPautaFiltro = cliente.nombre;
  renderSelectPautas();
  const pautaVigente = Array.from(pautasById.values()).find(
    (p) => p.client_id === clientId && p.vigente
  );
  if (pautaVigente) {
    document.getElementById("solicitud-pauta").value = pautaVigente.id;
  }
  document.getElementById("solicitud-texto").focus();
}

function abrirFichaCliente(clientId) {
  const cliente = clientsById.get(clientId);
  if (!cliente) return;

  const pautasCliente = Array.from(pautasById.values())
    .filter((p) => p.client_id === clientId)
    .sort((a, b) => b.fecha_inicio.localeCompare(a.fecha_inicio));
  const pautaIds = new Set(pautasCliente.map((p) => p.id));
  const item = rankingByClientId.get(clientId);

  const solicitudesPendientesCliente = solicitudesPendientesTodas.filter(
    (s) => s.pauta_id && pautaIds.has(s.pauta_id)
  );
  const solicitudesPublicadasCliente = solicitudesPublicadasTodas
    .filter((s) => s.pauta_id && pautaIds.has(s.pauta_id))
    .sort((a, b) => b.fecha_recepcion.localeCompare(a.fecha_recepcion));

  const ingresosGenerados = pautasCliente.reduce((acc, p) => acc + Number(p.valor_pagado), 0);

  // Timeline: cada evento viene de un dato real ya existente (fecha_registro
  // de la Pauta, fecha_recepcion de la Solicitud) -- nunca se inventa un
  // tipo de evento ("renovación" vs "pauta nueva") que el dominio no
  // distingue hoy.
  const eventos = [];
  for (const p of pautasCliente) {
    eventos.push({
      fecha: p.fecha_registro || p.fecha_inicio,
      texto: `Nueva pauta registrada — ${PAUTA_TIPO_LABELS[p.tipo] ?? p.tipo} (${p.publicaciones_contratadas} publicaciones)`,
    });
  }
  for (const s of solicitudesPublicadasCliente) {
    eventos.push({ fecha: s.fecha_recepcion, texto: `Publicación registrada: "${truncarTexto(s.texto)}"` });
  }
  for (const s of solicitudesPendientesCliente) {
    eventos.push({ fecha: s.fecha_recepcion, texto: `Nueva solicitud recibida: "${truncarTexto(s.texto)}"` });
  }
  eventos.sort((a, b) => String(b.fecha).localeCompare(String(a.fecha)));

  document.getElementById("drawer-ficha-titulo").textContent = cliente.nombre;

  const contactoHtml = `<span>${cliente.telefono}${cliente.instagram ? " · @" + cliente.instagram : ""}</span>`;

  const resumenHtml = item
    ? `
      <div class="ficha-summary">
        <span class="badge badge-${item.estado_comercial}">${ESTADO_COMERCIAL_LABELS[item.estado_comercial]}</span>
        <div class="ficha-summary-meta">
          <span>${PAUTA_TIPO_LABELS[item.tipo] ?? item.tipo} · vence ${formatFecha(item.fecha_vencimiento)}</span>
          ${contactoHtml}
        </div>
      </div>
      <div class="ficha-stats">
        <div class="ficha-stat">
          <div class="ficha-stat-label">Publicaciones restantes</div>
          <div class="ficha-stat-value">${item.publicaciones_restantes} de ${item.publicaciones_contratadas}</div>
        </div>
        <div class="ficha-stat">
          <div class="ficha-stat-label">Ingresos generados</div>
          <div class="ficha-stat-value">${formatMoneda(ingresosGenerados)}</div>
        </div>
        <div class="ficha-stat">
          <div class="ficha-stat-label">Peso comercial</div>
          <div class="ficha-stat-value">${formatMoneda(item.peso_comercial)}</div>
        </div>
        <div class="ficha-stat">
          <div class="ficha-stat-label">Solicitudes pendientes</div>
          <div class="ficha-stat-value">${solicitudesPendientesCliente.length}</div>
        </div>
      </div>`
    : `
      <div class="ficha-summary">
        <span class="badge badge-neutral">Sin pauta</span>
        <div class="ficha-summary-meta">${contactoHtml}</div>
      </div>
      <div class="ficha-stats">
        <div class="ficha-stat">
          <div class="ficha-stat-label">Ingresos generados</div>
          <div class="ficha-stat-value">${formatMoneda(ingresosGenerados)}</div>
        </div>
        <div class="ficha-stat">
          <div class="ficha-stat-label">Solicitudes pendientes</div>
          <div class="ficha-stat-value">${solicitudesPendientesCliente.length}</div>
        </div>
      </div>`;

  const notasHtml = cliente.observaciones
    ? `<div class="ficha-notas">${cliente.observaciones}</div>`
    : `<div class="ficha-notas is-empty">Sin notas internas todavía.</div>`;

  const pautasHtml = pautasCliente.length
    ? pautasCliente.map(renderHistorialItem).join("")
    : '<p class="muted">Este cliente todavía no tiene pautas.</p>';

  const pendientesHtml = solicitudesPendientesCliente.length
    ? solicitudesPendientesCliente
        .map(
          (s) => `
        <div class="ficha-list-item">
          <span class="ficha-list-item-main">${truncarTexto(s.texto)}</span>
          <span class="ficha-list-item-time">${s.fecha_recepcion.slice(0, 16).replace("T", " ")}</span>
        </div>`
        )
        .join("")
    : '<p class="muted">Sin solicitudes pendientes.</p>';

  const publicadasHtml = solicitudesPublicadasCliente.length
    ? solicitudesPublicadasCliente
        .slice(0, 15)
        .map(
          (s) => `
        <div class="ficha-list-item">
          <span class="ficha-list-item-main">${truncarTexto(s.texto, 40)}</span>
          <span class="ficha-list-item-time">${s.fecha_recepcion.slice(0, 16).replace("T", " ")}</span>
        </div>`
        )
        .join("")
    : '<p class="muted">Todavía no hay publicaciones.</p>';

  const timelineHtml = eventos.length
    ? eventos
        .map(
          (e) => `
        <div class="timeline-item">
          <div class="timeline-item-date">${formatFecha(e.fecha)}</div>
          <div class="timeline-item-text">${e.texto}</div>
        </div>`
        )
        .join("")
    : '<p class="muted">Sin actividad todavía.</p>';

  document.getElementById("ficha-content").innerHTML = `
    <div class="ficha-quick-actions">
      <button type="button" class="btn btn-secondary" data-open-drawer="drawer-cliente" data-edit-client="${cliente.id}">
        <svg class="icon"><use href="#icon-edit"></use></svg>Editar
      </button>
      <button type="button" class="btn btn-primary" data-open-drawer="drawer-pauta" data-preselect-client="${cliente.id}">
        <svg class="icon"><use href="#icon-plus"></use></svg>${item ? "Renovar pauta" : "Nueva pauta"}
      </button>
    </div>
    ${resumenHtml}
    <div class="ficha-section">
      <h3 class="ficha-section-title">Notas internas</h3>
      ${notasHtml}
    </div>
    <div class="ficha-section">
      <h3 class="ficha-section-title">Historial de pautas</h3>
      <div class="historial-content">${pautasHtml}</div>
    </div>
    <div class="ficha-section">
      <h3 class="ficha-section-title">Solicitudes pendientes</h3>
      ${pendientesHtml}
    </div>
    <div class="ficha-section">
      <h3 class="ficha-section-title">Historial de publicaciones</h3>
      ${publicadasHtml}
    </div>
    <div class="ficha-section">
      <h3 class="ficha-section-title">Actividad reciente</h3>
      <div class="timeline">${timelineHtml}</div>
    </div>`;

  closeAllDrawers();
  openDrawer("drawer-ficha");
}

// ---------- Solicitudes: kanban ----------

// Explica por qué una solicitud pendiente quedó en esa posición — mismo
// criterio que ordena la cola en el backend (AnalyticsService.
// solicitudes_pendientes_priorizadas), solo que acá se formatea en texto
// para el tooltip; no se recalcula el orden, solo se explica.
function razonOrdenSolicitud(solicitud, pauta) {
  if (solicitud.prioridad_manual) {
    return "Prioridad manual — siempre va primero en la cola.";
  }
  if (!pauta) {
    return "Sin pauta vinculada todavía — cuenta como $0 de peso comercial hasta que se vincule.";
  }
  return `Peso comercial: ${formatMoneda(pauta.peso_comercial)} — a mayor peso, más arriba en la cola.`;
}

// Misma explicación de razonOrdenSolicitud, en una frase corta para
// mostrar siempre visible en la tarjeta (no solo al pasar el mouse) — el
// editor necesita ver de un vistazo por qué esa solicitud quedó en esa
// posición de la cola, sin tener que interpretarlo.
function motivoPrioridadCorto(solicitud, pauta) {
  if (solicitud.prioridad_manual) return "Prioridad manual";
  if (!pauta) return "FIFO — sin pauta vinculada";
  return `Mayor peso comercial (${formatMoneda(pauta.peso_comercial)})`;
}

function renderKanbanCard(solicitud, esPublicada) {
  const pauta = solicitud.pauta_id ? pautasById.get(solicitud.pauta_id) : null;
  const client = pauta ? clientsById.get(pauta.client_id) : null;
  const nombreCliente = client ? client.nombre : "(sin vincular)";
  const horas = horasEnEspera(solicitud.fecha_recepcion);
  const esperandoMucho = !esPublicada && horas >= STALE_REQUEST_HOURS;
  const hora = solicitud.fecha_recepcion.slice(0, 16).replace("T", " ");
  const tituloOrden = esPublicada ? "" : ` title="${razonOrdenSolicitud(solicitud, pauta)}"`;

  const tags = [];
  if (!esPublicada) {
    tags.push(
      `<span class="kanban-card-chip${esperandoMucho ? " kanban-card-chip-urgent" : ""}">⏱ ${formatHoras(horas)}</span>`
    );
  }
  if (pauta) {
    tags.push(`<span class="kanban-card-chip">${PAUTA_TIPO_LABELS[pauta.tipo] ?? pauta.tipo}</span>`);
    tags.push(
      `<span class="kanban-card-chip kanban-card-chip-restantes">${pauta.publicaciones_restantes}/${pauta.publicaciones_contratadas} restantes</span>`
    );
  }

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
  // Publicadas: solo un resumen corto por defecto, el texto completo queda
  // a un clic ("Ver texto completo") — pedido explícito del Sprint UX 3
  // para que la columna de publicadas no compita en espacio con la cola.
  const textoHtml = esPublicada
    ? `<p class="kanban-card-texto is-truncated">${solicitud.texto}</p>
       <button type="button" class="kanban-card-ver">Ver texto completo</button>`
    : `<p class="kanban-card-texto">${solicitud.texto}</p>`;

  return `
    <div class="kanban-card ${claseExtra}"${tituloOrden}>
      <div class="kanban-card-header">
        <span class="kanban-card-cliente">${nombreCliente}${solicitud.prioridad_manual ? " ⚑" : ""}</span>
        <span class="kanban-card-time">${hora}</span>
      </div>
      ${tags.length ? `<div class="kanban-card-tags">${tags.join("")}</div>` : ""}
      ${!esPublicada ? `<p class="kanban-card-priority-reason">${motivoPrioridadCorto(solicitud, pauta)}</p>` : ""}
      ${textoHtml}
      ${accionHtml ? `<div class="kanban-card-footer">${accionHtml}</div>` : ""}
    </div>`;
}

// Métricas rápidas de la cola -- todo calculado desde las mismas listas ya
// cargadas, sin round-trips nuevos al backend. No incluye "tiempo promedio
// de publicación": el dominio solo guarda fecha_recepcion (cuándo llegó la
// solicitud), no cuándo se publicó realmente -- inventar esa métrica con
// el dato equivocado sería más engañoso que no mostrarla.
function renderMetricasSolicitudes(pendientes, publicadas) {
  const hoyStr = new Date().toISOString().slice(0, 10);
  const datos = {
    pendientes: pendientes.length,
    prioridad: pendientes.filter((s) => s.prioridad_manual).length,
    sinPauta: pendientes.filter((s) => !s.pauta_id).length,
    publicadasHoy: publicadas.filter((s) => s.fecha_recepcion.slice(0, 10) === hoyStr).length,
  };
  const campos = [
    ["pendientes", "Pendientes", "icon-inbox", false],
    ["prioridad", "Prioridad", "icon-alert", false],
    ["sinPauta", "Sin pauta", "icon-clock", false],
    ["publicadasHoy", "Publicadas hoy", "icon-check", false],
  ];
  renderStatRow("solicitudes-metricas", campos, datos);
}

async function loadSolicitudes() {
  // El backend ya entrega "recibida" en orden de trabajo (prioridad manual
  // > peso comercial > fecha de recepción) — ver
  // AnalyticsService.solicitudes_pendientes_priorizadas. No se reordena
  // acá; hacerlo pisaría esa regla con una versión más pobre (solo fecha).
  const [pendientes, publicadas] = await Promise.all([
    apiFetch("/publication-requests?estado=recibida"),
    apiFetch("/publication-requests?estado=publicada"),
  ]);
  publicadas.sort((a, b) => b.fecha_recepcion.localeCompare(a.fecha_recepcion));
  solicitudesPendientesTodas = pendientes;
  solicitudesPublicadasTodas = publicadas;
  const publicadasRecientes = publicadas.slice(0, 30);

  renderMetricasSolicitudes(pendientes, publicadas);

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

// Las 6 métricas que de verdad ayudan a responder "¿cómo va el negocio hoy?"
// (Sprint UX 3) — el resto de indicadores de AnalyticsService quedan en
// "Otros indicadores" más abajo, para no competir en espacio con estas.
const DASHBOARD_METRICAS_PRINCIPALES = [
  ["clientes_activos", "Clientes activos", "icon-users", false],
  ["ingreso_contratado_activo", "Ingresos vigencia actual", "icon-money", true],
  ["solicitudes_pendientes", "Solicitudes pendientes", "icon-inbox", false],
  ["publicaciones_este_mes", "Publicaciones este mes", "icon-check", false],
  ["renovaciones_del_mes", "Renovaciones del mes", "icon-refresh", false],
  ["ingresos_ultimo_mes", "Ingresos último mes", "icon-money", true],
];

const DASHBOARD_ACTIVIDAD = [
  ["pautas_vencidas", "Pautas vencidas", "icon-alert", false],
  ["peso_comercial_promedio", "Peso comercial promedio", "icon-target", true],
  ["valor_promedio_por_cliente", "Valor promedio/cliente", "icon-money", true],
  ["ingreso_historico", "Ingreso histórico", "icon-money", true],
];

// "Renovaciones del mes" e "ingresos último mes" no vienen del backend --
// se calculan aquí mismo, sobre las Pautas que ya están cargadas en
// memoria (pautasById), sin ningún round-trip nuevo a la API. Ambas
// definiciones fueron confirmadas con el negocio antes de implementarse
// (Sprint UX 3): "ingresos" es dinero ya cobrado (fecha_pago), no una
// proyección; "renovaciones" son contratos por paquete de tiempo (no
// Individual) cuyo fecha_fin cae en el mes calendario actual.

function calcularRenovacionesDelMes() {
  const ahora = new Date();
  let total = 0;
  for (const pauta of pautasById.values()) {
    if (pauta.tipo === "individual") continue;
    const fechaFin = new Date(pauta.fecha_fin + "T00:00:00");
    if (fechaFin.getMonth() === ahora.getMonth() && fechaFin.getFullYear() === ahora.getFullYear()) {
      total += 1;
    }
  }
  return total;
}

function calcularIngresosDelMes(offsetMeses) {
  const ahora = new Date();
  const objetivo = new Date(ahora.getFullYear(), ahora.getMonth() + offsetMeses, 1);
  let total = 0;
  for (const pauta of pautasById.values()) {
    const fechaPago = new Date(pauta.fecha_pago + "T00:00:00");
    if (fechaPago.getMonth() === objetivo.getMonth() && fechaPago.getFullYear() === objetivo.getFullYear()) {
      total += Number(pauta.valor_pagado);
    }
  }
  return total;
}

function renderMetricasPrincipales(resumen) {
  const datos = {
    ...resumen,
    renovaciones_del_mes: calcularRenovacionesDelMes(),
    ingresos_ultimo_mes: calcularIngresosDelMes(-1),
  };
  renderStatRow("dashboard-metricas-principales", DASHBOARD_METRICAS_PRINCIPALES, datos);
}

// ---------- Acciones para hoy ----------
//
// Traduce las mismas listas de /dashboard/alertas (ya calculadas por
// AnalyticsService) a frases concretas — no agrega ninguna regla de
// negocio nueva, solo prioriza y redacta lo que ya existe para que el
// editor no tenga que interpretar tablas.

const SEVERIDAD_ORDEN = { danger: 0, warning: 1, info: 2, success: 3 };
const SEVERIDAD_EMOJI = { danger: "🔴", warning: "🟠", info: "🔵", success: "🟢" };

function computarAccionesHoy(resumen, alertas) {
  const acciones = [];
  const idsCupoAgotado = new Set(alertas.clientes_cupo_agotado.map((c) => c.id));

  for (const cliente of alertas.clientes_por_vencer) {
    const item = rankingByClientId.get(cliente.id);
    if (!item || !item.vigente) continue;
    const dias = diasHasta(item.fecha_vencimiento);
    if (dias <= 0) {
      acciones.push({ severidad: "danger", texto: `Hoy vence ${cliente.nombre}`, clienteId: cliente.id, renovar: true });
    } else if (dias <= 3) {
      acciones.push({
        severidad: "warning",
        texto: `${cliente.nombre} vence en ${dias} día${dias === 1 ? "" : "s"}`,
        clienteId: cliente.id,
        renovar: true,
      });
    }
  }

  for (const cliente of alertas.clientes_cupo_agotado) {
    acciones.push({
      severidad: "danger",
      texto: `${cliente.nombre}: cupo agotado, necesita renovación`,
      clienteId: cliente.id,
      renovar: true,
    });
  }

  for (const cliente of alertas.clientes_menos_de_3_restantes) {
    if (idsCupoAgotado.has(cliente.id)) continue;
    const item = rankingByClientId.get(cliente.id);
    const restantes = item ? item.publicaciones_restantes : "pocas";
    acciones.push({
      severidad: "warning",
      texto: `${cliente.nombre} tiene solo ${restantes} publicaciones disponibles`,
      clienteId: cliente.id,
    });
  }

  if (alertas.solicitudes_antiguas.length > 0) {
    const n = alertas.solicitudes_antiguas.length;
    acciones.push({
      severidad: "danger",
      texto: `${n} solicitud${n === 1 ? "" : "es"} lleva${n === 1 ? "" : "n"} más de 4h esperando respuesta`,
      tab: "solicitudes",
    });
  }

  if (resumen.solicitudes_pendientes > 0) {
    const n = resumen.solicitudes_pendientes;
    acciones.push({
      severidad: "warning",
      texto: `Hay ${n} solicitud${n === 1 ? "" : "es"} pendiente${n === 1 ? "" : "s"}`,
      tab: "solicitudes",
    });
  }

  acciones.sort((a, b) => SEVERIDAD_ORDEN[a.severidad] - SEVERIDAD_ORDEN[b.severidad]);
  return acciones;
}

function renderAccionesHoy(resumen, alertas) {
  const acciones = computarAccionesHoy(resumen, alertas);
  const el = document.getElementById("dashboard-acciones");
  if (acciones.length === 0) {
    el.innerHTML = '<div class="action-feed-empty">Sin pendientes urgentes — todo al día.</div>';
    return;
  }
  el.innerHTML = acciones
    .map((accion) => {
      let botones = "";
      if (accion.clienteId) {
        botones += `<button type="button" class="btn btn-secondary" data-ficha-cliente="${accion.clienteId}">Ver cliente</button>`;
        if (accion.renovar) {
          botones += `<button type="button" class="btn btn-primary" data-open-drawer="drawer-pauta" data-preselect-client="${accion.clienteId}">Renovar pauta</button>`;
        }
      } else if (accion.tab) {
        botones += `<button type="button" class="btn btn-secondary" data-go-tab="${accion.tab}">Ver</button>`;
      }
      return `
        <div class="action-item" data-severity="${accion.severidad}">
          <span class="action-item-emoji">${SEVERIDAD_EMOJI[accion.severidad]}</span>
          <span class="action-item-text">${accion.texto}</span>
          <span class="action-item-actions">${botones}</span>
        </div>`;
    })
    .join("");
}

// ---------- Próximas renovaciones ----------
//
// Solo clientes activos (vigente=true) con un paquete de tiempo (no
// Individual — un cliente Individual no "renueva", ver
// AnalyticsService.clientes_con_contrato_por_renovar), agrupados por qué
// tan cerca está su vencimiento. Nunca muestra vencidos.

const RENEWAL_BUCKETS = [
  { limite: 7, titulo: "Vence en 7 días" },
  { limite: 15, titulo: "Vence en 15 días" },
  { limite: 30, titulo: "Vence en 30 días" },
];

function renderRenewalCard(item, dias) {
  return `
    <div class="renewal-card">
      <div class="renewal-card-name">${item.cliente.nombre}</div>
      <div class="renewal-card-meta">
        ${PAUTA_TIPO_LABELS[item.tipo] ?? item.tipo} · vence ${formatFecha(item.fecha_vencimiento)} (${dias} día${dias === 1 ? "" : "s"})
      </div>
      <div class="renewal-card-actions">
        <button type="button" class="btn btn-secondary" data-ficha-cliente="${item.cliente.id}">Ver cliente</button>
        <button type="button" class="btn btn-primary" data-open-drawer="drawer-pauta" data-preselect-client="${item.cliente.id}">Renovar pauta</button>
      </div>
    </div>`;
}

function renderProximasRenovaciones(ranking) {
  const candidatos = ranking
    .filter((item) => item.vigente && item.tipo !== "individual")
    .map((item) => ({ item, dias: diasHasta(item.fecha_vencimiento) }))
    .filter(({ dias }) => dias >= 0 && dias <= 30)
    .sort((a, b) => a.dias - b.dias);

  let restantes = candidatos;
  const el = document.getElementById("dashboard-renovaciones");
  el.innerHTML = RENEWAL_BUCKETS.map(({ limite, titulo }) => {
    const enEsteBucket = restantes.filter(({ dias }) => dias <= limite);
    restantes = restantes.filter(({ dias }) => dias > limite);
    const cuerpo = enEsteBucket.length
      ? enEsteBucket.map(({ item, dias }) => renderRenewalCard(item, dias)).join("")
      : '<p class="renewal-empty">Nada por aquí.</p>';
    return `
      <div>
        <h3 class="renewal-group-title">${titulo}</h3>
        <div class="renewal-cards">${cuerpo}</div>
      </div>`;
  }).join("");
}

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

function renderRankingComercial(ranking, elementId = "ranking-comercial", vacioMensaje = "Todavía no hay clientes con pautas.") {
  const el = document.getElementById(elementId);
  if (ranking.length === 0) {
    el.innerHTML = `<p class="muted">${vacioMensaje}</p>`;
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
  renderAccionesHoy(resumen, alertas);
  renderMetricasPrincipales(resumen);
  renderProximasRenovaciones(ranking);
  renderStatRow("dashboard-actividad", DASHBOARD_ACTIVIDAD, resumen);
  renderDashboardAlertas(alertas);
  renderRankingComercial(ranking);
  // Mismo ranking, filtrado a clientes cuyo contrato de referencia está
  // vigente hoy — el histórico ya trae `vigente` por item, así que no hace
  // falta otro round-trip al backend, solo filtrar aquí.
  renderRankingComercial(
    ranking.filter((item) => item.vigente),
    "ranking-comercial-activos",
    "Ningún cliente tiene un contrato vigente en este momento."
  );
}

// ---------- buscador global ----------
//
// Busca sobre lo que ya está cargado en memoria (clientsById, pautasById,
// solicitudes*Todas) -- sin endpoint nuevo. Clientes y pautas se buscan
// por nombre de cliente; solicitudes, por el texto de la publicación.

function buscarGlobal(termino) {
  const t = termino.trim().toLowerCase();
  if (t.length < 2) return null;

  const clientes = Array.from(clientsById.values())
    .filter((c) => c.nombre.toLowerCase().includes(t))
    .slice(0, 6);

  const pautas = Array.from(pautasById.values())
    .filter((p) => {
      const cliente = clientsById.get(p.client_id);
      return cliente && cliente.nombre.toLowerCase().includes(t);
    })
    .slice(0, 6);

  const solicitudes = [...solicitudesPendientesTodas, ...solicitudesPublicadasTodas]
    .filter((s) => s.texto.toLowerCase().includes(t))
    .slice(0, 6);

  return { clientes, pautas, solicitudes };
}

function renderResultadoCliente(cliente) {
  return `
    <button type="button" class="search-result-item" data-ficha-cliente="${cliente.id}">
      <svg class="search-result-item-icon"><use href="#icon-users"></use></svg>
      <span class="search-result-item-main">
        <span class="search-result-item-title">${cliente.nombre}</span>
        <span class="search-result-item-sub">${CLIENT_TIPO_LABELS[cliente.tipo] ?? cliente.tipo}</span>
      </span>
    </button>`;
}

function renderResultadoPauta(pauta) {
  const cliente = clientsById.get(pauta.client_id);
  return `
    <button type="button" class="search-result-item" data-ficha-cliente="${pauta.client_id}">
      <svg class="search-result-item-icon"><use href="#icon-contract"></use></svg>
      <span class="search-result-item-main">
        <span class="search-result-item-title">${cliente ? cliente.nombre : "(cliente desconocido)"}</span>
        <span class="search-result-item-sub">${PAUTA_TIPO_LABELS[pauta.tipo] ?? pauta.tipo} · ${formatFecha(pauta.fecha_inicio)} – ${formatFecha(pauta.fecha_fin)}</span>
      </span>
    </button>`;
}

function renderResultadoSolicitud(solicitud) {
  const pauta = solicitud.pauta_id ? pautasById.get(solicitud.pauta_id) : null;
  const cliente = pauta ? clientsById.get(pauta.client_id) : null;
  return `
    <button type="button" class="search-result-item" data-go-tab="solicitudes">
      <svg class="search-result-item-icon"><use href="#icon-inbox"></use></svg>
      <span class="search-result-item-main">
        <span class="search-result-item-title">${truncarTexto(solicitud.texto, 46)}</span>
        <span class="search-result-item-sub">${cliente ? cliente.nombre : "(sin vincular)"} · ${solicitud.estado}</span>
      </span>
    </button>`;
}

function renderResultadosBusqueda(resultados) {
  const el = document.getElementById("buscador-global-resultados");
  if (!resultados) {
    el.hidden = true;
    el.innerHTML = "";
    return;
  }
  const grupos = [
    ["Clientes", resultados.clientes.map(renderResultadoCliente)],
    ["Pautas", resultados.pautas.map(renderResultadoPauta)],
    ["Solicitudes", resultados.solicitudes.map(renderResultadoSolicitud)],
  ].filter(([, items]) => items.length > 0);

  el.innerHTML = grupos.length
    ? grupos
        .map(
          ([titulo, items]) => `
        <div class="search-result-group">
          <div class="search-result-group-title">${titulo}</div>
          ${items.join("")}
        </div>`
        )
        .join("")
    : '<div class="search-empty">Sin resultados.</div>';
  el.hidden = false;
}

function cerrarBusquedaGlobal() {
  const input = document.getElementById("buscador-global");
  if (input) input.value = "";
  renderResultadosBusqueda(null);
}

function setupBuscadorGlobal() {
  const input = document.getElementById("buscador-global");
  input.addEventListener("input", (event) => {
    renderResultadosBusqueda(buscarGlobal(event.target.value));
  });
  input.addEventListener("focus", () => {
    if (input.value.trim().length >= 2) renderResultadosBusqueda(buscarGlobal(input.value));
  });
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

function resetFormClienteDrawer() {
  editingClientId = null;
  document.getElementById("drawer-cliente-titulo").textContent = "Nuevo cliente";
  document.getElementById("form-cliente-submit").textContent = "Crear cliente";
  document.getElementById("form-cliente").reset();
}

function startEditCliente(clientId) {
  const cliente = clientsById.get(clientId);
  if (!cliente) return;
  editingClientId = clientId;
  document.getElementById("drawer-cliente-titulo").textContent = "Editar cliente";
  document.getElementById("form-cliente-submit").textContent = "Guardar cambios";
  document.getElementById("cliente-nombre").value = cliente.nombre;
  document.getElementById("cliente-tipo").value = cliente.tipo;
  document.getElementById("cliente-telefono").value = cliente.telefono;
  document.getElementById("cliente-instagram").value = cliente.instagram || "";
  document.getElementById("cliente-observaciones").value = cliente.observaciones || "";
}

function setupFormCliente() {
  document.getElementById("form-cliente").addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = {
      nombre: document.getElementById("cliente-nombre").value,
      tipo: document.getElementById("cliente-tipo").value,
      telefono: document.getElementById("cliente-telefono").value,
      instagram: document.getElementById("cliente-instagram").value || null,
      observaciones: document.getElementById("cliente-observaciones").value || null,
    };
    try {
      if (editingClientId) {
        await apiFetch(`/clients/${editingClientId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        showStatus("Cliente actualizado.", false);
      } else {
        await apiFetch("/clients", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        showStatus("Cliente creado.", false);
      }
      resetFormClienteDrawer();
      closeDrawer(document.getElementById("drawer-cliente"));
      await loadClientesYPautas();
    } catch (error) {
      showStatus(error.message, true);
    }
  });
}

function setupFormPauta() {
  document.getElementById("pauta-plan").addEventListener("change", (event) => {
    aplicarPlanSeleccionado(event.target.value);
  });
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

const AUTO_REFRESH_INTERVAL_MS = 30_000; // sensacion de "casi en vivo" sin websockets

function appEstaVisible() {
  return document.visibilityState === "visible" && !document.getElementById("app-shell").hidden;
}

function refrescarTodo() {
  return Promise.all([loadClientesYPautas(), loadSolicitudes(), loadDashboard()]);
}

// Sin sincronización en tiempo real entre pestañas/dispositivos — sin esto,
// una pestaña abierta hace rato no se entera de nada hasta que alguien
// toca "Actualizar" a mano. Dos mecanismos, ninguno necesita websockets:
//
// 1. Al volver de estar en otra pestaña/app (Page Visibility API) — cubre
//    "cargué algo desde el celular y volví al escritorio".
// 2. Sondeo cada AUTO_REFRESH_INTERVAL_MS mientras la pestaña esté visible
//    — cubre "me quedé quieto en una pantalla y alguien más cambió algo".
//    Se salta en silencio si falla (un hipo de red no debe interrumpir con
//    un toast cada 30 segundos) y no hace nada si la pestaña está oculta,
//    para no gastar red de fondo sin motivo.
function setupRefrescoAutomatico() {
  document.addEventListener("visibilitychange", () => {
    if (!appEstaVisible()) return;
    refrescarTodo().catch((error) => showStatus(error.message, true));
  });
  window.setInterval(() => {
    if (!appEstaVisible()) return;
    refrescarTodo().catch(() => {
      // silencioso -- ver comentario arriba
    });
  }, AUTO_REFRESH_INTERVAL_MS);
}

async function init() {
  setupTabs();
  setupMobileNav();
  setupGlobalClicks();
  setupFormSolicitud();
  setupFormCliente();
  setupFormPauta();
  setupFormLogin();
  setupLogout();
  setupRefrescoAutomatico();
  setupBuscadorGlobal();
  renderSelectPlanes();
  document.getElementById("refrescar-solicitudes").addEventListener("click", loadSolicitudes);
  document.getElementById("refrescar-clientes").addEventListener("click", loadClientesYPautas);
  document.getElementById("refrescar-dashboard").addEventListener("click", loadDashboard);
  document.getElementById("refrescar-contratos").addEventListener("click", loadClientesYPautas);
  document.getElementById("solicitud-pauta-buscar").addEventListener("input", (event) => {
    solicitudPautaFiltro = event.target.value;
    renderSelectPautas();
  });
  document.getElementById("clientes-buscar").addEventListener("input", (event) => {
    clientesFiltro = event.target.value;
    renderListaClientes();
  });
  document.getElementById("contratos-buscar").addEventListener("input", (event) => {
    contratosFiltro = event.target.value;
    renderListaContratos();
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
