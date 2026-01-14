"""
Gunicorn configuration for CASTOR Elecciones production deployment.

Usage:
    gunicorn -c gunicorn.conf.py "app:create_app()"

Or with environment variable:
    GUNICORN_CMD_ARGS="--bind=0.0.0.0:8000" gunicorn "app:create_app()"
"""
import os
import multiprocessing

# Server Socket
bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")
backlog = 2048

# Worker Processes
# Rule of thumb: (2 x CPU cores) + 1
# For ML workloads (BETO model), fewer workers with more memory is better
workers = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() + 1))
worker_class = os.environ.get("GUNICORN_WORKER_CLASS", "sync")  # Use 'gevent' for async
worker_connections = 1000
max_requests = 1000  # Restart workers after N requests (prevent memory leaks)
max_requests_jitter = 50  # Add randomness to prevent all workers restarting at once
timeout = 120  # 2 minutes for long-running ML analysis
graceful_timeout = 30
keepalive = 5

# Server Mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Logging
errorlog = "-"  # stderr
accesslog = "-"  # stdout
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process Naming
proc_name = "castor-elecciones"

# Server Hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    print("CASTOR Elecciones starting...")


def on_reload(server):
    """Called before reloading."""
    print("CASTOR Elecciones reloading...")


def when_ready(server):
    """Called just after the server is started."""
    print(f"CASTOR Elecciones ready. Listening on {bind}")


def worker_int(worker):
    """Called when a worker receives SIGINT or SIGQUIT."""
    print(f"Worker {worker.pid} interrupted")


def worker_abort(worker):
    """Called when a worker receives SIGABRT."""
    print(f"Worker {worker.pid} aborted")


def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass


def post_fork(server, worker):
    """Called just after a worker has been forked."""
    print(f"Worker spawned (pid: {worker.pid})")


def post_worker_init(worker):
    """Called just after a worker has initialized the application."""
    # This is where BETO model gets loaded per worker
    print(f"Worker {worker.pid} initialized")


def worker_exit(server, worker):
    """Called just after a worker has been exited."""
    print(f"Worker {worker.pid} exited")


def nworkers_changed(server, new_value, old_value):
    """Called when the number of workers is changed."""
    print(f"Workers changed from {old_value} to {new_value}")


def on_exit(server):
    """Called just before exiting."""
    print("CASTOR Elecciones shutting down...")


# Security Headers (add via reverse proxy or middleware)
# These are documented here for reference
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'",
}

# Preload app (loads BETO model once, shared across workers via copy-on-write)
preload_app = True

# For Heroku/Railway deployment
if os.environ.get("PORT"):
    bind = f"0.0.0.0:{os.environ['PORT']}"

# For development, reduce workers
if os.environ.get("FLASK_ENV") == "development":
    workers = 2
    reload = True
    loglevel = "debug"
