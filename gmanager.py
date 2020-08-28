# Библиотека для загрузки пути а также комманды терминала
import os
import subprocess
from os import listdir


gjf_file = r'*./gjf'
gausman_path = '/home/docent/gausman'
os.chdir(gausman_path)


files = [f for f in listdir(gausman_path) if os.path.splitext(f)[1] == '.gjf']
print(files)
for f in files:
    print("Обрабатывается файл: " + f)
    ret_code = subprocess.call(["g16", f])
    if ret_code == 0:
        subprocess.call(["7z", "a", os.path.splitext(f)[0], os.path.splitext(f)[0] + ".log"])
        f_zip = os.path.splitext(f)[0] + ".7z"
        subprocess.call(["rclone", "copy", "".join([gausman_path, '/', f_zip]), "remote:Gbot/log/"])
        os.remove(f)

    else:
        subprocess.call(["7z", "a", os.path.splitext(f)[0], os.path.splitext(f)[0] + ".log"])
        f_zip = os.path.splitext(f)[0] + ".7z"
        subprocess.call(["rclone", "copy", "".join([gausman_path, '/', f_zip]), "remote:Gbot/error/"])
        os.remove(f)
exit()
