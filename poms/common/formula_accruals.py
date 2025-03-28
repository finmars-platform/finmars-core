import calendar
import logging
from datetime import date, timedelta

from dateutil import relativedelta, rrule

from poms.common.exceptions import FinmarsBaseException

_l = logging.getLogger("poms.common")


class FormulaAccrualsError(FinmarsBaseException):
    pass


def weekday(dt1, dt2, byweekday):
    return sum(1 for _ in rrule.rrule(rrule.WEEKLY, dtstart=dt1, until=dt2, byweekday=byweekday))


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

    if accrual_calculation_model is None or periodicity is None or dt1 is None or dt2 is None or dt3 is None:
        return 0

    freq = periodicity.to_freq()

    if 0 < freq <= 12:
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
        return 0

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_ACT_ACT_ICMA:
        return (dt2 - dt1).days / (dt3 - dt1).days / freq

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_ACT_ACT_ISDA:
        ndays1 = (date(dt1.year, 1, 1) - date(dt1.year, 12, 31)).days
        ndays2 = (date(dt2.year, 1, 1) - date(dt2.year, 12, 31)).days
        is_leap1 = calendar.isleap(dt1.year)
        is_leap2 = calendar.isleap(dt2.year)
        if is_leap1 != is_leap2:
            return (date(dt2.year, 1, 1) - dt1).days / ndays1 + (dt2 - date(dt2.year, 1, 1)).days / ndays2
        else:
            return (dt2 - dt1).days / 365

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_ACT_360:
        return (dt2 - dt1).days / 360

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_ACT_365:
        return (dt2 - dt1).days / 365

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_ACT_366:
        if dt1.year < dt2.year:
            is_leap1 = calendar.isleap(dt1.year)
            is_leap2 = calendar.isleap(dt2.year)
            if (is_leap1 or is_leap2) and dt1 <= (date(dt1.year, 2, 28) + timedelta(days=1)) <= dt2:
                return ((dt2 - dt1).days + 1) / 366
            else:
                return ((dt2 - dt1).days + 1) / 365
        return 0

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_ACT_365A:
        return ((dt2 - dt1).days + 1) / 365

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_30_360_US:
        return _accrual_factor_30_360(dt1, dt2)

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_30_360_GERMAN:
        return _accrual_factor_30_360(dt1, dt2)

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_NL_365:  # 14
        is_leap1 = calendar.isleap(dt1.year)
        is_leap2 = calendar.isleap(dt2.year)
        k = 0
        if is_leap1 and dt1 < date(dt1.year, 2, 29) <= dt2:
            k = 1
        if is_leap2 and dt2 >= date(dt2.year, 2, 29) > dt1:
            k = 1
        return ((dt2 - dt1).days - k) / 365

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_BD_252:
        return ((dt2 - dt1).days - weekday(dt1, dt2, rrule.SA) - weekday(dt1, dt2, rrule.SU)) / 252

    elif accrual_calculation_model.id in (
        AccrualCalculationModel.DAY_COUNT_30_360_ISDA,
        AccrualCalculationModel.DAY_COUNT_30E_360,
    ):
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
    d1 = dt1.day
    d2 = dt2.day
    if d1 == 31:
        d1 = 30
    if d2 == 31 and d1 in (30, 31):
        d2 = 30
    return ((dt2.year - dt1.year) * 360 + (dt2.month - dt1.month) * 30 + (d2 - d1)) / 360


def get_coupon(accrual, dt1, dt2, maturity_date=None, factor=False):
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

    d1 = dt1.day
    m1 = dt1.month
    y1 = dt1.year
    d2 = dt2.day
    m2 = dt2.month
    y2 = dt2.year

    # Select Case day_convention_code
    if accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_NONE:
        return 0

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_ACT_ACT_ICMA:
        return cpn / freq

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_ACT_360:
        return cpn * (dt2 - dt1).days / 360

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_ACT_364:
        return cpn * (dt2 - dt1).days / 365

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_30_360_US:
        if d1 == 31:
            d1 = 30
        if d2 == 31 and d1 in (30, 31):
            d2 = 30
        return cpn * ((y2 - y1) * 360 + (m2 - m1) * 30 + (d2 - d1)) / 360

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_NL_365:
        is_leap1 = calendar.isleap(dt1.year)
        is_leap2 = calendar.isleap(dt2.year)
        ndays1 = 0
        if is_leap1 and dt1 < date(y1, 2, 29) and dt2 >= date(y1, 2, 29):
            ndays1 = 1
        if is_leap2 and dt2 >= date(y2, 2, 29) and dt1 < date(y2, 2, 29):
            ndays1 = 1
        return cpn * ((dt2 - dt1).days - ndays1) / 365

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_BD_252:
        return cpn * ((dt2 - dt1).days - weekday(dt1, dt2, rrule.SA) - weekday(dt1, dt2, rrule.SU)) / 252

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_30_360_ISDA:
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
        ndays1 = (date(dt1.year, 1, 1) - date(dt1.year, 12, 31)).days
        ndays2 = (date(dt2.year, 1, 1) - date(dt2.year, 12, 31)).days
        is_leap1 = calendar.isleap(dt1.year)
        is_leap2 = calendar.isleap(dt2.year)
        if is_leap1 != is_leap2:
            return cpn * ((date(dt2.year, 1, 1) - dt1).days / ndays1 + (dt2 - date(dt2.year, 1, 1)).days / ndays2)
        else:
            return cpn * (dt2 - dt1).days / 365

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_30E_PLUS_360:
        if d1 == 31:
            d1 = 30
        if d2 == 31:
            m2 += 1
            d2 = 1
        return cpn * ((y2 - y1) * 360 + (m2 - m1) * 30 + (d2 - d1)) / 360

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_ACT_365A:
        return cpn * ((dt2 - dt1).days + 1) / 360

    elif accrual_calculation_model.id == AccrualCalculationModel.DAY_COUNT_ACT_365L:
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


# DEPRECATED
# if __name__ == "__main__":
#     # noinspection PyUnresolvedReferences
#     import django
#     from django.db import transaction
#
#     from poms.instruments.models import (
#         AccrualCalculationModel,
#         AccrualCalculationSchedule,
#         Instrument,
#         Periodicity,
#     )
#     from poms.users.models import MasterUser
#
#     django.setup()
#
#     def _run_f_xirr_1(dates, values):
#         result = list(zip(dates, values))
#         print("data: %s", [(str(d), v) for d, v in result])
#         print("xirr: %s", f_xirr(result))
#
#         return result
#
#     def _run_f_xirr_2(arg0, arg1, arg2, x0):
#         # trn
#         result = [(date(2017, arg0, arg1), arg2), (date(2019, 9, 30), 1.0)]
#         print("data: %s", [(str(d), v) for d, v in result])
#         print("xirr: %s", f_xirr(result, x0=x0))
#         return result
#
#     def _test_ytm():
#         dates = [
#             date(2016, 2, 16),
#             date(2016, 3, 10),
#             date(2016, 9, 1),
#             date(2017, 1, 17),
#         ]
#         values = [
#             -90,
#             5,
#             5,
#             105,
#         ]
#         _run_f_xirr_1(dates, values)
#         print("https://support.office.com/en-us/article/XIRR-function-de1242ec-6477-445b-b11b-a303ad9adc9d")
#         dates = [
#             date(2008, 1, 1),
#             date(2008, 3, 1),
#             date(2008, 10, 30),
#             date(2009, 2, 15),
#             date(2009, 4, 1),
#         ]
#         values = [
#             -10000,
#             2750,
#             4250,
#             3250,
#             2750,
#         ]
#         data = _run_f_xirr_1(dates, values)
#
#         data = _run_f_xirr_2(1, 27, -1.0, 1.0)
#         data = _run_f_xirr_2(2, 3, -1.00857, 0.0)
#
#     _test_ytm()
#     pass
#
#     @transaction.atomic()
#     def _test_coupons():
#         try:
#             master_user = MasterUser.objects.get(pk=1)
#             usd = master_user.currencies.get(user_code="USD")
#             i = Instrument.objects.create(
#                 master_user=master_user,
#                 instrument_type=master_user.instrument_type,
#                 name="i1",
#                 pricing_currency=usd,
#                 accrued_currency=usd,
#             )
#
#             print("-" * 10)
#             accruals = [
#                 AccrualCalculationSchedule.objects.create(
#                     instrument=i,
#                     accrual_start_date=date(2001, 1, 1),
#                     first_payment_date=date(2001, 7, 1),
#                     accrual_size=10,
#                     accrual_calculation_model=AccrualCalculationModel.objects.get(
#                         pk=AccrualCalculationModel.DAY_COUNT_ACT_360
#                     ),
#                     periodicity=Periodicity.objects.get(pk=Periodicity.SEMI_ANNUALLY),
#                 ),
#                 AccrualCalculationSchedule.objects.create(
#                     instrument=i,
#                     accrual_start_date=date(2003, 1, 1),
#                     first_payment_date=date(2003, 7, 1),
#                     accrual_size=20,
#                     accrual_calculation_model=AccrualCalculationModel.objects.get(
#                         pk=AccrualCalculationModel.DAY_COUNT_ACT_360
#                     ),
#                     periodicity=Periodicity.objects.get(pk=Periodicity.SEMI_ANNUALLY),
#                 ),
#             ]
#             i.maturity_date = date(2005, 1, 1)
#             i.maturity_price = 100
#             i.save()
#
#             sd = accruals[0].accrual_start_date - timedelta(days=4)
#             ed = i.maturity_date + timedelta(days=4)
#             cpn_date = sd
#             while cpn_date <= ed:
#                 # print('%s', cpn_date)
#                 cpn_val, is_cpn = i.get_coupon(cpn_date=cpn_date)
#                 if is_cpn:
#                     print("    %s - %s (is_cpn=%s)", cpn_date, cpn_val, is_cpn)
#                 cpn_date += timedelta(days=1)
#
#             print(
#                 "get_future_coupons: %s",
#                 [(str(d), v) for d, v in i.get_future_coupons(begin_date=date(2000, 1, 1))],
#             )
#             print(
#                 "get_future_coupons: %s",
#                 [(str(d), v) for d, v in i.get_future_coupons(begin_date=date(2007, 1, 1))],
#             )
#
#             for d, v in i.get_future_coupons(begin_date=date(2000, 1, 1)):
#                 print("get_coupon: %s - %s", d, i.get_coupon(d))
#
#             i = Instrument.objects.create(
#                 master_user=master_user,
#                 instrument_type=master_user.instrument_type,
#                 name="i2",
#                 pricing_currency=usd,
#                 accrued_currency=usd,
#             )
#             print("-" * 10)
#             accruals = [
#                 AccrualCalculationSchedule.objects.create(
#                     instrument=i,
#                     accrual_start_date=date(2001, 1, 1),
#                     first_payment_date=date(2001, 7, 1),
#                     accrual_size=10,
#                     accrual_calculation_model=AccrualCalculationModel.objects.get(
#                         pk=AccrualCalculationModel.DAY_COUNT_ACT_360
#                     ),
#                     periodicity=Periodicity.objects.get(pk=Periodicity.SEMI_ANNUALLY),
#                 ),
#                 AccrualCalculationSchedule.objects.create(
#                     instrument=i,
#                     accrual_start_date=date(2003, 2, 1),
#                     first_payment_date=date(2004, 1, 1),
#                     accrual_size=20,
#                     accrual_calculation_model=AccrualCalculationModel.objects.get(
#                         pk=AccrualCalculationModel.DAY_COUNT_ACT_360
#                     ),
#                     periodicity=Periodicity.objects.get(pk=Periodicity.ANNUALLY),
#                 ),
#             ]
#             i.maturity_date = date(2007, 2, 1)
#             i.maturity_price = 100
#             i.save()
#
#             sd = accruals[0].accrual_start_date - timedelta(days=4)
#             ed = i.maturity_date + timedelta(days=4)
#             cpn_date = sd
#             while cpn_date <= ed:
#                 cpn_val, is_cpn = i.get_coupon(cpn_date=cpn_date)
#                 if is_cpn:
#                     print("    %s - %s (is_cpn=%s)", cpn_date, cpn_val, is_cpn)
#                 cpn_date += timedelta(days=1)
#
#             print(
#                 "get_future_coupons: %s",
#                 [(str(d), v) for d, v in i.get_future_coupons(begin_date=date(2000, 1, 1))],
#             )
#         finally:
#             transaction.set_rollback(True)
#
#     _test_coupons()
