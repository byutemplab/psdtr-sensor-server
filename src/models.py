from tinydb import TinyDB, Query

# Initialize db
alignment_settings_db = TinyDB('db/alignment-settings.json')
alignment_items = Query()

# TODO: how to store streaming data in db?
trajectories = {}
cmos_streaming = {}  # .mp4 ?
helicam_streaming = {}  # .npy + meta ?
sem_images = {}

# Projected frames
projected_frames = {
    "cmos-camera": None,
    "lock-in-camera": None,
    "sem-image": None,
}

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
