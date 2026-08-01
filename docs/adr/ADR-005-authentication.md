# ADR-005: Login MVP — sesiones server-side con Argon2id, alcance mínimo

- **Estado:** Aceptado
- **Fecha:** 2026-08-01 (Sprint — Login MVP)
- **Contexto del documento:** ver [ADR-001](ADR-001-project-vision.md) para
  las convenciones de formato.

## Contexto

El deploy a Railway (`master`, ver `CHANGELOG.md`) expone la aplicación en
una URL pública, con datos reales de clientes comerciales (teléfonos,
montos pagados vía `Pauta.valor_pagado`/`peso_comercial`). Hasta ahora,
autenticación estaba explícitamente **fuera del MVP**
(`docs/product/MVP_SCOPE.md`, sección "Fuera del MVP": *"Autenticación y
cuentas de usuario — hoy no hay 'usuarios del sistema'"*), una decisión
correcta mientras el sistema solo corría en local. Ese supuesto ya no es
válido una vez que la URL es pública — este ADR revierte esa exclusión,
deliberadamente y por escrito, no en silencio.

## Decisión 1 — Sesiones server-side en Postgres, no JWT

`Session` (`core/entities/session.py`) se persiste en base de datos,
referenciada por un token opaco de alta entropía
(`secrets.token_urlsafe(32)`) en una cookie `httpOnly`/`Secure` (en
producción)/`SameSite=Lax`. Se descartó JWT: con sesiones en base de
datos, revocar una sesión específica (ej. "se robó un dispositivo del
equipo") es un `DELETE` inmediato — con JWT stateless eso requiere una
lista de revocación, que termina siendo la misma tabla por otro nombre.
JWT es la herramienta correcta para autenticación API-a-API sin estado
compartido, no para el login clásico de una aplicación web como esta, con
un backend único y con estado.

El token crudo nunca se guarda — solo su hash SHA-256
(`core.ports.session_repository.SessionRepository.get_by_token_hash`,
nunca `get_by_token`), la misma disciplina que ya aplica
`User.password_hash` a las contraseñas: una fuga de la base de datos sola
no alcanza para robar una sesión activa.

## Decisión 2 — Argon2id, detrás de un puerto, nunca en `core/`

`core.ports.password_hasher.PasswordHasher` es un `Protocol` sin ninguna
dependencia; `security/password_hasher.py` (paquete nuevo, par de
`database/`) implementa `Argon2IdPasswordHasher` sobre `argon2-cffi`.
Igual que SQLAlchemy nunca aparece en `core/entities/`, `argon2-cffi`
—una librería criptográfica de terceros— tampoco: `core/` sigue sin
depender de infraestructura externa, ni siquiera para algo tan central
como el login.

Argon2id es la variante recomendada por OWASP hoy (ganadora de la
Password Hashing Competition) — se usan los parámetros por defecto de
`argon2-cffi`, sin ajuste manual: no hay razón para desconfiar de los
defaults de la librería a esta escala de equipo.

## Decisión 3 — Alcance estrictamente MVP, todo lo demás explícitamente pospuesto

Implementado en este sprint:

- `User`, `Session` (entidades + puertos + repositorios SQLAlchemy)
- `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`
- Protección de **todos** los endpoints existentes
  (`/clients`, `/pautas`, `/publication-requests`) vía
  `APIRouter(dependencies=[Depends(get_current_user)])` — a nivel de
  router, no por función, para que cualquier endpoint agregado después
  quede protegido automáticamente, sin depender de que alguien se acuerde.
- `scripts/create_user.py` — la única forma de crear una cuenta; no hay
  registro público ni endpoint de gestión de usuarios.

Explícitamente fuera de alcance, por decisión consciente, no por olvido:

| Diferido | Por qué |
|---|---|
| Invitaciones | Requiere email — pospuesto junto con SMTP |
| Reset de contraseña | Mismo motivo — sin email, el admin resetea manualmente vía `scripts/create_user.py` recreando el registro si hace falta |
| 2FA (TOTP) | Complejidad adicional sin urgencia real para un equipo pequeño en esta etapa |
| Bloqueo por intentos fallidos | Ninguna señal hoy de que haga falta; se agrega si se detecta abuso real |
| SMTP | Sin usarse todavía en ningún flujo de este sprint |
| Gestión avanzada de usuarios (roles, activar/desactivar, listar) | Un solo nivel de acceso: autenticado o no — no hay todavía ninguna decisión de negocio que dependa de distinguir usuarios entre sí |

Ver conversación de diseño para el detalle completo de por qué se
descartó JWT, WebAuthn/passkeys y OAuth con Google como alternativas —
resumen: costo de implementación y dependencias externas (email,
proveedor OAuth) desproporcionados para el tamaño actual del equipo y la
urgencia real (destrabar el deploy con datos sensibles), no un rechazo
de esas alternativas para el futuro.

## Consecuencias

- `docs/product/MVP_SCOPE.md` se actualiza: autenticación pasa de "fuera
  del MVP" a "dentro, alcance mínimo" — con referencia a este ADR.
- Ningún endpoint existente cambia su forma (`ClientOut`, `PautaOut`,
  `PublicationRequestOut` no ganan campos) — solo ganan un requisito
  previo (sesión válida) para poder llamarse.
- `tests/integration/api/conftest.py`: el fixture `client` pasa a
  autenticarse automáticamente (crea un usuario de prueba y hace login
  real vía `POST /auth/login`) — ningún test existente de Sprints
  anteriores necesitó cambiar su código, solo heredó el nuevo
  comportamiento del fixture. `unauthenticated_client` queda disponible
  para los tests que verifican específicamente el rechazo sin sesión.
- La interfaz (`app/api/static/`) gana una pantalla de login y un botón
  de cerrar sesión — sin este cambio, el resto de la UI quedaría
  inalcanzable detrás de los 401 de la API.
