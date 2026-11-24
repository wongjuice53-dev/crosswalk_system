# -*- coding: utf-8 -*-
"""违规判定状态机：区域 + 信号灯 + 轨迹三要素，连续帧确认（论文4.6节）

四状态：OUTSIDE(区域外) -> INSIDE(进入人行横道) -> CROSSING(持续移动) -> VIOLATED(确认违规)
- 闯红灯 crossing_red：红灯期间进入人行横道区域并持续穿越
- 违规横穿 jaywalking：在道路区域内、人行横道外持续穿行
"""
import cv2
import numpy as np

OUTSIDE, INSIDE, CROSSING, VIOLATED = 0, 1, 2, 3

def _foot(bbox):
    return ((bbox[0] + bbox[2]) / 2.0, float(bbox[3]))

def _inside(pt, polygon):
    if not polygon or len(polygon) < 3:
        return False
    return cv2.pointPolygonTest(np.array(polygon, dtype=np.float32), pt, False) >= 0

class TrackJudge:
    def __init__(self):
        self.state = OUTSIDE
        self.counter = 0          # 处于疑似违规状态的连续帧数
        self.inside_frames = 0
        self.enter_pos = None
        self.enter_light = "unknown"

class Judge:
    def __init__(self, crosswalk, road, confirm_frames=8, min_cross_frames=5, cross_disp=30):
        self.crosswalk = crosswalk
        self.road = road
        self.confirm_frames = confirm_frames
        self.min_cross_frames = min_cross_frames
        self.cross_disp = cross_disp
        self.states = {}  # track_id -> TrackJudge

    def update(self, tracks, light_state):
        """返回新确认的违规事件列表 [(track, vtype)]"""
        events = []
        alive = set()
        for t in tracks:
            alive.add(t.id)
            js = self.states.setdefault(t.id, TrackJudge())
            if js.state == VIOLATED:
                continue
            pt = _foot(t.bbox)
            in_cross = _inside(pt, self.crosswalk)
            in_road_not_cross = _inside(pt, self.road) and not in_cross

            # 状态迁移
            if js.state == OUTSIDE and (in_cross or in_road_not_cross):
                js.state = INSIDE
                js.inside_frames = 0
                js.enter_pos = pt
                js.enter_light = light_state
            if js.state in (INSIDE, CROSSING) and not (in_cross or in_road_not_cross):
                # 离开区域，回到区域外（未确认违规）
                js.state = OUTSIDE
                js.counter = 0
                js.inside_frames = 0
                continue

            if js.state == INSIDE:
                js.inside_frames += 1
                if js.inside_frames >= self.min_cross_frames and js.enter_pos is not None:
                    disp = abs(pt[0] - js.enter_pos[0]) + abs(pt[1] - js.enter_pos[1])
                    if disp >= self.cross_disp:
                        js.state = CROSSING

            if js.state == CROSSING:
                # 判定违规类型：红灯穿越人行横道 优先；否则 道路内横穿
                if in_cross and light_state == "red":
                    cand = "crossing_red"
                elif in_road_not_cross:
                    cand = "jaywalking"
                else:
                    cand = None
                if cand:
                    js.counter += 1
                    if js.counter >= self.confirm_frames:
                        js.state = VIOLATED
                        events.append((t, cand))
                else:
                    js.counter = 0

        for tid in [tid for tid in self.states if tid not in alive]:
            del self.states[tid]
        return events

    def state_of(self, track_id):
        js = self.states.get(track_id)
        return js.state if js else OUTSIDE
