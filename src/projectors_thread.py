# Initialize CMOS camera

import usb.core
import usb.util
import time
import threading
from projector.dotspattern import DotsPattern
from projector.pycrafter6500 import dmd
from alignment import ImageTransformer
from models import devices_db, devices_list, projected_frames


class ProjectorsThread(threading.Thread):
    def __init__(self):
        # Initialize projectors
        self.green_dots_pattern = DotsPattern()
        self.laser_dots_pattern = DotsPattern()

        # Set connection to projectors
        devices = list(usb.core.find(
            idVendor=0x0451, idProduct=0xc900, find_all=True))
        print("Found {} projector(s)".format(len(devices)))

        if(len(devices) == 0):
            print("No projector found")
            self.projector_1 = dmd()
            self.projector_2 = dmd()
        elif(len(devices) == 1):
            self.projector_1 = dmd(devices[0], devices[0].address)
            self.projector_2 = dmd()
        elif(len(devices) == 2):
            self.projector_1 = dmd(devices[0], devices[0].address)
            self.projector_2 = dmd(devices[1], devices[1].address)

        self.rgb_projector = self.projector_1
        self.laser_projector = self.projector_2

        # Init thread
        threading.Thread.__init__(self)

    def run(self):
        while(True):
            print("hey")
            time.sleep(1)
            # update connected status in db
            # if self.camera.connected is not None:
            #     devices_db.update(
            #         {'connected': self.camera.connected}, devices_list.name == "cmos-camera")
            # if(self.camera.connected):
            #     self.read = self.camera.Read()
            #     if(self.read is not None):
            #         print("CMOS Camera read successful")
            #         # Encode image as jpg
            #         self.ret, self.buffer = cv2.imencode(
            #             '.jpg', self.read)
            #         self.frame = self.buffer.tobytes()
            #         # Compute projection
            #         self.projected_frame = self.image_transformer.project(
            #             self.read)
            #         # Store frame in database
            #         projected_frames["cmos-camera"] = self.projected_frame

            #         time.sleep(0.02)
            # else:
            #     print("CMOS Camera disconnected")
            #     self.camera.Connect()  # Try to connect again
            #     time.sleep(1)
