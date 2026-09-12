import os
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Publicacion


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

TELEGRAM_API_URL = (
    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    "/sendMessage"
)


def _ahora_utc() -> datetime:
    """
    Devuelve la fecha y hora actual en UTC.

    Se elimina la zona horaria para mantener compatibilidad
    con las columnas DateTime actuales de SQLite.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def formatear_mensaje(publicacion: Publicacion) -> str:
    """
    Genera el texto del mensaje de Telegram
    con formato MarkdownV2-compatible (HTML).
    """
    categoria = ""

    if publicacion.fuente:
        categoria = publicacion.fuente.categoria

    # Construimos el resumen truncado.
    resumen = publicacion.resumen or ""

    if len(resumen) > 300:
        resumen = resumen[:300] + "..."

    lineas = [
        f"📰 <b>{_escapar_html(publicacion.titulo)}</b>",
        "",
    ]

    if categoria:
        lineas.append(f"📂 {_escapar_html(categoria)}")

    if publicacion.fuente:
        lineas.append(
            f"📡 {_escapar_html(publicacion.fuente.nombre)}"
        )

    if resumen:
        lineas.append("")
        lineas.append(_escapar_html(resumen))

    lineas.append("")
    lineas.append(f'🔗 <a href="{publicacion.url}">Leer más</a>')

    return "\n".join(lineas)


def _escapar_html(texto: str) -> str:
    """
    Escapa los caracteres especiales de HTML
    para evitar errores en la API de Telegram.
    """
    return (
        texto
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


async def enviar_mensaje(
    cliente: httpx.AsyncClient,
    texto: str,
) -> bool:
    """
    Envía un mensaje a Telegram usando la API de Bot.

    Devuelve True si el envío fue exitoso.
    """
    respuesta = await cliente.post(
        TELEGRAM_API_URL,
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": texto,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=15,
    )

    if respuesta.status_code == 200:
        return True

    print(
        f"Error al enviar a Telegram: "
        f"{respuesta.status_code} — "
        f"{respuesta.text}"
    )

    return False


async def enviar_pendientes() -> dict[str, int]:
    """
    Busca todas las publicaciones que aún no se han
    enviado a Telegram y las envía una por una.

    Actualiza el estado de cada publicación después
    del envío exitoso.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(
            "Telegram no configurado. "
            "Se omite el envío de notificaciones."
        )
        return {"enviadas": 0, "errores": 0}

    enviadas = 0
    errores = 0

    with SessionLocal() as db:

        consulta = (
            select(Publicacion)
            .where(
                Publicacion.enviada_telegram.is_(False)
            )
            .order_by(
                Publicacion.fecha_descubrimiento.asc()
            )
        )

        pendientes = list(
            db.scalars(consulta).all()
        )

        if not pendientes:
            return {"enviadas": 0, "errores": 0}

        print(
            f"Enviando {len(pendientes)} "
            f"publicaciones a Telegram..."
        )

        async with httpx.AsyncClient() as cliente:

            for publicacion in pendientes:

                try:
                    texto = formatear_mensaje(publicacion)

                    exito = await enviar_mensaje(
                        cliente=cliente,
                        texto=texto,
                    )

                    if exito:
                        publicacion.enviada_telegram = True
                        publicacion.fecha_envio = _ahora_utc()

                        db.commit()

                        enviadas += 1
                    else:
                        errores += 1

                except Exception as error:
                    db.rollback()
                    errores += 1

                    print(
                        f"Error enviando '{publicacion.titulo}': "
                        f"{error}"
                    )

    print(
        f"Telegram: {enviadas} enviadas, "
        f"{errores} errores."
    )

    return {"enviadas": enviadas, "errores": errores}

