from fastapi import APIRouter, HTTPException
from models.database import mongodb
from models.schemas import AnalyticsResponse
from datetime import datetime, timedelta
from bson import ObjectId
import json

router = APIRouter(prefix="/analytics", tags=["Analytics"])

# Helper function para convertir ObjectId a string
def convertir_objectid(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, list):
        return [convertir_objectid(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convertir_objectid(value) for key, value in obj.items()}
    return obj

@router.get("/resumen-mensual", response_model=AnalyticsResponse)
async def get_resumen_mensual():
    try:
        collections = mongodb.get_collections()
        
        # Ingresos por tipo de servicio
        pipeline_ingresos = [
            {
                "$group": {
                    "_id": "$tipo_servicio",
                    "total_ingresos": {"$sum": "$ingresos"},
                    "total_servicios": {"$sum": "$cantidad"}
                }
            }
        ]
        ingresos_por_tipo = list(collections["servicios"].aggregate(pipeline_ingresos))
        
        # Servicios por día
        pipeline_servicios_dia = [
            {
                "$group": {
                    "_id": {"fecha": "$fecha", "dia_semana": "$dia_semana"},
                    "servicios_atendidos": {"$sum": "$servicios_atendidos"},
                    "ingresos_totales": {"$sum": "$ingresos_totales"}
                }
            },
            {"$sort": {"_id.fecha": 1}}
        ]
        servicios_por_dia = list(collections["dias_operacion"].aggregate(pipeline_servicios_dia))
        
        # Ganancias totales
        pipeline_ganancias = [
            {
                "$group": {
                    "_id": None,
                    "ganancias_totales": {"$sum": "$ganancia_neta"},
                    "promedio_servicios": {"$avg": "$servicios_atendidos"}
                }
            }
        ]
        ganancias_totales = list(collections["dias_operacion"].aggregate(pipeline_ganancias))
        
        # Convertir ObjectId a string
        ingresos_por_tipo = convertir_objectid(ingresos_por_tipo)
        servicios_por_dia = convertir_objectid(servicios_por_dia)
        ganancias_totales = convertir_objectid(ganancias_totales)
        
        return AnalyticsResponse(
            ingresos_por_tipo={item["_id"]: item["total_ingresos"] for item in ingresos_por_tipo},
            servicios_por_dia=servicios_por_dia,
            ganancias_totales=ganancias_totales[0]["ganancias_totales"] if ganancias_totales else 0,
            promedio_servicios_dia=ganancias_totales[0]["promedio_servicios"] if ganancias_totales else 0
        )
        
    except Exception as e:
        raise HTTPException(500, f"Error obteniendo analytics: {str(e)}")

@router.get("/servicios-por-fecha")
async def get_servicios_por_fecha(fecha_inicio: str, fecha_fin: str):
    try:
        collections = mongodb.get_collections()
        
        pipeline = [
            {
                "$match": {
                    "fecha": {
                        "$gte": datetime.fromisoformat(fecha_inicio),
                        "$lte": datetime.fromisoformat(fecha_fin)
                    }
                }
            },
            {
                "$group": {
                    "_id": "$fecha",
                    "total_servicios": {"$sum": "$servicios_atendidos"},
                    "ingresos_totales": {"$sum": "$ingresos_totales"},
                    "ganancia_neta": {"$sum": "$ganancia_neta"}
                }
            },
            {"$sort": {"_id": 1}}
        ]
        
        resultados = list(collections["dias_operacion"].aggregate(pipeline))
        
        # Convertir ObjectId a string
        resultados = convertir_objectid(resultados)
        
        return resultados
        
    except Exception as e:
        raise HTTPException(500, f"Error obteniendo datos por fecha: {str(e)}")

@router.get("/top-dias")
async def get_top_dias(limit: int = 5):
    try:
        collections = mongodb.get_collections()
        
        pipeline = [
            {"$match": {"estado": "abierto"}},
            {"$sort": {"ingresos_totales": -1}},
            {"$limit": limit},
            {
                "$project": {
                    "_id": 0,  # Excluir el _id de MongoDB
                    "fecha": 1,
                    "dia_semana": 1,
                    "servicios_atendidos": 1,
                    "ingresos_totales": 1,
                    "ganancia_neta": 1
                }
            }
        ]
        
        resultados = list(collections["dias_operacion"].aggregate(pipeline))
        
        # Convertir ObjectId a string (aunque excluimos _id, por si hay otros campos)
        resultados = convertir_objectid(resultados)
        
        return resultados
        
    except Exception as e:
        raise HTTPException(500, f"Error obteniendo top días: {str(e)}")