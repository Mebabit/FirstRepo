import cv2
import numpy as np
import math
import time
import platform
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from pynput.keyboard import Key, Controller

# Configuration
CAMERA_INDEX       = 0  # Changed to 0 as default, change to 1 if using external webcam
DEAD_ZONE_DEG      = 15   # Angle must exceed this to start turning (neutral band ±15°)
RELEASE_ZONE_DEG   = 10   # Hysteresis: key is released only once angle returns inside this
SOFT_ZONE_DEG      = 30   # Full-strength turn reached at this angle
FLIP_CAMERA        = True
SHOW_ANGLE         = True
MIN_DETECTION_CONF = 0.7
MIN_TRACKING_CONF  = 0.5
GRACE_FRAMES       = 8
OPEN_FINGER_THRESH = 3
MODEL_PATH         = "hand_landmarker.task"

# Colors (BGR Format)
CLR_WHEEL   = (80, 200, 255)
CLR_LEFT    = (60, 120, 255)
CLR_RIGHT   = (50, 220, 140)
CLR_NEUTRAL = (200, 200, 200)
CLR_TEXT    = (255, 255, 255)
CLR_ACCENT  = (0, 180, 255)
CLR_HAND_L  = (255, 130, 60)
CLR_HAND_R  = (60, 230, 130)
CLR_ACCEL   = (50, 220, 100)
CLR_BRAKE   = (0, 60, 255)

keyboard = Controller()

# Hand Landmark Connections for Manual Drawing in Tasks API
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)
]


def is_open_hand(hand_landmarks):
    FINGER_TIPS = [8, 12, 16, 20]
    FINGER_PIPS = [6, 10, 14, 18]
    extended = sum(
        1 for tip, pip in zip(FINGER_TIPS, FINGER_PIPS)
        if hand_landmarks[tip].y < hand_landmarks[pip].y
    )
    return extended >= OPEN_FINGER_THRESH


class SteeringController:
    def __init__(self):
        self.keys_held     = {Key.left: False, Key.right: False, Key.up: False, Key.down: False}
        self.angle_history = []
        self.HISTORY_LEN   = 6   # Smooth over 6 frames — eliminates jitter without noticeable lag

    def _press(self, key):
        if not self.keys_held[key]:
            keyboard.press(key)
            self.keys_held[key] = True

    def _release(self, key):
        if self.keys_held[key]:
            keyboard.release(key)
            self.keys_held[key] = False

    def release_all(self):
        for key in list(self.keys_held.keys()):
            try:
                keyboard.release(key)
            except Exception:
                pass
            self.keys_held[key] = False
        self.angle_history.clear()

    def smooth_angle(self, raw_angle):
        self.angle_history.append(raw_angle)
        if len(self.angle_history) > self.HISTORY_LEN:
            self.angle_history.pop(0)
        return float(np.mean(self.angle_history))

    def update_steer(self, left_wrist, right_wrist):
        dx = right_wrist[0] - left_wrist[0]
        dy = right_wrist[1] - left_wrist[1]

        raw_angle_rad = math.atan2(dy, dx)
        raw_angle_deg = math.degrees(raw_angle_rad)
        angle = self.smooth_angle(raw_angle_deg)

        # --- 3-zone logic with hysteresis ---
        # Positive angle  → right hand is lower → steer LEFT  (SWAPPED from original)
        # Negative angle  → left hand is lower  → steer RIGHT (SWAPPED from original)
        # Within ±DEAD_ZONE_DEG               → STRAIGHT (neutral band)

        if self.keys_held[Key.left]:
            # Already steering left: stay left until angle drops back inside release zone
            if angle > RELEASE_ZONE_DEG:
                direction = "LEFT"
            else:
                direction = "STRAIGHT"
        elif self.keys_held[Key.right]:
            # Already steering right: stay right until angle rises back inside release zone
            if angle < -RELEASE_ZONE_DEG:
                direction = "RIGHT"
            else:
                direction = "STRAIGHT"
        else:
            # Not currently steering — only engage once past the dead zone
            if angle > DEAD_ZONE_DEG:
                direction = "LEFT"
            elif angle < -DEAD_ZONE_DEG:
                direction = "RIGHT"
            else:
                direction = "STRAIGHT"

        strength = 0.0
        if direction == "LEFT":
            strength = min(1.0, (abs(angle) - DEAD_ZONE_DEG) / (SOFT_ZONE_DEG - DEAD_ZONE_DEG))
            self._press(Key.left)
            self._release(Key.right)
        elif direction == "RIGHT":
            strength = min(1.0, (abs(angle) - DEAD_ZONE_DEG) / (SOFT_ZONE_DEG - DEAD_ZONE_DEG))
            self._press(Key.right)
            self._release(Key.left)
        else:
            self._release(Key.left)
            self._release(Key.right)

        return angle, direction, strength

    def update_throttle(self, left_open, right_open):
        both_open = left_open and right_open
        both_fist = (not left_open) and (not right_open)

        if both_fist:
            self._press(Key.up)
            self._release(Key.down)
            return "ACCEL"
        elif both_open:
            self._press(Key.down)
            self._release(Key.up)
            return "BRAKE"
        else:
            self._release(Key.up)
            self._release(Key.down)
            return "NEUTRAL"


def draw_landmarks_manual(frame, landmarks, w, h):
    # Draw connections
    for start_idx, end_idx in HAND_CONNECTIONS:
        pt1 = (int(landmarks[start_idx].x * w), int(landmarks[start_idx].y * h))
        pt2 = (int(landmarks[end_idx].x * w), int(landmarks[end_idx].y * h))
        cv2.line(frame, pt1, pt2, (80, 80, 100), 1)

    # Draw keypoints
    for lm in landmarks:
        cx, cy = int(lm.x * w), int(lm.y * h)
        cv2.circle(frame, (cx, cy), 2, (200, 200, 255), -1)


def draw_steering_wheel(frame, center, angle_deg, direction, strength):
    h, w = frame.shape[:2]
    radius = int(min(w, h) * 0.10)
    cx, cy = center

    color = CLR_NEUTRAL
    if direction == "LEFT":
        color = CLR_LEFT
    elif direction == "RIGHT":
        color = CLR_RIGHT

    cv2.circle(frame, (cx + 3, cy + 3), radius, (0, 0, 0), 4)
    cv2.circle(frame, (cx, cy), radius, color, 3)

    for sa in [0, 120, 240]:
        rad = math.radians(sa - angle_deg)
        x1 = int(cx + radius * 0.4 * math.cos(rad))
        y1 = int(cy - radius * 0.4 * math.sin(rad))
        x2 = int(cx + radius * 0.95 * math.cos(rad))
        y2 = int(cy - radius * 0.95 * math.sin(rad))
        cv2.line(frame, (x1, y1), (x2, y2), color, 2)

    cv2.circle(frame, (cx, cy), 6, color, -1)

    if direction != "STRAIGHT":
        start_a = -30 if direction == "RIGHT" else 150
        end_a   =  30 if direction == "RIGHT" else 210
        cv2.ellipse(frame, (cx, cy), (radius, radius), 0, start_a, end_a, color, 5)


def draw_hud(frame, angle, direction, strength, throttle_mode, both_hands_visible, left_open, right_open, fps):
    h, w = frame.shape[:2]

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, h - 160), (w, h), (10, 10, 20), -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

    bar_w = int(w * 0.5)
    bar_h = 14
    bar_x = (w - bar_w) // 2
    bar_y = h - 110
    font  = cv2.FONT_HERSHEY_SIMPLEX

    # Background track
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (40, 40, 50), -1)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (80, 80, 90), 1)

    mid = bar_x + bar_w // 2

    # Neutral zone band (visual indicator of the ±DEAD_ZONE_DEG safe range)
    neutral_half = int((bar_w // 2) * (DEAD_ZONE_DEG / SOFT_ZONE_DEG))
    cv2.rectangle(frame,
                  (mid - neutral_half, bar_y),
                  (mid + neutral_half, bar_y + bar_h),
                  (60, 60, 70), -1)
    cv2.putText(frame, "STRAIGHT",
                (mid - neutral_half, bar_y - 6), font, 0.35, CLR_NEUTRAL, 1)

    # Filled strength bar on active side
    fill_len = int((bar_w // 2) * strength)
    if direction == "LEFT" and fill_len > 0:
        cv2.rectangle(frame, (mid - fill_len, bar_y), (mid - neutral_half, bar_y + bar_h), CLR_LEFT, -1)
    elif direction == "RIGHT" and fill_len > 0:
        cv2.rectangle(frame, (mid + neutral_half, bar_y), (mid + fill_len, bar_y + bar_h), CLR_RIGHT, -1)

    # Center marker
    cv2.rectangle(frame, (mid - 2, bar_y - 4), (mid + 2, bar_y + bar_h + 4), (200, 200, 200), -1)

    dir_color = CLR_LEFT if direction == "LEFT" else (CLR_RIGHT if direction == "RIGHT" else CLR_NEUTRAL)
    cv2.putText(frame, "<- LEFT",  (bar_x, bar_y - 10),              font, 0.45, CLR_LEFT,  1)
    cv2.putText(frame, "RIGHT ->", (bar_x + bar_w - 80, bar_y - 10), font, 0.45, CLR_RIGHT, 1)
    cv2.putText(frame, direction,  (mid - 35, bar_y + bar_h + 28),   font, 0.8,  dir_color, 2)

    if SHOW_ANGLE:
        cv2.putText(frame, f"{angle:+.1f} deg", (bar_x, h - 80), font, 0.55, CLR_TEXT, 1)

    throttle_color = CLR_ACCEL if throttle_mode == "ACCEL" else (CLR_BRAKE if throttle_mode == "BRAKE" else CLR_NEUTRAL)
    throttle_label = {
        "ACCEL":   "ACCEL [UP]",
        "BRAKE":   "BRAKE [DOWN]",
        "NEUTRAL": "NEUTRAL",
    }[throttle_mode]

    cv2.rectangle(frame, (bar_x, h - 65), (bar_x + bar_w, h - 42), (30, 30, 40), -1)
    cv2.rectangle(frame, (bar_x, h - 65), (bar_x + bar_w, h - 42), throttle_color, 2)
    cv2.putText(frame, throttle_label, (bar_x + 10, h - 48), font, 0.65, throttle_color, 2)

    l_label = "OPEN" if left_open else "FIST"
    r_label = "OPEN" if right_open else "FIST"
    l_color = CLR_BRAKE if left_open else CLR_ACCEL
    r_color = CLR_BRAKE if right_open else CLR_ACCEL
    cv2.putText(frame, f"L:{l_label}", (bar_x + bar_w + 10, h - 100), font, 0.5, l_color, 1)
    cv2.putText(frame, f"R:{r_label}", (bar_x + bar_w + 10, h - 80),  font, 0.5, r_color, 1)

    cv2.putText(frame, f"FPS: {fps:.0f}", (w - 90, 30), font, 0.55, CLR_ACCENT, 1)

    status       = "BOTH HANDS DETECTED" if both_hands_visible else "SHOW BOTH HANDS"
    status_color = (60, 220, 60) if both_hands_visible else (0, 80, 255)
    cv2.putText(frame, status, (10, 30), font, 0.55, status_color, 1)

    draw_steering_wheel(frame, (w - 80, h - 80), angle, direction, strength)


def draw_hand_connection(frame, lw, rw):
    lx, ly = lw
    rx, ry = rw
    cv2.line(frame, (lx, ly), (rx, ry), (30, 100, 200), 8)
    cv2.line(frame, (lx, ly), (rx, ry), CLR_ACCENT, 2)
    cv2.circle(frame, (lx, ly), 10, CLR_HAND_L, -1)
    cv2.circle(frame, (rx, ry), 10, CLR_HAND_R, -1)
    cv2.circle(frame, (lx, ly), 13, CLR_HAND_L, 2)
    cv2.circle(frame, (rx, ry), 13, CLR_HAND_R, 2)
    mx = (lx + rx) // 2
    my = (ly + ry) // 2
    cv2.circle(frame, (mx, my), 7, CLR_WHEEL, -1)


def main():
    backend = cv2.CAP_AVFOUNDATION if platform.system() == "Darwin" else cv2.CAP_ANY
    cap = cv2.VideoCapture(CAMERA_INDEX, backend)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Cannot open camera.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 60)

    controller = SteeringController()

    # Modern MediaPipe Tasks Detector Setup
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=MIN_DETECTION_CONF,
        min_tracking_confidence=MIN_TRACKING_CONF
    )
    detector = vision.HandLandmarker.create_from_options(options)

    prev_time     = time.time()
    angle         = 0.0
    direction     = "STRAIGHT"
    strength      = 0.0
    throttle_mode = "NEUTRAL"
    left_open     = False
    right_open    = False
    lost_frames   = 0

    print("=" * 55)
    print("  Virtual Steering Wheel (MediaPipe Tasks Edition)")
    print("  Press Q to quit")
    print("=" * 55)

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.01)
                continue

            if FLIP_CAMERA:
                frame = cv2.flip(frame, 1)

            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Convert to MediaPipe Image
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            timestamp_ms = int(time.time() * 1000)
            
            # Detect Hands
            results = detector.detect_for_video(mp_image, timestamp_ms)

            both_visible = False

            if results.hand_landmarks and results.handedness:
                hand_data = {}

                for hand_landmarks, handedness_list in zip(results.hand_landmarks, results.handedness):
                    label = handedness_list[0].category_name  # "Left" or "Right"

                    draw_landmarks_manual(frame, hand_landmarks, w, h)

                    wrist  = hand_landmarks[0]
                    wx     = int(wrist.x * w)
                    wy     = int(wrist.y * h)
                    opened = is_open_hand(hand_landmarks)
                    hand_data[label] = (wrist.x, wrist.y, wx, wy, opened)

                if "Left" in hand_data and "Right" in hand_data:
                    both_visible = True
                    lost_frames  = 0

                    lx_n, ly_n, lx_px, ly_px, left_open  = hand_data["Left"]
                    rx_n, ry_n, rx_px, ry_px, right_open = hand_data["Right"]

                    draw_hand_connection(frame, (lx_px, ly_px), (rx_px, ry_px))
                    angle, direction, strength = controller.update_steer((lx_n, ly_n), (rx_n, ry_n))
                    throttle_mode = controller.update_throttle(left_open, right_open)
                else:
                    lost_frames += 1
                    if lost_frames >= GRACE_FRAMES:
                        controller.release_all()
                        angle, direction, strength = 0.0, "STRAIGHT", 0.0
                        throttle_mode = "NEUTRAL"
                        left_open = right_open = False
            else:
                lost_frames += 1
                if lost_frames >= GRACE_FRAMES:
                    controller.release_all()
                    angle, direction, strength = 0.0, "STRAIGHT", 0.0
                    throttle_mode = "NEUTRAL"
                    left_open = right_open = False

            now       = time.time()
            fps       = 1.0 / max(now - prev_time, 1e-6)
            prev_time = now

            draw_hud(frame, angle, direction, strength, throttle_mode, both_visible, left_open, right_open, fps)
            cv2.imshow("Virtual Steering Wheel", frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), ord('Q'), 27):
                break

    finally:
        controller.release_all()
        detector.close()
        cap.release()
        cv2.destroyAllWindows()
        print("\n[INFO] Stopped cleanly.")


if __name__ == "__main__":
    main()