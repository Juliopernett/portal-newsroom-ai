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
let editingPautaId = null;
let editingGastoId = null;
let gastosFiltro = "";
let gastosTodas = [];
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

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
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
      await loadGastos();
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
  gastos: "Gastos",
  reportes: "Reportes",
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
    const reporteToggleBtn = event.target.closest("[data-reporte-toggle]");
    if (reporteToggleBtn) {
      toggleReportePanel(reporteToggleBtn.dataset.reporteToggle);
      return;
    }
    const copiarReporteBtn = event.target.closest("[data-copiar-reporte]");
    if (copiarReporteBtn) {
      copiarReporte(copiarReporteBtn.dataset.copiarReporte);
      return;
    }
    const mediaToggleBtn = event.target.closest("[data-media-toggle]");
    if (mediaToggleBtn) {
      toggleMediaPanel(mediaToggleBtn.dataset.mediaToggle);
      return;
    }
    const subirMediaBtn = event.target.closest(".btn-subir-media");
    if (subirMediaBtn) {
      const input = document.querySelector(
        `.media-file-input[data-id="${subirMediaBtn.dataset.id}"]`
      );
      subirMedia(subirMediaBtn.dataset.id, input ? input.files[0] : null);
      return;
    }
    const eliminarMediaBtn = event.target.closest(".btn-eliminar-media");
    if (eliminarMediaBtn) {
      eliminarMedia(eliminarMediaBtn.dataset.id, eliminarMediaBtn.dataset.mediaId);
      return;
    }
    const eliminarGastoBtn = event.target.closest("[data-eliminar-gasto]");
    if (eliminarGastoBtn) {
      eliminarGasto(eliminarGastoBtn.dataset.eliminarGasto);
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
      } else if (openBtn.dataset.editPauta) {
        startEditPauta(openBtn.dataset.editPauta);
      } else if (openBtn.dataset.editGasto) {
        startEditGasto(openBtn.dataset.editGasto);
      } else if (openBtn.dataset.openDrawer === "drawer-cliente") {
        resetFormClienteDrawer();
      } else if (openBtn.dataset.openDrawer === "drawer-gasto") {
        resetFormGastoDrawer();
      } else if (openBtn.dataset.openDrawer === "drawer-pauta") {
        resetFormPautaDrawer();
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

// Preserva la pauta seleccionada al reconstruir el <select> -- si no se
// restaura, el refresco automático cada 30s (ver setupRefrescoAutomatico)
// vacía la selección mientras el usuario todavía está redactando el texto
// de la solicitud, y esta se guarda desvinculada sin que nadie lo note
// (bug real reportado por el usuario, 2026-08-14).
function renderSelectPautas() {
  const select = document.getElementById("solicitud-pauta");
  const previousValue = select.value;
  const placeholder = select.querySelector('option[value=""]');
  select.innerHTML = "";
  select.appendChild(placeholder);
  select.insertAdjacentHTML("beforeend", pautaOptionsHtml(pautasParaSolicitud()));
  if (previousValue && select.querySelector(`option[value="${previousValue}"]`)) {
    select.value = previousValue;
  }
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

// Mismo patrón que renderEditClienteButton -- corrige un dato de una Pauta
// ya registrada (fecha_fin equivocada, monto mal digitado, etc.) sin tener
// que borrar y recrearla. Antes de esto no había forma de corregir un
// error así salvo editando la base de datos a mano (caso real, 2026-08-14:
// una Pauta de 4 publicaciones quedó con fecha_fin 2026-08-14 en vez de
// 2026-09-13).
function renderEditPautaButton(pautaId) {
  return `
    <button type="button" class="btn-link" data-open-drawer="drawer-pauta" data-edit-pauta="${pautaId}">
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
        ${renderEditPautaButton(pauta.id)}
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
        ${renderEditPautaButton(pauta.id)}
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
    : renderEmptyState(
        "📄",
        contratosFiltro.trim() ? "No se encontraron contratos con ese criterio." : "No hay contratos vigentes en este momento."
      );
}

// ---------- Gastos ----------
//
// Alimenta el reporte de rentabilidad mensual del Dashboard (ingresos -
// gastos, ver core.analytics.rentabilidad_service) -- sin agrupar por
// categoría ni recurrencia porque el dato real que maneja el negocio hoy
// (una lista de "PAGOS" en Excel/WhatsApp) es solo descripción + valor +
// fecha, igual que core.entities.gasto.Gasto.

async function loadGastos() {
  gastosTodas = await apiFetch("/gastos");
  renderListaGastos();
}

function gastosFiltrados() {
  const termino = gastosFiltro.trim().toLowerCase();
  const ordenados = [...gastosTodas].sort((a, b) => b.fecha.localeCompare(a.fecha));
  if (!termino) return ordenados;
  return ordenados.filter((g) => g.descripcion.toLowerCase().includes(termino));
}

function renderGastoRow(gasto) {
  return `
    <div class="gasto-row">
      <span class="gasto-row-descripcion">${gasto.descripcion}</span>
      <span class="gasto-row-fecha">${formatFecha(gasto.fecha)}</span>
      <span class="gasto-row-valor">${formatMoneda(gasto.valor)}</span>
      <span class="gasto-row-actions">
        <button type="button" class="btn-link" data-open-drawer="drawer-gasto" data-edit-gasto="${gasto.id}">
          <svg class="icon"><use href="#icon-edit"></use></svg>Editar
        </button>
        <button type="button" class="btn-link" data-eliminar-gasto="${gasto.id}">
          <svg class="icon"><use href="#icon-close"></use></svg>Eliminar
        </button>
      </span>
    </div>`;
}

function renderListaGastos() {
  const el = document.getElementById("lista-gastos");
  if (!el) return;
  const gastos = gastosFiltrados();
  el.innerHTML = gastos.length
    ? gastos.map(renderGastoRow).join("")
    : renderEmptyState("💵", gastosFiltro.trim() ? "No se encontraron gastos con ese criterio." : "Todavía no hay gastos registrados.");
}

async function eliminarGasto(id) {
  try {
    await apiFetch(`/gastos/${id}`, { method: "DELETE" });
    showStatus("Gasto eliminado.", false);
    await Promise.all([loadGastos(), loadDashboard()]);
  } catch (error) {
    showStatus(error.message, true);
  }
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

// ---------- Solicitudes: Destinos multicanal (Sprint 4A, Incremento 5) ----------
// El picker de canales se limita a los tres ya automatizados/soportados
// (WordPress crea borrador solo; Facebook/Instagram registran enlace a
// mano) -- TikTok/YouTube ya existen en el modelo (CanalPublicacion) pero
// deliberadamente no aparecen acá todavía, a pedido explícito del negocio.
const CANALES_DESTINO = [
  { value: "wordpress", label: "WordPress" },
  { value: "facebook", label: "Facebook" },
  { value: "instagram", label: "Instagram" },
];

const DESTINO_ESTADO_LABELS = {
  pendiente: "Pendiente",
  publicado: "Publicado",
  fallido: "Falló",
  cancelado: "Cancelado",
};

const DESTINO_ESTADO_BADGE = {
  pendiente: "badge-neutral",
  publicado: "badge-saludable",
  fallido: "badge-critico",
  cancelado: "badge-neutral",
};

// Qué tarjeta tiene el panel de destinos abierto (una a la vez, mismo
// patrón que editingSolicitudId) y una cache por solicitud para no volver
// a pedir la lista al backend en cada re-render de la columna.
let destinosAbiertoId = null;
const destinosCache = new Map();

// Sprint 4A, Incremento 6 (Reportes automáticos): mismo patrón de
// abierto/cache que destinosAbiertoId/destinosCache, pero independiente --
// una tarjeta puede tener el panel de destinos y el de reporte abiertos a
// la vez, son cosas distintas. Disponible en ambas columnas (pendientes y
// publicadas), por eso su wiring vive en el click delegado en document
// (setupGlobalClicks), no en el querySelectorAll por columna que usan los
// botones de destinos.
let reporteAbiertoId = null;
const reporteCache = new Map();

// Sprint 4A, Incremento 7 (MediaAsset): mismo patrón abierto/cache que
// reporteAbiertoId/reporteCache -- también disponible en ambas columnas
// (revisar qué se adjuntó sigue siendo útil sobre una solicitud ya
// publicada), wiring por click delegado en document.
let mediaAbiertoId = null;
const mediaCache = new Map();

const MEDIA_TIPO_LABELS = { imagen: "Imagen", video: "Video" };

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
        <input type="text" class="kanban-card-edit-titulo" placeholder="Título (opcional)" value="${solicitud.titulo ?? ""}">
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

// Opciones del <select> para agregar un destino nuevo -- excluye canales
// que la solicitud ya tiene (en cualquier estado, incluido cancelado; si
// de verdad hace falta repetir un canal cancelado, no es el caso común
// que esta UI necesita cubrir hoy).
function destinoCanalOptionsHtml(destinosExistentes) {
  const usados = new Set(destinosExistentes.map((d) => d.canal));
  return CANALES_DESTINO.filter((c) => !usados.has(c.value))
    .map((c) => `<option value="${c.value}">${c.label}</option>`)
    .join("");
}

function renderDestinoRow(solicitud, destino) {
  const canalLabel = CANALES_DESTINO.find((c) => c.value === destino.canal)?.label ?? destino.canal;
  const badgeClase = DESTINO_ESTADO_BADGE[destino.estado] ?? "badge-neutral";
  const estadoLabel = DESTINO_ESTADO_LABELS[destino.estado] ?? destino.estado;

  let accionesHtml = "";
  if (destino.estado === "publicado") {
    const url = destino.canal === "wordpress" ? destino.wp_url : destino.url_publicacion;
    accionesHtml = url
      ? `<a class="destino-row-link" href="${url}" target="_blank" rel="noopener">Ver publicación</a>`
      : "";
  } else if (destino.canal === "wordpress") {
    accionesHtml = destino.wp_url
      ? `<a class="destino-row-link" href="${destino.wp_url}" target="_blank" rel="noopener">Ver borrador</a>
         <button type="button" class="btn btn-primary btn-confirmar-destino" data-id="${solicitud.id}" data-destino-id="${destino.id}">
           Confirmar publicado
         </button>`
      : `<button type="button" class="btn btn-secondary btn-crear-borrador" data-id="${solicitud.id}" data-destino-id="${destino.id}">
           Crear borrador
         </button>`;
    if (destino.estado !== "cancelado") {
      accionesHtml += `
         <button type="button" class="btn btn-secondary btn-cancelar-destino" data-id="${solicitud.id}" data-destino-id="${destino.id}">
           Cancelar
         </button>`;
    }
  } else {
    // Facebook / Instagram: sin automatización todavía -- el operador
    // pega el enlace a mano (ver ADR-006).
    accionesHtml = `
         <input type="url" class="destino-row-url" placeholder="Enlace de la publicación" data-destino-id="${destino.id}">
         <button type="button" class="btn btn-primary btn-confirmar-destino" data-id="${solicitud.id}" data-destino-id="${destino.id}">
           Confirmar
         </button>
         <button type="button" class="btn btn-secondary btn-cancelar-destino" data-id="${solicitud.id}" data-destino-id="${destino.id}">
           Cancelar
         </button>`;
  }

  return `
    <div class="destino-row">
      <span class="destino-row-canal">${canalLabel}</span>
      <span class="badge ${badgeClase}">${estadoLabel}</span>
      <div class="destino-row-actions">${accionesHtml}</div>
    </div>`;
}

function renderDestinosPanel(solicitud) {
  const destinos = destinosCache.get(solicitud.id) || [];
  const filasHtml = destinos.length
    ? destinos.map((d) => renderDestinoRow(solicitud, d)).join("")
    : `<p class="destinos-panel-empty">Sin destinos todavía.</p>`;
  const opciones = destinoCanalOptionsHtml(destinos);
  const agregarHtml = opciones
    ? `<div class="destino-row destino-row-agregar">
         <select class="destino-select" data-id="${solicitud.id}">
           <option value="">Agregar destino…</option>
           ${opciones}
         </select>
         <button type="button" class="btn btn-secondary btn-agregar-destino" data-id="${solicitud.id}">
           <svg class="icon"><use href="#icon-plus"></use></svg>Agregar
         </button>
       </div>`
    : "";
  return `<div class="destinos-panel">${filasHtml}${agregarHtml}</div>`;
}

// Texto plano para "Copiar reporte" -- generación automática, envío manual
// (Sprint 4A, Incremento 6): el sistema arma el texto, compartirlo con el
// cliente sigue siendo una acción humana (copiar y pegar en WhatsApp/email,
// no hay integración de envío). Mismos datos que renderReportePanel, en
// formato de texto en vez de HTML.
function formatoReporteTexto(reporte) {
  const lineas = [
    reporte.titulo ? `Reporte: ${reporte.titulo}` : "Reporte de publicación",
    `Cliente: ${reporte.cliente_nombre ?? "(sin vincular)"}`,
    `Estado: ${reporte.completa ? "Completa" : "En curso"}`,
    `Pauta consumida: ${reporte.pauta_consumida ? "Sí" : "No"}`,
    "",
    "Destinos:",
  ];
  if (!reporte.destinos.length) {
    lineas.push("  (sin destinos todavía)");
  }
  for (const destino of reporte.destinos) {
    const canalLabel = CANALES_DESTINO.find((c) => c.value === destino.canal)?.label ?? destino.canal;
    const estadoLabel = DESTINO_ESTADO_LABELS[destino.estado] ?? destino.estado;
    let linea = `  - ${canalLabel}: ${estadoLabel}`;
    if (destino.enlace) linea += ` — ${destino.enlace}`;
    if (destino.fecha_publicacion) linea += ` (${formatFechaHoraNegocio(destino.fecha_publicacion)})`;
    lineas.push(linea);
  }
  return lineas.join("\n");
}

function renderReportePanel(solicitud) {
  const reporte = reporteCache.get(solicitud.id);
  if (!reporte) return "";

  const filasHtml = reporte.destinos.length
    ? reporte.destinos
        .map((destino) => {
          const canalLabel =
            CANALES_DESTINO.find((c) => c.value === destino.canal)?.label ?? destino.canal;
          const badgeClase = DESTINO_ESTADO_BADGE[destino.estado] ?? "badge-neutral";
          const estadoLabel = DESTINO_ESTADO_LABELS[destino.estado] ?? destino.estado;
          const enlaceHtml = destino.enlace
            ? `<a class="destino-row-link" href="${destino.enlace}" target="_blank" rel="noopener">Ver publicación</a>`
            : `<span class="reporte-panel-sin-enlace">Sin enlace todavía</span>`;
          return `
            <div class="destino-row">
              <span class="destino-row-canal">${canalLabel}</span>
              <span class="badge ${badgeClase}">${estadoLabel}</span>
              <div class="destino-row-actions">${enlaceHtml}</div>
            </div>`;
        })
        .join("")
    : `<p class="destinos-panel-empty">Sin destinos todavía.</p>`;

  return `
    <div class="reporte-panel">
      <p class="reporte-panel-linea"><strong>Cliente:</strong> ${reporte.cliente_nombre ?? "(sin vincular)"}</p>
      <p class="reporte-panel-linea"><strong>Pauta consumida:</strong> ${reporte.pauta_consumida ? "Sí" : "No"}</p>
      ${filasHtml}
      <button type="button" class="btn btn-secondary btn-copiar-reporte" data-copiar-reporte="${solicitud.id}">
        <svg class="icon"><use href="#icon-detail"></use></svg>Copiar reporte
      </button>
    </div>`;
}

function renderMediaRow(solicitud, media) {
  const tipoLabel = MEDIA_TIPO_LABELS[media.tipo] ?? media.tipo;
  const href = `/publication-requests/${solicitud.id}/media/${media.id}/contenido`;
  return `
    <div class="destino-row">
      <span class="destino-row-canal">${tipoLabel}</span>
      <span class="media-row-nombre">${media.nombre_archivo}</span>
      <span class="media-row-tamano">${formatBytes(media.tamano_bytes)}</span>
      <div class="destino-row-actions">
        <a class="destino-row-link" href="${href}" target="_blank" rel="noopener">Ver</a>
        <button type="button" class="btn btn-secondary btn-eliminar-media" data-id="${solicitud.id}" data-media-id="${media.id}">
          Eliminar
        </button>
      </div>
    </div>`;
}

// Sin formulario de subir una vez la solicitud está completa -- el
// backend lo rechaza con 409 (ver ADR-007 Decisión 4); ocultarlo evita
// que el operador tope con ese error sin entender por qué.
function renderMediaPanel(solicitud, esPublicada) {
  const media = mediaCache.get(solicitud.id) || [];
  const filasHtml = media.length
    ? media.map((m) => renderMediaRow(solicitud, m)).join("")
    : `<p class="destinos-panel-empty">Sin archivos adjuntos todavía.</p>`;
  const subirHtml = esPublicada
    ? ""
    : `<div class="destino-row destino-row-agregar">
         <input type="file" class="media-file-input" accept="image/*,video/*" data-id="${solicitud.id}">
         <button type="button" class="btn btn-secondary btn-subir-media" data-id="${solicitud.id}">
           <svg class="icon"><use href="#icon-image"></use></svg>Subir
         </button>
       </div>`;
  return `<div class="reporte-panel">${filasHtml}${subirHtml}</div>`;
}

function renderKanbanCard(solicitud, esPublicada) {
  if (!esPublicada && solicitud.id === editingSolicitudId) {
    return renderKanbanCardEditForm(solicitud);
  }

  // Sprint 4A, Incremento 5 (UI de destinos): una solicitud ya ACEPTADA
  // pero todavía no completa (le falta confirmar algún destino) sigue
  // viviendo en la columna "pendientes" -- ver loadSolicitudes() -- pero
  // ya no tiene sentido ofrecerle Publicar/Vincular pauta/Editar (esas
  // acciones son de triage, y el triage ya pasó). Solo queda gestionar
  // sus destinos.
  const esRecibida = !esPublicada && solicitud.estado === "recibida";
  const esEnCurso = !esPublicada && solicitud.estado === "aceptada";

  const pauta = solicitud.pauta_id ? pautasById.get(solicitud.pauta_id) : null;
  const client = pauta ? clientsById.get(pauta.client_id) : null;
  const nombreCliente = client ? client.nombre : "(sin vincular)";
  const horas = horasEnEspera(solicitud.fecha_recepcion);
  const esperandoMucho = esRecibida && horas >= STALE_REQUEST_HOURS;
  const hora = formatFechaHoraNegocio(solicitud.fecha_recepcion);
  const tituloOrden = esRecibida ? ` title="${razonOrdenSolicitud(solicitud, pauta)}"` : "";
  const score = esRecibida ? scoreSolicitud(solicitud, pauta, horas) : null;

  const tags = [];
  if (esRecibida) {
    tags.push(
      `<span class="kanban-card-chip${esperandoMucho ? " kanban-card-chip-urgent" : ""}">⏱ ${formatHoras(horas)}</span>`
    );
  }
  if (esEnCurso) {
    tags.push(`<span class="kanban-card-chip">🚀 En curso</span>`);
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
  if (esRecibida) {
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
         </button>
         <button type="button" class="btn btn-secondary btn-cancelar-solicitud" data-id="${solicitud.id}">
           <svg class="icon"><use href="#icon-close"></use></svg>Cancelar
         </button>`;
  }
  if (!esPublicada) {
    const destinosAbiertos = destinosAbiertoId === solicitud.id;
    accionHtml += `
         <button type="button" class="btn btn-secondary btn-destinos-toggle" data-id="${solicitud.id}">
           <svg class="icon"><use href="#icon-inbox"></use></svg>${destinosAbiertos ? "Ocultar destinos" : "Destinos"}
         </button>`;
  }
  // Sprint 4A, Incremento 6: disponible en cualquier tarjeta (pendiente,
  // en curso o publicada) -- una solicitud puede tener destinos y quedar
  // parcialmente completa mucho antes de aparecer en "Publicadas" (ver
  // ADR-006), y el reporte sigue siendo útil para revisar ese avance.
  const reporteAbierto = reporteAbiertoId === solicitud.id;
  accionHtml += `
       <button type="button" class="btn btn-secondary" data-reporte-toggle="${solicitud.id}">
         <svg class="icon"><use href="#icon-detail"></use></svg>${reporteAbierto ? "Ocultar reporte" : "Ver reporte"}
       </button>`;
  // Sprint 4A, Incremento 7 (MediaAsset): mismo criterio que el reporte --
  // disponible en cualquier tarjeta, revisar/adjuntar material sigue
  // siendo útil aunque la solicitud ya esté publicada (solo la subida se
  // oculta ahí, ver renderMediaPanel).
  const mediaAbierto = mediaAbiertoId === solicitud.id;
  accionHtml += `
       <button type="button" class="btn btn-secondary" data-media-toggle="${solicitud.id}">
         <svg class="icon"><use href="#icon-image"></use></svg>${mediaAbierto ? "Ocultar media" : "Media"}
       </button>`;

  const claseExtra = esPublicada
    ? "is-publicada"
    : esEnCurso
      ? "is-en-curso"
      : esperandoMucho
        ? "is-urgent"
        : "";
  // Publicadas: solo un resumen corto por defecto, el texto completo queda
  // a un clic ("Ver texto completo") — pedido explícito del Sprint UX 3
  // para que la columna de publicadas no compita en espacio con la cola.
  const textoHtml = esPublicada
    ? `<p class="kanban-card-texto is-truncated">${solicitud.texto}</p>
       <button type="button" class="kanban-card-ver">Ver texto completo</button>`
    : `<p class="kanban-card-texto">${solicitud.texto}</p>`;
  const tituloHtml = solicitud.titulo
    ? `<p class="kanban-card-titulo">${solicitud.titulo}</p>`
    : "";
  const destinosPanelHtml =
    !esPublicada && destinosAbiertoId === solicitud.id ? renderDestinosPanel(solicitud) : "";
  const reportePanelHtml =
    reporteAbiertoId === solicitud.id ? renderReportePanel(solicitud) : "";
  const mediaPanelHtml =
    mediaAbiertoId === solicitud.id ? renderMediaPanel(solicitud, esPublicada) : "";

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
      ${esRecibida ? `<p class="kanban-card-priority-reason">${motivoPrioridadCorto(solicitud, pauta)}</p>` : ""}
      ${tituloHtml}
      ${textoHtml}
      ${accionHtml ? `<div class="kanban-card-footer">${accionHtml}</div>` : ""}
      ${destinosPanelHtml}
      ${reportePanelHtml}
      ${mediaPanelHtml}
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
  for (const btn of pendEl.querySelectorAll(".btn-cancelar-solicitud")) {
    btn.addEventListener("click", () => cancelarSolicitud(btn.dataset.id));
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
        form.querySelector(".kanban-card-edit-titulo").value,
        form.querySelector(".kanban-card-edit-texto").value,
        form.querySelector(".kanban-card-edit-prioridad").checked
      );
    });
  }
  for (const btn of pendEl.querySelectorAll(".btn-destinos-toggle")) {
    btn.addEventListener("click", () => toggleDestinosPanel(btn.dataset.id));
  }
  for (const btn of pendEl.querySelectorAll(".btn-agregar-destino")) {
    btn.addEventListener("click", () => {
      const select = pendEl.querySelector(`.destino-select[data-id="${btn.dataset.id}"]`);
      agregarDestino(btn.dataset.id, select.value);
    });
  }
  for (const btn of pendEl.querySelectorAll(".btn-crear-borrador")) {
    btn.addEventListener("click", () => crearBorradorWordpress(btn.dataset.id, btn.dataset.destinoId));
  }
  for (const btn of pendEl.querySelectorAll(".btn-confirmar-destino")) {
    btn.addEventListener("click", () => {
      const input = pendEl.querySelector(`.destino-row-url[data-destino-id="${btn.dataset.destinoId}"]`);
      confirmarDestino(btn.dataset.id, btn.dataset.destinoId, input ? input.value.trim() : null);
    });
  }
  for (const btn of pendEl.querySelectorAll(".btn-cancelar-destino")) {
    btn.addEventListener("click", () => cancelarDestino(btn.dataset.id, btn.dataset.destinoId));
  }
}

async function guardarEdicionSolicitud(id, titulo, texto, prioridadManual) {
  try {
    const body = { texto, prioridad_manual: prioridadManual };
    // titulo solo se envía si tiene contenido -- omitido, el backend lo deja
    // sin cambios (edit_solicitud no soporta "borrar" el título, ver su
    // docstring); mandar "" causaría un 422 (PublicationRequest lo rechaza).
    if (titulo.trim()) {
      body.titulo = titulo.trim();
    }
    await apiFetch(`/publication-requests/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
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
  //
  // "Publicada" ya no es un estado (Sprint 4A, Incremento 4 — ver
  // core.entities.publication_request) — una solicitud está completa
  // cuando fecha_cierre no es null, sin importar su estado. Y una
  // solicitud ya ACEPTADA pero todavía no completa ("en curso": le falta
  // confirmar algún destino) sigue viviendo en la cola de trabajo, no
  // debe desaparecer ni duplicarse en "Publicadas" -- por eso son tres
  // pedidos, no dos.
  const [recibidas, enCurso, publicadas] = await Promise.all([
    apiFetch("/publication-requests?estado=recibida"),
    apiFetch("/publication-requests?estado=aceptada&completa=false"),
    apiFetch("/publication-requests?completa=true"),
  ]);
  publicadas.sort((a, b) => b.fecha_cierre.localeCompare(a.fecha_cierre));
  const pendientes = [...recibidas, ...enCurso];
  solicitudesPendientesTodas = pendientes;
  solicitudesPublicadasTodas = publicadas;

  renderMetricasSolicitudes(pendientes, publicadas);

  document.getElementById("kanban-count-pendientes").textContent = pendientes.length;
  document.getElementById("kanban-count-publicadas").textContent = publicadas.length;

  renderKanbanPendientesColumn();
  renderKanbanPublicadasColumn();

  renderActividadReciente();
}

// Separado de loadSolicitudes (mismo motivo que renderKanbanPendientesColumn:
// Sprint 4A, Incremento 6) para poder redibujar solo esta columna al
// abrir/cerrar un panel de reporte, sin volver a pedirle nada al backend --
// usa el mismo top-30 ya calculado en solicitudesPublicadasTodas.
function renderKanbanPublicadasColumn() {
  const pubEl = document.getElementById("kanban-publicadas");
  const publicadasRecientes = solicitudesPublicadasTodas.slice(0, 30);
  pubEl.innerHTML = publicadasRecientes.length
    ? publicadasRecientes.map((s) => renderKanbanCard(s, true)).join("")
    : renderEmptyState("📭", "Todavía no hay publicaciones.");
}

async function publicarSolicitud(id) {
  try {
    await apiFetch(`/publication-requests/${id}/publish`, { method: "POST" });
    showStatus("Solicitud publicada.", false);
    await invalidarReporte(id);
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

async function cancelarSolicitud(id) {
  try {
    await apiFetch(`/publication-requests/${id}/cancelar`, { method: "POST" });
    showStatus("Solicitud cancelada.", false);
    await loadSolicitudes();
  } catch (error) {
    showStatus(error.message, true);
  }
}

async function toggleDestinosPanel(id) {
  if (destinosAbiertoId === id) {
    destinosAbiertoId = null;
    renderKanbanPendientesColumn();
    return;
  }
  destinosAbiertoId = id;
  if (!destinosCache.has(id)) {
    try {
      destinosCache.set(id, await apiFetch(`/publication-requests/${id}/destinos`));
    } catch (error) {
      showStatus(error.message, true);
      destinosAbiertoId = null;
      return;
    }
  }
  renderKanbanPendientesColumn();
}

// Igual que toggleDestinosPanel, pero redibuja ambas columnas -- a
// diferencia de destinos, el botón "Ver reporte" aparece tanto en
// pendientes como en publicadas (ver renderKanbanCard), y no sabemos de
// antemano en cuál de las dos vive la tarjeta que se acaba de tocar.
async function toggleReportePanel(id) {
  if (reporteAbiertoId === id) {
    reporteAbiertoId = null;
    renderKanbanPendientesColumn();
    renderKanbanPublicadasColumn();
    return;
  }
  reporteAbiertoId = id;
  if (!reporteCache.has(id)) {
    try {
      reporteCache.set(id, await apiFetch(`/publication-requests/${id}/reporte`));
    } catch (error) {
      showStatus(error.message, true);
      reporteAbiertoId = null;
      return;
    }
  }
  renderKanbanPendientesColumn();
  renderKanbanPublicadasColumn();
}

async function copiarReporte(id) {
  const reporte = reporteCache.get(id);
  if (!reporte) return;
  try {
    await navigator.clipboard.writeText(formatoReporteTexto(reporte));
    showStatus("Reporte copiado al portapapeles.", false);
  } catch {
    showStatus("No se pudo copiar el reporte. Copia el texto a mano.", true);
  }
}

// Mismo patrón abrir/cerrar que toggleReportePanel -- ambas columnas,
// mismo motivo (ver el comentario junto a mediaAbiertoId).
async function toggleMediaPanel(id) {
  if (mediaAbiertoId === id) {
    mediaAbiertoId = null;
    renderKanbanPendientesColumn();
    renderKanbanPublicadasColumn();
    return;
  }
  mediaAbiertoId = id;
  if (!mediaCache.has(id)) {
    try {
      mediaCache.set(id, await apiFetch(`/publication-requests/${id}/media`));
    } catch (error) {
      showStatus(error.message, true);
      mediaAbiertoId = null;
      return;
    }
  }
  renderKanbanPendientesColumn();
  renderKanbanPublicadasColumn();
}

async function refrescarMediaSolo(id) {
  mediaCache.set(id, await apiFetch(`/publication-requests/${id}/media`));
  renderKanbanPendientesColumn();
  renderKanbanPublicadasColumn();
}

async function subirMedia(id, file) {
  if (!file) {
    showStatus("Elige un archivo antes de subir.", true);
    return;
  }
  const formData = new FormData();
  formData.append("archivo", file);
  try {
    // Sin header Content-Type a mano -- el navegador arma el boundary
    // multipart correcto solo cuando el body es un FormData y ese header
    // se deja sin tocar.
    await apiFetch(`/publication-requests/${id}/media`, { method: "POST", body: formData });
    showStatus("Archivo subido.", false);
    await refrescarMediaSolo(id);
  } catch (error) {
    showStatus(error.message, true);
  }
}

async function eliminarMedia(id, mediaId) {
  try {
    await apiFetch(`/publication-requests/${id}/media/${mediaId}`, { method: "DELETE" });
    showStatus("Archivo eliminado.", false);
    await refrescarMediaSolo(id);
  } catch (error) {
    showStatus(error.message, true);
  }
}

// Refresco liviano tras agregar un destino o crear un borrador de
// WordPress -- ninguna de las dos cambia esta_completa, así que no hace
// falta releer dashboard/pautas, solo la lista de destinos de esta tarjeta.
async function refrescarDestinosSolo(id) {
  destinosCache.set(id, await apiFetch(`/publication-requests/${id}/destinos`));
  await invalidarReporte(id);
  renderKanbanPendientesColumn();
}

// El reporte (completa, pauta_consumida, destinos) se deriva de los mismos
// datos que cualquier acción de destinos puede cambiar -- agregar, crear
// borrador, confirmar, cancelar, publicar. Sin esto, un reporte ya abierto
// se queda mostrando el estado de antes del cambio (visto en verificación
// manual: confirmar Facebook no actualizaba "Pendiente"/"Sin enlace" del
// panel ya abierto). Si el panel está abierto para esta solicitud, se
// refresca de una vez; si no, simplemente se descarta -- toggleReportePanel
// ya sabe pedirlo de nuevo la próxima vez que se abra.
async function invalidarReporte(id) {
  reporteCache.delete(id);
  if (reporteAbiertoId !== id) return;
  try {
    reporteCache.set(id, await apiFetch(`/publication-requests/${id}/reporte`));
  } catch {
    reporteAbiertoId = null;
  }
}

// Refresco completo tras confirmar o cancelar un destino -- cualquiera de
// las dos puede completar la solicitud (esta_completa) y mover la cuota
// de la Pauta, así que sí hace falta releer todo lo que depende de eso.
async function refrescarTrasCambioDeCompletitud(id) {
  try {
    destinosCache.set(id, await apiFetch(`/publication-requests/${id}/destinos`));
  } catch {
    // La solicitud pudo haber quedado completa y salir de la cola --
    // seguir sin la cache actualizada no es un error, loadSolicitudes()
    // de todas formas va a redibujar todo desde cero.
    destinosCache.delete(id);
  }
  await invalidarReporte(id);
  await Promise.all([loadSolicitudes(), loadClientesYPautas(), loadDashboard(), loadAlertas()]);
}

async function agregarDestino(id, canal) {
  if (!canal) {
    showStatus("Elige un canal antes de agregar.", true);
    return;
  }
  try {
    await apiFetch(`/publication-requests/${id}/destinos`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ canal }),
    });
    showStatus("Destino agregado.", false);
    await refrescarDestinosSolo(id);
  } catch (error) {
    showStatus(error.message, true);
  }
}

async function crearBorradorWordpress(id, destinoId) {
  try {
    await apiFetch(`/publication-requests/${id}/destinos/${destinoId}/crear-borrador-wordpress`, {
      method: "POST",
    });
    showStatus("Borrador creado en WordPress.", false);
    await refrescarDestinosSolo(id);
  } catch (error) {
    showStatus(error.message, true);
  }
}

async function confirmarDestino(id, destinoId, urlPublicacion) {
  try {
    await apiFetch(`/publication-requests/${id}/destinos/${destinoId}/confirmar-publicacion`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(urlPublicacion ? { url_publicacion: urlPublicacion } : {}),
    });
    showStatus("Destino confirmado.", false);
    await refrescarTrasCambioDeCompletitud(id);
  } catch (error) {
    showStatus(error.message, true);
  }
}

async function cancelarDestino(id, destinoId) {
  try {
    await apiFetch(`/publication-requests/${id}/destinos/${destinoId}/cancelar`, {
      method: "POST",
    });
    showStatus("Destino cancelado.", false);
    await refrescarTrasCambioDeCompletitud(id);
  } catch (error) {
    showStatus(error.message, true);
  }
}

// ---------- Dashboard comercial ----------
//
// Todo lo que se ve aquí viene tal cual de /dashboard/{resumen,alertas,ranking}
// — esta pantalla no calcula ni reordena nada por su cuenta, solo formatea
// para pantalla (moneda, fechas, iconos) lo que ya entrega el backend.

// Las métricas que de verdad ayudan a responder "¿cómo va el negocio hoy?"
// (Sprint UX 3) — el resto de indicadores de AnalyticsService quedan en
// "Otros indicadores" más abajo, para no competir en espacio con estas.
const DASHBOARD_METRICAS_PRINCIPALES = [
  ["clientes_activos", "Clientes activos", "icon-users", false],
  ["ingreso_contratado_activo", "Ingresos año actual", "icon-money", true],
  ["solicitudes_pendientes", "Solicitudes pendientes", "icon-inbox", false],
  ["publicaciones_este_mes", "Publicaciones este mes", "icon-check", false],
  ["renovaciones_del_mes", "Renovaciones del mes", "icon-refresh", false],
  ["ingresos_ultimo_mes", "Ingresos último mes", "icon-money", true],
  ["pautado_mes_actual", "Pautado este mes", "icon-money", true],
];

const DASHBOARD_ACTIVIDAD = [
  ["pautas_vencidas", "Pautas vencidas", "icon-alert", false],
  ["peso_comercial_promedio", "Peso comercial promedio", "icon-target", true],
  ["valor_promedio_por_cliente", "Valor promedio/cliente", "icon-money", true],
  ["ingreso_historico", "Ingreso histórico", "icon-money", true],
];

// "Renovaciones del mes", "ingresos último mes" y "pautado este mes" no
// vienen del backend -- se calculan aquí mismo, sobre las Pautas que ya
// están cargadas en memoria (pautasById), sin ningún round-trip nuevo a
// la API. Las dos primeras definiciones fueron confirmadas con el
// negocio antes de implementarse (Sprint UX 3): "ingresos" es dinero ya
// cobrado (fecha_pago), no una proyección; "renovaciones" son contratos
// por paquete de tiempo (no Individual) cuyo fecha_fin cae en el mes
// calendario actual. "Pautado este mes" (2026-08-14) reutiliza la misma
// función que "ingresos último mes" con offset 0 en vez de -1 -- incluso
// el nombre "pautado" viene del mismo criterio de fecha_pago, ya
// confirmado, así que no hace falta una definición nueva.

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
    pautado_mes_actual: calcularIngresosDelMes(0),
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

const MESES_LABELS = [
  "Enero",
  "Febrero",
  "Marzo",
  "Abril",
  "Mayo",
  "Junio",
  "Julio",
  "Agosto",
  "Septiembre",
  "Octubre",
  "Noviembre",
  "Diciembre",
];

const MESES_ABREV = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];

// ---------- Gráficas del Dashboard (SVG generado a mano) ----------
//
// Sin librería de gráficas -- mismo criterio "sin framework, sin CDN" que
// el resto de esta app (ver style.css). Paleta y specs de marca (barras
// ≤24px, extremo redondeado 4px cuadrado en la base, grilla en gris
// recesivo, tooltip por barra) siguiendo el skill dataviz; colores
// reutilizados de las variables ya existentes y ya validadas con
// scripts/validate_palette.js (ver comentario en style.css).

const CHART_VIEW_WIDTH_DEFAULT = 960;
const CHART_VIEW_HEIGHT = 260;
const CHART_MARGIN = { top: 8, right: 8, bottom: 28, left: 56 };
const CHART_MAX_BAR_WIDTH = 24;
const CHART_BAR_RADIUS = 4;
let rentabilidadParaGraficas = [];

// El viewBox se arma con el ancho real del contenedor (`el.clientWidth`),
// no un ancho fijo -- las etiquetas (`.chart-axis-label`) tienen su
// font-size en px definido en el sistema de coordenadas del viewBox, así
// que con un viewBox fijo de 960 unidades escalado a un chart-card angosto
// de celular (~320px) el texto se volvía ilegible (bug reportado
// 2026-08-15: "las gráficas no se aprecian bien en dispositivos móviles").
// Con el viewBox igualado al ancho real, 1 unidad = 1px real siempre,
// sin importar el dispositivo.
function chartViewWidth(el) {
  return Math.max(280, el.clientWidth || CHART_VIEW_WIDTH_DEFAULT);
}

// Redondea `value` hacia arriba al siguiente "número limpio" (1/2/5 x
// 10^n) -- así el eje Y siempre termina en una marca legible (100.000,
// 200.000, 500.000...) en vez de un tope arbitrario como el máximo exacto
// de los datos.
function nicMaxEje(value) {
  if (value <= 0) return 100;
  const exponente = Math.floor(Math.log10(value));
  const base = Math.pow(10, exponente);
  const fraccion = value / base;
  let nice;
  if (fraccion <= 1) nice = 1;
  else if (fraccion <= 2) nice = 2;
  else if (fraccion <= 5) nice = 5;
  else nice = 10;
  return nice * base;
}

// Path de un rectángulo con esquinas redondeadas solo en el extremo lejano
// a la base (arriba si crece hacia arriba, abajo si crece hacia abajo) --
// "4px redondeado en el extremo, cuadrado en la base" (ver marks-and-anatomy
// del skill dataviz). `radius` se recorta al alto real para barras muy
// chicas, para no dibujar una curva más grande que la propia barra.
function rectRedondeadoPath(x, y, width, height, radius, directionUp) {
  const r = Math.max(0, Math.min(radius, height, width / 2));
  if (directionUp) {
    return `M${x},${y + height} L${x},${y + r} Q${x},${y} ${x + r},${y} L${x + width - r},${y} Q${x + width},${y} ${x + width},${y + r} L${x + width},${y + height} Z`;
  }
  return `M${x},${y} L${x + width},${y} L${x + width},${y + height - r} Q${x + width},${y + height} ${x + width - r},${y + height} L${x + r},${y + height} Q${x},${y + height} ${x},${y + height - r} Z`;
}

function chartEjeXLabel(item) {
  return `${MESES_ABREV[item.mes - 1]}'${String(item.anio).slice(2)}`;
}

// Grilla horizontal + etiquetas del eje Y -- 4 marcas limpias entre 0 y
// `maxVal`, gris recesivo (un paso fuera de la superficie, nunca punteado
// -- ver marks-and-anatomy.md).
function chartGridlinesSvg(maxVal, plotTop, plotHeight, plotLeft, plotRight) {
  const pasos = 4;
  let svg = "";
  for (let i = 0; i <= pasos; i++) {
    const valor = (maxVal / pasos) * i;
    const y = plotTop + plotHeight - (valor / maxVal) * plotHeight;
    svg += `<line class="chart-gridline" x1="${plotLeft}" y1="${y}" x2="${plotRight}" y2="${y}"></line>`;
    svg += `<text class="chart-axis-label" x="${plotLeft - 8}" y="${y + 3}" text-anchor="end">${formatMoneda(valor)}</text>`;
  }
  return svg;
}

// Ingresos vs. gastos -- barras agrupadas, ambas series siempre ≥0, mismo
// eje. Dos series con identidad fija (nunca ciclada) -- azul = ingresos,
// naranja = gastos, en ese orden en cada grupo.
function renderChartIngresosGastos(rentabilidad) {
  const el = document.getElementById("chart-ingresos-gastos");
  if (!rentabilidad.length) {
    el.innerHTML = `<p class="chart-empty">Todavía no hay datos para graficar.</p>`;
    return;
  }
  const viewWidth = chartViewWidth(el);
  const plotLeft = CHART_MARGIN.left;
  const plotRight = viewWidth - CHART_MARGIN.right;
  const plotTop = CHART_MARGIN.top;
  const plotHeight = CHART_VIEW_HEIGHT - CHART_MARGIN.top - CHART_MARGIN.bottom;
  const plotWidth = plotRight - plotLeft;
  const maxVal = nicMaxEje(Math.max(...rentabilidad.map((i) => Math.max(Number(i.ingresos), Number(i.gastos)))));
  const slotWidth = plotWidth / rentabilidad.length;
  const barGap = 4;
  const barWidth = Math.min(CHART_MAX_BAR_WIDTH, (slotWidth - 16 - barGap) / 2);
  const groupWidth = barWidth * 2 + barGap;

  let bars = "";
  let labels = "";
  rentabilidad.forEach((item, i) => {
    const slotX = plotLeft + i * slotWidth;
    const groupX = slotX + (slotWidth - groupWidth) / 2;
    const mesLabel = chartEjeXLabel(item);
    labels += `<text class="chart-axis-label" x="${slotX + slotWidth / 2}" y="${CHART_VIEW_HEIGHT - CHART_MARGIN.bottom + 16}" text-anchor="middle">${mesLabel}</text>`;

    const hIngresos = (Number(item.ingresos) / maxVal) * plotHeight;
    const yIngresos = plotTop + plotHeight - hIngresos;
    bars += `<path class="chart-bar" fill="var(--color-accent)" d="${rectRedondeadoPath(groupX, yIngresos, barWidth, hIngresos, CHART_BAR_RADIUS, true)}"
      data-chart-bar data-mes="${mesLabel}" data-serie="Ingresos" data-valor="${formatMoneda(item.ingresos)}"></path>`;

    const hGastos = (Number(item.gastos) / maxVal) * plotHeight;
    const yGastos = plotTop + plotHeight - hGastos;
    bars += `<path class="chart-bar" fill="var(--color-orange)" d="${rectRedondeadoPath(groupX + barWidth + barGap, yGastos, barWidth, hGastos, CHART_BAR_RADIUS, true)}"
      data-chart-bar data-mes="${mesLabel}" data-serie="Gastos" data-valor="${formatMoneda(item.gastos)}"></path>`;
  });

  el.innerHTML = `
    <svg class="chart-svg" viewBox="0 0 ${viewWidth} ${CHART_VIEW_HEIGHT}" role="img" aria-label="Ingresos y gastos por mes">
      ${chartGridlinesSvg(maxVal, plotTop, plotHeight, plotLeft, plotRight)}
      ${bars}
      ${labels}
    </svg>`;
}

// Rentabilidad -- una sola serie, color por signo (nunca color solo: la
// posición sobre/bajo la línea base ya redunda la señal). Verde/rojo son
// colores de estado (bueno/crítico), no identidad categórica -- por eso
// esta gráfica no lleva leyenda, a diferencia de la de arriba.
function renderChartRentabilidad(rentabilidad) {
  const el = document.getElementById("chart-rentabilidad");
  if (!rentabilidad.length) {
    el.innerHTML = `<p class="chart-empty">Todavía no hay datos para graficar.</p>`;
    return;
  }
  const viewWidth = chartViewWidth(el);
  const plotLeft = CHART_MARGIN.left;
  const plotRight = viewWidth - CHART_MARGIN.right;
  const plotTop = CHART_MARGIN.top;
  const plotHeight = CHART_VIEW_HEIGHT - CHART_MARGIN.top - CHART_MARGIN.bottom;
  const plotWidth = plotRight - plotLeft;
  const maxAbs = Math.max(...rentabilidad.map((i) => Math.abs(Number(i.rentabilidad))));
  const maxVal = nicMaxEje(maxAbs || 100);
  const baselineY = plotTop + plotHeight / 2;
  const halfHeight = plotHeight / 2;
  const slotWidth = plotWidth / rentabilidad.length;
  const barWidth = Math.min(CHART_MAX_BAR_WIDTH, slotWidth - 16);

  let bars = "";
  let labels = "";
  rentabilidad.forEach((item, i) => {
    const slotX = plotLeft + i * slotWidth;
    const barX = slotX + (slotWidth - barWidth) / 2;
    const mesLabel = chartEjeXLabel(item);
    labels += `<text class="chart-axis-label" x="${slotX + slotWidth / 2}" y="${CHART_VIEW_HEIGHT - CHART_MARGIN.bottom + 16}" text-anchor="middle">${mesLabel}</text>`;

    const valor = Number(item.rentabilidad);
    const esPositiva = valor >= 0;
    const h = (Math.abs(valor) / maxVal) * halfHeight;
    const y = esPositiva ? baselineY - h : baselineY;
    const color = esPositiva ? "var(--color-success)" : "var(--color-danger)";
    bars += `<path class="chart-bar" fill="${color}" d="${rectRedondeadoPath(barX, y, barWidth, h, CHART_BAR_RADIUS, esPositiva)}"
      data-chart-bar data-mes="${mesLabel}" data-serie="Rentabilidad" data-valor="${formatMoneda(item.rentabilidad)}"></path>`;
  });

  el.innerHTML = `
    <svg class="chart-svg" viewBox="0 0 ${viewWidth} ${CHART_VIEW_HEIGHT}" role="img" aria-label="Rentabilidad por mes">
      <line class="chart-baseline" x1="${plotLeft}" y1="${baselineY}" x2="${plotRight}" y2="${baselineY}"></line>
      ${bars}
      ${labels}
    </svg>`;
}

function renderRentabilidadCharts(rentabilidad) {
  rentabilidadParaGraficas = rentabilidad;
  renderChartIngresosGastos(rentabilidad);
  renderChartRentabilidad(rentabilidad);
}

// Re-dibuja con el nuevo ancho del contenedor al rotar el celular o
// redimensionar la ventana -- el viewBox depende de `el.clientWidth` (ver
// chartViewWidth), así que un simple CSS `width:100%` no alcanza para
// mantener el texto legible después de un cambio de tamaño.
let resizeChartsTimeout = null;
window.addEventListener("resize", () => {
  window.clearTimeout(resizeChartsTimeout);
  resizeChartsTimeout = window.setTimeout(() => {
    if (rentabilidadParaGraficas.length) renderRentabilidadCharts(rentabilidadParaGraficas);
  }, 200);
});

// Tooltip compartido por ambas gráficas -- delegado en document (mismo
// patrón que setupGlobalClicks), mouseover/mouseout sí burbujean a
// diferencia de mouseenter/mouseleave, así que no hace falta un listener
// por barra.
function setupChartTooltip() {
  const tooltip = document.getElementById("chart-tooltip");
  document.addEventListener("mouseover", (event) => {
    const bar = event.target.closest("[data-chart-bar]");
    if (!bar) return;
    tooltip.innerHTML = `${bar.dataset.mes} <span class="chart-tooltip-label">${bar.dataset.serie}</span><br><span class="chart-tooltip-value">${bar.dataset.valor}</span>`;
    tooltip.hidden = false;
  });
  document.addEventListener("mousemove", (event) => {
    if (tooltip.hidden) return;
    tooltip.style.left = `${event.clientX + 14}px`;
    tooltip.style.top = `${event.clientY + 14}px`;
  });
  document.addEventListener("mouseout", (event) => {
    const bar = event.target.closest("[data-chart-bar]");
    if (!bar) return;
    tooltip.hidden = true;
  });
}

// Últimos 12 meses, ingresos - gastos -- ver core.analytics.rentabilidad_service.
// El backend ya entrega los 12 meses en orden cronológico (el más viejo
// primero); esta pantalla solo formatea para pantalla, igual que el resto
// del Dashboard.
function renderRentabilidadMensual(rentabilidad) {
  const el = document.getElementById("rentabilidad-mensual");
  el.innerHTML = rentabilidad
    .map((item) => {
      const esPositiva = Number(item.rentabilidad) >= 0;
      return `
      <div class="rentabilidad-row">
        <span class="rentabilidad-row-mes">${MESES_LABELS[item.mes - 1]} ${item.anio}</span>
        <div class="rentabilidad-row-stats">
          <div class="rentabilidad-stat">
            <span class="rentabilidad-stat-label">Ingresos</span>
            <span class="rentabilidad-stat-value">${formatMoneda(item.ingresos)}</span>
          </div>
          <div class="rentabilidad-stat">
            <span class="rentabilidad-stat-label">Gastos</span>
            <span class="rentabilidad-stat-value">${formatMoneda(item.gastos)}</span>
          </div>
          <div class="rentabilidad-stat rentabilidad-stat-resultado" data-positive="${esPositiva}">
            <span class="rentabilidad-stat-label">Rentabilidad</span>
            <span class="rentabilidad-stat-value">${formatMoneda(item.rentabilidad)}</span>
          </div>
        </div>
      </div>`;
    })
    .join("");
}

async function loadDashboard() {
  const [resumen, alertas, ranking, rentabilidad] = await Promise.all([
    apiFetch("/dashboard/resumen"),
    apiFetch("/dashboard/alertas"),
    apiFetch("/dashboard/ranking"),
    apiFetch("/dashboard/rentabilidad"),
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
  renderRentabilidadCharts(rentabilidad);
  renderRentabilidadMensual(rentabilidad);
}

// ---------- Reportes (descargas CSV) ----------
//
// Cada descarga es un <a href> normal contra app.api.routers.reportes --
// no JS armando un Blob (esa versión no descargaba de forma confiable,
// bug reportado 2026-08-15). Lo único que hace esta pantalla es mantener
// el href de cada link sincronizado con los inputs Desde/Hasta; la
// navegación y el archivo los maneja el navegador solo.
function setupReportes() {
  const enlaces = [
    { desde: "reporte-rentabilidad-desde", hasta: "reporte-rentabilidad-hasta", link: "reporte-rentabilidad-descargar", base: "/reportes/rentabilidad.csv" },
    { desde: "reporte-pautas-desde", hasta: "reporte-pautas-hasta", link: "reporte-pautas-descargar", base: "/reportes/pautas.csv" },
    { desde: "reporte-gastos-desde", hasta: "reporte-gastos-hasta", link: "reporte-gastos-descargar", base: "/reportes/gastos.csv" },
  ];
  for (const { desde, hasta, link, base } of enlaces) {
    const desdeInput = document.getElementById(desde);
    const hastaInput = document.getElementById(hasta);
    const a = document.getElementById(link);
    const actualizarHref = () => {
      const params = new URLSearchParams();
      if (desdeInput.value) params.set("desde", desdeInput.value);
      if (hastaInput.value) params.set("hasta", hastaInput.value);
      const query = params.toString();
      a.href = query ? `${base}?${query}` : base;
    };
    desdeInput.addEventListener("change", actualizarHref);
    hastaInput.addEventListener("change", actualizarHref);
  }
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
    const titulo = document.getElementById("solicitud-titulo").value.trim();
    const payload = {
      pauta_id: pautaId || null,
      titulo: titulo || null,
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

function resetFormPautaDrawer() {
  editingPautaId = null;
  document.getElementById("drawer-pauta-titulo").textContent = "Nueva pauta";
  document.getElementById("form-pauta-submit-label").textContent = "Crear pauta";
  setIconUse(document.getElementById("form-pauta-submit-icon"), "icon-plus");
  document.getElementById("form-pauta").reset();
}

function startEditPauta(pautaId) {
  const pauta = pautasById.get(pautaId);
  if (!pauta) return;
  editingPautaId = pautaId;
  document.getElementById("drawer-pauta-titulo").textContent = "Editar pauta";
  document.getElementById("form-pauta-submit-label").textContent = "Guardar cambios";
  setIconUse(document.getElementById("form-pauta-submit-icon"), "icon-check");
  // El catálogo de planes es solo un atajo de captura (autocompleta
  // cantidad/valor) -- no es un dato guardado en la Pauta, así que no hay
  // nada que preseleccionar acá; queda en blanco hasta que se cree otra.
  document.getElementById("pauta-plan").value = "";
  document.getElementById("pauta-cliente").value = pauta.client_id;
  document.getElementById("pauta-fecha-inicio").value = pauta.fecha_inicio;
  document.getElementById("pauta-fecha-fin").value = pauta.fecha_fin;
  document.getElementById("pauta-cantidad").value = pauta.publicaciones_contratadas;
  document.getElementById("pauta-valor").value = pauta.valor_pagado;
  document.getElementById("pauta-fecha-pago").value = pauta.fecha_pago;
  document.getElementById("pauta-observaciones").value = pauta.observaciones || "";
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
      if (editingPautaId) {
        await apiFetch(`/pautas/${editingPautaId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        showStatus("Pauta actualizada.", false);
      } else {
        await apiFetch("/pautas", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        showStatus("Pauta creada.", false);
      }
      resetFormPautaDrawer();
      closeDrawer(document.getElementById("drawer-pauta"));
      await loadClientesYPautas();
      await loadDashboard();
      await loadAlertas();
    } catch (error) {
      showStatus(error.message, true);
    }
  });
}

function resetFormGastoDrawer() {
  editingGastoId = null;
  document.getElementById("drawer-gasto-titulo").textContent = "Nuevo gasto";
  document.getElementById("form-gasto-submit-label").textContent = "Registrar gasto";
  setIconUse(document.getElementById("form-gasto-submit-icon"), "icon-plus");
  document.getElementById("form-gasto").reset();
}

function startEditGasto(gastoId) {
  const gasto = gastosTodas.find((g) => g.id === gastoId);
  if (!gasto) return;
  editingGastoId = gastoId;
  document.getElementById("drawer-gasto-titulo").textContent = "Editar gasto";
  document.getElementById("form-gasto-submit-label").textContent = "Guardar cambios";
  setIconUse(document.getElementById("form-gasto-submit-icon"), "icon-check");
  document.getElementById("gasto-descripcion").value = gasto.descripcion;
  document.getElementById("gasto-valor").value = gasto.valor;
  document.getElementById("gasto-fecha").value = gasto.fecha;
}

function setupFormGasto() {
  document.getElementById("form-gasto").addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = {
      descripcion: document.getElementById("gasto-descripcion").value,
      valor: document.getElementById("gasto-valor").value,
      fecha: document.getElementById("gasto-fecha").value,
    };
    try {
      if (editingGastoId) {
        await apiFetch(`/gastos/${editingGastoId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        showStatus("Gasto actualizado.", false);
      } else {
        await apiFetch("/gastos", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        showStatus("Gasto registrado.", false);
      }
      resetFormGastoDrawer();
      closeDrawer(document.getElementById("drawer-gasto"));
      await loadGastos();
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
  return Promise.all([
    loadClientesYPautas(),
    loadSolicitudes(),
    loadDashboard(),
    loadAlertas(),
    loadGastos(),
  ]);
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
  setupFormGasto();
  setupChartTooltip();
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
  document.getElementById("refrescar-gastos").addEventListener("click", loadGastos);
  document.getElementById("gastos-buscar").addEventListener("input", (event) => {
    gastosFiltro = event.target.value;
    renderListaGastos();
  });
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
  setupReportes();

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
    await loadGastos();
  } catch (error) {
    showStatus(error.message, true);
  }
}

init();
