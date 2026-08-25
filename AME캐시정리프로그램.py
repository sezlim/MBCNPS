import os
import sys
import time
import configparser
import tkinter as tk
from tkinter import filedialog
from pathlib import Path

# 현재 실행 파일의 경로와 이름 확인 (자기 자신과 ini 파일 삭제 방지)
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
    exe_name = os.path.basename(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))
    exe_name = os.path.basename(__file__)

CONFIG_FILE = os.path.join(application_path, 'config.ini')


def create_config(target_path):
    """사용자가 지정한 경로로 INI 파일 생성"""
    config = configparser.ConfigParser()
    config['SETTINGS'] = {
        'TargetFolder': target_path,
        'DaysToKeep': '5'
    }
    with open(CONFIG_FILE, 'w', encoding='utf-8') as configfile:
        config.write(configfile)


def get_path_from_gui():
    """초기 경로 설정을 위한 커스텀 창 띄우기"""
    root = tk.Tk()
    root.title("AME 캐시 자동 정리 설정")

    # 창 크기 및 화면 중앙 배치
    window_width = 450
    window_height = 180
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    center_x = int(screen_width / 2 - window_width / 2)
    center_y = int(screen_height / 2 - window_height / 2)
    root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
    root.attributes('-topmost', True)

    selected_path = ""

    def on_set_path():
        nonlocal selected_path
        path = filedialog.askdirectory(parent=root, title="AME 캐시 경로 지정")
        if path:
            selected_path = path
            root.destroy()

    def on_close():
        root.destroy()
        sys.exit()

    root.protocol("WM_DELETE_WINDOW", on_close)

    msg = ("AME 캐시 폴더를 주기마다 삭제하는 프로그램 입니다.\n"
           "ame 캐시 경로가 잡혀있지 않습니다.\n\n"
           "프로그램을 사용하려면 경로를 잡아주고\n"
           "사용하지 않으려면 닫기를 눌러주세요.")

    lbl = tk.Label(root, text=msg, justify="center", font=("맑은 고딕", 10), pady=15)
    lbl.pack(expand=True)

    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=10)

    btn_set = tk.Button(btn_frame, text="경로 설정", command=on_set_path, width=12, bg="#0078D7", fg="white",
                        font=("맑은 고딕", 9, "bold"))
    btn_set.pack(side="left", padx=10)

    btn_close = tk.Button(btn_frame, text="닫기", command=on_close, width=12, font=("맑은 고딕", 9))
    btn_close.pack(side="right", padx=10)

    root.mainloop()
    return selected_path


def show_splash(target_path):
    """5초 동안 표시되는 실행 안내 팝업"""
    root = tk.Tk()
    root.title("캐시 자동 정리")

    window_width = 450
    window_height = 150
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    center_x = int(screen_width / 2 - window_width / 2)
    center_y = int(screen_height / 2 - window_height / 2)
    root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
    root.attributes('-topmost', True)

    msg = (f"Adobe cache 폴더경로는 : {target_path} 입니다.\n\n"
           f"이 폴더를 보고 5일 이상된 파일들을 삭제하여 용량을 확보합니다\n"
           f"자동으로 돌아갑니다")

    lbl = tk.Label(root, text=msg, justify="center", font=("맑은 고딕", 10), pady=30)
    lbl.pack(expand=True)

    root.after(5000, root.destroy)
    root.mainloop()


def run_cleanup(target_folder, days_to_keep):
    """실제 파일 삭제 로직"""
    target_dir = Path(target_folder)
    if not target_dir.exists():
        return

    current_time = time.time()
    age_limit = days_to_keep * 86400  # 1일 = 86400초

    # rglob('*')로 하위 폴더의 모든 항목 순회
    for file_path in target_dir.rglob('*'):
        # is_file()로 폴더는 제외하고 파일만 대상으로 지정
        if file_path.is_file():
            filename = file_path.name

            # ini 파일과 exe 프로그램 자체는 삭제에서 제외
            if filename.lower() == 'config.ini' or filename == exe_name:
                continue

            try:
                file_mtime = file_path.stat().st_mtime
                if (current_time - file_mtime) > age_limit:
                    file_path.unlink()  # 폴더는 건드리지 않고 파일만 삭제
            except Exception:
                pass


if __name__ == "__main__":
    if not os.path.exists(CONFIG_FILE):
        folder_path = get_path_from_gui()

        if folder_path:
            create_config(folder_path)
        else:
            sys.exit()

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding='utf-8')

    try:
        target_path = config.get('SETTINGS', 'TargetFolder')
        days = config.getint('SETTINGS', 'DaysToKeep', fallback=5)
    except Exception:
        sys.exit()

    show_splash(target_path)

    while True:
        run_cleanup(target_path, days)
        time.sleep(86400)  # 24시간 대기
