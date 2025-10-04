from fastapi import APIRouter, HTTPException, Query
from models.database import mongodb
from datetime import datetime, timedelta
from typing import Optional, List
import math

router = APIRouter(prefix="/api", tags=["Dashboard"])

# Helper function para calcular cambios porcentuales
def calcular_cambio_porcentual(actual, anterior):
    if anterior == 0:
        return 0
    return ((actual - anterior) / anterior) * 100

# Helper function para formatear respuesta
def formato_respuesta(data):
    return {"success": True, "data": data, "error": None}

@router.get("/dashboard/overview")
async def get_dashboard_overview():
    try:
        collections = mongodb.get_collections()
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        inicio_semana = hoy - timedelta(days=hoy.weekday())
        inicio_mes = hoy.replace(day=1)
        
        # Datos de hoy
        pipeline_hoy = [
            {"$match": {"fecha": hoy}},
            {"$group": {
                "_id": None,
                "ingresos": {"$sum": "$ingresos_totales"},
                "clientes": {"$sum": "$servicios_atendidos"}
            }}
        ]
        resultado_hoy = list(collections["dias_operacion"].aggregate(pipeline_hoy))
        ingresos_hoy = resultado_hoy[0]["ingresos"] if resultado_hoy else 0
        clientes_hoy = resultado_hoy[0]["clientes"] if resultado_hoy else 0
        
        # Datos de la semana
        pipeline_semana = [
            {"$match": {"fecha": {"$gte": inicio_semana, "$lte": hoy}}},
            {"$group": {
                "_id": None,
                "ingresos": {"$sum": "$ingresos_totales"},
                "clientes": {"$sum": "$servicios_atendidos"}
            }}
        ]
        resultado_semana = list(collections["dias_operacion"].aggregate(pipeline_semana))
        ingresos_semana = resultado_semana[0]["ingresos"] if resultado_semana else 0
        clientes_semana = resultado_semana[0]["clientes"] if resultado_semana else 0
        
        # Datos del mes
        pipeline_mes = [
            {"$match": {"fecha": {"$gte": inicio_mes, "$lte": hoy}}},
            {"$group": {
                "_id": None,
                "ingresos": {"$sum": "$ingresos_totales"},
                "clientes": {"$sum": "$servicios_atendidos"}
            }}
        ]
        resultado_mes = list(collections["dias_operacion"].aggregate(pipeline_mes))
        ingresos_mes = resultado_mes[0]["ingresos"] if resultado_mes else 0
        clientes_mes = resultado_mes[0]["clientes"] if resultado_mes else 0
        
        # Ticket promedio
        ticket_promedio = ingresos_semana / clientes_semana if clientes_semana > 0 else 0
        
        # Datos del período anterior para comparación
        semana_anterior_inicio = inicio_semana - timedelta(days=7)
        semana_anterior_fin = inicio_semana - timedelta(days=1)
        
        pipeline_semana_anterior = [
            {"$match": {"fecha": {"$gte": semana_anterior_inicio, "$lte": semana_anterior_fin}}},
            {"$group": {
                "_id": None,
                "ingresos": {"$sum": "$ingresos_totales"},
                "clientes": {"$sum": "$servicios_atendidos"}
            }}
        ]
        resultado_semana_anterior = list(collections["dias_operacion"].aggregate(pipeline_semana_anterior))
        ingresos_semana_anterior = resultado_semana_anterior[0]["ingresos"] if resultado_semana_anterior else 0
        clientes_semana_anterior = resultado_semana_anterior[0]["clientes"] if resultado_semana_anterior else 0
        ticket_semana_anterior = ingresos_semana_anterior / clientes_semana_anterior if clientes_semana_anterior > 0 else 0
        
        # Cálculo de cambios porcentuales
        cambio_ingresos = calcular_cambio_porcentual(ingresos_semana, ingresos_semana_anterior)
        cambio_clientes = calcular_cambio_porcentual(clientes_semana, clientes_semana_anterior)
        cambio_ticket = calcular_cambio_porcentual(ticket_promedio, ticket_semana_anterior)
        
        data = {
            "ingresos_hoy": ingresos_hoy,
            "ingresos_semana": ingresos_semana,
            "ingresos_mes": ingresos_mes,
            "clientes_hoy": clientes_hoy,
            "clientes_semana": clientes_semana,
            "clientes_mes": clientes_mes,
            "ticket_promedio": round(ticket_promedio, 2),
            "cambio_porcentual_ingresos": round(cambio_ingresos, 2),
            "cambio_porcentual_clientes": round(cambio_clientes, 2),
            "cambio_porcentual_ticket": round(cambio_ticket, 2)
        }
        
        return formato_respuesta(data)
        
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}

@router.get("/dashboard/revenue-weekly")
async def get_revenue_weekly(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None)
):
    try:
        collections = mongodb.get_collections()
        
        # Si no se proporcionan fechas, usar última semana
        if not fecha_inicio or not fecha_fin:
            hoy = datetime.now()
            fecha_fin = hoy.strftime("%Y-%m-%d")
            fecha_inicio = (hoy - timedelta(days=6)).strftime("%Y-%m-%d")
        
        pipeline = [
            {"$match": {
                "fecha": {
                    "$gte": datetime.fromisoformat(fecha_inicio),
                    "$lte": datetime.fromisoformat(fecha_fin)
                }
            }},
            {"$project": {
                "name": {"$substr": ["$dia_semana", 0, 3]},
                "ingresos": "$ingresos_totales",
                "fecha": 1
            }},
            {"$sort": {"fecha": 1}}
        ]
        
        resultados = list(collections["dias_operacion"].aggregate(pipeline))
        
        # Formatear resultados
        data = [{"name": item["name"], "ingresos": item["ingresos"]} for item in resultados]
        
        return formato_respuesta(data)
        
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}

@router.get("/dashboard/services-popular")
async def get_services_popular(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None)
):
    try:
        collections = mongodb.get_collections()
        
        # Si no se proporcionan fechas, usar última semana
        if not fecha_inicio or not fecha_fin:
            hoy = datetime.now()
            fecha_fin = hoy.strftime("%Y-%m-%d")
            fecha_inicio = (hoy - timedelta(days=7)).strftime("%Y-%m-%d")
        
        pipeline = [
            {"$match": {
                "fecha": {
                    "$gte": datetime.fromisoformat(fecha_inicio),
                    "$lte": datetime.fromisoformat(fecha_fin)
                }
            }},
            {"$group": {
                "_id": "$tipo_servicio",
                "cantidad": {"$sum": "$cantidad"},
                "ingresos": {"$sum": "$ingresos"}
            }},
            {"$sort": {"cantidad": -1}}
        ]
        
        resultados = list(collections["servicios"].aggregate(pipeline))
        
        data = []
        for item in resultados:
            data.append({
                "name": item["_id"].replace("_", " ").title(),
                "cantidad": item["cantidad"],
                "ingresos": item["ingresos"]
            })
        
        return formato_respuesta(data)
        
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}

@router.get("/dashboard/alerts")
async def get_alerts():
    try:
        collections = mongodb.get_collections()
        hoy = datetime.now()
        
        # Alertas basadas en análisis de datos
        alertas = []
        
        # Verificar días con baja actividad
        pipeline_baja_actividad = [
            {"$match": {
                "fecha": {"$gte": hoy - timedelta(days=7)},
                "servicios_atendidos": {"$lt": 5}
            }},
            {"$project": {
                "fecha": 1,
                "dia_semana": 1,
                "servicios_atendidos": 1
            }}
        ]
        
        dias_baja = list(collections["dias_operacion"].aggregate(pipeline_baja_actividad))
        
        for dia in dias_baja:
            alertas.append({
                "id": f"baja_{dia['fecha'].strftime('%Y%m%d')}",
                "tipo": "warning",
                "titulo": f"Baja actividad el {dia['dia_semana']}",
                "descripcion": f"Solo {dia['servicios_atendidos']} servicios atendidos",
                "fecha": dia["fecha"]
            })
        
        # Alertas de éxito (días con alta actividad)
        pipeline_alta_actividad = [
            {"$match": {
                "fecha": {"$gte": hoy - timedelta(days=7)},
                "servicios_atendidos": {"$gt": 15}
            }},
            {"$project": {
                "fecha": 1,
                "dia_semana": 1,
                "servicios_atendidos": 1
            }}
        ]
        
        dias_alta = list(collections["dias_operacion"].aggregate(pipeline_alta_actividad))
        
        for dia in dias_alta:
            alertas.append({
                "id": f"alta_{dia['fecha'].strftime('%Y%m%d')}",
                "tipo": "success",
                "titulo": f"Alta actividad el {dia['dia_semana']}",
                "descripcion": f"Excelente: {dia['servicios_atendidos']} servicios atendidos",
                "fecha": dia["fecha"]
            })
        
        # Ordenar por fecha más reciente
        alertas.sort(key=lambda x: x["fecha"], reverse=True)
        
        return formato_respuesta(alertas[:10])  # Solo últimas 10 alertas
        
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}

@router.get("/clientes/distribucion")
async def get_clientes_distribucion():
    try:
        # Simulación de datos de clientes (en un sistema real, esto vendría de una colección de clientes)
        data = {
            "nuevos": 35,  # 35% clientes nuevos
            "recurrentes": 65  # 65% clientes recurrentes
        }
        
        return formato_respuesta(data)
        
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}

@router.get("/clientes/satisfaccion")
async def get_clientes_satisfaccion():
    try:
        # Simulación de datos de satisfacción (en un sistema real, esto vendría de reseñas)
        data = [
            {"rating": "5★", "cantidad": 45},
            {"rating": "4★", "cantidad": 30},
            {"rating": "3★", "cantidad": 15},
            {"rating": "2★", "cantidad": 7},
            {"rating": "1★", "cantidad": 3}
        ]
        
        return formato_respuesta(data)
        
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}

@router.get("/servicios/evolucion-trimestral")
async def get_evolucion_trimestral():
    try:
        collections = mongodb.get_collections()
        
        pipeline = [
            {"$group": {
                "_id": {
                    "servicio": "$tipo_servicio",
                    "mes": {"$month": "$fecha"}
                },
                "cantidad": {"$sum": "$cantidad"},
                "ingresos": {"$sum": "$ingresos"}
            }},
            {"$sort": {"_id.mes": 1}}
        ]
        
        resultados = list(collections["servicios"].aggregate(pipeline))
        
        # Estructurar datos por servicio y mes
        servicios_data = {}
        for item in resultados:
            servicio = item["_id"]["servicio"]
            mes = item["_id"]["mes"]
            cantidad = item["cantidad"]
            
            if servicio not in servicios_data:
                servicios_data[servicio] = {
                    "servicio": servicio.replace("_", " ").title(),
                    "enero": 0, "febrero": 0, "marzo": 0,
                    "precio": 15000 if "normal" in servicio else 25000 if "premium" in servicio else 35000
                }
            
            # Mapear números de mes a nombres
            meses_map = {1: "enero", 2: "febrero", 3: "marzo"}
            if mes in meses_map:
                servicios_data[servicio][meses_map[mes]] = cantidad
        
        data = list(servicios_data.values())
        
        return formato_respuesta(data)
        
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}

@router.get("/servicios/demanda-horaria")
async def get_demanda_horaria():
    try:
        # Simulación de datos de demanda horaria (en un sistema real, esto necesitaría datos por hora)
        horas = [f"{h}:00" for h in range(8, 20)]
        demanda = [5, 8, 12, 15, 18, 22, 25, 28, 30, 25, 20, 15]
        
        data = [{"hora": hora, "servicios": servicios} for hora, servicios in zip(horas, demanda)]
        
        return formato_respuesta(data)
        
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}

@router.get("/finanzas/mensual")
async def get_finanzas_mensual():
    try:
        collections = mongodb.get_collections()
        
        pipeline = [
            {"$group": {
                "_id": {
                    "año": {"$year": "$fecha"},
                    "mes": {"$month": "$fecha"}
                },
                "ingresos": {"$sum": "$ingresos_totales"},
                "gastos": {"$sum": "$costos_totales"},
                "utilidad": {"$sum": "$ganancia_neta"}
            }},
            {"$sort": {"_id.año": 1, "_id.mes": 1}},
            {"$limit": 6}
        ]
        
        resultados = list(collections["dias_operacion"].aggregate(pipeline))
        
        meses_map = {
            1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
            7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"
        }
        
        data = []
        for item in resultados:
            data.append({
                "mes": meses_map[item["_id"]["mes"]],
                "ingresos": item["ingresos"],
                "gastos": item["gastos"],
                "utilidad": item["utilidad"]
            })
        
        return formato_respuesta(data)
        
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}

@router.get("/finanzas/gastos-distribucion")
async def get_gastos_distribucion():
    try:
        collections = mongodb.get_collections()
        
        pipeline = [
            {"$match": {"monto": {"$gt": 0}}},
            {"$group": {
                "_id": "$tipo_costo",
                "total": {"$sum": "$monto"}
            }}
        ]
        
        resultados = list(collections["costos"].aggregate(pipeline))
        
        # Mapear tipos de costo a categorías más generales
        categoria_map = {
            "materia_prima": "Químicos",
            "insumos_basicos": "Agua/Electricidad",
            "sueldos": "Personal",
            "arriendo": "Arriendo"
        }
        
        categorias = {}
        for item in resultados:
            categoria = categoria_map.get(item["_id"], "Otros")
            if categoria not in categorias:
                categorias[categoria] = 0
            categorias[categoria] += item["total"]
        
        total_gastos = sum(categorias.values())
        
        data = []
        for categoria, monto in categorias.items():
            data.append({
                "name": categoria,
                "value": round((monto / total_gastos) * 100, 2) if total_gastos > 0 else 0
            })
        
        return formato_respuesta(data)
        
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}

@router.get("/inventario/stock")
async def get_inventario_stock():
    try:
        # Datos simulados de inventario (en un sistema real, esto vendría de una colección de inventario)
        data = [
            {"producto": "Shampoo", "actual": 8, "minimo": 10, "optimo": 50},
            {"producto": "Cera", "actual": 15, "minimo": 5, "optimo": 20},
            {"producto": "Paños", "actual": 30, "minimo": 20, "optimo": 100},
            {"producto": "Abrillantador", "actual": 12, "minimo": 8, "optimo": 25},
            {"producto": "Desengrasante", "actual": 18, "minimo": 10, "optimo": 30}
        ]
        
        return formato_respuesta(data)
        
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}

@router.get("/inventario/consumo-semanal")
async def get_consumo_semanal():
    try:
        # Datos simulados de consumo (en un sistema real, esto se calcularía basado en servicios)
        dias = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        data = []
        
        for i, dia in enumerate(dias):
            data.append({
                "dia": dia,
                "shampoo": max(5, 10 - i),  # Simulación de consumo decreciente
                "cera": max(2, 5 - i),
                "panos": max(8, 15 - i * 2)
            })
        
        return formato_respuesta(data)
        
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}