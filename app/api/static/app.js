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

// Portal Vallenato opera en Colombia (UTC-5) pero el backend guarda
// fecha_recepcion/fecha_registro en UTC (bien, para almacenamiento) --
// mostrar ese string crudo corre la hora 5h adelante de la hora real del
// negocio (una solicitud de las 7:51pm aparecía como "00:51" del día
// siguiente). Mismo bug que core/clock.py resolvió en el backend para
// vigencia de Pauta, aquí para lo que se muestra en pantalla.
const NEGOCIO_TZ = "America/Bogota";

function formatFechaHoraNegocio(iso) {
  if (!iso) return "";
  return new Intl.DateTimeFormat("sv-SE", {
    timeZone: NEGOCIO_TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(iso));
}

// "Hoy" (solo fecha) en la zona horaria del negocio, a partir de un ISO
// UTC o de "ahora" -- para comparar "¿esto pasó hoy?" sin el mismo
// desfase.
function fechaNegocioISO(iso) {
  return new Intl.DateTimeFormat("sv-SE", { timeZone: NEGOCIO_TZ }).format(
    iso ? new Date(iso) : new Date()
  );
}

// Suma/resta días en aritmética de calendario pura, anclada a medianoche
// UTC -- evita que el desfase horario del navegador corra el resultado
// un día, independiente de en qué zona esté configurado el equipo.
function sumarDiasFecha(fechaIso, dias) {
  const fecha = new Date(fechaIso + "T00:00:00Z");
  fecha.setUTCDate(fecha.getUTCDate() + dias);
  return fecha.toISOString().slice(0, 10);
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

// Estado vacío amigable, reutilizado en toda la app en vez de listas o
// tablas en blanco (Sprint UX 4) -- `inline` es la variante chica para
// usarse dentro de una tarjeta/drawer en vez de ocupar toda la sección.
function renderEmptyState(emoji, mensaje, inline = false) {
  return `
    <div class="empty-state${inline ? " empty-state-inline" : ""}">
      <span class="empty-state-emoji">${emoji}</span>
      <p class="empty-state-text">${mensaje}</p>
    </div>`;
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
      await loadAlertas();
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
  alertas: "Alertas",
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
    inicioInput.value = fechaNegocioISO();
  }
  document.getElementById("pauta-fecha-fin").value = sumarDiasFecha(inicioInput.value, plan.dias);
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
          <button type="button" class="btn btn-secondary" data-open-drawer="drawer-pauta" data-preselect-client="${cliente.id}">
            <svg class="icon"><use href="#icon-plus"></use></svg>Nueva pauta
          </button>
          <span class="client-card-footer-secondary">
            <button type="button" class="btn-link" data-ficha-cliente="${cliente.id}">
              <svg class="icon"><use href="#icon-detail"></use></svg>Detalle
            </button>
            ${renderEditClienteButton(cliente.id)}
          </span>
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

  // Nivel 1 (se lee primero): nombre + estado, en la cabecera.
  // Nivel 2 (secundario, agrupado): plan, cupo, vencimiento, valor.
  // Nivel 3: peso comercial -- dato interno, la línea más chica de todas.
  return `
    <div class="client-card" data-quota="${nivel}">
      <div class="client-card-body" data-ficha-cliente="${cliente.id}">
        <div class="client-card-header">
          <h3>${cliente.nombre}</h3>
          <span class="badge badge-${item.estado_comercial}">${ESTADO_COMERCIAL_LABELS[item.estado_comercial]}</span>
        </div>
        <div class="client-card-secondary">
          <p class="client-card-plan">Plan ${PAUTA_TIPO_LABELS[item.tipo] ?? item.tipo}</p>
          <div class="client-card-progress-track">
            <div class="client-card-progress-fill" style="width:${pct}%"></div>
          </div>
          <p class="client-card-restantes">
            <strong>${item.publicaciones_restantes} de ${item.publicaciones_contratadas}</strong> publicaciones disponibles
          </p>
          <p class="client-card-meta">
            <svg class="icon"><use href="#icon-clock"></use></svg>Vence ${formatFecha(item.fecha_vencimiento)}
          </p>
          <p class="client-card-valor">${formatMoneda(item.valor_contratado)} contratados</p>
          <p class="client-card-peso" title="Peso comercial — uso interno">Peso comercial: ${formatMoneda(item.peso_comercial)}</p>
        </div>
      </div>
      <div class="client-card-footer">
        <button type="button" class="btn btn-secondary" data-quick-solicitud="${cliente.id}">
          <svg class="icon"><use href="#icon-inbox"></use></svg>Registrar publicación
        </button>
        <button type="button" class="btn btn-secondary" data-open-drawer="drawer-pauta" data-preselect-client="${cliente.id}">
          <svg class="icon"><use href="#icon-refresh"></use></svg>Renovar
        </button>
        <span class="client-card-footer-secondary">
          <button type="button" class="btn-link" data-ficha-cliente="${cliente.id}">
            <svg class="icon"><use href="#icon-detail"></use></svg>Detalle
          </button>
          ${renderEditClienteButton(cliente.id)}
        </span>
      </div>
    </div>`;
}

function renderListaClientes() {
  const el = document.getElementById("lista-clientes");
  const clientes = clientesFiltrados();
  if (clientes.length) {
    el.innerHTML = clientes.map(renderClientCard).join("");
  } else if (clientesFiltro.trim()) {
    el.innerHTML = renderEmptyState("🔍", "No se encontraron clientes con ese criterio.");
  } else {
    el.innerHTML = renderEmptyState("👥", "Aún no tienes clientes registrados.");
  }
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
    : renderEmptyState("📄", contratosFiltro.trim() ? "No se encontraron contratos con ese criterio." : "No hay contratos vigentes en este momento.");
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
    : renderEmptyState("📄", "Este cliente todavía no tiene pautas.", true);

  const pendientesHtml = solicitudesPendientesCliente.length
    ? solicitudesPendientesCliente
        .map(
          (s) => `
        <div class="ficha-list-item">
          <span class="ficha-list-item-main">${truncarTexto(s.texto)}</span>
          <span class="ficha-list-item-time">${formatFechaHoraNegocio(s.fecha_recepcion)}</span>
        </div>`
        )
        .join("")
    : renderEmptyState("✅", "Sin solicitudes pendientes.", true);

  const publicadasHtml = solicitudesPublicadasCliente.length
    ? solicitudesPublicadasCliente
        .slice(0, 15)
        .map(
          (s) => `
        <div class="ficha-list-item">
          <span class="ficha-list-item-main">${truncarTexto(s.texto, 40)}</span>
          <span class="ficha-list-item-time">${formatFechaHoraNegocio(s.fecha_recepcion)}</span>
        </div>`
        )
        .join("")
    : renderEmptyState("📭", "Todavía no hay publicaciones.", true);

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
    : renderEmptyState("🕐", "Sin actividad todavía.", true);

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

// ---------- Solicitudes: Inbox Editorial ----------

let editingSolicitudId = null;

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

// Misma explicación de razonOrdenSolicitud, con el prefijo "↑" pedido para
// que la tarjeta explique su propia posición sin que nadie tenga que
// interpretarlo (Sprint UX 3.1) — mostrada siempre visible, no solo al
// pasar el mouse.
function motivoPrioridadCorto(solicitud, pauta) {
  if (solicitud.prioridad_manual) return "↑ Prioridad manual";
  if (!pauta) return "↑ Llegó primero — sin pauta vinculada (FIFO)";
  return `↑ Mayor peso comercial (${formatMoneda(pauta.peso_comercial)})`;
}

// Score visual (🔥/🟠/🟢) -- una capa de presentación sobre los mismos tres
// factores que ya deciden el orden real (prioridad manual, peso comercial,
// tiempo esperando). No es una cuarta regla de negocio: STALE_REQUEST_HOURS
// (4h) es el mismo umbral ya usado en toda la app para marcar "esperando
// demasiado"; el doble de ese umbral (8h) es la única cifra nueva, y solo
// decide qué emoji se pinta, nunca el orden real de la cola.
function scoreSolicitud(solicitud, pauta, horas) {
  if (solicitud.prioridad_manual || horas >= STALE_REQUEST_HOURS * 2) {
    return { emoji: "🔥", label: "Alta prioridad" };
  }
  if ((pauta && Number(pauta.peso_comercial) > 0) || horas >= STALE_REQUEST_HOURS) {
    return { emoji: "🟠", label: "Importante" };
  }
  return { emoji: "🟢", label: "Normal" };
}

// "Cliente Premium" = misma definición que AnalyticsService.clientes_premium
// (Pauta vigente semestral o anual) -- replicada aquí sobre datos que ya
// están en memoria (pautasById) en vez de pedirle este dato al backend.
function esClientePremium(clientId) {
  for (const pauta of pautasById.values()) {
    if (
      pauta.client_id === clientId &&
      pauta.vigente &&
      (pauta.tipo === "semestral" || pauta.tipo === "anual")
    ) {
      return true;
    }
  }
  return false;
}

function renderKanbanCardEditForm(solicitud) {
  return `
    <div class="kanban-card is-editing">
      <div class="kanban-card-header">
        <span class="kanban-card-cliente">Editando solicitud…</span>
      </div>
      <form class="kanban-card-edit-form" data-id="${solicitud.id}">
        <textarea class="kanban-card-edit-texto" rows="3" required>${solicitud.texto}</textarea>
        <label class="checkbox">
          <input type="checkbox" class="kanban-card-edit-prioridad" ${solicitud.prioridad_manual ? "checked" : ""}>
          Prioridad manual
        </label>
        <div class="kanban-card-edit-actions">
          <button type="submit" class="btn btn-primary">
            <svg class="icon"><use href="#icon-check"></use></svg>Guardar
          </button>
          <button type="button" class="btn btn-secondary btn-cancelar-edicion" data-id="${solicitud.id}">
            <svg class="icon"><use href="#icon-close"></use></svg>Cancelar
          </button>
        </div>
      </form>
    </div>`;
}

function renderKanbanCard(solicitud, esPublicada) {
  if (!esPublicada && solicitud.id === editingSolicitudId) {
    return renderKanbanCardEditForm(solicitud);
  }

  const pauta = solicitud.pauta_id ? pautasById.get(solicitud.pauta_id) : null;
  const client = pauta ? clientsById.get(pauta.client_id) : null;
  const nombreCliente = client ? client.nombre : "(sin vincular)";
  const horas = horasEnEspera(solicitud.fecha_recepcion);
  const esperandoMucho = !esPublicada && horas >= STALE_REQUEST_HOURS;
  const hora = formatFechaHoraNegocio(solicitud.fecha_recepcion);
  const tituloOrden = esPublicada ? "" : ` title="${razonOrdenSolicitud(solicitud, pauta)}"`;
  const score = esPublicada ? null : scoreSolicitud(solicitud, pauta, horas);

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
    if (esPublicada) {
      tags.push(`<span class="kanban-card-chip">${formatMoneda(pauta.peso_comercial)}</span>`);
    }
  }

  let accionHtml = "";
  if (!esPublicada) {
    accionHtml = solicitud.pauta_id
      ? `<button type="button" class="btn btn-primary btn-publicar" data-id="${solicitud.id}">
           <svg class="icon"><use href="#icon-check"></use></svg>Publicar
         </button>`
      : `<select class="link-pauta-select" data-id="${solicitud.id}">
           <option value="">Elegir pauta…</option>
           ${pautaOptionsHtml(pautasVigentes())}
         </select>
         <button type="button" class="btn btn-secondary btn-vincular" data-id="${solicitud.id}">
           <svg class="icon"><use href="#icon-contract"></use></svg>Vincular
         </button>`;
    accionHtml += `
         <button type="button" class="btn btn-secondary btn-editar" data-id="${solicitud.id}">
           <svg class="icon"><use href="#icon-edit"></use></svg>Editar
         </button>`;
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
        <span class="kanban-card-header-left">
          <span class="kanban-card-cliente">${nombreCliente}${solicitud.prioridad_manual ? " ⚑" : ""}</span>
          ${score ? `<span class="kanban-card-score" title="${score.label}"><span class="kanban-card-score-emoji">${score.emoji}</span>${score.label}</span>` : ""}
        </span>
        <span class="kanban-card-time">${hora}</span>
      </div>
      ${tags.length ? `<div class="kanban-card-tags">${tags.join("")}</div>` : ""}
      ${!esPublicada ? `<p class="kanban-card-priority-reason">${motivoPrioridadCorto(solicitud, pauta)}</p>` : ""}
      ${textoHtml}
      ${accionHtml ? `<div class="kanban-card-footer">${accionHtml}</div>` : ""}
    </div>`;
}

// Estadísticas accionables de la cola -- las 6 que pide Sprint UX 3.1,
// todas calculadas desde las mismas listas ya cargadas, sin round-trips
// nuevos al backend. No incluye "tiempo promedio de publicación": el
// dominio solo guarda fecha_recepcion (cuándo llegó la solicitud), no
// cuándo se publicó realmente -- inventar esa métrica con el dato
// equivocado sería más engañoso que no mostrarla.
function renderMetricasSolicitudes(pendientes, publicadas) {
  const hoyStr = fechaNegocioISO();
  const pautaDe = (s) => (s.pauta_id ? pautasById.get(s.pauta_id) : null);

  const premiumPendientes = pendientes.filter((s) => {
    const pauta = pautaDe(s);
    return pauta && esClientePremium(pauta.client_id);
  }).length;

  const valorPendiente = pendientes.reduce((acc, s) => {
    const pauta = pautaDe(s);
    return acc + (pauta ? Number(pauta.peso_comercial) : 0);
  }, 0);

  const horasPendientes = pendientes.map((s) => horasEnEspera(s.fecha_recepcion));
  const tiempoPromedio =
    horasPendientes.length > 0
      ? horasPendientes.reduce((acc, h) => acc + h, 0) / horasPendientes.length
      : 0;

  const criticas = pendientes.filter(
    (s) => scoreSolicitud(s, pautaDe(s), horasEnEspera(s.fecha_recepcion)).emoji === "🔥"
  ).length;

  const datos = {
    pendientes: pendientes.length,
    premiumPendientes,
    publicadasHoy: publicadas.filter((s) => fechaNegocioISO(s.fecha_recepcion) === hoyStr).length,
    valorPendiente,
    tiempoPromedio: pendientes.length > 0 ? formatHoras(tiempoPromedio).replace("hace ", "") : "—",
    criticas,
  };
  const campos = [
    ["pendientes", "Pendientes", "icon-inbox", false],
    ["premiumPendientes", "Premium pendientes", "icon-target", false],
    ["publicadasHoy", "Publicadas hoy", "icon-check", false],
    ["valorPendiente", "Valor pendiente por publicar", "icon-money", true],
    ["tiempoPromedio", "Espera promedio", "icon-clock", false],
    ["criticas", "Críticas", "icon-alert", false],
  ];
  renderStatRow("solicitudes-metricas", campos, datos);
}

// ---------- Actividad reciente (panel derecho del Inbox) ----------
//
// Mezcla tres fuentes que ya están en memoria -- publicaciones recientes,
// solicitudes recién recibidas, pautas recién registradas -- en un único
// timeline ordenado por fecha. Se recalcula en cada refresco (ver
// setupRefrescoAutomatico), lo que le da sensación de "en vivo" sin
// necesitar websockets, mismo mecanismo que ya usa el resto de la app.
const ACTIVIDAD_RECIENTE_LIMITE = 25;

function renderActividadReciente() {
  const el = document.getElementById("actividad-reciente");
  if (!el) return;

  const eventos = [];
  for (const s of solicitudesPublicadasTodas) {
    const pauta = s.pauta_id ? pautasById.get(s.pauta_id) : null;
    const cliente = pauta ? clientsById.get(pauta.client_id) : null;
    eventos.push({
      fecha: s.fecha_recepcion,
      texto: `✅ Se publicó ${cliente ? cliente.nombre : "(cliente desconocido)"}`,
    });
  }
  for (const s of solicitudesPendientesTodas) {
    const pauta = s.pauta_id ? pautasById.get(s.pauta_id) : null;
    const cliente = pauta ? clientsById.get(pauta.client_id) : null;
    eventos.push({
      fecha: s.fecha_recepcion,
      texto: `➕ Nueva solicitud${cliente ? ` de ${cliente.nombre}` : ""}`,
    });
  }
  for (const pauta of pautasById.values()) {
    const cliente = clientsById.get(pauta.client_id);
    eventos.push({
      fecha: pauta.fecha_registro || pauta.fecha_inicio,
      texto: `🟠 Pauta registrada${cliente ? ` — ${cliente.nombre}` : ""}`,
    });
  }

  eventos.sort((a, b) => String(b.fecha).localeCompare(String(a.fecha)));
  const recientes = eventos.slice(0, ACTIVIDAD_RECIENTE_LIMITE);

  el.innerHTML = recientes.length
    ? recientes
        .map(
          (e) => `
        <div class="timeline-item">
          <div class="timeline-item-date">${formatHoras(horasEnEspera(e.fecha))}</div>
          <div class="timeline-item-text">${e.texto}</div>
        </div>`
        )
        .join("")
    : renderEmptyState("🕐", "Sin actividad todavía.", true);
}

// Re-renderiza solo la columna de pendientes desde el estado ya cargado en
// memoria (solicitudesPendientesTodas) -- usado al entrar/salir de modo
// edición, donde no hace falta pedirle nada nuevo al backend.
function renderKanbanPendientesColumn() {
  const pendEl = document.getElementById("kanban-pendientes");
  pendEl.innerHTML = solicitudesPendientesTodas.length
    ? solicitudesPendientesTodas.map((s) => renderKanbanCard(s, false)).join("")
    : renderEmptyState("✅", "No tienes solicitudes pendientes.");

  for (const btn of pendEl.querySelectorAll(".btn-publicar")) {
    btn.addEventListener("click", () => publicarSolicitud(btn.dataset.id));
  }
  for (const btn of pendEl.querySelectorAll(".btn-vincular")) {
    btn.addEventListener("click", () => {
      const select = pendEl.querySelector(`.link-pauta-select[data-id="${btn.dataset.id}"]`);
      vincularPauta(btn.dataset.id, select.value);
    });
  }
  for (const btn of pendEl.querySelectorAll(".btn-editar")) {
    btn.addEventListener("click", () => {
      editingSolicitudId = btn.dataset.id;
      renderKanbanPendientesColumn();
      pendEl.querySelector(".kanban-card-edit-texto")?.focus();
    });
  }
  for (const btn of pendEl.querySelectorAll(".btn-cancelar-edicion")) {
    btn.addEventListener("click", () => {
      editingSolicitudId = null;
      renderKanbanPendientesColumn();
    });
  }
  for (const form of pendEl.querySelectorAll(".kanban-card-edit-form")) {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      guardarEdicionSolicitud(
        form.dataset.id,
        form.querySelector(".kanban-card-edit-texto").value,
        form.querySelector(".kanban-card-edit-prioridad").checked
      );
    });
  }
}

async function guardarEdicionSolicitud(id, texto, prioridadManual) {
  try {
    await apiFetch(`/publication-requests/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texto, prioridad_manual: prioridadManual }),
    });
    showStatus("Solicitud actualizada.", false);
    editingSolicitudId = null;
    await loadSolicitudes();
  } catch (error) {
    showStatus(error.message, true);
  }
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

  renderKanbanPendientesColumn();

  const pubEl = document.getElementById("kanban-publicadas");
  pubEl.innerHTML = publicadasRecientes.length
    ? publicadasRecientes.map((s) => renderKanbanCard(s, true)).join("")
    : renderEmptyState("📭", "Todavía no hay publicaciones.");

  renderActividadReciente();
}

async function publicarSolicitud(id) {
  try {
    await apiFetch(`/publication-requests/${id}/publish`, { method: "POST" });
    showStatus("Solicitud publicada.", false);
    await Promise.all([loadSolicitudes(), loadClientesYPautas(), loadDashboard(), loadAlertas()]);
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
  ["ingreso_contratado_activo", "Ingresos año actual", "icon-money", true],
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

// ---------- Radar de Renovaciones (pestaña Alertas) ----------
//
// Solo clientes activos (vigente=true) con un paquete de tiempo (no
// Individual — un cliente Individual no "renueva", ver
// AnalyticsService.clientes_con_contrato_por_renovar), agrupados por qué
// tan cerca está su vencimiento. Nunca muestra vencidos.

const RENEWAL_BUCKETS = [
  { limite: 7, titulo: "Vence en 7 días", emoji: "🔴" },
  { limite: 15, titulo: "Vence en 15 días", emoji: "🟠" },
  { limite: 30, titulo: "Vence en 30 días", emoji: "🟢" },
];

// wa.me no acepta espacios/guiones/paréntesis en el teléfono -- se limpia
// aquí en vez de pedirle al operador que lo capture ya limpio.
function renderContactarBoton(cliente) {
  const telefono = (cliente.telefono || "").replace(/[^\d]/g, "");
  if (!telefono) return "";
  return `<a class="btn btn-primary" href="https://wa.me/${telefono}" target="_blank" rel="noopener">
    <svg class="icon"><use href="#icon-phone"></use></svg>Contactar
  </a>`;
}

function renderRenewalCard(item, dias) {
  return `
    <div class="renewal-card">
      <div class="renewal-card-name">${item.cliente.nombre}</div>
      <div class="renewal-card-meta">
        ${PAUTA_TIPO_LABELS[item.tipo] ?? item.tipo} · vence ${formatFecha(item.fecha_vencimiento)} (${dias} día${dias === 1 ? "" : "s"})
      </div>
      <div class="renewal-card-actions">
        <button type="button" class="btn btn-secondary" data-ficha-cliente="${item.cliente.id}">
          <svg class="icon"><use href="#icon-detail"></use></svg>Ver cliente
        </button>
        <button type="button" class="btn btn-primary" data-open-drawer="drawer-pauta" data-preselect-client="${item.cliente.id}">
          <svg class="icon"><use href="#icon-refresh"></use></svg>Renovar
        </button>
        ${renderContactarBoton(item.cliente)}
      </div>
    </div>`;
}

// Agrupa en los mismos 3 buckets tanto el resumen de conteos (arriba) como
// las tarjetas detalladas (abajo) -- una sola partición, nunca dos cálculos
// que puedan desincronizarse entre el número grande y las tarjetas.
function computarRadarBuckets(ranking) {
  const candidatos = ranking
    .filter((item) => item.vigente && item.tipo !== "individual")
    .map((item) => ({ item, dias: diasHasta(item.fecha_vencimiento) }))
    .filter(({ dias }) => dias >= 0 && dias <= 30)
    .sort((a, b) => a.dias - b.dias);

  let restantes = candidatos;
  return RENEWAL_BUCKETS.map(({ limite, titulo, emoji }) => {
    const items = restantes.filter(({ dias }) => dias <= limite);
    restantes = restantes.filter(({ dias }) => dias > limite);
    return { titulo, emoji, items };
  });
}

function renderRadarResumen(buckets) {
  document.getElementById("radar-resumen").innerHTML = buckets
    .map(({ emoji, items, titulo }) => renderStatCard(null, items.length, titulo, emoji))
    .join("");
}

function renderRadarRenovaciones(buckets) {
  const el = document.getElementById("radar-renovaciones");
  const total = buckets.reduce((acc, b) => acc + b.items.length, 0);
  if (total === 0) {
    el.innerHTML = renderEmptyState("📅", "No hay renovaciones programadas por ahora.");
    return;
  }
  el.innerHTML = buckets
    .map(({ titulo, items }) => {
      const cuerpo = items.length
        ? items.map(({ item, dias }) => renderRenewalCard(item, dias)).join("")
        : '<p class="renewal-empty">Sin renovaciones en este rango.</p>';
      return `
      <div>
        <h3 class="renewal-group-title">${titulo}</h3>
        <div class="renewal-cards">${cuerpo}</div>
      </div>`;
    })
    .join("");
}

// Categorías comerciales — oportunidades de venta/renovación, no urgencias.
const ALERTAS_OPORTUNIDAD = [
  {
    id: "individuales",
    campo: "clientes_individuales_pendientes",
    icon: "icon-inbox",
    severity: "neutral",
    label: "publicaciones individuales pendientes",
  },
  {
    id: "renovar",
    campo: "clientes_contrato_por_renovar",
    icon: "icon-refresh",
    severity: "neutral",
    label: "contratos próximos a renovar",
  },
  {
    id: "sin-usar",
    campo: "clientes_publicaciones_sin_usar",
    icon: "icon-money",
    severity: "neutral",
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

// `emoji` reemplaza el ícono SVG por un emoji de severidad (🔴/🟠/🟢) --
// usado por el resumen del Radar de Renovaciones, donde el color importa
// más que el ícono.
function renderStatCard(icon, valor, label, emoji) {
  const iconoHtml = emoji
    ? `<span class="stat-card-icon stat-card-icon-emoji">${emoji}</span>`
    : `<span class="stat-card-icon"><svg class="icon"><use href="#${icon}"></use></svg></span>`;
  return `
    <div class="stat-card">
      ${iconoHtml}
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

function renderAlertCard(config, items) {
  const count = items.length;
  const detalle =
    count === 0
      ? '<p class="muted">Sin novedades.</p>'
      : items.map((item) => `<div class="alert-detail-item">${item.nombre}</div>`).join("");

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

// Si ninguna categoría tiene nada que mostrar, una fila de tarjetas todas
// en "0" es ruido -- un solo mensaje amigable dice lo mismo mejor.
function renderAlertGrid(elementId, categorias, alertas, mensajeVacio) {
  const totalItems = categorias.reduce((acc, cfg) => acc + alertas[cfg.campo].length, 0);
  const el = document.getElementById(elementId);
  el.innerHTML =
    totalItems === 0
      ? renderEmptyState("✅", mensajeVacio)
      : categorias.map((cfg) => renderAlertCard(cfg, alertas[cfg.campo])).join("");
}

// Las 4 categorías "generales" que ya existían (Sprint 4B) -- las 5
// finas basadas en patrones de compra (racha, tipo habitual, etc.) viven
// en renderOportunidadesPatrones, con datos de /insights/oportunidades.
function renderOportunidadesGenerales(alertas) {
  renderAlertGrid(
    "alertas-oportunidades-generales",
    ALERTAS_OPORTUNIDAD,
    alertas,
    "No hay oportunidades comerciales identificadas por ahora."
  );
}

// ---------- Solicitudes pendientes (resumen en el Dashboard) ----------
//
// Mismo dato que ya se ve en la pestaña Solicitudes (resumen.solicitudes_
// pendientes, alertas.solicitudes_antiguas) -- esto solo lo resume para
// que el flujo de lectura del Dashboard no obligue a cambiar de pestaña
// para saber si hay algo esperando.

function renderDashboardSolicitudes(resumen, alertas) {
  const el = document.getElementById("dashboard-solicitudes-resumen");
  const pendientes = resumen.solicitudes_pendientes;

  if (pendientes === 0) {
    el.innerHTML = renderEmptyState("✅", "No tienes solicitudes pendientes.");
    return;
  }

  const antiguas = alertas.solicitudes_antiguas.length;
  el.innerHTML = `
    <div class="dash-inbox-summary">
      <div class="dash-inbox-summary-main">
        <span class="dash-inbox-count">${pendientes}</span>
        <span class="dash-inbox-label">solicitud${pendientes === 1 ? "" : "es"} pendiente${pendientes === 1 ? "" : "s"}</span>
      </div>
      ${antiguas > 0 ? `<p class="dash-inbox-warning">🔴 ${antiguas} lleva${antiguas === 1 ? "" : "n"} más de 4h esperando respuesta</p>` : ""}
      <button type="button" class="btn btn-primary" data-go-tab="solicitudes">
        <svg class="icon"><use href="#icon-inbox"></use></svg>Ir a solicitudes
      </button>
    </div>`;
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
  renderDashboardSolicitudes(resumen, alertas);
  renderMetricasPrincipales(resumen);
  renderStatRow("dashboard-actividad", DASHBOARD_ACTIVIDAD, resumen);
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

// ---------- Centro de Decisión (pestaña Alertas, Sprint 5A) ----------
//
// A diferencia del Dashboard, estas listas SÍ vienen ya priorizadas y
// redactadas por el backend (core.analytics.DecisionEngineService) --
// severidad, mensaje y acción sugerida son decisiones de negocio del
// motor, no de esta pantalla. Lo único que se calcula aquí es el Radar de
// Renovaciones (ver arriba), que sigue reutilizando /dashboard/ranking.

const ALERTA_SEVERIDAD_CSS = { critica: "danger", atencion: "warning", informativa: "success" };
const ALERTA_SEVERIDAD_EMOJI = { critica: "🔴", atencion: "🟠", informativa: "🟢" };

function renderAlertaInteligenteBotones(item) {
  let botones = "";
  if (item.cliente) {
    botones += `<button type="button" class="btn btn-secondary" data-ficha-cliente="${item.cliente.id}"><svg class="icon"><use href="#icon-detail"></use></svg>Ver cliente</button>`;
  }
  if (item.accion === "renovar" && item.cliente) {
    botones += `<button type="button" class="btn btn-primary" data-open-drawer="drawer-pauta" data-preselect-client="${item.cliente.id}"><svg class="icon"><use href="#icon-refresh"></use></svg>Renovar</button>`;
  } else if (item.accion === "reactivar" && item.cliente) {
    botones += `<button type="button" class="btn btn-primary" data-open-drawer="drawer-pauta" data-preselect-client="${item.cliente.id}"><svg class="icon"><use href="#icon-plus"></use></svg>Reactivar</button>`;
  } else if (item.accion === "contactar" && item.cliente) {
    botones += renderContactarBoton(item.cliente);
  } else if (item.accion === "ver_solicitudes") {
    botones += `<button type="button" class="btn btn-secondary" data-go-tab="solicitudes"><svg class="icon"><use href="#icon-detail"></use></svg>Ver</button>`;
  }
  return botones;
}

function renderCentroAlertas(alertas) {
  const el = document.getElementById("alertas-centro");
  if (alertas.length === 0) {
    el.innerHTML = renderEmptyState("✅", "Sin pendientes urgentes — todo al día.");
    return;
  }
  el.innerHTML = alertas
    .map(
      (item) => `
        <div class="action-item" data-severity="${ALERTA_SEVERIDAD_CSS[item.severidad] ?? "warning"}">
          <span class="action-item-emoji">${ALERTA_SEVERIDAD_EMOJI[item.severidad] ?? "⚪"}</span>
          <span class="action-item-text">${item.mensaje}</span>
          <span class="action-item-actions">${renderAlertaInteligenteBotones(item)}</span>
        </div>`
    )
    .join("");
}

function renderRiesgoAbandono(items) {
  const el = document.getElementById("alertas-riesgo-abandono");
  if (items.length === 0) {
    el.innerHTML = renderEmptyState("✅", "Ningún cliente vigente lleva demasiado tiempo en silencio.");
    return;
  }
  el.innerHTML = items
    .map(
      (item) => `
        <div class="action-item" data-severity="danger">
          <span class="action-item-emoji">⚠️</span>
          <span class="action-item-text">
            ${item.cliente.nombre}: hace ${item.dias_sin_actividad} días no envía material.
            Tiene ${item.publicaciones_restantes} publicaciones disponibles.
          </span>
          <span class="action-item-actions">
            <button type="button" class="btn btn-secondary" data-ficha-cliente="${item.cliente.id}"><svg class="icon"><use href="#icon-detail"></use></svg>Ver cliente</button>
            ${renderContactarBoton(item.cliente)}
          </span>
        </div>`
    )
    .join("");
}

function renderDormidos(items) {
  const el = document.getElementById("alertas-dormidos");
  if (items.length === 0) {
    el.innerHTML = renderEmptyState("✅", "No hay clientes dormidos por ahora.");
    return;
  }
  el.innerHTML = items
    .map(
      (item) => `
        <div class="action-item" data-severity="warning">
          <span class="action-item-emoji">💤</span>
          <span class="action-item-text">
            ${item.cliente.nombre}: hace ${item.dias_sin_actividad} días sin actividad.
            Último contrato ${PAUTA_TIPO_LABELS[item.ultimo_contrato_tipo] ?? item.ultimo_contrato_tipo},
            venció ${formatFecha(item.ultimo_contrato_fecha_fin)}.
          </span>
          <span class="action-item-actions">
            <button type="button" class="btn btn-secondary" data-ficha-cliente="${item.cliente.id}"><svg class="icon"><use href="#icon-detail"></use></svg>Ver cliente</button>
            <button type="button" class="btn btn-primary" data-open-drawer="drawer-pauta" data-preselect-client="${item.cliente.id}"><svg class="icon"><use href="#icon-plus"></use></svg>Reactivar</button>
          </span>
        </div>`
    )
    .join("");
}

// Cortes de estrellas/nivel definidos por DecisionEngineService.score_salud_cliente
// -- este mapa solo traduce el nivel (enum) a una frase para pantalla, la
// misma convención que ESTADO_COMERCIAL_LABELS/PAUTA_TIPO_LABELS.
const NIVEL_SALUD_LABELS = {
  excelente: "Cliente saludable",
  bueno: "Sin riesgo inminente",
  regular: "Atención recomendada",
  riesgo: "Riesgo de perder renovación",
  critico: "Riesgo alto — contactar ya",
};

function renderEstrellas(n) {
  return "★".repeat(n) + "☆".repeat(5 - n);
}

function renderSaludClientes(items) {
  const el = document.getElementById("alertas-salud");
  if (items.length === 0) {
    el.innerHTML = renderEmptyState("✅", "Ningún cliente con pautas todavía.");
    return;
  }
  el.innerHTML = items
    .map(
      (item) => `
        <div class="health-card" data-ficha-cliente="${item.cliente.id}">
          <div class="health-card-header">
            <h3>${item.cliente.nombre}</h3>
            <span class="badge badge-${item.nivel}">${NIVEL_SALUD_LABELS[item.nivel] ?? item.nivel}</span>
          </div>
          <div class="health-card-stars">${renderEstrellas(item.estrellas)}</div>
          <div class="health-card-score">${item.score}%</div>
        </div>`
    )
    .join("");
}

// Los patrones fine-grained ya vienen con `mensaje` redactado por el
// backend (core.analytics.DecisionEngineService.oportunidades_comerciales)
// -- esta pantalla no arma texto, solo lo muestra con acción "Ver cliente".
function renderOportunidadesPatrones(items) {
  const el = document.getElementById("alertas-oportunidades-patrones");
  if (items.length === 0) {
    el.innerHTML = renderEmptyState("✅", "No se detectaron patrones de compra por ahora.");
    return;
  }
  el.innerHTML = items
    .map(
      (item) => `
        <div class="action-item" data-severity="success">
          <span class="action-item-emoji">💡</span>
          <span class="action-item-text">${item.mensaje}</span>
          <span class="action-item-actions">
            <button type="button" class="btn btn-secondary" data-ficha-cliente="${item.cliente.id}"><svg class="icon"><use href="#icon-detail"></use></svg>Ver cliente</button>
          </span>
        </div>`
    )
    .join("");
}

async function loadAlertas() {
  const [centroAlertas, riesgoAbandono, dormidos, saludClientes, oportunidades, alertas, ranking] =
    await Promise.all([
      apiFetch("/insights/centro-alertas"),
      apiFetch("/insights/riesgo-abandono"),
      apiFetch("/insights/dormidos"),
      apiFetch("/insights/salud-clientes"),
      apiFetch("/insights/oportunidades"),
      apiFetch("/dashboard/alertas"),
      apiFetch("/dashboard/ranking"),
    ]);
  renderCentroAlertas(centroAlertas);
  const buckets = computarRadarBuckets(ranking);
  renderRadarResumen(buckets);
  renderRadarRenovaciones(buckets);
  renderRiesgoAbandono(riesgoAbandono);
  renderDormidos(dormidos);
  renderSaludClientes(saludClientes);
  renderOportunidadesGenerales(alertas);
  renderOportunidadesPatrones(oportunidades);
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

// Tarjeta lateral con el estado del contrato apenas se elige una pauta —
// "¿debo publicar o hablar de renovación?" sin abrir nada más (Sprint UX
// 3.1). Todo desde datos ya cargados (pautasById, solicitudesPublicadasTodas).
function renderContratoPreview(pautaId) {
  const el = document.getElementById("solicitud-contrato-preview");
  const pauta = pautaId ? pautasById.get(pautaId) : null;
  if (!pauta) {
    el.hidden = true;
    el.innerHTML = "";
    return;
  }
  const cliente = clientsById.get(pauta.client_id);
  const ultimaPublicacion = solicitudesPublicadasTodas
    .filter((s) => s.pauta_id && pautasById.get(s.pauta_id)?.client_id === pauta.client_id)
    .sort((a, b) => b.fecha_recepcion.localeCompare(a.fecha_recepcion))[0];

  el.innerHTML = `
    <span class="contract-preview-name">${cliente ? cliente.nombre : "(cliente desconocido)"}</span>
    <div class="contract-preview-stats">
      <div class="contract-preview-stat">
        <span class="contract-preview-stat-label">Plan</span>
        <span class="contract-preview-stat-value">${PAUTA_TIPO_LABELS[pauta.tipo] ?? pauta.tipo}</span>
      </div>
      <div class="contract-preview-stat">
        <span class="contract-preview-stat-label">Restantes</span>
        <span class="contract-preview-stat-value">${pauta.publicaciones_restantes} de ${pauta.publicaciones_contratadas}</span>
      </div>
      <div class="contract-preview-stat">
        <span class="contract-preview-stat-label">Vence</span>
        <span class="contract-preview-stat-value">${formatFecha(pauta.fecha_fin)}</span>
      </div>
      <div class="contract-preview-stat">
        <span class="contract-preview-stat-label">Valor contratado</span>
        <span class="contract-preview-stat-value">${formatMoneda(pauta.valor_pagado)}</span>
      </div>
      <div class="contract-preview-stat">
        <span class="contract-preview-stat-label">Peso comercial</span>
        <span class="contract-preview-stat-value">${formatMoneda(pauta.peso_comercial)}</span>
      </div>
      <div class="contract-preview-stat">
        <span class="contract-preview-stat-label">Última publicación</span>
        <span class="contract-preview-stat-value">${ultimaPublicacion ? formatHoras(horasEnEspera(ultimaPublicacion.fecha_recepcion)) : "Sin publicaciones todavía"}</span>
      </div>
    </div>`;
  el.hidden = false;
}

function setupFormSolicitud() {
  document.getElementById("solicitud-pauta").addEventListener("change", (event) => {
    renderContratoPreview(event.target.value);
  });

  // Ctrl/Cmd+Enter envía -- Enter solo hace salto de línea, para no
  // publicar una solicitud a medio escribir por accidente (confirmado con
  // el negocio, Sprint UX 3.1).
  document.getElementById("solicitud-texto").addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      document.getElementById("form-solicitud").requestSubmit();
    }
  });

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
      renderContratoPreview(null);
      await loadSolicitudes();
    } catch (error) {
      showStatus(error.message, true);
    }
  });
}

// Los botones "Crear"/"Guardar" comparten un único <svg><use> fijo en el
// HTML -- lo reapuntamos en vez de reescribir el botón entero, porque
// `.textContent = ...` habría borrado el ícono junto con la etiqueta.
function setIconUse(iconEl, symbolId) {
  iconEl.querySelector("use").setAttribute("href", `#${symbolId}`);
}

function resetFormClienteDrawer() {
  editingClientId = null;
  document.getElementById("drawer-cliente-titulo").textContent = "Nuevo cliente";
  document.getElementById("form-cliente-submit-label").textContent = "Crear cliente";
  setIconUse(document.getElementById("form-cliente-submit-icon"), "icon-plus");
  document.getElementById("form-cliente").reset();
}

function startEditCliente(clientId) {
  const cliente = clientsById.get(clientId);
  if (!cliente) return;
  editingClientId = clientId;
  document.getElementById("drawer-cliente-titulo").textContent = "Editar cliente";
  document.getElementById("form-cliente-submit-label").textContent = "Guardar cambios";
  setIconUse(document.getElementById("form-cliente-submit-icon"), "icon-check");
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
      await loadAlertas();
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
  return Promise.all([loadClientesYPautas(), loadSolicitudes(), loadDashboard(), loadAlertas()]);
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

// Atajos de teclado del Inbox Editorial (Sprint UX 3.1). Se ignoran
// mientras se escribe en un campo -- salvo Ctrl/Cmd+Enter, que ya tiene su
// propio listener en el textarea -- para no interceptar teclas normales
// mientras alguien redacta el texto de una publicación.
function setupAtajosTeclado() {
  document.addEventListener("keydown", (event) => {
    const enCampoDeTexto = ["INPUT", "TEXTAREA", "SELECT"].includes(event.target.tagName);

    if (event.key === "/" && !enCampoDeTexto) {
      event.preventDefault();
      document.getElementById("buscador-global").focus();
      return;
    }

    if (enCampoDeTexto) return;
    const enSolicitudes = document.getElementById("tab-solicitudes").classList.contains("active");
    if (!enSolicitudes) return;

    if (event.key === "n" || event.key === "N") {
      event.preventDefault();
      document.getElementById("solicitud-texto").focus();
    } else if (event.key === "p" || event.key === "P") {
      event.preventDefault();
      const primera = solicitudesPendientesTodas[0];
      if (!primera) return;
      if (primera.pauta_id) {
        publicarSolicitud(primera.id);
      } else {
        showStatus("La primera solicitud de la cola todavía no tiene pauta vinculada.", true);
      }
    }
  });
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
  setupAtajosTeclado();
  renderSelectPlanes();
  document.getElementById("refrescar-solicitudes").addEventListener("click", loadSolicitudes);
  document.getElementById("refrescar-clientes").addEventListener("click", loadClientesYPautas);
  document.getElementById("refrescar-dashboard").addEventListener("click", loadDashboard);
  document.getElementById("refrescar-alertas").addEventListener("click", loadAlertas);
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
    await loadAlertas();
  } catch (error) {
    showStatus(error.message, true);
  }
}

init();
