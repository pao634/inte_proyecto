import os
import uuid
import json
import re
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.http import HttpResponse, Http404
from django.urls import reverse
from pymongo import MongoClient
from config.database.mongo import mongo_instance, db
from datetime import datetime, timezone
from bson.objectid import ObjectId
from dotenv import load_dotenv
from django.views.decorators.csrf import csrf_exempt
from apps.utils.access_logic import check_team_contract_accepted, get_team_contract_status

load_dotenv()


def portal_visitante(request):
    from apps.public.views import _obtener_muro_unificado_public
    # Mostramos solo convocatorias por petición del usuario
    muro = _obtener_muro_unificado_public(request, es_visitante=True, solo_convocatorias=True)
    return render(request, 'portal_visitante.html', {"muro": muro})


def portal_publico(request):
    from apps.public.views import _obtener_muro_unificado_public
    # Mostramos solo convocatorias por petición del usuario
    muro = _obtener_muro_unificado_public(request, es_visitante=False, solo_convocatorias=True)
    return render(request, 'portal_publico.html', {"muro": muro})

def lista_anuncios(request):
    bloqueo = _bloqueo_por_contrato(request)
    if bloqueo:
        return bloqueo

    from apps.public.views import _obtener_muro_unificado_public
    # Obtenemos el muro completo pero filtramos por tipo anuncio si es necesario,
    # o mejor aún, usamos el dividido y tomamos anuncios.
    muro = _obtener_muro_unificado_public(dividido=True)["anuncios"]
    
    return render(request, 'ver_anuncios.html', {
        'anuncios': muro
    })

def panel_admin(request):
    return render(request, 'panel_admin.html')   

# Removed old helper function as it's replaced by _obtener_muro_unificado_public


# ==============================
# Vistas
# ==============================
def ver_convocatorias(request):
    """Vista que muestra las convocatorias (página independiente)"""
    bloqueo = _bloqueo_por_contrato(request)
    if bloqueo:
        return bloqueo

    from apps.public.views import _obtener_muro_unificado_public
    # Solo convocatorias para esta ruta específica
    muro = _obtener_muro_unificado_public(request, solo_convocatorias=True)
    return render(request, "ver_convocatorias.html", {"muro": muro, "layout": "grid"})


def calendario_emprendedor(request):
    bloqueo = _bloqueo_por_contrato(request)
    if bloqueo:
        return bloqueo
    return render(request, "calendario.html")


def guardar_documento(file, coleccion, usuario_id):

    if not file:
        return None

    contenido = file.read()

    documento = {
        "usuario_id": usuario_id,
        "nombre_archivo": file.name,
        "tipo_archivo": file.content_type,
        "archivo": contenido,
        "fecha_subida": datetime.now(timezone.utc)
    }

    resultado = db[coleccion].insert_one(documento)

    return str(resultado.inserted_id)


def _normalizar_documento_clave(nombre):
    return re.sub(r"\s+", " ", (nombre or "").strip().lower())


def _formatear_fecha_corta(fecha):
    if not isinstance(fecha, datetime):
        return "Sin fecha"
    try:
        fecha_local = fecha.astimezone(timezone.utc)
    except Exception:
        fecha_local = fecha
    return fecha_local.strftime("%d/%m/%Y %H:%M")


def _formatear_tamano_archivo(num_bytes):
    try:
        tamano = float(num_bytes or 0)
    except Exception:
        tamano = 0

    unidades = ["B", "KB", "MB", "GB"]
    indice = 0
    while tamano >= 1024 and indice < len(unidades) - 1:
        tamano /= 1024.0
        indice += 1

    if indice == 0:
        return f"{int(tamano)} {unidades[indice]}"
    return f"{tamano:.1f} {unidades[indice]}"


def _historial_expediente_proyecto(proyecto_id):
    documentos = list(
        db.expediente_documentos.find({"proyecto_id": str(proyecto_id)}).sort(
            [("fecha_subida", -1), ("version", -1), ("_id", -1)]
        )
    )

    grupos = {}
    for doc in documentos:
        documento_id = str(doc["_id"])
        clave = doc.get("documento_clave") or _normalizar_documento_clave(
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
        version_data = {
            "id": documento_id,
            "version": version,
            "nombre_archivo": doc.get("nombre_archivo") or "archivo",
            "tipo_archivo": doc.get("tipo_archivo") or "application/octet-stream",
            "tamano_archivo": _formatear_tamano_archivo(doc.get("tamano_bytes")),
            "fecha_subida": _formatear_fecha_corta(fecha_subida),
        }

        if clave not in grupos:
            grupos[clave] = {
                "clave": clave,
                "nombre_documento": nombre_documento,
                "total_versiones": 0,
                "ultima_fecha_dt": fecha_subida if isinstance(fecha_subida, datetime) else datetime.min.replace(tzinfo=timezone.utc),
                "ultima_version_num": version,
                "ultima_version_label": f"v{version}",
                "ultima_fecha": _formatear_fecha_corta(fecha_subida),
                "versiones": [],
            }

        grupos[clave]["versiones"].append(version_data)
        grupos[clave]["total_versiones"] += 1

    expedientes = list(grupos.values())
    for expediente in expedientes:
        expediente["versiones"].sort(key=lambda item: item["version"], reverse=True)

    expedientes.sort(
        key=lambda item: (item["ultima_fecha_dt"], item["ultima_version_num"]),
        reverse=True
    )

    for exp in expedientes:
        exp.pop("ultima_fecha_dt", None)

    return expedientes


def _historial_expediente_usuario(usuario_id):
    documentos = list(
        db.expediente_documentos.find({"usuario_id": usuario_id}).sort(
            [("fecha_subida", -1), ("version", -1), ("_id", -1)]
        )
    )

    grupos = {}
    for doc in documentos:
        documento_id = str(doc["_id"])
        clave = doc.get("documento_clave") or _normalizar_documento_clave(
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
        version_data = {
            "id": documento_id,
            "version": version,
            "nombre_archivo": doc.get("nombre_archivo") or "archivo",
            "tipo_archivo": doc.get("tipo_archivo") or "application/octet-stream",
            "tamano_archivo": _formatear_tamano_archivo(doc.get("tamano_bytes")),
            "fecha_subida": _formatear_fecha_corta(fecha_subida),
        }

        if clave not in grupos:
            grupos[clave] = {
                "clave": clave,
                "nombre_documento": nombre_documento,
                "total_versiones": 0,
                "ultima_fecha_dt": fecha_subida if isinstance(fecha_subida, datetime) else datetime.min.replace(tzinfo=timezone.utc),
                "ultima_version_num": version,
                "ultima_version_label": f"v{version}",
                "ultima_fecha": _formatear_fecha_corta(fecha_subida),
                "versiones": [],
            }

        grupos[clave]["versiones"].append(version_data)
        grupos[clave]["total_versiones"] += 1

    expedientes = list(grupos.values())
    for expediente in expedientes:
        expediente["versiones"].sort(key=lambda item: item["version"], reverse=True)

    expedientes.sort(
        key=lambda item: (item["ultima_fecha_dt"], item["ultima_version_num"]),
        reverse=True
    )
    return expedientes

def _obtener_contrato_vigente():
    return db.contrato_vigente.find_one(sort=[("fecha_actualizacion", -1), ("_id", -1)])


def _crear_proyecto_desde_solicitud(solicitud, usuario_id):
    """Construye y guarda un proyecto a partir de una solicitud."""
    if not solicitud:
        return None
    usuario_id_str = str(usuario_id) if usuario_id else ""
    now = datetime.now(timezone.utc)
    estado_solicitud = (solicitud.get("estado") or "").upper()
    estado_proyecto = "Activo" if estado_solicitud == "ACEPTADO" else "En proceso"
    nuevo = {
        "usuario_id": usuario_id_str,
        "nombre_proyecto": (solicitud.get("nombre_proyecto") or "Proyecto sin nombre").strip(),
        "estado": estado_proyecto,
        "resumen": {
            "descripcion": (solicitud.get("descripcion_negocio") or "").strip(),
            "lider": (solicitud.get("nombre_completo") or "").strip(),
            "correo": (solicitud.get("correo") or "").strip(),
            "telefono": (solicitud.get("telefono") or "").strip(),
            "carrera": (solicitud.get("carrera") or "").strip(),
            "equipo": solicitud.get("integrantes_equipo"),
            "integrantes": solicitud.get("integrantes") or []
        },
        "integrantes": solicitud.get("integrantes") or [],
        "creado_en": now,
        "ultima_actualizacion": now,
        "motivo_baja": None,
        "fecha_baja": None,
        "correo_usuario": (solicitud.get("correo") or "").strip().lower(),
    }
    res = db.proyectos.insert_one(nuevo)
    nuevo["_id"] = res.inserted_id
    
    # Automatizar creación de grupo en chat (Mensaje de bienvenida del admin)
    db.chat_mensajes.insert_one({
        "proyecto_id": str(res.inserted_id),
        "usuario_id": "admin",
        "usuario_nombre": "Administración",
        "emisor_tipo": "admin",
        "emisor_id": "admin",
        "emisor_nombre": "Administración",
        "mensaje": f"¡Bienvenidos al chat del proyecto {nuevo['nombre_proyecto']}! Aquí daremos seguimiento a sus asesorías.",
        "creado_en": now
    })
    
    return nuevo


def _obtener_proyectos_usuario(usuario_id, correo=None):
    """Obtiene todos los proyectos donde el usuario es líder o integrante."""
    usuario_id_str = str(usuario_id)
    correo_str = (correo or "").strip().lower()

    query = {
        "$or": [
            {"usuario_id": usuario_id_str},
            {"usuario_lider_id": usuario_id_str},
            {"correo_usuario": correo_str},
            {"resumen.correo": correo_str},
            {"integrantes.correo": correo_str}
        ]
    }
    proyectos = list(db.proyectos.find(query).sort("ultima_actualizacion", -1))
    for p in proyectos:
        p["id"] = str(p["_id"])
    return proyectos


def _obtener_proyecto_usuario(usuario_id, correo=None):
    """Obtiene el proyecto; si no existe, intenta crearlo a partir de la última solicitud por usuario_id o correo."""
    usuario_id_str = str(usuario_id)
    correo_str = (correo or "").strip().lower()

    # 1. Buscar en la colección de proyectos (LIDER o INTEGRANTE)
    query = {
        "$or": [
            {"usuario_id": usuario_id_str},
            {"usuario_lider_id": usuario_id_str},
            {"correo_usuario": correo_str},
            {"resumen.correo": correo_str},
            {"integrantes.correo": correo_str}
        ]
    }
    proyecto = db.proyectos.find_one(query)
    if proyecto:
        return proyecto

    # 2. Si no hay proyecto, buscar por usuario_id en solicitudes
    solicitud = db.solicitudes.find_one(
        {"usuario_id": {"$in": [usuario_id_str, usuario_id]}},
        sort=[("_id", -1)]
    )
    # Si no hay solicitud con usuario_id, intentar por correo
    if not solicitud and correo_str:
        solicitud = db.solicitudes.find_one(
            {
                "$or": [
                    {"correo": {"$regex": f"^{re.escape(correo_str)}$", "$options": "i"}},
                    {"integrantes.correo": correo_str}
                ]
            },
            sort=[("_id", -1)]
        )
    if not solicitud:
        return None

    return _crear_proyecto_desde_solicitud(solicitud, usuario_id_str or solicitud.get("usuario_id"))


def _ultimo_contrato_usuario(usuario_id, contrato_vigente_id=None):
    filtro = {"usuario_id": usuario_id}
    if contrato_vigente_id:
        filtro["contrato_vigente_id"] = str(contrato_vigente_id)
    return db.contrato_proyecto.find_one(
        filtro,
        sort=[("fecha_subida", -1), ("_id", -1)]
    )


def _estado_contrato(contrato):
    if not contrato:
        return "Sin enviar"

    estado = (contrato.get("estado") or "enviado").lower()
    if estado == "aceptado":
        return "Aceptado"
    if estado == "rechazado":
        return "Rechazado"
    return "En revision"

def _estado_proyecto_meta(estado):
    estado = (estado or "Sin proyecto").strip()
    presets = {
        "Activo": {"tone": "ok", "mensaje": "Tu proyecto sigue activo en el programa."},
        "Finalizado": {"tone": "warn", "mensaje": "El proyecto concluyó sus entregables."},
        "Inactivo": {"tone": "bad", "mensaje": "El acceso está suspendido. Contacta a tu administrador."},
    }
    base = presets.get(estado, {"tone": "neutral", "mensaje": "Aún no tienes un proyecto asignado."})
    base.update({"estado": estado})
    return base

@csrf_exempt
def toggle_reaccion_convocatoria(request):
    """
    Permite a los usuarios logueados (emprendedores) dar o quitar 'me encanta', 'me gusta', etc.
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return JsonResponse({"status": "error", "message": "Debes iniciar sesión"}, status=401)

    try:
        data = json.loads(request.body)
        convocatoria_id = data.get("convocatoria_id")
        tipo = data.get("tipo", "love") # Default to 'love' (Me encanta)
    except Exception:
        return JsonResponse({"status": "error", "message": "Datos inválidos"}, status=400)

    if not convocatoria_id:
        return JsonResponse({"status": "error", "message": "Falta ID de convocatoria"}, status=400)

    try:
        convocatoria = db.convocatorias.find_one({"_id": ObjectId(convocatoria_id)})
        if not convocatoria:
            return JsonResponse({"status": "error", "message": "Convocatoria no encontrada"}, status=404)

        # Usaremos una estructura de [{ 'usuario_id': '...', 'tipo': '...' }]
        reacciones = convocatoria.get("reacciones", [])
        
        # Encontrar si el usuario ya reaccionó
        reaccion_actual = next((r for r in reacciones if isinstance(r, dict) and r.get("usuario_id") == usuario_id), None)
        
        # Compatibilidad con datos viejos (si r era solo un ID)
        if not reaccion_actual:
            if usuario_id in reacciones:
                reaccion_actual = {"usuario_id": usuario_id, "tipo": "like"}

        if reaccion_actual:
            if reaccion_actual.get("tipo") == tipo:
                # Si es el mismo tipo, lo quitamos (toggle off)
                db.convocatorias.update_one(
                    {"_id": ObjectId(convocatoria_id)},
                    {"$pull": {"reacciones": {"usuario_id": usuario_id}}}
                )
                # Cleanup for old format if necessary
                db.convocatorias.update_one(
                    {"_id": ObjectId(convocatoria_id)},
                    {"$pull": {"reacciones": usuario_id}}
                )
                accion = "removed"
            else:
                # Si es un tipo diferente, actualizamos el tipo
                db.convocatorias.update_one(
                    {"_id": ObjectId(convocatoria_id), "reacciones.usuario_id": usuario_id},
                    {"$set": {"reacciones.$.tipo": tipo}}
                )
                accion = "updated"
        else:
            # Nueva reacción
            db.convocatorias.update_one(
                {"_id": ObjectId(convocatoria_id)},
                {"$addToSet": {"reacciones": {"usuario_id": usuario_id, "tipo": tipo}}}
            )
            accion = "added"

        # Obtener nuevo conteo
        convocatoria_actualizada = db.convocatorias.find_one({"_id": ObjectId(convocatoria_id)})
        reacciones_nuevas = convocatoria_actualizada.get("reacciones", [])
        nuevo_conteo = len(reacciones_nuevas)

        return JsonResponse({
            "status": "success",
             "accion": accion,
             "nuevo_conteo": nuevo_conteo,
             "tipo": tipo if accion != "removed" else None
        })
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


def _etapas_proyecto(usuario_id, proyecto):
    """Calcula avance por etapas sincronizado para todo el equipo."""
    etapas = []
    usuario_id_str = str(usuario_id)

    # Etapa 1: Registro aceptado
    tiene_proyecto = bool(proyecto)
    etapas.append({
        "nombre": "Registro aceptado",
        "estado": "Completado" if tiene_proyecto else "Pendiente",
        "detalle": "Solicitud aprobada y proyecto creado.",
        "fecha": _formatear_fecha_corta(proyecto.get("creado_en")) if proyecto else None
    })

    # Etapa 2: Contrato (Sincronizado por equipo)
    estado_contrato, ultimo_contrato = get_team_contract_status(usuario_id_str)
    etapas.append({
        "nombre": "Contrato firmado",
        "estado": "Completado" if estado_contrato == "Aceptado" else ("En curso" if estado_contrato == "En revision" else "Pendiente"),
        "detalle": f"Estado del contrato: {estado_contrato}",
        "fecha": _formatear_fecha_corta(ultimo_contrato.get("fecha_subida")) if ultimo_contrato else None
    })

    # Etapa 3: Expediente / evidencias (Sincronizado por proyecto)
    if tiene_proyecto:
        query_docs = {"proyecto_id": str(proyecto.get("_id"))}
    else:
        query_docs = {"usuario_id": usuario_id_str}
        
    docs = db.expediente_documentos.count_documents(query_docs)
    estado_docs = "Completado" if docs >= 3 else ("En curso" if docs > 0 else "Pendiente")
    etapas.append({
        "nombre": "Expediente y evidencias",
        "estado": estado_docs,
        "detalle": f"Documentos del equipo: {docs}",
        "fecha": None
    })

    # Etapa 4: Mentoría inicial
    etapas.append({
        "nombre": "Mentoría inicial",
        "estado": "En curso" if estado_contrato == "Aceptado" else "Pendiente",
        "detalle": "Sesión de asesoría inicial con administración.",
        "fecha": None
    })

    total = len(etapas)
    completadas = len([e for e in etapas if e["estado"] == "Completado"])
    progreso = int((completadas / total) * 100) if total else 0
    return etapas, progreso

    return etapas, progreso


def _usuario_tiene_contrato_aceptado(usuario_id):
    return check_team_contract_accepted(usuario_id)

def _check_contrato_individual_u(uid):
    uid_str = str(uid)
    vigente = _obtener_contrato_vigente()
    vigente_id = vigente.get("_id") if vigente else None
    
    ultimo = _ultimo_contrato_usuario(uid_str, vigente_id)
    if ultimo and (ultimo.get("estado") or "").lower() == "aceptado":
        return True

    ultimo_aceptado = db.contrato_proyecto.find_one(
        {"usuario_id": uid_str, "estado": {"$regex": "^aceptado$", "$options": "i"}},
        sort=[("fecha_subida", -1), ("_id", -1)]
    )
    return bool(ultimo_aceptado)

@csrf_exempt
def toggle_reaccion_convocatoria(request):
    """
    Permite a los usuarios logueados (emprendedores) dar o quitar 'like' a una convocatoria.
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return JsonResponse({"status": "error", "message": "Debes iniciar sesión"}, status=401)

    try:
        data = json.loads(request.body)
        convocatoria_id = data.get("convocatoria_id")
    except Exception:
        return JsonResponse({"status": "error", "message": "Datos inválidos"}, status=400)

    if not convocatoria_id:
        return JsonResponse({"status": "error", "message": "Falta ID de convocatoria"}, status=400)

    try:
        convocatoria = db.convocatorias.find_one({"_id": ObjectId(convocatoria_id)})
        if not convocatoria:
            return JsonResponse({"status": "error", "message": "Convocatoria no encontrada"}, status=404)

        reacciones = convocatoria.get("reacciones", [])
        
        if usuario_id in reacciones:
            # Quitar like
            db.convocatorias.update_one(
                {"_id": ObjectId(convocatoria_id)},
                {"$pull": {"reacciones": usuario_id}}
            )
            accion = "removed"
        else:
            # Poner like
            db.convocatorias.update_one(
                {"_id": ObjectId(convocatoria_id)},
                {"$addToSet": {"reacciones": usuario_id}}
            )
            accion = "added"

        # Obtener nuevo conteo
        convocatoria_actualizada = db.convocatorias.find_one({"_id": ObjectId(convocatoria_id)})
        nuevo_conteo = len(convocatoria_actualizada.get("reacciones", []))

        return JsonResponse({
            "status": "success",
             "accion": accion,
             "nuevo_conteo": nuevo_conteo
        })

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


def _bloqueo_por_contrato(request):
    return None


def documentacion_view(request):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login")

    contrato_vigente = _obtener_contrato_vigente()
    vigente_id = contrato_vigente.get("_id") if contrato_vigente else None

    # El contrato es a nivel de EQUIPO: se guarda y consulta con el ID del lÃ­der del proyecto,
    # para que si cualquier integrante lo envÃ­a, todos vean "En revision" y el admin habilite a todos al aceptar.
    contrato_owner_id = str(usuario_id)
    try:
        usuario_obj = db.usuarios.find_one({"_id": ObjectId(str(usuario_id))})
        correo_usuario = (usuario_obj.get("correo") or "").strip().lower() if usuario_obj else ""
        proyecto = db.proyectos.find_one({
            "$or": [
                {"usuario_id": str(usuario_id)},
                {"usuario_lider_id": str(usuario_id)},
                {"resumen.correo": correo_usuario},
                {"integrantes.correo": correo_usuario},
            ]
        }) if correo_usuario else db.proyectos.find_one({
            "$or": [{"usuario_id": str(usuario_id)}, {"usuario_lider_id": str(usuario_id)}]
        })
        if proyecto:
            contrato_owner_id = str(proyecto.get("usuario_lider_id") or proyecto.get("usuario_id") or usuario_id)
    except Exception:
        contrato_owner_id = str(usuario_id)

    estado, ultimo_contrato = get_team_contract_status(usuario_id)
    if estado == "Aceptado":
        return redirect("portal_publico")

    error = None  # Inicializar siempre para evitar UnboundLocalError en GET

    if request.method == "POST":
        accion = (request.POST.get("accion") or "").strip()
        ultimo_contrato = _ultimo_contrato_usuario(contrato_owner_id, vigente_id)

        if not contrato_vigente:
            error = "No hay contrato vigente configurado por administracion."
        elif ultimo_contrato and (ultimo_contrato.get("estado") or "").lower() == "enviado":
            error = "Tu contrato sigue en revision. Espera la respuesta del administrador."
        elif accion == "subir_contrato_editado":
            contrato_editado = request.FILES.get("contrato_editado")
            firmas_raw = request.POST.get("firmas_json") or "[]"
            try:
                firmas_participantes = json.loads(firmas_raw)
            except Exception:
                firmas_participantes = []

            firmas_validas = []
            for firma in firmas_participantes:
                nombre_firmante = (firma.get("nombre") or "").strip()
                rol_firmante = (firma.get("rol") or "").strip()
                firma_img = (firma.get("firma_base64") or "").strip()
                if nombre_firmante and rol_firmante and firma_img:
                    firmas_validas.append({
                        "nombre": nombre_firmante,
                        "rol": rol_firmante,
                        "firma_base64": firma_img
                    })

            if not contrato_editado:
                error = "Debes subir el contrato editado."
            elif not (contrato_editado.name or "").lower().endswith(".pdf"):
                error = "Para anexar firmas en el documento, sube el contrato editado en PDF."
            elif len(firmas_validas) < 1:
                error = "Debes anexar al menos una firma completa."
            else:
                db.contrato_proyecto.insert_one({
                    "usuario_id": contrato_owner_id,
                    "enviado_por_usuario_id": str(usuario_id),
                    "nombre_archivo": contrato_editado.name or "contrato_editado",
                    "tipo_archivo": getattr(contrato_editado, "content_type", "application/octet-stream"),
                    "archivo": contrato_editado.read(),
                    "firma_contrato": "firmas_multiples",
                    "modo_firma": "subido_editado_y_firmado",
                    "firmas_participantes": firmas_validas,
                    "estado": "enviado",
                    "fecha_subida": datetime.now(timezone.utc),
                    "fecha_firma": datetime.now(timezone.utc),
                    "contrato_vigente_id": str(contrato_vigente.get("_id"))
                })
                db.firmas.update_one(
                    {"usuario_id": usuario_id},
                    {"$set": {
                        "firma_contrato": "firmas_multiples",
                        "fecha": datetime.now(timezone.utc)
                    }},
                    upsert=True
                )
                return redirect("documentacion")
        else:
            error = "Accion no valida."

    contrato_vigente_es_pdf = (contrato_vigente.get("tipo_archivo") or "").lower() == "application/pdf" if contrato_vigente else False
    
    # Solo el líder (o el primero que subió) puede ver el formulario, pero todos ven el estado
    # Podríamos refinar esto para que cualquier integrante con permiso suba, pero mantengamos simple por ahora
    # Si ya hay un contrato en ejecución del equipo, no mostramos el formulario a los integrantes
    contrato_pendiente = estado == "En revision"
    contrato_aceptado = estado == "Aceptado"
    mostrar_formularios = not contrato_aceptado and not contrato_pendiente and bool(contrato_vigente)

    return render(request, "documentacion.html", {
        "error": error,
        "contrato_estado": estado,
        "contrato_aceptado": contrato_aceptado,
        "contrato_pendiente": contrato_pendiente,
        "mostrar_formularios": mostrar_formularios,
        "contrato_vigente_es_pdf": contrato_vigente_es_pdf,
        "contrato_vigente": contrato_vigente,
        "contrato_vigente_ver_url": "/usuarios/documentacion/contrato-vigente/ver/",
        "contrato_vigente_descarga_url": "/usuarios/documentacion/contrato-vigente/descargar/",
    })


def ver_contrato_vigente_usuario(request):
    if not request.session.get("usuario_id"):
        return redirect("login")

    contrato = _obtener_contrato_vigente()
    if not contrato or not contrato.get("archivo"):
        raise Http404("No hay contrato vigente disponible.")

    tipo = contrato.get("tipo_archivo") or "application/pdf"
    response = HttpResponse(contrato.get("archivo"), content_type=tipo)
    response["Content-Disposition"] = "inline"
    return response


def descargar_contrato_vigente_usuario(request):
    if not request.session.get("usuario_id"):
        return redirect("login")

    contrato = _obtener_contrato_vigente()
    if not contrato or not contrato.get("archivo"):
        raise Http404("No hay contrato vigente disponible.")

    tipo = contrato.get("tipo_archivo") or "application/octet-stream"
    nombre = contrato.get("nombre_archivo") or "contrato_vigente"
    response = HttpResponse(contrato.get("archivo"), content_type=tipo)
    response["Content-Disposition"] = f'attachment; filename="{nombre}"'
    return response


def ver_contrato_usuario(request, contrato_id):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login")

    try:
        contrato = db.contrato_proyecto.find_one({"_id": ObjectId(contrato_id)})
    except Exception:
        contrato = None

    if not contrato or not contrato.get("archivo"):
        raise Http404("Contrato no encontrado")

    # Permitir ver el contrato si pertenece al equipo del usuario (contrato guardado con el ID del lÃ­der).
    contrato_owner_id = str(contrato.get("usuario_id") or "")
    if contrato_owner_id != str(usuario_id):
        try:
            usuario_obj = db.usuarios.find_one({"_id": ObjectId(str(usuario_id))})
            correo_usuario = (usuario_obj.get("correo") or "").strip().lower() if usuario_obj else ""
            proyecto = db.proyectos.find_one({
                "$or": [
                    {"usuario_id": str(usuario_id)},
                    {"usuario_lider_id": str(usuario_id)},
                    {"resumen.correo": correo_usuario},
                    {"integrantes.correo": correo_usuario}
                ]
            })
            lider_id = str(proyecto.get("usuario_lider_id") or proyecto.get("usuario_id") or usuario_id) if proyecto else str(usuario_id)
            if str(lider_id) != contrato_owner_id:
                raise Http404("Contrato no autorizado")
        except Http404:
            raise
        except Exception:
            raise Http404("Contrato no autorizado")

    tipo = contrato.get("tipo_archivo") or "application/pdf"
    response = HttpResponse(contrato["archivo"], content_type=tipo)
    response["Content-Disposition"] = "inline"
    return response


def expediente_usuario(request):
    bloqueo = _bloqueo_por_contrato(request)
    if bloqueo:
        return bloqueo

    usuario_id = request.session.get("usuario_id")
    correo_sesion = (request.session.get("correo") or "").strip().lower()

    proyecto = _obtener_proyecto_usuario(usuario_id, correo_sesion)
    proyecto_id = str(proyecto.get("_id")) if proyecto else None
    
    error = None
    mensaje_exito = request.GET.get("ok") == "1"

    if request.method == "POST":
        accion = (request.POST.get("accion") or "").strip()
        if accion != "subir_documento_versionado":
            error = "Accion no valida."
        else:
            nombre_documento = (request.POST.get("nombre_documento") or "").strip()
            archivo = request.FILES.get("archivo_documento")

            if not nombre_documento:
                error = "Debes indicar el nombre del documento."
            elif not archivo:
                error = "Debes seleccionar un archivo para subir."
            else:
                documento_clave = _normalizar_documento_clave(nombre_documento)
                # Buscar ultima version pidiendo por proyecto o por usuario_id si no hay proyecto
                query_version = {"documento_clave": documento_clave}
                if proyecto_id:
                    query_version["proyecto_id"] = proyecto_id
                else:
                    query_version["usuario_id"] = usuario_id

                ultima_version = db.expediente_documentos.find_one(
                    query_version,
                    sort=[("version", -1), ("_id", -1)]
                )
                nueva_version = int((ultima_version or {}).get("version") or 0) + 1
                contenido = archivo.read()

                db.expediente_documentos.insert_one({
                    "usuario_id": usuario_id,
                    "proyecto_id": proyecto_id,  # Nuevo campo
                    "nombre_documento": nombre_documento,
                    "documento_clave": documento_clave,
                    "version": nueva_version,
                    "nombre_archivo": archivo.name,
                    "tipo_archivo": getattr(archivo, "content_type", "application/octet-stream"),
                    "archivo": contenido,
                    "tamano_bytes": len(contenido),
                    "fecha_subida": datetime.now(timezone.utc),
                })

                return redirect(f"{reverse('expediente_usuario')}?ok=1")

    # Mostrar el historial basado en proyecto si lo hay, o en el usuario
    if proyecto_id:
        expedientes = _historial_expediente_proyecto(proyecto_id)
    else:
        expedientes = _historial_expediente_usuario(usuario_id)
    total_documentos = len(expedientes)
    total_versiones = sum(item["total_versiones"] for item in expedientes)

    return render(request, "expediente.html", {
        "error": error,
        "mensaje_exito": mensaje_exito,
        "expedientes": expedientes,
        "total_documentos": total_documentos,
        "total_versiones": total_versiones,
    })


def descargar_documento_expediente(request, documento_id):
    bloqueo = _bloqueo_por_contrato(request)
    if bloqueo:
        return bloqueo

    usuario_id = request.session.get("usuario_id")
    try:
        documento = db.expediente_documentos.find_one({
            "_id": ObjectId(documento_id),
            "usuario_id": usuario_id,
        })
    except Exception:
        documento = None

    if not documento or not documento.get("archivo"):
        raise Http404("Documento no encontrado.")

    nombre = documento.get("nombre_archivo") or "documento"
    tipo = documento.get("tipo_archivo") or "application/octet-stream"
    response = HttpResponse(documento.get("archivo"), content_type=tipo)
    response["Content-Disposition"] = f'attachment; filename="{nombre}"'
    return response

def perfil_emprendedor(request):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login")

    bloqueo = _bloqueo_por_contrato(request)
    if bloqueo:
        return bloqueo

    correo_sesion = (request.session.get("correo") or "").strip().lower()
    proyecto = _obtener_proyecto_usuario(usuario_id, correo_sesion)
    estado_meta = _estado_proyecto_meta(proyecto.get("estado") if proyecto else None)
    proyecto_id = str(proyecto.get("_id")) if proyecto and proyecto.get("_id") else None
    etapas, progreso = _etapas_proyecto(usuario_id, proyecto)

    try:
        usuario_obj = db.usuarios.find_one({"_id": ObjectId(usuario_id)})
    except Exception:
        usuario_obj = db.usuarios.find_one({"_id": usuario_id})

    # Normalización de integrantes para el template
    integrantes_lista = []
    if proyecto:
        resumen = proyecto.get("resumen", {})
        integrantes_lista = proyecto.get("integrantes") or resumen.get("integrantes")
        # Si 'equipo' resultó ser una lista (como se ve en el caso del usuario)
        if not integrantes_lista and isinstance(resumen.get("equipo"), list):
            integrantes_lista = resumen.get("equipo")
        if not isinstance(integrantes_lista, list):
            integrantes_lista = []
        
        # Asegurar que cada integrante tenga la llave 'nombre'
        for i in integrantes_lista:
            if isinstance(i, dict):
                if not i.get("nombre") and i.get("nombre_completo"):
                    i["nombre"] = i["nombre_completo"]
        
        # Limpiar el campo equipo si quedó como lista (problema visto en screenshot)
        if isinstance(resumen.get("equipo"), list):
            resumen["equipo"] = f"Equipo de {resumen.get('lider', 'Emprendedor')}"
    
    # Obtener eventos del calendario para el perfil
    ahora_dt = datetime.now(timezone.utc)
    eventos_cursor = db.calendario_eventos.find({
        "fecha": {"$gte": ahora_dt.strftime("%Y-%m-%d")}
    }).sort("fecha", 1).limit(4)
    eventos = list(eventos_cursor)
    for ev in eventos:
        ev["id"] = str(ev["_id"])
        
    from apps.public.views import _obtener_muro_unificado_public
    muro = _obtener_muro_unificado_public(es_visitante=False)
    
    contexto = {
        "proyecto": proyecto,
        "integrantes_lista": integrantes_lista if isinstance(integrantes_lista, list) else [],
        "estado_meta": estado_meta,
        "ultima_actualizacion": _formatear_fecha_corta(proyecto.get("ultima_actualizacion")) if proyecto else None,
        "fecha_baja": _formatear_fecha_corta(proyecto.get("fecha_baja")) if proyecto else None,
        "motivo_baja": proyecto.get("motivo_baja") if proyecto else None,
        "usuario": usuario_obj,
        "proyecto_id": proyecto_id,
        "etapas": etapas,
        "progreso": progreso,
        "eventos": eventos,
        "muro": muro,
    }
    return render(request, "perfil_emprendedor.html", contexto)


def _chat_nombre_sesion(request):
    nombre = (request.session.get("nombre") or "Usuario").strip()
    apellido_paterno = (request.session.get("apellido_paterno") or "").strip()
    apellido_materno = (request.session.get("apellido_materno") or "").strip()
    return " ".join([p for p in [nombre, apellido_paterno, apellido_materno] if p]) or "Usuario"


def _chat_admin_nombre():
    rol_admin = db.roles.find_one({"nombre": {"$regex": "^Administrador$", "$options": "i"}})
    filtro = {}
    if rol_admin:
        filtro["rol_id"] = str(rol_admin["_id"])
    admin = db.usuarios.find_one(filtro) if filtro else db.usuarios.find_one()

    if not admin:
        return "Administrador"

    nombre = (admin.get("nombre") or "Administrador").strip()
    apellido_paterno = (admin.get("apellido_paterno") or "").strip()
    apellido_materno = (admin.get("apellido_materno") or "").strip()
    return " ".join([p for p in [nombre, apellido_paterno, apellido_materno] if p]) or "Administrador"


def chat_usuario(request):
    bloqueo = _bloqueo_por_contrato(request)
    if bloqueo:
        return bloqueo
    
    usuario_id = request.session.get("usuario_id")
    correo = request.session.get("correo")
    proyectos = _obtener_proyectos_usuario(usuario_id, correo)
    
    # Fallback: Si no tiene proyectos listados, intentar obtener/crear uno
    if not proyectos:
        p = _obtener_proyecto_usuario(usuario_id, correo)
        if p:
            p["id"] = str(p["_id"])
            proyectos = [p]
    
    return render(request, "chat_usuario.html", {
        "admin_nombre": _chat_admin_nombre(),
        "proyectos": proyectos
    })


def chat_usuario_mensajes(request):
    if not request.session.get("usuario_id"):
        return JsonResponse({"error": "No autorizado"}, status=403)

    usuario_id = request.session.get("usuario_id")
    proyecto_id = request.GET.get("proyecto_id")
    
    # Si no se pasa proyecto_id, intentamos tomar el primero del usuario
    if not proyecto_id:
        proyectos = _obtener_proyectos_usuario(usuario_id, request.session.get("correo"))
        if proyectos:
            proyecto_id = proyectos[0]["id"]

    filtros = {"proyecto_id": proyecto_id} if proyecto_id else {"usuario_id": usuario_id}
    mensajes = list(db.chat_mensajes.find(filtros).sort("creado_en", 1))
    data = []

    for msg in mensajes:
        fecha = msg.get("creado_en")
        msg_id = str(msg.get("_id"))
        adjunto = msg.get("adjunto") or {}
        es_mio = msg.get("emisor_tipo") == "usuario"
        data.append({
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
            "adjunto_url": f"/usuarios/chat/api/archivo/{msg_id}/" if adjunto.get("file_id") else "",
            "puede_editar": es_mio and not msg.get("eliminado", False),
            "puede_eliminar": es_mio and not msg.get("eliminado", False)
        })

    return JsonResponse({"mensajes": data})


@csrf_exempt
def chat_usuario_enviar(request):
    if not request.session.get("usuario_id"):
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
        proyecto_id = payload.get("proyecto_id")
        archivo = None
    else:
        mensaje = (request.POST.get("mensaje") or "").strip()
        proyecto_id = (request.POST.get("proyecto_id") or "").strip()
        archivo = request.FILES.get("archivo")

    if not mensaje and not archivo:
        return JsonResponse({"error": "Mensaje vacio"}, status=400)

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

    # Asegurar que el mensaje esté vinculado a un proyecto si existe uno
    if not proyecto_id:
        p = _obtener_proyecto_usuario(request.session.get("usuario_id"), request.session.get("correo"))
        if p:
            proyecto_id = str(p.get("_id"))

    db.chat_mensajes.insert_one({
        "proyecto_id": proyecto_id,
        "usuario_id": request.session.get("usuario_id"),
        "usuario_nombre": _chat_nombre_sesion(request),
        "emisor_tipo": "usuario",
        "emisor_id": request.session.get("usuario_id"),
        "emisor_nombre": _chat_nombre_sesion(request),
        "mensaje": mensaje,
        "adjunto": adjunto,
        "creado_en": datetime.now(timezone.utc)
    })

    return JsonResponse({"success": True})


@csrf_exempt
def chat_usuario_editar(request, mensaje_id):
    if not request.session.get("usuario_id"):
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
        {
            "_id": msg_id,
            "emisor_tipo": "usuario",
            "emisor_id": request.session.get("usuario_id")
        },
        {"$set": {"mensaje": nuevo_texto, "editado": True, "fecha_edicion": datetime.now(timezone.utc)}}
    )
    if resultado.matched_count == 0:
        return JsonResponse({"error": "No se puede editar este mensaje"}, status=403)

    return JsonResponse({"success": True})


@csrf_exempt
def chat_usuario_eliminar(request, mensaje_id):
    if not request.session.get("usuario_id"):
        return JsonResponse({"error": "No autorizado"}, status=403)
    if request.method != "POST":
        return JsonResponse({"error": "Metodo no permitido"}, status=405)

    try:
        msg_id = ObjectId(mensaje_id)
    except Exception:
        return JsonResponse({"error": "Mensaje invalido"}, status=400)

    msg = db.chat_mensajes.find_one(
        {
            "_id": msg_id,
            "emisor_tipo": "usuario",
            "emisor_id": request.session.get("usuario_id")
        }
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


def chat_usuario_archivo(request, mensaje_id):
    if not request.session.get("usuario_id"):
        return JsonResponse({"error": "No autorizado"}, status=403)

    try:
        msg_id = ObjectId(mensaje_id)
    except Exception:
        return JsonResponse({"error": "Mensaje invalido"}, status=400)

    mensaje = db.chat_mensajes.find_one({
        "_id": msg_id,
        "usuario_id": request.session.get("usuario_id")
    })
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

@csrf_exempt
def agregar_comentario_convocatoria(request):
    """
    Permite a los emprendedores agregar comentarios a una convocatoria.
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

    usuario_id = request.session.get("usuario_id")
    rol = request.session.get("rol")
    if not usuario_id or rol != "Emprendedor":
        return JsonResponse({"status": "error", "message": "Solo los emprendedores pueden comentar"}, status=403)

    nombre_usuario = f"{request.session.get('nombre', '')} {request.session.get('apellido_paterno', '')}".strip() or "Usuario"

    try:
        data = json.loads(request.body)
        convocatoria_id = data.get("convocatoria_id")
        texto = data.get("texto", "").strip()
    except Exception:
        return JsonResponse({"status": "error", "message": "Datos inválidos"}, status=400)

    if not convocatoria_id or not texto:
        return JsonResponse({"status": "error", "message": "Faltan datos"}, status=400)

    nuevo_comentario = {
        "usuario_id": usuario_id,
        "nombre": nombre_usuario,
        "texto": texto,
        "fecha": datetime.now(timezone.utc)
    }

    try:
        db.convocatorias.update_one(
            {"_id": ObjectId(convocatoria_id)},
            {"$push": {"comentarios": nuevo_comentario}}
        )
        return JsonResponse({
            "status": "success",
            "comentario": {
                "nombre": nombre_usuario,
                "texto": texto,
                "fecha": "Justo ahora"
            }
        })
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@csrf_exempt
def cambiar_contrasena_perfil(request):
    """
    Permite al usuario logueado cambiar su propia contraseña.
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return JsonResponse({"status": "error", "message": "No autorizado"}, status=403)

    try:
        data = json.loads(request.body)
        nueva_pass = (data.get("password") or "").strip()
        confirm_pass = (data.get("confirm_password") or "").strip()
    except Exception:
        return JsonResponse({"status": "error", "message": "Datos inválidos"}, status=400)

    if not nueva_pass or len(nueva_pass) < 8:
        return JsonResponse({"status": "error", "message": "La contraseña debe tener al menos 8 caracteres"}, status=400)
    
    if nueva_pass != confirm_pass:
        return JsonResponse({"status": "error", "message": "Las contraseñas no coinciden"}, status=400)

    try:
        db.usuarios.update_one(
            {"_id": ObjectId(usuario_id)},
            {"$set": {"contrasena": nueva_pass}}
        )
        return JsonResponse({"status": "success", "message": "Contraseña actualizada correctamente"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
