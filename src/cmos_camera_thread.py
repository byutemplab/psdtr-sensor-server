# Initialize CMOS camera

import cv2
import time
import threading
from cmoscamera.camerastream import CMOSCameraFeed
from alignment import ImageTransformer
from models import devices_db, devices_list, projected_frames


class CMOSCameraThread(threading.Thread):
    def __init__(self):
        current_settings = devices_db.search(
            devices_list.name == "cmos-camera")[0]["settings"]
        # Initialize camera
        self.camera = CMOSCameraFeed(current_settings)
        self.read = None
        self.frame = None
        self.projected_frame = None

        # Initialize image transformer
        cmos_camera_height = 960
        cmos_camera_width = 960
        sem_image_height = 500
        sem_image_width = 500
        self.image_transformer = ImageTransformer(
            cmos_camera_width, cmos_camera_height, "cmos-camera-marks", sem_image_width, sem_image_height, "sem-image-marks")

        # Init thread
        threading.Thread.__init__(self)

    def run(self):
        while(True):
            # update connected status in db
            db_connected_status = devices_db.search(
                devices_list.name == "cmos-camera")[0]["connected"]
            if self.camera.connected is not db_connected_status and db_connected_status is not None:
                devices_db.update(
                    {'connected': self.camera.connected}, devices_list.name == "cmos-camera")
            if(self.camera.connected):
                self.read = self.camera.Read()
                if(self.read is not None):
                    # Encode image as jpg
                    self.ret, self.buffer = cv2.imencode(
                        '.jpg', self.read)
                    self.frame = self.buffer.tobytes()
                    # Compute projection
                    self.projected_frame = self.image_transformer.project(
                        self.read)
                    # Store frame in database
                    projected_frames["cmos-camera"] = self.projected_frame

                    time.sleep(0.02)
            else:
                self.camera.Connect()  # Try to connect again
                time.sleep(1)
