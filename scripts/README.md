# Scripts

Vacío intencionalmente durante la fase Foundation.

Aquí vivirán scripts operativos puntuales (inicialización de base de datos,
carga de datos semilla, tareas de mantenimiento manual). Cada script
agregado debe:

- Ser idempotente (poder ejecutarse más de una vez sin efectos no
  deseados).
- Documentar su propósito en un docstring al inicio del archivo.
- Reutilizar `config/settings.py` y `shared/logger.py` en lugar de leer
  configuración o loguear por su cuenta.
