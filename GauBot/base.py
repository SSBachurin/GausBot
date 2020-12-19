
import logging
import traceback
from functools import wraps
import subprocess
from abc import ABC

from telegram.ext import CommandHandler, Filters
from telegram import Update, MessageEntity

from GauBot.drive import GauDrive

logger = logging.getLogger('GauBotBase')

class Wrapper(ABC):
    _handlers = {}

    @classmethod
    def command(cls, **kwargs):
        if not 'name' in kwargs or not 'help' in kwargs:
            raise Exception("Name and Help are required")
        def wrapper(f):
            cls._handlers[kwargs['name']] = {'handler': f, 'help': kwargs['help']}
            @wraps(f)
            def wrapped(self, *f_args, **f_kwargs):
                f(self, *f_args, **f_kwargs)
            return wrapped
        return wrapper
    
    @classmethod
    def access(cls, name):
        def wrapper(f):
            @wraps(f)
            def wrapped(self, update, *f_args, **f_kwargs):
                if not (name == "everyone" or self._check_access(name, update)):
                    return
                f(self, update, *f_args, **f_kwargs)
            return wrapped
        return wrapper

class GauBotBase(CommandHandler):
    def __init__(self, path, **kwargs):
        self.wd = path
        self.users_groups = kwargs.get("users", {})
        self.pass_update_queue = False
        self.pass_job_queue = False
        self.pass_user_data = False
        self.pass_chat_data = False
        self.filters = Filters.update.messages
        self._stop_flag = False
        self._work_started = False
        self._current_process = None
        self._drive = GauDrive()

    def _check_access(self, group_name, update):
        user_id = update.effective_user.id
        if user_id not in self.users_groups[group_name]:
            raise Exception("Unauthorized access denied for {}.".format(update.effective_user.name))
            return False
        return True

    def check_update(self, update):
        if isinstance(update, Update) and update.effective_message:
            message = update.effective_message

            if (message.entities and message.entities[0].type == MessageEntity.BOT_COMMAND
                    and message.entities[0].offset == 0):
                command = message.text[1:message.entities[0].length]
                args = message.text.split()[1:]
                command = command.split('@')
                command.append(message.bot.username)

                if not (command[0].lower() in Wrapper._handlers
                        and command[1].lower() == message.bot.username.lower()):
                        return None

                filter_result = self.filters(update)
                if filter_result:
                    return args, filter_result, command[0]
                else:
                    return False
            else:
                filter_result = self.filters(update)
                if filter_result:
                    return [], filter_result, "help_help"

    def handle_update(self, update, dispatcher, check_result, context=None):
        args, filter_result, command = check_result
        callback = Wrapper._handlers[command]['handler']
        if context:
            self.collect_additional_context(context, update, dispatcher, (args, filter_result))
            try:
                return callback(self, update, context)
            except Exception as e:
                context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error: {str(e)}")
                logging.error(e)
                traceback.print_exc()
        else:
            optional_args = self.collect_optional_args(dispatcher, update, (args, filter_result))
            return callback(self, dispatcher.bot, update, **optional_args)


    def _run(self, cmd):
        if self._stop_flag:
            self._stop_flag = False
            raise Exception("Fuck it!")
        _current_process = subprocess.Popen(cmd, cwd=self.wd)
        _current_process.wait()
        return _current_process.returncode