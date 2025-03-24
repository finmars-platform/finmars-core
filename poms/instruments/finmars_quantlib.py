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


class FixedRateBond:
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
        # mandatory args
        coupon_rate: float,
        issue_date: date,
        maturity_date: date,
        days_between_coupons: int,
        day_count: ql.DayCounter,
        # optional args
        calendar: ql.Calendar = ql.TARGET(),
        business_convention: int = ql.Following,
        termination_date_convention: int = ql.Following,
        date_generation_rule: int = ql.DateGeneration.Backward,
        end_of_month: bool = False,
        settlement_days: int = 2,
        face_amount: float = 100.0,
    ):
        if not all([coupon_rate, issue_date, maturity_date, days_between_coupons, day_count]):
            raise ValueError("all positional args to be provided")
        if not isinstance(day_count, ql.DayCounter):
            raise ValueError(f"day_count must be type ql.Counter, but not {type(day_count)}")

        self.issue_date = ql.Date(issue_date.day, issue_date.month, issue_date.year)
        self.maturity_date = ql.Date(maturity_date.day, maturity_date.month, maturity_date.year)
        self.day_count = day_count
        self.tenor = self.convert_days_to_tenor(days_between_coupons, self.day_count)
        self.calendar = calendar
        self.business_convention = business_convention
        self.termination_date_convention = termination_date_convention
        self.date_generation_rule = date_generation_rule
        self.end_of_month = end_of_month
        self.settlement_days = settlement_days
        self.face_amount = face_amount

        try:
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
        except Exception as e:
            raise TypeError(f"Failed to create ql.Schedule: {repr(e)}") from e

        # number_of_coupons = len(self.schedule) - 1
        # self.coupon_rates = [coupon_rate] * (number_of_coupons - 1) + [0.0]
        self.coupon_rates = [coupon_rate]
        # Create and store the QuantLib bond object
        self.ql_bond = ql.FixedRateBond(
            self.settlement_days,
            self.face_amount,
            self.schedule,
            self.coupon_rates,
            self.day_count,
        )
        spot_dates = [self.issue_date, self.maturity_date]
        spot_rates = [0.0, coupon_rate]
        interpolation = ql.Linear()
        self.compounding = ql.Compounded
        self.compounding_frequency = self.tenor
        self.spot_curve = ql.ZeroCurve(
            spot_dates,
            spot_rates,
            self.day_count,
            self.calendar,
            interpolation,
            self.compounding,
            self.compounding_frequency,
        )
        self.spot_curve_handle = ql.YieldTermStructureHandle(self.spot_curve)

    def cash_flows(self):
        return self.ql_bond.cashflows()

    @staticmethod
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
            raise ValueError(f"days {days} must be a positive integer")

        # Define standard periods and their day counts under the convention
        year_days = 360 if isinstance(day_count, ql.Thirty360) else 365
        periods = [
            (ql.Annual, year_days),  # 360 or 365 days
            (ql.Semiannual, year_days / 2),  # 180 or 182.5 days
            (ql.Quarterly, year_days / 4),  # 90 or 91.25 days
            (ql.Bimonthly, year_days / 6),  # 60 or 60.833 days
            (ql.Monthly, year_days / 12),  # 30 or 30.417 days
            (ql.EveryFourthWeek, 28),  # 28 days (4 weeks)
            (ql.Biweekly, 14),  # 14 days (2 weeks)
            (ql.Weekly, 7),  # 14 days (2 weeks)
        ]

        # Find the closest period by minimizing the absolute difference in days
        closest_period = min(periods, key=lambda p: abs(p[1] - days))

        # Return the corresponding ql.Period
        return closest_period[0]

    def accrued_amount(self, evaluation_date: date) -> float:
        """Calculate the accrued interest for a given evaluation date.
        Args:
            evaluation_date (datetime.date): The date for which to calculate accrued interest.
        Returns:
            float: The accrued amount on the specified date.
        """
        ql_date = ql.Date(evaluation_date.day, evaluation_date.month, evaluation_date.year)

        # Return 0 if evaluation_date is before issue_date, or after maturity date
        if ql_date < self.issue_date or ql_date >= self.maturity_date:
            return 0.0

        ql.Settings.instance().evaluationDate = ql_date

        # return ql.BondFunctions.accruedAmount(self.ql_bond)
        return self.ql_bond.accruedAmount()
