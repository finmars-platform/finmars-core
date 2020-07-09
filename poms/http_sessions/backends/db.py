from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore as DjangoSessionStore




class SessionStore(DjangoSessionStore):
    @classmethod
    def get_model_class(cls):
        from poms.http_sessions.models import Session
        return Session

    def create_model_instance(self, data):

        from poms.users.models import UserProfile

        obj = super(SessionStore, self).create_model_instance(data)

        try:
            user_id = int(data.get('_auth_user_id'))
        except (ValueError, TypeError):
            user_id = None
        if user_id:
            user_model = get_user_model()
            obj.user = user_model.objects.get(pk=user_id)

        obj.user_agent = data.get('user_agent', None)
        obj.user_ip = data.get('user_ip', None)



        try:
            master_user_id = int(data.get('current_master_user', None))
        except (ValueError, TypeError):
            master_user_id = None

        print('data %s' % data)
        print('create_model_instance master_user_id %s' % master_user_id)

        if obj.user:

            print("Trying to take last master user from User Profile")

            user_profile = UserProfile.objects.get(user=obj.user)

            if user_profile.active_master_user:

                print("Master user successfully taken from User Profile")

                obj.current_master_user = user_profile.active_master_user

        if not obj.current_master_user:

            if master_user_id:
                from poms.users.models import MasterUser

                print("Trying to take by master user id")

                obj.current_master_user = MasterUser.objects.get(pk=master_user_id)

        return obj
