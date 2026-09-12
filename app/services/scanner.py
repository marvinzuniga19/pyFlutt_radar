from datetime import datetime, timezone
from typing import Any

import feedparser
import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Fuente, Publicacion
from app.services.telegram import enviar_pendientes


# Fuentes que se insertarán automáticamente
# cuando se ejecute la aplicación por primera vez.
FUENTES_INICIALES = [
    {
        "nombre": "Python Insider",
        "url": "https://blog.python.org/rss.xml",
        "categoria": "Python",
    },
    {
        "nombre": "Flutter Blog",
        "url": "https://medium.com/feed/flutter",
        "categoria": "Flutter",
    },
    {
        "nombre": "Dart Blog",
        "url": "https://medium.com/feed/dartlang",
        "categoria": "Flutter",
    },
]


def ahora_utc() -> datetime:
    """
    Devuelve la fecha y hora actual en UTC.

    Se elimina la zona horaria para mantener compatibilidad
    con las columnas DateTime actuales de SQLite.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def limpiar_html(contenido: str | None) -> str:
    """
    Elimina las etiquetas HTML de los resúmenes obtenidos
    desde los feeds RSS.
    """
    if not contenido:
        return ""

    soup = BeautifulSoup(contenido, "html.parser")

    texto = soup.get_text(
        separator=" ",
        strip=True,
    )

    # Elimina espacios repetidos.
    texto_limpio = " ".join(texto.split())

    return texto_limpio


def convertir_fecha(entrada: Any) -> datetime | None:
    """
    Convierte una fecha de feedparser en datetime.

    Algunos feeds utilizan published_parsed y otros
    utilizan updated_parsed.
    """
    fecha = (
        entrada.get("published_parsed")
        or entrada.get("updated_parsed")
    )

    if fecha is None:
        return None

    try:
        return datetime(
            year=fecha.tm_year,
            month=fecha.tm_mon,
            day=fecha.tm_mday,
            hour=fecha.tm_hour,
            minute=fecha.tm_min,
            second=fecha.tm_sec,
        )

    except (AttributeError, TypeError, ValueError):
        return None


def crear_fuentes_iniciales() -> None:
    """
    Guarda las fuentes iniciales solamente si no existen.
    """
    with SessionLocal() as db:

        for datos_fuente in FUENTES_INICIALES:

            consulta = select(Fuente).where(
                Fuente.url == datos_fuente["url"]
            )

            fuente_existente = db.scalar(consulta)

            if fuente_existente is not None:
                continue

            nueva_fuente = Fuente(
                nombre=datos_fuente["nombre"],
                url=datos_fuente["url"],
                categoria=datos_fuente["categoria"],
                activa=True,
            )

            db.add(nueva_fuente)

            print(
                f"Fuente agregada: "
                f"{datos_fuente['nombre']}"
            )

        db.commit()


async def descargar_feed(
    cliente: httpx.AsyncClient,
    url: str,
) -> Any:
    """
    Descarga el contenido RSS o Atom de una fuente.
    """
    respuesta = await cliente.get(
        url,
        follow_redirects=True,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(X11; Linux x86_64) "
                "PyFlutterRadar/1.0"
            ),
            "Accept": (
                "application/rss+xml,"
                "application/atom+xml,"
                "application/xml,"
                "text/xml,"
                "*/*"
            ),
        },
    )

    respuesta.raise_for_status()

    feed = feedparser.parse(respuesta.content)

    return feed


async def escanear_fuentes() -> dict[str, int]:
    """
    Revisa todas las fuentes activas.

    Si una publicación no existe en la base de datos,
    la guarda como nueva.
    """
    print("")
    print("Iniciando escaneo automático...")

    publicaciones_nuevas = 0
    fuentes_con_error = 0

    with SessionLocal() as db:

        consulta_fuentes = select(Fuente).where(
            Fuente.activa.is_(True)
        )

        fuentes = list(
            db.scalars(consulta_fuentes).all()
        )

        if not fuentes:
            print("No existen fuentes activas.")

            return {
                "nuevas": 0,
                "errores": 0,
            }

        async with httpx.AsyncClient(
            timeout=20,
        ) as cliente:

            for fuente in fuentes:

                # Contador independiente para cada fuente.
                # Solo se suma al total si el commit funciona.
                nuevas_de_esta_fuente = 0

                try:
                    print(f"Revisando: {fuente.nombre}")

                    feed = await descargar_feed(
                        cliente=cliente,
                        url=fuente.url,
                    )

                    if not feed.entries:
                        print(
                            f"No se encontraron entradas "
                            f"en {fuente.nombre}."
                        )

                    # Procesamos solamente las últimas
                    # 15 publicaciones de cada fuente.
                    for entrada in feed.entries[:15]:

                        titulo = entrada.get(
                            "title",
                            "",
                        ).strip()

                        url = entrada.get(
                            "link",
                            "",
                        ).strip()

                        # Ignoramos entradas incompletas.
                        if not titulo or not url:
                            continue

                        # Comprobamos si la URL ya existe.
                        consulta_publicacion = (
                            select(Publicacion)
                            .where(
                                Publicacion.url == url
                            )
                        )

                        publicacion_existente = db.scalar(
                            consulta_publicacion
                        )

                        if publicacion_existente is not None:
                            continue

                        resumen_original = (
                            entrada.get("summary")
                            or entrada.get("description")
                            or ""
                        )

                        resumen_limpio = limpiar_html(
                            resumen_original
                        )

                        fecha_publicacion = convertir_fecha(
                            entrada
                        )

                        nueva_publicacion = Publicacion(
                            titulo=titulo[:300],
                            url=url[:700],
                            resumen=resumen_limpio,
                            fecha_publicacion=fecha_publicacion,
                            fecha_descubrimiento=ahora_utc(),
                            enviada_telegram=False,
                            fuente_id=fuente.id,
                        )

                        db.add(nueva_publicacion)

                        nuevas_de_esta_fuente += 1

                    # Registramos cuándo terminó
                    # la revisión de esta fuente.
                    fuente.ultima_revision = ahora_utc()

                    # Guarda las publicaciones encontradas.
                    db.commit()

                    # Solo aumentamos el total después
                    # de confirmar que se guardaron.
                    publicaciones_nuevas += (
                        nuevas_de_esta_fuente
                    )

                    print(
                        f"{fuente.nombre}: "
                        f"{nuevas_de_esta_fuente} nuevas."
                    )

                except httpx.HTTPStatusError as error:
                    db.rollback()
                    fuentes_con_error += 1

                    print(
                        f"Error HTTP en {fuente.nombre}: "
                        f"{error.response.status_code}"
                    )

                except httpx.RequestError as error:
                    db.rollback()
                    fuentes_con_error += 1

                    print(
                        f"Error de conexión en "
                        f"{fuente.nombre}: {error}"
                    )

                except Exception as error:
                    db.rollback()
                    fuentes_con_error += 1

                    print(
                        f"Error al revisar "
                        f"{fuente.nombre}: {error}"
                    )

    print(
        "Escaneo terminado. "
        f"Nuevas: {publicaciones_nuevas}. "
        f"Errores: {fuentes_con_error}."
    )

    # Enviar las publicaciones pendientes a Telegram.
    resultado_telegram = await enviar_pendientes()

    print("")

    return {
        "nuevas": publicaciones_nuevas,
        "errores": fuentes_con_error,
        "telegram_enviadas": resultado_telegram["enviadas"],
        "telegram_errores": resultado_telegram["errores"],
    }