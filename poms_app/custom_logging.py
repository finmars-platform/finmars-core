import os
import stat
from logging import handlers


class GroupWriteRotatingFileHandler(handlers.RotatingFileHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        os.chmod(self.baseFilename, 0o0777)
