# -*- coding: utf-8 -*-
"""
YOLOv5 object detection blueprint for Smart Home IoT.
Routes: /yolo page + /yolo/api/* endpoints.
"""
import base64
import os
import sys
from pathlib import Path

import cv2
import numpy as np
import torch
from flask import Blueprint, Response, jsonify, render_template, request
from PIL import Image

# -- YOLOv5 path setup --
FILE = Path(__file__).resolve()
ROOT = FILE.parents[1]  # smart-home-iot root
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# YOLOv5 core modules live in yolo_models/ and utils/
from yolo_models.common import DetectMultiBackend
from utils.augmentations import letterbox
from utils.general import check_img_size, non_max_suppression, scale_boxes
from utils.torch_utils import select_device
from ultralytics.utils.plotting import Annotator, colors

# ---------------------------------------------------------------------------
# Blueprint
# ---------------------------------------------------------------------------
yolo_bp = Blueprint("yolo", __name__, template_folder="../templates")

# ---------------------------------------------------------------------------
# Configurable defaults
# ---------------------------------------------------------------------------
WEIGHTS = ROOT / "yolov5s.pt"
IMGSZ = (640, 640)
CONF_THRES = 0.35
IOU_THRES = 0.45
DEVICE = ""

# ---------------------------------------------------------------------------
# Global model handle (lazy-loaded on first request)
# ---------------------------------------------------------------------------
_model = None
_stride = None
_names = None
_dev = None


def _get_model():
    global _model, _stride, _names, _dev
    if _model is not None:
        return _model, _stride, _names, _dev

    _dev = select_device(DEVICE)
    _model = DetectMultiBackend(str(WEIGHTS), device=_dev)
    _stride = _model.stride
    _names = _model.names
    imgsz_check = check_img_size(IMGSZ, s=_stride)
    _model.warmup(imgsz=(1, 3, *imgsz_check))
    print(f"[YOLO] Model loaded: {WEIGHTS} on {_dev}")
    return _model, _stride, _names, _dev


def _preprocess(im0, img_size, stride):
    im = letterbox(im0, img_size, stride=stride, auto=True)[0]
    im = im.transpose((2, 0, 1))[::-1]  # HWC → CHW, BGR → RGB
    im = np.ascontiguousarray(im)
    im = torch.from_numpy(im).float() / 255.0
    if im.ndim == 3:
        im = im.unsqueeze(0)
    return im


def _run_detection(im0, conf_thres=CONF_THRES, iou_thres=IOU_THRES, classes=None):
    model_, stride, names_, dev_ = _get_model()
    im = _preprocess(im0, IMGSZ, stride)
    im = im.to(dev_)
    if model_.fp16:
        im = im.half()

    pred = model_(im)
    pred = non_max_suppression(pred, conf_thres, iou_thres, classes=classes)

    detections = []
    annotator = Annotator(im0.copy(), line_width=2, example=str(names_))

    for det in pred:
        if len(det):
            det[:, :4] = scale_boxes(im.shape[2:], det[:, :4], im0.shape).round()
            for *xyxy, conf, cls in reversed(det):
                c = int(cls)
                label = f"{names_[c]} {conf:.2f}"
                annotator.box_label(xyxy, label, color=colors(c, True))
                detections.append({
                    "class": names_[c],
                    "class_id": c,
                    "confidence": round(float(conf), 4),
                    "bbox": [int(x) for x in xyxy],
                })

    return annotator.result(), detections


def _parse_classes(raw):
    if not raw or not raw.strip():
        return None
    try:
        ids = [int(x.strip()) for x in raw.replace(",", " ").split() if x.strip()]
        return ids if ids else None
    except ValueError:
        return None


# ==============================  ROUTES  ====================================

@yolo_bp.route("/")
def yolo_page():
    return render_template("yolo.html")


@yolo_bp.route("/api/model_info")
def model_info():
    _, _, names_, _ = _get_model()
    if isinstance(names_, dict):
        items = [{"id": int(k), "name": str(v)} for k, v in names_.items()]
    else:
        items = [{"id": i, "name": str(n)} for i, n in enumerate(names_)]
    return jsonify({"classes": items, "total": len(items)})


@yolo_bp.route("/api/detect_image", methods=["POST"])
def detect_image_api():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    file_bytes = np.frombuffer(file.read(), np.uint8)
    im0 = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if im0 is None:
        return jsonify({"error": "Cannot decode image"}), 400

    classes = _parse_classes(request.args.get("classes", ""))
    annotated, detections = _run_detection(im0, classes=classes)

    _, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
    img_b64 = base64.b64encode(buf).decode("utf-8")

    return jsonify({
        "image": f"data:image/jpeg;base64,{img_b64}",
        "detections": detections,
        "count": len(detections),
    })


@yolo_bp.route("/api/detect_frame", methods=["POST"])
def detect_frame_api():
    data = request.get_json(force=True)
    if not data or "frame" not in data:
        return jsonify({"error": "No frame data"}), 400

    frame_str = data["frame"]
    if "," in frame_str:
        frame_str = frame_str.split(",", 1)[1]

    try:
        img_bytes = base64.b64decode(frame_str)
    except Exception:
        return jsonify({"error": "Invalid base64"}), 400

    im0 = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    if im0 is None:
        return jsonify({"error": "Cannot decode frame"}), 400

    conf = float(request.args.get("conf", CONF_THRES))
    iou = float(request.args.get("iou", IOU_THRES))
    classes = _parse_classes(data.get("classes", "") or request.args.get("classes", ""))

    annotated, detections = _run_detection(im0, conf_thres=conf, iou_thres=iou, classes=classes)

    _, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
    img_b64 = base64.b64encode(buf).decode("utf-8")

    return jsonify({
        "frame": f"data:image/jpeg;base64,{img_b64}",
        "detections": detections,
        "count": len(detections),
    })
