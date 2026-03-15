from pymongo import MongoClient

MONGO_URI = "mongodb+srv://milton_user:Mongo123456@incubadoradeproyectoemp.ptri94g.mongodb.net/?retryWrites=true&w=majority"

def find_users():
    results = []
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
        dbs = client.list_database_names()
        results.append(f"Total DBs: {len(dbs)}")
        results.append(f"DB List: {dbs}")
        
        for db_name in dbs:
            if db_name in ['admin', 'local', 'config']:
                continue
            db = client[db_name]
            cols = db.list_collection_names()
            results.append(f"-- DB: {db_name} --")
            results.append(f"   Cols: {cols}")
            if "usuarios" in cols:
                count = db.usuarios.count_documents({})
                results.append(f"   🎯 ENCONTRADO! Collection 'usuarios' with {count} documents.")
                
                # Check for the specific user
                target = "202304042@utacapulco.edu.mx"
                user = db.usuarios.find_one({"correo": target})
                if user:
                    results.append(f"   ✅ Usuario {target} existe aquí!")
                else:
                    results.append(f"   ❌ Usuario {target} NO existe aquí.")
            results.append("-" * 30)
            
    except Exception as e:
        results.append(f"Error: {e}")
    
    with open("tmp/scan_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(results))

if __name__ == "__main__":
    find_users()
