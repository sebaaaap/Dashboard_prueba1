from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class Horario(BaseModel):
    apertura: str
    cierre: str

class DiaOperacionBase(BaseModel):
    fecha: datetime
    dia_semana: str
    servicios_atendidos: int
    ingresos_totales: float
    ganancia_neta: float
    costos_totales: float

class DiaOperacionCreate(DiaOperacionBase):
    horario: Horario
    estado: str

class ServicioBase(BaseModel):
    fecha: datetime
    tipo_servicio: str
    cantidad: int
    ingresos: float
    precio_unitario: float

class ServicioCreate(ServicioBase):
    dia_id: str

class CostoBase(BaseModel):
    fecha: datetime
    tipo_costo: str
    monto: float
    descripcion: Optional[str] = None

class CostoCreate(CostoBase):
    dia_id: str

# Schemas para responses
class DiaOperacionResponse(DiaOperacionBase):
    id: str
    horario: Horario
    estado: str

class AnalyticsResponse(BaseModel):
    ingresos_por_tipo: dict
    servicios_por_dia: List[dict]
    ganancias_totales: float
    promedio_servicios_dia: float