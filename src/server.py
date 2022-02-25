from tokenize import Name
import markdown
import os
import cv2
import time
import threading
import numpy as np
from cmoscamera.camerastream import CMOSCamera
from lockincamera.camerastream import LockInCamera
from alignment import ImageTransformer, alignment_settings
from PIL import Image

# Import the framework
from flask import Flask, Response
from flask_restful import Resource, Api, reqparse

# Devices list
devices = {
    "rgb-projector": {
        "id": 1,
        "name": "Green Projector",
        "device_type": "projector",
        "port": "COM1",
        "connected": False,
        "alignment_settings": {
            "top_left_corner": [0, 0],
            "top_right_corner": [1920, 0],
        },
        "pattern_settings": {
            "dot_color": "green",
            "dot_diameter": 10,
            "dot_shape": "circle",
            "trajectories_coords": [
                {"start": [537, 142], "end": [944, 198]},
                {"start": [411, 816], "end": [734, 1185]},
            ],
            "exposure_time": 50,
        },
    },
    "laser-projector": {
        "id": 2,
        "name": "Laser Projector",
        "device_type": "projector",
        "port": "COM2",
        "connected": False,
        "alignment_settings": {
            "top_left_corner": [0, 0],
            "top_right_corner": [1920, 0],
        },
        "pattern_settings": {},
    },
    "laser-waveform": {
        "id": 3,
        "name": "Waveform Generator",
        "device_type": "waveform-generator",
        "port": "COM3",
        "connected": False,
        "settings": {},
    },
    "helicam": {
        "id": 4,
        "name": "Lock-In Camera",
        "device_type": "camera",
        "port": "COM4",
        "connected": False,
        "streaming": False,
        "alignment_settings": {
            "top_left_corner": [0, 0],
            "top_right_corner": [1920, 0],
        },
        "settings": {},
    },
    "cmos-camera": {
        "id": 5,
        "name": "CMOS Camera",
        "device_type": "camera",
        "port": "COM5",
        "connected": False,
        "streaming": False,
        "alignment_settings": {
            "top_left_corner": [0, 0],
            "top_right_corner": [1920, 0],
        },
        "settings": {},
    },
}


class CMOSCameraThread(threading.Thread):
    def __init__(self):
        # Initialize camera
        self.camera = CMOSCamera()
        self.read = None
        self.frame = None
        self.projected_frame = None

        # Initialize image transformer
        camera_res = 960
        sem_image_height = 500
        sem_image_width = 500
        src_points = np.float32(np.int32(np.array(
            alignment_settings["cmos-camera-marks"]) * camera_res))
        dst_points = np.float32(np.int32(np.array(
            alignment_settings["sem-image-marks"]) * [sem_image_width, sem_image_height]))
        self.image_transformer = ImageTransformer(
            src_points, dst_points, sem_image_width, sem_image_height)

        threading.Thread.__init__(self)

    def run(self):
        while(True):
            devices["cmos-camera"]["connected"] = self.camera.connected
            if(self.camera.connected):
                self.read = self.camera.Read()
                if(self.read is not None):
                    print("CMOS Camera read successful")
                    # Encode image as jpg
                    self.ret, self.buffer = cv2.imencode(
                        '.jpg', self.read)
                    self.frame = self.buffer.tobytes()
                    # Compute projection
                    self.projected_frame = self.image_transformer.project(
                        self.read)
                    time.sleep(0.02)
            else:
                print("CMOS Camera disconnected")
                self.camera.Connect()  # Try to connect again
                time.sleep(1)


# Init CMOS Camera
cmos_camera_thread = CMOSCameraThread()


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


# Init Lock In Camera thread
lock_in_camera_thread = LockInCameraThread()


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
            sample = cmos_camera_thread.projected_frame
            if (sample is not None and sem_image is not None):
                self.superposed_frame = self.superpose(
                    cmos_camera_thread.projected_frame, sem_image)
                self.ret, self.buffer = cv2.imencode(
                    '.jpg', self.superposed_frame)
                self.frame = self.buffer.tobytes()
            else:
                self.frame = None
            time.sleep(0.1)


# Init Alignment check thread
alignment_check_thread = AlignmentCheckThread()

# Thread to close the warning windows from LockInCamera


class ClearPopupThread(threading.Thread):
    def __init__(self, window_name, button_name, quit_event):
        threading.Thread.__init__(self)
        self.quit_event = quit_event
        self.window_name = window_name
        self.button_name = button_name

    def run(self):
        from pywinauto import application, findwindows
        while True:
            try:
                handles = findwindows.find_windows(title=self.window_name)
            except findwindows.WindowNotFoundError:
                pass  # Just do nothing if the pop-up dialog was not found
            else:  # The window was found, so click the button
                for hwnd in handles:
                    app = application.Application()
                    app.connect(handle=hwnd)
                    popup = app[self.window_name]
                    button = getattr(popup, self.button_name)
                    button.click()
            if self.quit_event.is_set():
                break
            # should help reduce cpu load a little for this thread
            time.sleep(1)


quit_event = threading.Event()


# Create an instance of the API
app = Flask(__name__)
api = Api(app)

trajectories = {}
cmos_streaming = {}  # .mp4 ?
helicam_streaming = {}  # .npy + meta ?
sem_images = {}


@ app.route("/")
def index():
    """Present some documentation"""

    # Open the README file
    with open(os.path.dirname(app.root_path) + '/README.md', 'r') as markdown_file:

        # Read the content of the file
        content = markdown_file.read()

        # Convert to HTML
        return markdown.markdown(content)


class DeviceList(Resource):
    def get(self):
        return {'message': 'Success', 'data': devices}, 200

    def post(self):
        parser = reqparse.RequestParser()

        parser.add_argument('name', required=True, type=str,
                            help='name cannot be left blank')
        parser.add_argument('id', required=True, type=int,
                            help='id cannot be left blank')
        parser.add_argument('device_type', required=True,
                            type=str, help='device_type cannot be left blank')
        parser.add_argument('port', required=True,
                            type=str, help='port cannot be left blank')
        parser.add_argument('connected', required=False,
                            default=False, type=bool)
        parser.add_argument('settings', required=False, default={}, type=dict)

        # Parse the arguments into an object
        args = parser.parse_args()
        device = {
            "id": args["id"],
            "device_type": args["device_type"],
            "port": args["port"],
            "connected": args["connected"],
            "settings": args["settings"],
        }
        devices[args["name"]] = device

        return {'message': 'Device registered', 'data': device}, 201


class Device(Resource):
    def get(self, name):
        # If the key does not exist in the data store, return a 404 error.
        if not (name in devices):
            return {'message': 'Device not found', 'data': {}}, 404

        return {'message': 'Device found', 'data': devices[name]}, 200

    def delete(self, name):
        # If the key does not exist in the data store, return a 404 error.
        if not (name in devices):
            return {'message': 'Device not found', 'data': {}}, 404

        del devices[name]
        return '', 204


def cmoscamera_frames():
    while True:
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + cmos_camera_thread.frame + b'\r\n')  # concat frame one by one and show result

        time.sleep(0.05)


class CMOSCamera(Resource):
    def get(self):
        return Response(cmoscamera_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


def lockincamera_frames():
    while True:
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + lock_in_camera_thread.frame + b'\r\n')

        time.sleep(0.05)


class LockInCamera(Resource):
    def get(self):
        return Response(lockincamera_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


def sem_frames():
    yield (b'--frame\r\n'
           b'Content-Type: image/jpeg\r\n\r\n' + sem_image_frame + b'\r\n')


class SEMImages(Resource):
    def get(self):
        return Response(sem_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


def alignment_check_frames():
    while True:
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + alignment_check_thread.frame + b'\r\n')

        time.sleep(0.05)


class AlignmentCheck(Resource):
    def get(self):
        return Response(alignment_check_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


class AlignmentSettings(Resource):
    def get(self):
        return {'message': 'Success', 'data': alignment_settings}, 200


class AlignmentSetting(Resource):
    def get(self, name):
        return {'message': 'Success', 'data': alignment_settings[name]}, 200

    def post(self, name):
        parser = reqparse.RequestParser()

        parser.add_argument('point_idx', required=True, type=int,
                            help='point index cannot be left blank')
        parser.add_argument('x', required=True, type=float,
                            help='x coord cannot be left blank')
        parser.add_argument('y', required=True, type=float,
                            help='y coord cannot be left blank')

        # Parse the arguments into an object
        args = parser.parse_args()

        # Update alignment settings
        new_coord = (args['x'], args['y'])
        alignment_settings[name][args["point_idx"]] = new_coord

        # Update projective matrix
        camera_res = 960
        sem_image_height = 500
        sem_image_width = 500
        src_points = np.float32(np.int32(np.array(
            alignment_settings["cmos-camera-marks"]) * camera_res))
        dst_points = np.float32(np.int32(np.array(
            alignment_settings["sem-image-marks"]) * [sem_image_width, sem_image_height]))
        cmos_camera_thread.image_transformer.update_projective_matrix(
            src_points, dst_points)

        return {'message': 'Alignment settings changed', 'data': alignment_settings[name]}, 201


api.add_resource(DeviceList, '/devices')
api.add_resource(Device, '/device/<string:name>')
api.add_resource(AlignmentSettings, '/alignment-settings')
api.add_resource(AlignmentSetting, '/alignment-setting/<string:name>')
api.add_resource(CMOSCamera, '/cmos-camera/feed')
api.add_resource(LockInCamera, '/lock-in-camera/feed')
api.add_resource(SEMImages, '/sem-images/feed')
api.add_resource(AlignmentCheck, '/alignment-check/feed')


if __name__ == "__main__":
    sem_image = cv2.imread('./sem/data/gb-map-sample-1.png')
    sem_image_frame = cv2.imencode('.jpg', sem_image)[1].tobytes()
    mythread = ClearPopupThread('libHeLIC:Warning', 'OK', quit_event)
    # close windows warning popup
    mythread.start()
    cmos_camera_thread.start()
    lock_in_camera_thread.start()
    alignment_check_thread.start()

    app.run(host='0.0.0.0', port=80, debug=False, use_reloader=False)
