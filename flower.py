"""
Flower Gesture Project  ─  Bouquet Edition
==========================================
MediaPipe 0.10.x+ (Tasks API) · OpenCV · NumPy

Controls:
  - Left hand  → spread thumb & index to GROW the bouquet stems + leaves.
  - Right hand → spread thumb & index to BLOOM colourful flat flowers.
  - Press 'q'  → quit cleanly.

Setup (one-time):
  pip install opencv-python mediapipe numpy
  curl -o hand_landmarker.task https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
"""

import cv2
import mediapipe as mp
import numpy as np
import math
import threading
import os

from mediapipe.tasks.python.vision import (
    HandLandmarker, HandLandmarkerOptions, HandLandmarkerResult,
    RunningMode, HandLandmarksConnections, drawing_utils,
)
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.components.containers.landmark import NormalizedLandmark

# ─────────────────────────────────────────────────────────────────────────────
# 1. Model
# ─────────────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(SCRIPT_DIR, "hand_landmarker.task")
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"\nModel not found: {MODEL_PATH}\n"
        "Run: curl -o hand_landmarker.task https://storage.googleapis.com/"
        "mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task\n"
    )

# ─────────────────────────────────────────────────────────────────────────────
# 2. Thread-safe result store
# ─────────────────────────────────────────────────────────────────────────────
_lock          = threading.Lock()
_latest_result = None

def _result_callback(result: HandLandmarkerResult, _img, _ts):
    global _latest_result
    with _lock:
        _latest_result = result

landmarker = HandLandmarker.create_from_options(HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=RunningMode.LIVE_STREAM,
    num_hands=2,
    min_hand_detection_confidence=0.6,
    min_hand_presence_confidence=0.5,
    min_tracking_confidence=0.5,
    result_callback=_result_callback,
))

# ─────────────────────────────────────────────────────────────────────────────
# 3. Flower palette  (BGR) — matching the reference image
#    Each entry: (petal_main, petal_dark, centre_main, centre_ring)
# ─────────────────────────────────────────────────────────────────────────────
FLOWER_STYLES = [
    # petal colour,       petal shadow,     centre fill,      centre ring
    ((60,  130, 255),  (30,  90, 210),   (0,  180, 255),  (255,255,255)),  # orange
    ((180,  80, 230),  (140,  40, 190),  (0,  190, 255),  (255,255,255)),  # magenta/pink
    ((200, 160, 240),  (160, 110, 200),  (0,  200, 255),  (255,255,255)),  # soft lavender
    ((180, 210, 100),  (130, 170,  60),  (0,  220, 255),  (255,255,255)),  # teal/mint
    ((100, 180, 255),  ( 60, 130, 210),  (180, 80, 230),  (255,255,255)),  # peach/salmon
    ((80,  200, 255),  ( 40, 150, 200),  (0,  190, 255),  (255,255,255)),  # yellow
    ((160,  60, 220),  (110,  20, 170),  (0,  200, 255),  (255,255,255)),  # deep pink
]

# Stem/leaf greens
STEM_COL  = (40, 140, 60)
LEAF_COL  = (50, 170, 70)
LEAF_DARK = (30, 110, 45)

# ─────────────────────────────────────────────────────────────────────────────
# 4. Bouquet layout — each flower stem in the bouquet
#    (x_offset_frac, lean_deg, height_frac, style_idx, leaf_side)
#    x_offset_frac: fraction of frame width, centred on 0
#    lean_deg: how much the stem leans left(-) or right(+)
#    height_frac: stem height as fraction of frame height
#    style_idx: index into FLOWER_STYLES
#    leaf_side: +1 right, -1 left, 0 both
# ─────────────────────────────────────────────────────────────────────────────
BOUQUET = [
    (-0.22,  -8,  0.62,  0,  -1),   # orange, left-leaning tall
    (-0.07,  -3,  0.70,  1,  +1),   # magenta, slightly left, tallest
    ( 0.08,  +4,  0.65,  2,  -1),   # lavender, slightly right
    ( 0.20,  +9,  0.58,  3,   0),   # teal, right-leaning
    (-0.15,  -5,  0.48,  4,  +1),   # peach, mid-left shorter
    ( 0.00,  +1,  0.55,  5,  -1),   # yellow, centre
    ( 0.13,  +6,  0.50,  6,  +1),   # deep pink, mid-right
]

# ─────────────────────────────────────────────────────────────────────────────
# 5. Drawing primitives
# ─────────────────────────────────────────────────────────────────────────────

def draw_hud(frame, label, value, pos, scale=0.7):
    text = f"{label}: {value:.2f}"
    x, y = pos
    f = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(frame, text, (x+1,y+1), f, scale, (0,0,0),      2, cv2.LINE_AA)
    cv2.putText(frame, text, (x,  y  ), f, scale, (255,255,255), 2, cv2.LINE_AA)


def draw_tapered_stem(frame, x1, y1, x2, y2, thick1, thick2, color):
    """Draw a thick-to-thin stem as a series of filled circles."""
    dist  = math.hypot(x2-x1, y2-y1)
    steps = max(2, int(dist / 3))
    for i in range(steps+1):
        t  = i / steps
        x  = int(x1 + t*(x2-x1))
        y  = int(y1 + t*(y2-y1))
        th = max(1, int(thick1 + t*(thick2-thick1)))
        cv2.circle(frame, (x, y), th//2, color, -1)


def draw_leaf(frame, stem_x, stem_y, side, size, angle_offset=0):
    """
    Draw a rounded oval leaf on one side of the stem.
    side: +1 = right, -1 = left
    """
    if size < 4:
        return
    # Leaf is an ellipse rotated outward from stem
    angle   = 35 * side + angle_offset          # degrees
    rad     = math.radians(angle - 90)
    lx      = stem_x + int(size * 0.6 * math.cos(rad))
    ly      = stem_y + int(size * 0.6 * math.sin(rad))
    axes    = (max(2, size), max(1, size//2))
    rot     = int(angle - 90 + 90)              # cv2 angle

    cv2.ellipse(frame, (lx, ly), axes, rot, 0, 360, LEAF_COL,  -1)
    cv2.ellipse(frame, (lx, ly), axes, rot, 0, 360, LEAF_DARK,  1)
    # midrib line
    tip_x = lx + int(size * 0.8 * math.cos(rad))
    tip_y = ly + int(size * 0.8 * math.sin(rad))
    cv2.line(frame, (lx, ly), (tip_x, tip_y), LEAF_DARK, 1, cv2.LINE_AA)


def draw_oval_petal(frame, cx, cy, petal_r, angle_rad, color_main, color_dark):
    """
    Draw one soft oval petal pointing outward from (cx,cy) at angle_rad.
    The petal is an ellipse whose long axis points away from centre.
    """
    dist  = int(petal_r * 0.9)
    px    = cx + int(dist * math.cos(angle_rad))
    py    = cy + int(dist * math.sin(angle_rad))

    # axes: long axis along the radial direction, short axis perpendicular
    a_long  = max(3, petal_r)
    a_short = max(2, int(petal_r * 0.60))
    rot_deg = int(math.degrees(angle_rad))

    cv2.ellipse(frame, (px, py), (a_long, a_short), rot_deg, 0, 360, color_main, -1)
    cv2.ellipse(frame, (px, py), (a_long, a_short), rot_deg, 0, 360, color_dark,  1)


def draw_bouquet_flower(frame, tx, ty, bloom_v, style_idx):
    """
    Draw a flat, round bouquet-style flower at (tx, ty).
    Matches the reference: oval petals, white dot ring on centre.
    """
    if bloom_v <= 0.02:
        return

    s = FLOWER_STYLES[style_idx % len(FLOWER_STYLES)]
    petal_main, petal_dark, centre_fill, centre_ring = s

    # Petal size scales with bloom
    max_petal_r = 42
    petal_r     = max(3, int(max_petal_r * bloom_v))

    num_petals  = 8

    # ── Back-layer petals (slightly offset for depth) ─────────────────────────
    for i in range(num_petals):
        angle = (2*math.pi / num_petals) * i + math.pi/num_petals   # offset layer
        # slightly smaller & darker for back layer
        back_r = max(2, int(petal_r * 0.80))
        draw_oval_petal(frame, tx, ty, back_r, angle,
                        tuple(max(0,c-30) for c in petal_main),
                        tuple(max(0,c-50) for c in petal_dark))

    # ── Front-layer petals ────────────────────────────────────────────────────
    for i in range(num_petals):
        angle = (2*math.pi / num_petals) * i
        draw_oval_petal(frame, tx, ty, petal_r, angle, petal_main, petal_dark)

    # ── Centre disc ───────────────────────────────────────────────────────────
    centre_r = max(4, int(petal_r * 0.45))
    cv2.circle(frame, (tx, ty), centre_r,           centre_fill, -1)
    cv2.circle(frame, (tx, ty), centre_r,           petal_dark,   1)

    # ── White dot ring (signature bouquet detail) ─────────────────────────────
    if bloom_v > 0.35 and centre_r > 5:
        dot_r    = max(1, centre_r // 5)
        dot_dist = centre_r - dot_r - 1
        num_dots = 10
        for i in range(num_dots):
            a  = (2*math.pi / num_dots) * i
            dx = tx + int(dot_dist * math.cos(a))
            dy = ty + int(dot_dist * math.sin(a))
            cv2.circle(frame, (dx, dy), dot_r, (255,255,255), -1)

    # ── Inner highlight spot ──────────────────────────────────────────────────
    if centre_r > 4:
        cv2.circle(frame, (tx - centre_r//4, ty - centre_r//4),
                   max(1, centre_r//4), (255,255,255), -1)


def draw_bud(frame, tx, ty, style_idx):
    """Draw a small closed bud (used at the very beginning of bloom)."""
    s = FLOWER_STYLES[style_idx % len(FLOWER_STYLES)]
    petal_main = s[0]
    # green bud base
    cv2.ellipse(frame, (tx, ty), (6, 10), 0, 0, 360, LEAF_COL, -1)
    # petal tip peeking out
    cv2.ellipse(frame, (tx, ty-6), (5, 7), 0, 0, 360, petal_main, -1)
    cv2.ellipse(frame, (tx, ty-6), (5, 7), 0, 0, 360, s[1], 1)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Full bouquet renderer
# ─────────────────────────────────────────────────────────────────────────────

def draw_bouquet(frame, cx, base_y, grow_v, bloom_v):
    """
    Draw all bouquet stems, leaves, and flowers.
    cx      : horizontal centre of bouquet
    base_y  : where stems root (bottom of frame)
    grow_v  : 0→1, stem length
    bloom_v : 0→1, flower size
    """
    if grow_v <= 0.01:
        return

    h, w = frame.shape[:2]

    # ── Big base leaves (always visible once grown a little) ──────────────────
    if grow_v > 0.15:
        leaf_v = min(1.0, (grow_v - 0.15) / 0.3)
        big_sz = int(55 * leaf_v)
        draw_leaf(frame, cx - 40, base_y - 30, -1, big_sz, angle_offset=-10)
        draw_leaf(frame, cx + 40, base_y - 30, +1, big_sz, angle_offset=+10)
        draw_leaf(frame, cx,      base_y - 10,  0, int(big_sz * 0.7))

    # ── Draw each stem + leaf + flower ───────────────────────────────────────
    for (x_frac, lean_deg, h_frac, style_idx, leaf_side) in BOUQUET:
        sx = cx + int(x_frac * w)              # stem base x

        # How tall this stem grows (staggered: shorter stems reveal earlier)
        # Stems start appearing at different grow_v thresholds
        stem_threshold = 0.05 + 0.10 * (h_frac - 0.45) / 0.30
        if grow_v < stem_threshold:
            continue

        local_grow = min(1.0, (grow_v - stem_threshold) / (1.0 - stem_threshold + 0.01))

        max_stem_h   = int(h * h_frac)
        stem_h       = int(max_stem_h * local_grow)
        if stem_h < 5:
            continue

        lean_rad     = math.radians(lean_deg)
        tip_x        = sx + int(stem_h * math.sin(lean_rad))
        tip_y        = base_y - stem_h

        # ── Stem ─────────────────────────────────────────────────────────────
        # Draw as a smooth curve using intermediate points
        mid_x = sx + int(stem_h * 0.3 * math.sin(lean_rad))
        mid_y = base_y - int(stem_h * 0.55)

        # lower half
        draw_tapered_stem(frame, sx, base_y, mid_x, mid_y, 7, 4, STEM_COL)
        # upper half
        draw_tapered_stem(frame, mid_x, mid_y, tip_x, tip_y, 4, 2, STEM_COL)

        # ── Leaves ───────────────────────────────────────────────────────────
        if local_grow > 0.3:
            leaf_sz = int(28 * min(1.0, (local_grow - 0.3) / 0.4))
            # lower leaf
            lx_low = sx + int(stem_h * 0.25 * math.sin(lean_rad))
            ly_low = base_y - int(stem_h * 0.28)
            if leaf_side == 0:
                draw_leaf(frame, lx_low, ly_low, -1, leaf_sz)
                draw_leaf(frame, lx_low, ly_low, +1, leaf_sz)
            else:
                draw_leaf(frame, lx_low, ly_low, leaf_side, leaf_sz)

        if local_grow > 0.55:
            leaf_sz2 = int(22 * min(1.0, (local_grow - 0.55) / 0.35))
            # upper leaf
            lx_up = sx + int(stem_h * 0.60 * math.sin(lean_rad))
            ly_up = base_y - int(stem_h * 0.62)
            draw_leaf(frame, lx_up, ly_up, -leaf_side if leaf_side != 0 else +1, leaf_sz2)

        # ── Flower or bud ─────────────────────────────────────────────────────
        if bloom_v < 0.08 and local_grow > 0.85:
            draw_bud(frame, tip_x, tip_y, style_idx)
        elif bloom_v >= 0.08:
            draw_bouquet_flower(frame, tip_x, tip_y, bloom_v, style_idx)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Utilities
# ─────────────────────────────────────────────────────────────────────────────

def pixel_xy(lm: NormalizedLandmark, w, h):
    return int(lm.x * w), int(lm.y * h)

def pixel_dist(p1, p2):
    return math.hypot(p2[0]-p1[0], p2[1]-p1[1])

def norm_pinch(dist, diag, lo=0.03, hi=0.25):
    return float(np.clip((dist/diag - lo) / (hi - lo), 0.0, 1.0))


# ─────────────────────────────────────────────────────────────────────────────
# 8. Main loop
# ─────────────────────────────────────────────────────────────────────────────

def main():
    global _latest_result

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Cannot open webcam.")

    grow_v  = 0.0
    bloom_v = 0.0
    ts_ms   = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, w  = frame.shape[:2]
        diag  = math.hypot(w, h)

        # Bouquet always centred, rooted at bottom
        cx     = w // 2
        base_y = h - 15

        # ── Send to MediaPipe ─────────────────────────────────────────────────
        ts_ms += 33
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB,
                          data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        landmarker.detect_async(mp_img, ts_ms)

        # ── Grab result ───────────────────────────────────────────────────────
        with _lock:
            result = _latest_result

        if result and result.hand_landmarks:
            ds_lm   = drawing_utils.DrawingSpec(color=(80,80,255), thickness=2, circle_radius=3)
            ds_conn = drawing_utils.DrawingSpec(color=(180,180,180), thickness=1)
            for hl in result.hand_landmarks:
                drawing_utils.draw_landmarks(
                    frame, hl, HandLandmarksConnections.HAND_CONNECTIONS, ds_lm, ds_conn)

            for hand_lm, handed in zip(result.hand_landmarks, result.handedness):
                label = handed[0].category_name
                thumb = pixel_xy(hand_lm[4], w, h)
                idx   = pixel_xy(hand_lm[8], w, h)
                dist  = pixel_dist(thumb, idx)

                if label == "Left":
                    grow_v = norm_pinch(dist, diag)
                    draw_hud(frame, "Grow",  grow_v,  (10, 40))
                elif label == "Right":
                    bloom_v = norm_pinch(dist, diag)
                    draw_hud(frame, "Bloom", bloom_v, (10, 75))

        # ── Draw bouquet ──────────────────────────────────────────────────────
        draw_bouquet(frame, cx, base_y, grow_v, bloom_v)

        # ── Instructions ──────────────────────────────────────────────────────
        cv2.putText(frame,
                    "Left: grow stems  |  Right: bloom flowers  |  q = quit",
                    (10, h-12), cv2.FONT_HERSHEY_SIMPLEX,
                    0.45, (200,200,200), 1, cv2.LINE_AA)

        cv2.imshow("Flower Gesture Project", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    landmarker.close()


if __name__ == "__main__":
    main()