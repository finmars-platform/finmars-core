from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy


class PhoneNumberValidator(object):
    code = 'invalid'
    message = ugettext_lazy('Enter a valid phone number.')

    def __init__(self):
        pass

    def __call__(self, value):
        # raise ValidationError(self.message, code=self.code)
        return True




# class UserCodeUniqueValidator(UniqueTogetherValidator):
#     def __init__(self, *args, **kwargs):
#         super(UserCodeUniqueValidator, self).__init__(*args, **kwargs)
#         self.fields = ['master_user', 'user_code']
#
#     def __call__(self, attrs):
#         attrs = attrs.copy()
#         user_code = attrs.get('user_code', None)
#         if not user_code:
#             name = attrs.get('name', "")
#             user_code = Truncator(name).chars(25)
#             attrs['user_code'] = user_code
#         super(UserCodeUniqueValidator,self).__call__(attrs)
