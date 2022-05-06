import markdown
import os
import cv2
import time
import threading
from cmoscamera.camerastream import CMOSCameraFeed
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

LOCK_IN_CAMERA_CONNECTED = True

# Import image placeholder
no_image_placeholder = cv2.imencode('.jpg', cv2.imread(
    './assets/no_image_placeholder.png'))[1].tobytes()

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
        frame = cmos_camera_thread.frame if cmos_camera_thread.camera.connected else no_image_placeholder
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

        time.sleep(0.05)


class CMOSCameraFeed(Resource):
    def get(self):
        return Response(cmoscamera_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


def lockincamera_frames():
    while True:
        if LOCK_IN_CAMERA_CONNECTED:
            frame = lock_in_camera_thread.frame if lock_in_camera_thread.camera.connected else no_image_placeholder
        else:
            frame = no_image_placeholder
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

        time.sleep(0.05)


class CMOSCameraSettings(Resource):
    def get(self):
        settings = devices_db.search(
            devices_list.name == "cmos-camera")[0]["settings"]
        return {'message': 'Success', 'data': settings}, 200

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('exposure', type=int,
                            location='args', required=True)
        parser.add_argument('gain', type=int,  location='args', required=True)
        parser.add_argument('brightness', type=int,
                            location='args', required=True)

        # Parse the arguments
        args = parser.parse_args()

        # TODO: Validate the arguments
        # exposure 10 - 500000 (ms)
        if (args['exposure'] < 10 or args['exposure'] > 500000):
            return {'message': 'Exposure must be between 10 and 500000', 'data': {}}, 404
        # gain 0 - 100
        if (args['gain'] < 0 or args['gain'] > 100):
            return {'message': 'Gain must be between 0 and 100', 'data': {}}, 404
        # brightness 0 - 100
        if (args['brightness'] < 0 or args['brightness'] > 100):
            return {'message': 'Brightness must be between 0 and 100', 'data': {}}, 404

        # Update the settings in db
        updated_settings = devices_db.search(
            devices_list.name == "cmos-camera")[0]["settings"]
        updated_settings["exposure"] = args["exposure"]
        updated_settings["gain"] = args["gain"]
        updated_settings["brightness"] = args["brightness"]
        devices_db.update({"settings": updated_settings},
                          devices_list.name == "cmos-camera")

        # Update the settings in the camera
        cmos_camera_thread.camera.UpdateSettings(updated_settings)

        return {'message': 'Success', 'data': updated_settings}, 200


class LockInCamera(Resource):
    def get(self):
        return Response(lockincamera_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


def sem_frames():
    yield (b'--frame\r\n'
           b'Content-Type: image/jpeg\r\n\r\n' + sem_image_frame + b'\r\n')


class LockInCameraConnect(Resource):
    def post(self):
        # try to connect if not already connected
        if LOCK_IN_CAMERA_CONNECTED and not lock_in_camera_thread.camera.connected:
            lock_in_camera_thread.camera.Connect()
            if lock_in_camera_thread.camera.connected:
                return {'message': 'Connected lock-in camera', 'data': {}}, 200
            else:
                return {'message': 'Failed to connect lock-in camera', 'data': {}}, 400
        # if already connected, return error
        return {'message': 'Lock-in Camera already connected', 'data': {}}, 404


class SEMImages(Resource):
    def get(self):
        return Response(sem_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


def alignment_check_frames():
    while True:
        if LOCK_IN_CAMERA_CONNECTED:
            frame = alignment_check_thread.frame if (
                lock_in_camera_thread.camera.connected and cmos_camera_thread.camera.connected) else no_image_placeholder
        else:
            frame = alignment_check_thread.frame if cmos_camera_thread.camera.connected else no_image_placeholder
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

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


class TrajectoriesSettingPattern(Resource):
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

        parser.add_argument('start_x', required=True, type=float, location='args',
                            help='Trajectory start x coordinate cannot be blank')
        parser.add_argument('start_y', required=True, type=float, location='args',
                            help='Trajectory start y coordinate cannot be blank')
        parser.add_argument('end_x', required=True, type=float, location='args',
                            help='Trajectory end x coordinate cannot be blank')
        parser.add_argument('end_y', required=True, type=float, location='args',
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

        # Update trajectories
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

        parser.add_argument('start_x', required=True, type=float, location='args',
                            help='Trajectory start x coordinate cannot be blank')
        parser.add_argument('start_y', required=True, type=float, location='args',
                            help='Trajectory start y coordinate cannot be blank')
        parser.add_argument('end_x', required=True, type=float, location='args',
                            help='Trajectory end x coordinate cannot be blank')
        parser.add_argument('end_y', required=True, type=float, location='args',
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


class TrajectoriesSettingNumberOfMeasurements(Resource):
    def post(self, name):
        parser = reqparse.RequestParser()

        parser.add_argument('number_of_measurements', required=True, type=int, location='args',
                            help='Number of measurements cannot be blank')

        # Parse the arguments into an object
        args = parser.parse_args()

        # Validate the arguments
        if args["number_of_measurements"] < 0:
            return {'message': 'Number of measurements must be greater than 0', 'data': {}}, 404
        trajectories_setting = trajectories_db.search(
            trajectories_list.name == name)[0]
        if (trajectories_setting is None):
            return {'message': 'Trajectories setting not found', 'data': {}}, 404

        # Update number of measurements
        updated_number_of_measurements = int(args["number_of_measurements"])
        trajectories_db.update(
            {'number-of-measurements': updated_number_of_measurements}, trajectories_list.name == name)

        return {'message': 'Number of measurements changed', 'data': args['number_of_measurements']}, 201


class TrajectoriesSettingMeasurementTime(Resource):
    def post(self, name):
        parser = reqparse.RequestParser()

        parser.add_argument('measurement_time', required=True, type=int, location='args',
                            help='Measurement time cannot be blank')

        # Parse the arguments into an object
        args = parser.parse_args()

        # Validate the arguments
        if args["measurement_time"] < 0:
            return {'message': 'Measurement time must be greater than 0', 'data': {}}, 404
        trajectories_setting = trajectories_db.search(
            trajectories_list.name == name)[0]
        if (trajectories_setting is None):
            return {'message': 'Trajectories setting not found', 'data': {}}, 404

        # Update measurement time
        updated_measurement_time = int(args["measurement_time"])
        trajectories_db.update(
            {'measurement-time': updated_measurement_time}, trajectories_list.name == name)

        return {'message': 'Measurement time changed', 'data': args['measurement_time']}, 201


class TrajectoriesSettingGreenPointDiameter(Resource):
    def post(self, name):
        parser = reqparse.RequestParser()

        parser.add_argument('green_point_diameter', required=True, type=int, location='args',
                            help='Green point diameter cannot be blank')

        # Parse the arguments into an object
        args = parser.parse_args()

        # Validate the arguments
        if args["green_point_diameter"] < 0:
            return {'message': 'Green point diameter must be greater than 0', 'data': {}}, 404
        trajectories_setting = trajectories_db.search(
            trajectories_list.name == name)[0]
        if (trajectories_setting is None):
            return {'message': 'Trajectories setting not found', 'data': {}}, 404

        # Update green point diameter
        updated_green_point_diameter = int(args["green_point_diameter"])
        trajectories_db.update(
            {'green-point-diameter': updated_green_point_diameter}, trajectories_list.name == name)

        return {'message': 'Green point diameter changed', 'data': args['green_point_diameter']}, 201


class TrajectoriesSettingLaserPointDiameter(Resource):
    def post(self, name):
        parser = reqparse.RequestParser()

        parser.add_argument('laser_point_diameter', required=True, type=int, location='args',
                            help='Laser point diameter cannot be blank')

        # Parse the arguments into an object
        args = parser.parse_args()

        # Validate the arguments
        if args["laser_point_diameter"] < 0:
            return {'message': 'Laser point diameter must be greater than 0', 'data': {}}, 404
        trajectories_setting = trajectories_db.search(
            trajectories_list.name == name)[0]
        if (trajectories_setting is None):
            return {'message': 'Trajectories setting not found', 'data': {}}, 404

        # Update laser point diameter
        updated_laser_point_diameter = int(args["laser_point_diameter"])
        trajectories_db.update(
            {'laser-point-diameter': updated_laser_point_diameter}, trajectories_list.name == name)

        return {'message': 'Laser point diameter changed', 'data': args['laser_point_diameter']}, 201


class AlignmentSetting(Resource):
    def get(self, name):
        alignment_setting = alignment_settings_db.search(alignment_items.name == name)[
            0]
        return {'message': 'Success', 'data': alignment_setting}, 200

    def post(self, name):
        parser = reqparse.RequestParser()

        parser.add_argument('point_idx', required=True, type=int, location='args',
                            help='point index cannot be left blank')
        parser.add_argument('x', required=True, type=float, location='args',
                            help='x coord cannot be left blank')
        parser.add_argument('y', required=True, type=float, location='args',
                            help='y coord cannot be left blank')

        # Parse the arguments into an object
        args = parser.parse_args()

        # Validate the arguments
        if (alignment_settings_db.search(alignment_items.name == name) == []):
            return {'message': 'Alignment setting not found', 'data': {}}, 404
        if args["point_idx"] < 0 or args["point_idx"] > 3:
            return {'message': 'Point index must be between 0 and 3', 'data': {}}, 404
        if args["x"] < 0 or args["x"] > 1:
            return {'message': 'X coord must be between 0 and 1', 'data': {}}, 404
        if args["y"] < 0 or args["y"] > 1:
            return {'message': 'Y coord must be between 0 and 1', 'data': {}}, 404

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


class ProjectorBoxSetting(Resource):
    def get(self, name):
        projector_box_setting = alignment_settings_db.search(alignment_items.name == name)[
            0]
        return {'message': 'Success', 'data': projector_box_setting}, 200

    def post(self, name):
        parser = reqparse.RequestParser()

        parser.add_argument('x_offset', required=True, type=float, location='args',
                            help='x offset cannot be left blank')
        parser.add_argument('y_offset', required=True, type=float, location='args',
                            help='y offset cannot be left blank')
        parser.add_argument('side_length', required=True, type=float, location='args',
                            help='side length cannot be left blank')

        # Parse the arguments into an object
        args = parser.parse_args()

        # Validate the arguments
        projector_box_setting = alignment_settings_db.search(
            alignment_items.name == name)[0]
        if (projector_box_setting is None):
            return {'message': 'Projector box setting not found', 'data': {}}, 404
        if args["x_offset"] < -1 or args["x_offset"] > 1:
            return {'message': 'X offset must be between 0 and 1', 'data': {}}, 404
        if args["y_offset"] < -1 or args["y_offset"] > 1:
            return {'message': 'Y offset must be between 0 and 1', 'data': {}}, 404
        if args["side_length"] < 0 or args["side_length"] > 1:
            return {'message': 'Side length must be between 0 and 1', 'data': {}}, 404
        if 0.5 + args["side_length"] / 2 + args["x_offset"] > 1 or 0.5 - args["side_length"] / 2 + args["x_offset"] < 0:
            return {'message': 'Box is out of bounds', 'data': {}}, 404
        if 0.5 + args["side_length"] / 2 + args["y_offset"] > 1 or 0.5 - args["side_length"] / 2 + args["y_offset"] < 0:
            return {'message': 'Box is out of bounds', 'data': {}}, 404

        # Update projector box settings
        alignment_settings_db.update(
            {'x-offset': args['x_offset'],
             'y-offset': args['y_offset'],
             'side-length': args['side_length']
             }, alignment_items.name == name)

        updated_projector_box_setting = alignment_settings_db.search(
            alignment_items.name == name)[0]

        # TODO: Update projective matrix

        return {'message': 'Projector box settings changed', 'data': updated_projector_box_setting}, 200


class GreenProjectorSetPattern(Resource):
    def post(self, trajectories_setting_name):
        trajectories_setting = trajectories_db.search(
            trajectories_list.name == trajectories_setting_name)[0]
        pattern_set = green_projector_thread.SendPattern(trajectories_setting)

        if(pattern_set):
            return {'message': 'Pattern set in green projector', 'data': {}}, 200
        else:
            return {'message': 'Failed to set pattern in green projector', 'data': {}}, 400


class GreenProjectorSetBox(Resource):
    def post(self):
        box_setting = alignment_settings_db.search(
            alignment_items.name == 'green-projector-box')[0]
        box_set = green_projector_thread.SendBox(box_setting)

        if(box_set):
            return {'message': 'Box set in green projector', 'data': {}}, 200
        else:
            return {'message': 'Failed to set box in green projector', 'data': {}}, 400


api.add_resource(DeviceList, '/devices')
api.add_resource(Device, '/device/<string:name>')
api.add_resource(AlignmentSettings, '/alignment-settings')
api.add_resource(Trajectories, '/trajectories')
api.add_resource(TrajectoriesSettingPattern,
                 '/trajectories-setting/<string:name>/<int:trajectory_idx>')
api.add_resource(TrajectoriesSettingNumberOfMeasurements,
                 '/trajectories-setting/<string:name>/number-of-measurements')
api.add_resource(TrajectoriesSettingMeasurementTime,
                 '/trajectories-setting/<string:name>/measurement-time')
api.add_resource(TrajectoriesSettingGreenPointDiameter,
                 '/trajectories-setting/<string:name>/green-point-diameter')
api.add_resource(TrajectoriesSettingLaserPointDiameter,
                 '/trajectories-setting/<string:name>/laser-point-diameter')
api.add_resource(AlignmentSetting, '/alignment-setting/<string:name>')
api.add_resource(ProjectorBoxSetting, '/projector-box-setting/<string:name>')
api.add_resource(CMOSCameraFeed, '/cmos-camera/feed')
api.add_resource(CMOSCameraSettings, '/cmos-camera/settings')
api.add_resource(LockInCamera, '/lock-in-camera/feed')
api.add_resource(LockInCameraConnect, '/lock-in-camera/connect')
api.add_resource(SEMImages, '/sem-images/feed')
api.add_resource(AlignmentCheck, '/alignment-check/feed')
api.add_resource(GreenProjectorSetPattern,
                 '/green-projector/set-pattern/<string:trajectories_setting_name>')
# api.add_resource(LaserProjectorSetPattern,
#                  '/laser-projector/set-pattern/<string:trajectories_setting_name>')
api.add_resource(GreenProjectorSetBox,
                 '/green-projector/set-box')


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
    # laser_projector_thread = ProjectorThread('laser-projector', 1)
    # laser_projector_thread.start()
    green_projector_thread = ProjectorThread('green-projector', 1)
    green_projector_thread.start()

    app.run(host='0.0.0.0', port=80, debug=False, use_reloader=False)
