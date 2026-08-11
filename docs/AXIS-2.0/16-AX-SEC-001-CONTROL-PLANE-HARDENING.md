# AX-SEC-001 — Control Plane Hardening

## Objetivo

Cerrar el plano de control interno de AXIS sin modificar estrategias, señales,
parámetros de trading ni el flujo funcional de Telegram.

## Controles aplicados

- `AXIS_ADMIN_TOKEN` obligatorio para APIs internas, enviado exclusivamente en
  el header `X-AXIS-Admin-Token` y comparado en tiempo constante.
- `TELEGRAM_WEBHOOK_SECRET` obligatorio para `/telegram_webhook`, validado con
  el header oficial `X-Telegram-Bot-Api-Secret-Token`; el callback también debe
  pertenecer a `TELEGRAM_CHAT_ID`.
- Todas las rutas que mutan estado usan `POST`; controles, portfolio, Derby,
  canales, bitácora, journal y envíos manuales quedan autenticados.
- Datos operativos, alertas, portfolio, velas, canales, análisis, estado,
  diagnóstico y código fuente requieren token administrativo.
- CORS acepta solamente el dashboard desplegado por AXIS. No se mantienen
  secretos ni contraseñas por defecto en URL o código fuente.
- Las dashboards internas solicitan el token una vez por sesión de navegador
  y lo guardan en `sessionStorage`, nunca dentro del HTML ni en query strings.

## Operación

El token administrativo se administra en Railway y se conserva localmente en
`.axis-admin-token`, archivo ignorado por Git. Para usar una dashboard interna,
abrirla desde el dominio de producción e ingresar el token cuando lo solicite.

`/version` permanece público para salud de despliegue. Todo endpoint interno
debe recibir `X-AXIS-Admin-Token`; los cambios de estado deben hacerse por
`POST`.

## Verificación requerida tras despliegue

1. `/version` responde `OK` sin autenticación.
2. `/status` rechaza solicitudes sin token y responde con token.
3. Un callback de Telegram con secreto se procesa; sin secreto devuelve 403.
4. Las dashboards cargan datos y sus acciones autorizadas usan POST.
