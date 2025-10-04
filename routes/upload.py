from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import os
from utils.exel_procesador import ExcelProcessor

router = APIRouter(prefix="/upload", tags=["Upload"])

@router.post("/excel")
async def upload_excel(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(400, "Solo se permiten archivos Excel")
    
    # Crear directorio temporal si no existe
    os.makedirs("temp_uploads", exist_ok=True)
    file_path = f"temp_uploads/{file.filename}"
    
    try:
        # Guardar archivo temporalmente
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Procesar archivo
        processor = ExcelProcessor()
        resultados = processor.procesar_excel(file_path)
        
        # Limpiar archivo temporal
        os.remove(file_path)
        
        return {
            "message": "Archivo procesado exitosamente",
            "resultados": resultados
        }
        
    except Exception as e:
        # Limpiar en caso de error
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(500, f"Error procesando archivo: {str(e)}")