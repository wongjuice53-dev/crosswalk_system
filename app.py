# -*- coding: utf-8 -*-
"""Flask Web 后端：视频上传、区域配置、MJPEG 实时流、违规记录查询（论文4.7节）"""
import os
import time
import cv2
from flask import Flask, request, jsonify, render_template, Response, send_file, redirect

import config as cfgmod
import db
from pipeline import VideoProcessor, BASE

app = Flask(__name__)
UPLOAD_DIR = os.path.join(BASE, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
db.init()
proc = VideoProcessor()

ALLOWED = {".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv"}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/upload", methods=["POST"])
def upload():
    f = request.files.get("video")
    if not f:
        return jsonify(ok=False, msg="未选择文件")
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ALLOWED:
        return jsonify(ok=False, msg="不支持的格式：" + ext)
    path = os.path.join(UPLOAD_DIR, "source" + ext)
    f.save(path)
    cfg = cfgmod.load()
    cfg["video_source"] = path
    cfgmod.save(cfg)
    # 抽取首帧用于画布底图
    cap = cv2.VideoCapture(path)
    ok, frame = cap.read()
    cap.release()
    if ok:
        cv2.imwrite(os.path.join(BASE, "static", "first_frame.jpg"), frame)
        h, w = frame.shape[:2]
        return jsonify(ok=True, msg="上传成功", width=w, height=h)
    return jsonify(ok=False, msg="视频无法解码")


@app.route("/api/config", methods=["GET", "POST"])
def config_api():
    if request.method == "GET":
        return jsonify(cfgmod.load())
    data = request.get_json(force=True)
    cfg = cfgmod.load()
    for k in ("crosswalk", "road", "light_rect", "detector", "confirm_frames", "detect_interval"):
        if k in data:
            cfg[k] = data[k]
    cfgmod.save(cfg)
    return jsonify(ok=True)


@app.route("/api/start", methods=["POST"])
def start():
    ok, msg = proc.start()
    return jsonify(ok=ok, msg=msg)


@app.route("/api/stop", methods=["POST"])
def stop():
    proc.stop()
    return jsonify(ok=True)


@app.route("/api/status")
def status():
    return jsonify(status=proc.status, fps=round(proc.fps, 1),
                   detector=proc.detector_name, light=proc.light_state,
                   ped=proc.ped_count, in_crosswalk=proc.crosswalk_count,
                   vio=db.counts())


def _mjpeg():
    blank = None
    while True:
        frame = proc.get_frame()
        if frame is None:
            if blank is None:
                import numpy as np
                img = np.zeros((360, 640, 3), dtype=np.uint8)
                cv2.putText(img, "waiting...", (240, 180), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                blank = cv2.imencode(".jpg", img)[1].tobytes()
            frame = blank
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
        time.sleep(0.04)


@app.route("/video_feed")
def video_feed():
    return Response(_mjpeg(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/records")
def records():
    vtype = request.args.get("type") or None
    rows = db.query(vtype)
    return render_template("records.html", rows=rows, vtype=vtype or "")


@app.route("/shot/<path:p>")
def shot(p):
    return send_file(os.path.join(BASE, p))


@app.route("/api/export")
def export():
    path = os.path.join(BASE, "violation_records.csv")
    db.export_csv(path)
    return send_file(path, as_attachment=True, download_name="violation_records.csv")


@app.route("/api/clear", methods=["POST"])
def clear():
    conn_path = db.DB_PATH
    import sqlite3
    conn = sqlite3.connect(conn_path)
    conn.execute("DELETE FROM violation_records")
    conn.commit()
    conn.close()
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
