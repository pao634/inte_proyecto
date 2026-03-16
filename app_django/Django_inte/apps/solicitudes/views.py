from django.shortcuts import render
from django.http import JsonResponse
from datetime import datetime
import json 
from config.database.mongo import db 

def solicitud_ingreso_view(request):
    if request.method == "POST":
        try:
            # Intentamos obtener los datos sin romper el flujo de Django
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST.dict()

            # Validación de campos
            if not data.get("correo") or not data.get("nombre_completo"):
                return JsonResponse({"error": "Faltan campos obligatorios"}, status=400)

            # Preparar datos para MongoDB
            data["estado"] = "EN PROCESO"
            data["fecha_creacion"] = datetime.now()

            # 1. Guardar en MongoDB
            db.solicitudes.insert_one(data)

            # 2. Enviar Correo (Asíncrono para no bloquear)
            try:
                from apps.utils.email_service import enviar_correo_async
                enviar_correo_async(data["correo"], data)
            except Exception as mail_error:
                print(f"Error al enviar correo: {mail_error}")

            return JsonResponse({"message": "Registro exitoso y correo enviado"}, status=201)
        
        except Exception as e:
            print(f"Error general: {e}")
            return JsonResponse({"error": str(e)}, status=500)

    return render(request, "solicitudes/solicitud_ingreso.html")