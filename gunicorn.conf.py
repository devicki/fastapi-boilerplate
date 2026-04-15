import multiprocessing
import os

# --------------------
# Base directory (project root)
# --------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Server socket
bind = "0.0.0.0:8088"
backlog = 2048

# Worker processes
workers = min(4, multiprocessing.cpu_count())
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Timeout
timeout = 30
keepalive = 2
graceful_timeout = 30

# Application
preload_app = True
wsgi_module = "app.main:app"

# Process naming
proc_name = "fastapi-app"

# Logging
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

loglevel = os.getenv("LOG_LEVEL", "info").lower()
errorlog = os.path.join(BASE_DIR, "logs", "error.log")

# Server mechanics
daemon = False
pidfile = "/tmp/gunicorn.pid"
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
keyfile = None
certfile = None

# Reload (development)
reload = False
reload_engine = "auto"
