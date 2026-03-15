from pymongo import MongoClient

MONGO_URI = "mongodb+srv://milton_user:Mongo123456@incubadoradeproyectoemp.ptri94g.mongodb.net/?retryWrites=true&w=majority"

def check_user_types():
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
        db = client["milton_user"]
        user = db.usuarios.find_one({"correo": "202304042@utacapulco.edu.mx"})
        
        if user:
            print(f"User: {user['correo']}")
            print(f"rol_id: {user['rol_id']} ({type(user['rol_id'])})")
            print(f"contrasena: '{user['contrasena']}' ({type(user['contrasena'])})")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_user_types()
