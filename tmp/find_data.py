from pymongo import MongoClient

# Use the full URI provided by user
MONGO_URI = "mongodb+srv://milton_user:Mongo123456@incubadoradeproyectoemp.ptri94g.mongodb.net/?retryWrites=true&w=majority"

def find_users():
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
        dbs = client.list_database_names()
        print(f"Total DBs: {len(dbs)}")
        print(f"DB List: {dbs}")
        
        for db_name in dbs:
            if db_name in ['admin', 'local', 'config']:
                continue
            db = client[db_name]
            cols = db.list_collection_names()
            print(f"-- DB: {db_name} --")
            print(f"   Cols: {cols}")
            if "usuarios" in cols:
                count = db.usuarios.count_documents({})
                print(f"   🎯 ENCONTRADO! Collection 'usuarios' with {count} documents.")
                
                # Check for the specific user
                target = "202304042@utacapulco.edu.mx"
                user = db.usuarios.find_one({"correo": target})
                if user:
                    print(f"   ✅ Usuario {target} existe aquí!")
                else:
                    print(f"   ❌ Usuario {target} NO existe aquí.")
            print("-" * 30)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_users()
