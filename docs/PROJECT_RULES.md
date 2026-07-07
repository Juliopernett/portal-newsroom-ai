# Reglas del proyecto

Estas reglas no son sugerencias: son restricciones de diseño. Cualquier
Pull Request que las viole debe rechazarse, sin excepción.

## 1. El sistema nunca publica automáticamente

Ningún agente, workflow, ni script puede publicar contenido directamente en
WordPress ni en redes sociales. El resultado máximo permitido de cualquier
pipeline automatizado es un **borrador** más una **notificación** al equipo
editorial. La publicación final es siempre una acción humana explícita.

## 2. Toda configuración proviene de `.env`

Ningún módulo fuera de `config/settings.py` debe leer `os.environ`
directamente. Toda variable de entorno nueva se declara primero en
`config/settings.py` y se documenta en `.env.example`.

## 3. Todo módulo/agente debe ser independiente y reemplazable

Los agentes dependen de contratos (`core/ports/`), nunca de una librería o
servicio externo concreto de forma directa. Ver
[ARCHITECTURE.md](ARCHITECTURE.md).

## 4. No duplicar código (DRY)

Si una misma pieza de lógica se necesita en dos lugares, se extrae a
`core/`, `shared/` o un módulo común — no se copia.

## 5. Todo componente debe ser testeable

Toda función o clase pública debe poder probarse sin red, sin credenciales
reales y sin depender de servicios externos disponibles. Esto se logra
dependiendo de los `ports` definidos en `core/`, no de sus adaptadores.

## 6. Registrar logs importantes

Cualquier acción relevante para el negocio (contenido detectado, borrador
creado, notificación enviada, duplicado descartado, error de integración)
debe registrarse vía `shared/logger.py`. No usar `print()` en código de
producción.

## 7. Mantener tipado estricto

Todo el código de producción debe pasar `mypy --strict`. No se permite
`Any` salvo justificación explícita en comentario.

## 8. Usar nombres claros

Los nombres de funciones, clases y variables deben ser explícitos y reflejar
el vocabulario del negocio (noticia, borrador, aprobación, fuente,
duplicado), no abreviaturas ambiguas.

## 9. Documentar funciones públicas

Toda función, clase o método público debe tener docstring explicando su
propósito. Ver [CODING_STANDARDS.md](CODING_STANDARDS.md).

## 10. Registrar todo cambio importante

Todo cambio notable (nueva funcionalidad, cambio de comportamiento,
corrección de bug relevante) se documenta en `CHANGELOG.md`.

## 11. Evitar contenido duplicado

Ninguna noticia se procesa dos veces. La deduplicación se resuelve a nivel
de dominio contra el historial editorial persistido, no con heurísticas ad
hoc dentro de un agente individual.

## 12. Nunca commitear secretos

El archivo `.env` nunca se sube al repositorio (ver `.gitignore`). Las
claves de API, tokens y contraseñas viven únicamente en `.env` local o en
el gestor de secretos del entorno de despliegue.
