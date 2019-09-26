import copy
import csv
import logging
from abc import abstractmethod
from datetime import date
from io import StringIO
from math import isnan, copysign

from poms.common.formula_accruals import f_xirr, f_duration
from poms.common.utils import isclose
from poms.reports.utils import sprint_table

_l = logging.getLogger('poms.reports')


class BaseReportItem:
    is_cloned = False
    report = None
    pricing_provider = None
    fx_rate_provider = None

    dump_columns = []

    def __init__(self, report, pricing_provider, fx_rate_provider):
        self.report = report
        self.pricing_provider = pricing_provider
        self.fx_rate_provider = fx_rate_provider

    def clone(self):
        ret = copy.copy(self)
        ret.is_cloned = True
        return ret

    @classmethod
    def dump_values(cls, obj, columns=None):
        if columns is None:
            columns = cls.dump_columns
        row = []
        for f in columns:
            v = getattr(obj, f)
            if isinstance(v, float):
                if isclose(v, 0.0):
                    v = 0.0
            row.append(v)
        return row

    @classmethod
    def transpose(cls, columns, data, showindex=None):
        if showindex:
            ncols = ['I', 'attr']
            nrows = [[str(i + 1), c] for i, c in enumerate(columns)]
        else:
            ncols = ['attr']
            nrows = [[c] for c in columns]
        for irow, row in enumerate(data):
            ncols.append('%s' % (irow + 1))
            for icol, col in enumerate(row):
                nrows[icol].append(col)
        return ncols, nrows

    @classmethod
    def sdumps(cls, items, columns=None, filter=None, in_csv=False, transpose=False, showindex=None):
        if columns is None:
            columns = cls.dump_columns

        data = []
        for item in items:
            if filter and callable(filter):
                if filter(item):
                    pass
                else:
                    continue
            data.append(cls.dump_values(item, columns=columns))

        if in_csv:
            si = StringIO()
            cw = csv.writer(si)
            cw.writerow(columns)
            for r in data:
                cw.writerow(r)
            return si.getvalue()
        if transpose:
            columns, data = cls.transpose(columns=columns, data=data, showindex=showindex)
        return sprint_table(data, columns)

    @classmethod
    def dumps(cls, items, columns=None, trn_filter=None, in_csv=None):
        # pass
        _l.debug('\n%s', cls.sdumps(items, columns=columns, filter=trn_filter, in_csv=in_csv))


class YTMMixin:
    # instr
    # instr_pricing_ccy_cur_fx
    # instr_accrued_ccy_cur_fx
    # ytm
    # _instr_ytm_data

    @abstractmethod
    def get_instr_ytm_data_d0_v0(self):
        return date.min, 0

    def get_instr_ytm_data(self):
        if hasattr(self, '_instr_ytm_data'):
            return self._instr_ytm_data

        instr = self.instr

        if instr.maturity_date is None or instr.maturity_date == date.max:
            # _l.debug('get_instr_ytm_data: [], maturity_date rule')
            return []
        if instr.maturity_price is None or isnan(instr.maturity_price) or isclose(instr.maturity_price, 0.0):
            # _l.debug('get_instr_ytm_data: [], maturity_price rule')
            return []

        d0, v0 = self.get_instr_ytm_data_d0_v0()
        data = [(d0, v0)]

        # accruals = instr.get_accrual_calculation_schedules_all()
        # for accrual in accruals:
        #     if d0 > accrual.accrual_end_date:
        #         continue
        #
        #     prev_d = accrual.accrual_start_date
        #     for i in range(0, 3652058):
        #         try:
        #             d = accrual.first_payment_date + accrual.periodicity.to_timedelta(
        #                 n=accrual.periodicity_n, i=i, same_date=accrual.accrual_start_date)
        #         except (OverflowError, ValueError):  # date is out of range
        #             d = date.max
        #         if d < d0:
        #             prev_d = d
        #             continue
        #         if d >= accrual.accrual_end_date:
        #             # accrual last day value
        #             d = accrual.accrual_end_date - timedelta(days=1)
        #
        #         try:
        #             k = instr.accrued_multiplier * instr.get_factor(d) * (accrued_ccy_fx / pricing_ccy_fx)
        #         except ArithmeticError:
        #             k = 0
        #         cpn = get_coupon(accrual, prev_d, d, maturity_date=instr.maturity_date)
        #         data.append((d, cpn * k))
        #
        #         if d == date.max or d >= accrual.accrual_end_date - timedelta(days=1):
        #             break
        #         prev_d = d

        for cpn_date, cpn_val in instr.get_future_coupons(begin_date=d0, with_maturity=False):
            try:
                factor = instr.get_factor(cpn_date)
                k = instr.accrued_multiplier * factor * \
                    (self.instr_accrued_ccy_cur_fx / self.instr_pricing_ccy_cur_fx)
            except ArithmeticError:
                k = 0
            data.append((cpn_date, cpn_val * k))

        prev_factor = None
        for factor in instr.factor_schedules.all():
            if factor.effective_date < d0 or factor.effective_date > instr.maturity_date:
                prev_factor = factor
                continue

            prev_factor_value = prev_factor.factor_value if prev_factor else 1.0
            factor_value = factor.factor_value

            k = (prev_factor_value - factor_value) * instr.price_multiplier
            data.append((factor.effective_date, instr.maturity_price * k))

            prev_factor = factor

        factor = instr.get_factor(instr.maturity_date)
        k = instr.price_multiplier * factor
        data.append((instr.maturity_date, instr.maturity_price * k))

        # sort by date
        data.sort()
        self._instr_ytm_data = data

        # _l.debug('get_instr_ytm_data: data=%s', [(str(d), v) for d, v in data])

        return data

    @abstractmethod
    def get_instr_ytm_x0(self):
        return 0

    def get_instr_ytm(self):
        # _l.debug('get_instr_ytm: %s', self.__class__.__name__)

        if self.instr.maturity_date is None or self.instr.maturity_date == date.max:
            try:
                accrual_size = self.instr.get_accrual_size(self.report.report_date)
                ytm = (accrual_size * self.instr.accrued_multiplier) * \
                      (self.instr_accrued_ccy_cur_fx / self.instr_pricing_ccy_cur_fx) / \
                      (self.instr_price_cur_principal_price * self.instr.price_multiplier)
            except ArithmeticError:
                ytm = 0
            # _l.debug('get_instr_ytm.1: %s', ytm)
            return ytm

        x0 = self.get_instr_ytm_x0()
        # _l.debug('get_instr_ytm: x0=%s', x0)

        data = self.get_instr_ytm_data()

        # _l.debug('data %s' % self.instr.name)
        # _l.debug(data)

        if data:
            ytm = f_xirr(data, x0=x0)
        else:
            ytm = 0.0

        # _l.debug(ytm)
        # _l.debug('{:f}'.format(ytm))
        # _l.debug('get_instr_ytm: %s', ytm)
        return ytm

    def get_instr_duration(self):
        if self.instr.maturity_date is None or self.instr.maturity_date == date.max:
            try:
                duration = 1 / self.ytm
            except ArithmeticError:
                duration = 0
            # _l.debug('get_instr_duration.1: %s', duration)
            return duration
        data = self.get_instr_ytm_data()
        if data:
            duration = f_duration(data, ytm=self.ytm)
        else:
            duration = 0
        # _l.debug('get_instr_duration: %s', duration)
        return duration


class BaseReport:
    # CONSOLIDATION = 1
    MODE_IGNORE = 0
    MODE_INDEPENDENT = 1
    MODE_INTERDEPENDENT = 2
    MODE_CHOICES = (
        (MODE_IGNORE, 'Ignore'),
        (MODE_INDEPENDENT, 'Independent'),
        (MODE_INTERDEPENDENT, 'Offsetting (Interdependent - 0/100, 100/0, 50/50)'),
    )

    def __init__(self, id=None, master_user=None, member=None, task_id=None, task_status=None):
        self.id = id
        self.task_id = task_id
        self.task_status = task_status
        self.master_user = master_user
        self.member = member

        self.context = {
            'master_user': self.master_user,
            'member': self.member,
        }
