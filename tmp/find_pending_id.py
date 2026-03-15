import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client['milton_user']

# Search in solicitudes
solicitud = db.solicitudes.find_one({"estado": {"$regex": "^en proceso$", "$options": "i"}})
if solicitud:
    print(f"Found solicitud: {solicitud['_id']}")
else:
    print("No pending solicitudes found.")
client.close()
