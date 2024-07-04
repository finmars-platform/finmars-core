from QuantLib import ActualActual, Date


class MixinYearFraction:
    _daycount_model = "to be defined"

    def __init__(self):
        super().__init__(ActualActual.Actual365)

    def name(self):
        return self._daycount_model

    @staticmethod
    def days_in_year(end_date: Date) -> float:
        raise NotImplementedError

    def yearFraction(self, startDate: Date, endDate: Date, *args, **kwargs) -> float:
        days = self.dayCount(startDate, endDate)
        return days / self.days_in_year(endDate)


class Actual365A(MixinYearFraction, ActualActual):
    _daycount_model = "Actual/365A"

    @staticmethod
    def days_in_year(end_date: Date) -> int:
        # Check if February 29 is included in the date range
        if Date.isLeap(end_date.year()):
            days_feb_29 = Date(29, 2, end_date.year()).serialNumber()
            days_end_date = end_date.serialNumber()
            if days_feb_29 <= days_end_date:
                return 366

        return 365


class Actual365L(MixinYearFraction, ActualActual):
    _daycount_model = "Actual/365L"

    @staticmethod
    def days_in_year(end_date: Date) -> int:
        # Check if the end date is in a leap year
        if Date.isLeap(end_date.year()):
            return 366

        return 365
