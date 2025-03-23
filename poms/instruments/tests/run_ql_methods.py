import QuantLib as ql

# 1) Set the evaluation date
today = ql.Date(20, 3, 2025)
ql.Settings.instance().evaluationDate = today

# 2) Define bond details
face_amount = 100.0
coupon_rate = 0.05  # 5% annual coupon
issue_date = ql.Date(20, 3, 2020)
maturity_date = ql.Date(20, 3, 2030)
frequency = ql.Annual
calendar = ql.TARGET()
business_convention = ql.ModifiedFollowing
day_count = ql.ActualActual(ql.ActualActual.Bond)
schedule = ql.Schedule(
    issue_date,
    maturity_date,
    ql.Period(frequency),
    calendar,
    business_convention,
    business_convention,
    ql.DateGeneration.Backward,
    False,
)

# Create a fixed rate bond
# The redemption (notional repayment) is 100 at maturity.
# 'settlementDays=3' is how many days after today we consider the settlement.
settlement_days = 3
fixed_bond = ql.FixedRateBond(
    settlement_days,
    face_amount,
    schedule,
    [coupon_rate],
    day_count,
    business_convention,
    face_amount,  # redemption
    issue_date,
)

# 3) Set up Yield/Discounting
# For demonstration, assume a flat yield curve at 5%.
yield_rate = 0.05
compounding = ql.Compounded
compounding_frequency = ql.Annual

bond_yield = ql.FlatForward(today, yield_rate, day_count, compounding, compounding_frequency)
yield_handle = ql.YieldTermStructureHandle(bond_yield)

# We use a bond pricing engine that discounts bond cash flows
engine = ql.DiscountingBondEngine(yield_handle)
fixed_bond.setPricingEngine(engine)

# 4) Get prices and accrued amount
clean_price = fixed_bond.cleanPrice()
accrued_interest = fixed_bond.accruedAmount()
dirty_price = fixed_bond.dirtyPrice()

print("Settlement date:      ", fixed_bond.settlementDate())
print("Clean Price:          ", clean_price)
print("Accrued Amount:       ", accrued_interest)
print("Dirty Price (Full):   ", dirty_price)
