"""Conservative Gunicorn configuration for the single Django API service.

Run from the repository root with:
    gunicorn -c deploy/gunicorn.conf.py config.wsgi:application
and set DJANGO_SETTINGS_MODULE=config.settings.production in the service environment.
"""

from __future__ import annotations

import os
from pathlib import Path


bind = os.getenv("GUNICORN_BIND", "127.0.0.1:8000")
workers = int(os.getenv("GUNICORN_WORKERS", "2"))
threads = 1
worker_class = "sync"
timeout = 60
graceful_timeout = 30
keepalive = 5
max_requests = 1_000
max_requests_jitter = 100
chdir = str(Path(__file__).resolve().parent.parent / "backend")
wsgi_app = "config.wsgi:application"
accesslog = "-"
errorlog = "-"
capture_output = True
forwarded_allow_ips = os.getenv("GUNICORN_FORWARDED_ALLOW_IPS", "127.0.0.1")
if forwarded_allow_ips.strip() == "*":
    raise RuntimeError("GUNICORN_FORWARDED_ALLOW_IPS cannot be wildcarded.")
