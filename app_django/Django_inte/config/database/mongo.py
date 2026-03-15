from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import gridfs
import os
from dotenv import load_dotenv
import base64

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

class MongoDB:
    def __init__(self):
        try:
            self.client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            self.client.admin.command("ping")
            self.db = self.client["milton_user"]
            self.fs = gridfs.GridFS(self.db)
            print("Conexión a MongoDB exitosa")
        except ConnectionFailure as e:
            print("Error de conexión a MongoDB")
            raise e

    # Subir archivo desde disco (opcional)
    def subir_imagen(self, ruta_archivo):
        if not os.path.exists(ruta_archivo):
            print(f"No se encontró el archivo {ruta_archivo}")
            return None
        with open(ruta_archivo, "rb") as f:
            file_id = self.fs.put(f, filename=os.path.basename(ruta_archivo))
        print(f"Imagen subida a MongoDB con id: {file_id}")
        return file_id

    # NUEVO: Subir archivo desde formulario Django
    def subir_imagen_file(self, archivo):
        try:
            file_id = self.fs.put(
                archivo.read(),
                filename=archivo.name,
                content_type=getattr(archivo, "content_type", "application/octet-stream")
            )
            print(f"Imagen subida correctamente con id: {file_id}")
            return file_id
        except Exception as e:
            print(f"Error al subir imagen desde formulario: {e}")
            return None

    # Obtener imagen en base64
    def obtener_imagen_base64(self, file_id):
        try:
            archivo = self.fs.get(file_id)
            imagen_bytes = archivo.read()
            return base64.b64encode(imagen_bytes).decode()
        except Exception as e:
            print(f"Error al recuperar imagen: {e}")
            return None

# Instancia para usar en views
mongo_instance = MongoDB()
db = mongo_instance.db
