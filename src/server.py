import markdown
import os
import cv2
import time
import threading
from cmoscamera.camerastream import CMOSCamera
from lockincamera.camerastream import LockInCamera
from models import alignment_settings_db, alignment_items
from models import devices_db, devices_list
from models import trajectories_db, trajectories_list
from models import projected_frames
from clear_popup_thread import ClearPopupThread
from cmos_camera_thread import CMOSCameraThread
from lock_in_camera_thread import LockInCameraThread
from alignment_check_thread import AlignmentCheckThread
from projectors_thread import ProjectorThread
from flask import Flask, Response
from flask_restful import Resource, Api, reqparse

LOCK_IN_CAMERA_CONNECTED = False

# Create an instance of the API
app = Flask(__name__)
api = Api(app)


@ app.route("/")
def index():
    with open(os.path.dirname(app.root_path) + '/README.md', 'r') as markdown_file:
        # Read the content of the file
        content = markdown_file.read()
        # Convert to HTML
        return markdown.markdown(content)


class DeviceList(Resource):
    def get(self):
        return {'message': 'Success', 'data': devices_db.all()}, 200


class Device(Resource):
    def get(self, name):
        device = devices_db.search(devices_list.name == name)[0]

        if (device is None):
            return {'message': 'Device not found', 'data': {}}, 404

        return {'message': 'Device found', 'data': device}, 200


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
        return {'message': 'Success', 'data': alignment_settings_db.all()}, 200


class Trajectories(Resource):
    def get(self):
        return {'message': 'Success', 'data': trajectories_db.all()}, 200


class TrajectoriesSetting(Resource):
    def get(self, name, trajectory_idx):
        trajectories_setting = trajectories_db.search(
            trajectories_list.name == name)[0]
        if (trajectories_setting is None):
            return {'message': 'Trajectory not found', 'data': {}}, 404
        if trajectory_idx < 0 or trajectory_idx > len(trajectories_setting['trajectories']):
            return {'message': 'Trajectory index out of range', 'data': {}}, 404
        return {'message': 'Success', 'data': trajectories_setting['trajectories'][trajectory_idx]}, 200

    def post(self, name, trajectory_idx):
        parser = reqparse.RequestParser()

        parser.add_argument('start_x', required=True, type=float,
                            help='Trajectory start x coordinate cannot be blank')
        parser.add_argument('start_y', required=True, type=float,
                            help='Trajectory start y coordinate cannot be blank')
        parser.add_argument('end_x', required=True, type=float,
                            help='Trajectory end x coordinate cannot be blank')
        parser.add_argument('end_y', required=True, type=float,
                            help='Trajectory end y coordinate cannot be blank')

        # Parse the arguments into an object
        args = parser.parse_args()

        # Validate the arguments
        trajectories_setting = trajectories_db.search(
            trajectories_list.name == name)[0]
        if (trajectories_setting is None):
            return {'message': 'Trajectory not found', 'data': {}}, 404
        if trajectory_idx < 0 or trajectory_idx > len(trajectories_setting['trajectories']):
            return {'message': 'Trajectory index out of range', 'data': {}}, 404
        if args["start_x"] < 0 or args["start_x"] > 1:
            return {'message': 'Start x coord must be between 0 and 1', 'data': {}}, 404
        if args["start_y"] < 0 or args["start_y"] > 1:
            return {'message': 'Start y coord must be between 0 and 1', 'data': {}}, 404
        if args["end_x"] < 0 or args["end_x"] > 1:
            return {'message': 'End x coord must be between 0 and 1', 'data': {}}, 404
        if args["end_y"] < 0 or args["end_y"] > 1:
            return {'message': 'End y coord must be between 0 and 1', 'data': {}}, 404

        # Update alignment settings
        new_start_coord = (args['start_x'], args['start_y'])
        new_end_coord = (args['end_x'], args['end_y'])
        updated_trajectory = {
            'start': new_start_coord,
            'end': new_end_coord
        }
        updated_trajectories = trajectories_setting['trajectories']
        updated_trajectories[trajectory_idx] = updated_trajectory
        trajectories_db.update(
            {'trajectories': updated_trajectories}, trajectories_list.name == name)

        return {'message': 'Trajectories Setting changed', 'data': updated_trajectory}, 201

    def delete(self, name, trajectory_idx):
        trajectories_setting = trajectories_db.search(
            trajectories_list.name == name)[0]
        if (trajectories_setting is None):
            return {'message': 'Trajectories setting not found', 'data': {}}, 404
        if trajectory_idx < 0 or trajectory_idx > len(trajectories_setting['trajectories']):
            return {'message': 'Trajectory index out of range', 'data': {}}, 404

        updated_trajectories = trajectories_setting['trajectories']
        del updated_trajectories[trajectory_idx]
        trajectories_db.update(
            {'trajectories': updated_trajectories}, trajectories_list.name == name)

        return {'message': 'Trajectory deleted', 'data': {}}, 200

    def put(self, name, trajectory_idx):
        parser = reqparse.RequestParser()

        parser.add_argument('start_x', required=True, type=float,
                            help='Trajectory start x coordinate cannot be blank')
        parser.add_argument('start_y', required=True, type=float,
                            help='Trajectory start y coordinate cannot be blank')
        parser.add_argument('end_x', required=True, type=float,
                            help='Trajectory end x coordinate cannot be blank')
        parser.add_argument('end_y', required=True, type=float,
                            help='Trajectory end y coordinate cannot be blank')

        # Parse the arguments into an object
        args = parser.parse_args()

        # Validate the arguments
        trajectories_setting = trajectories_db.search(
            trajectories_list.name == name)[0]
        if (trajectories_setting is None):
            return {'message': 'Trajectories setting not found', 'data': {}}, 404
        if args["start_x"] < 0 or args["start_x"] > 1:
            return {'message': 'Start x coord must be between 0 and 1', 'data': {}}, 404
        if args["start_y"] < 0 or args["start_y"] > 1:
            return {'message': 'Start y coord must be between 0 and 1', 'data': {}}, 404
        if args["end_x"] < 0 or args["end_x"] > 1:
            return {'message': 'End x coord must be between 0 and 1', 'data': {}}, 404
        if args["end_y"] < 0 or args["end_y"] > 1:
            return {'message': 'End y coord must be between 0 and 1', 'data': {}}, 404

        # Update alignment settings
        start_coord = (args['start_x'], args['start_y'])
        end_coord = (args['end_x'], args['end_y'])
        new_trajectory = {
            'start': start_coord,
            'end': end_coord
        }
        updated_trajectories = trajectories_setting['trajectories']
        updated_trajectories.append(new_trajectory)
        trajectories_db.update(
            {'trajectories': updated_trajectories}, trajectories_list.name == name)

        return {'message': 'Added new trajectory', 'data': new_trajectory}, 201


class AlignmentSetting(Resource):
    def get(self, name):
        alignment_setting = alignment_settings_db.search(alignment_items.name == name)[
            0]
        return {'message': 'Success', 'data': alignment_setting}, 200

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

        # Validate the arguments
        if (alignment_settings_db.search(alignment_items.name == name) == []):
            return {'message': 'Alignment setting not found', 'data': {}}, 404
        if args["point_idx"] < 0 or args["point_idx"] > 3:
            return {'message': 'Point index must be between 0 and 3', 'data': {}}, 400
        if args["x"] < 0 or args["x"] > 1:
            return {'message': 'X coord must be between 0 and 1', 'data': {}}, 400
        if args["y"] < 0 or args["y"] > 1:
            return {'message': 'Y coord must be between 0 and 1', 'data': {}}, 400

        # Update alignment settings
        new_coord = (args['x'], args['y'])
        alignment_setting = alignment_settings_db.search(alignment_items.name == name)[
            0]
        alignment_setting['coordinates'][args["point_idx"]] = new_coord
        new_coordinates = alignment_setting['coordinates']
        alignment_settings_db.update(
            {'coordinates': new_coordinates}, alignment_items.name == name)

        # Update projective matrix
        cmos_camera_thread.image_transformer.update()

        return {'message': 'Alignment settings changed', 'data': alignment_setting}, 201


class LaserProjectorSetPattern(Resource):
    def post(self, trajectories_setting_name):
        trajectories_setting = trajectories_db.search(
            trajectories_list.name == trajectories_setting_name)[0]
        pattern_set = laser_projector_thread.SendPattern(trajectories_setting)

        if(pattern_set):
            return {'message': 'Pattern set in laser projector', 'data': {}}, 200
        else:
            return {'message': 'Failed to set pattern in laser projector', 'data': {}}, 400


api.add_resource(DeviceList, '/devices')
api.add_resource(Device, '/device/<string:name>')
api.add_resource(AlignmentSettings, '/alignment-settings')
api.add_resource(Trajectories, '/trajectories')
api.add_resource(TrajectoriesSetting,
                 '/trajectories-setting/<string:name>/<int:trajectory_idx>')
api.add_resource(AlignmentSetting, '/alignment-setting/<string:name>')
api.add_resource(CMOSCamera, '/cmos-camera/feed')
api.add_resource(LockInCamera, '/lock-in-camera/feed')
api.add_resource(SEMImages, '/sem-images/feed')
api.add_resource(AlignmentCheck, '/alignment-check/feed')
api.add_resource(LaserProjectorSetPattern,
                 '/laser-projector/set-pattern/<string:trajectories_setting_name>')
# api.add_resource(GreenProjectorSetPattern, '/rgb-projector/set-pattern')


if __name__ == "__main__":
    # Get sem image
    projected_frames["sem-image"] = cv2.imread(
        './sem/data/gb-map-sample-1.png')
    sem_image_frame = cv2.imencode('.jpg', projected_frames["sem-image"])[
        1].tobytes()

    # Close windows warning popup
    quit_event = threading.Event()
    mythread = ClearPopupThread('libHeLIC:Warning', 'OK', quit_event)
    mythread.start()

    # Init CMOS Camera
    cmos_camera_thread = CMOSCameraThread()
    cmos_camera_thread.start()

    # Init lock in camera
    if LOCK_IN_CAMERA_CONNECTED:
        lock_in_camera_thread = LockInCameraThread()
        lock_in_camera_thread.start()

    # Init Alignment check thread
    alignment_check_thread = AlignmentCheckThread()
    alignment_check_thread.start()

    # Init Projectors thread
    laser_projector_thread = ProjectorThread('rgb-projector', 1)
    laser_projector_thread.start()
    # rgb_projector_thread = ProjectorThread('rgb-projector', 1)  # TODO
    # rgb_projector_thread.start()

    app.run(host='0.0.0.0', port=80, debug=False, use_reloader=False)
