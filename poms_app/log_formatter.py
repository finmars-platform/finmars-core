import logging
import os


class GunicornWorkerIDLogFormatter(logging.Formatter):
    def format(self, record):
        record.pid = record.wid = os.getpid()
        return super().format(record)
