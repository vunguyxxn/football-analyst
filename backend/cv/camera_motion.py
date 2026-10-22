"""Conservative incremental ground-plane motion; failure latches until re-anchor."""
import cv2
import numpy as np


class CameraMotion:
    def __init__(self):
        self.previous = None
        self.mask = None
        self.matrix = None
        self.failed = False
        self.age = 0

    @staticmethod
    def ground_mask(frame, matrix, boxes):
        height, width = frame.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, (30, 35, 35), (90, 255, 255))
        mask = cv2.erode(mask, np.ones((7, 7), np.uint8))
        # Restrict to the calibrated ground plane, not audience/score overlays.
        yy, xx = np.mgrid[:height:4, :width:4]
        points = np.stack([xx, yy, np.ones_like(xx)], axis=-1) @ matrix.T
        with np.errstate(divide="ignore", invalid="ignore"):
            xy = points[..., :2] / points[..., 2:]
        inside = np.isfinite(xy).all(axis=-1) & (xy[..., 0] >= 0) & (xy[..., 0] <= 105) & (xy[..., 1] >= 0) & (xy[..., 1] <= 68)
        mask &= cv2.resize(inside.astype(np.uint8)*255, (width, height), interpolation=cv2.INTER_NEAREST)
        for x1, y1, x2, y2 in boxes:
            cv2.rectangle(mask, (max(0, int(x1)-12), max(0, int(y1)-12)),
                          (min(width-1, int(x2)+12), min(height-1, int(y2)+12)), 0, -1)
        return mask

    def update(self, frame, boxes, anchor=None):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if anchor is not None:
            self.matrix = anchor.copy()
            self.failed = False
            self.age = 0
            status = {"status": "manual_anchor"}
        elif self.failed or self.previous is None:
            return {"status": "lost", "reason": "manual_anchor_required"}
        else:
            self.age += 1
            current_mask = self.ground_mask(frame, self.matrix, boxes)
            points = cv2.goodFeaturesToTrack(self.previous, 500, .01, 10, mask=self.mask)
            status = {"status": "lost", "reason": "insufficient_ground_features"}
            if points is not None and len(points) >= 20:
                target, ok, _ = cv2.calcOpticalFlowPyrLK(self.previous, gray, points, None)
                if target is not None:
                    back, valid, _ = cv2.calcOpticalFlowPyrLK(gray, self.previous, target, None)
                    if back is not None:
                        good = (ok.ravel() == 1) & (valid.ravel() == 1)
                        good &= np.linalg.norm(back-points, axis=2).ravel() < 1
                        good &= np.isfinite(target).all(axis=(1, 2))
                        rounded = np.rint(np.nan_to_num(target[:, 0])).astype(int)
                        x, y = rounded.T
                        inside = (x >= 0) & (x < gray.shape[1]) & (y >= 0) & (y < gray.shape[0])
                        good &= inside
                        good[inside] &= current_mask[y[inside], x[inside]] > 0
                        old, new = points[good, 0], target[good, 0]
                        if len(old) >= 20:
                            transform, inliers = cv2.findHomography(old, new, cv2.RANSAC, 2.)
                            if transform is not None and inliers is not None:
                                selected = inliers.ravel().astype(bool)
                                count = int(selected.sum())
                                coverage = cv2.contourArea(cv2.convexHull(old[selected])) / gray.size if count >= 3 else 0
                                ratio = count / len(old)
                                predicted = cv2.perspectiveTransform(old[selected, None], transform)[:, 0]
                                error = float(np.median(np.linalg.norm(predicted-new[selected], axis=1))) if count else float('inf')
                                height, width = gray.shape
                                corners = np.float32([[0, 0], [width, 0], [width, height], [0, height]])[:, None]
                                warped = cv2.perspectiveTransform(corners, transform)
                                area = cv2.contourArea(warped, oriented=True)/(width*height)
                                shift = float(np.max(np.linalg.norm(warped-corners, axis=2)))
                                status = {"status": "lost", "reason": "motion_quality_gate", "inliers": count,
                                          "inlier_ratio": ratio, "coverage": coverage, "median_error_px": error}
                                if count >= 20 and ratio >= .7 and coverage >= .03 and error <= 1.5 and .8 < area < 1.25 and shift < .15*max(width, height) and abs(np.linalg.det(transform)) > 1e-9:
                                    candidate = self.matrix @ np.linalg.inv(transform)
                                    if np.isfinite(candidate).all() and abs(candidate[2, 2]) > 1e-9:
                                        self.matrix = candidate/candidate[2, 2]
                                        status["status"] = "tracked"
                                        status.pop("reason")
            # Bound cumulative unchecked drift; manual anchor restarts the chain.
            if self.age > 300:
                status = {"status": "lost", "reason": "reanchor_interval_exceeded"}
            if status["status"] == "lost":
                self.failed = True
                self.matrix = None
                self.previous = self.mask = None
                return status
        self.previous = gray
        self.mask = self.ground_mask(frame, self.matrix, boxes)
        return status
