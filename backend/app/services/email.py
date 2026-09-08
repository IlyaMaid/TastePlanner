import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger("tasteplanner.email")


def send_password_reset_email(to_email: str, reset_url: str) -> None:
    subject = "Восстановление пароля TastePlanner"
    body = (
        "Мы получили запрос на восстановление пароля.\n\n"
        f"Перейдите по ссылке, чтобы задать новый пароль:\n{reset_url}\n\n"
        "Ссылка действительна ограниченное время. Если вы не запрашивали "
        "восстановление пароля, просто проигнорируйте это письмо."
    )

    if not settings.smtp_host:
        logger.warning(
            "SMTP is not configured; password reset link for %s: %s",
            to_email,
            reset_url,
        )
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from
    message["To"] = to_email
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_user and settings.smtp_password:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(message)
