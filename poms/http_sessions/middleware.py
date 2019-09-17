from __future__ import unicode_literals

try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    MiddlewareMixin = object


class SessionMiddleware(MiddlewareMixin):
    # def process_request(self, request):
    #     if hasattr(request, 'session'):
    #         if request.session.get('user_agent', None) != request.user_agent:
    #             request.session['user_agent'] = request.user_agent
    #
    #         if request.session.get('user_ip', None) != request.user_ip:
    #             request.session['user_ip'] = request.user_ip

    def process_response(self, request, response):
        if hasattr(request, 'session') and hasattr(request, 'user') and request.user.is_authenticated:
            if request.session.get('user_agent', None) != request.user_agent:
                request.session['user_agent'] = request.user_agent
            if request.session.get('user_ip', None) != request.user_ip:
                request.session['user_ip'] = request.user_ip
        return response
