"""
ADB Tools for Android Emulator Control
"""
import subprocess
import time
from PIL import Image
import io
import os


class ADBTools:
    def __init__(self, device_id=None):
        self.device_id = device_id
        self.screenshot_dir = "screenshots"
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
    def _run_adb_command(self, command):
        """Run ADB command and return output"""
        if self.device_id:
            cmd = ['adb', '-s', self.device_id] + command
        else:
            cmd = ['adb'] + command
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            return "", "Command timed out", 1
    
    def get_screenshot(self, save_path=None):
        """Take screenshot and return PIL Image"""
        try:
            cmd = ['adb', 'exec-out', 'screencap', '-p']
            if self.device_id:
                cmd = ['adb', '-s', self.device_id, 'exec-out', 'screencap', '-p']
            
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            img = Image.open(io.BytesIO(result.stdout))
            
            if save_path:
                img.save(save_path)
            
            return img
        except Exception as e:
            print(f"Error taking screenshot: {e}")
            return None
    
    def tap(self, x, y):
        """Tap at specific coordinates"""
        stdout, stderr, code = self._run_adb_command(['shell', 'input', 'tap', str(x), str(y)])
        time.sleep(1)  # Wait for UI to respond
        return code == 0
    
    def swipe(self, start_x, start_y, end_x, end_y, duration=300):
        """Swipe from start to end coordinates"""
        stdout, stderr, code = self._run_adb_command([
            'shell', 'input', 'swipe', 
            str(start_x), str(start_y), 
            str(end_x), str(end_y), 
            str(duration)
        ])
        time.sleep(1)
        return code == 0
    
    def type_text(self, text):
        """Type text (spaces become %s)"""
        text = text.replace(' ', '%s')
        stdout, stderr, code = self._run_adb_command(['shell', 'input', 'text', text])
        time.sleep(0.5)
        return code == 0
    
    def press_key(self, keycode):
        """Press a key by keycode
        Common keycodes:
        - BACK: 4
        - HOME: 3
        - ENTER: 66
        - BACKSPACE: 67
        """
        stdout, stderr, code = self._run_adb_command(['shell', 'input', 'keyevent', str(keycode)])
        time.sleep(0.5)
        return code == 0
    
    def press_back(self):
        """Press back button"""
        return self.press_key(4)
    
    def press_home(self):
        """Press home button"""
        return self.press_key(3)
    
    def press_enter(self):
        """Press enter button"""
        return self.press_key(66)
    
    def clear_text(self, num_chars=50):
        """Clear text by pressing backspace multiple times"""
        for _ in range(num_chars):
            self.press_key(67)  # Backspace
        time.sleep(0.5)
        return True
    
    def get_screen_size(self):
        """Get screen dimensions"""
        stdout, stderr, code = self._run_adb_command(['shell', 'wm', 'size'])
        if code == 0 and stdout:
            # Parse "Physical size: 1080x2400"
            size_str = stdout.strip().split(': ')[-1]
            width, height = map(int, size_str.split('x'))
            return width, height
        return 1080, 2400  # Default
    
    def launch_app(self, package_name):
        """Launch app by package name"""
        stdout, stderr, code = self._run_adb_command([
            'shell', 'monkey', '-p', package_name, '-c', 
            'android.intent.category.LAUNCHER', '1'
        ])
        time.sleep(2)
        return code == 0
    
    def get_current_activity(self):
        """Get current activity name"""
        stdout, stderr, code = self._run_adb_command([
            'shell', 'dumpsys', 'window', 'windows', '|', 'grep', '-E', 'mCurrentFocus'
        ])
        return stdout.strip()
    
    def wait_for_ui(self, seconds=2):
        """Wait for UI to settle"""
        time.sleep(seconds)