from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

class MongoDB:
    def __init__(self):
        self.client = None
        self.db = None
        self.connect()
    
    def connect(self):
        try:
            self.client = MongoClient(os.getenv("MONGODB_URI"))
            self.db = self.client[os.getenv("DATABASE_NAME")]
            print("✅ Conectado a MongoDB Atlas")
        except Exception as e:
            print(f"❌ Error conectando a MongoDB: {e}")
    
    def get_collections(self):
        return {
            "dias_operacion": self.db.dias_operacion,
            "servicios": self.db.servicios,
            "costos": self.db.costos
        }

# Instancia global de la base de datos
mongodb = MongoDB()