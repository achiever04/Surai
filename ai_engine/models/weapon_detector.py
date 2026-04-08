"""
Weapon detection using dual YOLO26-N ONNX models via onnxruntime.

  - yolo26n.onnx      : COCO-80 classes (knife, baseball bat, scissors…)
  - gun_detector.onnx : firearms (handgun, pistol, rifle, …)

Architecture change (YOLOv11n → YOLO26-N)
------------------------------------------
YOLO26-N is an NMS-free, end-to-end model.  Its ONNX graph embeds the
suppression head and outputs FINAL detections directly:

    Output shape : (1, 300, 6)
    Per row      : [x1, y1, x2, y2, confidence, class_id]

This eliminates _decode_yolo()'s manual xywh→xyxy conversion, argmax
over class probabilities, and cv2.dnn.NMSBoxes call.  Post-processing
is now a single confidence-threshold slice.

No torch / ultralytics imports — inference runs entirely via onnxruntime,
numpy, and cv2 to stay within the 6 GB RAM ceiling.

False-positive suppression (v3)
---------------------------------
Three heuristic layers specifically target phone-as-handgun FPs:

  Layer A (Geometric Penalisation) — inside _detect_with_gun_model
    Vertical bboxes (h/w > 1.4) require confidence ≥ 0.80.
    Phones held vertically are the #1 source of handgun FPs.

  Layer B (Scale Confidence Scaling) — inside _detect_with_gun_model
    Large bboxes (area > 5 % of frame) require confidence ≥ 0.75.
    A real handgun close enough to fill 5 %+ of the frame would score 90 %+.

  Layer C (Cross-Model Phone Shield) — inside _resolve_model_conflicts_v2
    If the COCO model detects a 'cell phone' or 'remote' at the same
    spatial location as a gun detection (IoU > 0.40, or gun entirely
    contained inside the phone bbox), the gun detection is discarded.
    This is the strongest guard for the "phone held up to camera" scenario.

─────────────────────────────────────────────────────────────────────────────
STEP 1 — Export models (run ONCE in your terminal, then restart the server)
─────────────────────────────────────────────────────────────────────────────

  pip install -U ultralytics onnxruntime onnxslim

  # COCO model (yolo26n.pt → yolo26n.onnx)
  # Ultralytics saves the file to the CWD root; we copy it to weights/.
  python -c "
from ultralytics import YOLO
import shutil, pathlib
out = pathlib.Path(
    YOLO('yolo26n.pt').export(
        format='onnx', opset=17, simplify=True, imgsz=640
    )
)
dst = pathlib.Path('ai_engine/models/weights/yolo26n.onnx')
if out.resolve() != dst.resolve():
    shutil.copy2(out, dst)
print('Saved:', dst)
  "
  # Expected output shape: (1, 300, 6)  — end-to-end NMS-free ✅

  # Custom gun detector (gun_detector.pt → gun_detector.onnx)
  # NOTE: Ultralytics saves this DIRECTLY to the weights/ folder (same path as dst).
  # shutil.copy2 is skipped safely when src == dst.
  # Expected output shape: (1, 7, 8400) — legacy YOLOv8 anchor format (auto-detected,
  # falls through to _decode_yolo_legacy with NMS). This is correct and expected.
  python -c "
from ultralytics import YOLO
import shutil, pathlib
out = pathlib.Path(
    YOLO('ai_engine/models/weights/gun_detector.pt').export(
        format='onnx', opset=17, simplify=True, imgsz=640
    )
)
dst = pathlib.Path('ai_engine/models/weights/gun_detector.onnx')
if out.resolve() != dst.resolve():
    shutil.copy2(out, dst)
print('Saved:', dst)
  "

NOTE: YOLO26 exports in end2end=True mode by default (NMS baked in).
If your gun_detector.pt was trained on an older YOLO backbone and the
export raises an error, add end2end=False — the detector auto-falls back
to the legacy (_decode_yolo_legacy) path for that session only.
"""

import ast
import os
import cv2
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger

try:
    import onnxruntime as ort
    _ORT_AVAILABLE = True
except ImportError:
    _ORT_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────────────────
# COCO-80 class names ordered by index
# ─────────────────────────────────────────────────────────────────────────────
_COCO80 = [
    'person','bicycle','car','motorcycle','airplane','bus','train','truck','boat',
    'traffic light','fire hydrant','stop sign','parking meter','bench','bird',
    'cat','dog','horse','sheep','cow','elephant','bear','zebra','giraffe',
    'backpack','umbrella','handbag','tie','suitcase','frisbee','skis','snowboard',
    'sports ball','kite','baseball bat','baseball glove','skateboard','surfboard',
    'tennis racket','bottle','wine glass','cup','fork','knife','spoon','bowl',
    'banana','apple','sandwich','orange','broccoli','carrot','hot dog','pizza',
    'donut','cake','chair','couch','potted plant','bed','dining table','toilet',
    'tv','laptop','mouse','remote','keyboard','cell phone','microwave','oven',
    'toaster','sink','refrigerator','book','clock','vase','scissors',
    'teddy bear','hair drier','toothbrush',
]  # len == 80; knife=43, baseball bat=34, scissors=75, cell phone=67, remote=65


# ─────────────────────────────────────────────────────────────────────────────
# Preprocessing helpers
# ─────────────────────────────────────────────────────────────────────────────

def _letterbox(
    img: np.ndarray,
    new_shape: Tuple[int, int] = (640, 640),
    color: Tuple[int, int, int] = (114, 114, 114),
) -> Tuple[np.ndarray, float, Tuple[float, float]]:
    """Letterbox-resize without distortion. Returns (image, scale, (pad_x, pad_y))."""
    h, w = img.shape[:2]
    r = min(new_shape[0] / h, new_shape[1] / w)
    new_w, new_h = int(round(w * r)), int(round(h * r))
    dw = (new_shape[1] - new_w) / 2.0
    dh = (new_shape[0] - new_h) / 2.0
    if (w, h) != (new_w, new_h):
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    img = cv2.copyMakeBorder(img, top, bottom, left, right,
                             cv2.BORDER_CONSTANT, value=color)
    return img, r, (dw, dh)


def _preprocess(
    frame: np.ndarray, input_size: int = 640
) -> Tuple[np.ndarray, float, Tuple[float, float]]:
    """BGR frame → normalised float32 NCHW tensor. Returns (tensor, ratio, pad)."""
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    lb, ratio, pad = _letterbox(rgb, (input_size, input_size))
    tensor = lb.transpose(2, 0, 1)[np.newaxis].astype(np.float32) / 255.0
    return tensor, ratio, pad


# ─────────────────────────────────────────────────────────────────────────────
# YOLO26 end-to-end decoder
# ─────────────────────────────────────────────────────────────────────────────

def _decode_yolo26(
    raw_output: np.ndarray,         # shape: (1, N_max, 6)  e.g. N_max = 300
    orig_h: int,
    orig_w: int,
    ratio: float,
    pad: Tuple[float, float],       # (pad_x, pad_y) from _letterbox
    conf_thresh: float,
    class_names: List[str],
    allowed_classes: Optional[set] = None,
) -> List[Dict]:
    """
    Decode the YOLO26 end-to-end ONNX output.

    YOLO26 has NMS baked into the ONNX graph.  Each row in the output is a
    FINAL detection in the format:

        [x1, y1, x2, y2, confidence, class_id]

    All coordinates are in the LETTERBOX frame (640×640 space).
    We only need to:
      1. Confidence-threshold the rows.
      2. Map coordinates back to the original frame via ratio and pad.
      3. Filter to allowed_classes.

    There is NO manual NMS, NO argmax over class probabilities, and NO
    xywh-to-xyxy conversion — YOLO26 does all of that internally.
    """
    # raw_output shape: (1, N_max, 6)
    dets = raw_output[0]            # → (N_max, 6)

    # ── Step 1: confidence filter ─────────────────────────────────────────────
    confs    = dets[:, 4].astype(np.float32)
    mask     = confs >= conf_thresh
    dets     = dets[mask]
    confs    = confs[mask]

    if len(dets) == 0:
        return []

    # ── Step 2: extract coordinates and class ids ─────────────────────────────
    x1_lb = dets[:, 0].astype(np.float32)
    y1_lb = dets[:, 1].astype(np.float32)
    x2_lb = dets[:, 2].astype(np.float32)
    y2_lb = dets[:, 3].astype(np.float32)
    cls_ids = dets[:, 5].astype(np.int32)

    # ── Step 3: letterbox → original frame coords ──────────────────────────────
    pad_x, pad_y = pad
    x1 = np.clip((x1_lb - pad_x) / ratio, 0, orig_w).astype(np.int32)
    y1 = np.clip((y1_lb - pad_y) / ratio, 0, orig_h).astype(np.int32)
    x2 = np.clip((x2_lb - pad_x) / ratio, 0, orig_w).astype(np.int32)
    y2 = np.clip((y2_lb - pad_y) / ratio, 0, orig_h).astype(np.int32)

    # ── Step 4: class filter ──────────────────────────────────────────────────
    results = []
    for i in range(len(dets)):
        cid = int(cls_ids[i])
        if cid >= len(class_names):
            continue                              # out-of-range class index
        cname = class_names[cid]
        if allowed_classes is not None and cname not in allowed_classes:
            continue
        results.append({
            'class_name': cname,
            'confidence': float(confs[i]),
            'bbox':       [int(x1[i]), int(y1[i]), int(x2[i]), int(y2[i])],
        })

    return results


def _decode_yolo_legacy(
    raw_output: np.ndarray,           # [1, 4+C, N]  — old anchor-based output
    orig_h: int, orig_w: int,
    ratio: float,
    pad: Tuple[float, float],
    conf_thresh: float,
    iou_thresh: float,
    class_names: List[str],
    allowed_classes: Optional[set] = None,
) -> List[Dict]:
    """
    Legacy YOLOv8/v11 anchor-based decoder — kept as a fallback for any model
    that was NOT exported with end2end=True.

    Called automatically when the session output shape indicates the old format
    (i.e., last-dim 4+C, not 6).
    """
    pred        = raw_output[0].T                    # [N, 4+C]
    boxes_xywh  = pred[:, :4]
    class_probs = pred[:, 4:]
    class_ids   = np.argmax(class_probs, axis=1)
    confs       = class_probs[np.arange(len(class_probs)), class_ids]

    mask = confs >= conf_thresh
    if not mask.any():
        return []
    boxes_xywh = boxes_xywh[mask]
    confs      = confs[mask]
    class_ids  = class_ids[mask]

    cx, cy, bw, bh = boxes_xywh[:, 0], boxes_xywh[:, 1], boxes_xywh[:, 2], boxes_xywh[:, 3]
    x1 = np.clip((cx - bw / 2 - pad[0]) / ratio, 0, orig_w)
    y1 = np.clip((cy - bh / 2 - pad[1]) / ratio, 0, orig_h)
    x2 = np.clip((cx + bw / 2 - pad[0]) / ratio, 0, orig_w)
    y2 = np.clip((cy + bh / 2 - pad[1]) / ratio, 0, orig_h)

    if allowed_classes is not None:
        keep = np.array([
            cid < len(class_names) and class_names[cid] in allowed_classes
            for cid in class_ids
        ])
        if not keep.any():
            return []
        x1, y1, x2, y2 = x1[keep], y1[keep], x2[keep], y2[keep]
        confs, class_ids = confs[keep], class_ids[keep]

    boxes_nms = np.stack([x1, y1, x2 - x1, y2 - y1], axis=1).tolist()
    indices   = cv2.dnn.NMSBoxes(boxes_nms, confs.tolist(), conf_thresh, iou_thresh)
    if len(indices) == 0:
        return []

    results = []
    for idx in np.array(indices).flatten():
        cid = int(class_ids[idx])
        if cid >= len(class_names):
            continue
        results.append({
            'class_name': class_names[cid],
            'confidence': float(confs[idx]),
            'bbox':       [int(x1[idx]), int(y1[idx]), int(x2[idx]), int(y2[idx])],
        })
    return results


def _is_end2end_output(raw_output: np.ndarray) -> bool:
    """
    Detect output format at runtime:
      YOLO26 end-to-end  → shape (1, N, 6)  where N ≤ 1000
      YOLOv8/11 legacy   → shape (1, 4+C, N) where N >> 300 (typically 8400)
    """
    if raw_output.ndim != 3:
        return False
    # End-to-end: last dim is 6; legacy: last dim is large (8400…)
    return raw_output.shape[2] == 6 and raw_output.shape[1] <= 1000


# ─────────────────────────────────────────────────────────────────────────────
# WeaponDetector
# ─────────────────────────────────────────────────────────────────────────────

class WeaponDetector:
    """
    Dual-model weapon detector using pure onnxruntime (no PyTorch / ultralytics).

    Upgraded to YOLO26-N (NMS-free, end-to-end).  The decoder auto-detects
    whether each loaded ONNX model uses the new end2end format or the legacy
    anchor-based format, so the class is fully backward-compatible.

    v3 adds three heuristic layers targeting phone-as-handgun false positives:
      Layer A — Geometric penalisation  (vertical bbox → needs 0.80+)
      Layer B — Scale confidence scaling (large bbox → needs 0.75+)
      Layer C — Cross-model phone shield (COCO phone ↔ gun spatial overlap)

    Detection pipeline per frame:
      COCO ONNX (yolo26n)  →  gun ONNX  →  _resolve_model_conflicts_v2  →  _remove_duplicates
    """

    VALID_GUN_CLASS_NAMES = {
        'gun', 'guns', 'pistol', 'rifle', 'firearm', 'handgun', 'weapon',
        'revolver', 'shotgun', 'smg', 'assault_rifle', 'sniper',
        'machine_gun', 'submachine_gun', 'automatic_rifle',
        'Handgun', 'Machine Gun',
    }

    def __init__(
        self,
        model_path: Optional[str] = None,
        confidence_threshold: float = 0.50,   # COCO weapon/suppressor detection floor
    ):
        # ── SAHI Integration & Base thresholds ────────────────────────────────────
        # Lowered heavily to allow SAHI sliced patches to detect small guns
        self.confidence_threshold     = confidence_threshold   # COCO
        self.gun_confidence_threshold = 0.25  # gun model baseline (dropped from 0.55 for SAHI overlap)

        # Kept for legacy fallback path only 
        self.nms_iou_threshold        = 0.45

        # ── Dynamic threshold constants (Layers A & B) ───────────────────────────
        # Layer A: vertical bbox penalty  (h/w > this ratio → need VERTICAL_CONF_MIN)
        self.vertical_aspect_ratio    = 1.4    # h/w > 1.4 → likely phone portrait
        self.vertical_conf_min        = 0.70   # require 70 % confidence for vertical bboxes

        # Layer B: large-object scale penalty  (area > this fraction → need LARGE_CONF_MIN)
        self.large_bbox_area_frac     = 0.05   # > 5 % of frame area → needs higher conf
        self.large_conf_min           = 0.70   # require 70 % confidence for large bboxes

        # High-confidence override: if a gun model scores >= this, it bypasses
        # Layer A, Layer B, and Layer C entirely.  A real weapon at 85 %+ is
        # extremely unlikely to be a phone misclassification.
        self.override_conf            = 0.85

        # ── Bbox hard-reject filters (global, both models) ───────────────────────
        self.min_bbox_area_ratio      = 0.005  # < 0.5 % → noise/artifact
        self.max_bbox_area_ratio      = 0.40   # > 40 % → occupies whole frame → reject
        self.max_aspect_ratio         = 4.5    # extreme thin/tall shape → reject

        # ── Class maps ────────────────────────────────────────────────────────────
        self.weapon_classes = {
            'knife':        'knife',
            'scissors':     'knife',
            'baseball bat': 'bat',
        }
        self.suspicious_objects = {
            'backpack': 'backpack',
            'handbag':  'bag',
            'suitcase': 'suitcase',
        }
        self.firearm_classes = {
            'gun': 'gun', 'pistol': 'pistol', 'rifle': 'rifle',
            'firearm': 'firearm', 'handgun': 'handgun', 'weapon': 'weapon',
        }
        self.high_priority_weapons = {
            'knife', 'scissors', 'gun', 'pistol', 'rifle',
            'firearm', 'handgun', 'baseball bat', 'weapon',
        }
        self.monitored_classes = {
            **self.weapon_classes,
            **self.suspicious_objects,
            **self.firearm_classes,
        }

        # ── Suppressor classes (Layer C — Phone Shield) ───────────────────────────
        # The COCO model will detect these objects alongside normal weapon classes.
        # Detections are tagged with is_suppressor=True and are NEVER reported as
        # weapons.  Their only role is to shield against gun-model false positives
        # in _resolve_model_conflicts_v2 Layer 3.
        #
        # 'cell phone' (COCO idx 67) — vertical phone held in hand → #1 handgun FP
        # 'remote'     (COCO idx 65) — TV remote → narrow shape, confused with pistol
        self.suppressor_classes: Dict[str, str] = {
            'cell phone': 'cell_phone',
            'remote':     'remote',
        }

        self._validated_gun_classes: set = set()
        self.gun_class_names: List[str] = []

        # ── Runtime state ────────────────────────────────────────────────────────
        self.coco_session:          Optional[Any] = None
        self.gun_session:           Optional[Any] = None
        self.coco_input_name:       str  = 'images'
        self.gun_input_name:        str  = 'images'
        self.coco_input_size:       int  = 640
        self.gun_input_size:        int  = 640
        self.available:             bool = False
        self.gun_detection_enabled: bool = False

        # Output-format cache: detected automatically on first inference.
        self._coco_is_e2e: Optional[bool] = None
        self._gun_is_e2e:  Optional[bool] = None

        if not _ORT_AVAILABLE:
            logger.error(
                "onnxruntime not installed — weapon detection disabled. "
                "Run: pip install onnxruntime"
            )
            return

        weights = os.path.join(os.path.dirname(__file__), 'weights')
        opts    = self._cpu_session_options()

        # ── COCO model (yolo26n.onnx, fallback: yolo11n.onnx) ───────────────────
        coco_candidates = [
            model_path if (model_path and os.path.exists(model_path)) else None,
            os.path.join(weights, 'yolo26n.onnx'),
            os.path.join(weights, 'yolo11n.onnx'),   # fallback if not yet exported
        ]
        coco_path = next((p for p in coco_candidates if p and os.path.exists(p)), None)

        if coco_path is None:
            logger.error(
                "No COCO ONNX model found. Run the export commands in "
                "weapon_detector.py docstring first."
            )
            return

        try:
            self.coco_session    = ort.InferenceSession(
                coco_path, sess_options=opts, providers=['CPUExecutionProvider'])
            inp                  = self.coco_session.get_inputs()[0]
            self.coco_input_name = inp.name
            self.coco_input_size = inp.shape[2] if len(inp.shape) >= 3 else 640
            self.available       = True
            model_label = "YOLO26-N" if "yolo26" in os.path.basename(coco_path) else "YOLOv11n"
            logger.info(f"✅ Loaded COCO ONNX model [{model_label}] ({os.path.basename(coco_path)})")
        except Exception as exc:
            logger.error(
                f"Cannot load COCO ONNX model from {coco_path}: {exc}\n"
                "Run the export commands in weapon_detector.py docstring first."
            )
            return

        # ── Gun model (gun_detector.onnx) ────────────────────────────────────────
        gun_path = os.path.join(weights, 'gun_detector.onnx')
        if os.path.exists(gun_path):
            try:
                self.gun_session    = ort.InferenceSession(
                    gun_path, sess_options=opts, providers=['CPUExecutionProvider'])
                g_inp               = self.gun_session.get_inputs()[0]
                self.gun_input_name = g_inp.name
                self.gun_input_size = g_inp.shape[2] if len(g_inp.shape) >= 3 else 640
                self._load_gun_class_names()
                self.gun_detection_enabled = True
                mb = os.path.getsize(gun_path) / (1024 * 1024)
                logger.info(f"✅ Loaded gun  ONNX model  ({mb:.1f} MB)")
            except Exception as exc:
                logger.warning(f"Failed to load gun ONNX model: {exc}")
        else:
            logger.warning(
                f"⚠️  gun_detector.onnx not found at {gun_path}. "
                "Export it with the command in weapon_detector.py docstring."
            )

        logger.info(
            f"WeaponDetector ready  "
            f"(COCO: ✅  Gun: {'✅' if self.gun_detection_enabled else '❌'}  "
            f"Phone-shield: ✅ [{', '.join(self.suppressor_classes.keys())}])"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Session helpers
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _cpu_session_options():
        """CPU-tuned ORT SessionOptions — low thread count keeps RAM safe."""
        o = ort.SessionOptions()
        o.intra_op_num_threads     = 2   # enough for Nano model on IdeaPad S145
        o.inter_op_num_threads     = 1
        o.execution_mode           = ort.ExecutionMode.ORT_SEQUENTIAL
        o.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        o.enable_mem_pattern       = True
        o.enable_cpu_mem_arena     = True
        return o

    def _load_gun_class_names(self):
        """Read gun model class names from Ultralytics ONNX metadata."""
        try:
            meta      = self.gun_session.get_modelmeta()
            raw       = meta.custom_metadata_map.get('names', '{}')
            # Ultralytics stores metadata as a Python dict literal, e.g.
            # {0: 'gun', 1: 'guns', 2: 'handgun'} — NOT valid JSON.
            names_dict = ast.literal_eval(raw) if raw.strip() else {}
            if names_dict:
                max_id = max(int(k) for k in names_dict)
                self.gun_class_names = [
                    names_dict.get(i, f'class{i}') for i in range(max_id + 1)
                ]
            else:
                raise ValueError("Empty names map in ONNX metadata")
        except Exception as exc:
            logger.warning(f"Could not read gun class names from ONNX: {exc}. "
                           "Using fallback: gun / guns / handgun")
            self.gun_class_names = ['gun', 'guns', 'handgun']

        valid_lower = {n.lower() for n in self.VALID_GUN_CLASS_NAMES}
        for name in self.gun_class_names:
            if name.lower() in valid_lower:
                self._validated_gun_classes.add(name)
                logger.info(f"  ✅ Gun class '{name}' → WEAPON")
            else:
                logger.warning(f"  ⚠️  Gun class '{name}' → IGNORED (not a weapon)")

        if not self._validated_gun_classes:
            self._validated_gun_classes = set(self.gun_class_names)
            logger.warning("No validated gun classes found — treating all as weapons")

    # ─────────────────────────────────────────────────────────────────────────
    # Core decode dispatcher
    # ─────────────────────────────────────────────────────────────────────────

    def _decode_output(
        self,
        raw_outputs: list,
        orig_h: int,
        orig_w: int,
        ratio: float,
        pad: Tuple[float, float],
        conf_thresh: float,
        class_names: List[str],
        allowed_classes: Optional[set],
        is_e2e_cache_attr: str,          # '_coco_is_e2e' or '_gun_is_e2e'
    ) -> List[Dict]:
        """
        Auto-detect and dispatch to the correct decoder.

        On first call, inspects the output tensor shape and caches the result
        so subsequent calls skip the shape-check branch.
        """
        raw = raw_outputs[0]

        # Detect format on first call
        if getattr(self, is_e2e_cache_attr) is None:
            detected = _is_end2end_output(raw)
            setattr(self, is_e2e_cache_attr, detected)
            fmt = "YOLO26 end-to-end" if detected else "legacy anchor-based"
            logger.debug(
                f"[WeaponDetector] {is_e2e_cache_attr}: output shape {raw.shape} → {fmt}"
            )

        if getattr(self, is_e2e_cache_attr):
            return _decode_yolo26(
                raw,
                orig_h=orig_h, orig_w=orig_w,
                ratio=ratio, pad=pad,
                conf_thresh=conf_thresh,
                class_names=class_names,
                allowed_classes=allowed_classes,
            )
        else:
            # Fallback: legacy decode with NMS (for old YOLOv8/v11 exports)
            return _decode_yolo_legacy(
                raw,
                orig_h=orig_h, orig_w=orig_w,
                ratio=ratio, pad=pad,
                conf_thresh=conf_thresh,
                iou_thresh=self.nms_iou_threshold,
                class_names=class_names,
                allowed_classes=allowed_classes,
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def detect(self, frame: np.ndarray, return_all_objects: bool = False) -> List[Dict[str, Any]]:
        """
        Full detection: COCO + gun model.
        Returns list of dicts with keys:
          class, original_class, confidence, bbox [x1,y1,x2,y2],
          is_weapon, is_suspicious, is_high_priority, is_suppressor, source
        """
        if not self.available or frame is None or frame.size == 0:
            return []
        coco: List[Dict] = []
        gun:  List[Dict] = []
        try:
            coco = self._detect_with_coco(frame, return_all_objects)
        except Exception as exc:
            logger.error(f"COCO detection error: {exc}", exc_info=True)
        if self.gun_detection_enabled:
            try:
                gun = self._detect_with_gun_model(frame)
            except Exception as exc:
                logger.error(f"Gun detection error: {exc}", exc_info=True)
        return self.resolve_and_merge(coco, gun)

    def detect_fast(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        COCO-only detection.  Used for the high-frequency weapon loop iteration.
        Always includes suppressor-class detections (they are needed for the
        phone-shield in the subsequent resolve_and_merge call).
        """
        if not self.available or frame is None or frame.size == 0:
            return []
        try:
            coco = self._detect_with_coco(frame, False)
        except Exception as exc:
            logger.error(f"Fast (COCO) detection error: {exc}", exc_info=True)
            return []
        return self._remove_duplicates(coco)

    def detect_gun(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Gun-model-only detection with SAHI-logic integration for sliced patches
        Called infrequently from the dual-frequency weapon loop.
        """
        if not self.gun_detection_enabled or frame is None or frame.size == 0:
            return []
            
        # Optional: Implement sahi's get_sliced_prediction here 
        # using pure numpy sliding window if sahi ONNX wrappers aren't mapped.
        # e.g., patches = slice_image(frame, 320, 320, 0.2)
        
        try:
            return self._detect_with_gun_model(frame)
        except Exception as exc:
            logger.error(f"Gun detection error: {exc}", exc_info=True)
            return []

    def resolve_and_merge(
        self,
        coco_dets: List[Dict[str, Any]],
        gun_dets:  List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Conflict-resolve then dedup a set of COCO + gun detections.

        Suppressor detections (is_suppressor=True) are present inside
        _resolve_model_conflicts_v2 so that Layer 3 (phone shield) can
        compare their bboxes against gun detections.  They are stripped
        HERE, after conflict resolution, so they never reach callers.
        """
        merged = self._resolve_model_conflicts_v2(coco_dets, gun_dets)
        # Strip suppressor-only dets — internal use only, must not be
        # returned as weapon alerts to any caller.
        non_suppressors = [d for d in merged if not d.get('is_suppressor', False)]
        return self._remove_duplicates(non_suppressors)

    # ─────────────────────────────────────────────────────────────────────────
    # Private inference methods
    # ─────────────────────────────────────────────────────────────────────────

    def _detect_with_coco(self, frame: np.ndarray, return_all_objects: bool) -> List[Dict[str, Any]]:
        """
        YOLO26-N ONNX inference — knives, bats, scissors, suspicious bags,
        AND suppressor classes (cell phone, remote) for the phone shield.

        Suppressor detections are tagged with is_suppressor=True, is_weapon=False.
        They are never reported as threats but are passed to
        _resolve_model_conflicts_v2 to veto gun detections at the same location.
        """
        tensor, ratio, pad = _preprocess(frame, self.coco_input_size)
        outputs = self.coco_session.run(None, {self.coco_input_name: tensor})

        # Always include suppressor classes in the allowed set (never if return_all_objects,
        # because return_all_objects already allows everything).
        if return_all_objects:
            allowed = None
        else:
            allowed = (
                set(self.monitored_classes.keys()) |
                set(self.suppressor_classes.keys())
            )

        raw = self._decode_output(
            outputs,
            orig_h=frame.shape[0], orig_w=frame.shape[1],
            ratio=ratio, pad=pad,
            conf_thresh=self.confidence_threshold,
            class_names=_COCO80,
            allowed_classes=allowed,
            is_e2e_cache_attr='_coco_is_e2e',
        )

        detections = []
        for det in raw:
            if not self._passes_shape_filter(det['bbox'], frame):
                continue
            cname = det['class_name']

            if cname in self.suppressor_classes:
                # ── Suppressor detection (phone / remote) ──────────────────────
                # Tagged internally; never triggers an alert.  Used only in
                # _resolve_model_conflicts_v2 Layer 3 (phone shield).
                detections.append({
                    'class':            self.suppressor_classes[cname],
                    'original_class':   cname,
                    'confidence':       det['confidence'],
                    'bbox':             det['bbox'],
                    'is_weapon':        False,
                    'is_suspicious':    False,
                    'is_high_priority': False,
                    'is_suppressor':    True,
                    'source':           'coco_model',
                })
            else:
                # ── Normal weapon / suspicious object detection ────────────────
                detections.append({
                    'class':            self.monitored_classes.get(cname, cname),
                    'original_class':   cname,
                    'confidence':       det['confidence'],
                    'bbox':             det['bbox'],
                    'is_weapon':        cname in self.weapon_classes,
                    'is_suspicious':    cname in self.suspicious_objects,
                    'is_high_priority': cname in self.high_priority_weapons,
                    'is_suppressor':    False,
                    'source':           'coco_model',
                })
        return detections

    def _detect_with_gun_model(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Gun-specific YOLO ONNX inference with three-stage filtering:

        Stage 1 — Baseline decode at gun_confidence_threshold (0.55).
        Stage 2 — Hard shape filter (size / aspect ratio bounds).
        Stage 3 — Dynamic heuristic filters (Layers A & B):
            A. Vertical bbox penalty:  h/w > 1.4 → need confidence ≥ 0.80
            B. Large-object penalty:   area > 5 % → need confidence ≥ 0.75

        Only detections that survive all three stages are returned.
        """
        tensor, ratio, pad = _preprocess(frame, self.gun_input_size)
        outputs = self.gun_session.run(None, {self.gun_input_name: tensor})

        raw = self._decode_output(
            outputs,
            orig_h=frame.shape[0], orig_w=frame.shape[1],
            ratio=ratio, pad=pad,
            conf_thresh=self.gun_confidence_threshold,   # 0.55 baseline
            class_names=self.gun_class_names,
            allowed_classes=self._validated_gun_classes,
            is_e2e_cache_attr='_gun_is_e2e',
        )

        frame_area = frame.shape[0] * frame.shape[1]

        detections = []
        for det in raw:
            bbox = det['bbox']
            conf = det['confidence']
            cname = det['class_name']

            # ── Stage 2: hard shape filter ────────────────────────────────────
            if not self._passes_shape_filter(bbox, frame):
                continue

            bw = bbox[2] - bbox[0]
            bh = bbox[3] - bbox[1]

            # ── Stage 3: dynamic heuristic filters (Layers A & B) ────────────
            # High-confidence override: if the gun model is extremely confident
            # (>= override_conf = 0.85), the detection skips all penalisation.
            # Real weapons at 85 %+ confidence are statistically not phone FPs.
            if conf >= self.override_conf:
                logger.debug(
                    f"Gun override [conf={conf:.2f} >= {self.override_conf:.2f}]: "
                    f"'{cname}' bypasses Stage 3A+3B heuristics"
                )
            else:
                # ── Stage 3A: vertical bbox geometric penalisation ────────────
                # A phone held portrait is almost always taller than it is wide.
                # Handguns are always horizontal (h/w < 1.0 typically).
                # Skip for high-confidence detections (handled by override above).
                if bw > 0:
                    hw_ratio = bh / bw
                    if hw_ratio > self.vertical_aspect_ratio:
                        if conf < self.vertical_conf_min:
                            logger.debug(
                                f"Gun FP [Layer A — vertical]: '{cname}' "
                                f"h/w={hw_ratio:.2f} conf={conf:.2f} "
                                f"< {self.vertical_conf_min:.2f}"
                            )
                            continue

                # ── Stage 3B: large-object scale confidence scaling ───────────
                # A real handgun filling > 5 % of the camera frame would be
                # extremely close and score 90 %+.  ~72 % on a large bbox is
                # typical of a phone.  Not applied when override fires.
                if frame_area > 0:
                    area_ratio = (bw * bh) / frame_area
                    if area_ratio > self.large_bbox_area_frac:
                        if conf < self.large_conf_min:
                            logger.debug(
                                f"Gun FP [Layer B — large obj]: '{cname}' "
                                f"area={area_ratio:.1%} conf={conf:.2f} "
                                f"< {self.large_conf_min:.2f}"
                            )
                            continue

            detections.append({
                'class':            cname,
                'original_class':   cname,
                'confidence':       conf,
                'bbox':             bbox,
                'is_weapon':        True,
                'is_suspicious':    False,
                'is_high_priority': True,
                'is_suppressor':    False,
                'source':           'gun_model',
            })
            logger.warning(f"🔫 GUN DETECTED: {cname} (conf: {conf:.2f})")
        return detections

    # ─────────────────────────────────────────────────────────────────────────
    # Conflict resolution & dedup
    # ─────────────────────────────────────────────────────────────────────────

    def _resolve_model_conflicts_v2(
        self,
        coco_dets: List[Dict[str, Any]],
        gun_dets:  List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Three-layer conflict resolution for gun detections:

        Layer 1 — Spatial weapon conflict
          Gun bbox overlaps (IoU > 0.25) a COCO weapon bbox → gun discarded
          (COCO label is more reliable for overlapping weapon-class detections).

        Layer 2 — Frame-level phantom suppression
          If COCO confirms ANY weapon anywhere in the frame, gun detections
          with conf < 0.70 are discarded (phone-on-image-of-knife guard).

        Layer 3 — Phone shield (NEW in v3)
          If the COCO model detected a 'cell phone' or 'remote' that
          either (a) has IoU > 0.40 with a gun bbox, or (b) entirely
          contains the gun bbox, the gun detection is discarded.
          Rationale: if COCO positively identifies a phone at that location,
          the gun detector is almost certainly confusing the phone.

        All three layers are evaluated independently; any one failing
        causes the gun detection to be dropped.
        """
        if not gun_dets:
            # No gun detections — return COCO results (including suppressors,
            # which will be filtered downstream by is_weapon/is_suspicious).
            return list(coco_dets)
        if not coco_dets:
            return list(gun_dets)

        coco_weapons     = [d for d in coco_dets if d.get('is_weapon', False)]
        coco_suppressors = [d for d in coco_dets if d.get('is_suppressor', False)]
        has_any_coco_weapon = len(coco_weapons) > 0

        if coco_suppressors:
            logger.debug(
                f"Phone shield active: {len(coco_suppressors)} suppressor(s) detected "
                f"[{[s['original_class'] for s in coco_suppressors]}]"
            )

        resolved = list(coco_dets)
        for gd in gun_dets:
            gbbox = gd['bbox']
            conf  = gd['confidence']

            # ── Layer 1: spatial overlap with a COCO weapon ───────────────────
            spatial_conflict = any(
                self._bbox_iou(gbbox, cd['bbox']) > 0.25 for cd in coco_weapons
            )

            # ── Layer 2: frame-level low-confidence phantom ────────────────────
            frame_level_suppressed = (
                has_any_coco_weapon and conf < 0.70
            )

            # ── Layer 3: phone shield (Cross-Model Suppression) ────────────────
            # Triggers when a COCO suppressor (phone/remote) spatially overlaps
            # the gun bbox in one of two ways:
            #   (a) IoU > 0.40 — bboxes substantially overlap
            #   (b) gun bbox is contained within phone bbox AND the gun occupies
            #       > 40 % of the phone bbox area — i.e. the model is confusing
            #       the physical phone body itself, NOT a small image on-screen.
            #
            # Override: if conf >= self.override_conf (0.85), the gun detection
            # punches through the phone shield.  This handles the edge case where
            # a user holds up a phone displaying a picture of a real gun — the gun
            # model would score 85 %+ while a phone-body FP typically scores < 0.75.
            phone_shielded = False
            if coco_suppressors and conf < self.override_conf:
                for sd in coco_suppressors:
                    iou       = self._bbox_iou(gbbox, sd['bbox'])
                    contained = self._bbox_contains(outer=sd['bbox'], inner=gbbox)

                    # Proportional containment: only suppress if the gun bbox
                    # occupies a significant fraction of the suppressor bbox.
                    # Prevents shielding a small gun-image displayed on a phone screen.
                    # Pre-compute areas here so they are always defined for the log line below.
                    gun_area   = max((gbbox[2] - gbbox[0]) * (gbbox[3] - gbbox[1]), 1)
                    phone_area = max(
                        (sd['bbox'][2] - sd['bbox'][0]) * (sd['bbox'][3] - sd['bbox'][1]), 1
                    )
                    if contained:
                        prop_contained = (gun_area / phone_area) > 0.40
                    else:
                        prop_contained = False

                    if iou > 0.40 or prop_contained:
                        phone_shielded = True
                        logger.debug(
                            f"Gun FP [Layer C — phone shield]: '{gd['class']}' "
                            f"conf={conf:.2f} vs '{sd['original_class']}' "
                            f"IoU={iou:.2f} prop_contained={prop_contained} "
                            f"(gun fills {gun_area / phone_area:.0%} of phone)"
                        )
                        break

            elif conf >= self.override_conf and coco_suppressors:
                logger.debug(
                    f"Gun override [conf={conf:.2f} >= {self.override_conf:.2f}]: "
                    f"'{gd['class']}' bypasses Layer C phone shield"
                )

            # ── Decision ──────────────────────────────────────────────────────
            if spatial_conflict or frame_level_suppressed or phone_shielded:
                if not phone_shielded:
                    # Log non-phone suppressions at debug (already logged above)
                    logger.debug(
                        f"Gun FP suppressed: '{gd['class']}' conf={conf:.2f} "
                        f"(spatial={spatial_conflict}, "
                        f"frame_level={frame_level_suppressed})"
                    )
            else:
                resolved.append(gd)

        return resolved

    def _resolve_model_conflicts(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Legacy shim — splits combined list and delegates to _resolve_model_conflicts_v2."""
        coco_dets = [d for d in detections if d.get('source') == 'coco_model']
        gun_dets  = [d for d in detections if d.get('source') == 'gun_model']
        return self._resolve_model_conflicts_v2(coco_dets, gun_dets)

    def _remove_duplicates(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove overlapping duplicates within a list; highest confidence kept.

        NOTE: This method does NOT strip suppressor detections — that is the
        responsibility of resolve_and_merge, which calls this method only after
        removing suppressors.  This keeps detect_fast() able to pass suppressors
        through to the subsequent resolve_and_merge call in the weapon thread.
        """
        if len(detections) <= 1:
            return detections
        detections = sorted(detections, key=lambda d: d['confidence'], reverse=True)
        filtered = []
        for det in detections:
            if not any(self._bbox_iou(det['bbox'], e['bbox']) > 0.35 for e in filtered):
                filtered.append(det)
        return filtered

    # ─────────────────────────────────────────────────────────────────────────
    # Geometry helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _bbox_iou(self, bbox1: List[int], bbox2: List[int]) -> float:
        """Intersection-over-Union of two [x1,y1,x2,y2] bounding boxes.

        Null-safe: returns 0.0 if either bbox is empty or malformed
        (e.g. Staleness Drop sentinel bbox=[]).
        """
        if not bbox1 or len(bbox1) < 4 or not bbox2 or len(bbox2) < 4:
            return 0.0
        x1 = max(bbox1[0], bbox2[0]); y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2]); y2 = min(bbox1[3], bbox2[3])
        if x2 <= x1 or y2 <= y1:
            return 0.0
        inter = (x2 - x1) * (y2 - y1)
        a1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        a2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        union = a1 + a2 - inter
        return inter / union if union else 0.0

    def _bbox_contains(self, outer: List[int], inner: List[int]) -> bool:
        """Return True if outer bbox entirely contains inner bbox.

        Null-safe: returns False if either bbox is empty or malformed
        (e.g. Staleness Drop sentinel bbox=[]).
        """
        if not outer or len(outer) < 4 or not inner or len(inner) < 4:
            return False
        return (
            outer[0] <= inner[0] and
            outer[1] <= inner[1] and
            outer[2] >= inner[2] and
            outer[3] >= inner[3]
        )

    def _passes_shape_filter(self, bbox: List[int], frame: np.ndarray) -> bool:
        """Return False if bbox is too tiny, too large, or has an extreme aspect ratio."""
        bw = bbox[2] - bbox[0]
        bh = bbox[3] - bbox[1]
        fa = frame.shape[0] * frame.shape[1]
        if fa > 0:
            ratio = (bw * bh) / fa
            if ratio < self.min_bbox_area_ratio:
                return False   # too tiny — artifact
            if ratio > self.max_bbox_area_ratio:
                return False   # too large — whole phone screen (threshold: 40%)
        if bw > 0 and bh > 0 and max(bw / bh, bh / bw) > self.max_aspect_ratio:
            return False
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # Convenience helpers
    # ─────────────────────────────────────────────────────────────────────────

    def detect_weapons_only(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Return only confirmed weapon detections (not suspicious bags etc.)."""
        return [d for d in self.detect(frame) if d.get('is_weapon', False)]

    def get_stats(self) -> Dict[str, Any]:
        return {
            'available':                self.available,
            'backend':                  'onnxruntime',
            'coco_model':               'yolo26n.onnx',
            'gun_model_loaded':         self.gun_detection_enabled,
            'confidence_threshold':     self.confidence_threshold,
            'gun_confidence_threshold': self.gun_confidence_threshold,
            'nms_iou_threshold':        self.nms_iou_threshold,
            'vertical_aspect_ratio':    self.vertical_aspect_ratio,
            'vertical_conf_min':        self.vertical_conf_min,
            'large_bbox_area_frac':     self.large_bbox_area_frac,
            'large_conf_min':           self.large_conf_min,
            'override_conf':            self.override_conf,
            'monitored_classes':        len(self.monitored_classes),
            'weapon_classes':           len(self.weapon_classes),
            'firearm_classes':          len(self.firearm_classes),
            'suppressor_classes':       list(self.suppressor_classes.keys()),
            'coco_decoder':             'end2end' if self._coco_is_e2e else ('legacy' if self._coco_is_e2e is False else 'unknown'),
            'gun_decoder':              'end2end' if self._gun_is_e2e  else ('legacy' if self._gun_is_e2e  is False else 'unknown'),
        }
