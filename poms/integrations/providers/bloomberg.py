import base64
import logging
import uuid
from datetime import timedelta, datetime
from tempfile import NamedTemporaryFile
from time import sleep

import requests
from OpenSSL import crypto
from dateutil import parser
from django.conf import settings
from suds.client import Client
from suds.transport import Reply
from suds.transport.http import HttpAuthenticated

from poms.common import formula
from poms.currencies.models import CurrencyHistory
from poms.instruments.models import AccrualCalculationSchedule, InstrumentFactorSchedule, PriceHistory
from poms.integrations.models import FactorScheduleDownloadMethod, AccrualScheduleDownloadMethod, ProviderClass, \
    InstrumentDownloadScheme, PriceDownloadScheme
from poms.integrations.providers.base import AbstractProvider, ProviderException, parse_date_iso
from poms.common.utils import date_now, isclose

_l = logging.getLogger('poms.integrations.providers.bloomberg')


class BloombergException(ProviderException):
    pass


class BloombergTransportException(BloombergException):
    pass


def get_certs_from_file(p12cert, password):
    """
    Convert pkcs#12 bloomberg certificate into pem format certificates, used by authorized DLWS access.
    @param p12cert: path to pkcs#12 file
    @type str
    @param password: password to extract certificates from pkcs#12 file
    @type str
    @return: (cert,key): pem certificate as string and private key as string
    @rtype: tuple
    """
    with open(p12cert, 'rb') as f:
        p12 = crypto.load_pkcs12(f.read(), password)
        key = crypto.dump_privatekey(crypto.FILETYPE_PEM, p12.get_privatekey())
        cert = crypto.dump_certificate(crypto.FILETYPE_PEM, p12.get_certificate())
    return cert, key


def get_certs(p12cert, password, is_base64=False):
    """
    Convert pkcs#12 bloomberg certificate into pem format certificates, used by authorized DLWS access.
    @param p12cert: binary or base64 data
    @type str
    @param password: password to extract certificates from pkcs#12 file
    @type str
    @param is_base64: p12cert is bynary or base64 encoded string
    @type bool
    @return: (cert,key): pem certificate as string and private key as string
    @rtype: tuple
    """
    if is_base64:
        p12cert = base64.b64decode(p12cert)
    p12 = crypto.load_pkcs12(p12cert, password)
    key = crypto.dump_privatekey(crypto.FILETYPE_PEM, p12.get_privatekey())
    cert = crypto.dump_certificate(crypto.FILETYPE_PEM, p12.get_certificate())
    return cert, key


class RequestsTransport(HttpAuthenticated):
    """
    Custom transport for SUDs library, required for SSL client certificate authorization. Rely on requests library.
    Should be initialized with cert and key (pem certificate file path and private key respectively).
    """

    def __init__(self, **kwargs):
        self.cert = kwargs.pop('cert', None)
        self.key = kwargs.pop('key', None)
        self.timeout = kwargs.pop('timeout', 10)
        if not self.cert:
            raise BloombergTransportException("cert param could not be None")
        if not self.key:
            raise BloombergTransportException("key param could not be None")
        super(RequestsTransport, self).__init__(**kwargs)

    def get_soap_action(self, message):
        """
        Custom quirk to setup SOAPAction header
        """
        s = message.decode()
        if "submitGetDataRequest" in s:
            return '"submitGetDataRequest"'
        elif "submitGetDataRequest" in s:
            return '"submitGetDataRequest"'
        elif "retrieveGetDataRequest" in s:
            return '"retrieveGetDataResponse"'
        elif "submitGetHistoryRequest" in s:
            return '"submitGetHistoryRequest"'
        elif "retrieveGetHistoryRequest" in s:
            return '"retrieveGetHistoryResponse"'
        elif "getFieldsRequest" in s:
            return '"getFields"'
        return "''"

    def send(self, request):
        """
        Transport to send request with SSL client cert. Use temporary files for certs, which get deleted right after
        request completed.
        request param contain message attr with SOAP generated content.
        """
        self.addcredentials(request)

        with NamedTemporaryFile() as key, NamedTemporaryFile() as cert:
            cert.write(self.cert)
            cert.flush()
            key.write(self.key)
            key.flush()

            request.headers['SOAPAction'] = self.get_soap_action(request.message)

            resp = requests.post(
                request.url,
                data=request.message,
                headers=request.headers,
                cert=(cert.name, key.name),
                verify=True,
                timeout=self.timeout,
            )
            result = Reply(resp.status_code, resp.headers, resp.content)
            return result


class BloombergDataProvider(AbstractProvider):
    """
    Bloomberg python client for Finmars.
    """

    def __init__(self, cert=None, key=None, wsdl=None):
        """
        Constructor for BloomberDataProvider
        @param wsdl: url for WSDL file
        @type: str
        @param cert: SSL client pem certificate as string
        @type: str
        @param key: SSL client pem private key as string
        @type: str
        @return: BloomberDataProvider object
        @rtype: BloombergDataProvider
        """
        super(BloombergDataProvider, self).__init__()
        self.empty_value = settings.BLOOMBERG_EMPTY_VALUE

        self._wsdl = wsdl or settings.BLOOMBERG_WSDL
        self._cert = cert
        self._key = key
        self._soap_client = None

    @property
    def soap_client(self):
        if not self._soap_client:
            if not self._wsdl:
                raise BloombergException("wsdl should be provided")
            if not self._cert:
                raise BloombergException("client certificate pem file should be provided")
            if not self._key:
                raise BloombergException("private key pem file should be provided")

            transport = RequestsTransport(cert=self._cert, key=self._key)
            headers = {
                "Content-Type": "text/xml;charset=UTF-8",
                "SOAPAction": ""
            }
            self._soap_client = Client(self._wsdl, headers=headers, transport=transport)
            # _l.info('soap client: %s', self._soap_client)
        return self._soap_client

    def _response_is_valid(self, response, pending=False, raise_exception=True):
        if response.statusCode.code == 0:
            return True
        elif pending and response.statusCode.code == 100:
            return True
        else:
            if raise_exception:
                raise BloombergException(
                    "Bloomberg failed with code %s and description '%s'" % (
                        response.statusCode.code, response.description))
            return False

    def _data_is_ready(self, response):
        return response.statusCode.code == 0

    def _bbg_instr(self, code):
        allparts = code.split()
        parts = [p for p in allparts if not p.startswith('@')]
        overrides = [o[1:] for o in allparts if o.startswith('@')]
        if not parts:
            raise BloombergException('Invalid code')
        id0 = parts[0]
        try:
            yellowkey = parts[1]
        except IndexError:
            yellowkey = None

        ret = self.soap_client.factory.create('Instrument')
        # ret = {"id": id0}
        ret.id = id0
        if yellowkey:
            ret.yellowkey = yellowkey
            # ret['yellowkey'] = yellowkey
        if overrides:
            for o in overrides:
                override = self.soap_client.factory.create('Override')
                override.field = 'PRICING_SOURCE'
                override.value = o
                ret.overrides.override.append(override)
            # ret['overrides'] = [{'field': 'PRICING_SOURCE', 'value': o} for o in overrides]
        return ret

    def _invoke_sync(self, name, request_func, request_kwargs, response_func):
        _l.info('|> %s', name)
        response_id = request_func(**request_kwargs)
        _l.info('|  response_id=%s', response_id)
        for attempt in range(settings.BLOOMBERG_MAX_RETRIES):
            sleep(settings.BLOOMBERG_RETRY_DELAY)
            _l.info('|  attempt=%s', attempt)
            result = response_func(response_id)
            if result is not None:
                _l.info('|<')
                return result
        _l.info('|< failed')
        raise BloombergException("%s('%s') failed" % (name, response_id,))

    def get_max_retries(self):
        return settings.BLOOMBERG_MAX_RETRIES

    def get_retry_delay(self):
        return settings.BLOOMBERG_RETRY_DELAY

    def get_factor_schedule_method_fields(self, factor_schedule_method=None):
        if factor_schedule_method == FactorScheduleDownloadMethod.DEFAULT:
            return ['FACTOR_SCHEDULE']
        return []

    def get_accrual_calculation_schedule_method_fields(self, accrual_calculation_schedule_method=None):
        if accrual_calculation_schedule_method == AccrualScheduleDownloadMethod.DEFAULT:
            return ['START_ACC_DT', 'FIRST_CPN_DT', 'CPN', 'DAY_CNT', 'CPN_FREQ', 'MULTI_CPN_SCHEDULE']
        return []

    def parse_date(self, value):
        if value and value.lower() != 'n.s.':
            try:
                return datetime.strptime(value, settings.BLOOMBERG_DATE_INPUT_FORMAT).date()
            except ValueError:
                return None
        return None

    def is_valid_reference(self, value):
        if value:
            value = value.split()
            if len(value) in [2, 3]:
                return True
        return False

    def test_certificate(self, options):

        _l.info('download_currency_pricing: %s', options)

        return self._invoke_sync(name='test_certificate',
                                 request_func=self.get_test_certificate_send_request,
                                 request_kwargs={
                                 },
                                 response_func=self.get_test_certificate_get_response)

    def download_instrument(self, options):
        _l.info('download_instrument: %s', options)

        response_id = options.get('response_id', None)
        if response_id is None:
            instrument_download_scheme_id = options['instrument_download_scheme_id']
            instrument_code = options['instrument_code']

            instrument_download_scheme = InstrumentDownloadScheme.objects.get(pk=instrument_download_scheme_id)

            fields = instrument_download_scheme.fields
            factor_schedule_method_fields = self.get_factor_schedule_method_fields(
                instrument_download_scheme.factor_schedule_method_id)
            accrual_calculation_schedule_method_fields = self.get_accrual_calculation_schedule_method_fields(
                instrument_download_scheme.accrual_calculation_schedule_method_id)

            options['fields'] = fields
            options['factor_schedule_method_fields'] = factor_schedule_method_fields
            options['accrual_calculation_schedule_method_fields'] = accrual_calculation_schedule_method_fields

            request_fields = fields + factor_schedule_method_fields + accrual_calculation_schedule_method_fields
            response_id = self.get_instrument_send_request(instrument_code, request_fields)

            if response_id is None:
                raise BloombergException("Can't send request")

            options['response_id'] = response_id
            return None, False
        else:
            result = self.get_instrument_get_response(response_id)
            return result, result is not None

    def download_instrument_pricing(self, options):
        _l.info('download_instrument_pricing: %s', options)

        is_yesterday = options['is_yesterday']
        response_id = options.get('response_id', None)
        if response_id is None:
            price_download_scheme_id = options['price_download_scheme_id']
            price_download_scheme = PriceDownloadScheme.objects.get(pk=price_download_scheme_id)
            instruments = list(set(options['instruments']))
            if is_yesterday:
                fields = price_download_scheme.instrument_yesterday_fields
                response_id = self.get_pricing_latest_send_request(instruments, fields)
            else:
                fields = price_download_scheme.instrument_history_fields
                date_from = parse_date_iso(options['date_from'])
                date_to = parse_date_iso(options['date_to'])
                response_id = self.get_pricing_history_send_request(instruments, fields, date_from, date_to)

            if response_id is None:
                raise BloombergException("Can't send request")

            options['response_id'] = response_id
            return None, False
        else:
            if is_yesterday:
                result = self.get_pricing_latest_get_response(response_id)
            else:
                result = self.get_pricing_history_get_response(response_id)
            return result, result is not None

    def download_currency_pricing(self, options):
        _l.info('download_currency_pricing: %s', options)

        is_yesterday = options['is_yesterday']
        response_id = options.get('response_id', None)
        if response_id is None:
            price_download_scheme_id = options['price_download_scheme_id']
            price_download_scheme = PriceDownloadScheme.objects.get(pk=price_download_scheme_id)
            currencies = list(set(options['currencies']))
            if is_yesterday:
                fields = price_download_scheme.currency_history_fields
                response_id = self.get_pricing_latest_send_request(currencies, fields)
            else:
                fields = price_download_scheme.currency_history_fields
                date_from = parse_date_iso(options['date_from'])
                date_to = parse_date_iso(options['date_to'])
                response_id = self.get_pricing_history_send_request(currencies, fields, date_from, date_to)

            if response_id is None:
                raise BloombergException("Can't send request")

            options['response_id'] = response_id
            return None, False
        else:
            if is_yesterday:
                result = self.get_pricing_latest_get_response(response_id)
            else:
                result = self.get_pricing_history_get_response(response_id)
            return result, result is not None

    def get_instrument_send_request(self, instrument, fields):
        """
        Get single instrument data using instrument ISIN and industry code. Async mode. Instrument data should be
        retrieved by get_instrument_get_response further call.
        @param instrument: requested instrument id
        @type tuple: (ISNIN, industry), i.e. (X73487634234,Corp)
        @param fields: list of bloombeg fields to retrieve
        @type list: list of strings
        @return: response id, used by get_instrument_get_response method
        @rtype: str
        """
        _l.info('> get_instrument_send_request: instrument="%s", fields=%s',
                 instrument, fields)

        if not instrument or not fields:
            _l.info('< response_id=%s', None)
            return None

        fields_data = self.soap_client.factory.create('Fields')
        for field in fields:
            fields_data.field.append(field)

        headers = {
            "secmaster": True,
            "pricing": True,
            "historical": True,
        }
        instruments = [{"instrument": self._bbg_instr(instrument)}]

        _l.info('request: instruments=%s, fields=%s, headers=%s', instruments, fields, headers)
        response = self.soap_client.service.submitGetDataRequest(
            headers=headers,
            fields=fields_data,
            instruments=instruments,
        )
        _l.info('response=%s', response)
        self._response_is_valid(response)

        response_id = str(response.responseId)
        _l.info('< response_id=%s', response_id)

        return response_id

    def get_instrument_get_response(self, response_id):
        """
        Get single instrument data response. If bloomberg task is not ready, would return None.
        @param response_id:
        @type str
        @return: dictionary where key is requested bloomberg field and value - retrieved data
        @rtype: dict
        """

        _l.info('> get_instrument_get_response: response_id=%s', response_id)

        if response_id is None:
            _l.info('< result=%s', None)
            return None

        response = self.soap_client.service.retrieveGetDataResponse(responseId=response_id)
        _l.info('response=%s', response)

        self._response_is_valid(response, pending=True)
        if self._data_is_ready(response):
            result = {}
            for i, field in enumerate(response.fields[0]):
                d = response.instrumentDatas[0][0].data[i]
                if getattr(d, '_isArray', False):
                    value = []
                    for row in d.bulkarray:
                        cols = []
                        for c in row.data:
                            cols.append(c._value)
                        value.append(cols)
                else:
                    value = response.instrumentDatas[0][0].data[i]._value
                result[field] = value
            _l.info('< result=%s', result)
            return result
        return None

    def get_instrument_sync(self, instrument, fields):
        # response_id = self.get_instrument_send_request(instrument, fields)
        # for attempt in six.moves.range(1000):
        #     sleep(0.5)
        #     _l.info('get_instrument_sync: response_id=%s, attempt=%s', response_id, attempt)
        #     result = self.get_instrument_get_response(response_id)
        #     if result:
        #         return result
        # _l.info('get_instrument_sync: failed')
        # raise BloombergDataProviderException("get_instrument_sync('%s') failed" % response_id)
        return self._invoke_sync(name='get_instrument_sync',
                                 request_func=self.get_instrument_send_request,
                                 request_kwargs={'instrument': instrument, 'fields': fields},
                                 response_func=self.get_instrument_get_response)

    def get_fields(self):
        """
        Test method to check SSL connectivity. (is free!)
        @return: bloomberg mnemonic test data.
        @rtype: dict
        """
        _l.info('get_fields >')

        response = self.soap_client.service.getFields(
            criteria={
                "mnemonic": "NAME"
            }
        )
        _l.info('response=%s', response)
        self._response_is_valid(response)
        return response

    def get_test_certificate_send_request(self):
        """
        Async method to check if certificate is valid
        @return: response_id: used to get data in get_pricing_latest_get_response
        @rtype: str
        """
        _l.info('> get_test_certificate_send_request:')

        # fields = ['PX_YEST_BID', 'PX_YEST_ASK', 'PX_YEST_CLOSE', 'PX_CLOSE_1D', 'ACCRUED_FACTOR', 'CPN', 'SECURITY_TYP']
        fields = []

        fields_data = self.soap_client.factory.create('Fields')
        fields_data.field = fields

        headers = {
            "secmaster": True,
            "pricing": True,
            "historical": True,
        }

        _l.info('request: fields=%s, headers=%s', fields, headers)
        response = self.soap_client.service.submitGetDataRequest(
            headers=headers,
            fields=fields_data
        )
        _l.info('response=%s', response)

        is_authorized = False

        if response.statusCode.code == 200:
            is_authorized = True

        _l.info('< is_authorized=%s', is_authorized)

        return is_authorized

    def get_test_certificate_get_response(self, is_authorized):
        """
        Retrieval of status of test certificate request. Return True/False as status value
        @param is_authorized: authorization status
        @type str
        @return: dictionary, where key - is_authorized, value - True/False
        @rtype: dict
        """

        _l.info('get_test_certificate_get_response is_authorized %s' % is_authorized)

        return {
            "is_authorized": is_authorized
        }

    def get_pricing_latest_send_request(self, instruments, fields):
        """
        Async method to get pricing data. Would return response id, used in
        get_pricing_latest_get_response method.
        This method should be used to collect "yesterday" data info. Normally should be used for automatic daily
        update methods.
        @param instruments: list of instrument tuples. Each tuple - (ISIN,Insustry)
        @type tuple
        @return: response_id: used to get data in get_pricing_latest_get_response
        @rtype: str
        """
        _l.info('> get_pricing_latest_send_request: instrument=%s, fields=%s', instruments, fields)

        # fields = ['PX_YEST_BID', 'PX_YEST_ASK', 'PX_YEST_CLOSE', 'PX_CLOSE_1D', 'ACCRUED_FACTOR', 'CPN', 'SECURITY_TYP']

        if not instruments or not fields:
            _l.info('< response_id=%s', None)
            return None

        fields_data = self.soap_client.factory.create('Fields')
        fields_data.field = fields

        instruments_data = self.soap_client.factory.create('Instruments')
        for code in instruments:
            instruments_data.instrument.append(self._bbg_instr(code))

        headers = {
            "secmaster": True,
            "pricing": True,
            "historical": True,
        }

        _l.info('request: instruments=%s, fields=%s, headers=%s', instruments_data, fields, headers)
        response = self.soap_client.service.submitGetDataRequest(
            headers=headers,
            fields=fields_data,
            instruments=instruments_data
        )
        _l.info('response=%s', response)
        self._response_is_valid(response)

        response_id = str(response.responseId)
        _l.info('< response_id=%s', response_id)

        return response_id

    def get_pricing_latest_get_response(self, response_id):
        """
        Retrieval of yesterday pricing data. Return None is data is not ready.
        @param response_id: request-response reference, received in get_pricing_latest_send_request
        @type str
        @return: dictionary, where key - ISIN, value - dict with {bloomberg_field:value} dicts
        @rtype: dict
        """
        if response_id is None:
            _l.info('< result=%s', None)
            return None

        response = self.soap_client.service.retrieveGetDataResponse(responseId=response_id)
        _l.info('> get_pricing_latest_get_response: response_id=%s, response=%s', response_id, response)

        self._response_is_valid(response, pending=True)
        if self._data_is_ready(response):
            result = {}
            for instrument in response.instrumentDatas[0]:
                # i = 0
                # instrument_fields = {}
                # for field in resp.fields[0]:
                #     instrument_fields[field] = instrument.data[i]._value
                #     i += 1
                instrument_fields = {}
                for i, field in enumerate(response.fields[0]):
                    instrument_fields[field] = instrument.data[i]._value
                result[instrument.instrument.id] = instrument_fields

            _l.info('< result=%s', result)
            return result
        return None

    def get_pricing_latest_sync(self, instruments, fields):
        return self._invoke_sync(name='get_pricing_latest_sync',
                                 request_func=self.get_pricing_latest_send_request,
                                 request_kwargs={
                                     'instruments': instruments,
                                     'fields': fields
                                 },
                                 response_func=self.get_pricing_latest_get_response)

    def get_pricing_history_send_request(self, instruments, fields, date_from, date_to):
        _l.info('> get_pricing_history_send_request: instrument=%s, fields=%s, date_from=%s, date_to=%s',
                 instruments, fields, date_from, date_to)

        if not instruments or not fields or not date_from or not date_to:
            _l.info('< response_id=%s', None)
            return None

        start = date_from.strftime("%Y-%m-%d")
        end = date_to.strftime("%Y-%m-%d")
        # fields = ['PX_BID', 'PX_ASK', 'PX_LAST']

        headers = {
            # "secmaster": True,
            # "pricing": True,
            # "historical": True,
            "daterange": {
                "period": {
                    "start": start,
                    "end": end
                }
            }
        }

        fields_data = self.soap_client.factory.create('Fields')
        fields_data.field = fields

        instruments_data = self.soap_client.factory.create('Instruments')
        for code in instruments:
            instruments_data.instrument.append(self._bbg_instr(code))

        _l.info('request: instruments=%s, fields=%s, headers=%s', instruments_data, fields, headers)
        response = self.soap_client.service.submitGetHistoryRequest(
            headers=headers,
            fields=fields_data,
            instruments=instruments_data
        )
        _l.info('response=%s', response)
        self._response_is_valid(response)

        response_id = str(response.responseId)
        _l.info('< response_id=%s', response_id)

        return response_id

    def get_pricing_history_get_response(self, response_id):
        if response_id is None:
            _l.info('< result=%s', None)
            return None

        response = self.soap_client.service.retrieveGetHistoryResponse(responseId=response_id)
        _l.info('> get_pricing_history_get_response: response_id=%s, response=%s', response_id, response)

        self._response_is_valid(response, pending=True)
        if self._data_is_ready(response):
            result = {}
            try:
                fields = response.fields[0]
            except (AttributeError, KeyError, IndexError):
                _l.info('< result=%s', result)
                return result
            for instrument in response.instrumentDatas[0]:
                try:
                    instrument_date = instrument.date
                except (IndexError, KeyError, AttributeError):
                    continue
                instrument_fields = {
                    'DATE': instrument_date,
                }
                for i, field in enumerate(fields):
                    try:
                        value = instrument.data[i]._value
                    except (IndexError, KeyError, AttributeError):
                        continue
                    instrument_fields[field] = value

                if instrument.instrument.id in result:
                    result[instrument.instrument.id].append(instrument_fields)
                else:
                    result[instrument.instrument.id] = [instrument_fields]
            _l.info('< result=%s', result)
            return result
        return None

    def get_pricing_history_sync(self, instruments, fields, date_from, date_to):
        """
        Sync method to get historical pricing data. Would block until response is ready.
        @param date_from: start of historical range
        @type datetime
        @param date_to: inclusive end of historical range
        @type datetime
        @param instruments: list of instrument tuples. Each tuple - (ISIN,Insustry)
        @type tuple
        @return: dictionary, where key - ISIN, value - dict with {bloomberg_field:value} dicts
        @rtype: dict
        """

        return self._invoke_sync(name='get_pricing_history_sync',
                                 request_func=self.get_pricing_history_send_request,
                                 request_kwargs={
                                     'instruments': instruments,
                                     'fields': fields,
                                     'date_from': date_from,
                                     'date_to': date_to
                                 },
                                 response_func=self.get_pricing_history_get_response)

    def create_accrual_calculation_schedules(self, instrument_download_scheme, instrument, values):
        accrual_calculation_schedule_method = instrument_download_scheme.accrual_calculation_schedule_method_id
        if accrual_calculation_schedule_method != AccrualScheduleDownloadMethod.DEFAULT:
            return []
        start_acc_dt = values['START_ACC_DT']
        first_cpn_dt = values['FIRST_CPN_DT']
        cpn = values['CPN']
        day_cnt = values['DAY_CNT']
        cpn_freq = values['CPN_FREQ']
        multi_cpn_schedule = values['MULTI_CPN_SCHEDULE']

        # multi_cpn_schedule = [
        #     ['08/20/2017', '5.0000'],
        #     ['02/20/2038', '6.7670']
        # ]

        is_multi_cpn_schedule = multi_cpn_schedule and \
                                not isinstance(multi_cpn_schedule, str) and \
                                isinstance(multi_cpn_schedule, (tuple, list))

        accrual_start_date = self.parse_date(start_acc_dt)
        first_payment_date = self.parse_date(first_cpn_dt)
        accrual_size = self.parse_float(cpn)

        accrual_calculation_model = self.get_accrual_calculation_model(
            instrument.master_user, ProviderClass.BLOOMBERG, day_cnt)
        periodicity = self.get_periodicity(instrument.master_user, ProviderClass.BLOOMBERG, cpn_freq)
        if periodicity is None:
            return []

        accrual_calculation_schedules = []
        if is_multi_cpn_schedule:
            for row in multi_cpn_schedule:
                accrual_size = self.parse_float(row[1])

                s = AccrualCalculationSchedule()
                s.instrument = instrument
                if accrual_start_date:
                    s.accrual_start_date = accrual_start_date
                if first_payment_date:
                    s.first_payment_date = first_payment_date
                if accrual_size:
                    s.accrual_size = accrual_size
                if accrual_calculation_model:
                    s.accrual_calculation_model = accrual_calculation_model
                if periodicity:
                    s.periodicity = periodicity

                accrual_calculation_schedules.append(s)
                # next row
                accrual_start_date = self.parse_date(row[0])
                first_payment_date = accrual_start_date + periodicity.to_timedelta()
        else:
            s = AccrualCalculationSchedule()
            s.instrument = instrument
            if accrual_start_date:
                s.accrual_start_date = accrual_start_date
            if first_payment_date:
                s.first_payment_date = first_payment_date
            if accrual_size:
                s.accrual_size = accrual_size
            if accrual_calculation_model:
                s.accrual_calculation_model = accrual_calculation_model
            if periodicity:
                s.periodicity = periodicity

            accrual_calculation_schedules.append(s)

        return accrual_calculation_schedules

    def create_factor_schedules(self, instrument_download_scheme, instrument, values):
        factor_schedule_method = instrument_download_scheme.factor_schedule_method_id
        if factor_schedule_method != FactorScheduleDownloadMethod.DEFAULT:
            return []

        factor_schedule = values['FACTOR_SCHEDULE']

        # factor_schedule = [
        #     ['03/20/2013', '1.000000000'],
        #     ['08/20/2019', '.973684211'],
        # ]

        if factor_schedule and isinstance(factor_schedule, (list, tuple)):
            factor_schedules = []
            for r in factor_schedule:
                effective_date = self.parse_date(r[0])
                factor_value = self.parse_float(r[1])
                factor_schedules.append(
                    InstrumentFactorSchedule(
                        instrument=instrument,
                        effective_date=effective_date,
                        factor_value=factor_value
                    )
                )
                pass
            return factor_schedules

        return None

    def create_instrument_pricing(self, price_download_scheme, options, values, instruments, pricing_policies):
        date_from = parse_date_iso(options['date_from'])
        date_to = parse_date_iso(options['date_to'])
        is_yesterday = options['is_yesterday']
        fill_days = options['fill_days']
        # price_download_scheme_id = options['price_download_scheme_id']

        errors = {}
        prices = []

        if is_yesterday:
            for i in instruments:
                instr = self._bbg_instr(i.reference_for_pricing)
                instr_id = instr['id']
                instr_values = values.get(instr_id, None)
                if not instr_values:
                    continue

                instr_day_value = self.get_instrument_yesterday_values(price_download_scheme, instr_values)
                for pp in pricing_policies:
                    if pp.expr:
                        try:
                            principal_price = formula.safe_eval(pp.expr, names=instr_day_value)
                        except formula.InvalidExpression:
                            self.fail_pricing_policy(errors, pp, instr_day_value)
                        else:
                            if principal_price is not None:
                                price = PriceHistory(instrument=i, pricing_policy=pp, date=date_to,
                                                     principal_price=principal_price)
                                prices.append(price)
        else:
            for i in instruments:
                instr = self._bbg_instr(i.reference_for_pricing)
                instr_id = instr['id']
                instr_values = values.get(instr_id)
                if not instr_values:
                    continue

                for instr_day_value in instr_values:
                    d = parse_date_iso(instr_day_value['DATE'])
                    instr_day_value = self.get_instrument_history_values(price_download_scheme, instr_day_value)
                    for pp in pricing_policies:
                        if pp.expr:
                            try:
                                principal_price = formula.safe_eval(pp.expr, names=instr_day_value)
                            except formula.InvalidExpression:
                                self.fail_pricing_policy(errors, pp, instr_day_value)
                            else:
                                if principal_price is not None:
                                    price = PriceHistory(instrument=i, pricing_policy=pp, date=d,
                                                         principal_price=principal_price)
                                    prices.append(price)

        return prices, errors

    def create_currency_pricing(self, price_download_scheme, options, values, currencies, pricing_policies):
        date_from = parse_date_iso(options['date_from'])
        date_to = parse_date_iso(options['date_to'])
        is_yesterday = options['is_yesterday']
        fill_days = options['fill_days']
        # price_download_scheme_id = options['price_download_scheme_id']

        errors = {}
        prices = []

        if is_yesterday:
            for i in currencies:
                instr = self._bbg_instr(i.reference_for_pricing)
                instr_id = instr['id']
                instr_values = values.get(instr_id)
                if not instr_values:
                    continue

                instr_day_value = self.get_currency_history_values(price_download_scheme, instr_values)
                for pp in pricing_policies:
                    if pp.expr:
                        try:
                            fx_rate = formula.safe_eval(pp.expr, names=instr_day_value)
                        except formula.InvalidExpression:
                            self.fail_pricing_policy(errors, pp, instr_day_value)
                        else:
                            if fx_rate is not None:
                                price = CurrencyHistory(currency=i, pricing_policy=pp, date=date_to, fx_rate=fx_rate)
                                prices.append(price)
        else:
            for i in currencies:
                instr = self._bbg_instr(i.reference_for_pricing)
                instr_id = instr['id']
                instr_values = values.get(instr_id)
                if not instr_values:
                    continue

                for instr_day_value in instr_values:
                    d = parse_date_iso(instr_day_value['DATE'])
                    instr_day_value = self.get_currency_history_values(price_download_scheme, instr_day_value)
                    for pp in pricing_policies:
                        if pp.expr:
                            try:
                                fx_rate = formula.safe_eval(pp.expr, names=instr_day_value)
                            except formula.InvalidExpression:
                                self.fail_pricing_policy(errors, pp, instr_day_value)
                            else:
                                if fx_rate is not None:
                                    price = CurrencyHistory(currency=i, pricing_policy=pp, date=d, fx_rate=fx_rate)
                                    prices.append(price)

        return prices, errors


# ----------------------------------------------------------------------------------------------------------------------

class FakeBloombergDataProvider(BloombergDataProvider):
    """
    Bloomberg python client for Finmars.
    """

    def __init__(self, *args, **kwargs):
        super(FakeBloombergDataProvider, self).__init__(*args, **kwargs)
        from django.core.cache import caches
        self._cache = caches['default']

    @staticmethod
    def _new_response_id():
        return uuid.uuid4().hex

    @staticmethod
    def _make_key(key):
        return 'bloomberg.fake.%s' % key

    def _bbg_instr(self, code):
        allparts = code.split()
        parts = [p for p in allparts if not p.startswith('@')]
        overrides = [o[1:] for o in allparts if o.startswith('@')]
        if not parts:
            raise BloombergException('Invalid code')
        id0 = parts[0]
        try:
            yellowkey = parts[1]
        except IndexError:
            yellowkey = None

        ret = {"id": id0}
        if yellowkey:
            ret['yellowkey'] = yellowkey
        if overrides:
            ret['overrides'] = [{'field': 'PRICING_SOURCE', 'value': o} for o in overrides]
        return ret

    def get_fields(self):
        return 'fake'

    def get_instrument_send_request(self, instrument, fields):
        _l.info('> get_instrument_send_request: instrument="%s", fields=%s', instrument, fields)

        if settings.BLOOMBERG_SANDBOX_SEND_EMPTY:
            _l.info('< get_instrument_send_request: BLOOMBERG_SANDBOX_SEND_EMPTY')
            return None
        if settings.BLOOMBERG_SANDBOX_SEND_FAIL:
            _l.info('< get_instrument_send_request: BLOOMBERG_SANDBOX_SEND_FAIL')
            raise BloombergException('BLOOMBERG_SANDBOX_SEND_FAIL')

        if not instrument or not fields:
            _l.info('< response_id=%s', None)
            return None

        response_id = self._new_response_id()

        key = self._make_key(response_id)
        self._cache.set(key, {
            'action': 'instrument',
            'instrument': instrument,
            'fields': fields,
            'response_id': response_id,
        }, timeout=30)

        _l.info('< response_id=%s', response_id)

        return response_id

    def get_instrument_get_response(self, response_id):
        _l.info('> get_instrument_get_response: response_id=%s', response_id)

        if settings.BLOOMBERG_SANDBOX_WAIT_FAIL:
            _l.info('< get_instrument_get_response: BLOOMBERG_SANDBOX_WAIT_FAIL')
            raise BloombergException('BLOOMBERG_SANDBOX_WAIT_FAIL')

        if response_id is None:
            _l.info('< result=%s', None)
            return None

        key = self._make_key(response_id)
        req = self._cache.get(key)
        if not req:
            raise RuntimeError('invalid response_id')

        instr = req['instrument'].split(maxsplit=2)
        instr_id = instr[0]
        # instr_yellowkey = instr[1]

        fake_data = {
            "ACCRUED_FACTOR": "1.000000000",
            "CALC_TYP": "1",
            "CALC_TYP_DES": "STREET CONVENTION",
            "CNTRY_OF_RISK": "N.S.",
            "COUPON_FREQUENCY_DESCRIPTION": "S/A",
            "CPN": "5.375000",
            "CPN_FREQ": "2",
            "CPN_TYP": "FIXED",
            "CPN_TYP_SPECIFIC": "",
            "CRNCY": "USD",
            "CUR_CPN": "",
            "DAYS_TO_SETTLE": "2",
            "DAY_CNT": "20",
            "DAY_CNT_DES": "ISMA-30/360",
            "DES_NOTES": "",
            "FIRST_CPN_DT": "12/16/2016",
            "FIRST_SETTLE_DT": "06/16/2016",
            "ID_BB_GLOBAL": "BBG00D2QX2B8",
            "ID_CUSIP": "LW4068711",
            "ID_ISIN": instr_id,
            "INDUSTRY_SECTOR": "Industrial",
            "INDUSTRY_SUBGROUP": "Transport-Marine",
            "INT_ACC_DT": "06/16/2016",
            "ISSUER": "SCF CAPITAL LTD",
            "MATURITY": "06/16/2023",
            "MTY_TYP": "AT MATURITY",
            "OPT_PUT_CALL": "",
            "PAYMENT_RANK": "Sr Unsecured",
            "SECURITY_DES": "SCFRU 5 3/8 06/16/23",
            "SECURITY_TYP": "EURO-DOLLAR",
        }

        code = req['instrument']
        if 'cpn' in code or 'USP16394AG62' in code:
            fake_data['START_ACC_DT'] = "06/16/2016"
            fake_data['FIRST_CPN_DT'] = "07/16/2016"
            fake_data['CPN'] = '5.0000'
            fake_data['DAY_CNT'] = '30'
            fake_data['CPN_FREQ'] = '1'
            fake_data['MULTI_CPN_SCHEDULE'] = [
                ['08/20/2017', '5.0000'],
                ['02/20/2038', '6.7670']
            ]
        if 'factor' in code or 'USP16394AG62' in code:
            fake_data['FACTOR_SCHEDULE'] = [
                ['03/20/2013', '1.000000000'],
                ['08/20/2019', '.973684211'],
                ['02/20/2020', '.947368421'],
                ['08/20/2020', '.921052632'],
                ['02/20/2021', '.894736842'],
                ['08/20/2021', '.868421053'],
                ['02/20/2022', '.842105263'],
                ['08/20/2022', '.815789474'],
                ['02/20/2023', '.789473684'],
                ['08/20/2023', '.763157895'],
                ['02/20/2024', '.736842105'],
                ['08/20/2024', '.710526316'],
                ['02/20/2025', '.684210526'],
                ['08/20/2025', '.657894737'],
                ['02/20/2026', '.631578947'],
                ['08/20/2026', '.605263158'],
                ['02/20/2027', '.578947368'],
                ['08/20/2027', '.552631579'],
                ['02/20/2028', '.526315790'],
                ['08/20/2028', '.500000000'],
                ['02/20/2029', '.473684211'],
                ['08/20/2029', '.447368421'],
                ['02/20/2030', '.421052632'],
                ['08/20/2030', '.394736842'],
                ['02/20/2031', '.368421053'],
                ['08/20/2031', '.342105263'],
                ['02/20/2032', '.315789474'],
                ['08/20/2032', '.289473684'],
                ['02/20/2033', '.263157895'],
                ['08/20/2033', '.236842105'],
                ['02/20/2034', '.210526316'],
                ['08/20/2034', '.184210526'],
                ['02/20/2035', '.157894737'],
                ['08/20/2035', '.131578947'],
                ['02/20/2036', '.105263158'],
                ['08/20/2036', '.078947369'],
                ['02/20/2037', '.052631579'],
                ['08/20/2037', '.026315790']
            ]

        result = {}
        for field in req['fields']:
            result[field] = fake_data.get(field, None)
        _l.info('< result=%s', result)
        return result

    def get_pricing_latest_send_request(self, instruments, fields):
        _l.info('> get_pricing_latest_send_request: instruments=%s, fields=%s',
                 instruments, fields)

        if settings.BLOOMBERG_SANDBOX_SEND_EMPTY:
            _l.info('< get_pricing_latest_send_request: BLOOMBERG_SANDBOX_SEND_EMPTY')
            return None
        if settings.BLOOMBERG_SANDBOX_SEND_FAIL:
            _l.info('< get_pricing_latest_send_request: BLOOMBERG_SANDBOX_SEND_FAIL')
            raise BloombergException('BLOOMBERG_SANDBOX_SEND_FAIL')

        if not instruments or not fields:
            _l.info('< response_id=%s', None)
            return None

        response_id = self._new_response_id()
        # if not fields:
        #     fields = ['PX_YEST_BID', 'PX_YEST_ASK', 'PX_YEST_CLOSE', 'PX_CLOSE_1D', 'ACCRUED_FACTOR', 'CPN',
        #               'SECURITY_TYP']

        key = self._make_key(response_id)
        self._cache.set(key, {
            'action': 'pricing_latest',
            'instruments': instruments,
            'fields': fields,
            'response_id': response_id,
        }, timeout=30)

        _l.info('< response_id=%s', response_id)

        return response_id

    def get_pricing_latest_get_response(self, response_id):
        _l.info('> get_pricing_latest_get_response: response_id=%s', response_id)

        if settings.BLOOMBERG_SANDBOX_WAIT_FAIL:
            _l.info('< get_pricing_latest_get_response: BLOOMBERG_SANDBOX_WAIT_FAIL')
            raise BloombergException('BLOOMBERG_SANDBOX_WAIT_FAIL')

        if response_id is None:
            _l.info('< result=%s', None)
            return None

        fake_data = {
            "ACCRUED_FACTOR": "1.000000000",
            "CPN": "6.625000",
            # "PX_CLOSE_1D": "N.S.",
            # "PX_YEST_ASK": "N.S.",
            # "PX_YEST_BID": "N.S.",
            # "PX_YEST_CLOSE": "N.S.",
            # "PX_CLOSE_1D": "N.S.",
            "PX_YEST_ASK": "10.0",
            "PX_YEST_BID": "11.0",
            "PX_YEST_CLOSE": "12.0",
            "SECURITY_TYP": "EURO-DOLLAR",

            "PX_ASK": "20.0",
            "PX_BID": "21.0",
            "PX_LAST": "22.0",
        }

        key = self._make_key(response_id)
        req = self._cache.get(key)
        if not req:
            raise RuntimeError('invalid response_id')

        instruments = req['instruments'] or []
        fields = req['fields']

        result = {}
        for instrument in instruments:
            instr = self._bbg_instr(instrument)
            instr_id = instr['id']
            price_empty = 'priceempty' in instr_id

            if 'skip' in instr_id:
                continue

            instrument_fields = {}
            for field in fields:
                if price_empty and field:
                    instrument_fields[field] = 'N.S.'
                else:
                    instrument_fields[field] = fake_data.get(field, None)

            result[instr_id] = instrument_fields
        _l.info('< result=%s', result)
        return result

    def get_pricing_history_send_request(self, instruments, fields, date_from, date_to):
        _l.info('> get_pricing_history_send_request: instrument=%s, date_from=%s, date_to=%s',
                 instruments, date_from, date_to)

        if settings.BLOOMBERG_SANDBOX_SEND_EMPTY:
            _l.info('< get_pricing_history_send_request: BLOOMBERG_SANDBOX_SEND_EMPTY')
            return None
        if settings.BLOOMBERG_SANDBOX_SEND_FAIL:
            _l.info('< get_pricing_history_send_request: BLOOMBERG_SANDBOX_SEND_FAIL')
            raise BloombergException('BLOOMBERG_SANDBOX_SEND_FAIL')

        if not instruments or not fields or not date_from or not date_to:
            _l.info('< response_id=%s', None)
            return None

        response_id = self._new_response_id()

        # if not fields:
        #     fields = ['PX_BID', 'PX_ASK', 'PX_LAST']

        key = self._make_key(response_id)
        self._cache.set(key, {
            'action': 'pricing_history',
            'instruments': instruments,
            'fields': fields,
            'date_from': '%s' % date_from,
            'date_to': '%s' % date_to,
            'response_id': response_id,
        }, timeout=30)

        _l.info('< response_id=%s', response_id)

        return response_id

    def get_pricing_history_get_response(self, response_id):
        _l.info('> get_pricing_history_get_response: response_id=%s', response_id)

        if settings.BLOOMBERG_SANDBOX_WAIT_FAIL:
            _l.info('< get_pricing_history_get_response: BLOOMBERG_SANDBOX_WAIT_FAIL')
            raise BloombergException('BLOOMBERG_SANDBOX_WAIT_FAIL')

        if response_id is None:
            _l.info('< result=%s', None)
            return None

        fake_data = {
            "DATE": "<REPLACE>",
            "PX_ASK": "20.0",
            "PX_BID": "21.0",
            "PX_LAST": "22.0",
        }

        key = self._make_key(response_id)
        req = self._cache.get(key)
        if not req:
            raise RuntimeError('invalid response_id')

        instrs = req['instruments'] or []
        fields = req['fields']
        date_from = parser.parse(req['date_from']).date()
        date_to = parser.parse(req['date_to']).date()

        result = {}
        for instrument in instrs:
            instr = self._bbg_instr(instrument)
            instr_id = instr['id']
            price_empty = 'priceempty' in instr_id

            if 'skip' in instr_id:
                continue

            d = date_from
            while d <= date_to:
                price_fields = {'DATE': d}
                for i, field in enumerate(fields):
                    if price_empty:
                        price_fields[field] = 'N.S.'
                    else:
                        price_fields[field] = fake_data.get(field, None)

                if instr_id in result:
                    result[instr_id].append(price_fields)
                else:
                    result[instr_id] = [price_fields]

                d += timedelta(days=1)
        _l.info('< result=%s', result)
        return result

    def get_test_certificate_send_request(self):
        _l.info('> get_test_certificate_send_request:')

        if settings.BLOOMBERG_SANDBOX_SEND_EMPTY:
            _l.info('< get_pricing_latest_send_request: BLOOMBERG_SANDBOX_SEND_EMPTY')
            return None
        if settings.BLOOMBERG_SANDBOX_SEND_FAIL:
            _l.info('< get_pricing_latest_send_request: BLOOMBERG_SANDBOX_SEND_FAIL')
            raise BloombergException('BLOOMBERG_SANDBOX_SEND_FAIL')

        return True

    def get_test_certificate_get_response(self, response_id):
        return {
            "is_authorized": True
        }
