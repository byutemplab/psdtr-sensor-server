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
from models import alignment_items, alignment_settings_db


class ImageTransformer():
    def __init__(self, src_cols, src_rows, src_marks_db_name, dest_cols, dest_rows, dest_marks_db_name):
        self.src_cols = src_cols
        self.src_rows = src_rows
        self.dest_cols = dest_cols
        self.dest_rows = dest_rows
        self.src_marks_db_name = src_marks_db_name
        self.dest_marks_db_name = dest_marks_db_name
        self.update()

    def update(self):
        src_marks = alignment_settings_db.search(
            alignment_items.name == self.src_marks_db_name)[0]["coordinates"]
        dest_marks = alignment_settings_db.search(
            alignment_items.name == self.dest_marks_db_name)[0]["coordinates"]
        self.update_marks(src_marks, dest_marks)

    def update_marks(self, src_marks, dst_marks):
        src_points = np.float32(
            np.int32(np.array(src_marks) * [self.src_cols, self.src_rows]))
        dst_points = np.float32(
            np.int32(np.array(dst_marks) * [self.dest_cols, self.dest_cols]))
        self.update_projective_matrix(src_points, dst_points)

    def update_projective_matrix(self, src_points, dst_points):
        self.projective_matrix = cv2.getPerspectiveTransform(
            src_points, dst_points)

    def project(self, image):
        # transform image to np array
        return cv2.warpPerspective(image, self.projective_matrix, (self.dest_cols, self.dest_rows))
