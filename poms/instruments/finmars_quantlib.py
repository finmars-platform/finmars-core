from datetime import date
from typing import List

import QuantLib as ql


class MixinYearFraction:
    _daycount_model = "to be defined"

    def __init__(self):
        super().__init__(ql.ActualActual.Actual365)

    def name(self):
        return self._daycount_model

    @staticmethod
    def days_in_year(end_date: ql.Date) -> float:
        raise NotImplementedError

    def yearFraction(self, startDate: ql.Date, endDate: ql.Date, *args, **kwargs) -> float:
        days = self.dayCount(startDate, endDate)
        return days / self.days_in_year(endDate)


class Actual365A(MixinYearFraction, ql.ActualActual):
    _daycount_model = "Actual/365A"

    @staticmethod
    def days_in_year(end_date: ql.Date) -> int:
        # Check if February 29 is included in the date range
        if ql.Date.isLeap(end_date.year()):
            days_feb_29 = ql.Date(29, 2, end_date.year()).serialNumber()
            days_end_date = end_date.serialNumber()
            if days_feb_29 <= days_end_date:
                return 366

        return 365


class Actual365L(MixinYearFraction, ql.ActualActual):
    _daycount_model = "Actual/365L"

    @staticmethod
    def days_in_year(end_date: ql.Date) -> int:
        # Check if the end date is in a leap year
        return 366 if ql.Date.isLeap(end_date.year()) else 365


def convert_days_to_tenor(days: int, day_count: ql.DayCounter = ql.Thirty360) -> ql.Period:
    """
    Convert a number of days in period into a QuantLib Period object (tenor) based on a day count convention.
    It uses self.day_count value (ql.DayCounter) - Day count convention (e.g., 30E/360).

    Args:
        days (int): Number of days between coupon payments (e.g., 172).
        day_count (ql.DayCounter): Day count convention (e.g., 30E/360).
            Defaults to 30E/360, as it’s common for European bonds.

    Returns:
        ql.Period: The corresponding QuantLib Period (e.g., Annual, Semiannual, Quarterly).

    Raises:
        ValueError: If days is negative or cannot be reasonably mapped to a period.
    """
    if days <= 0:
        raise ValueError("Days must be a positive integer.")

    # Define standard periods and their day counts under the convention
    year_days = 360 if isinstance(day_count, ql.Thirty360) else 365
    periods = [
        (ql.Period(1, ql.Years), year_days),  # 360 or 365 days
        (ql.Period(6, ql.Months), year_days / 2),  # 180 or 182.5 days
        (ql.Period(3, ql.Months), year_days / 4),  # 90 or 91.25 days
        (ql.Period(2, ql.Months), year_days / 6),  # 60 or 60.833 days
        (ql.Period(1, ql.Months), year_days / 12),  # 30 or 30.417 days
        (ql.Period(ql.EveryFourthWeek), 28),  # 28 days (4 weeks)
        (ql.Period(ql.Biweekly), 14),  # 14 days (2 weeks)
    ]

    # Find the closest period by minimizing the absolute difference in days
    closest_period = min(periods, key=lambda p: abs(p[1] - days))

    # Return the corresponding ql.Period
    return closest_period[0]


class BondCalculation:
    """A class representing a fixed-rate bond for QuantLib calculations.

    This class defines the essential attributes required to construct a `ql.FixedRateBond`
    object and compute properties like accrued interest via `ql.BondFunctions.accruedAmount`.

    Attributes:
        face_amount (float): Nominal value of the bond, repaid at maturity and used for coupon
            calculations. Example: 100.0 (e.g., $100 par value).
        issue_date (ql.Date): Date the bond was issued, starting point of the coupon schedule.
            Example: ql.Date(15, 1, 2025) for January 15, 2025.
        maturity_date (ql.Date): Date the bond matures, when the final coupon and principal
            are paid. Must be later than issue_date. Example: ql.Date(1, 1, 2030).
        coupon_rates (List[float]): Annual coupon rates (as decimals) paid periodically.
            Typically, a single rate for fixed-rate bonds. Example: [0.03] for 3% annual coupon.
        day_count (ql.DayCounter): Convention for calculating year fractions between dates.
            Affects coupon and accrued interest amounts. Example: ql.Thirty360(ql.Thirty360.European).
        tenor (ql.Period): Frequency of coupon payments (e.g., annual, semiannual).
            Determines the coupon schedule. Example: ql.Period(ql.Semiannual) for 6-month intervals.
        settlement_days (int): Number of business days from trade date to settlement date.
            Used to compute the settlement date, affecting accrued interest. Default: 2 (T+2) days.
        calendar (ql.Calendar): Defines business days and holidays for date adjustments.
            Used in the schedule and settlement date. Example: ql.TARGET() for Eurozone.
        business_convention (int, optional): Business day convention for adjusting coupon dates.
            Determines how non-business days are handled. Defaults to ql.Following (next business day).
            Example: ql.Preceding (previous business day).
        termination_date_convention (int, optional): Business day convention for the maturity date.
            Adjusts the final payment date if it falls on a non-business day. Defaults to ql.Following.
            Example: ql.Unadjusted (no adjustment).
        date_generation_rule (int, optional): Rule for generating the coupon schedule.
            Defines whether dates are calculated forward from issue_date or backward from maturity_date.
            Defaults to ql.DateGeneration.Backward (from maturity). Example: ql.DateGeneration.Forward.
        end_of_month (bool, optional): Whether coupon dates align with month-end.
            If True, dates are set to the last day of the month (e.g., June 30, December 31).
            Defaults to False (follows tenor strictly). Example: True for month-end aligned bonds.
    """

    def __init__(
        self,
        face_amount: float,
        issue_date: ql.Date,
        maturity_date: ql.Date,
        coupon_rate: float,
        day_count: ql.DayCounter,
        tenor: ql.Period,
        settlement_days: int = 2,
        calendar: ql.Calendar = ql.TARGET,
        business_convention: int = ql.Following,
        termination_date_convention: int = ql.Following,
        date_generation_rule: int = ql.DateGeneration.Backward,
        end_of_month: bool = False,
    ):
        self.settlement_days = settlement_days
        self.face_amount = face_amount
        self.issue_date = issue_date
        self.maturity_date = maturity_date
        self.coupon_rates = [coupon_rate]
        self.day_count = day_count
        self.calendar = calendar
        self.tenor = tenor
        self.business_convention = business_convention
        self.termination_date_convention = termination_date_convention
        self.date_generation_rule = date_generation_rule
        self.end_of_month = end_of_month

        # Compute and store the schedule
        self.schedule = ql.Schedule(
            self.issue_date,
            self.maturity_date,
            self.tenor,
            self.calendar,
            self.business_convention,
            self.termination_date_convention,
            self.date_generation_rule,
            self.end_of_month,
        )

        # Create and store the QuantLib bond object
        self.ql_bond = ql.FixedRateBond(
            self.settlement_days, self.face_amount, self.schedule, self.coupon_rates, self.day_count
        )

    def accrued_amount(self, evaluation_date: date) -> float:
        """Calculate the accrued interest for a given evaluation date.
        Args:
            evaluation_date (datetime.date): The date for which to calculate accrued interest.
        Returns:
            float: The accrued amount on the specified date.
        """
        ql_date = ql.Date(evaluation_date.day, evaluation_date.month, evaluation_date.year)

        ql.Settings.instance().evaluationDate = ql_date

        return ql.BondFunctions.accruedAmount(self.ql_bond)
