import calendar
import logging
from datetime import date, timedelta

from dateutil import relativedelta, rrule

from poms.common.exceptions import FinmarsBaseException

# no need for scipy 2024-10-27 szhitenev
# from scipy.optimize import newton

_l = logging.getLogger("poms.common")


class FormulaAccrualsError(FinmarsBaseException):
    pass


def calculate_accrual_schedule_factor(
    accrual_calculation_schedule=None,
    accrual_calculation_model=None,
    periodicity=None,
    dt1=None,
    dt2=None,
    dt3=None,
    maturity_date=None,
) -> float:
    from poms.instruments.models import AccrualCalculationModel

    # day_convention_code - accrual_calculation_model
    # freq
    # dt1 - first accrual date - берется из AccrualCalculationSchedule
    # dt2 - дата на которую идет расчет accrued interest
    # dt3 - first coupon date - берется из AccrualCalculationSchedule
    # maturity_date - instrument.maturity_date

    if accrual_calculation_schedule:
        accrual_calculation_model = accrual_calculation_schedule.accrual_calculation_model
        periodicity = accrual_calculation_schedule.periodicity
        if maturity_date is None:
            maturity_date = accrual_calculation_schedule.instrument.maturity_date

    # if isinstance(accrual_calculation_model, AccrualCalculationModel):
    #     accrual_calculation_model = accrual_calculation_model.id

    # if isinstance(periodicity, Periodicity):
    #     periodicity = periodicity.id

    if accrual_calculation_model is None or periodicity is None or dt1 is None or dt2 is None or dt3 is None:
        return 0

    # k = 0
    # If freq > 0 And freq <= 12 Then
    #     While DateAdd("m", 12 / freq * k, dt3) <= dt2
    #         k = k + 1
    #     Wend
    #     dt3 = DateAdd("m", 12 / freq * k, dt3)
    #     If k > 0 Then dt1 = DateAdd("m", -12 / freq, dt3)
    #     If Not IsNull(MaturityDate) Then If dt3 >= MaturityDate And dt2 < MaturityDate Then dt3 = MaturityDate
    #
    # ElseIf freq >= 12 Then
    #     MsgBox ("Cpn Frequency over '12'. This situation is not handled in the 'CaouponAccrualFactor' code!!!")
    #     CouponAccrualFactor = 0
    #     Exit Function
    # ElseIf freq = 0 Then
    #         freq = 1
    #         dt3 = DateAdd("m", 12, dt1)
    # Else
    #     dt3 = MaturityDate
    # End If

    freq = periodicity.to_freq()

    if 0 < freq <= 12:
        # k = 0
        # while (dt3 + relativedelta.relativedelta(months=12 / freq * k)) <= dt2:
        #     k += 1
        # dt3 += relativedelta.relativedelta(months=12 / freq * k)
        # if k > 0:
        #     dt1 = dt3 + relativedelta.relativedelta(months=-12 / freq)
        # if maturity_date is not None:
        #     if dt3 >= maturity_date > dt2:
        #         dt3 = maturity_date

        k = 0
        while (dt3 + periodicity.to_timedelta(i=k)) <= dt2:
            k += 1
        dt3 += periodicity.to_timedelta(i=k)
        if k > 0:
            dt1 = dt3 - periodicity.to_timedelta(i=1)
        if maturity_date is not None and dt3 >= maturity_date > dt2:
            dt3 = maturity_date

    elif freq >= 12:
        return 0
    elif freq == 0:
        freq = 1
        dt3 = dt1 + relativedelta.relativedelta(years=1)
    else:
        dt3 = maturity_date

    if accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_NONE:
        # Case 0  'none
        #     CouponAccrualFactor = 0
        return 0

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_ACT_ACT_ICMA:
        # Case 1  'ACT/ACT
        #     CouponAccrualFactor = (dt2 - dt1) / (dt3 - dt1) / freq
        return (dt2 - dt1).days / (dt3 - dt1).days / freq

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_ACT_ACT_ISDA:
        # Case 100  'ACT/ACT  - ISDA
        #     Ndays1 = DateSerial(y1, 1, 1) - DateSerial(y1, 12, 31)
        #     Ndays2 = DateSerial(y2, 1, 1) - DateSerial(y2, 12, 31)
        #     Y1_leap = Month(DateSerial(Year(dt1), 2, 29)) = 2
        #     Y2_leap = Month(DateSerial(Year(dt2), 2, 29)) = 2
        #     If Y1_leap <> Y2_leap Then
        #         CouponAccrualFactor = (DateSerial(y2, 1, 1) - dt1) / Ndays1 + (dt2 - DateSerial(y2, 1, 1)) / Ndays2
        #     Else
        #         CouponAccrualFactor = (dt2 - dt1) / 365
        #     End If
        ndays1 = (date(dt1.year, 1, 1) - date(dt1.year, 12, 31)).days
        ndays2 = (date(dt2.year, 1, 1) - date(dt2.year, 12, 31)).days
        is_leap1 = calendar.isleap(dt1.year)
        is_leap2 = calendar.isleap(dt2.year)
        if is_leap1 != is_leap2:
            return (date(dt2.year, 1, 1) - dt1).days / ndays1 + (dt2 - date(dt2.year, 1, 1)).days / ndays2
        else:
            return (dt2 - dt1).days / 365

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_ACT_360:
        # Case 2  'ACT/360
        #     CouponAccrualFactor = (dt2 - dt1) / 360
        return (dt2 - dt1).days / 360

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_ACT_365:
        # Case 3  'ACT/365
        #     CouponAccrualFactor = (dt2 - dt1) / 365
        return (dt2 - dt1).days / 365

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_ACT_366:
        # Case 107  'Act/365(366)
        #     If y1 < y2 Then
        #         If (Month(DateSerial(y1, 2, 29)) = 2 Or Month(DateSerial(y2, 2, 29)) = 2) And _
        #                 DateSerial(y1, 2, 29) >= dt1 And DateSerial(y1, 2, 29) <= dt2 Then
        #             CouponAccrualFactor = (dt2 - dt1 + 1) / 366
        #         Else
        #             CouponAccrualFactor = (dt2 - dt1 + 1) / 365
        #         End If
        #     End If
        if dt1.year < dt2.year:
            # TODO: verify
            is_leap1 = calendar.isleap(dt1.year)
            is_leap2 = calendar.isleap(dt2.year)
            if (is_leap1 or is_leap2) and dt1 <= (date(dt1.year, 2, 28) + timedelta(days=1)) <= dt2:
                return ((dt2 - dt1).days + 1) / 366
            else:
                return ((dt2 - dt1).days + 1) / 365
        return 0

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_ACT_365A:
        # Case 104  'Act+1/365
        #     CouponAccrualFactor = (dt2 - dt1 + 1) / 365
        return ((dt2 - dt1).days + 1) / 365

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_30_360_US:
        return _accrual_factor_30_360(dt1, dt2)

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_30_360_GERMAN:
        return _accrual_factor_30_360(dt1, dt2)

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_NL_365:  # 14
        # Case 9  'NL/365
        #     Y1_leap = Month(DateSerial(Year(dt1), 2, 29)) = 2
        #     Y2_leap = Month(DateSerial(Year(dt2), 2, 29)) = 2
        #     k = 0
        #     If Y1_leap And dt1 < DateSerial(Year(dt1), 2, 29) And dt2 >= DateSerial(Year(dt1), 2, 29) Then k = 1
        #     If Y2_leap And dt2 >= DateSerial(Year(dt2), 2, 29) And dt1 < DateSerial(Year(dt2), 2, 29) Then k = 1
        #     CouponAccrualFactor = (dt2 - dt1 - k) / 365
        is_leap1 = calendar.isleap(dt1.year)
        is_leap2 = calendar.isleap(dt2.year)
        k = 0
        if is_leap1 and dt1 < date(dt1.year, 2, 29) <= dt2:
            k = 1
        if is_leap2 and dt2 >= date(dt2.year, 2, 29) > dt1:
            k = 1
        return ((dt2 - dt1).days - k) / 365

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_BD_252:
        # Case 33  'BUS DAYS/252
        #     CouponAccrualFactor = (DateDiff("d", dt1, dt2) - DateDiff("ww", dt1, dt2, vbSaturday) - _
        #         DateDiff("ww", dt1, dt2, vbSunday)) / 252
        return ((dt2 - dt1).days - weekday(dt1, dt2, rrule.SA) - weekday(dt1, dt2, rrule.SU)) / 252

    elif (
        accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_30_360_ISDA
        or accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_30E_360
    ):
        # 11 & 28
        # Case 35  'GERMAN-30/360 (EOM)
        #     If IsNull(MaturityDate) Then
        #         CouponAccrualFactor = 0
        #         Exit Function
        #     End If
        #     lastDay1 = Month(dt1 + 1) = (Month(dt1) + 1)
        #     lastDay2 = Month(dt1 + 1) = (Month(dt1) + 1)
        #     If lastDay1 Then d1 = 30
        #     If lastDay2 And Not ((dt2 = MaturityDate) And Month(dt2) = 2) Then d2 = 30
        #     CouponAccrualFactor = ((y2 - y1) * 360 + (M2 - M1) * 30 + (d2 - d1)) / 360
        if maturity_date is None:
            return 0
        d1 = dt1.day
        d2 = dt2.day
        last_day1 = (dt1 + timedelta(days=1)).month == (dt1.month + 1)
        last_day2 = (dt2 + timedelta(days=1)).month == (dt2.month + 1)
        if last_day1:
            d1 = 30
        if last_day2 and (dt2 != maturity_date or dt2.month != 2):
            d2 = 30
        return ((dt2.year - dt1.year) * 360 + (dt2.month - dt1.month) * 30 + (d2 - d1)) / 360

    else:
        err_msg = f"unknown accrual_calculation_model.id={accrual_calculation_model.id}"
        _l.error(f"coupon_accrual_factor - {err_msg}")
        raise FormulaAccrualsError(
            error_key="coupon_accrual_factor",
            message=err_msg,
        )


def _accrual_factor_30_360(dt1, dt2):
    # Case 5  '30/360
    #     If d1 = 31 Then d1 = 30
    #     If d2 = 31 And (d1 = 30 Or d1 = 31) Then d2 = 30
    #     CouponAccrualFactor = ((y2 - y1) * 360 + (M2 - M1) * 30 + (d2 - d1)) / 360
    d1 = dt1.day
    d2 = dt2.day
    if d1 == 31:
        d1 = 30
    if d2 == 31 and d1 in (30, 31):
        d2 = 30
    return ((dt2.year - dt1.year) * 360 + (dt2.month - dt1.month) * 30 + (d2 - d1)) / 360


def get_coupon(accrual, dt1, dt2, maturity_date=None, factor=False):
    # accruals = [
    #     {
    #         'accrual_start_date': '2001-01-01',
    #         'first_payment_date': '2001-07-01',
    #         'accrual_size': 10,
    #         'accrual_calculation_model': 'ISMA_30_360_NO_EOM',
    #         'periodicity': 'SEMI_ANNUALLY',
    #     },
    #     {
    #         'accrual_start_date': '2003-01-01',
    #         'first_payment_date': '2003-07-01',
    #         'accrual_size': 20,
    #         'accrual_calculation_model': 'ISMA_30_360_NO_EOM',
    #         'periodicity':'SEMI_ANNUALLY',
    #     }
    # ]
    # maturity_date = '2005-01-01'
    # maturity_price = 100
    # cpns = (
    #     '2001-07-01', 5, # used accrual[0], first_payment_date
    #     '2002-01-01', 5, # used accrual[0], first_payment_date + interval
    #     '2002-07-01', 5, # used accrual[0], first_payment_date + interval * 2
    #     '2003-01-01', 5, # used accrual[0], first_payment_date + interval * 3
    #
    #     '2003-07-01', 10, # used accrual[1], first_payment_date
    #     '2004-01-01', 10, # used accrual[1], first_payment_date + interval
    #     '2004-07-01', 10, # used accrual[1], first_payment_date + interval * 2
    #
    #     '2005-01-01', 100, # maturity_date, maturity_price
    # )
    #
    #
    #
    # accruals = [
    #     {
    #         'accrual_start_date': '2001-01-01',
    #         'first_payment_date': '2001-07-01',
    #         'accrual_size': 10,
    #         'accrual_calculation_model': 'ISMA_30_360_NO_EOM',
    #         'periodicity': 'SEMI_ANNUALLY',
    #     },
    #     {
    #         'accrual_start_date': '2003-02-01',
    #         'first_payment_date': '2004-01-01',
    #         'accrual_size': 20,
    #         'accrual_calculation_model': 'ISMA_30_360_NO_EOM',
    #         'periodicity':'ANNUALLY',
    #     }
    # ]
    # maturity_date = '2007-02-01'
    # maturity_price = 100
    # cpns = (
    #     '2001-07-01', 5, # used accrual[0], first_payment_date
    #     '2002-01-01', 5, # used accrual[0], first_payment_date + interval
    #     '2002-07-01', 5, # used accrual[0], first_payment_date + interval * 2
    #     '2003-01-01', 5, # used accrual[0], first_payment_date + interval * 3
    #
    #     '2004-01-01', 20, # used accrual[1], first_payment_date
    #     '2005-01-01', 20, # used accrual[1], first_payment_date + interval
    #     '2006-01-01', 20, # used accrual[1], first_payment_date + interval * 2
    #     '2007-01-01', 20, # used accrual[1], first_payment_date + interval * 2
    #
    #     '2007-02-01', 100, # maturity_date, maturity_price
    # )

    # Пример 1
    #
    # '2001-07-01', 5, # used accrual[0], first_payment_date
    # '2002-01-01', 5, # used accrual[0], first_payment_date + interval
    # '2002-07-01', 5, # used accrual[0], first_payment_date + interval * 2
    # '2002-12-31', 4.9.., #
    #
    # '2003-07-01', 10, # used accrual[1], first_payment_date
    # '2004-01-01', 10, # used accrual[1], first_payment_date + interval
    # '2004-07-01', 10, # used accrual[1], first_payment_date + interval * 2
    # '2005-07-01', 10,
    #
    # '2005-01-01', 100, # maturity_date, maturity_price
    #
    # Пример 2
    #
    # '2001-07-01', 5, # used accrual[0], first_payment_date
    # '2002-01-01', 5, # used accrual[0], first_payment_date + interval
    # '2002-07-01', 5, # used accrual[0], first_payment_date + interval * 2
    # '2003-01-01', 5, # used accrual[0], first_payment_date + interval * 3
    # '2003-01-31', 5*1/6,
    #
    # '2004-01-01', 20*11/12, # used accrual[1], first_payment_date
    # '2005-01-01', 20, # used accrual[1], first_payment_date + interval
    # '2006-01-01', 20, # used accrual[1], first_payment_date + interval * 2
    # '2007-01-01', 20, # used accrual[1], first_payment_date + interval * 2
    # '2007-02-01', 20*1/12,
    #
    # '2007-02-01', 100, # maturity_date, maturity_price

    # GetCoupon – имя функции, куда записывается результат вычислений
    # Dt1 – предыдущая купонная дата или Accrual start Date, если это первый купон из текущей строчки
    # Accrual Schedule  (т.е. если в Accrual Schedule 2 строчки, например один период Accrual Size был 5,
    # а потом стал 10, то для расчета первого купона с Accrual Size = 10 используем Accrual Start Date из 2-ой строчки,
    # но не дату выплаты последнего купона = 5)
    #
    # Dt2 – текущая купонная дата
    #
    # If Not CpnDate Then
    #     GetCoupon = 0
    #     Exit Function
    # Else
    #
    #    d1 = Day(dt1)
    #    M1 = Month(dt1)
    #    y1 = Year(dt1)
    #    d2 = Day(dt2)
    #    M2 = Month(dt2)
    #    y2 = Year(dt2)

    from poms.instruments.models import AccrualCalculationModel

    accrual_calculation_model = accrual.accrual_calculation_model

    try:
        cpn = float(accrual.accrual_size)
    except Exception:
        cpn = 0.0

    if factor:
        cpn = 1.0

    periodicity = accrual.periodicity
    freq = periodicity.to_freq()
    # dt3 = accrual.first_payment_date
    # dt3 = datetime.date(datetime.strptime(accrual.first_payment_date, "%Y-%m-%d"))

    d1 = dt1.day
    m1 = dt1.month
    y1 = dt1.year
    d2 = dt2.day
    m2 = dt2.month
    y2 = dt2.year

    # Select Case day_convention_code
    if accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_NONE:
        #     Case 0  '
        #         GetCoupon = 0
        return 0

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_ACT_ACT_ICMA:
        #     Case 1  'ACT/ACT
        #         GetCoupon = CPN / freq
        return cpn / freq

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_ACT_360:
        #     Case 2  'ACT/360
        #         GetCoupon = CPN * (dt2 - dt1) / 360
        return cpn * (dt2 - dt1).days / 360

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_ACT_364:
        #     Case 3  'ACT/365
        #         GetCoupon = CPN * (dt2 - dt1) / 365
        return cpn * (dt2 - dt1).days / 365

        # elif accrual_calculation_model.id == AccrualCalculationModel.:
        # #     Case 4  '30/ACT
        # #         GetCoupon = Null
        # return 0

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_30_360_US:
        #     Case 5  '30/360
        #         If d1 = 31 Then d1 = 30
        #         If d2 = 31 And (d1 = 30 Or d1 = 31) Then d2 = 30
        #         GetCoupon = CPN * ((y2 - y1) * 360 + (M2 - M1) * 30 + (d2 - d1)) / 360
        if d1 == 31:
            d1 = 30
        if d2 == 31 and d1 in (30, 31):
            d2 = 30
        return cpn * ((y2 - y1) * 360 + (m2 - m1) * 30 + (d2 - d1)) / 360

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_NL_365:
        #     Case 9  'NL/365
        #         Y1_leap = Month(DateSerial(Year(dt1), 2, 29)) = 2  ‘ check if dt1 lying in leap year
        #         Y2_leap = Month(DateSerial(Year(dt2), 2, 29)) = 2  ‘check if dt2 lying in leap year
        #         Ndays1 = 0
        #         If Y1_leap And dt1 < DateSerial(Year(dt1), 2, 29) And dt2 >= DateSerial(Year(dt1), 2, 29) Then Ndays1 = 1
        #         If Y2_leap And dt2 >= DateSerial(Year(dt2), 2, 29) And dt1 < DateSerial(Year(dt2), 2, 29) Then Ndays1 = 1
        #         GetCoupon = CPN * (dt2 - dt1 - Ndays1) / 365
        is_leap1 = calendar.isleap(dt1.year)
        is_leap2 = calendar.isleap(dt2.year)
        ndays1 = 0
        if is_leap1 and dt1 < date(y1, 2, 29) and dt2 >= date(y1, 2, 29):
            ndays1 = 1
        if is_leap2 and dt2 >= date(y2, 2, 29) and dt1 < date(y2, 2, 29):
            ndays1 = 1
        return cpn * ((dt2 - dt1).days - ndays1) / 365

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_BD_252:
        #     Case 33  'BUS DAYS/252
        #         GetCoupon = CPN * (DateDiff("d", dt1, dt2) - DateDiff("ww", dt1, dt2, vbSaturday) - _
        #             DateDiff("d", dt1, dt2, vbSunday)) / 252
        return cpn * ((dt2 - dt1).days - weekday(dt1, dt2, rrule.SA) - weekday(dt1, dt2, rrule.SU)) / 252

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_30_360_ISDA:
        #     Case 35  'GERMAN-30/360 (EOM)
        #         If IsNull(MaturityDate) Then
        #             AddCoupon = 0
        #             Exit Function
        #         End If
        #         lastDay1 = Month(dt1 + 1) = (Month(dt1) + 1)
        #         lastDay2 = Month(dt1 + 1) = (Month(dt1) + 1)
        #         If lastDay1 Then d1 = 30
        #         If lastDay2 And Not ((dt2 = MaturityDate) And Month(dt2) = 2) Then d2 = 30
        #         GetCoupon = CPN * ((y2 - y1) * 360 + (M2 - M1) * 30 + (d2 - d1)) / 360
        if maturity_date is None:
            return 0
        last_day1 = (dt1 + timedelta(days=1)).month == (dt1.month + 1)
        last_day2 = (dt2 + timedelta(days=1)).month == (dt2.month + 1)
        if last_day1:
            d1 = 30
        if last_day2 and (dt2 != maturity_date or dt2.month != 2):
            d2 = 30
        return cpn * ((y2 - y1) * 360 + (m2 - m1) * 30 + (d2 - d1)) / 360

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_30_360_GERMAN:
        #     Case 38  'GERMAN-30/360 (NO EOM)
        #         If IsNull(MaturityDate) Then
        #             AddCoupon = 0
        #             Exit Function
        #         End If
        #         lastDay1 = Month(dt1 + 1) = (Month(dt1) + 1)
        #         lastDay2 = Month(dt1 + 1) = (Month(dt1) + 1)
        #         If lastDay1 Then d1 = 30
        #         If lastDay2 And Not ((dt2 = MaturityDate) And Month(dt2) = 2) Then d2 = 30
        #         GetCoupon = CPN * ((y2 - y1) * 360 + (M2 - M1) * 30 + (d2 - d1)) / 360
        if maturity_date is None:
            return 0

        d1 = dt1.day
        d2 = dt2.day
        last_day1 = (dt1 + timedelta(days=1)).month == (dt1.month + 1)
        last_day2 = (dt2 + timedelta(days=1)).month == (dt2.month + 1)
        if last_day1:
            d1 = 30
        if last_day2 and (dt2 != maturity_date or dt2.month != 2):
            d2 = 30
        return cpn * ((y2 - y1) * 360 + (m2 - m1) * 30 + (d2 - d1)) / 360

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_ACT_ACT_ISDA:
        #     Case 100  'ACT/ACT  - ISDA
        #         Ndays1 = DateSerial(y1, 1, 1) - DateSerial(y1, 12, 31)
        #         Ndays2 = DateSerial(y2, 1, 1) - DateSerial(y2, 12, 31)
        #         Y1_leap = Month(DateSerial(Year(dt1), 2, 29)) = 2
        #         Y2_leap = Month(DateSerial(Year(dt2), 2, 29)) = 2
        #         If Y1_leap <> Y2_leap Then
        #             GetCoupon = CPN * (DateSerial(y2, 1, 1) - dt1) / Ndays1 + (dt2 - DateSerial(y2, 1, 1)) / Ndays2
        #         Else
        #             GetCoupon = CPN * (dt2 - dt1) / 365
        #         End If
        ndays1 = (date(dt1.year, 1, 1) - date(dt1.year, 12, 31)).days
        ndays2 = (date(dt2.year, 1, 1) - date(dt2.year, 12, 31)).days
        is_leap1 = calendar.isleap(dt1.year)
        is_leap2 = calendar.isleap(dt2.year)
        if is_leap1 != is_leap2:
            return cpn * ((date(dt2.year, 1, 1) - dt1).days / ndays1 + (dt2 - date(dt2.year, 1, 1)).days / ndays2)
        else:
            return cpn * (dt2 - dt1).days / 365

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_30E_PLUS_360:
        #     Case 101  '30E+/360
        #         If d1 = 31 Then d1 = 30
        #         If d2 = 31 Then
        #         M2 = M2 + 1
        #         d2 = 1
        #         End If
        #         GetCoupon = CPN * ((y2 - y1) * 360 + (M2 - M1) * 30 + (d2 - d1)) / 360
        if d1 == 31:
            d1 = 30
        if d2 == 31:
            m2 += 1
            d2 = 1
        return cpn * ((y2 - y1) * 360 + (m2 - m1) * 30 + (d2 - d1)) / 360

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_ACT_365A:
        #     Case 105  'Act+1/360
        #         GetCoupon = CPN * (dt2 - dt1 + 1) / 360
        return cpn * ((dt2 - dt1).days + 1) / 360

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_ACT_365L:
        #     Case 107  'Act/365(366)
        #         If y1 < y2 Then
        #             If (Month(DateSerial(y1, 2, 29)) = 2 Or Month(DateSerial(y2, 2, 29)) = 2) And _
        #                 DateSerial(y1, 2, 29) >= dt1 And DateSerial(y1, 2, 29) <= dt2 Then
        #                 GetCoupon = CPN * (dt2 - dt1 + 1) / 366
        #             Else
        #                 AddCoupon = CPN * (dt2 - dt1 + 1) / 365
        #             End If
        #         End If
        if dt1.year < dt2.year:
            # TODO: verify
            is_leap1 = calendar.isleap(dt1.year)
            is_leap2 = calendar.isleap(dt2.year)
            if (is_leap1 or is_leap2) and dt1 <= (date(y1, 2, 28) + timedelta(days=1)) <= dt2:
                return cpn * ((dt2 - dt1).days + 1) / 366
            else:
                return cpn * ((dt2 - dt1).days + 1) / 365

        return 0

    else:
        err_msg = f"unknown accrual_calculation_model.id={accrual_calculation_model.id}"
        _l.error(f"get_coupon {err_msg}")
        raise FormulaAccrualsError(
            error_key="get_coupon",
            message=err_msg,
        )


# def weeks_fast(dt1, dt2, byweekday):
#     print(-10, dt1, dt1.strftime('%A'), ' - ', dt2, dt2.strftime('%A'), byweekday)
#
#     td = relativedelta.relativedelta(weekday=byweekday)
#
#     dt1w = dt1 + td
#     dt2w = dt2 + td
#
#     count = int((dt2 - dt1).days / 7)
#
#     if dt2w > dt2:
#         count -= 1
#     if dt2w == dt2:
#         count += 1
#
#     print(-11, count)
#
#     return count


def weekday(dt1, dt2, byweekday):
    return sum(1 for _ in rrule.rrule(rrule.WEEKLY, dtstart=dt1, until=dt2, byweekday=byweekday))

# OLD VERSION
# def f_xnpv(data, rate):
#     """Equivalent of Excel's XNPV function.
#     https://support.office.com/en-us/article/XNPV-function-1b42bbf6-370f-4532-a0eb-d67c16b664b7
#
#     from datetime import date
#     dates = [date(2016, 2, 16), date(2016, 3, 10), date(2016, 9, 1), date(2017, 1, 17),]
#     values = [-90, 5, 5, 105, ]
#     data = [(d, v) for d, v in zip(dates, values)]
#     f_xnpv(0.09, data)
#     16.7366702148651
#     """
#     # _l.debug('xnpv > rate=%s', rate)
#     if not data:
#         return 0.0
#
#     if rate <= -1.0:
#         return float("inf")
#     d0, v0 = data[0]  # or min(dates)
#
#     # for di, vi in data:
#     #     _l.debug('f_xnpv: di=%s, vi=%s 1rate=%s, days=%s, exp=%s',
#     #              di, vi, (1.0 + rate), (di - d0).days, ((di - d0).days / 365.0) )
#     #     try:
#     #         _l.debug('    res=%s', vi / ((1.0 + rate) ** ((di - d0).days / 365.0)))
#     #     except Exception as e:
#     #         _l.debug('    res=%s', repr(e))
#
#     try:
#         return sum(vi / ((1.0 + rate) ** ((di - d0).days / 365.0)) for di, vi in data)
#     except (OverflowError, ZeroDivisionError):
#         return 0.0


def f_xnpv(data, rate):
    """Calculate the Net Present Value for irregular cash flows."""
    if rate == -1:
        return float("inf")  # Avoid division by zero

    npv = 0.0
    start_date = data[0][0]  # Use the first date as the base date
    for d, value in data:
        days = (d - start_date).days / 365.0  # Convert days to years
        npv += value / ((1 + rate) ** days)
    return npv


def f_xirr(data, x0=0.0, tol=0.000001, maxiter=100):
    """Calculate the XIRR (Internal Rate of Return) for irregular cash flows."""
    if not data:
        return 0.0

    # Newton-Raphson iteration
    rate = x0
    epsilon = 1e-5
    for _ in range(maxiter):
        npv = f_xnpv(data, rate)
        # Calculate the derivative (approximate derivative using finite difference)

        npv_derivative = (f_xnpv(data, rate + epsilon) - npv) / epsilon

        # Avoid division by zero if the derivative is very small
        if abs(npv_derivative) < tol:
            return 0.0

        # Update the rate using Newton-Raphson
        new_rate = rate - npv / npv_derivative

        # Check for convergence
        if abs(new_rate - rate) < tol:
            return new_rate

        rate = new_rate

    # If the method fails to converge, return 0.0
    return 0.0


# def f_duration(data, ytm=None):
#     """Equivalent of Excel's XIRR function.
#     https://support.office.com/en-us/article/XIRR-function-de1242ec-6477-445b-b11b-a303ad9adc9d
#
#     from datetime import date
#     dates = [date(2016, 2, 16), date(2016, 3, 10), date(2016, 9, 1), date(2017, 1, 17), ]
#     values = [-90, 5, 5, 105, ]
#     data = [(d, v) for d, v in zip(dates, values)]
#     f_xirr(data)
#     0.6438341602180792
#     """
#     # _l.debug('duration >')
#
#     if not data:
#         return 0.0
#
#     if ytm is None:
#         ytm = f_xirr(data)
#     d0, v0 = data[0]
#     v0 = -v0
#
#     try:
#         return (
#             sum(
#                 ((di - d0).days / 365.0)
#                 * (vi / ((1.0 + ytm) ** ((di - d0).days / 365.0)))
#                 for di, vi in data
#             )
#             / v0
#             / (1 + ytm)
#         )
#     except (OverflowError, ZeroDivisionError):
#         return 0.0


if __name__ == "__main__":
    # noinspection PyUnresolvedReferences
    import django
    from django.db import transaction

    from poms.instruments.models import (
        AccrualCalculationModel,
        AccrualCalculationSchedule,
        Instrument,
        Periodicity,
    )
    from poms.users.models import MasterUser

    django.setup()

    # print('1 -> ', coupon_accrual_factor(
    #     accrual_calculation_model=AccrualCalculationModel.NONE,
    #     freq=12,
    #     dt1=date(2016, 1, 1),
    #     dt2=date(2016, 1, 15),
    #     dt3=date(2016, 2, 1),
    #     maturity_date=date(2016, 12, 31)
    # ))
    # d0 = date(2016, 2, 29)
    # d1 = date(2016, 1, 31)
    # d2 = date(2016, 2, 11)
    # d3 = date(2016, 3, 3)
    # for d in [d0, d1, d2, d3]:
    #     print(d, d.strftime('%A'))
    #
    # print('-' * 10)
    # for periodicity in Periodicity.objects.all():
    #     d = d0
    #     td0 = periodicity.to_timedelta(n=0, i=1, same_date=d)
    #     td1 = periodicity.to_timedelta(n=1, i=1, same_date=d)
    #     td2 = periodicity.to_timedelta(n=2, i=1, same_date=d)
    #     print(0, periodicity.id, periodicity.system_code, td0, td1, td2)
    #     print('\t', d + td0, d + td1, d + td2)
    #
    # print('-' * 10)
    # print(101, 'd2 - d1', d2 - d1)
    # print(102, 'd2 - d1', relativedelta.relativedelta(d2, d1))
    # print(103, 'd3 - d1', relativedelta.relativedelta(d3, d1))
    # print(104, relativedelta.relativedelta(date(2016, 1, 1), date(2016, 1, 12)))
    #
    # print('-' * 10)
    # print(200, d1 + relativedelta.relativedelta(days=5))
    # print(201, d1 + relativedelta.relativedelta(days=5, weekday=relativedelta.MO))
    # print(202, d1 + relativedelta.relativedelta(days=20, weekday=relativedelta.MO))
    # print(203, d1 + relativedelta.relativedelta(days=5, weekday=relativedelta.MO) +
    #       relativedelta.relativedelta(days=5, weekday=relativedelta.MO) +
    #       relativedelta.relativedelta(days=5, weekday=relativedelta.MO) +
    #       relativedelta.relativedelta(days=5, weekday=relativedelta.MO))
    # print(204, d1 + relativedelta.relativedelta(day=31))
    # print(205, d1 + relativedelta.relativedelta(months=1, day=31))
    #
    # print('-' * 10)
    # print(300, [d.date().isoformat() for d in rrule.rrule(dtstart=d1, count=4, freq=rrule.WEEKLY)])
    # print(300, [d.date().isoformat() for d in rrule.rrule(dtstart=d1, count=4, freq=rrule.WEEKLY,
    #                                                       byweekday=[rrule.FR])])
    #
    # print(301, [d.date().isoformat() for d in rrule.rrule(dtstart=d1, count=4, freq=rrule.MONTHLY)])
    #
    # print(302, [d.date().isoformat() for d in rrule.rrule(dtstart=d1, count=7, freq=rrule.DAILY)])
    # print(303, [d.date().isoformat() for d in rrule.rrule(dtstart=d1, count=7, freq=rrule.DAILY,
    #                                                       byweekday=[rrule.FR])])
    # print(304, [d.date().isoformat() for d in rrule.rrule(dtstart=d1, count=7, freq=rrule.DAILY,
    #                                                       byweekday=[rrule.MO, rrule.TU, rrule.WE, rrule.TH,
    #                                                                  rrule.FR])])
    # print(305, [d.date().isoformat() for d in rrule.rrule(dtstart=d1, count=4, freq=rrule.MONTHLY,
    #                                                       bymonthday=[31], bysetpos=-1)])
    #
    # print('-' * 10)
    # print(401, weekday(date(2016, 1, 31), date(2016, 2, 14), rrule.SU))
    # print(402, weekday(date(2016, 1, 31), date(2016, 2, 13), rrule.SU))
    # print(403, weekday(date(2016, 2, 1), date(2016, 2, 14), rrule.SU))
    # print(404, weekday(date(2016, 2, 1), date(2016, 2, 13), rrule.SU))
    #
    # print(411, weekday(date(2016, 1, 31), date(2016, 2, 14), rrule.SA))
    # print(412, weekday(date(2016, 1, 31), date(2016, 2, 13), rrule.SA))
    # print(413, weekday(date(2016, 2, 1), date(2016, 2, 14), rrule.SA))
    # print(414, weekday(date(2016, 2, 1), date(2016, 2, 13), rrule.SA))
    #
    # print('-' * 10)
    # print(500, coupon_accrual_factor(
    #     accrual_calculation_model=AccrualCalculationModel.objects.get(pk=AccrualCalculationModel.ACT_ACT),
    #     periodicity=Periodicity.objects.get(pk=Periodicity.MONTHLY),
    #     dt1=date(2016, 1, 1),
    #     dt2=date(2016, 3, 31),
    #     dt3=date(2016, 2, 1),
    #     maturity_date=date.max
    # ))
    # s = datetime.utcnow()
    # count = 0
    # for d in rrule.rrule(dtstart=date.min, until=date.max, freq=rrule.MONTHLY):
    #     count += 1
    # print(400, date.min, date.max, count, datetime.utcnow() - s)
    # s = datetime.utcnow()
    # sd = date.min
    # count = 0
    # while True:
    #     try:
    #         d = sd + relativedelta.relativedelta(days=count)
    #     except ValueError:
    #         break
    #     count += 1
    #     if d >= date.max:
    #         break
    # print(401, date.min, date.max, count, datetime.utcnow() - s)
    # i = Instrument.objects.get(pk=19)
    # _l.debug('> instr_accrual: instr=%s', i.id)
    # d = date(2016, 4, 7)
    # instr_accrual = i.find_accrual(d)
    # _l.debug('< instr_accrual: %s', instr_accrual)
    # if instr_accrual:
    #     _l.debug('> instr_accrual_accrued_price: instr=%s', i.id)
    #     instr_accrual_accrued_price = i.get_accrued_price(d, accrual=instr_accrual)
    #     _l.debug('< instr_accrual_accrued_price: %s', instr_accrual_accrued_price)

    def _test_ytm():
        dates = [
            date(2016, 2, 16),
            date(2016, 3, 10),
            date(2016, 9, 1),
            date(2017, 1, 17),
        ]
        values = [
            -90,
            5,
            5,
            105,
        ]
        data = [(d, v) for d, v in zip(dates, values)]
        _l.debug("data: %s", [(str(d), v) for d, v in data])
        _l.debug("xirr: %s", f_xirr(data))

        _l.debug("https://support.office.com/en-us/article/XIRR-function-de1242ec-6477-445b-b11b-a303ad9adc9d")
        dates = [
            date(2008, 1, 1),
            date(2008, 3, 1),
            date(2008, 10, 30),
            date(2009, 2, 15),
            date(2009, 4, 1),
        ]
        values = [
            -10000,
            2750,
            4250,
            3250,
            2750,
        ]
        data = [(d, v) for d, v in zip(dates, values)]
        _l.debug("data: %s", [(str(d), v) for d, v in data])
        _l.debug("xirr: %s", f_xirr(data))
        _l.debug("xirr: %s <- from MS", 0.373362535)

        # trn
        data = [(date(2017, 1, 27), -1.0), (date(2019, 9, 30), 1.0)]
        _l.debug("data: %s", [(str(d), v) for d, v in data])
        _l.debug("xirr: %s", f_xirr(data, x0=1.0))
        # item
        data = [(date(2017, 2, 3), -1.00857), (date(2019, 9, 30), 1.0)]
        _l.debug("data: %s", [(str(d), v) for d, v in data])
        _l.debug("xirr: %s", f_xirr(data, x0=0.0))

    _test_ytm()
    pass

    @transaction.atomic()
    def _test_coupons():
        try:
            master_user = MasterUser.objects.get(pk=1)
            usd = master_user.currencies.get(user_code="USD")
            i = Instrument.objects.create(
                master_user=master_user,
                instrument_type=master_user.instrument_type,
                name="i1",
                pricing_currency=usd,
                accrued_currency=usd,
            )

            _l.debug("-" * 10)
            accruals = [
                AccrualCalculationSchedule.objects.create(
                    instrument=i,
                    accrual_start_date=date(2001, 1, 1),
                    first_payment_date=date(2001, 7, 1),
                    accrual_size=10,
                    accrual_calculation_model=AccrualCalculationModel.objects.get(
                        pk=AccrualCalculationModel.DAY_COUNT_ACT_360
                    ),
                    periodicity=Periodicity.objects.get(pk=Periodicity.SEMI_ANNUALLY),
                ),
                AccrualCalculationSchedule.objects.create(
                    instrument=i,
                    accrual_start_date=date(2003, 1, 1),
                    first_payment_date=date(2003, 7, 1),
                    accrual_size=20,
                    accrual_calculation_model=AccrualCalculationModel.objects.get(
                        pk=AccrualCalculationModel.DAY_COUNT_ACT_360
                    ),
                    periodicity=Periodicity.objects.get(pk=Periodicity.SEMI_ANNUALLY),
                ),
            ]
            i.maturity_date = date(2005, 1, 1)
            i.maturity_price = 100
            i.save()

            sd = accruals[0].accrual_start_date - timedelta(days=4)
            ed = i.maturity_date + timedelta(days=4)
            cpn_date = sd
            while cpn_date <= ed:
                # _l.debug('%s', cpn_date)
                cpn_val, is_cpn = i.get_coupon(cpn_date=cpn_date)
                if is_cpn:
                    _l.debug("    %s - %s (is_cpn=%s)", cpn_date, cpn_val, is_cpn)
                cpn_date += timedelta(days=1)

            _l.debug(
                "get_future_coupons: %s",
                [(str(d), v) for d, v in i.get_future_coupons(begin_date=date(2000, 1, 1))],
            )
            _l.debug(
                "get_future_coupons: %s",
                [(str(d), v) for d, v in i.get_future_coupons(begin_date=date(2007, 1, 1))],
            )

            for d, v in i.get_future_coupons(begin_date=date(2000, 1, 1)):
                _l.debug("get_coupon: %s - %s", d, i.get_coupon(d))

            i = Instrument.objects.create(
                master_user=master_user,
                instrument_type=master_user.instrument_type,
                name="i2",
                pricing_currency=usd,
                accrued_currency=usd,
            )
            _l.debug("-" * 10)
            accruals = [
                AccrualCalculationSchedule.objects.create(
                    instrument=i,
                    accrual_start_date=date(2001, 1, 1),
                    first_payment_date=date(2001, 7, 1),
                    accrual_size=10,
                    accrual_calculation_model=AccrualCalculationModel.objects.get(
                        pk=AccrualCalculationModel.DAY_COUNT_ACT_360
                    ),
                    periodicity=Periodicity.objects.get(pk=Periodicity.SEMI_ANNUALLY),
                ),
                AccrualCalculationSchedule.objects.create(
                    instrument=i,
                    accrual_start_date=date(2003, 2, 1),
                    first_payment_date=date(2004, 1, 1),
                    accrual_size=20,
                    accrual_calculation_model=AccrualCalculationModel.objects.get(
                        pk=AccrualCalculationModel.DAY_COUNT_ACT_360
                    ),
                    periodicity=Periodicity.objects.get(pk=Periodicity.ANNUALLY),
                ),
            ]
            i.maturity_date = date(2007, 2, 1)
            i.maturity_price = 100
            i.save()

            sd = accruals[0].accrual_start_date - timedelta(days=4)
            ed = i.maturity_date + timedelta(days=4)
            cpn_date = sd
            while cpn_date <= ed:
                # _l.debug('%s', cpn_date)
                cpn_val, is_cpn = i.get_coupon(cpn_date=cpn_date)
                if is_cpn:
                    _l.debug("    %s - %s (is_cpn=%s)", cpn_date, cpn_val, is_cpn)
                cpn_date += timedelta(days=1)

            _l.debug(
                "get_future_coupons: %s",
                [(str(d), v) for d, v in i.get_future_coupons(begin_date=date(2000, 1, 1))],
            )
        finally:
            transaction.set_rollback(True)

    _test_coupons()
