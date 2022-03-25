import cv2
import time
import threading
import numpy as np
from PIL import Image
from models import projected_frames


class AlignmentCheckThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def superpose(self, sample, sem_image):  # TODO add trajectories
        # blend images with 0.5 transparency
        sample = Image.fromarray(sample).convert('RGBA')
        sample = sample.resize((500, 500))
        sem_image = Image.fromarray(sem_image).convert('RGBA')
        sem_image = sem_image.resize((500, 500))
        combined_frame = Image.blend(sample, sem_image, 0.5)

        return np.array(combined_frame)

    def run(self):
        while(True):
            if (projected_frames["sem-image"] is not None and projected_frames["cmos-camera"] is not None):
                self.superposed_frame = self.superpose(
                    projected_frames["cmos-camera"], projected_frames["sem-image"])
                self.ret, self.buffer = cv2.imencode(
                    '.jpg', self.superposed_frame)
                self.frame = self.buffer.tobytes()
            else:
                self.frame = None
            time.sleep(0.1)
