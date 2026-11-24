# -*- coding: utf-8 -*-
"""视频处理流水线：采集 -> 预处理 -> 检测 -> 跟踪 -> 信号灯 -> 判定 -> 标记（论文4.2/4.3节）"""
import os
import time
import threading
import cv2
import numpy as np

import config as cfgmod
import db
from detector import Detector
from tracker import Tracker
from light import LightRecognizer
from judge import Judge, OUTSIDE, INSIDE, CROSSING, VIOLATED, _foot, _inside

BASE = os.path.dirname(os.path.abspath(__file__))
SHOT_DIR = os.path.join(BASE, "screenshots")

class VideoProcessor:
    def __init__(self):
        self.thread = None
        self.stop_flag = threading.Event()
        self.frame_jpg = None      # 最新标注帧（JPEG bytes）
        self.lock = threading.Lock()
        self.status = "idle"       # idle / running / stopped / finished / error
        self.fps = 0.0
        self.detector_name = "-"
        self.light_state = "unknown"
        self.ped_count = 0        # 当前画面跟踪到的行人数
        self.crosswalk_count = 0  # 当前处于人行横道区域内的行人数
        self.cfg = None

    def start(self):
        self.cfg = cfgmod.load()
        if not self.cfg["video_source"] or not os.path.exists(self.cfg["video_source"]):
            return False, "请先上传视频"
        if len(self.cfg["crosswalk"]) < 3:
            return False, "请先在画面上圈画人行横道区域"
        if self.thread and self.thread.is_alive():
            return False, "已在运行"
        self.stop_flag.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        return True, "started"

    def stop(self):
        self.stop_flag.set()

    def _annotate(self, frame, tracks, judge):
        # 画区域
        if len(self.cfg["crosswalk"]) >= 3:
            pts = np.array(self.cfg["crosswalk"], dtype=np.int32)
            cv2.polylines(frame, [pts], True, (255, 200, 0), 2)
        if len(self.cfg["road"]) >= 3:
            pts = np.array(self.cfg["road"], dtype=np.int32)
            cv2.polylines(frame, [pts], True, (0, 200, 255), 2)
        if len(self.cfg["light_rect"]) == 4:
            x, y, w, h = [int(v) for v in self.cfg["light_rect"]]
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
        for t in tracks:
            x1, y1, x2, y2 = [int(v) for v in t.bbox]
            st = judge.state_of(t.id)
            if st == VIOLATED:
                color = (0, 0, 255)
            elif st == CROSSING:
                color = (0, 165, 255)
            else:
                color = (0, 200, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, "ID%d" % t.id, (x1, max(0, y1 - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            for i in range(1, len(t.history)):
                p1 = (int(t.history[i-1][0]), int(t.history[i-1][1]))
                p2 = (int(t.history[i][0]), int(t.history[i][1]))
                cv2.line(frame, p1, p2, (255, 0, 255), 1)
        cv2.putText(frame, "light: %s  det: %s  %.1fFPS" % (self.light_state, self.detector_name, self.fps),
                    (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        return frame

    def _run(self):
        self.status = "running"
        try:
            det = Detector(self.cfg["detector"])
            self.detector_name = det.name
        except Exception as e:
            self.status = "error"
            self.frame_jpg = None
            print("detector init failed:", e)
            return
        tracker = Tracker(self.cfg["iou_thresh"], self.cfg["match_dist"], self.cfg["max_age"], self.cfg["n_init"])
        light = LightRecognizer(self.cfg["light_rect"])
        judge = Judge(self.cfg["crosswalk"], self.cfg["road"],
                      self.cfg["confirm_frames"], self.cfg["min_cross_frames"], self.cfg["cross_disp"])

        cap = cv2.VideoCapture(self.cfg["video_source"])
        if not cap.isOpened():
            self.status = "error"
            return
        frame_idx = 0
        dets = []
        t0 = time.time()
        n = 0
        while not self.stop_flag.is_set():
            ok, frame = cap.read()
            if not ok:
                self.status = "finished"
                break
            frame_idx += 1
            # 预处理：灰度化+高斯滤波（供检测/边缘使用）
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            cv2.GaussianBlur(gray, (5, 5), 0)
            if frame_idx % self.cfg["detect_interval"] == 0 or not dets:
                dets = det.detect(frame)
            tracks = tracker.update(dets)
            self.ped_count = len(tracks)
            cw = self.cfg["crosswalk"]
            self.crosswalk_count = sum(1 for t in tracks if len(cw) >= 3 and _inside(_foot(t.bbox), cw))
            self.light_state = light.state(frame)
            events = judge.update(tracks, self.light_state)
            for t, vtype in events:
                x1, y1, x2, y2 = [int(v) for v in t.bbox]
                shot = os.path.join(SHOT_DIR, "v_%d_%d.jpg" % (t.id, int(time.time())))
                cv2.imwrite(shot, self._annotate(frame.copy(), tracks, judge))
                db.insert(vtype, t.id, "(%d,%d)" % ((x1 + x2) // 2, y2),
                          self.light_state, os.path.relpath(shot, BASE).replace("\\", "/"),
                          os.path.basename(self.cfg["video_source"]), round(t.conf, 3),
                          "闯红灯" if vtype == "crossing_red" else "违规横穿")
                print("violation:", vtype, "track", t.id)
            out = self._annotate(frame, tracks, judge)
            ok2, jpg = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ok2:
                with self.lock:
                    self.frame_jpg = jpg.tobytes()
            n += 1
            if n >= 25:
                self.fps = n / (time.time() - t0)
                t0, n = time.time(), 0
        cap.release()
        if self.status == "running":
            self.status = "stopped"

    def get_frame(self):
        with self.lock:
            return self.frame_jpg
