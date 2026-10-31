import logging
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from html import escape

from .config import settings
from .database import SessionLocal
from .models import RegistroCorreo

logger = logging.getLogger("convive.email")

SMTP_TIMEOUT_SECONDS = 15
RESET_SUBJECT = "Recupera tu contraseña de ConVive"

# Paleta del front (fondo oscuro con acento lima).
BG = "#09090b"
CARD = "#18181b"
ACCENT = "#ccff00"
MUTED = "#a1a1aa"


def _build_message(to: str, subject: str, text: str, html: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    return msg


def _send(msg: EmailMessage) -> None:
    context = ssl.create_default_context()
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=SMTP_TIMEOUT_SECONDS) as smtp:
        smtp.starttls(context=context)
        if settings.SMTP_USER:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.send_message(msg)


def reset_email_content(link: str) -> tuple[str, str]:
    minutes = settings.RESET_TOKEN_MINUTES
    text = (
        f"Recibimos una solicitud para cambiar tu contraseña de ConVive.\n\n"
        f"Usa este enlace (vence en {minutes} minutos y solo puede usarse una vez):\n{link}\n\n"
        "Si no lo solicitaste, ignora este mensaje: tu contraseña no cambiará."
    )
    return text, _reset_html(escape(link, quote=True), minutes)


def _reset_html(link: str, minutes: int) -> str:
    """HTML compatible con Gmail: tablas y estilos en línea (sin CSS externo ni imágenes)."""
    font = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
    return f"""\
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark">
<title>{RESET_SUBJECT}</title>
</head>
<body style="margin:0;padding:0;background-color:{BG};">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">
  Elige una nueva contraseña para tu cuenta de ConVive. El enlace vence en {minutes} minutos.
</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="{BG}" style="background-color:{BG};">
  <tr>
    <td align="center" style="padding:40px 16px;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:520px;">
        <tr>
          <td align="left" style="padding:0 8px 24px;font-family:{font};font-size:24px;font-weight:800;letter-spacing:-0.5px;color:#ffffff;">
            Con<span style="color:{ACCENT};">Vive</span>
          </td>
        </tr>
        <tr>
          <td bgcolor="{CARD}" style="background-color:{CARD};border:1px solid #27272a;border-top:3px solid {ACCENT};border-radius:24px;padding:40px 32px;">
            <p style="margin:0;font-family:{font};font-size:12px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:{ACCENT};">
              Recuperar contraseña
            </p>
            <h1 style="margin:12px 0 0;font-family:{font};font-size:30px;line-height:1.15;font-weight:800;letter-spacing:-0.5px;color:#ffffff;">
              Volvamos a <span style="color:{ACCENT};">encontrarnos.</span>
            </h1>
            <p style="margin:16px 0 0;font-family:{font};font-size:15px;line-height:1.6;color:{MUTED};">
              Recibimos una solicitud para cambiar la contraseña de tu cuenta de ConVive.
              Pulsa el botón para elegir una nueva.
            </p>
            <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:28px 0 0;">
              <tr>
                <td align="center" bgcolor="{ACCENT}" style="background-color:{ACCENT};border-radius:999px;">
                  <a href="{link}" target="_blank" style="display:inline-block;padding:14px 32px;font-family:{font};font-size:16px;font-weight:700;color:#0f172a;text-decoration:none;border-radius:999px;">
                    Elegir nueva contraseña
                  </a>
                </td>
              </tr>
            </table>
            <p style="margin:24px 0 0;font-family:{font};font-size:13px;line-height:1.6;color:{MUTED};">
              El enlace vence en <strong style="color:#e4e4e7;">{minutes} minutos</strong>
              y solo puede usarse una vez.
            </p>
            <hr style="border:0;border-top:1px solid #27272a;margin:28px 0 20px;">
            <p style="margin:0;font-family:{font};font-size:12px;line-height:1.6;color:#71717a;">
              Si el botón no funciona, copia y pega este enlace en tu navegador:<br>
              <a href="{link}" target="_blank" style="color:{ACCENT};word-break:break-all;">{link}</a>
            </p>
          </td>
        </tr>
        <tr>
          <td align="center" style="padding:24px 16px 0;font-family:{font};font-size:12px;line-height:1.6;color:#71717a;">
            Si no solicitaste este cambio, ignora este mensaje: tu contraseña no cambiará.<br>
            ConVive · Tu espacio. Tu ritmo. Tu gente.
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
</body>
</html>
"""


def deliver_reset_email(registro_id: int, to: str, link: str) -> None:
    """Tarea en segundo plano: envia el correo y registra el resultado.

    Nunca lanza excepciones: un fallo de SMTP queda como FALLIDO en REGISTRO_CORREO.
    Sin SMTP_HOST (desarrollo) imprime el enlace en consola.
    """
    estado = "ENVIADO"
    try:
        text, html = reset_email_content(link)
        if not settings.SMTP_HOST:
            print(f"[ConVive] Enlace de recuperacion para {to}: {link}")
        else:
            _send(_build_message(to, RESET_SUBJECT, text, html))
    except Exception:  # noqa: BLE001 - cualquier fallo se registra, no se propaga
        logger.exception("No se pudo enviar el correo de recuperacion (registro %s)", registro_id)
        estado = "FALLIDO"

    with SessionLocal() as db:
        registro = db.get(RegistroCorreo, registro_id)
        if registro is not None:
            registro.estado_envio = estado
            registro.fecha_envio = datetime.utcnow()
            db.commit()
