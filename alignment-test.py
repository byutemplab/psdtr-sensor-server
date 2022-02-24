from alignment import ImageTransformer
import skimage
from skimage import io
from skimage.transform import warp, ProjectiveTransform
import os
import numpy as np
import cv2

#############################
#          Test 1           #
#############################

# img = cv2.imread('./sem/data/sem-image-sample.png')
# rows, cols = img.shape[:2]
# src_points = np.float32([[0, 0], [cols-1, 0], [0, rows-1], [cols-1, rows-1]])
# dst_points = np.float32(
#     [[0, 0], [cols-1, 0], [int(0.33*cols), rows-1], [int(0.66*cols), rows-1]])
# projective_matrix = cv2.getPerspectiveTransform(src_points, dst_points)
# img_output = cv2.warpPerspective(img, projective_matrix, (cols, rows))
# cv2.imshow('Input', img)
# cv2.imshow('Output', img_output)
# cv2.waitKey()

#############################
#          Test 2           #
#############################

# frame = cv2.imread('./sem/data/delete.png')
# transformed_frame = cmos_camera_feed_t.transform(frame)
# self.last_frame = transformed_frame.tobytes()

#############################
#          Test 3           #
#############################

# points_a = np.float32([[0, 0],
#                        [0, 400],
#                        [400, 400],
#                        [400, 400]])
# points_b = np.float32([[0, 0],
#                        [0, 400],
#                        [400, 400],
#                        [400, 400]])
# matrix = cv2.getPerspectiveTransform(points_a, points_b)

# file = os.path.join('./sem/data/sem-image-sample.png')
# frame = io.imread(file)
# new_frame = warp(frame, matrix)

# io.imshow(new_frame)
# io.show()

#############################
#          Test 4           #
#############################

img = cv2.imread('./sem/data/sem-image-sample.png')
rows, cols = img.shape[:2]
src_points = np.float32([[0, 0], [cols-1, 0], [0, rows-1], [cols-1, rows-1]])
dst_points = np.float32(
    [[0, 0], [cols-1, 0], [int(0.33*cols), rows-1], [int(0.66*cols), rows-1]])
image_transformer = ImageTransformer(src_points, dst_points, rows, cols)
img_output = image_transformer.project(img)
cv2.imshow('Input', img)
cv2.imshow('Output', img_output)
cv2.waitKey()
