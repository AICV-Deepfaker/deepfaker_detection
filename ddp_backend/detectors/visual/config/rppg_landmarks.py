#rppg_landmarks.py
class FCConfig:
    FACE_PAD_RATIO = 0.2      # bbox fallback 패딩 비율
    FACE_OVAL_INDICES = list(range(0, 33))  # insightface 2d106 face contour
    DET_SIZE = (640, 640)       # insightface detection 입력 크기