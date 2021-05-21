import logging
from collections import defaultdict
from pprint import pprint
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


def __create_kb(kb_list, is_inline=False):
    if is_inline:
        keyboard_list = []
        for kb_row in kb_list:
            row = []
            for button in kb_row:
                try:
                    row.append(telegram.InlineKeyboardButton(loc.get(button),
                                                             callback_data=loc.get(button)))
                except AttributeError:
                    row.append(telegram.InlineKeyboardButton(button,
                                                             callback_data=button))
            keyboard_list.append(row)
    else:
        keyboard_list = []
        for kb_row in kb_list:
            row = []
            for button in kb_row:
                try:
                    row.append(telegram.KeyboardButton(loc.get(button)))
                except AttributeError:
                    row.append(telegram.KeyboardButton(button))
            keyboard_list.append(row)
    return keyboard_list


def __def_user_data(context,
                    kb_list=None,
                    current_menu=None,
                    last_msg_id=None,
                    task=None,
                    checklist=None):

    if kb_list is None:
        current_kb = {loc.get('menu_some'): 'menu_some',
                      loc.get('menu_checklists'): 'menu_checklists'}
    else:
        if isinstance(kb_list, str):
            kb_list = [[kb_list]]
        current_kb = {}
        for row in kb_list:
            for button in row:
                try:
                    current_kb.update({loc.get(button): button})
                except AttributeError:
                    if button != loc.get('menu_main'):
                        current_kb.update({str(button): 'menu_checklist'})
                    else:
                        current_kb.update({str(button): 'menu_main'})
    if current_menu is None:
        current_menu = loc.get('menu_main')
    context.user_data[0] = {'current_menu': current_menu,
                            'current_kb': current_kb,
                            'last_msg_id': last_msg_id,
                            'task': task,
                            'checklist': checklist}
    pprint(context.user_data)


def receiver(update, context):
    if update.callback_query is not None:
        update.callback_query.answer()
        print(update.callback_query)
        if update.callback_query.data in context.user_data[0]['current_kb']:
            pressed = update.callback_query.data
        else:
            pressed = loc.get('menu_main')
        pprint(pressed)
    else:
        if update.message.text in context.user_data[0]['current_kb']:
            pressed = update.message.text
        else:
            return
    next_menu = context.user_data[0]['current_kb'].get(pressed)
    possibles = globals().copy()
    possibles.update(locals())
    method = possibles.get(next_menu)
    checklist = None
    if not method:
        try:
            checklist = Checklist.objects.filter(shortname=pressed).first()
        except Exception as e:
            pprint(f'{e}')
        # raise NotImplementedError("Method %s not implemented" % next_menu)
    last_msg_id = context.user_data[0]['last_msg_id']
    if last_msg_id is not None:
        try:
            context.bot.delete_message(update.message.chat.id, context.user_data[0]['last_msg_id'])
            last_msg_id = None
        except AttributeError as e:
            try:
                context.bot.delete_message(update.callback_query.message.chat.id, context.user_data[0]['last_msg_id'])
                last_msg_id = None
            except Exception as e:
                print(f'{e}')

    current_menu = context.user_data[0]['current_menu']
    task = context.user_data[0]['task']

    __def_user_data(context,
                    current_menu,
                    last_msg_id,
                    task,
                    checklist)
    method(update, context)


def menu_main(update, context):
    kb_list = [['menu_some'],
               ['menu_checklists']]
    __def_user_data(context,
                    kb_list,
                    loc.get('menu_main'))
    buttons = __create_kb(kb_list)
    reply_markup = telegram.ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    user = User.get_user(update, context)
    if update.message is not None:
        chat_id = update.message.chat.id
    else:
        chat_id = update.callback_query.message.chat.id
    message = context.bot.send_message(chat_id, loc.get('conv_opened_menu_main',
                                                                       first_name=user.first_name),
                                       reply_markup=reply_markup)
    __def_user_data(context,
                    kb_list,
                    loc.get('menu_main'),
                    message.message_id)


def menu_some(update, context):
    kb_list = [['menu_main'], ]
    __def_user_data(context,
                    kb_list,
                    loc.get('menu_some'))
    buttons = __create_kb([['menu_main']])
    reply_markup = telegram.ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    message = context.bot.send_message(update.message.chat.id, loc.get('conv_opened_menu_some'),
                                       reply_markup=reply_markup)
    context.user_data[0]['last_msg_id'] = message.message_id


def menu_checklists(update, context):
    kb_list = [['menu_main'], ]
    checklists = Checklist.objects.filter(users__user_id=update.message.chat.id)
    for checklist in checklists:
        kb_list.append([str(checklist)])
    buttons = __create_kb(kb_list)
    reply_markup = telegram.ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    message = context.bot.send_message(update.message.chat.id, 'your checklists:',
                                       reply_markup=reply_markup)
    __def_user_data(context,
                    kb_list,
                    loc.get('menu_checklists'),
                    message.message_id)


def menu_checklist(update, context):
    kb_list = []
    tasks = Task.objects.filter(parent=context.user_data[0]['checklist']).all()
    for task in tasks:
        kb_list.append([str(task), ])
    kb_list.append([loc.get('menu_main')])
    inline_kb = __create_kb(kb_list, is_inline=True)
    reply_markup = telegram.InlineKeyboardMarkup(inline_kb, row_width=1)
    try:
        message = context.bot.send_message(update.message.chat.id, 'tasks in checklist:',
                                           reply_markup=reply_markup)
    except AttributeError:
        message = context.bot.send_message(update.callback_query.message.chat.id, 'tasks in checklist:',
                                           reply_markup=reply_markup)

    __def_user_data(context, kb_list, loc.get('menu_checklist'),
                    message.message_id, checklist=context.user_data[0]['checklist'])
