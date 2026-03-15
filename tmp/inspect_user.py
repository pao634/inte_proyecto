from pymongo import MongoClient

MONGO_URI = "mongodb+srv://milton_user:Mongo123456@incubadoradeproyectoemp.ptri94g.mongodb.net/?retryWrites=true&w=majority"

def inspect_user():
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
        db = client["milton_user"]
        user = db.usuarios.find_one({"correo": "202304042@utacapulco.edu.mx"})
        
        if user:
            # We print everything except sensitive stuff if needed, but here we need to see the password to compare
            print("--- User Info ---")
            for k, v in user.items():
                print(f"{k}: {v}")
        else:
            print("User not found in milton_user.usuarios")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_user()
