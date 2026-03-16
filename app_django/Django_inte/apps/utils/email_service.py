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
    #  Mensaje HTML
    # ======================================================
    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <body style="margin:0; padding:0; font-family:sans-serif; background:#0b1021;">
        <table align="center" width="600" cellpadding="0" cellspacing="0" style="background:#1e293b; border-radius:18px; overflow:hidden; color:#ffffff; margin-top:40px;">
            <tr><td style="padding:26px; text-align:center; background:#1f3c88;">Solicitud en Revision 🚀</td></tr>
            <tr>
                <td style="padding:30px;">
                    <p>Hola <strong>{datos.get('nombre_completo', '')}</strong>,</p>
                    <p>Recibimos tu solicitud y ya se encuentra <strong>en proceso de revision</strong>.</p>
                    <p>Adjuntamos tu cedula de inscripcion en PDF para tu registro.</p>
                    <p style="background:#fbbf24; color:#111827; padding:10px; border-radius:8px; text-align:center; font-weight:bold;">
                        Documento adjunto disponible
                    </p>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    mensaje = EmailMultiAlternatives(
        subject="Confirmacion de solicitud - Incubadora de Empresas",
        body="Recibimos tu solicitud. Revisa el documento adjunto.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[destinatario]
    )
    mensaje.attach_alternative(html, "text/html")
    mensaje.attach("Cedula_Inscripcion.pdf", pdf_content, "application/pdf")

    try:
        mensaje.send()
        print(f"Correo enviado a {destinatario}")
        return True
    except Exception as e:
        print(f"Error enviando correo: {e}")
        return False

def enviar_correo_async(destinatario, datos):
    thread = threading.Thread(target=enviar_correo, args=(destinatario, datos))
    thread.daemon = True
    thread.start()
    return True

def notificar_equipo_contrato(contrato_id, estado, motivo=None):
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
    
    mensaje = EmailMultiAlternatives(subject=sub, body=msg, from_email=settings.DEFAULT_FROM_EMAIL, to=[destinatario])
    mensaje.attach_alternative(html, "text/html")
    try:
        mensaje.send()
        return True
    except:
        return False

def enviar_certificado_finalizacion(destinatario, nombre, proyecto_nombre, archivo_bin, nombre_archivo="Certificado.pdf"):
    sub = f"🎓 ¡Felicidades! Proyecto Finalizado - {proyecto_nombre}"
    html = f"""
    <div style="font-family:sans-serif; text-align:center; padding:40px;">
        <h1>¡Felicidades {nombre}!</h1>
        <p>Has concluido exitosamente el proyecto <strong>{proyecto_nombre}</strong>.</p>
        <p>Adjuntamos tu certificado oficial.</p>
    </div>
    """
    mensaje = EmailMultiAlternatives(subject=sub, body=sub, from_email=settings.DEFAULT_FROM_EMAIL, to=[destinatario])
    mensaje.attach_alternative(html, "text/html")
    if archivo_bin:
        mensaje.attach(nombre_archivo, archivo_bin, "application/pdf")
    try:
        mensaje.send()
        return True
    except:
        return False
