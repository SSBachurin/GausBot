
import logging
import traceback
from functools import wraps
import os
import pathlib
import subprocess
from os import listdir
from os.path import isfile, join, basename, splitext
import filecmp
from glob import glob
from pathlib import Path
from subprocess import call
import pickle
from multiprocessing.pool import ThreadPool
from abc import ABC
import gzip
import shutil

from telegram.ext import CommandHandler, Filters
from telegram import Update, MessageEntity
from telegram.ext.dispatcher import run_async

logger = logging.getLogger('GauBot')

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

class GauBot(CommandHandler, ABC):
    def __init__(self, path, **kwargs):
        self.wd = path
        self.users_groups = kwargs.get("users", {})
        self.pass_update_queue = False
        self.pass_job_queue = False
        self.pass_user_data = False
        self.pass_chat_data = False
        self._stop_flag = False
        self._work_started = False
        self._current_process = None
        self.filters = Filters.update.messages

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

    def _compress(self, _in, _out):
        with open(_in, 'rb') as f_in:
            with gzip.open(_out, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
    
    @Wrapper.command(name="help", help="get help")
    @Wrapper.access("everyone")
    def help(self, update, context):
        help_page = []
        for cmd, cfg in Wrapper._handlers.items():
            help_page.append(f"/{cmd} - {cfg['help']}")
        context.bot.send_message(chat_id=update.effective_chat.id, text="; ".join(help_page))
    
    @Wrapper.command(name="help_help", help="help for help:-D")
    @Wrapper.access("everyone")
    def help_help(self, update, context):
        context.bot.send_message(chat_id=update.effective_chat.id, text="Список команд /help")

    @Wrapper.command(name="work", help="поставить в очередь задачу (arg: <Имя файла> без расширения)")
    @Wrapper.access("admins")
    def work(self, update, context):
        filename = str(update.message.text).split(' ')[1]
        if filename == 'all':
            subprocess.call(["rclone", "copy", "remote:Gbot/input/", self.wd])
            file_list = os.listdir(self.wd)
            context.bot.send_message(chat_id=update.effective_chat.id, text=str(['обрабатываются файлы', file_list]))
        else:
            context.bot.send_message(chat_id=update.effective_chat.id, text=str(['обрабатываются файлы', filename]))
            subprocess.call(["rclone", "copy", "".join(["remote:Gbot/input/", filename, ".gjf"]), self.wd])
    
    @Wrapper.command(name="stop", help="остановить кластер")
    @Wrapper.access("admins")
    def stop_work(self, update, context):
        context.bot.send_message(chat_id=update.effective_chat.id, text='Прерывание работы кластера')
        self._stop_flag = True
        if self._current_process:
            self._current_process.terminate()

    @Wrapper.command(name="list", help="вывести список файлов в очереди")
    @Wrapper.access("admins")
    def list_work(self, update, context):
        file_list = os.listdir(self.wd)
        context.bot.send_message(chat_id=update.effective_chat.id, text=file_list)

    @Wrapper.command(name="queue", help="вывести список файлов на сервере")
    @Wrapper.access("admins")
    def queue_work(self, update, context):
        queue = str(subprocess.check_output(["rclone", "ls", "remote:Gbot/input"]))
        context.bot.send_message(chat_id=update.effective_chat.id, text=queue)

    @Wrapper.command(name="remove", help="удалить файл из очереди (arg: <Имя файла> без расширения)")
    @Wrapper.access("admins")
    def remove_work(self, update, context):
        filename = str(update.message.text).split(' ')[1]
        subprocess.call(["rm", "".join([filename, ".gjf"])])
        context.bot.send_message(chat_id=update.effective_chat.id, text=['Удалена задача', filename])

    @Wrapper.command(name="init", help="запустить кластер расчётов")
    @Wrapper.access("admins")
    @run_async
    def initiate(self, update, context):
        if self._work_started:
            raise Exception("I'm already doin' calc")
        self._stop_flag = False
        self._work_started = True
        added = []
        for f in glob(f"{self.wd}/*.gjf"):
            logging.info(f"File processing: {f}")
            context.bot.send_message(chat_id=update.effective_chat.id, text=f"File processing: {f}")
            try:
                ret_code = _run(["g16", f])
            except:
                logging.warning("Someone has killed us O_o")
                break
            if ret_code == 0:
                try:
                    f_zip = splitext(f)[0] + ".gz"
                    _compress(join(self.wd, splitext(f)[0] + ".log"))
                    _run(["rclone", "copy", join(self.wd, f_zip), "remote:Gbot/log/"]) # gapi
                except:
                    logging.warning("Someone has killed us O_o")
                    break
                os.remove(f)
                context.bot.send_message(chat_id=update.effective_chat.id, text=f"File successefuly complited: {f}")
                continue
            try:
                f_zip = splitext(f)[0] + ".gz"
                _compress(join(self.wd, splitext(f)[0] + ".log"))
                _run(["rclone", "copy", join(self.wd, f_zip), "remote:Gbot/error/"]) # gapi
            except:
                logging.warning("Someone has killed us O_o")
                break
            os.remove(f)
            context.bot.send_message(chat_id=update.effective_chat.id, text=f"We're fucked up: {f}")
        self._work_started = False




