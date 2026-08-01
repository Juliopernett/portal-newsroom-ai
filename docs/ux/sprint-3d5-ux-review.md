# Sprint 3D.5 — Revisión UX de la interfaz reemplaza-Excel

> Documento de análisis. El hallazgo P2 (#8, "vincular pauta") se
> implementó en Sprint 3E, antes que las mejoras visuales, por decisión
> explícita: cerrar el flujo operativo primero. Los 5 ítems P0 se
> implementaron en Sprint 3F (ver estado junto a cada uno abajo); después
> de ese sprint el desarrollo se detiene deliberadamente para validar el
> sistema en operación real antes de continuar con P1, WhatsApp, IA o
> automatizaciones. Revisa `app/api/static/` (Sprint 3D-UI) contra el uso
> diario real descrito en Domain Discovery (Sprint 3B), no contra un
> ideal abstracto.

## Contexto

La interfaz actual (2 pantallas: Cola de Solicitudes, Clientes y Pautas)
ya se probó de punta a punta en navegador y cumple la Definición de
Terminado de Sprint 3D-UI: un operador puede crear cliente, pauta y
solicitud, y publicar, sin abrir Excel. Esta revisión no cuestiona eso —
cuestiona cuánto tiempo y cuántos clics le toma a alguien haciéndolo
**todo el día**, no una vez para probar.

## Reanálisis del flujo diario

Sin cambios respecto a Domain Discovery (Sprint 3B): la jornada es
mayoritariamente **cola de solicitudes** (llega un WhatsApp → se
registra → en algún momento se publica), con **administración de
clientes/pautas** como tarea ocasional, no constante. La interfaz actual
ya refleja esa separación en dos pestañas — lo que no refleja es la
diferencia de urgencia *dentro* de cada pantalla: hoy todo se ve con el
mismo peso visual, y el operador tiene que leer cada fila para saber si
algo necesita atención ya.

## Respuestas a las preguntas puntuales

**¿Qué información debería verse apenas abrir la aplicación?**
Hoy: un formulario vacío y una tabla, sin ningún resumen. Debería verse,
antes que nada, una respuesta a "¿tengo algo urgente ahora mismo?" — un
conteo de pendientes, pautas por vencer y cupos agotados, visible sin
clics ni cambiar de pestaña. Todos estos datos ya existen en las
respuestas de `/pautas` y `/publication-requests` — no requiere tocar el
backend, solo calcularlo y mostrarlo al cargar.

**¿Qué información falta en la cola de solicitudes?**
Tres cosas, todas ya disponibles en los datos que la interfaz ya trae:
cuánto cupo le queda a la pauta de esa solicitud (para no publicar a
ciegas al último cupo sin saberlo), si esa pauta ya venció (hoy el botón
"Publicar" **no se desactiva** en ese caso — la interfaz no impide ni
advierte que se está por publicar fuera del período contratado), y cuánto
tiempo lleva la solicitud esperando (para distinguir "llegó hace 5
minutos" de "lleva un día sin respuesta").

**¿Qué acciones pueden hacerse con menos clics?**
La que más falta, en realidad, **no se puede hacer con ningún clic
hoy**: no existe manera de vincular una pauta a una solicitud que llegó
sin ella. Se crea sin pauta (comportamiento correcto, Sprint 3B.1), pero
queda huérfana para siempre en la interfaz actual — no hay botón
"vincular" en ningún lado. Es el hallazgo más importante de esta
revisión, y toca la API (ver prioridad P2 más abajo).

**¿Qué formularios ocupan demasiado espacio?**
"Nuevo cliente" y "Nueva pauta" — ambos siempre visibles y expandidos,
empujando hacia abajo la lista de clientes (la información que sí se
consulta seguido) y obligando a hacer scroll incluso en pantallas
normales, como se vio en la prueba de Sprint 3D-UI. Son acciones de baja
frecuencia (un cliente se crea una vez; una pauta, cada renovación) y no
deberían competir en espacio con la lista.

**¿Qué información administrativa puede ocultarse o mostrarse solo
cuando sea necesaria?**
Los dos formularios de creación (colapsados detrás de un botón "+"), y
el historial de solicitudes ya publicadas (hoy invisible por diseño —
está bien que lo siga siendo por defecto, pero hoy no hay ninguna forma
de verlo si hiciera falta revisar algo).

**Indicadores visuales para detectar rápido:**

| Señal | ¿Hay dato hoy? | Notas |
|---|---|---|
| Pautas por vencer | Sí (`fecha_fin`) | Hoy solo existe "vencida" (ya pasó). Falta el estado intermedio "por vencer en N días" — el que de verdad importa para renovar a tiempo. |
| Cupos agotados | Sí (`cuota_agotada`) | Ya existe como badge — funciona bien, no cambiar. |
| Solicitudes urgentes | Parcial | Existe `prioridad_manual` (bandera manual). Falta la urgencia por antigüedad (nadie marca una solicitud como urgente por el simple hecho de llevar horas sin atender). |
| Clientes prioritarios | No | No existe ningún dato de negocio que respalde esto — `Client` no tiene ningún campo de prioridad. Inventar un indicador visual sin un dato real detrás sería decorar, no informar. Alternativa sin tocar el dominio: ordenar/destacar por `valor_pagado` acumulado de sus pautas (dato que ya existe) — pero es una aproximación, no lo mismo que "prioritario", y habría que confirmarlo con el negocio antes de tratarlo como tal. |

## Wireframes

### Cola de Solicitudes (pantalla de entrada)

```
┌──────────────────────────────────────────────────────────────────┐
│ Portal Vallenato     [Cola de Solicitudes*] [Clientes y Pautas]   │
├──────────────────────────────────────────────────────────────────┤
│ ⚠ 3 pautas por vencer esta semana    ⛔ 1 cliente con cupo agotado │  ← nuevo: barra resumen
├────────────────────────────┬───────────────────────────────────────┤
│ Registrar solicitud         │ Pendientes (5)                        │
│ ┌────────────────────────┐ │ ┌────────────────────────────────────┐ │
│ │ Pauta:  [ selector ▾ ] │ │ │ 🔴 09:10 · Silvestre D. · quedan 1  │ │  ← rojo: cupo casi agotado
│ │ Texto:  [____________] │ │ │    "confirmar fecha del concierto"  │ │
│ │ ☐ Prioridad manual      │ │ │                        [Publicar]  │ │
│ │ [ Registrar ]           │ │ ├────────────────────────────────────┤ │
│ └────────────────────────┘ │ │ ⚑ 08:40 · Peter M. · quedan 6       │ │  ← ⚑: prioridad manual
│                             │ │    "anuncio nuevo sencillo"         │ │
│                             │ │                        [Publicar]  │ │
│                             │ ├────────────────────────────────────┤ │
│                             │ │ ⏱ hace 26h · (sin vincular)         │ │  ← urgente por antigüedad
│                             │ │    "información del evento"         │ │
│                             │ │        [Vincular pauta]  [🔒 —]     │ │  ← Publicar deshabilitado y visible por qué
│                             │ └────────────────────────────────────┘ │
└────────────────────────────┴───────────────────────────────────────┘
```

### Clientes y Pautas (formularios colapsados)

```
┌──────────────────────────────────────────────────────────────────┐
│ Portal Vallenato     [Cola de Solicitudes] [Clientes y Pautas*]   │
├──────────────────────────────────────────────────────────────────┤
│ [+ Nuevo cliente]   [+ Nueva pauta]                (Actualizar)   │  ← formularios ocultos por defecto
├──────────────────────────────────────────────────────────────────┤
│ 🔴 Peter Manjarrés (Artista)                  cupo agotado  10/10 │
│    +57 300 444 5566 · 2026-07-01 – 2026-07-31                     │
├──────────────────────────────────────────────────────────────────┤
│ 🟡 Churo Díaz (Artista)                     vence en 4 días  2/10 │  ← amarillo: por vencer
│    +57 300 222 1122 · 2026-07-27 – 2026-08-04                     │
├──────────────────────────────────────────────────────────────────┤
│ 🟢 Silvestre Dangond (Artista)                    vigente   9/10  │
│    +57 300 111 2233 · 2026-07-30 – 2026-08-30                     │
└──────────────────────────────────────────────────────────────────┘
```

Al hacer clic en "+ Nueva pauta" o "+ Nuevo cliente", el formulario
correspondiente se expande in situ (acordeón), sin navegar a otra
pantalla ni perder el contexto de la lista.

## Lista priorizada de mejoras

**P0 — alto impacto, no requieren tocar el backend** (todo el dato ya
está en las respuestas de `/pautas` y `/publication-requests`, es
cálculo y presentación en el frontend):

1. ✅ **Resuelto en Sprint 3F.** Barra de resumen al abrir (pendientes / por vencer / cupos agotados) — visible en ambas pestañas, no solo en la de Solicitudes.
2. ✅ **Resuelto en Sprint 3F.** Badge "vence en Nd" en pautas (≤7 días, umbral visual), además del "vencida" actual. También se agregó "cupo bajo (N)" (≤2 restantes, no confundir con "cupo agotado") — ambos en la pestaña Clientes y Pautas, junto a los badges existentes de cada pauta.
3. ⚠️ **Implementado distinto de lo propuesto.** No se resaltó "cupo bajo" fila por fila en la cola de solicitudes (hubiera requerido rediseñar la tabla) — el dato ya es visible al revisar la pauta correspondiente en la otra pestaña. Si en el uso real esto resulta insuficiente, es candidato para un ajuste puntual, no un sprint nuevo.
4. ✅ **Resuelto en Sprint 3F.** Solicitudes con ≥4 horas esperando (umbral visual, no de negocio) se resaltan en la cola con un ícono de reloj y un borde de color.
5. ✅ **Resuelto en Sprint 3F.** "Nuevo cliente" y "Nueva pauta" ahora son `<details>` colapsados por defecto, y se vuelven a colapsar automáticamente después de crear con éxito.

**P1 — impacto medio, tampoco requieren backend:**

6. Advertir visualmente (no solo deshabilitar) cuando una solicitud está vinculada a una pauta ya vencida, antes de intentar publicarla.
7. Truncar el texto largo en la tabla de la cola, con opción de expandir.

**P2 — requieren tocar la API (fuera de alcance de un sprint de solo-UX, a decidir aparte):**

8. ✅ **Resuelto en Sprint 3E.** Acción "vincular pauta" sobre una solicitud ya `RECIBIDA` sin pauta — `POST /publication-requests/{id}/link-pauta`, expone `core.services.publication_request_service.link_pauta`. Verificado en navegador real de punta a punta.
9. **"Cliente prioritario"** — no se implementa hasta que el negocio confirme qué significa realmente (¿el que más paga? ¿el que más pautas activas tiene? ¿uno marcado a mano?). Inventar la respuesta en el frontend sería adivinar, no diseñar.

## Qué no se tocó en este sprint

Ningún archivo de código — ni `app/api/static/`, ni la API, ni el
dominio. Este documento es la base para decidir, en un próximo sprint de
UI, cuáles de las mejoras P0/P1 se implementan (todas son seguras y no
tocan el backend), y si P2 amerita su propio sprint pequeño de API antes
de construir la acción de "vincular pauta" en la interfaz.
