import logging
from collections import defaultdict
from pprint import pprint
from typing import Dict

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
    if checklist is None:
        try:
            if context.user_data[0]['checklist']:
                checklist = context.user_data[0]['checklist']
        except KeyError:
            pprint(f'{KeyError}')
    if task is None:
        try:
            if context.user_data[0]['task']:
                task = context.user_data[0]['task']
        except KeyError:
            pprint(f'{KeyError}')
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
                    if button == loc.get('menu_main'):
                        current_kb.update({str(button): 'menu_main'})
                    if button == loc.get('button_back'):
                        if task is not None:
                            current_kb.update({button: 'menu_task'})
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
                    elif button in [loc.get('task_complete'), loc.get('task_comment'), loc.get('task_cancel')]:
                        current_kb.update({button: button})
    if current_menu is None:
        current_menu = loc.get('menu_main')
    context.user_data[0] = {'current_menu': current_menu,
                            'current_kb': current_kb,
                            'last_msg_id': last_msg_id,
                            'task': task,
                            'checklist': checklist}
    pprint(context.user_data)


def __callback_receiver(update, context):
    update.callback_query.answer()
    if update.callback_query.data in context.user_data[0]['current_kb']:
        pressed = update.callback_query.data
        next_menu = context.user_data[0]['current_kb'].get(pressed)
        possibles = globals().copy()
        possibles.update(locals())
        method = possibles.get(next_menu)
        checklist = None
        task = context.user_data[0]['task']
        if not method:
            # raise NotImplementedError("Method %s not implemented" % next_menu)
            if task is not None:
                if pressed == loc.get('task_complete'):
                    task.status = 'completed'
                    task.save()
                    method = menu_task
                if pressed == loc.get('task_cancel'):
                    task.status = 'cancelled'
                    task.save()
                    method = menu_task
                if pressed == loc.get('task_comment'):
                    method = menu_task_comment
        try:
            if context.user_data[0]['checklist']:
                try:
                    task = Task.objects.get(shortname=pressed[2:])
                except Exception as e:
                    pprint(f'{e}')
        except Exception as e:
            pprint(f'{e}')
        if task is not None and pressed == loc.get('task_complete'):
            task.status = 'completed'
            task.save()
        # task is not None and pressed == loc.get('task_comment'):
        # TODO: Сдедать комментарии к задачам
        # task.save()
        elif task is not None and pressed == loc.get('task_cancel'):
            task.status = 'cancelled'
            task.save()
        last_msg_id = context.user_data[0]['last_msg_id']
        if last_msg_id is not None:
            try:
                context.bot.delete_message(update.message.chat.id, context.user_data[0]['last_msg_id'])
                last_msg_id = None
            except AttributeError as e:
                try:
                    context.bot.delete_message(update.callback_query.message.chat.id,
                                               context.user_data[0]['last_msg_id'])
                    last_msg_id = None
                except Exception as e:
                    print(f'{e}')
        current_menu = context.user_data[0]['current_menu']

        __def_user_data(update, context,
                        current_menu,
                        last_msg_id,
                        task=task,
                        checklist=checklist)
        method(update, context)
    else:
        pressed = loc.get('menu_main')


def __receiver(update, context):
    if update.message.text in context.user_data[0]['current_kb']:
        pressed = update.message.text
    else:
        pressed = loc.get('menu_main')
    next_menu = context.user_data[0]['current_kb'].get(pressed)
    possibles = globals().copy()
    possibles.update(locals())
    method = possibles.get(next_menu)
    checklist = None
    if not method:
        raise NotImplementedError("Method %s not implemented" % next_menu)
    try:
        checklist = Checklist.objects.get(shortname=pressed)
    except Exception as e:
        pprint(f'{e}')
    try:
        if context.user_data[0]['checklist']:
            try:
                task = Task.objects.get(shortname=pressed)
            except Exception as e:
                pprint(f'{e}')
    except Exception as e:
        pprint(f'{e}')
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

    __def_user_data(update, context,
                    current_menu,
                    last_msg_id,
                    task=task,
                    checklist=checklist)
    method(update, context)


def menu_main(update, context):
    kb_list = [['menu_some'],
               ['menu_checklists']]
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
                    loc.get('menu_main'),
                    message.message_id)


def menu_some(update, context):
    kb_list = [['menu_main'], ]
    __def_user_data(update, context,
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
    __def_user_data(update, context,
                    kb_list,
                    loc.get('menu_checklists'),
                    message.message_id)


def menu_checklist(update, context):
    kb_list = []
    tasks = Task.objects.filter(parent=context.user_data[0]['checklist']).all()
    for task in tasks:
        kb_list.append([task.bstr()])
    kb_list.append([loc.get('menu_main')])
    inline_kb = __create_kb(kb_list, is_inline=True)
    reply_markup = telegram.InlineKeyboardMarkup(inline_kb, row_width=3)
    try:
        message = context.bot.send_message(update.message.chat.id, 'tasks in checklist:',
                                           reply_markup=reply_markup)
    except AttributeError:
        message = context.bot.send_message(update.callback_query.message.chat.id, 'tasks in checklist:',
                                           reply_markup=reply_markup)

    __def_user_data(update, context, kb_list, loc.get('menu_checklist'),
                    message.message_id, checklist=context.user_data[0]['checklist'])


def menu_task(update, context):
    kb_list = [
        [loc.get('task_complete'), loc.get('task_comment'), loc.get('task_cancel')],
        [loc.get('menu_main')]
    ]
    inline_kb = __create_kb(kb_list, is_inline=True)
    reply_markup = telegram.InlineKeyboardMarkup(inline_kb, row_width=3)
    task = context.user_data[0]['task']
    text = loc.get('task_page', shortname=task.shortname,
                   description=task.description,
                   comment=task.comment,
                   deadline=task.deadline,
                   priority=task.priority,
                   status=task.status)
    try:
        message = context.bot.send_message(update.callback_query.message.chat.id, text,
                                           reply_markup=reply_markup,
                                           parse_mode=ParseMode.HTML)
    except AttributeError:
        message = context.bot.send_message(update.message.chat.id, text,
                                           reply_markup=reply_markup,
                                           parse_mode=ParseMode.HTML)
    __def_user_data(update, context, kb_list, loc.get('menu_task'),
                    message.message_id,
                    checklist=context.user_data[0]['checklist'])


def menu_task_comment(update, context):
    kb_list = [[loc.get('button_back')]]
    inline_kb = __create_kb(kb_list, is_inline=True)
    reply_markup = telegram.InlineKeyboardMarkup(inline_kb, row_width=3)
    text = loc.get('conv_write_new_comment', comment=context.user_data[0]['task'].comment)
    message = context.bot.send_message(update.callback_query.message.chat.id, text,
                                       reply_markup=reply_markup,
                                       parse_mode=ParseMode.HTML)
    __def_user_data(update, context, kb_list, loc.get('menu_task_comment'),
                    message.message_id, checklist=context.user_data[0]['checklist'])
