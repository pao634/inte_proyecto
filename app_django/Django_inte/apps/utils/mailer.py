import base64
import os
from typing import Iterable, Optional

import logging
import requests
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


def _send_via_smtp(
    *,
    subject: str,
    text_body: str,
    html_body: Optional[str],
    to: Iterable[str],
    from_email: Optional[str] = None,
    attachments: Optional[list[dict]] = None,
) -> bool:
    mensaje = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_email or settings.DEFAULT_FROM_EMAIL,
        to=list(to),
    )
    if html_body:
        mensaje.attach_alternative(html_body, "text/html")
    for att in attachments or []:
        mensaje.attach(att["filename"], att["content_bytes"], att["mime_type"])
    try:
        mensaje.send()
        logger.info(f"Correo enviado exitosamente vía SMTP a {to}")
        return True
    except Exception as e:
        logger.error(f"Error crítico en SMTP: {str(e)}", exc_info=True)
        return False


def _send_via_sendgrid(
    *,
    subject: str,
    text_body: str,
    html_body: Optional[str],
    to: Iterable[str],
    from_email: str,
    api_key: str,
    attachments: Optional[list[dict]] = None,
) -> bool:
    personalizations = [{"to": [{"email": email} for email in to]}]
    content = [{"type": "text/plain", "value": text_body or ""}]
    if html_body:
        content.append({"type": "text/html", "value": html_body})

    payload: dict = {
        "personalizations": personalizations,
        "from": {"email": from_email},
        "subject": subject,
        "content": content,
    }

    atts = []
    for att in attachments or []:
        atts.append(
            {
                "content": base64.b64encode(att["content_bytes"]).decode("ascii"),
                "filename": att["filename"],
                "type": att["mime_type"],
                "disposition": "attachment",
            }
        )
    if atts:
        payload["attachments"] = atts

    try:
        resp = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15,
        )
        return resp.status_code in (200, 202)
    except Exception as e:
        logger.error(f"Error crítico en SendGrid API: {str(e)}", exc_info=True)
        return False


def send_email(
    *,
    subject: str,
    text_body: str,
    to: Iterable[str],
    html_body: Optional[str] = None,
    attachments: Optional[list[dict]] = None,
    from_email: Optional[str] = None,
) -> bool:
    """
    Envia correo. Si existe SENDGRID_API_KEY se usa SendGrid (HTTPS),
    si no, se usa SMTP (Django EmailMultiAlternatives).
    """
    to_list = [e for e in list(to) if e]
    logger.info(f"Iniciando proceso de envío de correo a: {to_list}")
    if not to_list:
        logger.warning("Intento de envío fallido: Lista de destinatarios vacía.")
        return False

    provider = (os.getenv("EMAIL_PROVIDER") or "").strip().lower()
    sendgrid_key = (os.getenv("SENDGRID_API_KEY") or "").strip()
    
    if provider in ("sendgrid",) or sendgrid_key:
        logger.info(f"Usando proveedor: SendGrid (API Key configurada)")
        from_addr = (os.getenv("SENDGRID_FROM_EMAIL") or from_email or settings.DEFAULT_FROM_EMAIL or "").strip()
        if not sendgrid_key or not from_addr:
            logger.error(f"Error de configuración SendGrid: Faltan llaves o correo de origen (From: {from_addr})")
            return False
        return _send_via_sendgrid(
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            to=to_list,
            from_email=from_addr,
            api_key=sendgrid_key,
            attachments=attachments,
        )

    logger.info(f"Usando proveedor: SMTP (Host: {settings.EMAIL_HOST}, User: {settings.EMAIL_HOST_USER})")
    if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        logger.error("Error de configuración SMTP: Faltan EMAIL_HOST_USER o EMAIL_HOST_PASSWORD en el entorno.")

    return _send_via_smtp(
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        to=to_list,
        from_email=from_email,
        attachments=attachments,
    )

