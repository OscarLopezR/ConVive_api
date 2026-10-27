import smtplib
from email.message import EmailMessage

from .config import settings


def send_reset_email(to: str, link: str) -> None:
    """Envia el enlace de recuperacion. Sin SMTP configurado, lo imprime en consola."""
    if not settings.SMTP_HOST:
        print(f"[ConVive] Enlace de recuperacion para {to}: {link}")
        return

    msg = EmailMessage()
    msg["Subject"] = "Recupera tu contrasena de ConVive"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg.set_content(
        f"Usa este enlace para elegir una nueva contrasena (vence en "
        f"{settings.RESET_TOKEN_MINUTES} minutos):\n\n{link}\n\n"
        "Si no lo solicitaste, ignora este mensaje."
    )
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
        smtp.starttls()
        if settings.SMTP_USER:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.send_message(msg)
