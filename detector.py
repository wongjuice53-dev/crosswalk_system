# -*- coding: utf-8 -*-
"""行人检测器：YOLOv8n 优先，无 ultralytics 时降级为 OpenCV 内置 HOG+SVM（论文2.3节）"""
import cv2

class Detector:
    def __init__(self, mode="auto"):
        self.mode = mode
        self.yolo = None
        self.hog = None
        use_yolo = mode in ("auto", "yolo")
        if use_yolo:
            try:
                from ultralytics import YOLO
                self.yolo = YOLO("yolov8n.pt")  # 首次运行自动下载权重
                self.name = "YOLOv8n"
            except Exception:
                self.yolo = None
                if mode == "yolo":
                    raise RuntimeError("YOLO 模式需要安装 ultralytics：pip install ultralytics")
        if self.yolo is None:
            self.hog = cv2.HOGDescriptor()
            self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            self.name = "HOG+SVM"

    def detect(self, frame):
        """返回 [(x1,y1,x2,y2,conf), ...]"""
        if self.yolo is not None:
            res = self.yolo.predict(frame, classes=[0], verbose=False, imgsz=640)[0]
            out = []
            for b in res.boxes:
                x1, y1, x2, y2 = [int(v) for v in b.xyxy[0].tolist()]
                out.append((x1, y1, x2, y2, float(b.conf[0])))
            return out
        # HOG 降级方案：缩小检测提速
        small = cv2.resize(frame, None, fx=0.6, fy=0.6)
        rects, weights = self.hog.detectMultiScale(small, winStride=(8, 8), scale=1.05)
        out = []
        for (x, y, w, h), wt in zip(rects, weights):
            out.append((int(x / 0.6), int(y / 0.6), int((x + w) / 0.6), int((y + h) / 0.6), float(wt)))
        return out
