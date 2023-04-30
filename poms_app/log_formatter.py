import os

from colorlog import ColoredFormatter
import gunicorn.sock

class GunicornWorkerIDLogFormatter(ColoredFormatter):
    def format(self, record):
        record.pid = record.wid = os.getpid()
        return super().format(record)