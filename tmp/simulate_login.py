import os
import sys

# Add the project root to sys.path so we can import apps
sys.path.append(os.path.join(os.getcwd(), 'app_django', 'Django_inte'))

from config.database.mongo import db
from bson import ObjectId

def simulate_login():
    correo = "202304042@utacapulco.edu.mx"
    contrasena = "Jose1708$"
    
    print(f"Simulando login para: {correo}")
    
    usuario = db.usuarios.find_one({
        "correo": correo,
        "contrasena": contrasena,
        "activo": True
    })
    
    if not usuario:
        print("❌ Login fallido: Usuario no encontrado o contraseña incorrecta")
        return
    
    print(f"✅ Usuario encontrado: {usuario.get('nombre')}")
    
    try:
        rol_id = usuario.get("rol_id")
        print(f"Buscando rol con id: {rol_id} (tipo {type(rol_id)})")
        
        rol = db.roles.find_one({"_id": ObjectId(rol_id)})
        if not rol:
            print("❌ Error: Rol no encontrado en la base de datos")
        else:
            print(f"✅ Rol encontrado: {rol.get('nombre')}")
            print("--- ACCESO CONCEDIDO ---")
            
    except Exception as e:
        print(f"💥 Error durante la simulación: {e}")

if __name__ == "__main__":
    simulate_login()
