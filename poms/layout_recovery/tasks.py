import logging

from celery import shared_task

from poms.layout_recovery.handlers import LayoutArchetypeGenerateHandler, LayoutFixHandler

_l = logging.getLogger('poms.layout_recovery')


@shared_task(name='layout_recovery.generate_layout_archetype', bind=True)
def generate_layout_archetype(self, instance):
    _l.debug('generate_layout_archetype init')

    handler = LayoutArchetypeGenerateHandler()
    handler.process()

    return instance


@shared_task(name='layout_recovery.fix_layout', bind=True)
def fix_layout(self, instance):
    _l.debug('fix_layout init')

    handler = LayoutFixHandler()

    handler.process()

    return instance
