"""ADB Tools - Fixed version"""
import subprocess
import time
import io
from PIL import Image


class ADBTools:
    def __init__(self, device_id=None):
        self.device_id = device_id
        
    def _run(self, command):
        prefix = ['adb', '-s', self.device_id] if self.device_id else ['adb']
        cmd = prefix + command
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        except subprocess.TimeoutExpired:
            print(" ADB command timeout")
            return None

    def get_screenshot(self):
        """Fixed: Better error handling"""
        try:
            cmd = ['adb', 'exec-out', 'screencap', '-p']
            if self.device_id:
                cmd = ['adb', '-s', self.device_id, 'exec-out', 'screencap', '-p']
            res = subprocess.run(cmd, capture_output=True, timeout=10)
            return Image.open(io.BytesIO(res.stdout))
        except Exception as e:
            print(f" Screenshot failed: {e}")
            return None

    def tap(self, x, y):
        """Fixed: Validate coordinates"""
        if x is None or y is None:
            print(" Invalid tap coordinates")
            return
        self._run(['shell', 'input', 'tap', str(int(x)), str(int(y))])
        time.sleep(1.5)  # Increased for reliability

    def type_text(self, text):
        """Fixed: Better text handling"""
        if not text:
            return
        text = str(text).replace(' ', '%s').replace("'", "").replace('"', '')
        self._run(['shell', 'input', 'text', text])
        time.sleep(0.5)

    def press_key(self, key):
        """Fixed: Key mapping"""
        key_map = {
            'enter': 66,
            'back': 4,
            'home': 3,
            'backspace': 67
        }
        keycode = key_map.get(str(key).lower(), key)
        self._run(['shell', 'input', 'keyevent', str(keycode)])
        time.sleep(0.5)

    def swipe(self, start_x, start_y, end_x, end_y, duration=300):
        """Fixed: Validate swipe params"""
        if None in [start_x, start_y, end_x, end_y]:
            print(" Invalid swipe coordinates")
            return
        self._run(['shell', 'input', 'swipe', 
                   str(int(start_x)), str(int(start_y)), 
                   str(int(end_x)), str(int(end_y)), 
                   str(duration)])
        time.sleep(1)

    def get_screen_size(self):
        """Fixed: Return tuple properly"""
        res = self._run(['shell', 'wm', 'size'])
        if res and res.stdout:
            size_str = res.stdout.strip().split(': ')[-1]
            w, h = size_str.split('x')
            return int(w), int(h)
        return 1080, 2400  # Default

    def launch_app(self, package):
        self._run(['shell', 'monkey', '-p', package, '-c', 
                   'android.intent.category.LAUNCHER', '1'])
        time.sleep(3)

    def press_home(self):
        """Added: Home button"""
        self.press_key(3)