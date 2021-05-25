import logging
from collections import defaultdict
from pprint import pprint
from typing import Dict
from django.template.defaultfilters import date as _date
from datetime import datetime

import telegram
from telegram import ParseMode

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


def __def_user_data(update, context,
                    kb_list=None,
                    current_menu=None,
                    last_msg_id=None,
                    task=None,
                    checklist=None):

    if kb_list is None:
        current_kb = {loc.get('menu_checklists'): 'menu_checklists'}
    else:
        if isinstance(kb_list, str):
            kb_list = [[kb_list]]
        current_kb = {}
        for row in kb_list:
            for button in row:
                try:
                    current_kb.update({loc.get(button): button})
                except AttributeError:
                    log.info(f'{AttributeError}')
                    current_kb.update({button: button})
                    try:
                        user_id = update.message.chat.id
                    except AttributeError:
                        user_id = update.callback_query.message.chat.id
                    if button in [i.shortname for i in Checklist.objects \
                            .filter(users__user_id=user_id)]:
                        current_kb.update({str(button): 'menu_checklist'})
                    elif button[2:] in [i.shortname for i in Task.objects \
                            .filter(parent=context.user_data[0]['checklist'])]:
                        current_kb.update({str(button): 'menu_task'})

    if current_menu is None:
        current_menu = {loc.get('menu_main'): 'menu_main'}
    if last_msg_id is None:
        try:
            last_msg_id = context.user_data[0]['last_msg_id']
        except Exception as e:
            log.error(f'{e}')
    if task is None:
        try:
            task = context.user_data[0]['task']
        except Exception as e:
            log.error(f'{e}')
    if checklist is None:
        try:
            checklist = context.user_data[0]['checklist']
        except Exception as e:
            log.error(f'{e}')
    context.user_data[0] = {'current_menu': current_menu,
                            'current_kb': current_kb,
                            'last_msg_id': last_msg_id,
                            'checklist': checklist,
                            'task': task}


def __callback_receiver(update, context):
    try:
        pprint(context.user_data[0])
    except KeyError:
        context.user_data[0] = {
            'checklist': None,
            'current_kb': {'Чеклисты': 'menu_checklists'},
            'current_menu': {'Главное меню': 'menu_main'},
            'last_msg_id': None,
            'task': None
        }
    update.callback_query.answer()
    task = context.user_data[0]['task'] if context.user_data[0]['task'] is not None else None
    last_msg_id = context.user_data[0]['last_msg_id'] if context.user_data[0]['last_msg_id'] is not None else None
    checklist = context.user_data[0]['checklist'] if context.user_data[0]['checklist'] is not None else None
    pressed = update.callback_query.data
    current_menu = list(context.user_data[0]['current_menu'].values())[0]
    if current_menu == 'menu_checklist':
        if pressed == loc.get('button_back'):
            next_menu = 'menu_checklists'
            checklist = None
        else:
            task = Task.objects.filter(parent=context.user_data[0]['checklist']).get(shortname=pressed[2:])
            next_menu = 'menu_task'
    elif current_menu == 'menu_task':
        if pressed == loc.get('button_back'):
            next_menu = 'menu_checklist'
            task = None
        elif pressed == loc.get('task_complete'):
            next_menu = 'menu_task'
            if task.status != 'completed':
                task.status = 'completed'
            else:
                task.status = 'pending'
            task.save()
        elif pressed == loc.get('task_cancel'):
            next_menu = 'menu_task'
            if task.status != 'cancelled':
                task.status = 'cancelled'
            else:
                task.status = 'pending'
            task.save()
        elif pressed == loc.get('task_comment'):
            next_menu = 'menu_task_comment'

    if last_msg_id is not None:
        context.bot.delete_message(update.callback_query.message.chat.id, context.user_data[0]['last_msg_id'])
        last_msg_id = None
    __def_user_data(update, context,
                    current_menu=current_menu,
                    last_msg_id=last_msg_id,
                    task=task,
                    checklist=checklist)
    possibles = globals().copy()
    possibles.update(locals())
    try:
        method = possibles.get(next_menu)
    except UnboundLocalError:
        method = menu_main
    method(update, context)


def __receiver(update, context):
    try:
        pprint(context.user_data[0])
    except KeyError:
        context.user_data[0] = {
            'checklist': None,
            'current_kb': {'Чеклисты': 'menu_checklists'},
            'current_menu': {'Главное меню': 'menu_main'},
            'last_msg_id': None,
            'task': None
        }
    checklist = context.user_data[0]['checklist']
    current_menu = context.user_data[0]['current_menu']
    task = context.user_data[0]['task']
    last_msg_id = context.user_data[0]['last_msg_id']
    if last_msg_id is not None:
        try:
            context.bot.delete_message(update.message.chat.id, context.user_data[0]['last_msg_id'])
            last_msg_id = None
        except AttributeError:
            context.bot.delete_message(update.callback_query.message.chat.id, context.user_data[0]['last_msg_id'])
            last_msg_id = None
    if update.message.text in context.user_data[0]['current_kb']:
        pressed = update.message.text
        next_menu = context.user_data[0]['current_kb'].get(pressed)
    else:
        if list(current_menu.values())[0] == 'menu_task_comment' and task is not None:
            comment = update.message.text
            task.comment = comment
            task.save()
            next_menu = 'menu_task'
        else:
            next_menu = 'menu_main'
    possibles = globals().copy()
    possibles.update(locals())
    method = possibles.get(next_menu)

    __def_user_data(update, context,
                    current_menu=current_menu,
                    last_msg_id=last_msg_id,
                    task=task,
                    checklist=checklist)
    method(update, context)


def menu_main(update, context):
    kb_list = [['menu_checklists']]
    __def_user_data(update, context,
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
    __def_user_data(update, context,
                    kb_list,
                    {loc.get('menu_main'): 'menu_main'},
                    message.message_id)


def menu_checklists(update, context):
    if context.user_data[0]['checklist']:
        checklist = context.user_data[0]['checklist']
    else:
        checklist = None
    if context.user_data[0]['task']:
        task = context.user_data[0]['task']
    else:
        task = None
    kb_list = [['menu_main'], ]
    try:
        chat_id = update.message.chat.id
    except AttributeError:
        chat_id = update.callback_query.message.chat.id
    checklists = Checklist.objects.filter(users__user_id=chat_id)
    for checklist in checklists:
        kb_list.append([str(checklist)])
    buttons = __create_kb(kb_list)
    reply_markup = telegram.ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    text = loc.get('conv_opened_menu_checklists')
    message = context.bot.send_message(chat_id, text,
                                       reply_markup=reply_markup)
    current_menu = {loc.get('menu_checklists'): 'menu_checklists'}
    __def_user_data(update, context,
                    kb_list=kb_list,
                    current_menu=current_menu,
                    last_msg_id=message.message_id,
                    task=task,
                    checklist=checklist)


def menu_checklist(update, context):
    kb_list = []
    tasks = Task.objects.filter(parent=context.user_data[0]['checklist']).all()
    for task in tasks:
        kb_list.append([task.bstr()])
    kb_list.append([loc.get('button_back')])
    inline_kb = __create_kb(kb_list, is_inline=True)
    reply_markup = telegram.InlineKeyboardMarkup(inline_kb, row_width=3)
    text = loc.get('conv_opened_menu_checklist', shortname=context.user_data[0]['checklist'].shortname)
    try:
        message = context.bot.send_message(update.message.chat.id, text,
                                           reply_markup=reply_markup,
                                           parse_mode=ParseMode.HTML)
    except AttributeError:
        message = context.bot.send_message(update.callback_query.message.chat.id, text,
                                           reply_markup=reply_markup,
                                           parse_mode=ParseMode.HTML)
    current_menu = {loc.get('menu_checklist'): 'menu_checklist'}
    __def_user_data(update, context, kb_list,
                    current_menu=current_menu,
                    last_msg_id=message.message_id,
                    checklist=context.user_data[0]['checklist'])


def menu_task(update, context):
    kb_list = [
        [loc.get('task_complete'), loc.get('task_comment'), loc.get('task_cancel')],
        [loc.get('button_back')]
    ]
    inline_kb = __create_kb(kb_list, is_inline=True)
    reply_markup = telegram.InlineKeyboardMarkup(inline_kb, row_width=3)
    task = context.user_data[0]['task']
    # deadline = task.deadline.strftime('%H:%M %a %d.%m.%Y')
    deadline = _date(task.deadline, 'H:i D d.m.Y')
    if task.priority == 1:
        priority = loc.get('priority_one')
    elif task.priority == 2:
        priority = loc.get('priority_two')
    elif task.priority == 3:
        priority = loc.get('priority_three')
    if task.status == 'pending':
        status = loc.get('task_status_pending')
    elif task.status == 'completed':
        status = loc.get('task_status_completed')
    elif task.status == 'cancelled':
        status = loc.get('task_status_cancelled')
    else:
        status = task.status
    if task.description != '':
        task_page_description = loc.get('task_page_description',
                                        description=task.description)
    else:
        task_page_description = ''
    if task.comment != '':
        task_page_comment = loc.get('task_page_comment',
                                    comment=task.comment)
    else:
        task_page_comment = ''
    text = loc.get('task_page', shortname=task.shortname,
                   task_page_description=task_page_description,
                   task_page_comment=task_page_comment,
                   deadline=deadline,
                   priority=priority,
                   status=status)
    try:
        message = context.bot.send_message(update.callback_query.message.chat.id, text,
                                           reply_markup=reply_markup,
                                           parse_mode=ParseMode.HTML)
    except AttributeError:
        message = context.bot.send_message(update.message.chat.id, text,
                                           reply_markup=reply_markup,
                                           parse_mode=ParseMode.HTML)
    current_menu = {loc.get('menu_task'): 'menu_task'}
    __def_user_data(update, context,
                    kb_list=kb_list,
                    current_menu=current_menu,
                    last_msg_id=message.message_id,
                    checklist=context.user_data[0]['checklist'])


def menu_task_comment(update, context):
    kb_list = [[loc.get('button_back')]]
    inline_kb = __create_kb(kb_list, is_inline=True)
    reply_markup = telegram.InlineKeyboardMarkup(inline_kb, row_width=3)
    text = loc.get('conv_write_new_comment', comment=context.user_data[0]['task'].comment)
    message = context.bot.send_message(update.callback_query.message.chat.id, text,
                                       reply_markup=reply_markup,
                                       parse_mode=ParseMode.HTML)
    __def_user_data(update, context, kb_list,
                    current_menu={loc.get('menu_task_comment'): 'menu_task_comment'},
                    last_msg_id=message.message_id,
                    checklist=context.user_data[0]['checklist'])
