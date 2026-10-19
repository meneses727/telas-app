from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth, telas, datos, mineria, motor, recomendaciones, dashboard, simulaciones, propuestas

app = FastAPI(
    title="Modelo de abastecimiento de telas",
    description="API para predicción de abastecimiento de telas con data mining y lógica difusa (Mamdani).",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.lista_origenes_permitidos,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router)
app.include_router(telas.router)
app.include_router(datos.router)
app.include_router(mineria.router)
app.include_router(motor.router)
app.include_router(recomendaciones.router)
app.include_router(dashboard.router)
app.include_router(simulaciones.router)
app.include_router(propuestas.router)


@app.get("/health", tags=["sistema"])
def health_check():
    return {"status": "ok"}
