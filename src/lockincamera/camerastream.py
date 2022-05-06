# -------------------------------------------------------------------------------
# Author:      Santiago Gomez Paz
# Project:     2021 - TEMP lab molten salt reactor sensor
# -------------------------------------------------------------------------------

from __future__ import division, print_function
from logging import error
from .libHeLIC import LibHeLIC
import numpy as np
import ctypes as ct
import cv2

DEBUG = False


class LockInCamera():
    def __init__(self):
        self.connected = False
        self.scans_array = []

    def Connect(self):
        # Init library and open camera
        self.heSys = LibHeLIC()
        self.connected = self.heSys.Open(0, sys='c3cam_sl70')
        if(self.connected == False):
            self.connected = False
            return None

        self.connected = True

        # Set parameters
        self.frames = 50
        self.settings = (
            ('CamMode',       3),         # intensity
            ('SensTqp',       69989),     # measure 500 Hz
            ('SensDeltaExp',  0),
            ('SensNavM2',     2),
            ('SensNFrames',   self.frames),
            ('BSEnable',      1),
            ('DdsGain',       2),
            ('TrigFreeExtN',  1),
            ('InvEncCnt',     0),
            ('FWHMnFrame',    1),
            ('IterMaxFrac',   2),
            ('MinEnergWin',   16),
            ('OffsetMethod',  1),
            ('UseLastFrame',  1),
            ('NFrmAvg',       3),
            ('AcqStop',       0),
        )
        for k, v in self.settings:
            try:
                setattr(self.heSys.map, k, v)  # heSys.map.k=v
            except RuntimeError:
                error('Could not set map property %s to %s', k, v)

        # Allocate place for data in IQ format
        self.heSys.AllocCamData(1, LibHeLIC.CamDataFmt['DF_I16Q16'], 0, 0, 0)

    def Read(self):
        # Get raw data from the camera
        res = self.heSys.Acquire()
        if(res < 0):
            print("Error acquiring data from Lock In Camera")
            self.connected = False
            return None

        if(DEBUG):
            print("Acquire returned", res)

        # Process data
        cd = self.heSys.ProcessCamData(1, 0, 0)
        if(DEBUG):
            print("ProcessCamData returned", cd.contents.data)

        # Get data and put it in an array
        # Array shape: frames * 300 [width] * 300 [height] * 2 [I and Q]
        img = self.heSys.GetCamData(1, 0, 0)
        data = img.contents.data
        data = LibHeLIC.Ptr2Arr(data, (self.frames, 300, 300, 2), ct.c_int16)

        # Sum data from all frames, skip frame 0
        intensity = data[1:, :, :, 0].sum(axis=0, dtype=np.int16)

        # Save in array
        self.scans_array.append(intensity)

        return intensity

    def SaveScansArray(self, path):
        # Save data list to a npy file
        np.save(path, self.scans_array)
