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
    
@router.get("/dashboard/revenue")
async def get_revenue(
    periodo: str = Query("semana", description="Periodo: hoy, semana, mes"),
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None)
):
    try:
        collections = mongodb.get_collections()
        
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Determinar el rango de fechas según el periodo
        if periodo == "hoy":
            fecha_inicio = hoy
            fecha_fin = hoy
        elif periodo == "semana":
            fecha_inicio = hoy - timedelta(days=hoy.weekday())
            fecha_fin = hoy
        elif periodo == "mes":
            fecha_inicio = hoy.replace(day=1)
            fecha_fin = hoy
        else:
            # Usar fechas personalizadas si se proporcionan
            if fecha_inicio and fecha_fin:
                fecha_inicio = datetime.fromisoformat(fecha_inicio)
                fecha_fin = datetime.fromisoformat(fecha_fin)
            else:
                fecha_inicio = hoy - timedelta(days=7)
                fecha_fin = hoy
        
        pipeline = [
            {"$match": {
                "fecha": {
                    "$gte": fecha_inicio,
                    "$lte": fecha_fin
                }
            }},
            {"$group": {
                "_id": None,
                "ingresos_totales": {"$sum": "$ingresos_totales"},
                "servicios_atendidos": {"$sum": "$servicios_atendidos"},
                "ganancia_neta": {"$sum": "$ganancia_neta"},
                "dias_operacion": {"$sum": 1}
            }}
        ]
        
        resultados = list(collections["dias_operacion"].aggregate(pipeline))
        
        if resultados:
            data = {
                "ingresos_totales": resultados[0]["ingresos_totales"],
                "servicios_atendidos": resultados[0]["servicios_atendidos"],
                "ganancia_neta": resultados[0]["ganancia_neta"],
                "dias_operacion": resultados[0]["dias_operacion"],
                "ticket_promedio": round(resultados[0]["ingresos_totales"] / resultados[0]["servicios_atendidos"], 2) if resultados[0]["servicios_atendidos"] > 0 else 0,
                "periodo": {
                    "fecha_inicio": fecha_inicio.strftime("%Y-%m-%d"),
                    "fecha_fin": fecha_fin.strftime("%Y-%m-%d"),
                    "tipo": periodo
                }
            }
        else:
            data = {
                "ingresos_totales": 0,
                "servicios_atendidos": 0,
                "ganancia_neta": 0,
                "dias_operacion": 0,
                "ticket_promedio": 0,
                "periodo": {
                    "fecha_inicio": fecha_inicio.strftime("%Y-%m-%d"),
                    "fecha_fin": fecha_fin.strftime("%Y-%m-%d"),
                    "tipo": periodo
                }
            }
        
        return formato_respuesta(data)
        
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}

@router.get("/dashboard/services")
async def get_services(
    periodo: Optional[str] = Query("semana"),
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None)
):
    """Ruta VERDADERA - Solo datos reales de la base de datos"""
    try:
        collections = mongodb.get_collections()
        
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Determinar fechas REALES
        if periodo == "hoy":
            fecha_inicio_dt = hoy
            fecha_fin_dt = hoy
        elif periodo == "semana":
            fecha_inicio_dt = hoy - timedelta(days=hoy.weekday())
            fecha_fin_dt = hoy
        elif periodo == "mes":
            fecha_inicio_dt = hoy.replace(day=1)
            fecha_fin_dt = hoy
        else:
            if fecha_inicio and fecha_fin:
                fecha_inicio_dt = datetime.fromisoformat(fecha_inicio)
                fecha_fin_dt = datetime.fromisoformat(fecha_fin)
            else:
                fecha_inicio_dt = hoy - timedelta(days=7)
                fecha_fin_dt = hoy

        # 1. Obtener datos REALES de días_operacion
        pipeline_dias = [
            {"$match": {
                "fecha": {
                    "$gte": fecha_inicio_dt,
                    "$lte": fecha_fin_dt
                }
            }},
            {"$group": {
                "_id": None,
                "total_servicios": {"$sum": "$servicios_atendidos"},
                "total_ingresos": {"$sum": "$ingresos_totales"},
                "dias_operacion": {"$sum": 1},
                "promedio_diario": {"$avg": "$servicios_atendidos"},
                "ganancia_neta": {"$sum": "$ganancia_neta"},
                "costos_totales": {"$sum": "$costos_totales"}
            }}
        ]
        
        resultado_dias = list(collections["dias_operacion"].aggregate(pipeline_dias))
        
        # 2. Obtener datos REALES de servicios
        pipeline_servicios = [
            {"$match": {
                "fecha": {
                    "$gte": fecha_inicio_dt,
                    "$lte": fecha_fin_dt
                }
            }},
            {"$group": {
                "_id": "$tipo_servicio",
                "cantidad": {"$sum": "$cantidad"},
                "ingresos": {"$sum": "$ingresos"},
                "veces_contratado": {"$sum": 1}
            }},
            {"$sort": {"cantidad": -1}}
        ]
        
        resultado_servicios = list(collections["servicios"].aggregate(pipeline_servicios))
        
        # 3. Obtener días REALES con datos
        pipeline_dias_concretos = [
            {"$match": {
                "fecha": {
                    "$gte": fecha_inicio_dt,
                    "$lte": fecha_fin_dt
                }
            }},
            {"$project": {
                "fecha": 1,
                "dia_semana": 1,
                "servicios_atendidos": 1,
                "ingresos_totales": 1,
                "ganancia_neta": 1
            }},
            {"$sort": {"fecha": 1}}
        ]
        
        dias_con_datos = list(collections["dias_operacion"].aggregate(pipeline_dias_concretos))

        # PROCESAR DATOS REALES - SIN INVENTAR NADA
        estadisticas_generales = {
            "total_servicios": 0,
            "total_ingresos": 0,
            "ganancia_neta": 0,
            "costos_totales": 0,
            "dias_operacion": 0,
            "promedio_diario": 0,
            "ticket_promedio": 0
        }

        # Solo si hay datos REALES
        if resultado_dias:
            estadisticas_generales = {
                "total_servicios": resultado_dias[0].get("total_servicios", 0),
                "total_ingresos": resultado_dias[0].get("total_ingresos", 0),
                "ganancia_neta": resultado_dias[0].get("ganancia_neta", 0),
                "costos_totales": resultado_dias[0].get("costos_totales", 0),
                "dias_operacion": resultado_dias[0].get("dias_operacion", 0),
                "promedio_diario": round(resultado_dias[0].get("promedio_diario", 0), 2),
                "ticket_promedio": round(
                    resultado_dias[0].get("total_ingresos", 0) / 
                    resultado_dias[0].get("total_servicios", 1), 2
                ) if resultado_dias[0].get("total_servicios", 0) > 0 else 0
            }

        # Procesar servicios REALES
        distribucion_tipos = []
        for servicio in resultado_servicios:
            distribucion_tipos.append({
                "tipo_servicio": servicio["_id"],
                "cantidad": servicio["cantidad"],
                "ingresos": servicio["ingresos"],
                "veces_contratado": servicio["veces_contratado"],
                "precio_promedio": round(servicio["ingresos"] / servicio["cantidad"], 2) if servicio["cantidad"] > 0 else 0
            })

        # Procesar días REALES
        evolucion_diaria = []
        for dia in dias_con_datos:
            evolucion_diaria.append({
                "fecha": dia["fecha"].strftime("%Y-%m-%d"),
                "dia_semana": dia["dia_semana"],
                "servicios": dia["servicios_atendidos"],
                "ingresos": dia["ingresos_totales"],
                "ganancia": dia["ganancia_neta"]
            })

        # Servicio más popular REAL
        servicio_mas_popular = None
        if distribucion_tipos:
            servicio_mas_popular = max(distribucion_tipos, key=lambda x: x["cantidad"])

        # RESPUESTA 100% REAL
        data = {
            "metadata": {
                "datos_reales": True,
                "total_documentos_encontrados": len(dias_con_datos),
                "periodo_consultado": {
                    "tipo": periodo,
                    "fecha_inicio": fecha_inicio_dt.strftime("%Y-%m-%d"),
                    "fecha_fin": fecha_fin_dt.strftime("%Y-%m-%d")
                },
                "fechas_con_datos_reales": [dia["fecha"].strftime("%Y-%m-%d") for dia in dias_con_datos]
            },
            "estadisticas_generales": estadisticas_generales,
            "distribucion_tipos": distribucion_tipos,
            "evolucion_diaria": evolucion_diaria,
            "servicio_mas_popular": servicio_mas_popular,
            "total_tipos_servicios": len(distribucion_tipos)
        }

        return {
            "success": True, 
            "data": data, 
            "error": None,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False, 
            "data": None, 
            "error": f"Error real: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }