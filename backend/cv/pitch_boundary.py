"""Image-space white-line/grass boundary filter; never supplies metric coordinates."""
import cv2
import numpy as np


def clip_polygon(polygon, a, b, c):
    """Keep a*x+b*y+c >= 0, including the painted line itself."""
    output = []
    for start, end in zip(polygon, np.roll(polygon, -1, axis=0)):
        before, after = a * start[0] + b * start[1] + c, a * end[0] + b * end[1] + c
        if before >= 0:
            output.append(start)
        if (before >= 0) != (after >= 0):
            output.append(start + (end - start) * before / (before - after))
    return np.asarray(output, dtype=np.float32).reshape(-1, 2)


def pitch_region(frame):
    """Require long near/far touchlines each frame; no stale or grass-only fallback."""
    height, width = frame.shape[:2]
    small_width = min(960, width)
    small_height = max(1, round(height * small_width / width))
    small = cv2.resize(frame, (small_width, small_height))
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    green = cv2.inRange(hsv, (30, 40, 30), (90, 255, 255))
    green = cv2.morphologyEx(green, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    contours, _ = cv2.findContours(green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contour = max(contours, key=cv2.contourArea)
    if cv2.contourArea(contour) < .25 * small_width * small_height:
        return None
    hull = cv2.convexHull(contour).reshape(-1, 2).astype(np.float32)
    support = np.zeros_like(green)
    cv2.fillConvexPoly(support, hull.astype(np.int32), 255)
    white = cv2.inRange(hsv, (0, 0, 140), (180, 105, 255)) & support
    # Hough on a filled pale walkway invents lines through its interior.
    # Require actual image edges, not just a low-saturation colour region.
    white = cv2.dilate(white, np.ones((3, 3), np.uint8)) & cv2.Canny(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), 10, 30)
    lines = cv2.HoughLinesP(white, 1, np.pi / 720, 30,
                            minLineLength=max(40, small_width * .12), maxLineGap=24)
    if lines is None:
        return None
    near, far, diagonal = [], [], []
    for x1, y1, x2, y2 in lines.reshape(-1, 4):
        if abs(x2 - x1) < 1:
            continue
        slope = (float(y2) - y1) / (float(x2) - x1)
        intercept = y1 - slope * x1
        middle = slope * small_width / 2 + intercept
        span = abs(x2 - x1)
        if abs(slope) <= .3:
            item = (span / (1 + 3 * abs(slope)), slope, intercept)
            if span >= .3 * small_width and .55 * small_height < middle < small_height:
                near.append(item)
            if span >= .4 * small_width and 0 < middle < .4 * small_height:
                far.append(item)
        elif .3 < abs(slope) < 3:
            diagonal.append((x1, y1, x2, y2, slope, intercept))
    if not near or not far:
        return None
    # Painted walkways/advertising can run parallel below the real touchline.
    # Of the long lower-field lines, keep the innermost one, not the longest.
    _, near_slope, near_intercept = min(near, key=lambda line: line[1] * small_width / 2 + line[2])
    # Technical-area dashes can join into a long line ABOVE the touchline.
    # Choose the innermost long far line, keeping those staff outside.
    _, far_slope, far_intercept = max(far, key=lambda line: line[1] * small_width / 2 + line[2])
    if near_intercept - far_intercept < .3 * small_height:
        return None
    hull = clip_polygon(hull, -far_slope, 1, -far_intercept)
    hull = clip_polygon(hull, near_slope, -1, near_intercept)
    # A visible goal line must actually meet the far touchline at its endpoint;
    # penalty-box lines stop inside the field and must not crop the pitch.
    for x1, y1, x2, y2, slope, intercept in diagonal:
        if abs(slope - far_slope) < 1e-6:
            continue
        x = (far_intercept - intercept) / (slope - far_slope)
        y = far_slope * x + far_intercept
        meets_corner = min(np.hypot(x - x1, y - y1), np.hypot(x - x2, y - y2)) <= 20
        right = x > .65 * small_width and slope > 0
        left = x < .35 * small_width and slope < 0
        if meets_corner and (right or left) and 0 <= y < .4 * small_height:
            a, b, c = -slope, 1, -intercept
            if a * small_width / 2 + b * small_height / 2 + c < 0:
                a, b, c = -a, -b, -c
            hull = clip_polygon(hull, a, b, c)
    if len(hull) < 3 or cv2.contourArea(hull) < .2 * small_width * small_height:
        return None
    return hull * [width / small_width, height / small_height]


def inside_pitch(region, box):
    if region is None:
        return False
    left, top, right, bottom = box
    if not np.isfinite(box).all() or right <= left or bottom <= top:
        return False
    return cv2.pointPolygonTest(np.asarray(region, dtype=np.float32),
                                (float((left + right) / 2), float(bottom)), False) >= 0
