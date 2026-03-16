import os
import re
import json
import mimetypes
import base64
import smtplib
import tempfile
import shutil
import subprocess
import threading
import logging
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404
from datetime import datetime
from django.contrib import messages
from config.database.mongo import db  
from django.views.decorators.http import require_POST
from config.database.mongo import mongo_instance, db
from django.utils import timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings
from bson import ObjectId
from docx2pdf import convert
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.core.mail import EmailMultiAlternatives

ADMIN_ROLE_ID = "699eb18f8a2f8c9f2f85cc98"
try:
    ADMIN_ROLE_OBJ = ObjectId(ADMIN_ROLE_ID)
except Exception:
    ADMIN_ROLE_OBJ = None
ADMIN_ROLE_IDS = [ADMIN_ROLE_ID] + ([ADMIN_ROLE_OBJ] if ADMIN_ROLE_OBJ else [])


def _es_admin(request):
    return request.session.get("rol") == "Administrador" and request.session.get("usuario_id")


def _require_admin(request):
    if not _es_admin(request):
        return redirect("login")
    return None


def _formatear_fecha_corta(dt):
    if not isinstance(dt, datetime):
        return ""
    try:
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return ""


def _asegurar_proyecto_activo(solicitud, usuario_id):
    """
    Crea o actualiza el registro de proyecto para un emprendedor aceptado.
    Guarda un resumen mínimo para vistas de admin y perfil.
    """
    if not solicitud or not usuario_id:
        return

    now = datetime.utcnow()
    nombre_proyecto = (solicitud.get("nombre_proyecto") or "Proyecto sin nombre").strip()
    estado_solicitud = (solicitud.get("estado") or "").upper()
    estado_proyecto = "Activo" if estado_solicitud == "ACEPTADO" else "En proceso"

    correo_sol = (solicitud.get("correo") or "").strip()

    resumen = {
        "descripcion": (solicitud.get("descripcion_negocio") or "").strip(),
        "lider": (solicitud.get("nombre_completo") or "").strip(),
        "correo": correo_sol,
        "telefono": (solicitud.get("telefono") or "").strip(),
        "carrera": (solicitud.get("carrera") or "").strip(),
        "equipo": solicitud.get("integrantes_equipo"),
        "integrantes": solicitud.get("integrantes") or [] # Guardamos la lista detallada
    }

    db.proyectos.update_one(
        {"usuario_id": str(usuario_id)},
        {
            "$set": {
                "usuario_id": str(usuario_id),
                "nombre_proyecto": nombre_proyecto,
                "estado": estado_proyecto,
                "correo_usuario": correo_sol,
                "resumen": resumen,
                "integrantes": solicitud.get("integrantes") or [],
                "ultima_actualizacion": now,
                "motivo_baja": None,
                "fecha_baja": None,
            },
            "$setOnInsert": {"creado_en": now},
        },
        upsert=True,
    )

def perfil_admin(request):
    return render(request, "perfil_admin.html")

def panel_admin(request):
    guard = _require_admin(request)
    if guard:
        return guard
    return render(request, "panel_admin.html")

def lista_anuncios(request):
    guard = _require_admin(request)
    if guard:
        return guard
    anuncios_cursor = db.anuncios.find().sort('_id', -1)
    anuncios = list(anuncios_cursor)
    return render(request, 'ver_anuncios.html', {
            'anuncios': anuncios
        })

def panel_publicaciones_admin(request):
    """
    Vista unificada para manejar Anuncios y Convocatorias desde el panel admin.
    """
    guard = _require_admin(request)
    if guard: return guard
    
    # Obtenemos TODO el muro sin restricciones para el admin
    from apps.public.views import _obtener_muro_unificado_public
    muro = _obtener_muro_unificado_public(request=request, es_visitante=False)
    
    return render(request, "crear_publicacion.html", {"muro": muro})


def crear_anuncio(request):
    guard = _require_admin(request)
    if guard:
        return guard
    if request.method == 'POST':
        solo_emprendedores = request.POST.get('solo_emprendedores') == 'on'
        titulo = request.POST.get('titulo')
        contenido = request.POST.get('contenido')
        
        nuevo_aviso = {
            "titulo": titulo,
            "contenido": contenido,
            "solo_emprendedores": solo_emprendedores,
            "tipo": "anuncio", # Converted from noticia to match public wall logic
            "fecha": timezone.now().strftime("%d/%m/%Y %H:%M"),
            "fecha_sort": timezone.now()
        }
        result = db.anuncios.insert_one(nuevo_aviso)
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax'):
            return JsonResponse({
                "success": True, 
                "id": str(result.inserted_id),
                "item": {
                    "titulo": titulo,
                    "contenido": contenido,
                    "solo_emprendedores": solo_emprendedores,
                    "fecha": nuevo_aviso["fecha"],
                    "tipo": "anuncio"
                }
            })
        return redirect('panel_publicaciones_admin')

    # Jalamos los anuncios para el panel del Admin
    anuncios_cursor = db.anuncios.find().sort('_id', -1)
    lista_final = []
    
    for a in anuncios_cursor:
        
        a['id'] = str(a['_id']) 
        lista_final.append(a)

    return render(request, 'crear_anuncio.html', {
        'todos_los_anuncios': lista_final  
    })

def eliminar_anuncio(request, id):
    guard = _require_admin(request)
    if guard:
        return guard
    db.anuncios.delete_one({'_id': ObjectId(id)})
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax'):
        return JsonResponse({"success": True})
    return redirect('panel_publicaciones_admin')

def editar_anuncio(request, id):
    guard = _require_admin(request)
    if guard:
        return guard
    anuncio_id = ObjectId(id)
    if request.method == 'POST':
        solo_emprendedores = request.POST.get('solo_emprendedores') == 'on'
        db.anuncios.update_one(
            {'_id': anuncio_id},
            {'$set': {
                'titulo': request.POST.get('titulo'),
                'contenido': request.POST.get('contenido'),
                'solo_emprendedores': solo_emprendedores
            }}
        )
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax'):
            return JsonResponse({"success": True})
        return redirect('panel_publicaciones_admin')
        return redirect('panel_publicaciones_admin')
    
    anuncio = db.anuncios.find_one({'_id': anuncio_id})

    if anuncio:
        anuncio['id'] = str(anuncio['_id'])
    
    
    anuncios_cursor = db.anuncios.find().sort('_id', -1)
    lista_final = []
    for a in anuncios_cursor:
        a['id'] = str(a['_id'])
        lista_final.append(a)

    return render(request, 'crear_anuncio.html', {
        'anuncio_edit': anuncio, 
        'todos_los_anuncios': lista_final 
    })

def crear_convocatoria_admin(request):
    guard = _require_admin(request)
    if guard:
        return guard
    if request.method == "POST":
        titulo = request.POST.get("titulo")
        fecha_fin_str = request.POST.get("fecha_fin")
        banner = request.FILES.get("banner")

        # Convertimos string HTML datetime-local a datetime real
        fecha_fin = None
        if fecha_fin_str:
            try:
                fecha_fin = datetime.fromisoformat(fecha_fin_str)
            except Exception as e:
                return JsonResponse({"error": "Formato de fecha invalido"}, status=400)

        file_id_banner = None
        if banner:
            file_id_banner = mongo_instance.subir_imagen_file(banner)

        db.convocatorias.insert_one({
            "titulo": titulo,
            "fecha_fin": fecha_fin,
            "banner_file_id": file_id_banner
        })

        return JsonResponse({"success": True})

    # =============================
    # GET: mostrar convocatorias
    # =============================
    convocatorias = []
    datos_bd = list(db.convocatorias.find())

    for c in datos_bd:
        banner_base64 = None

        if c.get("banner_file_id"):
            banner_base64 = mongo_instance.obtener_imagen_base64(
                c["banner_file_id"]
            )

        fecha_formateada = None
        if isinstance(c.get("fecha_fin"), datetime):
            fecha_formateada = c["fecha_fin"].strftime("%Y-%m-%dT%H:%M")
        else:
            fecha_formateada = c.get("fecha_fin")

        convocatorias.append({
            "id": str(c["_id"]),
            "titulo": c.get("titulo"),
            "fecha_fin": fecha_formateada,
            "banner": banner_base64
        })

    return render(request, "crear_convocatoria.html", {
        "convocatorias": convocatorias
    })

@require_POST
def editar_convocatoria(request):
    guard = _require_admin(request)
    if guard:
        return guard
    id_conv = request.POST.get("id")
    titulo = request.POST.get("titulo")
    fecha_fin_str = request.POST.get("fecha_fin")
    banner = request.FILES.get("banner")

    if not id_conv:
        return JsonResponse({"error": "ID no recibido"}, status=400)

    # Convertimos fecha correctamente
    fecha_fin = None
    if fecha_fin_str:
        try:
            fecha_fin = datetime.fromisoformat(fecha_fin_str)
        except Exception:
            return JsonResponse({"error": "Formato de fecha invalido"}, status=400)

    update_data = {
        "titulo": titulo,
        "fecha_fin": fecha_fin
    }

    if banner:
        file_id_banner = mongo_instance.subir_imagen_file(banner)
        update_data["banner_file_id"] = file_id_banner

    db.convocatorias.update_one(
        {"_id": ObjectId(id_conv)},
        {"$set": update_data}
    )

    return JsonResponse({"success": True})

def eliminar_convocatoria(request):
    guard = _require_admin(request)
    if guard:
        return guard
    if request.method == "POST":

        id_conv = request.POST.get("id")

        if not id_conv:
            return JsonResponse({"error": "ID no recibido"}, status=400)

        db.convocatorias.delete_one({"_id": ObjectId(id_conv)})

        return JsonResponse({"success": True})

    return JsonResponse({"error": "Metodo no permitido"}, status=405)

def obtener_solicitudes(request):
    guard = _require_admin(request)
    if guard:
        return guard

    filtro_pendientes = {
        "$or": [
            {"estado": {"$regex": "^EN PROCESO$", "$options": "i"}},
            {"estado": {"$exists": False}}
        ]
    }

    solicitudes = list(db.solicitudes.find(filtro_pendientes))

    for s in solicitudes:
        s["_id"] = str(s["_id"])

        # Formatear fecha
        if "fecha_creacion" in s and isinstance(s["fecha_creacion"], datetime):
            s["fecha_creacion"] = s["fecha_creacion"].strftime("%d/%m/%Y %H:%M")

    return JsonResponse(solicitudes, safe=False)
def solicitudes_panel(request):
    guard = _require_admin(request)
    if guard:
        return guard
    return render(request, "solicitudes.html")


logger = logging.getLogger(__name__)

def enviar_correo_estado_solicitud(destinatario, nombre, estado, password=None, motivo=None, smtp_server_conn=None):
    smtp_host = "smtp.gmail.com"
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
        mensaje["Subject"] = "🚀 ¡Felicidades! Tu proyecto ha sido aceptado"
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
    else:
        mensaje["Subject"] = "Información sobre tu solicitud - Incubadora de Empresas"
        html = f"""
        <html>
        <body style="margin:0; font-family: 'Inter', 'Segoe UI', Arial, sans-serif; background-color: #f8fafc; color: #1e293b;">
            <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);">
                <div style="background: linear-gradient(135deg, #64748b 0%, #475569 100%); padding: 40px 20px; text-align: center;">
                    <h1 style="color: #ffffff; margin: 0; font-size: 28px;">Actualización de Solicitud</h1>
                </div>
                <div style="padding: 40px 30px;">
                    <p style="font-size: 18px; margin-top: 0;">Hola <strong>{nombre}</strong>,</p>
                    <p style="line-height: 1.6; font-size: 16px;">Agradecemos sinceramente tu interés en la <strong>Incubadora de Empresas</strong> y el tiempo dedicado a tu solicitud.</p>
                    <p style="line-height: 1.6; font-size: 16px;">Tras una revisión detallada de tu propuesta, lamentamos informarte que en esta ocasión tu solicitud ha sido <strong>declinada</strong>.</p>
                    
                    <div style="background-color: #fff1f2; border-left: 4px solid #f43f5e; padding: 20px; margin: 30px 0; border-radius: 4px;">
                        <p style="margin-top: 0; font-weight: 700; color: #be123c;">Motivo de la decisión:</p>
                        <p style="margin-bottom: 0; color: #9f1239; font-style: italic;">"{motivo or 'No se proporcionó un motivo específico.'}"</p>
                    </div>

                    <p style="line-height: 1.6; font-size: 16px;">Valoramos mucho tu espíritu emprendedor y te animamos a seguir trabajando en tu proyecto. Te invitamos a participar en futuras convocatorias una vez que hayas realizado los ajustes necesarios.</p>
                    
                    <p style="margin-top: 40px; font-size: 14px; text-align: center; color: #64748b;">Si deseas recibir más orientación, puedes contactarnos directamente.</p>
                </div>
                <div style="background-color: #f8fafc; padding: 20px; text-align: center; border-top: 1px solid #e2e8f0;">
                    <p style="margin: 0; font-size: 12px; color: #94a3b8;">&copy; 2026 Incubadora de Empresas. Todos los derechos reservados.</p>
                </div>
            </div>
        </body>
        </html>
        """

    mensaje = EmailMultiAlternatives(
        subject=mensaje_subject,
        body="", # Texto plano vacío, usamos HTML
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[destinatario]
    )
    mensaje.attach_alternative(html, "html")

    try:
        mensaje.send(fail_silently=False)
        return True
    except Exception as e:
        logger.error(f"Error enviando correo a {destinatario}: {str(e)}")
        return False

def _background_enviar_correos_bulk(destinatarios_list, estado, password=None, motivo=None):
    """ Envia correos a múltiples destinatarios usando una sola conexión SMTP. """
    smtp_host = "smtp.gmail.com"
    smtp_port = 587
    sender_email = os.getenv("EMAIL_HOST_USER")
    sender_password = os.getenv("EMAIL_HOST_PASSWORD")

    if not sender_email or not sender_password or not destinatarios_list:
        return

    try:
        for dest in destinatarios_list:
            enviar_correo_estado_solicitud(
                destinatario=dest.get("correo"),
                nombre=dest.get("nombre"),
                estado=estado,
                password=password,
                motivo=motivo
            )
    except Exception as e:
        logger.error(f"Error en bulk email background: {str(e)}")


def enviar_correo_rechazo_contrato(destinatario, nombre, motivo):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = os.getenv("EMAIL_HOST_USER")
    sender_password = os.getenv("EMAIL_HOST_PASSWORD")

    if not sender_email or not sender_password or not destinatario:
        return False

    mensaje = MIMEMultipart("alternative")
    mensaje["From"] = sender_email
    mensaje["To"] = destinatario
    mensaje["Subject"] = "⚠️ Revisa tu contrato y vuelve a enviarlo"

    motivo_txt = motivo or "Tu contrato requiere ajustes. Sube nuevamente el archivo corregido."
    html = f"""
    <html>
    <body style="margin:0; font-family: 'Inter', 'Segoe UI', Arial, sans-serif; background-color: #fef2f2; color: #1e293b;">
        <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);">
            <div style="background: linear-gradient(135deg, #f43f5e 0%, #e11d48 100%); padding: 40px 20px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 28px;">Ajustes en tu Contrato</h1>
            </div>
            <div style="padding: 40px 30px;">
                <p style="font-size: 18px; margin-top: 0;">Hola <strong>{nombre}</strong>,</p>
                <p style="line-height: 1.6; font-size: 16px;">Hemos revisado el contrato que subiste y hemos encontrado algunos detalles que requieren tu atención antes de poder aprobarlo.</p>
                
                <div style="background-color: #fff7ed; border-left: 4px solid #f97316; padding: 20px; margin: 30px 0; border-radius: 4px;">
                    <p style="margin-top: 0; font-weight: 700; color: #c2410c;">Observaciones:</p>
                    <p style="margin-bottom: 0; color: #9a3412;">{motivo_txt}</p>
                </div>

                <p style="line-height: 1.6; font-size: 16px;">Por favor, realiza los ajustes necesarios y vuelve a subir el archivo corregido a través del portal para que podamos continuar con tu proceso.</p>
                
                <p style="margin-top: 40px; font-size: 14px; text-align: center; color: #64748b;">Asegúrate de que la información coincida exactamente con los datos de tu proyecto.</p>
            </div>
            <div style="background-color: #f8fafc; padding: 20px; text-align: center; border-top: 1px solid #e2e8f0;">
                <p style="margin: 0; font-size: 12px; color: #94a3b8;">&copy; 2026 Incubadora de Empresas. Todos los derechos reservados.</p>
            </div>
        </div>
    </body>
    </html>
    """
    mensaje.attach(MIMEText(html, "html"))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(mensaje)
        server.quit()
        return True
    except Exception:
        return False

@csrf_exempt
def actualizar_estado(request, id):
    guard = _require_admin(request)
    if guard:
        return guard
    if request.method != "POST":
        return JsonResponse({"error": "Metodo no permitido"}, status=405)

    # Intentar extraer datos del body (JSON) o del POST (Form) de manera segura
    try:
        if request.content_type == 'application/json':
            body_unicode = request.body.decode('utf-8')
            data = json.loads(body_unicode) if body_unicode else {}
        else:
            data = request.POST.dict()
    except Exception:
        return JsonResponse({"error": "Error al procesar los datos enviados"}, status=400)

    nuevo_estado = (data.get("estado") or "").strip()
    password = (data.get("password") or "").strip()
    motivo = (data.get("motivo") or "").strip()

    if nuevo_estado not in ["Aceptado", "Rechazado"]:
        return JsonResponse({"error": "Estado invalido"}, status=400)

    # Búsqueda robusta por ID: intentamos como ObjectId y luego como string si falla
    query = None
    try:
        # Intentamos convertir a ObjectId si es un hex válido de 24 caracteres
        query = {"_id": ObjectId(id)}
    except Exception:
        # Si falla (ej. hash de 40 caracteres), buscamos por string directamente
        query = {"_id": id}

    solicitud = db.solicitudes.find_one(query)
    
    # Fallback adicional: si buscamos por ObjectId y no existe, probamos como string exacto
    if not solicitud and isinstance(query.get("_id"), ObjectId):
        solicitud = db.solicitudes.find_one({"_id": id})

    if not solicitud:
        return JsonResponse({"error": "Solicitud no encontrada"}, status=404)

    correo = (solicitud.get("correo") or "").strip()
    nombre = (solicitud.get("nombre_completo") or "Emprendedor").strip()

    if nuevo_estado == "Aceptado":
        if len(password) < 8:
            return JsonResponse(
                {"error": "La contraseña debe tener al menos 8 caracteres"},
                status=400
            )

        rol_emprendedor = db.roles.find_one({
            "nombre": {"$regex": "^Emprendedor$", "$options": "i"}
        })

        if not rol_emprendedor:
            return JsonResponse(
                {"error": "No existe el rol 'Emprendedor' en la base de datos"},
                status=500
            )

        # 1. Procesar Líder
        datos_lider = {
            "nombre": nombre,
            "correo": correo,
            "contrasena": password,
            "rol_id": str(rol_emprendedor["_id"]),
            "activo": True
        }
        
        usuario_lider_id = None
        user_lider_existente = db.usuarios.find_one({"correo": correo})
        if user_lider_existente:
            db.usuarios.update_one(
                {"_id": user_lider_existente["_id"]},
                {"$set": {**datos_lider, "fecha_actualizacion": datetime.utcnow()}}
            )
            usuario_lider_id = user_lider_existente["_id"]
        else:
            res_lider = db.usuarios.insert_one({**datos_lider, "fecha_creacion": datetime.utcnow()})
            usuario_lider_id = res_lider.inserted_id

        # 2. Procesar Integrantes adicionales
        integrantes = solicitud.get("integrantes") or []
        
        # Robustez: si integrantes es un string (JSON), lo parseamos
        if isinstance(integrantes, str):
            try:
                integrantes = json.loads(integrantes)
            except Exception:
                integrantes = []

        # Lista para envío masivo en segundo plano
        destinatarios_bulk = [{"correo": correo, "nombre": nombre}]

        for integrante in integrantes:
            i_correo = (integrante.get("correo") or "").strip().lower()
            i_nombre = (integrante.get("nombre") or "Integrante").strip()
            
            if not i_correo or i_correo == correo: # Evitar duplicar líder
                continue
                
            datos_integra = {
                "nombre": i_nombre,
                "correo": i_correo,
                "contrasena": password, # Misma password temporal para todos por simplicidad
                "rol_id": str(rol_emprendedor["_id"]),
                "activo": True
            }
            
            user_existente = db.usuarios.find_one({"correo": i_correo})
            if user_existente:
                db.usuarios.update_one(
                    {"_id": user_existente["_id"]},
                    {"$set": {**datos_integra, "fecha_actualizacion": datetime.utcnow()}}
                )
            else:
                db.usuarios.insert_one({**datos_integra, "fecha_creacion": datetime.utcnow()})
            
            # Agregamos a la lista de envíos background
            destinatarios_bulk.append({"correo": i_correo, "nombre": i_nombre})

        _asegurar_proyecto_activo(solicitud, usuario_lider_id)

        # Enviar correos de aceptación en segundo plano (Bulk)
        threading.Thread(
            target=_background_enviar_correos_bulk,
            args=(destinatarios_bulk, nuevo_estado, password, None)
        ).start()

    else:
        # Caso Rechazado: Enviar correo informativo en segundo plano
        threading.Thread(
            target=enviar_correo_estado_solicitud,
            args=(correo, nombre, nuevo_estado, None, motivo)
        ).start()

    # Elimina la solicitud del tablero (aceptada pasa a usuarios, rechazada se descarta).
    db.solicitudes.delete_one({"_id": solicitud["_id"]})

    return JsonResponse({"success": True, "mail_enviado": True})

from django.shortcuts import render

def solicitudes_panel(request):
    guard = _require_admin(request)
    if guard:
        return guard
    return render(request, "solicitudes.html")

def detalle_solicitud(request):
    guard = _require_admin(request)
    if guard:
        return guard
    return render(request, "detalle_solicitud.html")


def obtener_solicitudes(request):
    guard = _require_admin(request)
    if guard:
        return guard

    filtro_pendientes = {
        "$or": [
            {"estado": {"$regex": "^EN PROCESO$", "$options": "i"}},
            {"estado": {"$exists": False}}
        ]
    }

    solicitudes = list(db.solicitudes.find(filtro_pendientes))

    for s in solicitudes:
        s["_id"] = str(s["_id"])

        if "fecha_creacion" in s and isinstance(s["fecha_creacion"], datetime):
            s["fecha_creacion"] = s["fecha_creacion"].strftime("%d/%m/%Y %H:%M")

        s.pop("csrfmiddlewaretoken", None)

    return JsonResponse(solicitudes, safe=False)

# =========================
# UTILIDAD: CONVERTIR DOCX A PDF
# =========================
def obtener_pdf(contrato):
    ruta_docx = contrato.get("ruta")
    ruta_pdf = contrato.get("ruta_pdf")

    if ruta_pdf and os.path.exists(ruta_pdf):
        return ruta_pdf

    if ruta_docx and ruta_docx.lower().endswith(".docx"):
        ruta_pdf = ruta_docx.replace(".docx", ".pdf")

        if not os.path.exists(ruta_pdf):
            convert(ruta_docx, ruta_pdf)

        # Guardar ruta PDF en Mongo
        db.contrato_proyecto.update_one(
            {"_id": contrato["_id"]},
            {"$set": {"ruta_pdf": ruta_pdf}}
        )

        return ruta_pdf

    return None


# =========================
# CONTRATO VIGENTE (ADMIN)
# =========================
def _obtener_contrato_vigente():
    return db.contrato_vigente.find_one(sort=[("fecha_actualizacion", -1), ("_id", -1)])


def _convertir_office_bytes_a_pdf_bytes(office_bytes, extension):
    temp_dir = tempfile.mkdtemp(prefix="contrato_vigente_")
    ruta_docx = os.path.join(temp_dir, f"contrato{extension}")
    ruta_pdf = os.path.join(temp_dir, "contrato.pdf")
    try:
        with open(ruta_docx, "wb") as f:
            f.write(office_bytes)

        # Intento 1: Microsoft Word COM (Windows)
        try:
            import pythoncom
            import win32com.client

            pythoncom.CoInitialize()
            word = None
            try:
                word = win32com.client.DispatchEx("Word.Application")
                word.Visible = False
                doc = word.Documents.Open(ruta_docx, ReadOnly=1)
                doc.SaveAs(ruta_pdf, FileFormat=17)  # 17 = PDF
                doc.Close(False)
            finally:
                if word:
                    word.Quit()
                pythoncom.CoUninitialize()
        except Exception:
            pass

        if os.path.exists(ruta_pdf):
            with open(ruta_pdf, "rb") as f:
                return f.read()

        # Intento 2: docx2pdf
        try:
            convert(ruta_docx, ruta_pdf)
        except Exception:
            pass

        if os.path.exists(ruta_pdf):
            with open(ruta_pdf, "rb") as f:
                return f.read()

        # Intento 3: LibreOffice (si existe en PATH)
        try:
            subprocess.run(
                ["soffice", "--headless", "--convert-to", "pdf", "--outdir", temp_dir, ruta_docx],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

        if os.path.exists(ruta_pdf):
            with open(ruta_pdf, "rb") as f:
                return f.read()

        raise RuntimeError("No se pudo convertir el contrato a PDF.")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _asegurar_contrato_vigente_pdf(contrato):
    if not contrato:
        return None

    tipo = (contrato.get("tipo_archivo") or "").lower()
    nombre = (contrato.get("nombre_archivo") or "").lower()
    es_pdf = tipo == "application/pdf" or nombre.endswith(".pdf")
    if es_pdf:
        return contrato

    extension = (contrato.get("extension") or "").lower()
    es_office = extension in [".doc", ".docx"] or nombre.endswith(".docx") or nombre.endswith(".doc") or "word" in tipo
    if not es_office:
        return contrato

    try:
        ext = ".docx" if nombre.endswith(".docx") or extension == ".docx" else ".doc"
        pdf_bytes = _convertir_office_bytes_a_pdf_bytes(contrato.get("archivo") or b"", ext)
        nuevo_nombre = f"{os.path.splitext(contrato.get('nombre_archivo') or 'contrato')[0]}.pdf"
        db.contrato_vigente.update_one(
            {"_id": contrato["_id"]},
            {"$set": {
                "archivo": pdf_bytes,
                "tipo_archivo": "application/pdf",
                "nombre_archivo": nuevo_nombre,
                "extension": ".pdf",
            }}
        )
        contrato["archivo"] = pdf_bytes
        contrato["tipo_archivo"] = "application/pdf"
        contrato["nombre_archivo"] = nuevo_nombre
        contrato["extension"] = ".pdf"
    except Exception:
        return contrato

    return contrato


def contrato_vigente_admin(request):
    guard = _require_admin(request)
    if guard:
        return guard
    if request.method == "POST":
        accion = (request.POST.get("accion") or "").strip().lower()

        if accion == "eliminar":
            db.contrato_vigente.delete_many({})
            messages.success(request, "Contrato vigente eliminado.")
            return redirect("contrato_vigente_admin")

        archivo = request.FILES.get("contrato_vigente")
        if not archivo:
            messages.error(request, "Selecciona un archivo .pdf, .docx o .doc.")
            return redirect("contrato_vigente_admin")

        nombre = (archivo.name or "contrato_vigente").strip()
        extension = os.path.splitext(nombre)[1].lower()
        if extension not in [".pdf", ".docx", ".doc"]:
            messages.error(request, "Formato no permitido. Solo PDF, DOCX o DOC.")
            return redirect("contrato_vigente_admin")

        archivo_bytes = archivo.read()
        tipo = getattr(archivo, "content_type", "application/octet-stream")
        nombre_guardado = nombre
        extension_guardada = extension

        db.contrato_vigente.delete_many({})
        db.contrato_vigente.insert_one({
            "nombre_archivo": nombre_guardado,
            "tipo_archivo": tipo,
            "archivo": archivo_bytes,
            "extension": extension_guardada,
            "fecha_actualizacion": datetime.now(),
            "actualizado_por": request.session.get("usuario_id")
        })
        messages.success(request, "Contrato vigente actualizado correctamente.")
        return redirect("contrato_vigente_admin")

    contrato = _obtener_contrato_vigente()
    return render(request, "contrato_vigente.html", {
        "contrato_vigente": contrato
    })


def ver_contrato_vigente_admin(request):
    guard = _require_admin(request)
    if guard:
        return guard
    contrato = _obtener_contrato_vigente()
    if not contrato or not contrato.get("archivo"):
        raise Http404("No hay contrato vigente configurado.")

    tipo = contrato.get("tipo_archivo") or "application/pdf"
    response = HttpResponse(contrato.get("archivo"), content_type=tipo)
    response["Content-Disposition"] = "inline"
    return response


# =========================
# LISTAR CONTRATOS
# =========================
def ver_contratos(request):
    guard = _require_admin(request)
    if guard:
        return guard
    contratos_raw = list(db.contrato_proyecto.find().sort("_id", -1))

    # Solo mostrar contratos de emprendedores vigentes (oculta admins u orígenes huérfanos).
    rol_emprendedor = db.roles.find_one({"nombre": {"$regex": "^Emprendedor$", "$options": "i"}})
    rol_empr_ids = []
    if rol_emprendedor:
        rol_empr_ids.extend([str(rol_emprendedor.get("_id")), rol_emprendedor.get("_id")])
    rol_excluir = set(ADMIN_ROLE_IDS)

    contratos = []

    for c in contratos_raw:
        c["id"] = str(c["_id"])
        c["nombre_contrato"] = c.get("nombre_archivo") or c.get("nombre") or "Sin nombre"
        c["estado"] = (c.get("estado") or "enviado").lower()
        firmas_participantes = c.get("firmas_participantes") or []
        c["firmas_total"] = len(firmas_participantes)
        c["firmado"] = bool(c.get("firma_contrato")) or c["firmas_total"] > 0
        c["usuario_nombre"] = (
            c.get("usuario_nombre")
            or c.get("nombre_usuario")
            or c.get("nombre_emprendedor")
            or "Usuario desconocido"
        )
        c["usuario_correo"] = (
            c.get("usuario_correo")
            or c.get("correo_usuario")
            or c.get("correo")
            or ""
        )

        usuario_id = c.get("usuario_id")
        if usuario_id:
            usuario = None
            try:
                usuario = db.usuarios.find_one({"_id": ObjectId(str(usuario_id))})
            except Exception:
                usuario = db.usuarios.find_one({"_id": usuario_id})

            # Filtra contratos cuyo usuario ya no existe o no es emprendedor.
            if not usuario:
                continue
            if rol_empr_ids and usuario.get("rol_id") not in rol_empr_ids:
                continue
            if usuario.get("rol_id") in rol_excluir:
                continue

            nombre = (usuario.get("nombre") or "").strip()
            ap_pat = (usuario.get("apellido_paterno") or "").strip()
            ap_mat = (usuario.get("apellido_materno") or "").strip()
            nombre_completo = " ".join([p for p in [nombre, ap_pat, ap_mat] if p]).strip()
            if nombre_completo:
                c["usuario_nombre"] = nombre_completo
            c["usuario_correo"] = (usuario.get("correo") or c["usuario_correo"]).strip()

        contratos.append(c)

    return render(request, "ver_contratos.html", {
        "todos_los_contratos": contratos
    })




# =========================
# VER CONTRATO (PDF SI EXISTE)
# =========================
def ver_contrato(request, id):
    guard = _require_admin(request)
    if guard:
        return guard
    try:
        contrato = db.contrato_proyecto.find_one({"_id": ObjectId(id)})
    except Exception:
        raise Http404("ID de contrato invalido.")

    if not contrato:
        raise Http404("Contrato no encontrado")

    archivo = contrato.get("archivo")
    nombre = contrato.get("nombre_archivo") or contrato.get("filename") or "contrato.pdf"
    tipo = contrato.get("tipo_archivo") or contrato.get("content_type") or "application/pdf"

    # Compatibilidad con contratos historicos guardados por ruta en disco.
    if not archivo:
        ruta = contrato.get("ruta") or contrato.get("ruta_pdf")
        if ruta and os.path.exists(ruta):
            with open(ruta, "rb") as f:
                archivo = f.read()
            if not tipo or tipo == "application/pdf":
                guessed = mimetypes.guess_type(ruta)[0]
                if guessed:
                    tipo = guessed
            if not nombre:
                nombre = os.path.basename(ruta)

    # Compatibilidad con contratos historicos guardados en GridFS.
    if not archivo and contrato.get("file_id"):
        try:
            grid_file = mongo_instance.fs.get(ObjectId(str(contrato.get("file_id"))))
            archivo = grid_file.read()
            nombre = nombre or getattr(grid_file, "filename", "contrato.pdf")
            tipo = tipo or getattr(grid_file, "content_type", "application/pdf")
        except Exception:
            archivo = None

    if not archivo:
        raise Http404("No se pudo mostrar el contrato.")

    response = HttpResponse(archivo, content_type=tipo)
    response["Content-Disposition"] = "inline"
    return response

def confirmar_contrato(request, id):
    guard = _require_admin(request)
    if guard:
        return guard
    if request.method != "POST":
        return redirect("ver_contratos")

    accion = request.POST.get("decision")
    motivo_rechazo = (request.POST.get("motivo_rechazo") or "").strip()
    if accion not in ["aceptado", "rechazado"]:
        messages.error(request, "Accion no valida.")
        return redirect("ver_contratos")

    try:
        contrato_obj_id = ObjectId(id)
        contrato = db.contrato_proyecto.find_one({"_id": contrato_obj_id})

        if not contrato:
            messages.error(request, "Contrato no encontrado.")
            return redirect("ver_contratos")

        if accion == "aceptado":
            db.contrato_proyecto.update_one(
                {"_id": contrato_obj_id},
                {"$set": {
                    "estado": "aceptado",
                    "fecha_decision": datetime.now(),
                    "actualizado_por": "admin"
                }}
            )
            
            # --- ACTIVACIÓN AUTOMÁTICA DEL EQUIPO Y PROYECTO ---
            usuario_id = contrato.get("usuario_id")
            if usuario_id:
                # 1. Buscar el proyecto
                proyecto = db.proyectos.find_one({
                    "$or": [
                        {"usuario_id": str(usuario_id)},
                        {"usuario_lider_id": str(usuario_id)},
                        {"correo_usuario": (contrato.get("usuario_correo") or "").strip().lower()}
                    ]
                })
                
                if proyecto:
                    # Activar el proyecto
                    db.proyectos.update_one(
                        {"_id": proyecto["_id"]},
                        {"$set": {
                            "estado": "Activo",
                            "ultima_actualizacion": datetime.utcnow(),
                            "motivo_baja": None,
                            "fecha_baja": None
                        }}
                    )
                    
                    # Identificar todos los correos del equipo para activarlos
                    emails_equipo = [proyecto.get("correo_usuario")]
                    for m in (proyecto.get("integrantes") or []):
                        if isinstance(m, dict) and m.get("correo"):
                            emails_equipo.append(m.get("correo").strip().lower())
                        elif isinstance(m, str):
                            emails_equipo.append(m.strip().lower())
                    
                    emails_equipo = list(set([e for e in emails_equipo if e]))
                    
                    # Activar a todos los usuarios del equipo
                    db.usuarios.update_many(
                        {"correo": {"$in": emails_equipo}},
                        {"$set": {"activo": True, "fecha_actualizacion": datetime.utcnow()}}
                    )
                else:
                    # Fallback si no hay proyecto (usuario solitario)
                    try:
                        u_obj_id = ObjectId(str(usuario_id))
                    except Exception:
                        u_obj_id = usuario_id
                    db.usuarios.update_one({"_id": u_obj_id}, {"$set": {"activo": True}})

            # Notificar a todo el equipo
            from apps.utils.email_service import notificar_equipo_contrato
            notificar_equipo_contrato(contrato_obj_id, "aceptado")

            messages.success(request, "El contrato fue aceptado y todo el equipo ha sido activado.")
        else:
            usuario_id = contrato.get("usuario_id")
            db.contrato_proyecto.delete_one({"_id": contrato_obj_id})
            if usuario_id:
                db.firmas.update_one(
                    {"usuario_id": usuario_id},
                    {"$set": {
                        "firma_contrato": None,
                        "fecha": datetime.now()
                    }},
                    upsert=True
                )
                usuario = None
                try:
                    usuario = db.usuarios.find_one({"_id": ObjectId(str(usuario_id))})
                except Exception:
                    usuario = db.usuarios.find_one({"_id": usuario_id})
                if usuario:
                    correo = (usuario.get("correo") or "").strip()
                    nombre = (usuario.get("nombre") or "Emprendedor").strip()
                    if correo:
                        from apps.utils.email_service import notificar_equipo_contrato
                        notificar_equipo_contrato(contrato_obj_id, "rechazado", motivo_rechazo)
            messages.success(request, "Contrato rechazado y eliminado. El usuario debe subir uno nuevo sin firma.")

    except Exception as e:
        print(f"Error en BD: {e}")
        messages.error(request, "Hubo un error al conectar con la base de datos.")

    return redirect("ver_contratos")


# =========================
# EXPEDIENTES VERSIONADOS (ADMIN)
# =========================
def _exp_normalizar_documento_clave(nombre):
    return re.sub(r"\s+", " ", (nombre or "").strip().lower())


def _exp_timestamp(fecha):
    if not isinstance(fecha, datetime):
        return None
    try:
        return fecha.timestamp()
    except Exception:
        try:
            return fecha.replace(tzinfo=None).timestamp()
        except Exception:
            return None


def _exp_formatear_fecha(fecha):
    if isinstance(fecha, datetime):
        try:
            fecha_local = timezone.localtime(fecha)
        except Exception:
            fecha_local = fecha
        return fecha_local.strftime("%d/%m/%Y %H:%M")
    return "Sin fecha"


def _exp_formatear_tamano(num_bytes):
    try:
        tam = float(num_bytes or 0)
    except Exception:
        tam = 0

    unidades = ["B", "KB", "MB", "GB"]
    indice = 0
    while tam >= 1024 and indice < len(unidades) - 1:
        tam /= 1024.0
        indice += 1

    if indice == 0:
        return f"{int(tam)} {unidades[indice]}"
    return f"{tam:.1f} {unidades[indice]}"


def _exp_historial_usuario_admin(usuario_id):
    documentos = list(
        db.expediente_documentos.find({"usuario_id": usuario_id}).sort(
            [("fecha_subida", -1), ("version", -1), ("_id", -1)]
        )
    )

    grupos = {}
    for doc in documentos:
        documento_id = str(doc["_id"])
        clave = doc.get("documento_clave") or _exp_normalizar_documento_clave(
            doc.get("nombre_documento") or doc.get("nombre_archivo") or documento_id
        )
        nombre_documento = (
            doc.get("nombre_documento")
            or doc.get("titulo_documento")
            or doc.get("nombre_archivo")
            or "Documento sin nombre"
        )
        version = int(doc.get("version") or 1)
        fecha_subida = doc.get("fecha_subida")
        fecha_ts = _exp_timestamp(fecha_subida)

        version_data = {
            "id": documento_id,
            "version": version,
            "nombre_archivo": doc.get("nombre_archivo") or "archivo",
            "tipo_archivo": doc.get("tipo_archivo") or "application/octet-stream",
            "tamano_archivo": _exp_formatear_tamano(doc.get("tamano_bytes")),
            "fecha_subida": _exp_formatear_fecha(fecha_subida),
            "download_url": reverse("descargar_documento_expediente_admin", args=[documento_id]),
        }

        if clave not in grupos:
            grupos[clave] = {
                "clave": clave,
                "nombre_documento": nombre_documento,
                "total_versiones": 0,
                "ultima_fecha_ts": fecha_ts,
                "ultima_version_num": version,
                "ultima_version_label": f"v{version}",
                "ultima_fecha": _exp_formatear_fecha(fecha_subida),
                "versiones": [],
            }

        grupos[clave]["versiones"].append(version_data)
        grupos[clave]["total_versiones"] += 1

        if fecha_ts is not None:
            ultima_ts = grupos[clave]["ultima_fecha_ts"]
            if ultima_ts is None or fecha_ts > ultima_ts:
                grupos[clave]["ultima_fecha_ts"] = fecha_ts
                grupos[clave]["ultima_fecha"] = _exp_formatear_fecha(fecha_subida)

        if version > grupos[clave]["ultima_version_num"]:
            grupos[clave]["ultima_version_num"] = version
            grupos[clave]["ultima_version_label"] = f"v{version}"

    expedientes = list(grupos.values())
    for expediente in expedientes:
        expediente["versiones"].sort(key=lambda item: item["version"], reverse=True)

    expedientes.sort(
        key=lambda item: (item.get("ultima_fecha_ts") or 0, item["ultima_version_num"]),
        reverse=True
    )
    return expedientes


def _exp_historial_proyecto_admin(proyecto_id):
    documentos = list(
        db.expediente_documentos.find({"proyecto_id": str(proyecto_id)}).sort(
            [("fecha_subida", -1), ("version", -1), ("_id", -1)]
        )
    )

    grupos = {}
    for doc in documentos:
        documento_id = str(doc["_id"])
        clave = doc.get("documento_clave") or _exp_normalizar_documento_clave(
            doc.get("nombre_documento") or doc.get("nombre_archivo") or documento_id
        )
        nombre_documento = (
            doc.get("nombre_documento")
            or doc.get("titulo_documento")
            or doc.get("nombre_archivo")
            or "Documento sin nombre"
        )
        version = int(doc.get("version") or 1)
        fecha_subida = doc.get("fecha_subida")
        fecha_ts = _exp_timestamp(fecha_subida)

        version_data = {
            "id": documento_id,
            "version": version,
            "nombre_archivo": doc.get("nombre_archivo") or "archivo",
            "tipo_archivo": doc.get("tipo_archivo") or "application/octet-stream",
            "tamano_archivo": _exp_formatear_tamano(doc.get("tamano_bytes")),
            "fecha_subida": _exp_formatear_fecha(fecha_subida),
            "download_url": reverse("descargar_documento_expediente_admin", args=[documento_id]),
        }

        if clave not in grupos:
            grupos[clave] = {
                "clave": clave,
                "nombre_documento": nombre_documento,
                "total_versiones": 0,
                "ultima_fecha_ts": fecha_ts,
                "ultima_version_num": version,
                "ultima_version_label": f"v{version}",
                "ultima_fecha": _exp_formatear_fecha(fecha_subida),
                "versiones": [],
            }

        grupos[clave]["versiones"].append(version_data)
        grupos[clave]["total_versiones"] += 1

        if fecha_ts is not None:
            ultima_ts = grupos[clave]["ultima_fecha_ts"]
            if ultima_ts is None or fecha_ts > ultima_ts:
                grupos[clave]["ultima_fecha_ts"] = fecha_ts
                grupos[clave]["ultima_fecha"] = _exp_formatear_fecha(fecha_subida)

        if version > grupos[clave]["ultima_version_num"]:
            grupos[clave]["ultima_version_num"] = version
            grupos[clave]["ultima_version_label"] = f"v{version}"

    expedientes = list(grupos.values())
    for expediente in expedientes:
        expediente["versiones"].sort(key=lambda item: item["version"], reverse=True)

    expedientes.sort(
        key=lambda item: (item.get("ultima_fecha_ts") or 0, item["ultima_version_num"]),
        reverse=True
    )
    return expedientes


def expedientes_admin(request):
    guard = _require_admin(request)
    if guard:
        return guard

    admin_ids = {ADMIN_ROLE_ID}
    try:
        rol_admin = db.roles.find_one({"nombre": {"$regex": "^Administrador$", "$options": "i"}})
        if rol_admin:
            admin_ids.add(str(rol_admin["_id"]))
            admin_ids.add(rol_admin["_id"])
    except Exception:
        pass

    # 1. Obtener todos los proyectos activos con sus integrantes
    proyectos_cursor = db.proyectos.find().sort("nombre", 1)
    proyectos_data = []
    usuarios_mapeados = set()

    total_documentos = 0
    total_versiones = 0

    for proyecto in proyectos_cursor:
        integrantes_p = []
        # Emails de todos los miembros (Líder + Integrantes)
        emails_equipo = [proyecto.get("correo_usuario")]
        for m in (proyecto.get("integrantes") or []):
            if isinstance(m, dict) and m.get("correo"):
                emails_equipo.append(m.get("correo"))
            elif isinstance(m, str):
                emails_equipo.append(m)
        
        # Filtramos None o vacíos
        emails_equipo = [e for e in emails_equipo if e]

        # Buscar estos usuarios en la BD
        users_equipo = list(db.usuarios.find({"correo": {"$in": emails_equipo}}))
        
        for u in users_equipo:
            u_id = str(u["_id"])
            usuarios_mapeados.add(u_id)
            
            integrantes_p.append({
                "id": u_id,
                "nombre": u.get("nombre", "Sin nombre"),
                "correo": u.get("correo", ""),
                "es_lider": u.get("correo") == proyecto.get("correo_lider")
            })

        proyecto_id_str = str(proyecto["_id"])
        expedientes_proyecto = _exp_historial_proyecto_admin(proyecto_id_str)
        
        docs_count = len(expedientes_proyecto)
        versions_count = sum(item["total_versiones"] for item in expedientes_proyecto)
        total_documentos += docs_count
        total_versiones += versions_count

        ultima_ts = max([exp.get("ultima_fecha_ts") for exp in expedientes_proyecto if exp.get("ultima_fecha_ts")], default=None)
        ultima_fecha = _exp_formatear_fecha(datetime.fromtimestamp(ultima_ts)) if ultima_ts else "Sin registros"

        # Intentar obtener nombre del proyecto de múltiples fuentes
        nombre_proyecto = proyecto.get("nombre_proyecto") or proyecto.get("nombre")
        if not nombre_proyecto or nombre_proyecto == "Proyecto sin nombre":
            # Buscar en solicitudes relacionadas si existe
            sol_related = db.solicitudes.find_one({"usuario_id": proyecto.get("usuario_id")})
            if sol_related:
                nombre_proyecto = sol_related.get("nombre_proyecto") or sol_related.get("nombre")

        proyectos_data.append({
            "nombre_proyecto": nombre_proyecto or "Proyecto sin nombre",
            "integrantes": integrantes_p,
            "id_proyecto": proyecto_id_str,
            "expedientes": expedientes_proyecto,
            "total_documentos": docs_count,
            "total_versiones": versions_count,
            "ultima_fecha": ultima_fecha
        })

    # 2. Usuarios sin proyecto (Huérfanos o con solicitud en proceso)
    filtro_huerfanos = {
        "rol_id": {"$nin": list(admin_ids)},
        "_id": {"$nin": [ObjectId(uid) for uid in usuarios_mapeados if ObjectId.is_valid(uid)]}
    }
    huerfanos_cursor = db.usuarios.find(filtro_huerfanos).sort("nombre", 1)
    
    usuarios_extra = []
    for u in huerfanos_cursor:
        u_id = str(u["_id"])
        expedientes = _exp_historial_usuario_admin(u_id)
        docs_count = len(expedientes)
        versions_count = sum(item["total_versiones"] for item in expedientes)
        total_documentos += docs_count
        total_versiones += versions_count
        ultima_ts = max([exp.get("ultima_fecha_ts") for exp in expedientes if exp.get("ultima_fecha_ts")], default=None)
        ultima_fecha = _exp_formatear_fecha(datetime.fromtimestamp(ultima_ts)) if ultima_ts else "Sin registros"

        usuarios_extra.append({
            "id": u_id,
            "nombre": u.get("nombre", "Sin nombre"),
            "correo": u.get("correo", ""),
            "expedientes": expedientes,
            "total_documentos": docs_count,
            "total_versiones": versions_count,
            "ultima_fecha": ultima_fecha,
        })

    contexto = {
        "proyectos_expedientes": proyectos_data,
        "usuarios_sin_proyecto": usuarios_extra,
        "total_proyectos": len(proyectos_data),
        "total_documentos": total_documentos,
        "total_versiones": total_versiones,
    }
    return render(request, "expedientes_admin.html", contexto)


def descargar_documento_expediente_admin(request, documento_id):
    guard = _require_admin(request)
    if guard:
        return guard

    try:
        documento = db.expediente_documentos.find_one({"_id": ObjectId(documento_id)})
    except Exception:
        documento = None

    if not documento or not documento.get("archivo"):
        raise Http404("Documento no encontrado.")

    nombre = documento.get("nombre_archivo") or "documento"
    tipo = documento.get("tipo_archivo") or "application/octet-stream"

    response = HttpResponse(documento.get("archivo"), content_type=tipo)
    response["Content-Disposition"] = f'attachment; filename="{nombre}"'
    return response


def ver_documento_expediente_admin(request, documento_id):
    guard = _require_admin(request)
    if guard:
        return guard

    try:
        documento = db.expediente_documentos.find_one({"_id": ObjectId(documento_id)})
    except Exception:
        documento = None

    if not documento or not documento.get("archivo"):
        raise Http404("Documento no encontrado.")

    nombre = documento.get("nombre_archivo") or "documento"
    tipo = documento.get("tipo_archivo") or "application/octet-stream"
    response = HttpResponse(documento.get("archivo"), content_type=tipo)
    response["Content-Disposition"] = f'inline; filename=\"{nombre}\"'
    return response
        





def _chat_nombre_desde_usuario(usuario):
    nombre = (usuario.get("nombre") or "Usuario").strip()
    apellido_paterno = (usuario.get("apellido_paterno") or "").strip()
    apellido_materno = (usuario.get("apellido_materno") or "").strip()
    return " ".join([p for p in [nombre, apellido_paterno, apellido_materno] if p]) or "Usuario"


def _chat_nombre_sesion(request):
    nombre = (request.session.get("nombre") or "Administrador").strip()
    apellido_paterno = (request.session.get("apellido_paterno") or "").strip()
    apellido_materno = (request.session.get("apellido_materno") or "").strip()
    return " ".join([p for p in [nombre, apellido_paterno, apellido_materno] if p]) or "Administrador"


def _chat_es_admin(request):
    return request.session.get("rol") == "Administrador" and request.session.get("usuario_id")


def chat_admin(request):
    if not _chat_es_admin(request):
        return redirect("login")

    conversaciones = chat_admin_conversaciones_data()
    seleccionado = conversaciones[0]["proyecto_id"] if conversaciones else ""
    return render(request, "chat_admin.html", {
        "conversaciones": conversaciones,
        "usuario_inicial": seleccionado
    })


def chat_admin_conversaciones_data():
    proyectos = list(db.proyectos.find().sort("nombre_proyecto", 1))
    ultimo_mensaje = {}

    # Obtenemos el último mensaje de cada proyecto
    for msg in db.chat_mensajes.find({"proyecto_id": {"$exists": True, "$ne": ""}}).sort("creado_en", -1):
        pid = msg.get("proyecto_id")
        if pid and pid not in ultimo_mensaje:
            ultimo_mensaje[pid] = msg

    conversaciones = []
    for p in proyectos:
        pid = str(p["_id"])
        nombre = (p.get("nombre_proyecto") or "").strip()
        lider = p.get("resumen", {}).get("lider", "Sin líder")
        
        # Fallback si no hay nombre
        if not nombre or nombre.lower() == "proyecto":
            nombre = f"Proyecto de {lider}"

        ultimo = ultimo_mensaje.get(pid, {})
        fecha = ultimo.get("creado_en")
        fecha_texto = fecha.strftime("%H:%M") if isinstance(fecha, datetime) else ""
        conversaciones.append({
            "id": pid,
            "proyecto_id": pid,
            "proyecto_nombre": nombre,
            "lider": lider,
            "correo": p.get("correo_usuario") or p.get("resumen", {}).get("correo", ""),
            "ultimo_mensaje": (ultimo.get("mensaje") or "").strip(),
            "hora_ultimo_mensaje": fecha_texto,
            "tipo": "proyecto"
        })

    return conversaciones


def chat_admin_conversaciones(request):
    if not _chat_es_admin(request):
        return JsonResponse({"error": "No autorizado"}, status=403)
    return JsonResponse({"conversaciones": chat_admin_conversaciones_data()})


def chat_admin_mensajes(request, usuario_id):
    if not _chat_es_admin(request):
        return JsonResponse({"error": "No autorizado"}, status=403)

    # Tratamos usuario_id como proyecto_id para el filtrado
    mensajes = list(db.chat_mensajes.find({"proyecto_id": usuario_id}).sort("creado_en", 1))
    datos = []
    for msg in mensajes:
        fecha = msg.get("creado_en")
        msg_id = str(msg.get("_id"))
        adjunto = msg.get("adjunto") or {}
        es_mio = msg.get("emisor_tipo") == "admin"
        datos.append({
            "id": msg_id,
            "mensaje": msg.get("mensaje", ""),
            "emisor_tipo": msg.get("emisor_tipo", "usuario"),
            "emisor_nombre": msg.get("emisor_nombre", "Usuario"),
            "hora": fecha.strftime("%H:%M") if isinstance(fecha, datetime) else "",
            "es_mio": es_mio,
            "editado": bool(msg.get("editado")),
            "adjunto": bool(adjunto.get("file_id")),
            "adjunto_nombre": adjunto.get("filename", ""),
            "adjunto_tipo": adjunto.get("content_type", ""),
            "adjunto_url": f"/admin/chats/api/archivo/{msg_id}/" if adjunto.get("file_id") else "",
            "puede_editar": es_mio and not msg.get("eliminado", False),
            "puede_eliminar": es_mio and not msg.get("eliminado", False)
        })

    return JsonResponse({"mensajes": datos})


@csrf_exempt
def chat_admin_enviar(request, usuario_id):
    if not _chat_es_admin(request):
        return JsonResponse({"error": "No autorizado"}, status=403)
    if request.method != "POST":
        return JsonResponse({"error": "Metodo no permitido"}, status=405)

    payload = {}
    if request.content_type and "application/json" in request.content_type:
        try:
            payload = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "JSON invalido"}, status=400)
        mensaje = (payload.get("mensaje") or "").strip()
        archivo = None
    else:
        mensaje = (request.POST.get("mensaje") or "").strip()
        archivo = request.FILES.get("archivo")

    if not mensaje and not archivo:
        return JsonResponse({"error": "Mensaje vacio"}, status=400)

    try:
        proyecto_obj_id = ObjectId(usuario_id)
    except Exception:
        return JsonResponse({"error": "Proyecto invalido"}, status=400)

    proyecto = db.proyectos.find_one({"_id": proyecto_obj_id})
    if not proyecto:
        return JsonResponse({"error": "Proyecto no encontrado"}, status=404)
    
    proyecto_nombre = proyecto.get("nombre_proyecto", "Proyecto")

    adjunto = None
    if archivo:
        file_id = mongo_instance.fs.put(
            archivo.read(),
            filename=archivo.name,
            content_type=getattr(archivo, "content_type", "application/octet-stream")
        )
        adjunto = {
            "file_id": str(file_id),
            "filename": archivo.name,
            "content_type": getattr(archivo, "content_type", "application/octet-stream")
        }

    db.chat_mensajes.insert_one({
        "proyecto_id": usuario_id,
        "usuario_id": "admin",
        "usuario_nombre": "Administración",
        "emisor_tipo": "admin",
        "emisor_id": request.session.get("usuario_id"),
        "emisor_nombre": _chat_nombre_sesion(request),
        "mensaje": mensaje,
        "adjunto": adjunto,
        "creado_en": timezone.now()
    })

    return JsonResponse({"success": True})


@csrf_exempt
def chat_admin_editar(request, mensaje_id):
    if not _chat_es_admin(request):
        return JsonResponse({"error": "No autorizado"}, status=403)
    if request.method != "POST":
        return JsonResponse({"error": "Metodo no permitido"}, status=405)

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON invalido"}, status=400)

    nuevo_texto = (payload.get("mensaje") or "").strip()
    if not nuevo_texto:
        return JsonResponse({"error": "Mensaje vacio"}, status=400)

    try:
        msg_id = ObjectId(mensaje_id)
    except Exception:
        return JsonResponse({"error": "Mensaje invalido"}, status=400)

    resultado = db.chat_mensajes.update_one(
        {"_id": msg_id, "emisor_tipo": "admin", "emisor_id": request.session.get("usuario_id")},
        {"$set": {"mensaje": nuevo_texto, "editado": True, "fecha_edicion": timezone.now()}}
    )
    if resultado.matched_count == 0:
        return JsonResponse({"error": "No se puede editar este mensaje"}, status=403)

    return JsonResponse({"success": True})


@csrf_exempt
def chat_admin_eliminar(request, mensaje_id):
    if not _chat_es_admin(request):
        return JsonResponse({"error": "No autorizado"}, status=403)
    if request.method != "POST":
        return JsonResponse({"error": "Metodo no permitido"}, status=405)

    try:
        msg_id = ObjectId(mensaje_id)
    except Exception:
        return JsonResponse({"error": "Mensaje invalido"}, status=400)

    msg = db.chat_mensajes.find_one(
        {"_id": msg_id, "emisor_tipo": "admin", "emisor_id": request.session.get("usuario_id")}
    )
    if not msg:
        return JsonResponse({"error": "No se puede eliminar este mensaje"}, status=403)

    adjunto = msg.get("adjunto") or {}
    file_id = adjunto.get("file_id")
    if file_id:
        try:
            mongo_instance.fs.delete(ObjectId(file_id))
        except Exception:
            pass

    db.chat_mensajes.update_one(
        {"_id": msg_id},
        {"$set": {
            "mensaje": "Mensaje eliminado",
            "eliminado": True,
            "editado": False,
            "adjunto": None
        }}
    )
    return JsonResponse({"success": True})


def chat_admin_archivo(request, mensaje_id):
    if not _chat_es_admin(request):
        return JsonResponse({"error": "No autorizado"}, status=403)

    try:
        msg_id = ObjectId(mensaje_id)
    except Exception:
        return JsonResponse({"error": "Mensaje invalido"}, status=400)

    mensaje = db.chat_mensajes.find_one({"_id": msg_id})
    if not mensaje:
        raise Http404("Mensaje no encontrado")

    adjunto = mensaje.get("adjunto") or {}
    file_id = adjunto.get("file_id")
    if not file_id:
        raise Http404("Archivo no encontrado")

    try:
        file_obj_id = file_id if isinstance(file_id, ObjectId) else ObjectId(str(file_id))
        archivo = mongo_instance.fs.get(file_obj_id)
    except Exception:
        raise Http404("Archivo no encontrado")

    contenido = archivo.read()
    content_type = adjunto.get("content_type") or "application/octet-stream"
    nombre = adjunto.get("filename") or "archivo"
    inline = content_type.startswith("image/") or content_type == "application/pdf"
    disposition = "inline" if inline else "attachment"

    response = HttpResponse(contenido, content_type=content_type)
    response["Content-Disposition"] = f'{disposition}; filename="{nombre}"'
    return response

def agregar_administrador(request):
    guard = _require_admin(request)
    if guard:
        return guard
    
    admins_cursor = db.usuarios.find({"rol_id": {"$in": ADMIN_ROLE_IDS}}).sort("fecha_creacion", -1)
    
    lista_admins = []
    for a in admins_cursor:
        lista_admins.append({
            "id": str(a.get("_id")),
            "nombre": a.get("nombre", "Sin nombre"),
            "correo": a.get("correo", "Sin correo"),
            
            "password": a.get("contrasena", "********") 
        })

    
    return render(request, "agregar_administrador.html", {
        "administradores": lista_admins
    })
    
@csrf_exempt
def crear_admin_api(request):
    guard = _require_admin(request)
    if guard:
        return guard
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            correo = (data.get("correo") or "").strip()
            if not correo:
                return JsonResponse({"status": "error", "message": "Correo requerido"}, status=400)

            # Evita duplicar correos
            existente = db.usuarios.find_one({"correo": correo})
            if existente:
                return JsonResponse({"status": "error", "message": "El correo ya esta registrado"}, status=400)
            
            db.usuarios.insert_one({
                "nombre": data.get("nombre"),
                "apellido_paterno": "",
                "apellido_materno": "", 
                "correo": correo,
                "contrasena": data.get("password"),
                "rol_id": ADMIN_ROLE_ID,
                "activo": True,
                "fecha_creacion": datetime.utcnow()
            })
            return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({"status": "error", "message": "Metodo no permitido"}, status=405)


@csrf_exempt
def actualizar_password_admin(request, id):
    guard = _require_admin(request)
    if guard:
        return guard
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Metodo no permitido"}, status=405)
    try:
        data = json.loads(request.body or "{}")
    except Exception:
        data = {}
    nueva = (data.get("password") or "").strip()
    if len(nueva) < 8:
        return JsonResponse({"success": False, "error": "Contrasena muy corta"}, status=400)
    filtro = {"rol_id": {"$in": ADMIN_ROLE_IDS}}
    try:
        filtro["_id"] = ObjectId(id)
    except Exception:
        filtro["_id"] = id
    db.usuarios.update_one(filtro, {"$set": {"contrasena": nueva}})
    return JsonResponse({"success": True})


@csrf_exempt
def eliminar_admin(request, id):
    guard = _require_admin(request)
    if guard:
        return guard
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Metodo no permitido"}, status=405)
    filtro = {"rol_id": {"$in": ADMIN_ROLE_IDS}}
    try:
        filtro["_id"] = ObjectId(id)
    except Exception:
        filtro["_id"] = id
    db.usuarios.delete_one(filtro)
    return JsonResponse({"success": True})


# =========================
# PROYECTOS
# =========================
def _serializar_proyecto(proyecto, usuarios_map):
    usuario_id = str(proyecto.get("usuario_id", ""))
    correo_usuario = (proyecto.get("correo_usuario") or proyecto.get("resumen", {}).get("correo") or "").strip().lower()
    usr = usuarios_map.get(usuario_id) or usuarios_map.get(correo_usuario, {})
    return {
        "id": str(proyecto.get("_id")),
        "nombre_proyecto": proyecto.get("nombre_proyecto", "Proyecto"),
        "estado": proyecto.get("estado", "Activo"),
        "ultima_actualizacion": _formatear_fecha_corta(proyecto.get("ultima_actualizacion")),
        "motivo_baja": proyecto.get("motivo_baja") or "",
        "fecha_baja": _formatear_fecha_corta(proyecto.get("fecha_baja")),
        "usuario": {
            "id": usuario_id,
            "nombre": usr.get("nombre", "Sin nombre"),
            "correo": usr.get("correo", ""),
            "activo": usr.get("activo", True),
        },
        "resumen": proyecto.get("resumen", {}),
        "integrantes": proyecto.get("integrantes") or proyecto.get("resumen", {}).get("integrantes") or []
    }


def proyectos_activos(request):
    guard = _require_admin(request)
    if guard:
        return guard
    return render(request, "proyectos_activos.html")


def proyectos_api(request):
    guard = _require_admin(request)
    if guard:
        return guard
    if request.method != "GET":
        return JsonResponse({"error": "Metodo no permitido"}, status=405)

    proyectos = list(db.proyectos.find())

    # Fallback: generar proyectos para usuarios sin registro usando su última solicitud
    usuarios_con_proyecto = {p.get("usuario_id") for p in proyectos}
    solicitudes = list(db.solicitudes.find().sort("_id", -1))
    for s in solicitudes:
        uid = str(s.get("usuario_id") or "")
        correo_sol = (s.get("correo") or "").strip().lower()

        # Si no hay usuario_id, intenta vincular por correo a un usuario existente
        if not uid and correo_sol:
            usr = db.usuarios.find_one({"correo": correo_sol})
            if usr:
                uid = str(usr.get("_id"))

        if uid and uid in usuarios_con_proyecto:
            continue
        now = datetime.utcnow()
        estado_solicitud = (s.get("estado") or "").upper()
        estado_proyecto = "Activo" if estado_solicitud == "ACEPTADO" else "En proceso"
        proyectos.append({
            "_id": s.get("_id"),
            "usuario_id": uid,
            "nombre_proyecto": (s.get("nombre_proyecto") or "Proyecto sin nombre").strip(),
            "estado": estado_proyecto,
            "resumen": {
                "descripcion": (s.get("descripcion_negocio") or "").strip(),
                "lider": (s.get("nombre_completo") or "").strip(),
                "correo": correo_sol,
                "telefono": (s.get("telefono") or "").strip(),
                "carrera": (s.get("carrera") or "").strip(),
                "equipo": s.get("integrantes_equipo"),
            },
            "ultima_actualizacion": s.get("fecha_creacion") or now,
            "motivo_baja": None,
            "fecha_baja": None,
            "correo_usuario": correo_sol,
        })
        usuarios_con_proyecto.add(uid)

    proyectos.sort(key=lambda p: p.get("ultima_actualizacion") or datetime.min, reverse=True)
    usuario_ids = [u for u in {p.get("usuario_id") for p in proyectos if p.get("usuario_id")} if u]
    correos = [p.get("correo_usuario") for p in proyectos if p.get("correo_usuario")]
    usuarios_cursor = db.usuarios.find({
        "$or": [
            {"_id": {"$in": [ObjectId(u) for u in usuario_ids if ObjectId.is_valid(str(u))]}},
            {"correo": {"$in": correos}}
        ]
    })
    usuarios_map = {}
    for u in usuarios_cursor:
        usuarios_map[str(u["_id"])] = u
        if u.get("correo"):
            usuarios_map[u.get("correo").strip().lower()] = u

    data = [_serializar_proyecto(p, usuarios_map) for p in proyectos]
    return JsonResponse({"proyectos": data})


@csrf_exempt
def proyecto_cambiar_estado(request, id):
    guard = _require_admin(request)
    if guard:
        return guard
    if request.method != "POST":
        return JsonResponse({"error": "Metodo no permitido"}, status=405)

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        payload = {}

    nuevo_estado = (payload.get("estado") or "").strip()
    motivo = (payload.get("motivo") or "").strip()

    estados_validos = ["Activo", "Finalizado", "Inactivo"]
    if nuevo_estado not in estados_validos:
        return JsonResponse({"error": "Estado invalido"}, status=400)

    try:
        proyecto_obj_id = ObjectId(id)
    except Exception:
        return JsonResponse({"error": "ID invalido"}, status=400)

    proyecto = db.proyectos.find_one({"_id": proyecto_obj_id})
    if not proyecto:
        return JsonResponse({"error": "Proyecto no encontrado"}, status=404)

    ahora = datetime.utcnow()
    update = {
        "estado": nuevo_estado,
        "ultima_actualizacion": ahora,
        "motivo_baja": motivo if nuevo_estado != "Activo" else None,
        "fecha_baja": ahora if nuevo_estado != "Activo" else None,
    }

    db.proyectos.update_one({"_id": proyecto_obj_id}, {"$set": update})

    usuario_id = proyecto.get("usuario_id")
    if usuario_id:
        try:
            filtro_usuario = {"_id": ObjectId(usuario_id)}
        except Exception:
            filtro_usuario = {"_id": usuario_id}
        db.usuarios.update_one(filtro_usuario, {"$set": {"activo": nuevo_estado == "Activo"}})

    proyecto_actualizado = db.proyectos.find_one({"_id": proyecto_obj_id})
    usuarios_cursor = db.usuarios.find({"_id": {"$in": [ObjectId(u) for u in [usuario_id] if ObjectId.is_valid(str(u))]}})
    usuarios_map = {str(u["_id"]): u for u in usuarios_cursor}
    return JsonResponse({"proyecto": _serializar_proyecto(proyecto_actualizado, usuarios_map)})


@csrf_exempt
def finalizar_proyecto_api(request, id):
    """
    Marca un proyecto como Finalizado, inactiva a sus integrantes y envía certificados.
    """
    guard = _require_admin(request)
    if guard: return guard
    
    if request.method != "POST":
        return JsonResponse({"error": "Metodo no permitido"}, status=405)

    try:
        p_id = ObjectId(id)
    except Exception:
        return JsonResponse({"error": "ID invalido"}, status=400)

    proyecto = db.proyectos.find_one({"_id": p_id})
    if not proyecto:
        return JsonResponse({"error": "Proyecto no encontrado"}, status=404)

    archivo = request.FILES.get("certificado")
    archivo_bin = None
    nombre_archivo = "Certificado.pdf"
    content_type = "application/pdf"
    
    if archivo:
        archivo_bin = archivo.read()
        nombre_archivo = archivo.name
        content_type = archivo.content_type
        
        # Guardar en GridFS para referencia histórica
        file_id = mongo_instance.fs.put(
            archivo_bin,
            filename=nombre_archivo,
            content_type=content_type,
            proyecto_id=str(p_id),
            tipo="certificado_finalizacion"
        )
        
        # Actualizar proyecto con el cert
        db.proyectos.update_one({"_id": p_id}, {"$set": {"certificado_id": str(file_id)}})

    # Actualizar estado del proyecto
    ahora = datetime.utcnow()
    db.proyectos.update_one({"_id": p_id}, {
        "$set": {
            "estado": "Finalizado",
            "ultima_actualizacion": ahora,
            "fecha_finalizacion": ahora
        }
    })

    # Inactivar a todo el equipo
    emails_equipo = [proyecto.get("correo_usuario")]
    for m in (proyecto.get("integrantes") or []):
        if isinstance(m, dict) and m.get("correo"):
            emails_equipo.append(m.get("correo").strip().lower())
        elif isinstance(m, str):
            emails_equipo.append(m.strip().lower())
    
    emails_equipo = list(set([e for e in emails_equipo if e]))
    
    db.usuarios.update_many(
        {"correo": {"$in": emails_equipo}},
        {"$set": {"activo": False}}
    )

    # Notificar y enviar certificado
    from apps.utils.email_service import enviar_certificado_finalizacion
    p_nombre = proyecto.get("nombre_proyecto") or "Proyecto"
    
    for email in emails_equipo:
        usr = db.usuarios.find_one({"correo": email})
        nombre_dest = usr.get("nombre") if usr else "Emprendedor"
        enviar_certificado_finalizacion(email, nombre_dest, p_nombre, archivo_bin, nombre_archivo)

    return JsonResponse({"success": True})

def usuarios(request):
    guard = _require_admin(request)
    if guard:
        return guard

    # Traer solo emprendedores (excluir administradores).
    rol_emprendedor = db.roles.find_one({"nombre": {"$regex": "^Emprendedor$", "$options": "i"}})
    rol_ids = []
    if rol_emprendedor:
        rol_ids.extend([str(rol_emprendedor.get("_id")), rol_emprendedor.get("_id")])

    if rol_ids:
        filtro = {"rol_id": {"$in": rol_ids}}
    else:
        # Si no hay rol "Emprendedor" en la BD, excluimos admins y mostramos el resto.
        filtro = {"rol_id": {"$nin": ADMIN_ROLE_IDS}}

    usuarios_cursor = db.usuarios.find(filtro)

    # Obtener proyectos para agrupar
    proyectos = {str(p["usuario_id"]): p.get("nombre_proyecto", "Proyecto sin nombre") for p in db.proyectos.find()}
    proyectos_agrupados = {}

    for u in usuarios_cursor:
        u_id_str = str(u["_id"])
        rol_nombre = "Sin rol"

        if u.get("rol_id"):
            rol = None
            try:
                rol = db.roles.find_one({"_id": ObjectId(u["rol_id"])})
            except Exception:
                rol = db.roles.find_one({"_id": u["rol_id"]})
            if rol:
                rol_nombre = rol.get("nombre", "Sin rol")

        # Buscar a qué proyecto pertenece
        nombre_proyecto = "Sin Proyecto"
        if u_id_str in proyectos:
            nombre_proyecto = proyectos[u_id_str]
        else:
            proyecto_integrante = db.proyectos.find_one({"integrantes.correo": u.get("correo")})
            if proyecto_integrante:
                nombre_proyecto = proyecto_integrante.get("nombre_proyecto", "Proyecto sin nombre")

        if nombre_proyecto not in proyectos_agrupados:
            proyectos_agrupados[nombre_proyecto] = []

        proyectos_agrupados[nombre_proyecto].append({
            "id": u_id_str,
            "nombre": u.get("nombre", ""),
            "correo": u.get("correo", ""),
            "rol": rol_nombre,
            "activo": u.get("activo", True)
        })

    return render(request, "usuarios.html", {
        "proyectos_usuarios": proyectos_agrupados
    })

@csrf_exempt
def bloquear_usuario(request, id):
    guard = _require_admin(request)
    if guard:
        return guard

    if request.method == "POST":

        db.usuarios.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"activo": False}}
        )

        return JsonResponse({"success": True})

    return JsonResponse({"error": "Metodo no permitido"}, status=405)

@csrf_exempt
def desbloquear_usuario(request, id):
    guard = _require_admin(request)
    if guard:
        return guard

    if request.method == "POST":

        db.usuarios.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"activo": True}}
        )

        return JsonResponse({"success": True})

    return JsonResponse({"error": "Metodo no permitido"}, status=405)

@csrf_exempt
def cambiar_estado_usuario(request, id):
    guard = _require_admin(request)
    if guard:
        return guard

    if request.method == "POST":

        usuario = db.usuarios.find_one({"_id": ObjectId(id)})

        if not usuario:
            return JsonResponse({"success": False})

        nuevo_estado = not usuario.get("activo", True)

        db.usuarios.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"activo": nuevo_estado}}
        )

        return JsonResponse({
            "success": True,
            "activo": nuevo_estado
        })

    return JsonResponse({"success": False})


@csrf_exempt
def actualizar_password_usuario(request, id):
    guard = _require_admin(request)
    if guard:
        return guard
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Metodo no permitido"}, status=405)
    try:
        data = json.loads(request.body or "{}")
    except Exception:
        data = {}
    nueva = (data.get("password") or "").strip()
    if len(nueva) < 8:
        return JsonResponse({"success": False, "error": "Contrasena muy corta"}, status=400)
    db.usuarios.update_one({"_id": ObjectId(id)}, {"$set": {"contrasena": nueva}})
    return JsonResponse({"success": True})


def _ejecutar_borrado_cascada_usuario(usuario_id_str):
    """
    Helper que ejecuta el borrado total de un usuario y, si es líder, 
    de todo su equipo y proyecto asociado.
    """
    try:
        target_obj_id = ObjectId(usuario_id_str)
    except Exception:
        return 0

    usuario = db.usuarios.find_one({"_id": target_obj_id})
    if not usuario:
        return 0

    correo_usuario = (usuario.get("correo") or "").strip().lower()
    
    # Buscamos proyectos vinculados
    proyecto = db.proyectos.find_one({
        "$or": [
            {"usuario_id": usuario_id_str},
            {"usuario_lider_id": usuario_id_str},
            {"correo_usuario": correo_usuario},
            {"integrantes.correo": correo_usuario}
        ]
    })

    usuarios_a_eliminar = [target_obj_id]
    ids_match_str = [usuario_id_str]

    if proyecto:
        # Si hay proyecto, identificamos a todos los integrantes para el borrado total
        integrantes = proyecto.get("integrantes") or []
        correos_equipo = [correo_usuario]
        for inte in integrantes:
            c = (inte.get("correo") or "").strip().lower()
            if c: correos_equipo.append(c)
        
        # Buscar todos los IDs de usuario del equipo
        equipo_users = list(db.usuarios.find({"correo": {"$in": correos_equipo}}))
        for u in equipo_users:
            if u["_id"] not in usuarios_a_eliminar:
                usuarios_a_eliminar.append(u["_id"])
                ids_match_str.append(str(u["_id"]))

        # GridFS: Borrar archivos
        mensajes_con_archivo = db.chat_mensajes.find({
            "$or": [
                {"usuario_id": {"$in": ids_match_str}},
                {"receptor_id": {"$in": ids_match_str}}
            ],
            "adjunto.file_id": {"$exists": True}
        })
        for msg in mensajes_con_archivo:
            f_id = msg.get("adjunto", {}).get("file_id")
            if f_id:
                try: mongo_instance.fs.delete(ObjectId(f_id))
                except: pass

        docs_expediente = db.expediente_documentos.find({"usuario_id": {"$in": ids_match_str}})
        for doc in docs_expediente:
            f_id = doc.get("file_id")
            if f_id:
                try: mongo_instance.fs.delete(ObjectId(f_id))
                except: pass

        # Borrado en cascada
        cascada = [
            ("expediente_documentos", {"usuario_id": {"$in": ids_match_str}}),
            ("contrato_proyecto", {"usuario_id": {"$in": ids_match_str}}),
            ("proyectos", {"_id": proyecto["_id"]}),
            ("chat_mensajes", {
                "$or": [
                    {"usuario_id": {"$in": ids_match_str}},
                    {"receptor_id": {"$in": ids_match_str}}
                ]
            }),
            ("firmas", {"usuario_id": {"$in": ids_match_str}}),
        ]
        for col, filtro in cascada:
            db[col].delete_many(filtro)
    else:
        cascada_simple = [
            ("expediente_documentos", {"usuario_id": {"$in": ids_match_str}}),
            ("contrato_proyecto", {"usuario_id": {"$in": ids_match_str}}),
            ("chat_mensajes", {"usuario_id": {"$in": ids_match_str}}),
            ("firmas", {"usuario_id": {"$in": ids_match_str}}),
        ]
        for col, filtro in cascada_simple:
            db[col].delete_many(filtro)

    db.usuarios.delete_many({"_id": {"$in": usuarios_a_eliminar}})
    
    # También borrar solicitudes asociadas si existen por correo
    if correos_equipo:
        db.solicitudes.delete_many({"correo": {"$in": correos_equipo}})
        
    return len(usuarios_a_eliminar)

@csrf_exempt
def eliminar_usuario(request, id):
    guard = _require_admin(request)
    if guard: return guard
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Metodo no permitido"}, status=405)
    
    eliminados = _ejecutar_borrado_cascada_usuario(id)
    return JsonResponse({"success": True, "usuarios_eliminados": eliminados})

@csrf_exempt
def eliminar_proyecto_api(request, id):
    guard = _require_admin(request)
    if guard: return guard
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Metodo no permitido"}, status=405)

    try:
        p_id = ObjectId(id)
    except:
        return JsonResponse({"success": False, "error": "ID invalido"}, status=400)

    proyecto = db.proyectos.find_one({"_id": p_id})
    if not proyecto:
        return JsonResponse({"success": False, "error": "Proyecto no encontrado"}, status=404)

    # Identificamos al líder para disparar el borrado en cascada
    usuario_id = proyecto.get("usuario_id") or proyecto.get("usuario_lider_id")
    
    if usuario_id:
        eliminados = _ejecutar_borrado_cascada_usuario(str(usuario_id))
    else:
        # Si por alguna razón no hay usuario_id (raro), borramos solo el proyecto y datos vinculados
        db.proyectos.delete_one({"_id": p_id})
        eliminados = 0

    return JsonResponse({"success": True, "usuarios_eliminados": eliminados})


# =========================
# CALENDARIO (ADMIN + USUARIO)
# =========================
def _serializar_evento(evt):
    return {
        "id": str(evt.get("_id")),
        "titulo": evt.get("titulo", ""),
        "fecha": evt.get("fecha"),
        "categoria": evt.get("categoria", ""),
        "color": evt.get("color", "#1f3c88"),
        "descripcion": evt.get("descripcion", ""),
    }


def calendario_admin(request):
    guard = _require_admin(request)
    if guard:
        return guard
    return render(request, "calendario_admin.html")


@csrf_exempt
def calendario_eventos(request):
    if request.method == "GET":
        eventos = [_serializar_evento(e) for e in db.calendario_eventos.find().sort("fecha", 1)]
        return JsonResponse({"eventos": eventos})

    guard = _require_admin(request)
    if guard:
        return guard

    try:
        data = json.loads(request.body or "{}")
    except Exception:
        data = {}

    if request.method == "POST":
        titulo = (data.get("titulo") or "").strip()
        fecha = (data.get("fecha") or "").strip()
        if not titulo or not fecha:
            return JsonResponse({"success": False, "error": "Titulo y fecha son requeridos"}, status=400)
        nuevo = {
            "titulo": titulo,
            "fecha": fecha,
            "categoria": (data.get("categoria") or "").strip(),
            "color": (data.get("color") or "#1f3c88").strip(),
            "descripcion": (data.get("descripcion") or "").strip(),
        }
        res = db.calendario_eventos.insert_one(nuevo)
        nuevo["_id"] = res.inserted_id
        return JsonResponse({"success": True, "evento": _serializar_evento(nuevo)})

    return JsonResponse({"success": False, "error": "Metodo no permitido"}, status=405)


@csrf_exempt
def calendario_evento_detalle(request, id):
    guard = _require_admin(request)
    if guard:
        return guard

    try:
        obj_id = ObjectId(id)
    except Exception:
        return JsonResponse({"success": False, "error": "ID invalido"}, status=400)

    if request.method == "PUT":
        try:
            data = json.loads(request.body or "{}")
        except Exception:
            data = {}
        update = {k: v for k, v in {
            "titulo": (data.get("titulo") or "").strip(),
            "fecha": (data.get("fecha") or "").strip(),
            "categoria": (data.get("categoria") or "").strip(),
            "color": (data.get("color") or "#1f3c88").strip(),
            "descripcion": (data.get("descripcion") or "").strip(),
        }.items() if v}
        if not update:
            return JsonResponse({"success": False, "error": "Sin datos"}, status=400)
        db.calendario_eventos.update_one({"_id": obj_id}, {"$set": update})
        return JsonResponse({"success": True})

    if request.method == "DELETE":
        db.calendario_eventos.delete_one({"_id": obj_id})
        return JsonResponse({"success": True})

    return JsonResponse({"success": False, "error": "Metodo no permitido"}, status=405)
    
