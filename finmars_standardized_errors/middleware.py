import datetime
import json
import re
import traceback
from http import HTTPStatus

from django.http import HttpResponse
from django.utils.timezone import now

from finmars_standardized_errors.models import ErrorRecord

try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    MiddlewareMixin = object

import logging

_l = logging.getLogger('finmars')


class ExceptionMiddleware(MiddlewareMixin):
    '''Finmars Error Handler Middleware
    Idea is unify all error responses of all backend microservices

    check process_exception method

    '''

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        ''' Method that overrides default exception response

        :param request: Request object
        :param exception: Application error
        :return: Return is object with fixed error structure in JSON
        '''
        # print('process_exception.exception %s' % exception)

        _l.error("ExceptionMiddleware process error %s" % request.build_absolute_uri())
        _l.error(traceback.format_exc())

        lines = traceback.format_exc().splitlines()[-6:]
        traceback_lines = []

        http_code_to_message = {v.value: v.description for v in HTTPStatus}

        for line in lines:
            traceback_lines.append(re.sub(r'File ".*[\\/]([^\\/]+.py)"', r'File "\1"', line))

        url = request.build_absolute_uri()
        username = str(request.user.username)
        status_code = getattr(exception, 'status_code', 500)
        message = http_code_to_message[status_code]

        details = {
            'traceback': '\n'.join(traceback_lines),
            'error_message': repr(exception),
        }

        if getattr(exception, 'error_key', None):
            details['error_key'] = exception.error_key

        data = {
            'error': {
                'url': url,
                'username': username,
                'details': details,
                'message': message,
                'status_code': status_code,
                'datetime': str(datetime.datetime.strftime(now(), '%Y-%m-%d %H:%M:%S'))
            }
        }

        ErrorRecord.objects.create(url=url, username=username, status_code=status_code, message=message, details={
            'traceback': '\n'.join(traceback_lines),
            'error_message': repr(exception),
        })

        response_json = json.dumps(data, indent=2, sort_keys=True)

        return HttpResponse(response_json, status=status_code, content_type="application/json")
