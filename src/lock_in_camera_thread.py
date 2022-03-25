import cv2
import time
import threading
from lockincamera.camerastream import LockInCamera


class LockInCameraThread(threading.Thread):
    def __init__(self):
        # Initialize camera
        self.camera = LockInCamera()
        self.read = None
        self.frame = None
        # self.projected_frame = None
        # Init thread
        threading.Thread.__init__(self)

    def run(self):
        while(True):
            devices["helicam"]["connected"] = self.camera.connected
            if(self.camera.connected):
                self.read = self.camera.Read()
                if(self.read is not None):
                    print("Lock In Camera read successful")
                    # Encode image as jpg
                    self.ret, self.buffer = cv2.imencode(
                        '.jpg', self.read)
                    self.frame = self.buffer.tobytes()
                    # Compute projection
                    # self.projected_frame = self.image_transformer.project(
                    #     self.read)
                    time.sleep(0.2)
            else:
                print("Lock In Camera disconnected")
                self.camera.Connect()  # Try to connect again
                time.sleep(1)
