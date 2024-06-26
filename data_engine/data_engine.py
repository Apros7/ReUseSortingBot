"""
Data Engine classes
- DataRecorder: Used to record and store new videos         (POST)
- DataExplorer: Used to load, get, sort and explore data    (GET)
"""

import subprocess
import os
import cv2
import time
import logging
from datetime import datetime
import shutil

from utils import get_free_filename

logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s, %(levelname)s]: %(message)s')

def get_top_folder(): return subprocess.check_output(["git", "rev-parse", "--show-toplevel"]).decode('utf-8').strip("\n")

class BaseModel():
    def __init__(self, cap): self.cap = cap; self.should_quit = False
    def quit(self):
        if self.cap: self.cap.release()
        cv2.destroyAllWindows()
        self.should_quit = True

class DataRecorder(BaseModel):
    def __init__(self):
        self.top_folder = get_top_folder()
        if not os.path.exists(self.top_folder): os.makedirs(self.top_folder)

        self.fps = 10
        self.recording = False
        self.cap = cv2.VideoCapture(0)
        self.frames_index = 0
        # self.fourcc = cv2.VideoWriter_fourcc(*'avc1')
        # self.fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        super().__init__(self.cap)

    def add_description(self, frame): 
        return cv2.rectangle(frame, (10, 10), (50, 30), (0, 0, 255), 2) if self.recording else cv2.rectangle(frame, (10, 10), (50, 30), (128, 128, 128), 2)

    def record(self, start): 
        if not start and self.recording: self.recording = False; self.frames_index = 0
        if not self.recording and start: 
            self.data_folder = get_free_filename()
            if not os.path.exists(self.data_folder): os.makedirs(self.data_folder)
            self.recording = True
            self.frame_dir = os.path.join(self.top_folder, self.data_folder)

    def record_frame(self, frame):
        cv2.imwrite(os.path.join(self.frame_dir, f"frame_{self.frames_index:04d}.jpg"), frame)
        self.frames_index += 1

    def run(self):
        while True:
            _, frame = self.cap.read()
            cv2.imshow("Camera", self.add_description(frame.copy()))
            if self.recording: 
                self.record_frame(frame)
            key = cv2.waitKey(1000//self.fps) & 0xFF
            if key == ord('q'): self.quit(); break
            if key == ord('r'): self.record(start=True)
            if key == ord('s'): self.record(start=False)

class DataExplorer(BaseModel):
    def __init__(self, explore: str = "new"):
        self.check_new_folder()
        if explore not in ["new", "verified", "labelled"]:
            raise LookupError(f"Data folder to explore has to be one of {["new", "verified", "labelled"]}, but is {explore}")
        self.fps = 10
        self.data_folder = os.path.join(get_top_folder(), "data", explore)
        self.pause = False
        self.files_skipped = [] # when reloading folder, remember already skipped files
        self.files = sorted(os.listdir(self.data_folder))
        logging.info("\n".join(["You can choose from the following list: ", "--------", 
                                *[f"{l}: {df}" for l, df in enumerate(self.files)], "--------"]))
        super().__init__(None)

    def check_new_folder(self):
        print("Checking 'new' folder for videos too long...")
        path = os.path.join(get_top_folder(), "data", "new")
        for folder in os.listdir(path):
            folder_path = os.path.join(path, folder)
            files = [f for f in os.listdir(folder_path) if f.startswith('frame_') and f.endswith('.jpg')]
            files.sort(key=lambda x: int(x.split('_')[1].split('.')[0]))

            num_parts = (len(files) + 99) // 100
            if num_parts < 2: continue
            print(num_parts, "for", folder_path)
            for i in range(num_parts):
                part_folder = os.path.join(path, f'{folder}_part_{i+1}')
                os.makedirs(part_folder, exist_ok=True)
                print("putting", part_folder)
                for j in range(100):
                    file_index = i * 100 + j
                    if file_index < len(files):
                        file_path = os.path.join(folder_path, files[file_index])
                        shutil.move(file_path, part_folder)
            self.delete(folder_path)
        print("Done checking")


    def add_description(self, frame):
        font = cv2.FONT_HERSHEY_DUPLEX
        font_scale = 0.5
        thickness = 1

        frame = frame.copy()
        cv2.rectangle(frame, (0, 0), (280, 210), (255, 255, 255), -1)

        text = "Press 'p' to (un)pause"
        cv2.putText(frame, text, (10, 20), font, font_scale, (0, 0, 0), thickness)

        text = "Press 'q' to quit"
        cv2.putText(frame, text, (10, 40), font, font_scale, (0, 0, 0), thickness)

        text = "Press 'a' to accept"
        cv2.putText(frame, text, (10, 60), font, font_scale, (0, 0, 0), thickness)

        text = "Press 's' to skip"
        cv2.putText(frame, text, (10, 80), font, font_scale, (0, 0, 0), thickness)

        text = "Press 'd' to delete"
        cv2.putText(frame, text, (10, 100), font, font_scale, (0, 0, 0), thickness)

        text = "Press 'r' to review"
        cv2.putText(frame, text, (10, 120), font, font_scale, (0, 0, 0), thickness)

        text = "Press 'b' to back 1 frame"
        cv2.putText(frame, text, (10, 140), font, font_scale, (0, 0, 0), thickness)

        text = "Press 'n' to next 1 frames"
        cv2.putText(frame, text, (10, 160), font, font_scale, (0, 0, 0), thickness)

        text = "Press 'k' to delete prev. frame"
        cv2.putText(frame, text, (10, 180), font, font_scale, (0, 0, 0), thickness)

        text = "Press 'l' to accept prev. frames"
        cv2.putText(frame, text, (10, 200), font, font_scale, (0, 0, 0), thickness)


        return frame

    def prompt_index(self): return int(input("What index to you want to see (put -1 if all): "))
    
    def accept(self, file_path):
        verified_dir = 'data/verified'
        if not os.path.exists(verified_dir):
            os.makedirs(verified_dir)
        filename = os.path.basename(file_path)
        shutil.move(file_path, os.path.join(verified_dir, filename))

    def accept_prev_frames(self, file_to_view, frame_files, up_to_index):
        new_filename = get_free_filename(file_to_view.split("_")[-2])
        verified_dir = 'data/verified'
        if not os.path.exists(verified_dir):
            os.makedirs(verified_dir)
        filename = os.path.basename(new_filename)
        frames_files_to_move = frame_files[:up_to_index]

        new_dir = os.path.join(verified_dir, filename)
        if not os.path.exists(new_dir):
            os.makedirs(new_dir)

        for file in frames_files_to_move:
            shutil.move(os.path.join(file_to_view, file), new_dir)

    def delete_files(self, file_to_view, frame_files, up_to_index):
        for frame in frame_files[:up_to_index]:
            os.remove(os.path.join(file_to_view, frame))

    def delete(self, file_path):
        if os.path.exists(file_path):
            shutil.rmtree(file_path)

    # def _freeze(self, file_to_view, frame, frame_files, index, allow_pause):
    #     while True:
    #         cv2.imshow("frame", self.add_description(frame))
    #         key = cv2.waitKey(1000//self.fps) & 0xFF
    #         if key == ord('q'): self.quit(); return True
    #         if key == ord('a'): self.accept(file_to_view); return True
    #         if key == ord('s'): self.files_skipped.append(file_to_view); return True
    #         if key == ord('d'): self.delete(file_to_view); return True
    #         if key == ord('r'): self._view(index); self.pause = False; return True
    #         if key == ord('p') and allow_pause: self.pause = not self.pause; return False
    #         if key == ord('b'): self.delete_files(frame_files, index); self.pause = False; self._view(index); return False
    #         if key == ord('n'): self.accept_prev_frames(file_to_view, frame_files, index); return True

    def _view(self, index: int = None):
        file_to_view = os.path.join(self.data_folder, self.files[index])
        logging.info(f"Viewing: {file_to_view}")
        frame_files = sorted(os.listdir(file_to_view))
        frame_index = 0

        while True:
            cv2.namedWindow("frame", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("frame", 800, 600)
            frame_path = os.path.join(file_to_view, frame_files[frame_index])
            frame = cv2.imread(frame_path)
            cv2.imshow("frame", self.add_description(frame))
            key = cv2.waitKey(1000//self.fps) & 0xFF
            if key == ord('q'): self.quit(); break
            if key == ord('a'): self.accept(file_to_view); self.files_skipped.append(self.files[index]); return
            if key == ord('s'): self.files_skipped.append(self.files[index]); return
            if key == ord('d'): self.delete(file_to_view); return
            if key == ord('r'): frame_index = 0; self.pause = False
            if key == ord('p'): self.pause = not self.pause
            if key == ord('b'): frame_index -= 1
            if key == ord('n'): frame_index += 1
            if key == ord('k'): self.delete_files(file_to_view, frame_files, frame_index); self.pause = False; frame_index = 0; return False
            if key == ord('l'): self.accept_prev_frames(file_to_view, frame_files, frame_index); return True

            if not self.pause:
                frame_index += 1

            if frame_index >= len(frame_files): frame_index = len(frame_files) - 1
            if frame_index < 0: frame_index = 0

    def _reload(self):
        self.files = sorted(os.listdir(self.data_folder))
        return [file for file in self.files if file not in self.files_skipped]
    
    def view(self, index: int = None):
        index = self.prompt_index() if index is None else index
        if index > len(self.files) - 1: logging.warning(f"Your index is {index}, but max is {len(self.files) - 1}, so setting it to -1"); index = -1
        if index >= 0: self._view(index); return
        while True:
            if self.should_quit: break
            unseen_files = self._reload()
            if len(unseen_files) == 0: break
            for i in range(len(self.files)): self._view(i)


if __name__ == "__main__":
    # DataRecorder().run()
    # DataExplorer().view(-1)
    DataExplorer(explore = "verified").view(-1)
