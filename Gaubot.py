from telegram.ext import Updater
import logging
from telegram.ext import CommandHandler
from functools import wraps
from telegram.ext.dispatcher import run_async
from telegram.ext import MessageHandler, Filters
import os
import psutil
import pathlib
import subprocess
from os import listdir
from os.path import isfile, join, basename
import filecmp
from pathlib import Path
from subprocess import call
pid_gaus = "0"
LIST_OF_ADMINS = [469473176]
gausman_path = '/home/docent/gausman'
TOKEN = 'Your Token'
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher
updater.start_polling()


# Security
def restricted(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in LIST_OF_ADMINS:
            print("Unauthorized access denied for {}.".format(user_id))
            return
        return func(update, context, *args, **kwargs)
    return wrapped


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)


# Запуск бота
@restricted
def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Список команд /help")


start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)


@restricted
def help(update, context):
    help_page = '/work <Имя файла> без расширения - поставить в очередь задачу; /init - запустить кластер расчётов; ' \
                '/stop - остановить кластер; /remove <Имя файла> без расширения - удалить файл из очереди; /list - ' \
                'вывести список файлов в очереди; /queue - вывести список файлов на сервере'
    context.bot.send_message(chat_id=update.effective_chat.id, text=help_page)


help_handler = CommandHandler('help', help)
dispatcher.add_handler(help_handler)


@restricted
def work(update, context):
    filename = str(update.message.text).split(' ')[1]
    if filename == 'all':
        subprocess.call(["rclone", "copy", "remote:Gbot/input/", gausman_path])
        file_list = os.listdir(gausman_path)
        context.bot.send_message(chat_id=update.effective_chat.id, text=str(['обрабатываются файлы', file_list]))
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text=str(['обрабатываются файлы', filename]))
        subprocess.call(["rclone", "copy", "".join(["remote:Gbot/input/", filename, ".gjf"]), gausman_path])


work_handler = CommandHandler('work', work)
dispatcher.add_handler(work_handler)


@restricted
@run_async
def initiate(update, context):
    global pid_gaus
    pid_gaus = subprocess.Popen(["/usr/bin/python3.8", "gmanager.py"]).pid
    context.bot.send_message(chat_id=update.effective_chat.id, text='Запущены расчёты. PID = {}'.format(pid_gaus))


initiate_handler = CommandHandler('init', initiate)
dispatcher.add_handler(initiate_handler)


@restricted
def stop_work(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text='Прерывание работы '
                                                                    'кластера, PID={}'.format(pid_gaus))
    process = psutil.Process(pid_gaus)
    for proc in process.children(recursive=True):
        proc.kill()
    process.kill()


stop_work_handler = CommandHandler('stop', stop_work)
dispatcher.add_handler(stop_work_handler)


@restricted
def list_work(update, context):
    file_list = os.listdir(gausman_path)
    context.bot.send_message(chat_id=update.effective_chat.id, text=file_list)


list_work_handler = CommandHandler('list', list_work)
dispatcher.add_handler(list_work_handler)

@restricted
def queue_work(update, context):

    queue = str(subprocess.check_output(["rclone", "ls", "remote:Gbot/input"]))

    context.bot.send_message(chat_id=update.effective_chat.id, text=queue)


queue_work_handler = CommandHandler('queue', queue_work)
dispatcher.add_handler(queue_work_handler)


@restricted
def remove_work(update, context):
    filename = str(update.message.text).split(' ')[1]
    subprocess.call(["rm", "".join([filename, ".gjf"])])
    context.bot.send_message(chat_id=update.effective_chat.id, text=['Удалена задача', filename])


remove_work_handler = CommandHandler('remove', remove_work)
dispatcher.add_handler(remove_work_handler)
