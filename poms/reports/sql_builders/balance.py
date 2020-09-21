import logging
import time

_l = logging.getLogger('poms.reports')


class ReportBuilderSql:

    def __init__(self, instance=None):

        _l.debug('ReportBuilderSql init')

        self.instance = instance

    def build_balance(self):

        st = time.perf_counter()

        self.build()

        _l.debug('build_st done: %s', "{:3.3f}".format(time.perf_counter() - st))

        return self.instance

    def build(self):

        return self.instance
