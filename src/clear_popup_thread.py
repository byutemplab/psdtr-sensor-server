# Thread to close the warning windows from LockInCamera

import time
import threading


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
