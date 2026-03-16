from pymongo import MongoClient
import gridfs
import os
from dotenv import load_dotenv
import base64

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "milton_user")


class MongoDB:
    """
    Conexion lazy a MongoDB.

    Evita resolver DNS / conectar en import-time (manage.py check, collectstatic, etc.),
    algo importante en despliegues como Render.
    """

    def __init__(self, uri=MONGO_URI, db_name=MONGO_DB_NAME):
        self._uri = uri
        self._db_name = db_name
        self._client = None
        self._db = None
        self._fs = None

    def connect(self):
        if self._db is not None:
            return self._db

        if not self._uri:
            raise RuntimeError("MONGO_URI no esta configurado.")

        self._client = MongoClient(self._uri, serverSelectionTimeoutMS=5000)
        self._client.admin.command("ping")
        self._db = self._client[self._db_name]
        self._fs = gridfs.GridFS(self._db)
        return self._db

    @property
    def db(self):
        return self.connect()

    @property
    def fs(self):
        self.connect()
        return self._fs

    def subir_imagen(self, ruta_archivo):
        if not os.path.exists(ruta_archivo):
            print(f"No se encontro el archivo {ruta_archivo}")
            return None
        with open(ruta_archivo, "rb") as f:
            file_id = self.fs.put(f, filename=os.path.basename(ruta_archivo))
        print(f"Imagen subida a MongoDB con id: {file_id}")
        return file_id

    def subir_imagen_file(self, archivo):
        try:
            file_id = self.fs.put(
                archivo.read(),
                filename=archivo.name,
                content_type=getattr(archivo, "content_type", "application/octet-stream"),
            )
            print(f"Imagen subida correctamente con id: {file_id}")
            return file_id
        except Exception as e:
            print(f"Error al subir imagen desde formulario: {e}")
            return None

    def obtener_imagen_base64(self, file_id):
        try:
            archivo = self.fs.get(file_id)
            imagen_bytes = archivo.read()
            return base64.b64encode(imagen_bytes).decode()
        except Exception as e:
            print(f"Error al recuperar imagen: {e}")
            return None


class _LazyDBProxy:
    def __init__(self, mongo: MongoDB):
        self._mongo = mongo

    def __getattr__(self, name):
        return getattr(self._mongo.db, name)

    def __getitem__(self, key):
        return self._mongo.db[key]

    def __repr__(self):
        return "<LazyMongoDBProxy>"


mongo_instance = MongoDB()
db = _LazyDBProxy(mongo_instance)

