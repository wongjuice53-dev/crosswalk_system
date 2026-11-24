# -*- coding: utf-8 -*-
"""配置管理：区域、检测器、阈值等，持久化到 config.json"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CFG_PATH = os.path.join(BASE, "config.json")

DEFAULTS = {
    "detector": "auto",        # auto / yolo / hog
    "video_source": "",        # 当前视频文件路径
    "crosswalk": [],           # 人行横道多边形 [[x,y],...]
    "road": [],                # 道路区域多边形（可选，用于违规横穿判定）
    "light_rect": [],          # 信号灯矩形 [x,y,w,h]
    "detect_interval": 2,      # 每隔几帧做一次检测
    "confirm_frames": 8,       # 连续多少帧确认违规
    "min_cross_frames": 5,     # 进入区域至少多少帧才算穿越
    "cross_disp": 30,          # 穿越位移阈值（像素）
    "match_dist": 80,          # 跟踪匹配中心距阈值
    "iou_thresh": 0.1,
    "max_age": 30,
    "n_init": 3,
}

def load():
    cfg = dict(DEFAULTS)
    if os.path.exists(CFG_PATH):
        try:
            with open(CFG_PATH, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass
    return cfg

def save(cfg):
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
