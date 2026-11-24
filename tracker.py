# -*- coding: utf-8 -*-
"""多目标跟踪：IoU + 中心距最近邻匹配（SORT 简化形式，论文2.4/4.4节）"""
import math

def _iou(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    ua = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
    return inter / ua if ua > 0 else 0.0

def _center(b):
    return ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0)

class Track:
    _next_id = 1

    def __init__(self, bbox, conf, n_init):
        self.id = Track._next_id
        Track._next_id += 1
        self.bbox = bbox
        self.conf = conf
        self.hits = 1
        self.misses = 0
        self.n_init = n_init
        self.history = [_center(bbox)]  # 轨迹点（中心点序列）

    @property
    def confirmed(self):
        return self.hits >= self.n_init

    def update(self, bbox, conf):
        self.bbox = bbox
        self.conf = conf
        self.hits += 1
        self.misses = 0
        self.history.append(_center(bbox))
        if len(self.history) > 200:
            self.history = self.history[-200:]

class Tracker:
    def __init__(self, iou_thresh=0.1, match_dist=80, max_age=30, n_init=3):
        self.iou_thresh = iou_thresh
        self.match_dist = match_dist
        self.max_age = max_age
        self.n_init = n_init
        self.tracks = []

    def update(self, detections):
        unmatched = set(range(len(self.tracks)))
        for (x1, y1, x2, y2, conf) in detections:
            best, best_score = -1, -1.0
            for i in unmatched:
                t = self.tracks[i]
                iou = _iou(t.bbox, (x1, y1, x2, y2))
                cx1, cy1 = _center(t.bbox)
                cx2, cy2 = _center((x1, y1, x2, y2))
                dist = math.hypot(cx1 - cx2, cy1 - cy2)
                if iou >= self.iou_thresh:
                    score = 1.0 + iou
                elif dist <= self.match_dist:
                    score = 1.0 - dist / self.match_dist
                else:
                    continue
                if score > best_score:
                    best, best_score = i, score
            if best >= 0:
                self.tracks[best].update((x1, y1, x2, y2), conf)
                unmatched.discard(best)
            else:
                self.tracks.append(Track((x1, y1, x2, y2), conf, self.n_init))
        for i in unmatched:
            self.tracks[i].misses += 1
        self.tracks = [t for t in self.tracks if t.misses <= self.max_age]
        return [t for t in self.tracks if t.confirmed]
