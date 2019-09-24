from __future__ import unicode_literals

import logging
from threading import local

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core import serializers
from django.core.signals import request_finished
from django.db import transaction
from django.db.models.signals import post_init, post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.utils.decorators import ContextDecorator

from poms.common.middleware import get_request

_l = logging.getLogger('poms.audit')

_state = local()


def _is_accept(model):
    from poms.audit.models import ObjectHistory4Entry
    from poms.common.models import AbstractClassModel
    from poms.integrations.models import Task

    app_label = getattr(model._meta, 'app_label', None)
    if app_label not in ['users', 'chats', 'tags', 'accounts', 'counterparties', 'currencies', 'instruments',
                         'integrations', 'portfolios', 'strategies', 'transactions', ]:
        return False
    if issubclass(model, (AbstractClassModel, Task, ObjectHistory4Entry)):
        return False
    return True


def _is_send_instance_notifications(instance):
    from poms.portfolios.models import Portfolio
    from poms.accounts.models import Account
    from poms.accounts.models import AccountType
    from poms.counterparties.models import Responsible, Counterparty
    from poms.instruments.models import Instrument, InstrumentType, PricingPolicy, PriceHistory
    from poms.currencies.models import Currency, CurrencyHistory
    from poms.transactions.models import TransactionType
    from poms.chats.models import ThreadGroup, Thread
    from poms.strategies.models import Strategy1, Strategy2, Strategy3
    return isinstance(instance, (Portfolio, Account, AccountType, Responsible, Counterparty, Instrument,
                                 InstrumentType, PricingPolicy, Currency, TransactionType, PriceHistory,
                                 CurrencyHistory, ThreadGroup, Thread, Strategy1, Strategy2, Strategy3,))


def _is_has_object_permissions(instance):
    from poms.portfolios.models import Portfolio
    from poms.accounts.models import Account
    from poms.accounts.models import AccountType
    from poms.counterparties.models import Responsible, Counterparty
    from poms.instruments.models import Instrument, InstrumentType, PriceHistory
    from poms.transactions.models import TransactionType
    from poms.chats.models import ThreadGroup, Thread
    from poms.strategies.models import Strategy1, Strategy2, Strategy3
    return isinstance(instance, (Portfolio, Account, AccountType, Responsible, Counterparty, Instrument,
                                 InstrumentType, TransactionType, PriceHistory, ThreadGroup, Thread, Strategy1,
                                 Strategy2, Strategy3,))


_history_model_list = None


def get_history_model_list():
    global _history_model_list
    if _history_model_list is None:
        _history_model_list = tuple(m for m in apps.get_models() if _is_accept(m))
    return _history_model_list


def get_history_model_content_type_list():
    return [ContentType.objects.get_for_model(model).pk for model in get_history_model_list()]


def activate():
    _state.active = True

    _state.flag = None
    set_flag_addition()

    _state.actor_content_object = None
    _state.actor_content_object_id = None
    _state.entries4 = []


def deactivate():
    from poms.audit.models import ObjectHistory4Entry
    from poms.notifications import send_instance_created, send_instance_changed, send_instance_deleted

    changed_notif_already_sent = set()
    if getattr(_state, "active", True) and _state.entries4:
        if _state.actor_content_object:
            if transaction.get_rollback():
                return
            group_id = 0
            actor_content_type = ContentType.objects.get_for_model(_state.actor_content_object)
            actor_object_id = _state.actor_content_object_id
            actor_object_repr = str(_state.actor_content_object)
            user = get_request().user

            for e in _state.entries4:
                e.master_user = user.master_user
                e.member = user.member
                e.group_id = group_id

                e.actor_content_type = actor_content_type
                e.actor_object_id = actor_object_id
                e.actor_object_repr = actor_object_repr

                e.save()

                if group_id == 0:
                    group_id = e.id
                    e.group_id = group_id
                    e.save(update_fields=['group_id'])

                original_instance = getattr(e, 'original_instance', None)
                if original_instance:
                    is_send = _is_send_instance_notifications(original_instance)
                    check_perms = _is_has_object_permissions(original_instance)
                    if is_send:
                        if e.action_flag == ObjectHistory4Entry.ADDITION:
                            send_instance_created(user.master_user, user.member, original_instance,
                                                  check_perms=check_perms)
                        elif e.action_flag == ObjectHistory4Entry.CHANGE:
                            if original_instance.id not in changed_notif_already_sent:
                                send_instance_changed(user.master_user, user.member, original_instance,
                                                      check_perms=check_perms)
                                changed_notif_already_sent.add(original_instance.id)
                        elif e.action_flag == ObjectHistory4Entry.DELETION:
                            send_instance_deleted(user.master_user, user.member, original_instance,
                                                  check_perms=check_perms)
        else:
            _l.debug('actor_content_object is not defined (maybe registration)')

    if hasattr(_state, "active"):
        del _state.active
    if hasattr(_state, "flag"):
        del _state.flag
    if hasattr(_state, "actor_content_object"):
        del _state.actor_content_object
    if hasattr(_state, "actor_content_object_id"):
        del _state.actor_content_object_id
    if hasattr(_state, "entries4"):
        del _state.entries4


# @receiver([request_finished, got_request_exception], dispatch_uid='poms_history_cleanup')
@receiver(request_finished, dispatch_uid='poms_history_cleanup')
def _cleanup(**kwargs):
    if hasattr(_state, "active"):
        del _state.active
    if hasattr(_state, "flag"):
        del _state.flag
    if hasattr(_state, "actor_content_object"):
        del _state.actor_content_object
    if hasattr(_state, "actor_content_object_id"):
        del _state.actor_content_object_id
    if hasattr(_state, "entries4"):
        del _state.entries4


# request_finished.connect(_cleanup, dispatch_uid='poms_history_cleanup')
# got_request_exception.connect(_cleanup, dispatch_uid='poms_history_cleanup.exception')


def is_active():
    return getattr(_state, "active", False)


def set_actor_content_object(obj):
    _state.actor_content_object = obj
    _state.actor_content_object_id = obj.id


def set_flag_addition():
    from poms.audit.models import ObjectHistory4Entry

    _state.flag = ObjectHistory4Entry.ADDITION


def set_flag_change():
    from poms.audit.models import ObjectHistory4Entry

    _state.flag = ObjectHistory4Entry.CHANGE


def set_flag_deletion():
    from poms.audit.models import ObjectHistory4Entry

    _state.flag = ObjectHistory4Entry.DELETION


# class enable(ContextDecorator):
#     def __enter__(self):
#         activate()
#
#     def __exit__(self, exc_type, exc_value, traceback):
#         deactivate()


class History(ContextDecorator):
    def __init__(self):
        self.is_owner = False

    def __enter__(self):
        if is_active():
            return
        self.is_owner = True
        activate()

    def __exit__(self, exc_type, exc_value, traceback):
        if self.is_owner:
            deactivate()
        else:
            # write collected data
            flag = _state.flag
            actor_content_object = _state.actor_content_object
            actor_content_object_id = _state.actor_content_object_id

            deactivate()
            activate()

            _state.flag = flag
            _state.actor_content_object = actor_content_object
            _state.actor_content_object_id = actor_content_object_id


def enable(using=None):
    if callable(using):
        return History()(using)
    else:
        return History()


def _is_enabled_for_model(obj):
    return isinstance(obj, get_history_model_list())


def _fields_to_set(fields):
    ret = set()
    for k, v in fields.items():
        if isinstance(v, list):
            ret.add((k, tuple(v)))
        else:
            ret.add((k, v))
    return ret


def _serialize(obj):
    val = serializers.serialize('python', [obj])[0]
    if val['model'] == 'transactions.transactiontype':
        val['fields'].pop('book_transaction_layout_json')
    return val


def _get_model(content_type):
    app_label, model = content_type.split('.')
    return ContentType.objects.get_by_natural_key(app_label, model).model_class()


def _get_content_type(instance):
    content_type = ContentType.objects.get_for_model(instance)
    return '%s.%s' % (content_type.app_label, content_type.model)


def _value_to_str(value):
    if isinstance(value, str):
        return value
    elif isinstance(value, bool):
        return 'true' if value else 'false'
    else:
        return str(value)


@receiver(post_init, dispatch_uid='poms_history_post_init')
def _instance_post_init(sender, instance=None, **kwargs):
    if not is_active():
        return
    if not _is_enabled_for_model(instance):
        return
    if instance.pk:
        instance._poms_history_initial_state = _serialize(instance)
    else:
        instance._poms_history_initial_state = {'pk': None, 'fields': {}}


@receiver(post_save, dispatch_uid='poms_history_post_save')
def _instance_post_save(sender, instance=None, created=None, **kwargs):
    from poms.audit.models import ObjectHistory4Entry

    if not is_active():
        return False
    if not _is_enabled_for_model(instance):
        return
    if not hasattr(instance, '_poms_history_initial_state'):
        return

    # _l.debug('post_save: sender=%s, instance=%s, created=%s, kwargs=%s',
    #          sender, instance, created, kwargs)

    if created:
        e4 = ObjectHistory4Entry(
            action_flag=ObjectHistory4Entry.ADDITION,
            content_type=ContentType.objects.get_for_model(instance),
            object_id=instance.id,
            object_repr=str(instance)
        )
        e4.original_instance = instance
        _state.entries4.append(e4)

    else:
        i = instance._poms_history_initial_state
        c = _serialize(instance)

        if c['pk'] == i['pk']:
            cfields = _fields_to_set(c['fields'])
            ifileds = _fields_to_set(i['fields'])
            changed = ifileds - cfields
            # fields = []
            for attr, v in changed:
                f = instance._meta.get_field(attr)
                old_value = i['fields'].get(attr, None)
                new_value = c['fields'].get(attr, None)

                _l.debug('post_save: changed field "%s": %s -> %s', f, old_value, new_value)

                e4 = ObjectHistory4Entry(
                    # action_flag=ObjectHistory4Entry.CHANGE,
                    action_flag=_state.flag,
                    content_type=ContentType.objects.get_for_model(instance),
                    object_id=instance.id,
                    object_repr=str(instance),

                    field_name=str(f.name)
                )
                e4.original_instance = instance

                if f.one_to_one:
                    _l.warn('_instance_post_save: one_to_one')
                    pass
                elif f.one_to_many:
                    _l.warn('_instance_post_save: one_to_many')
                    pass
                elif f.many_to_one:
                    fctype = ContentType.objects.get_for_model(f.related_model)

                    if new_value:
                        e4.value_content_type = fctype
                        e4.value_object_id = new_value
                        e4.value = str(fctype.get_object_for_this_type(pk=new_value))

                    if old_value:
                        e4.old_value_content_type = fctype
                        e4.old_value_object_id = old_value
                        e4.old_value = str(fctype.get_object_for_this_type(pk=old_value))

                    _state.entries4.append(e4)
                elif f.many_to_many:
                    pass
                else:
                    e4.value = _value_to_str(new_value)
                    e4.old_value = _value_to_str(old_value)
                    _state.entries4.append(e4)


@receiver(m2m_changed, dispatch_uid='poms_history_m2m_changed')
def _instance_m2m_changed(sender, instance=None, action=None, reverse=None, model=None, pk_set=None, **kwargs):
    from poms.audit.models import ObjectHistory4Entry

    if not is_active():
        return False
    if not _is_enabled_for_model(instance):
        return
    if not hasattr(instance, '_poms_history_initial_state'):
        return

    _l.debug('m2m_changed.%s: sender=%s, instance=%s, reverse=%s, model=%s, pk_set=%s, kwargs=%s',
             action, sender, instance, reverse, model, pk_set, kwargs)

    # if _state.flag == ObjectHistory4Entry.ADDITION:
    #     return

    if action not in ['pre_remove', 'pre_add']:
        return

    attr = None
    attr_ctype = ContentType.objects.get_for_model(model)
    # find attribute name
    for f in instance._meta.get_fields():
        if f.many_to_many:
            if f.auto_created:
                if f.through == sender:
                    attr = f.related_name
                    break
            else:
                if f.rel.through == sender:
                    attr = f.name
                    break
    if attr is None:
        return

    if attr not in instance._poms_history_initial_state:
        instance._poms_history_initial_state[attr] = [o.pk for o in getattr(instance, attr).all()]

    for pk in pk_set:
        e4 = ObjectHistory4Entry(
            content_type=ContentType.objects.get_for_model(instance),
            object_id=instance.id,
            object_repr=str(instance),

            field_name=str(attr),
            value_content_type=attr_ctype,
            value_object_id=pk,
            value=str(attr_ctype.get_object_for_this_type(pk=pk))
        )

        if action == 'pre_add':
            e4.action_flag = ObjectHistory4Entry.M2M_ADDITION
            _state.entries4.append(e4)
        elif action == 'pre_remove':
            e4.action_flag = ObjectHistory4Entry.M2M_DELETION
            _state.entries4.append(e4)


@receiver(post_delete, dispatch_uid='poms_history_on_delete')
def _instance_post_delete(sender, instance=None, **kwargs):
    from poms.audit.models import ObjectHistory4Entry

    if not is_active():
        return False
    if not _is_enabled_for_model(instance):
        return

    _l.debug('post_delete: sender=%s, instance=%s, kwargs=%s',
             sender, instance, kwargs)

    e4 = ObjectHistory4Entry(
        action_flag=ObjectHistory4Entry.DELETION,
        content_type=ContentType.objects.get_for_model(instance),
        object_id=instance.id,
        object_repr=str(instance)
    )
    e4.original_instance = instance
    _state.entries4.append(e4)
