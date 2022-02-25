##############################
#         ALIGNMENT          #
##############################

# 1. Select two base points (top left and bottom right)
# 2. Base plane for transformation is the sem image
# 3. These two points set the test pattern for the green projector
# 4. CMOS camera feed
#     a. Select location of marks on the sample
#     b. Select location of green dots
# 5. Set transformation settings (rotation and scale) for the CMOS camera feed
# 6. Set transformation settings (rotation and scale) for the green projector pattern !!! np array transform !!!
# 7. Lock-in camera feed
#     a. Select location of green dots
# 8. Set transformation settings (rotation and scale) for the lock-in camera feed
#
# Future improvements:
#   - could we make the lock-in camera array the base plane for transformation
#     so to not lose quality?

import cv2
import numpy as np

alignment_settings = {
    "cmos-camera-marks": [[0.05, 0.4], [0.35, 0], [0.95, 0.5], [0.7, 0.9]],
    "sem-image-marks": [[0, 0], [1, 0], [1, 1], [0, 1]],
    "cmos-camera-green-dots": [[0, 0], [0, 0], [0, 0], [0, 0]],
    "lock-in-camera-green-dots": [[0, 0], [0, 0], [0, 0], [0, 0]],
}


class ImageTransformer():
    def __init__(self, src_points, dst_points, cols, rows):
        self.update_projective_matrix(src_points, dst_points)
        self.cols = cols
        self.rows = rows

    def update_projective_matrix(self, src_points, dst_points):
        self.projective_matrix = cv2.getPerspectiveTransform(
            src_points, dst_points)

    def project(self, image):
        # transform image to np array
        return cv2.warpPerspective(image, self.projective_matrix, (self.cols, self.rows))
