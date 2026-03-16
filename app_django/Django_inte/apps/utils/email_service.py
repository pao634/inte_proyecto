import os
from io import BytesIO
from datetime import datetime
import threading
import gridfs

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from config.database.mongo import db

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# ==========================================================
#  Utilidades de Email
# ==========================================================


# ==========================================================
#  Enviar correo con PDF institucional
# ==========================================================

def enviar_correo(destinatario, datos):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = os.getenv("EMAIL_HOST_USER")
    sender_password = os.getenv("EMAIL_HOST_PASSWORD")

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

    # Paleta
    primary = colors.HexColor("#1f3c88")
    accent = colors.HexColor("#f97316")
    soft_bg = colors.HexColor("#f5f7fb")
    border = colors.HexColor("#e5e7eb")

    # Tipografias
    title_style = ParagraphStyle(
        name="Title",
        parent=styles["Title"],
        fontSize=20,
        textColor=colors.white,
        alignment=0,
        spaceAfter=4,
        leading=22,
    )

    subtitle_style = ParagraphStyle(
        name="Subtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.white,
        alignment=0,
    )

    section_style = ParagraphStyle(
        name="Section",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=primary,
        spaceBefore=14,
        spaceAfter=8,
    )

    label_style = ParagraphStyle(
        name="Label",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#6b7280"),
        leading=12,
    )

    value_style = ParagraphStyle(
        name="Value",
        parent=styles["Normal"],
        fontSize=11.5,
        textColor=colors.HexColor("#111827"),
        leading=14,
    )

    note_style = ParagraphStyle(
        name="Note",
        parent=styles["Normal"],
        fontSize=10.5,
        textColor=colors.HexColor("#374151"),
        leading=14,
    )

    # Encabezado
    header = Table(
        [
            [
                Paragraph("Cedula de inscripcion", title_style),
                Paragraph(
                    "Estado: Recibida",
                    ParagraphStyle(
                        name="Badge",
                        parent=styles["Normal"],
                        fontSize=10,
                        textColor=colors.white,
                        alignment=1,
                    ),
                ),
            ],
            [
                Paragraph(
                    "Solicitud de ingreso a la incubadora • Formato de evaluacion de emprendimientos",
                    subtitle_style,
                ),
                "",
            ],
        ],
        colWidths=[360, 120],
    )
    header.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), primary),
                ("SPAN", (0, 1), (1, 1)),
                ("ALIGN", (1, 0), (1, 0), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 18),
                ("RIGHTPADDING", (0, 0), (-1, -1), 18),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ]
        )
    )
    elements.append(header)
    elements.append(Spacer(1, 14))

    # Resumen
    resumen = Table(
        [
            [
                Paragraph("Nombre completo", label_style),
                Paragraph(datos.get("nombre_completo", ""), value_style),
                Paragraph("Correo", label_style),
                Paragraph(datos.get("correo", ""), value_style),
            ]
        ],
        colWidths=[90, 190, 70, 130],
    )
    resumen.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), soft_bg),
                ("BOX", (0, 0), (-1, -1), 0.6, border),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, border),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    elements.append(resumen)
    elements.append(Spacer(1, 18))

    # Informacion personal
    elements.append(Paragraph("Informacion personal", section_style))
    info_personal = Table(
        [
            [Paragraph("Carrera", label_style), Paragraph(datos.get("carrera", ""), value_style)],
            [Paragraph("Matricula", label_style), Paragraph(datos.get("matricula", ""), value_style)],
            [Paragraph("Telefono", label_style), Paragraph(datos.get("telefono", ""), value_style)],
        ],
        colWidths=[120, 320],
    )
    info_personal.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.6, border),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, border),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, soft_bg]),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(info_personal)
    elements.append(Spacer(1, 18))

    # Informacion del emprendimiento
    elements.append(Paragraph("Informacion del emprendimiento", section_style))
    info_empr = Table(
        [
            [Paragraph("Nombre del proyecto", label_style), Paragraph(datos.get("nombre_proyecto", ""), value_style)],
            [Paragraph("Descripcion", label_style), Paragraph(datos.get("descripcion_negocio", ""), value_style)],
        ],
        colWidths=[140, 300],
    )
    info_empr.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.6, border),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, border),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, soft_bg]),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(info_empr)
    elements.append(Spacer(1, 16))

    # Nota y fecha
    fecha_actual = datetime.now().strftime("%d/%m/%Y")
    nota = Table(
        [
            [
                Paragraph(
                    f"Fecha de solicitud: {fecha_actual}<br/>Revisaremos tu solicitud y te enviaremos los siguientes pasos.",
                    note_style,
                )
            ]
        ],
        colWidths=[440],
    )
    nota.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff7ed")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#fdba74")),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    elements.append(nota)
    elements.append(Spacer(1, 24))

    # Firmas
    firmas = Table(
        [
            ["_____________________________", "_____________________________"],
            ["Firma del Alumno", "Firma del Asesor Academico"],
        ],
        colWidths=[220, 220],
    )
    firmas.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTSIZE", (0, 0), (-1, -1), 11),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(firmas)

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()

    # ======================================================
    #  Mensaje HTML
    # ======================================================
    mensaje = MIMEMultipart("mixed")
    mensaje["From"] = sender_email
    mensaje["To"] = destinatario
    mensaje["Subject"] = "Confirmacion de solicitud a la incubadora"

    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
      <style>
        @keyframes sweep{{0%{{background-position:0% 50%;}}50%{{background-position:100% 50%;}}100%{{background-position:0% 50%;}}}}
        @keyframes floaty{{0%{{transform:translateY(0);}}50%{{transform:translateY(-6px);}}100%{{transform:translateY(0);}}}}
      </style>
    </head>
    <body style="margin:0; padding:0; font-family:'Poppins','Segoe UI',Arial,sans-serif; background:#0b1021;">
        <table align="center" width="680" cellpadding="0" cellspacing="0" role="presentation"
               style="background:linear-gradient(135deg,#0ea5e9,#6366f1,#22c55e);background-size:200% 200%; animation:sweep 10s ease infinite; border-radius:18px; overflow:hidden; box-shadow:0 14px 40px rgba(0,0,0,0.35); color:#ffffff;">
            <tr>
                <td style="padding:26px; text-align:center;">
                    <div style="font-size:26px; font-weight:800; letter-spacing:0.5px;">🚀 Incubadora de Proyectos</div>
                    <div style="font-size:14px; opacity:0.9;">Universidad Tecnológica de Acapulco</div>
                </td>
            </tr>
            <tr>
                <td style="padding:30px; background:rgba(255,255,255,0.08); backdrop-filter:blur(4px);">
                    <p style="margin:0 0 12px 0; font-size:20px; font-weight:800;">Hola {datos.get('nombre_completo', '')} ✨</p>
                    <p style="margin:0 0 12px 0; font-size:15px; line-height:1.6;">
                        Recibimos tu solicitud de ingreso a la incubadora. En las próximas 48 horas revisaremos tu información
                        y te contactaremos con los siguientes pasos.
                    </p>
                    <p style="margin:0 0 16px 0; font-size:15px; line-height:1.6;">
                        Adjuntamos tu cédula de inscripción en PDF para que la conserves y la compartas con tu equipo. 📄
                    </p>
                    <table cellpadding="0" cellspacing="0" role="presentation" style="margin:0 0 16px 0;">
                        <tr>
                            <td style="background:#fbbf24; color:#111827; padding:14px 18px; border-radius:12px; font-size:14px; font-weight:800; box-shadow:0 10px 24px rgba(251,191,36,.45); animation:floaty 5s ease-in-out infinite;">
                                📎 Cédula de inscripción (PDF adjunto)
                            </td>
                        </tr>
                    </table>
                    <p style="margin:0; font-size:13px; color:#e0f2fe;">
                        Si tienes dudas, responde a este correo y con gusto te ayudaremos. ¡Estamos listos para despegar contigo! 🧑‍🚀
                    </p>
                </td>
            </tr>
            <tr>
                <td style="background:rgba(0,0,0,0.25); padding:16px 24px; color:#e2e8f0; font-size:12px; text-align:center;">
                    Este mensaje se envió automáticamente. Por favor no compartas tus credenciales.
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    mensaje.attach(MIMEText(html, "html"))

    # ======================================================
    #  Enviar Correo usando Django Mail
    # ======================================================
    mensaje = EmailMultiAlternatives(
        subject="Confirmacion de solicitud a la incubadora",
        body="", # Texto plano vacío
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[destinatario]
    )
    mensaje.attach_alternative(html, "html")

    # Adjuntar PDF
    mensaje.attach("Solicitud_Incubadora.pdf", pdf, "application/pdf")

    try:
        mensaje.send(fail_silently=False)
        print(f"Correo enviado exitosamente a {destinatario}")
        return True
    except Exception as e:
        print(f"Error al enviar correo ({destinatario}): {e}")
        return False

def enviar_correo_async(destinatario, datos):
    """
    Inicia el envío de correo en un hilo separado para no bloquear el flujo principal.
    """
    thread = threading.Thread(target=enviar_correo, args=(destinatario, datos))
    thread.daemon = True
    thread.start()
    return True

def notificar_equipo_contrato(contrato_id, estado, motivo=None):
    """
    Busca a todos los integrantes de un proyecto y les notifica sobre el cambio de estado del contrato.
    """
    try:
        from bson.objectid import ObjectId
        contrato = db.contrato_proyecto.find_one({"_id": ObjectId(str(contrato_id))})
        if not contrato:
            return False

        usuario_id = contrato.get("usuario_id")
        if not usuario_id:
            return False

        # 1. Encontrar el proyecto
        usuario_obj = db.usuarios.find_one({"_id": ObjectId(str(usuario_id))})
        correo_lider = (usuario_obj.get("correo") or "").strip().lower() if usuario_obj else ""

        proyecto = db.proyectos.find_one({
            "$or": [
                {"usuario_id": str(usuario_id)},
                {"usuario_lider_id": str(usuario_id)},
                {"correo_usuario": correo_lider}
            ]
        })

        if not proyecto:
            # Si no hay proyecto, notificar solo al usuario que subió el contrato
            if usuario_obj:
                return _enviar_correo_individual_contrato(usuario_obj.get("correo"), usuario_obj.get("nombre"), estado, motivo)
            return False

        # 2. Recolectar todos los correos del equipo
        correos_equipo = []
        lider_email = (proyecto.get("correo_usuario") or "").strip().lower()
        if lider_email:
            correos_equipo.append(lider_email)

        for m in (proyecto.get("integrantes") or []):
            email = None
            if isinstance(m, dict) and m.get("correo"):
                email = m.get("correo").strip().lower()
            elif isinstance(m, str):
                email = m.strip().lower()
            
            if email and email not in correos_equipo:
                correos_equipo.append(email)

        # 3. Enviar correos
        exito_total = True
        nombre_proyecto = proyecto.get("nombre_proyecto") or "Tu Proyecto"
        
        for email in correos_equipo:
            user_target = db.usuarios.find_one({"correo": email})
            nombre_dest = user_target.get("nombre") if user_target else "Emprendedor"
            
            # Reutilizamos la lógica de diseño premium adaptándola
            res = _enviar_correo_individual_contrato(email, nombre_dest, estado, motivo, nombre_proyecto)
            if not res:
                exito_total = False
                
        return exito_total
    except Exception as e:
        print(f"Error en notificar_equipo_contrato: {e}")
        return False

def _enviar_correo_individual_contrato(destinatario, nombre, estado, motivo=None, proyecto_nombre="Tu Proyecto"):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = os.getenv("EMAIL_HOST_USER")
    sender_password = os.getenv("EMAIL_HOST_PASSWORD")
    portal_url = os.getenv("PORTAL_URL", "https://incubadora.local/login/")

    if not sender_email or not sender_password or not destinatario:
        return False

    mensaje = MIMEMultipart("alternative")
    mensaje["From"] = sender_email
    mensaje["To"] = destinatario
    
    if estado.lower() == "aceptado":
        mensaje["Subject"] = f"✅ Contrato Aceptado - {proyecto_nombre}"
        color_header = "#059669" # Verde
        status_text = "¡TU CONTRATO HA SIDO APROBADO!"
        body_text = f"Nos emociona informarte que el contrato para el proyecto <strong>{proyecto_nombre}</strong> ha sido aceptado oficialmente. Todo tu equipo ya tiene acceso completo a las herramientas del portal."
        icon = "✓"
    else:
        mensaje["Subject"] = f"⚠️ Ajustes Requeridos en Contrato - {proyecto_nombre}"
        color_header = "#e11d48" # Rojo/Rosa fuerte
        status_text = "SE REQUIEREN AJUSTES EN EL CONTRATO"
        body_text = f"Tras revisar el contrato enviado para el proyecto <strong>{proyecto_nombre}</strong>, hemos detectado algunos detalles que deben corregirse antes de poder proceder."
        icon = "!"

    motivo_html = ""
    if motivo:
        motivo_html = f"""
        <div style="background-color: #fef2f2; border-left: 4px solid #f43f5e; padding: 20px; margin: 30px 0; border-radius: 4px;">
            <p style="margin-top: 0; font-weight: 700; color: #9f1239;">Observaciones de administración:</p>
            <p style="margin-bottom: 0; color: #be123c; font-style: italic;">"{motivo}"</p>
        </div>
        """

    html = f"""
    <html>
    <body style="margin:0; font-family: 'Inter', 'Segoe UI', Arial, sans-serif; background-color: #f8fafc; color: #1e293b;">
        <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);">
            <div style="background: {color_header}; padding: 40px 20px; text-align: center;">
                <div style="background: white; width: 50px; height: 50px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 15px;">
                    <span style="color: {color_header}; font-size: 24px; font-weight: bold;">{icon}</span>
                </div>
                <h2 style="color: #ffffff; margin: 0; font-size: 20px; letter-spacing: 1px;">{status_text}</h2>
            </div>
            <div style="padding: 40px 30px;">
                <p style="font-size: 18px; margin-top: 0;">Hola <strong>{nombre}</strong>,</p>
                <p style="line-height: 1.6; font-size: 16px;">{body_text}</p>
                
                {motivo_html}

                <div style="text-align: center; margin: 35px 0;">
                    <a href="{portal_url}" style="display: inline-block; background-color: #1f3c88; color: #ffffff; padding: 14px 28px; border-radius: 10px; text-decoration: none; font-weight: 700; font-size: 16px; box-shadow: 0 4px 6px -1px rgba(31, 60, 136, 0.3);">Ir al Panel de Control</a>
                </div>
                
                <p style="margin-top: 40px; font-size: 14px; text-align: center; color: #64748b;">Este es un mensaje automático de la Incubadora de Empresas.</p>
            </div>
            <div style="background-color: #f8fafc; padding: 20px; text-align: center; border-top: 1px solid #e2e8f0;">
                <p style="margin: 0; font-size: 12px; color: #94a3b8;">&copy; 2026 Incubadora de Empresas. Todos los derechos reservados.</p>
            </div>
        </div>
    </body>
    </html>
    """
    mensaje = EmailMultiAlternatives(
        subject=subject_text,
        body="", 
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[destinatario]
    )
    mensaje.attach_alternative(html, "html")

    try:
        mensaje.send(fail_silently=False)
        return True
    except Exception:
        return False

def enviar_certificado_finalizacion(destinatario, nombre, proyecto_nombre, archivo_bin, nombre_archivo="Certificado.pdf"):
    """
    Envía un correo premium notificando la finalización del proyecto con el certificado adjunto.
    """
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = os.getenv("EMAIL_HOST_USER")
    sender_password = os.getenv("EMAIL_HOST_PASSWORD")

    if not sender_email or not sender_password or not destinatario:
        return False

    mensaje = MIMEMultipart("mixed")
    mensaje["From"] = sender_email
    mensaje["To"] = destinatario
    mensaje["Subject"] = f"🎓 ¡Felicidades! Proyecto Finalizado - {proyecto_nombre}"

    html = f"""
    <html>
    <body style="margin:0; font-family: 'Inter', 'Segoe UI', Arial, sans-serif; background-color: #f8fafc; color: #1e293b;">
        <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);">
            <div style="background: linear-gradient(135deg, #1e293b 0%, #334155 100%); padding: 50px 20px; text-align: center;">
                <div style="font-size: 50px; margin-bottom: 20px;">🎓</div>
                <h1 style="color: #ffffff; margin: 0; font-size: 28px; letter-spacing: 1px;">¡META ALCANZADA!</h1>
                <p style="color: #94a3b8; margin-top: 10px; font-size: 16px;">Has completado exitosamente tu proceso de incubación</p>
            </div>
            <div style="padding: 40px 30px;">
                <p style="font-size: 18px; margin-top: 0;">Hola <strong>{nombre}</strong>,</p>
                <p style="line-height: 1.6; font-size: 16px;">
                    Es un honor para nosotros informarte que el proyecto <strong>{proyecto_nombre}</strong> ha concluido formalmente su etapa en nuestra incubadora.
                </p>
                <p style="line-height: 1.6; font-size: 16px;">
                    Adjunto a este correo encontrarás tu <strong>Certificado/Cédula de Finalización</strong>, el cual acredita tu esfuerzo y dedicación durante este programa.
                </p>
                
                <div style="background-color: #f1f5f9; border-radius: 12px; padding: 25px; margin: 30px 0; text-align: center;">
                    <p style="margin: 0; font-weight: 700; color: #1e293b; font-size: 15px;">📄 Documento disponible:</p>
                    <p style="margin: 5px 0 0 0; color: #64748b; font-size: 14px;">{nombre_archivo}</p>
                </div>

                <p style="line-height: 1.6; font-size: 15px; color: #64748b;">
                    A partir de este momento, tu proyecto pasará a nuestro historial de casos de éxito. ¡Te deseamos lo mejor en esta nueva etapa de crecimiento independiente!
                </p>
                
                <p style="margin-top: 40px; font-size: 13px; text-align: center; color: #94a3b8; border-top: 1px solid #f1f5f9; padding-top: 20px;">
                    Este es un mensaje automático de la Incubadora de Empresas.
                </p>
            </div>
            <div style="background-color: #f8fafc; padding: 20px; text-align: center; border-top: 1px solid #e2e8f0;">
                <p style="margin: 0; font-size: 12px; color: #94a3b8;">&copy; 2026 Incubadora de Empresas. Todos los derechos reservados.</p>
            </div>
        </div>
    </body>
    </html>
    """
    mensaje.attach(MIMEText(html, "html"))

    mensaje = EmailMultiAlternatives(
        subject=f"🎓 ¡Felicidades! Proyecto Finalizado - {proyecto_nombre}",
        body="", 
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[destinatario]
    )
    mensaje.attach_alternative(html, "html")

    # Adjuntar Documento
    if archivo_bin:
        mensaje.attach(nombre_archivo, archivo_bin, "application/octet-stream")

    try:
        mensaje.send(fail_silently=False)
        return True
    except Exception as e:
        print(f"Error al enviar certificado: {e}")
        return False
