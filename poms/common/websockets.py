# DEPRECATED since 2023-02-07

# import json
# import traceback
# from logging import getLogger
#
# import websockets
# from django.conf import settings
#
# _l = getLogger('poms.common')
#
# import asyncio
# import datetime
# from datetime import date
#
# event_loop = asyncio.new_event_loop()
#
#
# async def send_message(message):
#     try:
#
#         uri = settings.WEBSOCKET_HOST
#         async with websockets.connect(
#                 uri,
#                 extra_headers=[('finmars-app', settings.WEBSOCKET_APP_TOKEN)]
#         ) as websocket:
#             await websocket.send(message)
#
#     except Exception as error:
#         _l.debug('Websocket send message error %s' % error)
#
#
# # LEVELS
# # System - to everyone on finmars shard
# # Ecosystem - to every member in master user
# # Member - to specific member
#
# def jsonconverter(o):
#     if isinstance(o, datetime.datetime):
#         return o.__str__()
#     if isinstance(o, date):
#         return o.__str__()
#
#
# def send_websocket_message(data, level='system', context=None):
#     if settings.USE_WEBSOCKETS:
#
#         try:
#
#             message = {
#                 "level": level,
#                 "master_user": None,
#                 "member": None,
#                 "data": data
#             }
#
#             context = context or {}
#             request = context.get('request', None)
#
#             # _l.info('context %s' % context)
#             # _l.info('request %s' % request)
#
#             master_user = None
#             member = None
#
#             if request:
#                 master_user = request.user.master_user
#                 if request.user.member:
#                     member = request.user.member
#
#             elif context.get('master_user', None) and not master_user:
#                 master_user = context.get('master_user')
#
#             if context.get('member', None) and not member:
#                 member = context.get('member')
#
#             message['master_user'] = {
#                 "id": master_user.id,
#                 "unique_id": str(master_user.unique_id),
#                 "token": master_user.token
#             }
#
#             message['member'] = {
#                 "id": member.id,
#                 "username": member.username
#             }
#
#             # _l.debug('send_websocket_message %s' % data)
#
#             # _l.info('message %s' % message)
#
#             json_message = json.dumps(message, default=jsonconverter)
#             # json_message = json.dumps(message)
#
#             event_loop.run_until_complete(send_message(json_message))
#
#         except Exception as e:
#
#             _l.error("Websocket Exception %s" % e)
#             _l.error("Websocket Traceback %s" % traceback.format_exc())
