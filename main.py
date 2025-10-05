from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import upload_router, analytics_router, dashboard_router

app = FastAPI(
    title="Car Wash Analytics API",
    description="API para gestión y análisis de lavadero de autos",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Para desarrollo
        "https://tudominio-frontend.com"  # Tu dominio de frontend en producción
    ],  # En producción, especifica los dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas
app.include_router(upload_router)
app.include_router(analytics_router)
app.include_router(dashboard_router)

@app.get("/")
async def root():
    return {"message": "Car Wash Analytics API - Bienvenido"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "connected"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)