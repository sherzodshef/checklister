import logging
from collections import defaultdict
from typing import Dict

import telegram

# Local imports
from tgbot import localization
from tgbot.models import User, Checklist, Task

log = logging.getLogger('User menu')
loc = localization.Localization(
    language='ru',
    fallback='ru'
)


def receiver(update, context):
    if len(context.user_data) == 0:
        context.user_data[0] = {'current_menu': loc.get('button_main_menu'),
                                'current_kb': {loc.get('button_some_menu'): 'some_menu'},
                                'last_msg_id': None,
                                'task': None,
                                'checklist': None}
    print(context.user_data)

    if update.callback_query is not None:
        update.callback_query.answer()
        print(update.callback_query)
        if update.callback_query.data in context.user_data[0]['current_kb']:
            pressed = update.callback_query.data
        else:
            pressed = loc.get('button_main_menu')
    else:
        if update.message.text in context.user_data[0]['current_kb']:
            pressed = update.message.text
        else:
            return
    try:
        checklist = Checklist.objects.filter(shortname=pressed).first()
        context.user_data[0]['checklist'] = checklist
    except Exception as e:
        log.error(f'{e}')
        context.user_data[0]['checklist'] = None

    next_menu = context.user_data[0]['current_kb'].get(pressed)
    possibles = globals().copy()
    possibles.update(locals())
    method = possibles.get(next_menu)
    if not method:
        raise NotImplementedError("Method %s not implemented" % next_menu)
    if context.user_data[0]['last_msg_id'] is not None:
        try:
            context.bot.delete_message(update.message.chat.id, context.user_data[0]['last_msg_id'])
            context.user_data[0]['last_msg_id'] = None
        except AttributeError as e:
            try:
                context.bot.delete_message(update.callback_query.message.chat.id, context.user_data[0]['last_msg_id'])
                context.user_data[0]['last_msg_id'] = None
            except Exception as e:
                print(f'{e}')
    method(update, context)


def main_menu(update, context):
    buttons = [[telegram.KeyboardButton(loc.get('button_some_menu'))],
               [telegram.KeyboardButton(loc.get('button_checklists_menu'))]]
    reply_markup = telegram.ReplyKeyboardMarkup(buttons, resize_keyboard=True)

    user = User.get_user(update, context)
    try:
        message = context.bot.send_message(update.message.chat.id, loc.get('conv_opened_main_menu',
                                                                           first_name=user.first_name),
                                           reply_markup=reply_markup)
    except AttributeError:
        message = context.bot.send_message(update.callback_query.message.chat.id, loc.get('conv_opened_main_menu',
                                                                                          first_name=user.first_name),
                                           reply_markup=reply_markup)

    context.user_data[0]['current_menu'] = loc.get('button_main_menu')
    context.user_data[0]['current_kb'] = {loc.get('button_some_menu'): 'some_menu',
                                          loc.get('button_checklists_menu'): 'checklists_menu'}
    context.user_data[0]['last_msg_id'] = message.message_id


def some_menu(update, context):
    context.user_data[0] = {'current_menu': loc.get('button_some_menu'),
                            'current_kb': {loc.get('button_go_back'): 'main_menu'},
                            'last_msg_id': None,
                            'task': None,
                            'checklist': None}
    buttons = [[telegram.KeyboardButton(loc.get('button_go_back'))]]
    reply_markup = telegram.ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    message = context.bot.send_message(update.message.chat.id, loc.get('conv_opened_some_menu'),
                                       reply_markup=reply_markup)
    context.user_data[0]['last_msg_id'] = message.message_id


def checklists_menu(update, context):
    reply_kb = [[telegram.KeyboardButton(loc.get('button_go_back'))]]
    current_kb = {loc.get('button_go_back'): 'main_menu'}
    checklists = Checklist.objects.filter(users__user_id=update.message.chat.id)
    for checklist in checklists:
        reply_kb.append([telegram.KeyboardButton(str(checklist))])
        current_kb.update({str(checklist): 'checklist_menu'})
    reply_markup = telegram.ReplyKeyboardMarkup(reply_kb, resize_keyboard=True)
    message = context.bot.send_message(update.message.chat.id, 'your checklists:',
                                       reply_markup=reply_markup)

    context.user_data[0]['current_menu'] = loc.get('button_checklists_menu')
    context.user_data[0]['current_kb'] = current_kb
    context.user_data[0]['last_msg_id'] = message.message_id


def checklist_menu(update, context):
    inline_kb = []
    current_kb = {loc.get('button_go_back'): 'main_menu'}
    tasks = Task.objects.filter(parent=context.user_data[0]['checklist']).all()
    for task in tasks:
        inline_kb.append([telegram.InlineKeyboardButton(str(task), callback_data=str(task))])
        current_kb.update({str(task): 'checklist_menu'})
    inline_kb.append([telegram.InlineKeyboardButton(loc.get('button_go_back'),
                                                    callback_data=loc.get('button_go_back'))])
    reply_markup = telegram.InlineKeyboardMarkup(inline_kb)
    try:
        message = context.bot.send_message(update.message.chat.id, 'tasks in checklist:',
                                           reply_markup=reply_markup)
    except AttributeError:
        message = context.bot.send_message(update.callback_query.message.chat.id, 'tasks in checklist:',
                                           reply_markup=reply_markup)

    context.user_data[0]['current_menu'] = loc.get('menu_checklist')
    context.user_data[0]['current_kb'] = current_kb
    context.user_data[0]['last_msg_id'] = message.message_id
