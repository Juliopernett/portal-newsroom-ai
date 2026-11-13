# Respaldos de la base de datos

Cada noche un servicio cron de Railway hace una copia completa de Postgres
(`pg_dump`, formato comprimido), la sube a un bucket privado compatible con S3
(Cloudflare R2) y conserva las últimas 30. Si algo falla, el cron termina con
error y Railway avisa por correo (Notificaciones → "Deployment Failed/Crashed").

## 1. Crear el bucket en Cloudflare R2 (una sola vez, lo hace el dueño)

1. Cloudflare → **R2 Object Storage** → crear bucket privado, por ejemplo `newsroom-respaldos`
   (sin acceso público). El plan gratuito incluye 10 GB.
2. R2 → **Manage API Tokens** → *Create API token* con permiso **Object Read & Write**
   limitado a ese bucket. Cloudflare muestra una sola vez el `Access Key ID` y el
   `Secret Access Key`.
3. Anota el endpoint de S3: `https://<ID_DE_CUENTA>.r2.cloudflarestorage.com`.

## 2. Variables en Railway (las pone el dueño, nunca en el chat ni en el repo)

En el servicio nuevo `respaldo-base-datos`:

| Variable | Valor |
|---|---|
| `DATABASE_URL` | la misma del servicio web (referencia a Postgres) |
| `RESPALDO_S3_ENDPOINT` | `https://<ID_DE_CUENTA>.r2.cloudflarestorage.com` |
| `RESPALDO_S3_BUCKET` | `newsroom-respaldos` |
| `RESPALDO_S3_ACCESS_KEY_ID` | el Access Key ID |
| `RESPALDO_S3_SECRET_ACCESS_KEY` | el Secret Access Key |
| `RESPALDO_CONSERVAR` | (opcional) cuántas copias guardar, 30 por defecto |

## 3. Servicio cron en Railway

- Repo: el mismo (`portal-newsroom-ai`), rama `master`.
- **Start command:** `python -m scripts.respaldar_base`
- **Cron schedule:** `0 8 * * *` (08:00 UTC = 03:00 hora de Colombia).

## 4. Probar que funciona

Con el servicio creado, pulsa **Run now** una vez. En los registros debe salir
`[respaldo] OK newsroom/2026/newsroom-AAAA-MM-DDTHHMMZ.dump (X MB)` y el archivo
aparece en el bucket. Si sale `ERROR`, el mensaje dice qué falta.

## 5. Restaurar (en una emergencia)

1. Descarga el `.dump` más reciente desde el bucket de R2.
2. Crea una base Postgres **vacía** (nueva, en Railway o local).
3. Ejecuta:

   ```bash
   pg_restore --no-owner --no-privileges --dbname "postgresql://USUARIO:CLAVE@HOST:5432/BASE" respaldo.dump
   ```

4. Apunta `DATABASE_URL` del servicio web a esa base y reinícialo.

**Haz una restauración de prueba al menos una vez** (en una base local o de
prueba): una copia que nunca se ha restaurado no es una garantía.

## Notas

- `pg_dump` debe ser de la misma versión mayor que el Postgres de Railway o más nueva (hoy 18). Si Railway sube Postgres, cambia `PG_CLIENT_MAJOR` en `docker/Dockerfile`; el error típico es «server version mismatch».
- La copia contiene datos sensibles (clientes, contratos, finanzas): el bucket debe
  ser privado y las claves solo viven en las variables de Railway.
- El volumen de archivos multimedia (`portal-newsroom-ai-volume`) **no** entra en
  esta copia; solo la base de datos.
- Retención: se borran las copias más antiguas solo después de verificar que la
  nueva se guardó con el tamaño correcto.
