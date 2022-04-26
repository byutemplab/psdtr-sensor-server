from tinydb import TinyDB, Query

# Initialize db
alignment_settings_db = TinyDB('db/alignment-settings.json')
alignment_items = Query()
devices_db = TinyDB('db/devices.json')
devices_list = Query()
trajectories_db = TinyDB('db/trajectories.json')
trajectories_list = Query()

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
