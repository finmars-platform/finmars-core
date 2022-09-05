from celery import shared_task

from poms.common.models import ProxyRequest, ProxyUser

import logging
_l = logging.getLogger('poms.common')


@shared_task(name='common.run_data_procedure_from_formula', bind=True)
def run_data_procedure_from_formula(self, master_user_id, member_id, user_code,user_context,  **kwargs):

    _l.info('run_data_procedure_from_formula init')

    from poms.users.models import MasterUser
    from poms.users.models import Member
    from poms.procedures.models import RequestDataFileProcedure

    master_user = MasterUser.objects.get(id=master_user_id)

    member = Member.objects.get(id=member_id)

    proxy_user = ProxyUser(self.member, self.master_user)
    proxy_request = ProxyRequest(proxy_user)

    context = {
        'request': proxy_request
    }

    merged_context = {}
    merged_context.update(context)

    if user_context:
        merged_context['names'].update(user_context)


    procedure = RequestDataFileProcedure.objects.get(master_user=master_user, user_code=user_code)

    kwargs.pop('user_context', None)

    from poms.procedures.handlers import RequestDataFileProcedureProcess
    instance = RequestDataFileProcedureProcess(procedure=procedure, master_user=master_user, member=member,
                                               context=merged_context, **kwargs)
    instance.process()