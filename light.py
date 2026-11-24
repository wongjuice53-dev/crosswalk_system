# -*- coding: utf-8 -*-
"""信号灯识别：HSV 阈值 + 区域判定（论文4.5节）"""
import cv2
import numpy as np

class LightRecognizer:
    def __init__(self, rect):
        """rect = [x, y, w, h]，用户在浏览器里框选信号灯所在区域"""
        self.rect = rect

    def state(self, frame):
        if not self.rect or len(self.rect) != 4:
            return "unknown"
        x, y, w, h = [int(v) for v in self.rect]
        if w <= 0 or h <= 0:
            return "unknown"
        fh, fw = frame.shape[:2]
        x, y = max(0, x), max(0, y)
        roi = frame[y:min(fh, y + h), x:min(fw, x + w)]
        if roi.size == 0:
            return "unknown"
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        # 红色两段 H 区间
        red1 = cv2.inRange(hsv, (0, 100, 100), (10, 255, 255))
        red2 = cv2.inRange(hsv, (170, 100, 100), (180, 255, 255))
        green = cv2.inRange(hsv, (50, 100, 100), (85, 255, 255))
        total = roi.shape[0] * roi.shape[1]
        r_ratio = (cv2.countNonZero(red1) + cv2.countNonZero(red2)) / total
        g_ratio = cv2.countNonZero(green) / total
        if r_ratio > 0.02 and r_ratio > g_ratio:
            return "red"
        if g_ratio > 0.02 and g_ratio > r_ratio:
            return "green"
        return "unknown"
