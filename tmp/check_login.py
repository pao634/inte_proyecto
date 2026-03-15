from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# We use the provided URI but target the correct DB
MONGO_URI = "mongodb+srv://milton_user:Mongo123456@incubadoradeproyectoemp.ptri94g.mongodb.net/milton_usuario?retryWrites=true&w=majority"

def diagnose():
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client["milton_usuario"]
        
        # Check connection
        client.admin.command('ping')
        print("✅ Conexión a MongoDB exitosa")
        
        # Check collections
        collections = db.list_collection_names()
        print(f"📁 Colecciones encontradas: {collections}")
        
        if "usuarios" not in collections:
            print("❌ La colección 'usuarios' NO existe en 'milton_usuario'")
            return

        # Check for the specific user
        target_email = "202304042@utacapulco.edu.mx"
        user = db.usuarios.find_one({"correo": target_email})
        
        if user:
            print(f"👤 Usuario encontrado: {user.get('nombre')} {user.get('apellido_paterno')}")
            print(f"🔑 Password en BD: '{user.get('contrasena')}'")
            print(f"🔓 Activo: {user.get('activo')}")
            print(f"🛡️ Rol ID: {user.get('rol_id')}")
            
            # Compare passwords (plain text check as per user's earlier snippet)
            provided_pass = "Jose1708$"
            if str(user.get('contrasena')).strip() == provided_pass:
                print("✅ La contraseña COINCIDE")
            else:
                print(f"❌ La contraseña NO coincide (BD tiene '{user.get('contrasena')}' vs Proporcionada '{provided_pass}')")
        else:
            print(f"❌ No se encontró ningún usuario con el correo: {target_email}")
            
    except Exception as e:
        print(f"💥 Error durante el diagnóstico: {e}")

if __name__ == "__main__":
    diagnose()
