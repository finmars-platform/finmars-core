import QuantLib as ql


class Actual366(ql.DayCounter):
    def __init__(self):
        ql.DayCounter.__init__(self)

    def name(self):
        return "Actual/366"

    def dayCount(self, date1, date2):
        return date2 - date1

    def yearFraction(self, date1, date2, refPeriodStart, refPeriodEnd):
        return self.dayCount(date1, date2) / 366.0


class Actual364(ql.DayCounter):
    def __init__(self):
        ql.DayCounter.__init__(self)

    def name(self):
        return "Actual/364"

    def dayCount(self, date1, date2):
        return date2 - date1

    def yearFraction(self, date1, date2, refPeriodStart, refPeriodEnd):
        return self.dayCount(date1, date2) / 364.0
