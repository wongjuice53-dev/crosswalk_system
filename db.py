# -*- coding: utf-8 -*-
"""SQLite 违规记录存储，表结构与论文表3-1一致"""
import os
import sqlite3
import csv
import time

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "violation.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS violation_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    violation_time TEXT NOT NULL,
    violation_type TEXT NOT NULL,
    track_id INTEGER,
    position TEXT,
    light_state TEXT,
    screenshot_path TEXT,
    video_clip_path TEXT,
    video_source TEXT,
    confidence REAL,
    remark TEXT
);
"""

def init():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(SCHEMA)
    conn.commit()
    conn.close()

def insert(vtype, track_id, position, light_state, screenshot_path, video_source, confidence, remark=""):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "INSERT INTO violation_records (violation_time, violation_type, track_id, position, light_state, screenshot_path, video_clip_path, video_source, confidence, remark) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (time.strftime("%Y-%m-%d %H:%M:%S"), vtype, track_id, position, light_state, screenshot_path, "", video_source, confidence, remark),
    )
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid

def query(vtype=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    sql = "SELECT * FROM violation_records"
    args = []
    if vtype:
        sql += " WHERE violation_type=?"
        args.append(vtype)
    sql += " ORDER BY id DESC"
    rows = conn.execute(sql, args).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def counts():
    conn = sqlite3.connect(DB_PATH)
    total = conn.execute("SELECT COUNT(*) FROM violation_records").fetchone()[0]
    red = conn.execute("SELECT COUNT(*) FROM violation_records WHERE violation_type='crossing_red'").fetchone()[0]
    jay = conn.execute("SELECT COUNT(*) FROM violation_records WHERE violation_type='jaywalking'").fetchone()[0]
    conn.close()
    return {"total": total, "crossing_red": red, "jaywalking": jay}

def export_csv(path):
    rows = query()
    cols = ["id", "violation_time", "violation_type", "track_id", "position", "light_state", "screenshot_path", "video_clip_path", "video_source", "confidence", "remark"]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        wcsv = csv.DictWriter(f, fieldnames=cols)
        wcsv.writeheader()
        for r in rows:
            wcsv.writerow(r)
    return path
