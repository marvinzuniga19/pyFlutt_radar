# PyFlutter Radar

Monitor automático de novedades sobre **Python** y **Flutter**. Escanea feeds RSS periódicamente, guarda las publicaciones en una base de datos y envía notificaciones a **Telegram**.

## Características

- Escaneo automático de feeds RSS con intervalo configurable.
- Notificaciones a Telegram para cada publicación nueva.
- Dashboard web con Bootstrap 5 para visualizar las novedades.
- Escaneo manual desde la interfaz web.
- Endpoint de salud (`/health`) para monitoreo.

## Fuentes incluidas

| Fuente | Categoría |
|---|---|
| [Python Insider](https://blog.python.org/rss.xml) | Python |
| [Flutter Blog](https://medium.com/feed/flutter) | Flutter |
| [Dart Blog](https://medium.com/feed/dartlang) | Flutter |

## Tecnologías

- **FastAPI** — Framework web.
- **SQLAlchemy** — ORM para la base de datos.
- **APScheduler** — Programador de tareas automáticas.
- **feedparser** — Lectura de feeds RSS/Atom.
- **httpx** — Cliente HTTP asíncrono.
- **BeautifulSoup** — Limpieza de contenido HTML.
- **Bootstrap 5** — Interfaz web.
- **SQLite** (desarrollo) / **PostgreSQL** (producción).

## Requisitos

- Python 3.11 o superior.
- Un bot de Telegram (opcional, para notificaciones).

## Instalación local

1. Clonar el repositorio:

```bash
git clone https://github.com/TU_USUARIO/pyflutter-radar.git
cd pyflutter-radar
```

2. Crear y activar el entorno virtual:

```bash
python -m venv .venv
source .venv/bin/activate
```

3. Instalar las dependencias:

```bash
pip install -r requirements.txt
```

4. Configurar las variables de entorno:

```bash
cp .env.example .env
```

Editar el archivo `.env` con tus valores:

```env
SCAN_INTERVAL_MINUTES=60
TELEGRAM_BOT_TOKEN=tu_token_aqui
TELEGRAM_CHAT_ID=tu_chat_id_aqui
```

5. Ejecutar la aplicación:

```bash
uvicorn app.main:app --reload
```

La app estará disponible en `http://localhost:8000`.

## Configuración de Telegram

1. Hablar con [@BotFather](https://t.me/BotFather) en Telegram.
2. Crear un bot con `/newbot` y copiar el token.
3. Obtener tu Chat ID hablando con [@userinfobot](https://t.me/userinfobot).
4. Agregar ambos valores al archivo `.env`.

## Estructura del proyecto

```
pyflutter-radar/
├── app/
│   ├── main.py              # App FastAPI, rutas y scheduler
│   ├── models.py            # Modelos SQLAlchemy (Fuente, Publicacion)
│   ├── database.py          # Configuración de la base de datos
│   ├── services/
│   │   ├── scanner.py       # Escaneo de feeds RSS
│   │   └── telegram.py      # Envío de notificaciones a Telegram
│   ├── templates/
│   │   └── index.html       # Dashboard web
│   └── static/css/
│       └── styles.css        # Estilos personalizados
├── data/
│   └── radar.db             # Base de datos SQLite (local)
├── requirements.txt
├── render.yaml              # Configuración de deploy en Render
├── .env.example             # Variables de entorno de ejemplo
└── .gitignore
```

## Rutas de la API

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/` | Dashboard con las publicaciones. |
| `POST` | `/escanear` | Ejecutar un escaneo manual. |
| `GET` | `/health` | Estado del servicio y del scheduler. |

## Deploy en Render

La app está preparada para desplegarse en [Render](https://render.com) con PostgreSQL:

1. Subir el código a GitHub.
2. En Render: **New → Blueprint** → conectar el repositorio.
3. Render detecta `render.yaml` y crea el servicio web + base de datos.
4. Agregar las variables `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`.

> **Nota:** En desarrollo local la app usa SQLite automáticamente. En Render usa PostgreSQL a través de la variable `DATABASE_URL`.

## Variables de entorno

| Variable | Descripción | Requerida |
|---|---|---|
| `DATABASE_URL` | URL de conexión a PostgreSQL. Si no se define, usa SQLite. | No |
| `SCAN_INTERVAL_MINUTES` | Intervalo entre escaneos automáticos (en minutos). Default: `60`. | No |
| `TELEGRAM_BOT_TOKEN` | Token del bot de Telegram. | No |
| `TELEGRAM_CHAT_ID` | ID del chat de Telegram donde enviar las notificaciones. | No |

## Licencia

MIT

