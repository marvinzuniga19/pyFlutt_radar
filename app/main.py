import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncIterator

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import Base, engine, obtener_base_datos
from app.models import Publicacion
from app.services.scanner import (
    crear_fuentes_iniciales,
    escanear_fuentes,
)


# Cargar variables del archivo .env
load_dotenv()

INTERVALO_ESCANEO = int(
    os.getenv("SCAN_INTERVAL_MINUTES", "60")
)

# Programador automático
scheduler = AsyncIOScheduler(timezone="UTC")


@asynccontextmanager
async def lifespan(
    fastapi_app: FastAPI,
) -> AsyncIterator[None]:
    # Crear las tablas.
    Base.metadata.create_all(bind=engine)

    # Insertar fuentes iniciales.
    crear_fuentes_iniciales()

    # Programar el escaneo automático.
    scheduler.add_job(
        escanear_fuentes,
        trigger="interval",
        minutes=INTERVALO_ESCANEO,
        id="escanear_fuentes",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        next_run_time=datetime.now(timezone.utc),
    )

    scheduler.start()

    print(
        "Escáner automático iniciado. "
        f"Intervalo: {INTERVALO_ESCANEO} minutos."
    )

    yield

    if scheduler.running:
        scheduler.shutdown(wait=False)


# Esta es la variable que Uvicorn está buscando.
app = FastAPI(
    title="PyFlutter Radar",
    description="Monitor de novedades sobre Python y Flutter",
    version="1.0.0",
    lifespan=lifespan,
)


# Configurar archivos estáticos.
app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static",
)


# Configurar plantillas HTML.
templates = Jinja2Templates(
    directory="app/templates"
)


@app.get("/")
async def inicio(
    request: Request,
    db: Session = Depends(obtener_base_datos),
):
    consulta = (
        select(Publicacion)
        .options(
            joinedload(Publicacion.fuente)
        )
        .order_by(
            Publicacion.fecha_descubrimiento.desc()
        )
    )

    publicaciones = db.scalars(consulta).all()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "nombre_app": "PyFlutter Radar",
            "publicaciones": publicaciones,
            "intervalo_escaneo": INTERVALO_ESCANEO,
        },
    )


@app.post("/escanear")
async def escanear_manualmente():
    resultado = await escanear_fuentes()

    print(
        "Escaneo manual terminado: "
        f"{resultado}"
    )

    return RedirectResponse(
        url="/",
        status_code=303,
    )


@app.get("/health")
async def verificar_estado():
    trabajo = scheduler.get_job(
        "escanear_fuentes"
    )

    proxima_ejecucion = None

    if trabajo and trabajo.next_run_time:
        proxima_ejecucion = (
            trabajo.next_run_time.isoformat()
        )

    return {
        "status": "ok",
        "database": "connected",
        "scanner": (
            "active"
            if scheduler.running
            else "inactive"
        ),
        "interval_minutes": INTERVALO_ESCANEO,
        "next_scan": proxima_ejecucion,
    }