from logging import getLogger

from celery import shared_task, current_task

from poms.celery_tasks import finmars_task
from poms.users.models import MasterUser

_l = getLogger('poms.users')


@finmars_task(name='users.clone_master_user', bind=True)
def clone_master_user(self, instance, name, current_user):
    from poms.users.cloner import FullDataCloner

    reference_master_user = MasterUser.objects.get(id=instance.reference_master_user)

    copy_settings = {
        "members": True
    }

    try:

        cloner = FullDataCloner(source_master_user=reference_master_user, name=instance.name,
                                copy_settings=copy_settings, current_user=current_user)
        new_master_user = cloner.clone()

    except Exception as e:
        _l.debug("Clone Master User Exception ")
        _l.debug(e)

    setattr(instance, 'task_id', current_task.request.id)

    return instance
