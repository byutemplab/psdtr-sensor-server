import zwoasi as asi
import cv2


class CMOSCameraFeed():
    def __init__(self, settings):
        self.connected = False
        self.settings = settings
        self.resolution = 960
        # Init asi library
        env_filename = 'cmoscamera/asi-sdk/lib/ASICamera2.dll'
        asi.init(env_filename)

    def Connect(self):
        # Look for connected cameras
        num_cameras = asi.get_num_cameras()

        # If no camera is connected, exit
        if num_cameras == 0:
            self.connected = False
        # If camera is connected, initialize it
        else:
            self.connected = True
            self.camera = asi.Camera(0)
            self.camera.start_video_capture()

            # Set camera parameters
            self.camera.set_control_value(
                asi.ASI_EXPOSURE, self.settings["exposure"])
            self.camera.set_control_value(asi.ASI_GAIN, self.settings["gain"])
            self.camera.set_control_value(
                asi.ASI_BRIGHTNESS, self.settings["brightness"])
            self.camera.set_control_value(asi.ASI_FLIP, 0)
            self.camera.set_control_value(asi.ASI_HIGH_SPEED_MODE, 1)
            self.camera.set_roi_format(self.resolution, self.resolution, 1, 0)
            # self.camera.set_control_value(asi.ASI_WB_B, 99)
            # self.camera.set_control_value(asi.ASI_WB_R, 75)
            # self.camera.set_control_value(asi.ASI_GAMMA, 50)

    def Read(self):
        try:
            return self.camera.capture_video_frame(
                timeout=3000)  # read the camera frame
        except:
            self.connected = False

    def ChangeResolution(self, resolution):
        self.resolution = resolution if resolution <= 960 else 960
        try:
            self.camera.set_roi_format(self.resolution, self.resolution, 1, 0)
        except:
            self.connected = False

    def UpdateSettings(self, settings):
        self.settings = settings
        if self.connected:
            try:
                self.camera.set_control_value(
                    asi.ASI_EXPOSURE, self.settings["exposure"])
                self.camera.set_control_value(
                    asi.ASI_GAIN, self.settings["gain"])
                self.camera.set_control_value(
                    asi.ASI_BRIGHTNESS, self.settings["brightness"])
            except:
                self.connected = False
