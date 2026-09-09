import os
import shutil
import time
import fnmatch
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext


class MAMAutoCopierApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MAM 자동 파일 복사 스케줄러 (주말/야간 무인 운용)")
        self.root.geometry("860x900")
        self.root.resizable(True, True)

        self.is_running = False
        self.worker_thread = None
        self.stop_event = threading.Event()

        self._build_ui()

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use('clam')

        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ==========================================
        # 1. 경로 설정 그룹
        # ==========================================
        self.path_group = ttk.LabelFrame(main_frame, text=" 1. 경로 설정 ", padding="10")
        self.path_group.pack(fill=tk.X, pady=5)

        ttk.Label(self.path_group, text="소스 폴더:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.src_path_var = tk.StringVar()
        self.src_entry = ttk.Entry(self.path_group, textvariable=self.src_path_var, width=65)
        self.src_entry.grid(row=0, column=1, padx=5, pady=2)
        self.src_btn = ttk.Button(self.path_group, text="찾아보기", command=lambda: self._browse_folder(self.src_path_var))
        self.src_btn.grid(row=0, column=2, pady=2)

        ttk.Label(self.path_group, text="타겟 폴더:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.dst_path_var = tk.StringVar()
        self.dst_entry = ttk.Entry(self.path_group, textvariable=self.dst_path_var, width=65)
        self.dst_entry.grid(row=1, column=1, padx=5, pady=2)
        self.dst_btn = ttk.Button(self.path_group, text="찾아보기", command=lambda: self._browse_folder(self.dst_path_var))
        self.dst_btn.grid(row=1, column=2, pady=2)

        ttk.Label(self.path_group, text="로그파일 저장폴더:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.log_path_var = tk.StringVar(value=os.getcwd())
        self.log_entry = ttk.Entry(self.path_group, textvariable=self.log_path_var, width=65)
        self.log_entry.grid(row=2, column=1, padx=5, pady=2)
        self.log_btn = ttk.Button(self.path_group, text="폴더 선택", command=lambda: self._browse_folder(self.log_path_var))
        self.log_btn.grid(row=2, column=2, pady=2)

        # ==========================================
        # 2. 파일 필터링 설정 그룹 (대소문자 안내 반영)
        # ==========================================
        self.filter_group = ttk.LabelFrame(main_frame, text=" 2. 파일 필터링 설정 (※ 대문자와 소문자를 따로따로 2번 적어주셔야 합니다) ",
                                           padding="10")
        self.filter_group.pack(fill=tk.X, pady=5)

        frame_inc_ext = ttk.Frame(self.filter_group)
        frame_inc_ext.grid(row=0, column=0, padx=5, sticky=tk.N + tk.S + tk.E + tk.W)

        frame_exc_ext = ttk.Frame(self.filter_group)
        frame_exc_ext.grid(row=0, column=1, padx=5, sticky=tk.N + tk.S + tk.E + tk.W)

        frame_exc_kw = ttk.Frame(self.filter_group)
        frame_exc_kw.grid(row=0, column=2, padx=5, sticky=tk.N + tk.S + tk.E + tk.W)

        self.filter_group.columnconfigure(0, weight=1)
        self.filter_group.columnconfigure(1, weight=1)
        self.filter_group.columnconfigure(2, weight=1)

        # (1) 허용 확장자
        ttk.Label(frame_inc_ext, text="✅ 허용 확장자\n(비워두면 모든 파일 허용)").pack(anchor=tk.W)
        self.list_inc_ext, self.entry_inc_ext, self.add_btn_1, self.del_btn_1 = self._create_listbox_widget(
            frame_inc_ext, default_items=[".mxf", ".MXF", ".mov", ".MOV"]
        )

        # (2) 제외 확장자/패턴
        ttk.Label(frame_exc_ext, text="⛔ 제외 패턴\n(예: *.tmp, *.TMP)").pack(anchor=tk.W)
        self.list_exc_ext, self.entry_exc_ext, self.add_btn_2, self.del_btn_2 = self._create_listbox_widget(
            frame_exc_ext, default_items=["*.tmp", "*.TMP", "Thumbs.db"]
        )

        # (3) 제외 키워드
        ttk.Label(frame_exc_kw, text="⛔ 제외 파일명 키워드\n(예: draft)").pack(anchor=tk.W)
        self.list_exc_kw, self.entry_exc_kw, self.add_btn_3, self.del_btn_3 = self._create_listbox_widget(
            frame_exc_kw, default_items=["draft", "temp"]
        )

        # ==========================================
        # 3. 동작 규칙 그룹 (요청사항 반영)
        # ==========================================
        self.action_group = ttk.LabelFrame(main_frame, text=" 3. 복사 및 스케줄 옵션 ", padding="10")
        self.action_group.pack(fill=tk.X, pady=5)

        # [1줄] 하위폴더 탐색 여부 (y/n 형태로 직관적 명시)
        subfolder_frame = ttk.Frame(self.action_group)
        subfolder_frame.grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=5, pady=3)
        ttk.Label(subfolder_frame, text="하위폴더 탐색 여부 (y/n):").pack(side=tk.LEFT, padx=(0, 5))
        self.subfolder_choice_var = tk.StringVar(value="y")
        self.sub_y_rb = ttk.Radiobutton(subfolder_frame, text="y (포함)", variable=self.subfolder_choice_var, value="y")
        self.sub_y_rb.pack(side=tk.LEFT, padx=5)
        self.sub_n_rb = ttk.Radiobutton(subfolder_frame, text="n (미포함)", variable=self.subfolder_choice_var, value="n")
        self.sub_n_rb.pack(side=tk.LEFT, padx=5)

        # [2줄] 폴더구조 유지 방식
        structure_frame = ttk.Frame(self.action_group)
        structure_frame.grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=5, pady=3)
        ttk.Label(structure_frame, text="폴더 구조 처리:").pack(side=tk.LEFT, padx=(0, 15))
        self.structure_mode_var = tk.StringVar(value="preserve")
        self.struct_preserve_rb = ttk.Radiobutton(structure_frame, text="폴더구조를 유지하겠습니다.",
                                                  variable=self.structure_mode_var, value="preserve")
        self.struct_preserve_rb.pack(side=tk.LEFT, padx=5)
        self.struct_flat_rb = ttk.Radiobutton(structure_frame, text="타겟폴더에 구조 상관없이 파일을 모으겠습니다.",
                                              variable=self.structure_mode_var, value="flat")
        self.struct_flat_rb.pack(side=tk.LEFT, padx=5)

        # [3줄] 파일명 중복 처리 방식 선택 옵션 추가
        conflict_frame = ttk.Frame(self.action_group)
        conflict_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=3)
        ttk.Label(conflict_frame, text="중복 파일 처리:").pack(side=tk.LEFT, padx=(0, 15))
        self.conflict_mode_var = tk.StringVar(value="rename")
        self.conflict_rename_rb = ttk.Radiobutton(conflict_frame, text="파일명 뒤에 숫자(_1, _2...) 붙이기",
                                                  variable=self.conflict_mode_var, value="rename")
        self.conflict_rename_rb.pack(side=tk.LEFT, padx=5)
        self.conflict_overwrite_rb = ttk.Radiobutton(conflict_frame, text="덮어쓰기", variable=self.conflict_mode_var,
                                                     value="overwrite")
        self.conflict_overwrite_rb.pack(side=tk.LEFT, padx=5)

        # [4줄] 복사 완료 후 원본 삭제 옵션
        self.delete_after_copy_var = tk.BooleanVar(value=False)
        self.delete_chk = ttk.Checkbutton(self.action_group, text="복사 완료 후 원본 파일 삭제 (주의)",
                                          variable=self.delete_after_copy_var)
        self.delete_chk.grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=5, pady=3)

        # [5줄] 반복 주기 설정
        cycle_frame = ttk.Frame(self.action_group)
        cycle_frame.grid(row=4, column=0, columnspan=2, sticky=tk.W, padx=5, pady=3)
        ttk.Label(cycle_frame, text="반복 주기 (초):").pack(side=tk.LEFT)
        self.interval_var = tk.IntVar(value=60)
        self.interval_entry = ttk.Entry(cycle_frame, textvariable=self.interval_var, width=8)
        self.interval_entry.pack(side=tk.LEFT, padx=5)

        # ==========================================
        # 4. 제어 및 상태 모니터
        # ==========================================
        ctrl_frame = ttk.Frame(main_frame)
        ctrl_frame.pack(fill=tk.X, pady=10)

        self.start_btn = tk.Button(ctrl_frame, text="▶ 스케줄러 시작", bg="#2e7d32", fg="white", font=("맑은 고딕", 12, "bold"),
                                   height=2, command=self.start_scheduler)
        self.start_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        self.stop_btn = tk.Button(ctrl_frame, text="⏹ 정지", bg="#c62828", fg="white", font=("맑은 고딕", 12, "bold"),
                                  height=2, state=tk.DISABLED, command=self.stop_scheduler)
        self.stop_btn.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=5)

        log_group = ttk.LabelFrame(main_frame, text=" 실시간 실행 로그 ", padding="5")
        log_group.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_group, height=10, state='disabled', font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _create_listbox_widget(self, parent, default_items):
        input_frame = ttk.Frame(parent)
        input_frame.pack(fill=tk.X, pady=2)

        entry = ttk.Entry(input_frame)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))

        listbox = tk.Listbox(parent, height=5, selectmode=tk.SINGLE)

        def add_item(event=None):
            val = entry.get().strip()
            if val and val not in listbox.get(0, tk.END):
                listbox.insert(tk.END, val)
            entry.delete(0, tk.END)

        def remove_item():
            sel = listbox.curselection()
            if sel:
                listbox.delete(sel[0])

        entry.bind("<Return>", add_item)

        btn_add = ttk.Button(input_frame, text="추가", width=4, command=add_item)
        btn_add.pack(side=tk.LEFT)

        listbox.pack(fill=tk.BOTH, expand=True, pady=(2, 0))

        btn_del = ttk.Button(parent, text="선택 항목 삭제", command=remove_item)
        btn_del.pack(fill=tk.X, pady=(2, 0))

        for item in default_items:
            listbox.insert(tk.END, item)

        return listbox, entry, btn_add, btn_del

    def _browse_folder(self, var):
        path = filedialog.askdirectory()
        if path:
            var.set(path)

    def _set_inputs_state(self, state):
        """스케줄러 시작/정지에 따라 입력 필드 전체 활성/비활성화 제어"""
        st = tk.NORMAL if state else tk.DISABLED

        # 1. 경로 설정
        self.src_entry.config(state=st)
        self.src_btn.config(state=st)
        self.dst_entry.config(state=st)
        self.dst_btn.config(state=st)
        self.log_entry.config(state=st)
        self.log_btn.config(state=st)

        # 2. 필터 설정 (엔트리, 버튼, 리스트박스)
        for entry, b_add, b_del in [
            (self.entry_inc_ext, self.add_btn_1, self.del_btn_1),
            (self.entry_exc_ext, self.add_btn_2, self.del_btn_2),
            (self.entry_exc_kw, self.add_btn_3, self.del_btn_3)
        ]:
            entry.config(state=st)
            b_add.config(state=st)
            b_del.config(state=st)

        # 3. 옵션 라디오버튼 및 체크박스/엔트리
        for w in [
            self.sub_y_rb, self.sub_n_rb,
            self.struct_preserve_rb, self.struct_flat_rb,
            self.conflict_rename_rb, self.conflict_overwrite_rb,
            self.delete_chk, self.interval_entry
        ]:
            w.config(state=st)

    def log(self, message):
        now = datetime.now()
        timestamp = now.strftime("[%Y-%m-%d %H:%M:%S]")
        formatted_msg = f"{timestamp} {message}\n"

        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, formatted_msg)
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

        log_dir = self.log_path_var.get().strip()
        if log_dir and os.path.isdir(log_dir):
            date_str = now.strftime("%Y-%m-%d")
            file_name = f"copy_history_{date_str}.log"
            full_path = os.path.join(log_dir, file_name)
            try:
                with open(full_path, "a", encoding="utf-8") as f:
                    f.write(formatted_msg)
            except Exception:
                pass

    def start_scheduler(self):
        src = self.src_path_var.get().strip()
        dst = self.dst_path_var.get().strip()
        log_dir = self.log_path_var.get().strip()

        if not src or not os.path.exists(src):
            messagebox.showerror("오류", "올바른 소스 폴더 경로를 입력하세요.")
            return
        if not dst:
            messagebox.showerror("오류", "올바른 타겟 폴더 경로를 지정하세요.")
            return
        if not os.path.isdir(log_dir):
            messagebox.showerror("오류", "올바른 로그파일 저장폴더를 지정하세요.")
            return

        if self.delete_after_copy_var.get():
            if not messagebox.askyesno("경고", "복사 후 원본 파일 '삭제' 옵션이 켜져 있습니다.\n정말 진행하시겠습니까?"):
                return

        self.is_running = True
        self.stop_event.clear()

        # 버튼 상태 변경 및 입력창 잠금
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self._set_inputs_state(False)

        self.current_inc_exts = list(self.list_inc_ext.get(0, tk.END))
        self.current_exc_exts = list(self.list_exc_ext.get(0, tk.END))
        self.current_exc_kws = list(self.list_exc_kw.get(0, tk.END))

        self.log(f"=== 파일 자동 복사 시작 (주기: {self.interval_var.get()}초) ===")
        if not self.current_inc_exts:
            self.log("[INFO] 허용 확장자가 비어있어 '모든 파일'을 대상으로 탐색합니다.")

        self.worker_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.worker_thread.start()

    def stop_scheduler(self):
        self.stop_event.set()
        self.is_running = False
        self.log("=== 정지 요청 전송됨. 현재 대기 및 작업 완료 후 중지됩니다... ===")

        # 버튼 상태 원복 및 입력창 잠금 해제
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self._set_inputs_state(True)

    def _scheduler_loop(self):
        while not self.stop_event.is_set():
            try:
                self._run_copy_job()
            except Exception as e:
                self.log(f"[ERROR] 루프 실행 중 예외 발생: {str(e)}")

            interval = max(5, self.interval_var.get())
            for _ in range(interval):
                if self.stop_event.is_set():
                    break
                time.sleep(1)

        self.log("=== 스케줄러 정지 완료 ===")

    def _wait_interval(self, seconds):
        for _ in range(seconds):
            if self.stop_event.is_set():
                return False
            time.sleep(1)
        return True

    def _is_file_ready(self, filepath, filename):
        try:
            s1 = os.path.getsize(filepath)
            if not self._wait_interval(21):
                return False
            s2 = os.path.getsize(filepath)
            if s1 != s2:
                self.log(f"[WAIT] {filename} 크기 변경 됨 ({s1} -> {s2})")
                return False

            if not self._wait_interval(21):
                return False
            s3 = os.path.getsize(filepath)
            if s2 != s3:
                self.log(f"[WAIT] {filename} 크기 변경 됨 ({s2} -> {s3})")
                return False

            return True
        except (IOError, OSError):
            return False

    def _run_copy_job(self):
        src_root = self.src_path_var.get().strip()
        dst_root = self.dst_path_var.get().strip()
        include_sub = (self.subfolder_choice_var.get() == "y")
        keep_struct = (self.structure_mode_var.get() == "preserve")
        conflict_mode = self.conflict_mode_var.get()

        for root_dir, dirs, files in os.walk(src_root):
            if not include_sub and root_dir != src_root:
                continue

            for file in files:
                if self.stop_event.is_set():
                    return

                src_filepath = os.path.join(root_dir, file)
                _, ext = os.path.splitext(file)

                # 1. 허용 확장자 검사 (대소문자 엄격 구분 적용)
                if self.current_inc_exts and ext not in self.current_inc_exts:
                    continue

                # 2. 제외 패턴 검사 (대소문자 엄격 구분)
                if any(fnmatch.fnmatchcase(file, pat) for pat in self.current_exc_exts):
                    continue

                # 3. 제외 키워드 검사 (대소문자 엄격 구분)
                if any(ex_name in file for ex_name in self.current_exc_kws if ex_name):
                    continue

                # 목적지 경로 계산
                if keep_struct:
                    rel_path = os.path.relpath(root_dir, src_root)
                    target_dir = os.path.join(dst_root, rel_path) if rel_path != "." else dst_root
                else:
                    target_dir = dst_root

                os.makedirs(target_dir, exist_ok=True)
                dst_filepath = os.path.join(target_dir, file)

                # 파일 중복 처리 로직
                if os.path.exists(dst_filepath):
                    try:
                        if os.path.getsize(src_filepath) == os.path.getsize(dst_filepath):
                            continue
                    except:
                        pass

                    if conflict_mode == "rename":
                        name, file_ext = os.path.splitext(file)
                        counter = 1
                        while os.path.exists(dst_filepath):
                            new_filename = f"{name}_{counter}{file_ext}"
                            dst_filepath = os.path.join(target_dir, new_filename)
                            counter += 1

                # 4. 파일 쓰기 완료 검증 (21초 x 2회 대기)
                self.log(f"[CHECKING] {file} (21초 x 2회 대기)...")
                if not self._is_file_ready(src_filepath, file):
                    self.log(f"[SKIP] {file} (생성 중이거나 변경됨)")
                    continue

                # 5. 파일 복사 및 원본 삭제 처리
                try:
                    self.log(f"[COPY START] {file} -> {target_dir}")
                    shutil.copy2(src_filepath, dst_filepath)
                    self.log(f"[COPY DONE] {file}")

                    if self.delete_after_copy_var.get():
                        os.remove(src_filepath)
                        self.log(f"[DELETE SRC] {src_filepath}")

                except Exception as e:
                    self.log(f"[ERROR] 복사 실패 ({file}): {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = MAMAutoCopierApp(root)
    root.mainloop()
