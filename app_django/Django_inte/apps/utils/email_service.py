import os
from io import BytesIO
from datetime import datetime
import threading
import gridfs
import logging

logger = logging.getLogger(__name__)

from django.conf import settings

from config.database.mongo import db
from apps.utils.mailer import send_email

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# ==========================================================
#  Utilidades de Email
# ==========================================================

def enviar_correo(destinatario, datos):
    """
    Genera un PDF y envía un correo de confirmación de solicitud.
    """
    # ======================================================
    #  Generar PDF
    # ======================================================
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=42,
        bottomMargin=42,
    )

    styles = getSampleStyleSheet()
    elements = []

    # Paleta y Estilos
    primary = colors.HexColor("#1f3c88")
    soft_bg = colors.HexColor("#f5f7fb")
    border = colors.HexColor("#e5e7eb")

    title_style = ParagraphStyle(name="Title", parent=styles["Title"], fontSize=20, textColor=colors.white, leading=22)
    subtitle_style = ParagraphStyle(name="Subtitle", parent=styles["Normal"], fontSize=11, textColor=colors.white)
    section_style = ParagraphStyle(name="Section", parent=styles["Heading2"], fontSize=13, textColor=primary, spaceBefore=14, spaceAfter=8)
    label_style = ParagraphStyle(name="Label", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#6b7280"), leading=12)
    value_style = ParagraphStyle(name="Value", parent=styles["Normal"], fontSize=11.5, textColor=colors.HexColor("#111827"), leading=14)
    note_style = ParagraphStyle(name="Note", parent=styles["Normal"], fontSize=10.5, textColor=colors.HexColor("#374151"), leading=14)

    # Encabezado
    header_data = [
        [Paragraph("Cedula de inscripcion", title_style), Paragraph("Estado: En proceso", ParagraphStyle(name="Badge", parent=styles["Normal"], fontSize=10, textColor=colors.white, alignment=1))],
        [Paragraph("Solicitud de ingreso a la incubadora • Formato de evaluacion de emprendimientos", subtitle_style), ""]
    ]
    header = Table(header_data, colWidths=[360, 120])
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), primary),
        ("SPAN", (0, 1), (1, 1)),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 18),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
    ]))
    elements.append(header)
    elements.append(Spacer(1, 14))

    # Resumen y Tablas de datos
    resumen_data = [[Paragraph("Nombre completo", label_style), Paragraph(datos.get("nombre_completo", ""), value_style), Paragraph("Correo", label_style), Paragraph(datos.get("correo", ""), value_style)]]
    resumen = Table(resumen_data, colWidths=[90, 190, 70, 130])
    resumen.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), soft_bg),
        ("BOX", (0, 0), (-1, -1), 0.6, border),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, border),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(resumen)
    elements.append(Spacer(1, 18))

    # Info Personal
    elements.append(Paragraph("Informacion personal", section_style))
    info_p = Table([
        [Paragraph("Carrera", label_style), Paragraph(datos.get("carrera", ""), value_style)],
        [Paragraph("Matricula", label_style), Paragraph(datos.get("matricula", ""), value_style)],
        [Paragraph("Telefono", label_style), Paragraph(datos.get("telefono", ""), value_style)],
    ], colWidths=[120, 320])
    info_p.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, border),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, soft_bg]),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(info_p)
    elements.append(Spacer(1, 18))

    # Info Proyecto
    elements.append(Paragraph("Informacion del emprendimiento", section_style))
    info_e = Table([
        [Paragraph("Nombre del proyecto", label_style), Paragraph(datos.get("nombre_proyecto", ""), value_style)],
        [Paragraph("Descripcion", label_style), Paragraph(datos.get("descripcion_negocio", ""), value_style)],
    ], colWidths=[140, 300])
    info_e.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, border),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, soft_bg]),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(info_e)
    elements.append(Spacer(1, 16))

    # Fecha y Firmas
    fecha_actual = datetime.now().strftime("%d/%m/%Y")
    nota_p = Paragraph(f"Fecha de solicitud: {fecha_actual}<br/>Revisaremos tu solicitud y te enviaremos los siguientes pasos.", note_style)
    nota = Table([[nota_p]], colWidths=[440])
    nota.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff7ed")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#fdba74")),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    elements.append(nota)
    elements.append(Spacer(1, 24))

    firmas = Table([["_____________________________", "_____________________________"], ["Firma del Alumno", "Firma del Asesor Academico"]], colWidths=[220, 220])
    firmas.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("TOPPADDING", (0, 0), (-1, -1), 10)]))
    elements.append(firmas)

    doc.build(elements)
    pdf_content = buffer.getvalue()
    buffer.close()

    # ======================================================
    #  Mensaje HTML - Diseño Premium (Match Screenshot)
    # ======================================================
    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 0; background-color: #0b1021; }}
        </style>
    </head>
    <body>
        <table align="center" width="100%" cellpadding="0" cellspacing="0" style="background-color: #0b1021; padding: 40px 0;">
            <tr>
                <td>
                    <table align="center" width="600" cellpadding="0" cellspacing="0" style="background: linear-gradient(180deg, #3b82f6 0%, #1d4ed8 100%); border-radius: 20px; overflow: hidden; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3); color: #ffffff;">
                        <!-- Header -->
                        <tr>
                            <td style="padding: 40px 20px; text-align: center;">
                                <div style="font-size: 40px; margin-bottom: 10px;">🚀</div>
                                <h1 style="margin: 0; font-size: 28px; font-weight: 700; color: #fff;">Incubadora de Proyectos</h1>
                                <p style="margin: 5px 0 0 0; font-size: 16px; opacity: 0.9;">Universidad Tecnológica de Acapulco</p>
                            </td>
                        </tr>
                        <!-- Divider -->
                        <tr>
                            <td style="padding: 0 40px;">
                                <div style="height: 1px; background: rgba(255,255,255,0.15);"></div>
                            </td>
                        </tr>
                        <!-- Body -->
                        <tr>
                            <td style="padding: 40px;">
                                <h2 style="margin: 0 0 20px 0; font-size: 24px; color: #fff;">Hola {datos.get('nombre_completo', 'Emprendedor')} ✨</h2>
                                <p style="font-size: 16px; line-height: 1.6; margin-bottom: 20px; color: #fff;">
                                    Recibimos tu solicitud de ingreso a la incubadora. En las próximas 48 horas revisaremos tu información y te contactaremos con los siguientes pasos.
                                </p>
                                <p style="font-size: 16px; line-height: 1.6; margin-bottom: 30px; color: #fff;">
                                    Adjuntamos tu cédula de inscripción en PDF para que la conserves y la compartas con tu equipo. 📄
                                </p>
                                
                                <!-- Badge/Button -->
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td>
                                            <div style="background: #fbbf24; border-radius: 12px; padding: 15px 25px; display: inline-block; color: #111827; font-weight: 700; font-size: 16px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.15);">
                                                📎 Cédula de inscripción (PDF adjunto)
                                            </div>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        <!-- Footer -->
                        <tr>
                            <td style="padding: 0 40px 40px 40px; color: rgba(255,255,255,0.8); font-size: 14px; line-height: 1.5; text-align: left;">
                                <p style="margin: 0;">Responde a este correo y con gusto te ayudaremos. ¡Estamos listos para despegar contigo!</p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    ok = send_email(
        subject="Confirmacion de solicitud a la incubadora",
        text_body="Recibimos tu solicitud. Revisa el documento adjunto.",
        html_body=html,
        to=[destinatario],
        attachments=[{
            "filename": "Cedula_Inscripcion.pdf",
            "content_bytes": pdf_content,
            "mime_type": "application/pdf",
        }],
    )

    if ok:
        logger.info(f"Confirmación de solicitud enviada exitosamente a {destinatario}")
        return True

    logger.error(f"Fallo el envío de confirmación de solicitud a {destinatario}")
    return False

def enviar_correo_async(destinatario, datos):
    thread = threading.Thread(target=enviar_correo, args=(destinatario, datos))
    thread.daemon = True
    thread.start()
    return True

def notificar_equipo_contrato(contrato_id, estado, motivo=None):
    thread = threading.Thread(target=_background_notificar_equipo_contrato, args=(contrato_id, estado, motivo))
    thread.start()
    return True

def _background_notificar_equipo_contrato(contrato_id, estado, motivo=None):
    try:
        from bson.objectid import ObjectId
        contrato = db.contrato_proyecto.find_one({"_id": ObjectId(str(contrato_id))})
        if not contrato: return False
        
        usuario_id = contrato.get("usuario_id")
        user = db.usuarios.find_one({"_id": ObjectId(str(usuario_id))})
        if not user: return False

        # Notificar al líder y equipo si existe
        correo_lider = (user.get("correo") or "").strip().lower()
        proyecto = db.proyectos.find_one({"$or": [{"usuario_id": str(usuario_id)}, {"correo_usuario": correo_lider}]})
        
        destinatarios = [correo_lider]
        if proyecto and proyecto.get("integrantes"):
            for m in proyecto["integrantes"]:
                email = m.get("correo") if isinstance(m, dict) else m
                if email and email not in destinatarios: destinatarios.append(email)

        for email in destinatarios:
            _enviar_correo_individual_contrato(email, "Emprendedor", estado, motivo, proyecto.get("nombre_proyecto") if proyecto else "Tu Proyecto")
        return True
    except Exception as e:
        print(f"Error en notificar_equipo_contrato: {e}")
        return False

def _enviar_correo_individual_contrato(destinatario, nombre, estado, motivo=None, proyecto_nombre="Tu Proyecto"):
    portal_url = os.getenv("PORTAL_URL", "https://incubadora-ut.onrender.com/login/")
    if estado.lower() == "aceptado":
        sub = f"✅ Contrato Aceptado - {proyecto_nombre}"
        msg = f"Tu contrato para <strong>{proyecto_nombre}</strong> ha sido aprobado."
        color = "#059669"
    else:
        sub = f"⚠️ Ajustes en Contrato - {proyecto_nombre}"
        msg = f"Se requieren ajustes en el contrato de <strong>{proyecto_nombre}</strong>."
        color = "#e11d48"

    motivo_html = f"<div style='background:#fef2f2; padding:15px; border-left:4px solid #f43f5e;'><strong>Nota:</strong> {motivo}</div>" if motivo else ""

    html = f"""
    <div style="font-family:sans-serif; max-width:600px; margin:auto; border:1px solid #eee; border-radius:10px; overflow:hidden;">
        <div style="background:{color}; color:white; padding:20px; text-align:center;"><h2>{sub}</h2></div>
        <div style="padding:20px;">
            <p>Hola,</p>
            <p>{msg}</p>
            {motivo_html}
            <div style="text-align:center; margin:30px;"><a href="{portal_url}" style="background:#1f3c88; color:white; padding:12px 20px; text-decoration:none; border-radius:5px;">Ir al Portal</a></div>
        </div>
    </div>
    """
    
    return send_email(
        subject=sub,
        text_body=msg,
        html_body=html,
        to=[destinatario],
    )

def enviar_certificado_finalizacion(destinatario, nombre, proyecto_nombre, archivo_bin, nombre_archivo="Certificado.pdf"):
    thread = threading.Thread(
        target=_background_enviar_certificado,
        args=(destinatario, nombre, proyecto_nombre, archivo_bin, nombre_archivo)
    )
    thread.start()
    return True

def _background_enviar_certificado(destinatario, nombre, proyecto_nombre, archivo_bin, nombre_archivo):
    sub = f"🎓 ¡Felicidades! Proyecto Finalizado - {proyecto_nombre}"
    html = f"""
    <div style="font-family:sans-serif; text-align:center; padding:40px;">
        <h1>¡Felicidades {nombre}!</h1>
        <p>Has concluido exitosamente el proyecto <strong>{proyecto_nombre}</strong>.</p>
        <p>Adjuntamos tu certificado oficial.</p>
    </div>
    """
    return send_email(
        subject=sub,
        text_body=sub,
        html_body=html,
        to=[destinatario],
        attachments=[{
            "filename": nombre_archivo,
            "content_bytes": archivo_bin,
            "mime_type": "application/pdf",
        }],
    )
def enviar_confirmacion_registro(destinatario, nombre, password, request=None):
    """
    Correo de bienvenida con credenciales (Bulk/Individual).
    """
    portal_url = request.build_absolute_uri('/login/') if request else os.getenv("PORTAL_URL", "https://incubadora-ut.onrender.com/login/")
    
    subject = "🚀 ¡Felicidades! Tu proyecto ha sido aceptado"
    html = f"""
    <html>
    <body style="margin:0; font-family: 'Inter', 'Segoe UI', Arial, sans-serif; background-color: #f8fafc; color: #1e293b;">
        <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);">
            <div style="background: linear-gradient(135deg, #1f3c88 0%, #2f5fcb 100%); padding: 40px 20px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 28px;">¡Grandes noticias!</h1>
            </div>
            <div style="padding: 40px 30px;">
                <p style="font-size: 18px; margin-top: 0;">Hola <strong>{nombre}</strong>,</p>
                <p style="line-height: 1.6; font-size: 16px;">Nos complace informarte que tu solicitud para formar parte de la <strong>Incubadora de Empresas</strong> ha sido <strong>ACEPTADA</strong>.</p>
                <div style="background-color: #f1f5f9; border-radius: 12px; padding: 25px; margin: 30px 0; border: 1px solid #e2e8f0;">
                    <p style="margin-top: 0; font-weight: 600; color: #1f3c88;">Tus credenciales de acceso:</p>
                    <ul style="list-style: none; padding: 0; margin: 0;">
                        <li style="margin-bottom: 10px;">📧 <strong>Correo:</strong> {destinatario}</li>
                        <li>🔑 <strong>Contraseña temporal:</strong> <code style="background: #ffffff; padding: 2px 6px; border-radius: 4px; border: 1px solid #d1d5db;">{password or '—'}</code></li>
                    </ul>
                </div>
                <div style="text-align: center; margin-top: 30px;">
                    <a href="{portal_url}" style="display: inline-block; background-color: #1f3c88; color: #ffffff; padding: 14px 28px; border-radius: 10px; text-decoration: none; font-weight: 700; font-size: 16px; box-shadow: 0 4px 6px -1px rgba(31, 60, 136, 0.3);">Acceder al Portal</a>
                </div>
                <p style="margin-top: 40px; font-size: 14px; text-align: center; color: #64748b;">Este es un mensaje automático, por favor no respondas a este correo.</p>
            </div>
            <div style="background-color: #f8fafc; padding: 20px; text-align: center; border-top: 1px solid #e2e8f0;">
                <p style="margin: 0; font-size: 12px; color: #94a3b8;">&copy; 2026 Incubadora de Empresas. Todos los derechos reservados.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return send_email(subject=subject, text_body="Tu solicitud ha sido aceptada.", html_body=html, to=[destinatario])


def enviar_credenciales_equipo_lider(destinatario_lider, nombre_lider, credenciales_equipo, request=None):
    """
    Envia al lider un correo con todas las credenciales del equipo.

    credenciales_equipo: lista de dicts [{nombre, correo, password}]
    """
    raise NotImplementedError(
        "Función desactivada: ahora se envían correos individuales a cada integrante."
    )
    portal_url = request.build_absolute_uri('/login/') if request else os.getenv("PORTAL_URL", "https://incubadora-ut.onrender.com/login/")

    subject = "✅ Credenciales del equipo - Incubadora de Empresas"

    rows = ""
    for c in (credenciales_equipo or []):
        n = (c.get("nombre") or "Integrante")
        e = (c.get("correo") or "")
        p = (c.get("password") or "—")
        rows += f"""
            <tr>
                <td style="padding:10px 12px; border-bottom:1px solid #e2e8f0;">{n}</td>
                <td style="padding:10px 12px; border-bottom:1px solid #e2e8f0;">{e}</td>
                <td style="padding:10px 12px; border-bottom:1px solid #e2e8f0;"><code style="background:#ffffff; padding:2px 6px; border-radius:4px; border:1px solid #d1d5db;">{p}</code></td>
            </tr>
        """

    html = f"""
    <html>
    <body style="margin:0; font-family: 'Inter', 'Segoe UI', Arial, sans-serif; background-color: #f8fafc; color: #1e293b;">
        <div style="max-width: 680px; margin: 40px auto; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);">
            <div style="background: linear-gradient(135deg, #1f3c88 0%, #2f5fcb 100%); padding: 36px 20px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 26px;">Credenciales del Equipo</h1>
                <p style="color:#e0e7ff; margin:10px 0 0;">Incubadora de Empresas</p>
            </div>
            <div style="padding: 34px 28px;">
                <p style="font-size: 16px; margin-top: 0;">Hola <strong>{nombre_lider}</strong>,</p>
                <p style="line-height: 1.6; font-size: 15px;">
                    Tu solicitud fue <strong>ACEPTADA</strong>. A continuacion te compartimos las credenciales de acceso del lider y del equipo.
                </p>
                <div style="background-color:#f1f5f9; border-radius: 12px; padding: 18px; border: 1px solid #e2e8f0; overflow:auto;">
                    <table style="width:100%; border-collapse:collapse; font-size:14px;">
                        <thead>
                            <tr>
                                <th align="left" style="padding:10px 12px; border-bottom:2px solid #cbd5e1; color:#1f3c88;">Nombre</th>
                                <th align="left" style="padding:10px 12px; border-bottom:2px solid #cbd5e1; color:#1f3c88;">Correo</th>
                                <th align="left" style="padding:10px 12px; border-bottom:2px solid #cbd5e1; color:#1f3c88;">Contraseña temporal</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows}
                        </tbody>
                    </table>
                </div>

                <p style="margin-top:18px; line-height:1.6; font-size: 14px; color:#475569;">
                    Recomendacion: una vez dentro, cambien su contraseña por seguridad.
                </p>

                <div style="text-align: center; margin-top: 26px;">
                    <a href="{portal_url}" style="display: inline-block; background-color: #1f3c88; color: #ffffff; padding: 12px 22px; border-radius: 10px; text-decoration: none; font-weight: 700; font-size: 15px; box-shadow: 0 4px 6px -1px rgba(31, 60, 136, 0.3);">Acceder al Portal</a>
                </div>

                <p style="margin-top: 26px; font-size: 12px; text-align: center; color: #94a3b8;">Este es un mensaje automatico, por favor no respondas a este correo.</p>
            </div>
        </div>
    </body>
    </html>
    """

    return send_email(
        subject=subject,
        text_body="Tu solicitud fue aceptada. Revisa las credenciales del equipo en este correo.",
        html_body=html,
        to=[destinatario_lider],
    )

def enviar_correo_reset(destinatario, token, request):
    """
    Correo para restablecer contraseña con enlace dinámico.
    """
    link = request.build_absolute_uri(f"/login/reset/{token}/")
    subject = "Recuperación de contraseña - Incubadora de Empresas"
    html = f"""
    <html>
    <body style="margin:0; font-family: 'Inter', 'Segoe UI', Arial, sans-serif; background-color: #f8fafc; color: #1e293b;">
        <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);">
            <div style="background: linear-gradient(135deg, #1e293b 0%, #334155 100%); padding: 40px 20px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 28px;">Restablecer Contraseña</h1>
            </div>
            <div style="padding: 40px 30px;">
                <p style="font-size: 18px; margin-top: 0;">Hola,</p>
                <p style="line-height: 1.6; font-size: 16px;">Hemos recibido una solicitud para restablecer la contraseña de tu cuenta en la <strong>Incubadora de Empresas</strong>.</p>
                <p style="line-height: 1.6; font-size: 16px;">Para continuar con el proceso, por favor haz clic en el siguiente botón:</p>
                <div style="text-align: center; margin: 35px 0;">
                    <a href="{link}" style="display: inline-block; background-color: #1f3c88; color: #ffffff; padding: 14px 28px; border-radius: 10px; text-decoration: none; font-weight: 700; font-size: 16px; box-shadow: 0 4px 6px -1px rgba(31, 60, 136, 0.3);">Restablecer mi contraseña</a>
                </div>
                <p style="line-height: 1.6; font-size: 16px; color: #64748b;">Si tú no solicitaste este cambio, puedes ignorar este correo de forma segura.</p>
                <p style="margin-top: 40px; font-size: 14px; text-align: center; color: #94a3b8; border-top: 1px solid #f1f5f9; padding-top: 20px;">Este enlace expirará pronto por motivos de seguridad.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return send_email(subject=subject, text_body="Solicitud de reset de contraseña.", html_body=html, to=[destinatario])

def enviar_confirmacion_password(destinatario, nombre, request):
    """
    Correo de confirmación de cambio exitoso de contraseña.
    """
    login_url = request.build_absolute_uri('/login/')
    subject = "Contraseña actualizada con éxito - Incubadora de Empresas"
    html = f"""
    <html>
    <body style="margin:0; font-family: 'Inter', 'Segoe UI', Arial, sans-serif; background-color: #f8fafc; color: #1e293b;">
        <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);">
            <div style="background: linear-gradient(135deg, #059669 0%, #10b981 100%); padding: 40px 20px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px;">¡Todo listo, {nombre}!</h1>
            </div>
            <div style="padding: 40px 30px;">
                <p style="font-size: 18px; margin-top: 0;">Tu contraseña ha sido actualizada.</p>
                <div style="text-align: center; margin: 35px 0;">
                    <a href="{login_url}" style="display: inline-block; background-color: #1f3c88; color: #ffffff; padding: 14px 28px; border-radius: 10px; text-decoration: none; font-weight: 700; font-size: 16px;">Ir al Login</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return send_email(subject=subject, text_body="Tu contraseña ha sido actualizada.", html_body=html, to=[destinatario])

def enviar_rechazo_solicitud(destinatario, nombre, motivo):
    """
    Correo informativo cuando se declina una solicitud.
    """
    subject = "Información sobre tu solicitud - Incubadora de Empresas"
    html = f"""
    <html>
    <body style="margin:0; font-family: 'Inter', 'Segoe UI', Arial, sans-serif; background-color: #f8fafc; color: #1e293b;">
        <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);">
            <div style="background: linear-gradient(135deg, #64748b 0%, #475569 100%); padding: 40px 20px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 28px;">Actualización de Solicitud</h1>
            </div>
            <div style="padding: 40px 30px;">
                <p style="font-size: 18px; margin-top: 0;">Hola <strong>{nombre}</strong>,</p>
                <p style="line-height: 1.6; font-size: 16px;">Lamentamos informarte que en esta ocasión tu solicitud ha sido <strong>declinada</strong>.</p>
                <div style="background-color: #fff1f2; border-left: 4px solid #f43f5e; padding: 20px; margin: 30px 0; border-radius: 4px;">
                    <p style="margin-top: 0; font-weight: 700; color: #be123c;">Motivo:</p>
                    <p style="margin-bottom: 0; color: #9f1239; font-style: italic;">"{motivo or 'No se proporcionó un motivo específico.'}"</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return send_email(subject=subject, text_body="Actualización de tu solicitud.", html_body=html, to=[destinatario])
