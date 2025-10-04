import pandas as pd
from datetime import datetime
from models.database import mongodb
from models.schemas import DiaOperacionCreate, ServicioCreate, CostoCreate

class ExcelProcessor:
    def __init__(self):
        self.collections = mongodb.get_collections()
    
    def procesar_excel(self, file_path: str):
        try:
            # Leer el archivo Excel
            df = pd.read_excel(file_path)
            resultados = {
                "dias_insertados": 0,
                "servicios_insertados": 0,
                "costos_insertados": 0
            }
            
            for index, row in df.iterrows():
                # Procesar cada fila
                dia_result = self._procesar_dia(row)
                if dia_result:
                    resultados["dias_insertados"] += 1
                    dia_id = dia_result
                    
                    # Procesar servicios
                    servicios_ids = self._procesar_servicios(row, dia_id)
                    resultados["servicios_insertados"] += len(servicios_ids)
                    
                    # Procesar costos
                    costos_ids = self._procesar_costos(row, dia_id)
                    resultados["costos_insertados"] += len(costos_ids)
            
            return resultados
            
        except Exception as e:
            raise Exception(f"Error procesando Excel: {str(e)}")
    
    def _procesar_dia(self, row):
        try:
            # Determinar estado y horario
            if row['hora_apertura'] == 'Cerrado':
                estado = 'cerrado'
                horario = {"apertura": "Cerrado", "cierre": "Cerrado"}
            else:
                estado = 'abierto'
                horario = {"apertura": row['hora_apertura'], "cierre": row['hora_cierre']}
            
            # Calcular costos totales
            costos_totales = (
                row.get('costo_materia_prima', 0) + 
                row.get('insumos_basicos', 0) + 
                row.get('costo_sueldos', 0) + 
                row.get('arriendo_pagado', 0)
            )
            
            dia_data = DiaOperacionCreate(
                fecha=row['fecha'],
                dia_semana=row['dia_semana'],
                horario=horario,
                estado=estado,
                servicios_atendidos=row['servicios_atendidos'],
                ingresos_totales=row['ingresos_servicios'],
                ganancia_neta=row['ganancia_neta'],
                costos_totales=costos_totales
            )
            
            # Insertar en MongoDB
            result = self.collections["dias_operacion"].insert_one(dia_data.dict())
            return str(result.inserted_id)
            
        except Exception as e:
            print(f"Error procesando día: {e}")
            return None
    
    def _procesar_servicios(self, row, dia_id):
        servicios_ids = []
        try:
            # Mapeo de tipos de servicio
            servicios_map = [
                ('servicios_normal', 'ingresos_normal', 'normal', 15000),
                ('servicios_premium', 'ingresos_premium', 'premium', 25000),
                ('servicios_full_premium', 'ingresos_full_premium', 'full_premium', 35000)
            ]
            
            for servicio_col, ingreso_col, tipo, precio in servicios_map:
                cantidad = row[servicio_col]
                if cantidad > 0:
                    servicio_data = ServicioCreate(
                        dia_id=dia_id,
                        fecha=row['fecha'],
                        tipo_servicio=tipo,
                        cantidad=cantidad,
                        ingresos=row[ingreso_col],
                        precio_unitario=precio
                    )
                    
                    result = self.collections["servicios"].insert_one(servicio_data.dict())
                    servicios_ids.append(str(result.inserted_id))
                    
        except Exception as e:
            print(f"Error procesando servicios: {e}")
        
        return servicios_ids
    
    def _procesar_costos(self, row, dia_id):
        costos_ids = []
        try:
            costos_map = [
                ('costo_materia_prima', 'materia_prima', 'Costo de materia prima del día'),
                ('insumos_basicos', 'insumos_basicos', 'Insumos básicos del día'),
                ('costo_sueldos', 'sueldos', 'Costos de personal'),
                ('arriendo_pagado', 'arriendo', 'Arriendo del local')
            ]
            
            for costo_col, tipo, descripcion in costos_map:
                monto = row.get(costo_col, 0)
                if monto > 0:
                    costo_data = CostoCreate(
                        dia_id=dia_id,
                        fecha=row['fecha'],
                        tipo_costo=tipo,
                        monto=monto,
                        descripcion=descripcion
                    )
                    
                    result = self.collections["costos"].insert_one(costo_data.dict())
                    costos_ids.append(str(result.inserted_id))
                    
        except Exception as e:
            print(f"Error procesando costos: {e}")
        
        return costos_ids