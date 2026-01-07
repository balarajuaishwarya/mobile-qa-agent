import subprocess
import time
import io
from typing import Optional, Tuple
from PIL import Image
import config


class ADBInterface:
    """Manages ADB commands for Android device control"""
    
    def __init__(self, device_id: Optional[str] = None):
        """
        Initialize ADB interface
        
        Args:
            device_id: Specific device ID (e.g., "emulator-5554") 
        """
        self.device_id = device_id 
        self._screen_size_cache = None
        
        # Verify ADB is available
        if not self._check_adb():
            raise RuntimeError("ADB not found in PATH")
        
        # Verify device is connected
        if not self._check_device():
            raise RuntimeError(f"Device not found: {self.device_id or 'any'}")
    
    def _check_adb(self) -> bool:
        """Check if ADB is available"""
        try:
            subprocess.run(['adb', 'version'], capture_output=True, timeout=5)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def _check_device(self) -> bool:
        """Check if device is connected"""
        try:
            result = self._run(['devices'])
            if result and result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                devices = [line for line in lines if '\tdevice' in line]
                return len(devices) > 0
        except:
            pass
        return False
    
    def _run(self, command: list, timeout: int = None) -> Optional[subprocess.CompletedProcess]:
        """
        Execute an ADB command
        
        Args:
            command: ADB command parts (without 'adb' prefix)
            timeout: Command timeout in seconds
            
        Returns:
            CompletedProcess or None on failure
        """
        cmd = ['adb']
        if self.device_id:
            cmd.extend(['-s', self.device_id])
        cmd.extend(command)
        
        try:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout or config.ADB_TIMEOUT
            )
        except subprocess.TimeoutExpired:
            print(f"  ADB command timeout: {' '.join(command)}")
            return None
        except Exception as e:
            print(f"  ADB error: {e}")
            return None
    
    def get_screen_size(self) -> Tuple[int, int]:
        """
        Get device screen dimensions
        
        Returns:
            Tuple of (width, height) in pixels
        """
        # Use cached value if available
        if config.CACHE_SCREEN_SIZE and self._screen_size_cache:
            return self._screen_size_cache
        
        result = self._run(['shell', 'wm', 'size'])
        if result and result.returncode == 0:
            try:
                # Parse "Physical size: 1080x2400"
                size_str = result.stdout.strip().split(': ')[-1]
                width, height = map(int, size_str.split('x'))
                
                self._screen_size_cache = (width, height)
                return (width, height)
            except:
                pass
        
        print(f"  Using default screen size: {config.DEFAULT_SCREEN_SIZE}")
        return config.DEFAULT_SCREEN_SIZE
    
    def get_screenshot(self) -> Optional[Image.Image]:
        """
        Capture screenshot from device
        
        Returns:
            PIL Image object or None on failure
        """
        try:
            cmd = ['adb']
            if self.device_id:
                cmd.extend(['-s', self.device_id])
            cmd.extend(['exec-out', 'screencap', '-p'])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=config.ADB_TIMEOUT
            )
            
            if result.returncode == 0:
                image = Image.open(io.BytesIO(result.stdout))
                
                # Optimize image size if configured
                if config.COMPRESS_IMAGES:
                    image = self._optimize_image(image)
                
                time.sleep(config.SCREENSHOT_DELAY)
                return image
                
        except Exception as e:
            print(f"  Screenshot failed: {e}")
        
        return None
    
    def _optimize_image(self, image: Image.Image) -> Image.Image:
        """Resize and compress image for faster API calls"""
        width, height = image.size
        max_dim = config.MAX_IMAGE_DIMENSION
        
        if width > max_dim or height > max_dim:
            # Maintain aspect ratio
            if width > height:
                new_width = max_dim
                new_height = int(height * (max_dim / width))
            else:
                new_height = max_dim
                new_width = int(width * (max_dim / height))
            
            image = image.resize((new_width, new_height), Image.LANCZOS)
        
        return image
    
    def tap(self, x: int, y: int) -> bool:
        """
        Tap at specific screen coordinates
        
        Args:
            x, y: Pixel coordinates
            
        Returns:
            True if successful
        """
        if x is None or y is None or x < 0 or y < 0:
            print(f"  Invalid tap coordinates: ({x}, {y})")
            return False
        
        result = self._run(['shell', 'input', 'tap', str(int(x)), str(int(y))])
        time.sleep(config.ACTION_DELAY)
        return result is not None and result.returncode == 0
    
    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, 
              duration: int = 300) -> bool:
        """
        Swipe gesture
        
        Args:
            start_x, start_y: Starting coordinates
            end_x, end_y: Ending coordinates
            duration: Swipe duration in milliseconds
            
        Returns:
            True if successful
        """
        coords = [start_x, start_y, end_x, end_y]
        if any(c is None or c < 0 for c in coords):
            print(f"  Invalid swipe coordinates")
            return False
        
        result = self._run([
            'shell', 'input', 'swipe',
            str(int(start_x)), str(int(start_y)),
            str(int(end_x)), str(int(end_y)),
            str(duration)
        ])
        time.sleep(config.ACTION_DELAY)
        return result is not None and result.returncode == 0
    
    def type_text(self, text: str) -> bool:
        """
        Type text (spaces become %s for ADB compatibility)
        
        Args:
            text: Text to type
            
        Returns:
            True if successful
        """
        if not text:
            return False
        
        # Clean and format text for ADB
        formatted = str(text).replace(' ', '%s').replace("'", "").replace('"', '')
        
        result = self._run(['shell', 'input', 'text', formatted])
        time.sleep(config.ACTION_DELAY * 0.5)
        return result is not None and result.returncode == 0
    
    def press_key(self, key: str) -> bool:
        """
        Press a key by name or keycode
        
        Args:
            key: Key name (enter, back, home) or keycode number
            
        Returns:
            True if successful
        """
        key_map = {
            'enter': 66,
            'back': 4,
            'home': 3,
            'backspace': 67,
            'menu': 82
        }
        
        # Convert name to keycode
        keycode = key_map.get(str(key).lower(), key)
        
        result = self._run(['shell', 'input', 'keyevent', str(keycode)])
        time.sleep(config.ACTION_DELAY * 0.5)
        return result is not None and result.returncode == 0
    
    def launch_app(self, package: str) -> bool:
        """
        Launch an app by package name
        
        Args:
            package: App package name (e.g., "md.obsidian")
            
        Returns:
            True if successful
        """
        result = self._run([
            'shell', 'monkey', '-p', package,
            '-c', 'android.intent.category.LAUNCHER', '1'
        ])
        time.sleep(config.APP_LAUNCH_WAIT)
        return result is not None and result.returncode == 0
    
    def is_screen_on(self) -> bool:
        """Check if device screen is on"""
        result = self._run(['shell', 'dumpsys', 'power'])
        if result and result.returncode == 0:
            return 'Display Power: state=ON' in result.stdout
        return False
    
    def wake_device(self) -> bool:
        """Wake device if screen is off"""
        if not self.is_screen_on():
            self.press_key(26)  # Power button
            time.sleep(1)
            self.press_key(82)  # Menu to unlock
            time.sleep(1)
            return True
        return False
