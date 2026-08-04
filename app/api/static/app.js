"use strict";
/**
 * Portal Vallenato — interfaz mínima sobre la API existente (Sprint 3D-UI).
 *
 * Sin build step, sin framework: fetch + DOM directo. Todo el estado vive
 * en memoria del navegador (mapas de clientes/pautas) y se recarga desde
 * la API en cada acción relevante — no hay caché ni sincronización
 * elaborada, no la necesita un solo operador usando esto en su navegador.
 *
 * Sprint 3F (revisión UX P0): los umbrales de abajo son puramente de
 * presentación — deciden qué se resalta en pantalla, nunca qué se
 * permite hacer. No son reglas de negocio, no viven en el dominio ni en
 * la API, y cambiarlos no requiere tocar ningún endpoint.
 */

const CLIENT_TIPO_LABELS = {
  artista: "Artista",
  manager: "Manager",
  promotor: "Promotor",
  empresario: "Empresario",
};

const EXPIRING_SOON_DAYS = 7; // pauta vigente que vence dentro de N días
const LOW_QUOTA_THRESHOLD = 2; // publicaciones restantes que ya cuentan como "cupo bajo"
const STALE_REQUEST_HOURS = 4; // solicitud recibida hace más de N horas, sin atender

let clientsById = new Map();
let pautasById = new Map();
let pendientesCount = 0;

// ---------- utilidades ----------

async function apiFetch(path, options) {
  const response = await fetch(path, options);
  if (response.status === 401) {
    // Sesión ausente o vencida — vale tanto al cargar la app por primera
    // vez como a mitad de uso (sesión vencida mientras la pestaña seguía
    // abierta). showLogin() está declarada más abajo; el "hoisting" de
    // funciones normales de JS hace que esto funcione sin importar el
    // orden de las declaraciones en el archivo.
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

function diasParaVencer(pauta) {
  const hoy = new Date();
  hoy.setHours(0, 0, 0, 0);
  const fin = new Date(pauta.fecha_fin + "T00:00:00");
  return Math.round((fin - hoy) / 86_400_000);
}

function horasEnEspera(fechaRecepcionIso) {
  return (Date.now() - new Date(fechaRecepcionIso).getTime()) / 3_600_000;
}

// ---------- autenticación ----------

function showLogin() {
  document.body.classList.add("login-active");
  document.getElementById("login-screen").hidden = false;
  document.getElementById("app-header").hidden = true;
  document.getElementById("nav-tabs").hidden = true;
  document.getElementById("btn-logout").hidden = true;
  document.querySelector("main").hidden = true;
  document.getElementById("resumen").innerHTML = "";
}

function showApp() {
  document.body.classList.remove("login-active");
  document.getElementById("login-screen").hidden = true;
  document.getElementById("app-header").hidden = false;
  document.getElementById("nav-tabs").hidden = false;
  document.getElementById("btn-logout").hidden = false;
  document.querySelector("main").hidden = false;
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

// ---------- pestañas ----------

function activateTab(name) {
  for (const btn of document.querySelectorAll(".tab-btn")) {
    btn.classList.toggle("active", btn.dataset.tab === name);
  }
  for (const panel of document.querySelectorAll(".tab-panel")) {
    panel.classList.toggle("active", panel.id === "tab-" + name);
  }
}

// ---------- carga de datos compartidos (clientes + pautas) ----------

async function loadClientesYPautas() {
  const [clientes, pautas] = await Promise.all([
    apiFetch("/clients"),
    apiFetch("/pautas"),
  ]);
  clientsById = new Map(clientes.map((c) => [c.id, c]));
  pautasById = new Map(pautas.map((p) => [p.id, p]));

  renderSelectClientes();
  renderSelectPautas();
  renderListaClientes(clientes, pautas);
  renderResumen();
}

function renderResumen() {
  const el = document.getElementById("resumen");
  if (!el) return;

  const pautas = Array.from(pautasById.values());
  const porVencer = pautas.filter(
    (p) => !p.vencida && diasParaVencer(p) <= EXPIRING_SOON_DAYS
  ).length;
  const agotadas = pautas.filter((p) => p.cuota_agotada).length;

  const plural = (n, singular, pluralForm) => (n === 1 ? singular : pluralForm);

  el.innerHTML = `
    <span class="resumen-item">
      ${pendientesCount} ${plural(pendientesCount, "solicitud pendiente", "solicitudes pendientes")}
    </span>
    <span class="resumen-item ${porVencer > 0 ? "is-alert" : ""}">
      ${porVencer} ${plural(porVencer, "pauta por vencer", "pautas por vencer")}
    </span>
    <span class="resumen-item ${agotadas > 0 ? "is-danger" : ""}">
      ${agotadas} ${plural(agotadas, "cupo agotado", "cupos agotados")}
    </span>
  `;
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
// ofrecerla para vincular una solicitud, ni la actual ni una futura. El
// campo `vigente` ya viene calculado por la API (PautaService), no se
// recalcula aquí.
function pautasVigentes() {
  return Array.from(pautasById.values()).filter((p) => p.vigente);
}

let solicitudPautaFiltro = "";

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

function estadoPautaBadges(pauta) {
  const badges = [];

  if (pauta.vencida) {
    badges.push('<span class="badge badge-danger">vencida</span>');
  } else {
    if (pauta.vigente) badges.push('<span class="badge badge-ok">vigente</span>');
    const dias = diasParaVencer(pauta);
    if (dias <= EXPIRING_SOON_DAYS) {
      badges.push(`<span class="badge badge-expiring">vence en ${dias}d</span>`);
    }
  }

  if (pauta.cuota_agotada) {
    badges.push('<span class="badge badge-warning">cupo agotado</span>');
  } else if (pauta.publicaciones_restantes <= LOW_QUOTA_THRESHOLD) {
    badges.push(`<span class="badge badge-lowquota">cupo bajo (${pauta.publicaciones_restantes})</span>`);
  }

  return badges.join(" ");
}

function renderListaClientes(clientes, pautas) {
  const container = document.getElementById("lista-clientes");
  container.innerHTML = "";

  const pautasPorCliente = new Map();
  for (const pauta of pautas) {
    const lista = pautasPorCliente.get(pauta.client_id) ?? [];
    lista.push(pauta);
    pautasPorCliente.set(pauta.client_id, lista);
  }

  if (clientes.length === 0) {
    container.innerHTML = "<p>Todavía no hay clientes registrados.</p>";
    return;
  }

  for (const client of clientes) {
    const card = document.createElement("div");
    card.className = "client-card";

    const pautasDelCliente = pautasPorCliente.get(client.id) ?? [];
    const filas = pautasDelCliente
      .map(
        (p) => `
        <tr>
          <td data-label="Período">${formatFecha(p.fecha_inicio)} – ${formatFecha(p.fecha_fin)}</td>
          <td data-label="Restantes">${p.publicaciones_restantes}/${p.publicaciones_contratadas}</td>
          <td data-label="Estado">${estadoPautaBadges(p)}</td>
        </tr>`
      )
      .join("");

    card.innerHTML = `
      <h3>${client.nombre} <span class="muted">(${CLIENT_TIPO_LABELS[client.tipo] ?? client.tipo})</span></h3>
      <p class="muted">${client.telefono}${client.instagram ? " · " + client.instagram : ""}</p>
      ${
        pautasDelCliente.length
          ? `<table class="compact responsive-stack">
               <thead><tr><th>Período</th><th>Restantes</th><th>Estado</th></tr></thead>
               <tbody>${filas}</tbody>
             </table>`
          : '<p class="muted">Sin pautas todavía.</p>'
      }
    `;
    container.appendChild(card);
  }
}

// ---------- cola de solicitudes ----------

async function loadSolicitudes() {
  const solicitudes = await apiFetch("/publication-requests?estado=recibida");
  const tbody = document.getElementById("tabla-solicitudes");
  tbody.innerHTML = "";
  pendientesCount = solicitudes.length;

  if (solicitudes.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" class="muted">No hay solicitudes pendientes.</td></tr>';
    renderResumen();
    return;
  }

  // orden de llegada, con las de prioridad manual primero — regla del negocio
  solicitudes.sort((a, b) => {
    if (a.prioridad_manual !== b.prioridad_manual) return a.prioridad_manual ? -1 : 1;
    return a.fecha_recepcion.localeCompare(b.fecha_recepcion);
  });

  for (const solicitud of solicitudes) {
    const pauta = solicitud.pauta_id ? pautasById.get(solicitud.pauta_id) : null;
    const client = pauta ? clientsById.get(pauta.client_id) : null;
    const nombreCliente = client ? client.nombre : "(sin vincular)";
    const esperandoMucho = horasEnEspera(solicitud.fecha_recepcion) >= STALE_REQUEST_HOURS;

    const accionHtml = solicitud.pauta_id
      ? `<button type="button" class="btn-publicar" data-id="${solicitud.id}">Publicar</button>`
      : `<div class="link-pauta">
           <select class="link-pauta-select" data-id="${solicitud.id}">
             <option value="">Elegir pauta…</option>
             ${pautaOptionsHtml(pautasVigentes())}
           </select>
           <button type="button" class="btn-vincular secondary" data-id="${solicitud.id}">
             Vincular
           </button>
         </div>`;

    const tr = document.createElement("tr");
    if (esperandoMucho) tr.className = "row-urgent";
    tr.innerHTML = `
      <td data-label="Recibida">${esperandoMucho ? "⏱ " : ""}${solicitud.fecha_recepcion.slice(0, 16).replace("T", " ")}</td>
      <td data-label="Cliente">${nombreCliente}</td>
      <td data-label="Texto">${solicitud.texto}</td>
      <td data-label="Prioridad">${solicitud.prioridad_manual ? "⚑ Sí" : "—"}</td>
      <td data-label="Acción">${accionHtml}</td>
    `;
    tbody.appendChild(tr);
  }

  for (const btn of tbody.querySelectorAll(".btn-publicar")) {
    btn.addEventListener("click", () => publicarSolicitud(btn.dataset.id));
  }
  for (const btn of tbody.querySelectorAll(".btn-vincular")) {
    btn.addEventListener("click", () => {
      const select = tbody.querySelector(`.link-pauta-select[data-id="${btn.dataset.id}"]`);
      vincularPauta(btn.dataset.id, select.value);
    });
  }

  renderResumen();
}

async function publicarSolicitud(id) {
  try {
    await apiFetch(`/publication-requests/${id}/publish`, { method: "POST" });
    showStatus("Solicitud publicada.", false);
    await Promise.all([loadSolicitudes(), loadClientesYPautas()]);
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

// ---------- formularios ----------

function collapseDetailsOf(form) {
  const details = form.closest("details.collapsible");
  if (details) details.open = false;
}

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
      collapseDetailsOf(event.target);
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
      collapseDetailsOf(event.target);
      await loadClientesYPautas();
    } catch (error) {
      showStatus(error.message, true);
    }
  });
}

// ---------- dashboard comercial (Sprint 4B) ----------
//
// Todo lo que se ve aquí viene tal cual de /dashboard/{resumen,alertas,ranking}
// — esta pantalla no calcula ni reordena nada por su cuenta, solo formatea
// para pantalla (moneda, fechas) lo que ya entrega el backend.

const DASHBOARD_CARDS = [
  ["clientes_activos", "Clientes activos"],
  ["pautas_activas", "Pautas activas"],
  ["pautas_vencidas", "Pautas vencidas"],
  ["solicitudes_pendientes", "Solicitudes pendientes"],
  ["publicaciones_este_mes", "Publicaciones este mes"],
  ["ingreso_contratado_activo", "Ingreso contratado activo"],
  ["ingreso_historico", "Ingreso histórico"],
  ["peso_comercial_promedio", "Peso comercial promedio"],
];

const DASHBOARD_CAMPOS_MONETARIOS = new Set([
  "ingreso_contratado_activo",
  "ingreso_historico",
  "peso_comercial_promedio",
]);

function formatMoneda(valor) {
  return "$" + Number(valor).toLocaleString("es-CO", { maximumFractionDigits: 0 });
}

function renderDashboardResumen(resumen) {
  const el = document.getElementById("dashboard-resumen");
  el.innerHTML = DASHBOARD_CARDS.map(([campo, etiqueta]) => {
    const valor = resumen[campo];
    const texto = DASHBOARD_CAMPOS_MONETARIOS.has(campo) ? formatMoneda(valor) : valor;
    return `
      <div class="dashboard-card">
        <span class="dashboard-card-valor">${texto}</span>
        <span class="dashboard-card-etiqueta">${etiqueta}</span>
      </div>`;
  }).join("");
}

function renderAlertaLista(id, items, formatear) {
  const el = document.getElementById(id);
  el.innerHTML =
    items.length === 0
      ? '<li class="muted">Sin novedades.</li>'
      : items.map((item) => `<li>${formatear(item)}</li>`).join("");
}

function renderDashboardAlertas(alertas) {
  renderAlertaLista("alerta-cupo-agotado", alertas.clientes_cupo_agotado, (c) => c.nombre);
  renderAlertaLista("alerta-por-vencer", alertas.clientes_por_vencer, (c) => c.nombre);
  renderAlertaLista("alerta-cupo-bajo", alertas.clientes_cupo_bajo, (c) => c.nombre);
  renderAlertaLista("alerta-solicitudes-antiguas", alertas.solicitudes_antiguas, (s) => {
    const recibida = s.fecha_recepcion.slice(0, 16).replace("T", " ");
    return `${s.texto} — recibida ${recibida}`;
  });
}

function renderDashboardRanking(ranking) {
  const tbody = document.getElementById("tabla-ranking");
  if (ranking.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="6" class="muted">Todavía no hay clientes con pautas.</td></tr>';
    return;
  }
  tbody.innerHTML = ranking
    .map((item) => {
      const estado = item.vigente
        ? '<span class="badge badge-ok">vigente</span>'
        : '<span class="badge badge-danger">vencido</span>';
      return `
      <tr>
        <td data-label="Cliente">${item.cliente.nombre}</td>
        <td data-label="Valor contratado">${formatMoneda(item.valor_contratado)}</td>
        <td data-label="Peso comercial">${formatMoneda(item.peso_comercial)}</td>
        <td data-label="Publicaciones restantes">${item.publicaciones_restantes}</td>
        <td data-label="Fecha de vencimiento">${formatFecha(item.fecha_vencimiento)}</td>
        <td data-label="Estado">${estado}</td>
      </tr>`;
    })
    .join("");
}

async function loadDashboard() {
  const [resumen, alertas, ranking] = await Promise.all([
    apiFetch("/dashboard/resumen"),
    apiFetch("/dashboard/alertas"),
    apiFetch("/dashboard/ranking"),
  ]);
  renderDashboardResumen(resumen);
  renderDashboardAlertas(alertas);
  renderDashboardRanking(ranking);
}

// ---------- arranque ----------

function setupTabs() {
  for (const btn of document.querySelectorAll(".tab-btn")) {
    btn.addEventListener("click", () => activateTab(btn.dataset.tab));
  }
  activateTab("solicitudes");
}

async function init() {
  setupTabs();
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
