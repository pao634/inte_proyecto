from pymongo import MongoClient
from bson import ObjectId

MONGO_URI = "mongodb+srv://milton_user:Mongo123456@incubadoradeproyectoemp.ptri94g.mongodb.net/?retryWrites=true&w=majority"

def check_roles():
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
        db = client["milton_user"]
        
        # Check roles
        roles = list(db.roles.find())
        print("--- Roles in DB ---")
        for r in roles:
            print(f"ID: {r['_id']} ({type(r['_id'])}) | Nombre: {r.get('nombre')}")
            
        # Target user's role
        target_role_id_str = "699eb18f8a2f8c9f2f85cc98"
        role_by_objid = db.roles.find_one({"_id": ObjectId(target_role_id_str)})
        role_by_str = db.roles.find_one({"_id": target_role_id_str})
        
        print(f"\nSearching for {target_role_id_str}:")
        print(f"By ObjectId: {'Found' if role_by_objid else 'NOT Found'}")
        print(f"By String: {'Found' if role_by_str else 'NOT Found'}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_roles()
