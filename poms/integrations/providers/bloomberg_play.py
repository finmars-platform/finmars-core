# noinspection PyUnresolvedReferences
import django

django.setup()

from poms.integrations.providers.bloomberg import (
    get_certs_from_file,
    FakeBloombergDataProvider,
)

import logging
import os
import pprint
from datetime import date

__author__ = "alyakhov"

_l = logging.getLogger("poms.integrations.providers.bloomberg")


def test_instrument_data(b):
    """
    Test instrument data methods
    """
    _l.debug("-" * 79)

    instrument_fields = sorted(
        {
            "CRNCY",
            "SECURITY_TYP",
            "ISSUER",
            "CNTRY_OF_RISK",
            "INDUSTRY_SECTOR",
            "INDUSTRY_SUBGROUP",
            "SECURITY_DES",
            "ID_ISIN",
            "ID_CUSIP",
            "ID_BB_GLOBAL",
            "MATURITY",
            "CPN",
            "CUR_CPN",
            "CPN_FREQ",
            "COUPON_FREQUENCY_DESCRIPTION",
            "CALC_TYP",
            "CALC_TYP_DES",
            "DAY_CNT",
            "DAY_CNT_DES",
            "INT_ACC_DT",
            "FIRST_SETTLE_DT",
            "FIRST_CPN_DT",
            "OPT_PUT_CALL",
            "MTY_TYP",
            "PAYMENT_RANK",
            "CPN_TYP",
            "CPN_TYP_SPECIFIC",
            "ACCRUED_FACTOR",
            "DAYS_TO_SETTLE",
            "DES_NOTES",
            "PX_YEST_BID",
            "PX_YEST_ASK",
            "PX_YEST_CLOSE",
            "FACTOR_SCHEDULE",
            "MULTI_CPN_SCHEDULE",
        }
    )

    # instrument = 'XS1433454243 Corp'
    # instrument = 'USP7807HAK16 Corp'
    instrument = "USP16394AG62 Corp"
    # instrument = 'XS0955552178 @BGN Corp'

    response = b.get_instrument_sync(instrument, instrument_fields)

    # res = {
    #     "ACCRUED_FACTOR": "1.000000000",
    #     "CALC_TYP": "1",
    #     "CALC_TYP_DES": "STREET CONVENTION",
    #     "CNTRY_OF_RISK": "N.S.",
    #     "COUPON_FREQUENCY_DESCRIPTION": "S/A",
    #     "CPN": "5.375000",
    #     "CPN_FREQ": "2",
    #     "CPN_TYP": "FIXED",
    #     "CPN_TYP_SPECIFIC": "",
    #     "CRNCY": "USD",
    #     "CUR_CPN": "",
    #     "DAYS_TO_SETTLE": "2",
    #     "DAY_CNT": "20",
    #     "DAY_CNT_DES": "ISMA-30/360",
    #     "DES_NOTES": "",
    #     "FIRST_CPN_DT": "12/16/2016",
    #     "FIRST_SETTLE_DT": "06/16/2016",
    #     "ID_BB_GLOBAL": "BBG00D2QX2B8",
    #     "ID_CUSIP": "LW4068711",
    #     "ID_ISIN": "XS1433454243",
    #     "INDUSTRY_SECTOR": "Industrial",
    #     "INDUSTRY_SUBGROUP": "Transport-Marine",
    #     "INT_ACC_DT": "06/16/2016",
    #     "ISSUER": "SCF CAPITAL LTD",
    #     "MATURITY": "06/16/2023",
    #     "MTY_TYP": "AT MATURITY",
    #     "OPT_PUT_CALL": "",
    #     "PAYMENT_RANK": "Sr Unsecured",
    #     "SECURITY_DES": "SCFRU 5 3/8 06/16/23",
    #     "SECURITY_TYP": "EURO-DOLLAR"
    # }

    _l.debug("response: %s", pprint.pformat(response))


def test_pricing_latest(b):
    """
    Test pricing data methods
    """
    _l.debug("-" * 79)

    instrument1 = {"code": "XS1433454243", "industry": "Corp"}
    instrument2 = {"code": "USL9326VAA46", "industry": "Corp"}

    response = b.get_pricing_latest_sync([instrument1, instrument2])
    # res = {
    #     "USL9326VAA46": {
    #         "ACCRUED_FACTOR": "1.000000000",
    #         "CPN": "6.625000",
    #         "PX_CLOSE_1D": "N.S.",
    #         "PX_YEST_ASK": "N.S.",
    #         "PX_YEST_BID": "N.S.",
    #         "PX_YEST_CLOSE": "N.S.",
    #         "SECURITY_TYP": "EURO-DOLLAR"
    #     },
    #     "XS1433454243": {
    #         "ACCRUED_FACTOR": "1.000000000",
    #         "CPN": "5.375000",
    #         "PX_CLOSE_1D": "N.S.",
    #         "PX_YEST_ASK": "N.S.",
    #         "PX_YEST_BID": "N.S.",
    #         "PX_YEST_CLOSE": "N.S.",
    #         "SECURITY_TYP": "EURO-DOLLAR"
    #     }
    # }
    _l.debug("response: %s", pprint.pformat(response))


def test_pricing_history(b):
    """
    Test pricing data methods
    """
    _l.debug("-" * 79)

    # instrument1 = {"code": 'XS1433454243', "industry": "Corp"}
    # instrument2 = {"code": 'USL9326VAA46', "industry": "Corp"}

    # instruments = ['XS1076436218 @BGN Corp', 'CH0246198037 @BGN Corp'] # not worked
    # instruments = ['XS1076436218 Corp', 'CH0246198037 Corp'] # worked
    # fields = ["PX_ASK", "PX_BID", "PX_CLOSE", ]

    instruments = ["RUBUSD Curncy"]
    fields = [
        "PX_BID",
    ]

    response = b.get_pricing_history_sync(
        instruments=instruments,
        fields=fields,
        date_from=date(year=2017, month=3, day=1),
        date_to=date(year=2017, month=3, day=2),
    )

    # res = {
    #     "USL9326VAA46": [
    #         {
    #             "PX_ASK": "94.413",
    #             "PX_BID": "93.108",
    #             "PX_LAST": "93.761",
    #             "date": "2016-06-15"
    #         }
    #     ],
    #     "XS1433454243": [
    #         {
    #             "PX_ASK": "100.302",
    #             "PX_BID": "99.88",
    #             "PX_LAST": "100.091",
    #             "date": "2016-06-15"
    #         }
    #     ]
    # }

    _l.debug("response: %s", pprint.pformat(response))


if __name__ == "__main__":
    p12cert = os.environ["TEST_BLOOMBERG_CERT"]
    password = os.environ["TEST_BLOOMBERG_CERT_PASSWORD"]
    cert, key = get_certs_from_file(p12cert, password)

    # b = BloombergDataProvider(wsdl="https://service.bloomberg.com/assets/dl/dlws.wsdl", cert=cert, key=key)
    b = FakeBloombergDataProvider(
        wsdl="https://service.bloomberg.com/assets/dl/dlws.wsdl", cert=cert, key=key
    )
    # print(b._bbg_instr('10 20'))
    # print(b._bbg_instr('XS0955552178 @BGN Corp'))
    # b.get_fields()
    # test_instrument_data(b)
    # test_pricing_latest(b)
    test_pricing_history(b)

    # from dateutil import parser
    # _l.debug('1: %s', parser.parse("06/16/2023"))
    # _l.debug('2: %s', parser.parse("2016-06-15"))

    # from poms.integrations.tasks import bloomberg_call
    # from poms.users.models import MasterUser
    #
    # master_user = MasterUser.objects.first()
    #
    # a = bloomberg_call(
    #     master_user=master_user,
    #     action='fields'
    # )
    # a = bloomberg_instrument(
    #     master_user=master_user,
    #     instrument={
    #         "code": 'XS1433454243',
    #         "industry": "Corp"
    #     },
    #     fields=['CRNCY']
    # )
    # a = bloomberg_pricing_latest(
    #     master_user=master_user,
    #     instruments=[
    #         {"code": 'XS1433454243', "industry": "Corp"},
    #         {"code": 'USL9326VAA46', "industry": "Corp"},
    #     ]
    # )
    # a = bloomberg_pricing_history(
    #     master_user=master_user,
    #     instruments=[
    #         {"code": 'XS1433454243', "industry": "Corp"},
    #         {"code": 'USL9326VAA46', "industry": "Corp"},
    #     ],
    #     date_from=date(year=2016, month=6, day=14),
    #     date_to=date(year=2016, month=6, day=15),
    # )
    #
    # if getattr(settings, 'CELERY_ALWAYS_EAGER', False):
    #     print('a.get ->', a.get(timeout=60, interval=0.1))
    # else:
    #     b = AsyncResult(a.id)
    #     print('b.get ->', b.get(timeout=60, interval=0.1))

    pass
