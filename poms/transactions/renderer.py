import logging

_l = logging.getLogger('poms.transactions.renderer')

#
# class ComplexTransactionRenderer(object):
#     def __init__(self, ):
#         pass
#
#     def render(self, complex_transaction, context):
#         transactions = list(complex_transaction.transactions.all())
#
#         transaction_serializer = TransactionSerializer(instance=transactions, many=True, context=context)
#         transactions_data = transaction_serializer.data
#
#         transactions_data = self._process_object(transactions_data)
#
#         # instruments_data = {}
#         # for transaction in complex_transaction.transactions.all():
#         #     instrument = transaction.instrument
#         #     if instrument.id not in instruments_data:
#         #         instrument_serializer = RenderingInstrumentSerializer(instance=instrument, context=context)
#         #         instruments_data[instrument.id] = instrument_serializer.data
#         #
#         # for transaction_data in transactions_data:
#         #     for key, value in transaction_data.items():
#         #         if key == 'instrument':
#         #             transaction_data['instrument'] = instruments_data[value]
#         #             transaction_data['instrument_object'] = instruments_data[value]
#         #         if key == 'instrument_object':
#         #             pass
#         #         elif key.endswith('_object'):
#         #             tkey = key[:-7]
#         #             transaction_data[tkey] = value
#
#         # _l.debug(json.dumps(transactions_data, indent=2))
#
#         transaction_type = complex_transaction.transaction_type
#         display_expr = transaction_type.display_expr
#         if display_expr:
#             try:
#                 ret = formula.safe_eval(display_expr, names={
#                     'code': complex_transaction.code,
#                     'transactions': transactions_data,
#                 })
#                 return str(ret)
#             except formula.InvalidExpression:
#                 _l.debug('Invalid display expression: transaction_type=%s, display_expr="%s"',
#                          transaction_type.id, transaction_type.display_expr,
#                          exc_info=True)
#                 return gettext_lazy('Invalid transaction type display expression.')
#         return gettext_lazy('Empty transaction type display expression.')
#
#     def _process_object(self, data):
#         if isinstance(data, (list, tuple)):
#             ret = []
#             for value in data:
#                 ret.append(self._process_object(value))
#             return ret
#         elif isinstance(data, (dict, OrderedDict)):
#             ret = OrderedDict()
#             skip = set()
#             for key, value in data.items():
#                 if key in ['granted_permissions', 'object_permissions', 'user_object_permissions',
#                            'group_object_permissions']:
#                     pass
#                 elif key.endswith('_object'):
#                     tkey = key[:-7]
#                     skip.add(tkey)
#                     value = self._process_object(value)
#                     ret[tkey] = value
#                     # ret[key] = value
#                     ret.pop(key, None)
#                 elif key not in skip:
#                     ret[key] = self._process_object(value)
#             return ret
#         else:
#             return data
