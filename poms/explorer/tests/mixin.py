class CreateUserMemberMixin:
    def create_user_member(self):
        from poms.users.models import Member
        from django.contrib.auth.models import User

        user = User.objects.create_user(username="testuser")
        member, _ = Member.objects.get_or_create(
            user=user,
            master_user=self.master_user,
            username="testuser",
            defaults=dict(
                is_admin=False,
                is_owner=False,
            ),
        )
        user.member = member
        user.save()
        self.client.force_authenticate(user=user)
        return user, member
