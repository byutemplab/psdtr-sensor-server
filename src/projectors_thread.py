import os
import usb.core
import usb.util
import skimage.draw
import numpy as np
import time
import threading
from projector.pycrafter6500 import dmd
from models import devices_db, devices_list, projected_frames

RES_Y = 1080  # projectors' resolution
RES_X = 1920


class ProjectorThread(threading.Thread):
    def __init__(self, name, address):
        # Init thread
        threading.Thread.__init__(self)

        # Initialize projector
        self.name = name
        self.address = address
        self.dmd = dmd(address)

        # devices = list(usb.core.find(idVendor=0x0451,           # just for testing
        #                idProduct=0xc900, find_all=True))
        # print("addresses available")
        # for dev in devices:
        #     print(dev.address)

    def run(self):
        while(True):
            # check if projector is connected
            self.dmd.CheckConnection()

            # update connected status in db
            db_connected_status = devices_db.search(
                devices_list.name == self.name)[0]["connected"]
            if self.dmd.connected is not db_connected_status and db_connected_status is not None:
                devices_db.update({'connected': self.dmd.connected},
                                  devices_list.name == self.name)

            if (not self.dmd.connected):
                print(self.name, "disconnected")

            time.sleep(1)

    def SendPattern(self, pattern):
        # Check if projector is connected
        connected = self.dmd.CheckConnection()
        print(connected)
        if (not connected):
            return False

        # Init empty array
        frames_array = []
        for frame in range(pattern['number-of-measurements']):
            frames_array.append(np.zeros((RES_Y, RES_X)).astype(np.uint8))

        if self.name == 'rgb-projector':
            # Draw each green dot trajectory in the frames array
            for trajectory in pattern['trajectories']:
                # Get every point in the line
                rr, cc = skimage.draw.line(int(trajectory['start'][1] * RES_Y), int(trajectory['start'][0] * RES_X),
                                           int(trajectory['end'][1] * RES_Y), int(trajectory['end'][0] * RES_X))

                # Calculate distance between dots
                dot_step = (len(rr) - 1) / \
                    (pattern['number-of-measurements'] - 1)

                # Go through each frame, draw corresponding points
                for frame_idx, frame in enumerate(frames_array):
                    # Get point in the line for this frame
                    dot_idx = round(frame_idx * dot_step)

                    # Draw point in current frame
                    rr_disk, cc_disk = skimage.draw.disk(
                        (rr[dot_idx], cc[dot_idx]), pattern['green-point-diameter'])
                    frame[rr_disk, cc_disk] = 1

        if self.name == 'laser-projector':
            # Draw the middle point of each trajectory for the laser beam
            for trajectory in pattern['trajectories']:
                # Get the middle point of the trajectory
                middle_point = (int((trajectory['start'][1] + trajectory['end'][1]) * RES_Y / 2),
                                int((trajectory['start'][0] + trajectory['end'][0]) * RES_X / 2))

                # Draw the middle point
                rr_disk, cc_disk = skimage.draw.disk(
                    middle_point, pattern['laser-point-diameter'])

                # Draw point in each frame
                for frame in frames_array:
                    frame[rr_disk, cc_disk] = 1

        self.dmd.stopsequence()
        self.dmd.changemode(3)

        # Set secondary parameters
        exposure = [pattern['measurement-time'] * 1000]*len(frames_array)
        dark_time = [0]*len(frames_array)
        trigger_in = [0]*len(frames_array)
        trigger_out = [0]*len(frames_array)
        repetitions = 0  # infinite loop

        # Start sequence
        self.dmd.defsequence(frames_array, 'green', exposure, trigger_in,
                             dark_time, trigger_out, repetitions)
        self.dmd.startsequence()

        return True
