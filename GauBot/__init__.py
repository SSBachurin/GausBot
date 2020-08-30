
import logging
import os
import subprocess
from os.path import join, splitext
from glob import glob

from telegram.ext.dispatcher import run_async

from GauBot.base import GauBotBase, Wrapper

logger = logging.getLogger('GauBot')

class GauBot(GauBotBase):
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
                ret_code = self._run(["g16", f])
            except:
                logging.warning("Someone has killed us O_o")
                break
            if ret_code == 0:
                try:
                    f_zip = splitext(f)[0] + ".gz"
                    self._drive._compress(join(self.wd, splitext(f)[0] + ".log"))
                    self._run(["rclone", "copy", join(self.wd, f_zip), "remote:Gbot/log/"]) # gapi
                except:
                    logging.warning("Someone has killed us O_o")
                    break
                os.remove(f)
                context.bot.send_message(chat_id=update.effective_chat.id, text=f"File successefuly complited: {f}")
                continue
            try:
                f_zip = splitext(f)[0] + ".gz"
                self._drive._compress(join(self.wd, splitext(f)[0] + ".log"))
                self._run(["rclone", "copy", join(self.wd, f_zip), "remote:Gbot/error/"]) # gapi
            except:
                logging.warning("Someone has killed us O_o")
                break
            os.remove(f)
            context.bot.send_message(chat_id=update.effective_chat.id, text=f"We're fucked up: {f}")
        self._work_started = False
