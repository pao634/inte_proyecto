from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = "mongodb+srv://milton_user:Mongo123456@incubadoradeproyectoemp.ptri94g.mongodb.net/?retryWrites=true&w=majority"

def list_all():
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        
        # List all databases
        dbs = client.list_database_names()
        print(f"📁 Bases de datos en el cluster: {dbs}")
        
        for db_name in dbs:
            if db_name in ['admin', 'local', 'config']:
                continue
            db = client[db_name]
            collections = db.list_collection_names()
            print(f"📍 Database: {db_name} -> Colecciones: {collections}")
            
    except Exception as e:
        print(f"💥 Error: {e}")

if __name__ == "__main__":
    list_all()
