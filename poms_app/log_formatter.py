import os

from colorlog import ColoredFormatter

class GunicornWorkerIDLogFormatter(ColoredFormatter):
    def format(self, record):
        record.wid = os.environ.get('GUNICORN_WORKER_ID', 'main')
        return super().format(record)