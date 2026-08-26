# Gunicorn config for Talos (Pi)
bind = "0.0.0.0:5009"
workers = 2
worker_class = "sync"
timeout = 30

accesslog = "/opt/talos/logs/access.log"
errorlog  = "/opt/talos/logs/error.log"
loglevel  = "info"

max_requests = 1000
max_requests_jitter = 100
