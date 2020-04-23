import logging
import os
import stat
from logging import handlers


class GroupWriteRotatingFileHandler(handlers.RotatingFileHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # os.chmod(self.baseFilename, 0o0777)

    def _open(self):
        prevumask=os.umask(0o002)

        rtv=logging.handlers.RotatingFileHandler._open(self)

        os.chmod(self.baseFilename, 0o0777)

        os.umask(prevumask)
        return rtv
