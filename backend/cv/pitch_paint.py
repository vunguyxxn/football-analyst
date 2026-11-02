"""Observed paint including narrow white lines mixed with green by compression."""
import cv2
import numpy as np


def paint_pixels(frame, *, expanded=False):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    saturation, value = hsv[:, :, 1], hsv[:, :, 2]
    grass = ((hsv[:, :, 0] > 30) & (hsv[:, :, 0] < 90) & (saturation > 60)).astype(np.float32)
    near_grass = cv2.boxFilter(grass, -1, (31, 31)) > .45
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    brighter = cv2.morphologyEx(value, cv2.MORPH_TOPHAT, kernel) >= 15
    less_saturated = cv2.morphologyEx(saturation, cv2.MORPH_BLACKHAT, kernel) >= 20
    white = (saturation < 100) & (value > 150)
    # Absolute saturation can stay high because of grass bleed. Both local
    # contrasts are mandatory; broad mowing stripes are not painted evidence.
    mixed = (value > 150) & brighter & less_saturated
    if not expanded:
        mixed &= saturation < 140
    yy, xx = np.nonzero((white | mixed) & near_grass)
    return np.column_stack([xx, yy]).astype(np.float32)
