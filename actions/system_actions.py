# Nirvan_Assistant/actions/system_actions.py
import subprocess
import webbrowser
import time
import psutil
import pyautogui
import threading
import platform
import logging
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from .common import speak

# Configure logging
logging.basicConfig(filename='system_actions.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Global variables for state management
ACTIVE_MEDIA_PLAYERS = {}
ACTIVE_BROWSER_TABS = {}
MEDIA_CONTROL_LOCK = threading.Lock()
SYSTEM_MONITOR_INTERVAL = 5  # seconds

class SystemActionError(Exception):
    """Base exception for system action errors."""
    pass

class ApplicationNotFoundError(SystemActionError):
    """Raised when application is not found."""
    pass

class ProcessNotFoundError(SystemActionError):
    """Raised when process is not found."""
    pass

class MediaControlError(SystemActionError):
    """Raised when media control fails."""
    pass

class TabManagementError(SystemActionError):
    """Raised when tab management fails."""
    pass

class SystemMonitor(threading.Thread):
    """Background thread to monitor system resources and application states."""
    def __init__(self):
        super().__init__(daemon=True)
        self.running = True
        self.start_time = time.time()
        
    def run(self):
        logging.info("System monitor started")
        while self.running:
            try:
                self._check_browser_tabs()
                self._check_media_players()
                time.sleep(SYSTEM_MONITOR_INTERVAL)
            except Exception as e:
                logging.error(f"System monitor error: {str(e)}")
                
    def _check_browser_tabs(self):
        """Check and clean up closed browser tabs."""
        with MEDIA_CONTROL_LOCK:
            for tab_id, tab_info in list(ACTIVE_BROWSER_TABS.items()):
                if not tab_info['process'].is_running():
                    logging.info(f"Cleaning up closed tab: {tab_info['url']}")
                    ACTIVE_BROWSER_TABS.pop(tab_id, None)
                    
    def _check_media_players(self):
        """Check and clean up closed media players."""
        with MEDIA_CONTROL_LOCK:
            for player_id, player_info in list(ACTIVE_MEDIA_PLAYERS.items()):
                if not player_info['process'].is_running():
                    logging.info(f"Cleaning up closed media player: {player_info['name']}")
                    ACTIVE_MEDIA_PLAYERS.pop(player_id, None)
    
    def stop(self):
        """Stop the monitoring thread."""
        self.running = False
        logging.info("System monitor stopped")

# Start system monitor
SYSTEM_MONITOR = SystemMonitor()
SYSTEM_MONITOR.start()

def _get_platform_key(key_name: str) -> str:
    """Get platform-specific key mapping."""
    key_map = {
        'close_tab': 'command+w' if platform.system() == 'Darwin' else 'ctrl+w',
        'play_pause': 'playpause' if platform.system() == 'Darwin' else 'space',
        'next_track': 'nexttrack' if platform.system() == 'Darwin' else 'nexttrack',
        'alt_tab': 'command+tab' if platform.system() == 'Darwin' else 'alt+tab'
    }
    return key_map.get(key_name, '')

def _find_process_by_name(process_name: str) -> Optional[psutil.Process]:
    """Find a process by name."""
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] == process_name:
            return proc
    return None

def _get_active_window_title() -> str:
    """Get active window title."""
    try:
        if platform.system() == 'Windows':
            import win32gui
            return win32gui.GetWindowText(win32gui.GetForegroundWindow())
        elif platform.system() == 'Darwin':
            from AppKit import NSWorkspace
            return NSWorkspace.sharedWorkspace().activeApplication()['NSApplicationName']
        else:
            # Linux implementation
            return subprocess.check_output(
                ['xdotool', 'getwindowfocus', 'getwindowname']
            ).decode().strip()
    except Exception as e:
        logging.error(f"Error getting active window: {str(e)}")
        return ""

def _activate_window(window_title: str) -> bool:
    """Activate window by title."""
    try:
        if platform.system() == 'Windows':
            import win32gui
            import win32con
            
            def callback(hwnd, extra):
                if window_title.lower() in win32gui.GetWindowText(hwnd).lower():
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(hwnd)
                    return False
                return True
                
            win32gui.EnumWindows(callback, None)
            return True
            
        elif platform.system() == 'Darwin':
            from AppKit import NSWorkspace
            apps = NSWorkspace.sharedWorkspace().runningApplications()
            for app in apps:
                if window_title.lower() in app.localizedName().lower():
                    app.activateWithOptions_(NSWorkspaceLaunchDefault)
                    return True
            return False
            
        else:  # Linux
            subprocess.run(['wmctrl', '-a', window_title])
            return True
            
    except Exception as e:
        logging.error(f"Error activating window: {str(e)}")
        return False

def _simulate_keypress(keys: str) -> bool:
    """Simulate keypress with error handling and delays."""
    try:
        # Human interaction delay
        time.sleep(0.5)
        
        if '+' in keys:
            keys = keys.split('+')
            pyautogui.hotkey(*keys)
        else:
            pyautogui.press(keys)
            
        time.sleep(0.5)  # Post-action delay
        return True
    except Exception as e:
        logging.error(f"Keypress simulation failed: {str(e)}")
        return False

def _register_media_player(player_name: str) -> str:
    """Register a new media player."""
    with MEDIA_CONTROL_LOCK:
        player_id = f"media_{time.time()}"
        try:
            proc = _find_process_by_name(player_name)
            if proc:
                ACTIVE_MEDIA_PLAYERS[player_id] = {
                    'name': player_name,
                    'process': proc,
                    'last_activity': time.time()
                }
                return player_id
        except Exception as e:
            logging.error(f"Error registering media player: {str(e)}")
    return ""

def _register_browser_tab(url: str, browser_name: str) -> str:
    """Register a new browser tab."""
    with MEDIA_CONTROL_LOCK:
        tab_id = f"tab_{time.time()}"
        try:
            proc = _find_process_by_name(browser_name)
            if proc:
                ACTIVE_BROWSER_TABS[tab_id] = {
                    'url': url,
                    'browser': browser_name,
                    'process': proc,
                    'last_accessed': time.time()
                }
                return tab_id
        except Exception as e:
            logging.error(f"Error registering browser tab: {str(e)}")
    return ""

# Application Management Functions
def open_application(app_name: str) -> str:
    """Opens a system application with enhanced error handling."""
    app_map = {
        "chrome": "google chrome",
        "notepad": "notepad.exe" if platform.system() == 'Windows' else "textedit",
        "calculator": "calc.exe" if platform.system() == 'Windows' else "calculator",
        "spotify": "spotify",
        "vlc": "vlc",
        "firefox": "firefox",
        "safari": "safari",
        "edge": "msedge"
    }
    
    normalized_name = app_name.lower()
    command = app_map.get(normalized_name)
    
    if not command:
        msg = f"Application '{app_name}' is not configured"
        logging.warning(msg)
        speak(msg)
        return ""

    try:
        # Try to find existing process first
        existing_proc = _find_process_by_name(command)
        if existing_proc:
            speak(f"{app_name} is already running")
            return ""

        # Launch new process
        if platform.system() == 'Windows':
            subprocess.Popen(command, shell=True)
        else:
            subprocess.Popen([command])
            
        # Wait for application to start
        start_time = time.time()
        while time.time() - start_time < 5:  # 5 second timeout
            if _find_process_by_name(command):
                speak(f"Opening {app_name}")
                
                # Register media player if applicable
                if normalized_name in ['spotify', 'vlc']:
                    return _register_media_player(command)
                    
                return ""
            time.sleep(0.5)
            
        raise ApplicationNotFoundError(f"Timed out waiting for {app_name} to start")
        
    except FileNotFoundError:
        msg = f"Application '{app_name}' not found on system"
        logging.error(msg)
        speak(msg)
    except subprocess.CalledProcessError as e:
        msg = f"Error opening {app_name}: {str(e)}"
        logging.error(msg)
        speak(msg)
    except ApplicationNotFoundError as e:
        msg = str(e)
        logging.error(msg)
        speak(msg)
    except Exception as e:
        msg = f"Unexpected error opening {app_name}: {str(e)}"
        logging.exception(msg)
        speak(msg)
        
    return ""

def close_application(app_name: str) -> bool:
    """Closes a running application."""
    app_map = {
        "chrome": "google chrome",
        "notepad": "notepad.exe" if platform.system() == 'Windows' else "textedit",
        "calculator": "calc.exe" if platform.system() == 'Windows' else "calculator",
        "spotify": "spotify",
        "vlc": "vlc",
        "firefox": "firefox",
        "safari": "safari",
        "edge": "msedge"
    }
    
    normalized_name = app_name.lower()
    command = app_map.get(normalized_name)
    
    if not command:
        msg = f"Application '{app_name}' is not configured for closing"
        logging.warning(msg)
        speak(msg)
        return False

    try:
        proc = _find_process_by_name(command)
        if not proc:
            msg = f"{app_name} is not running"
            logging.info(msg)
            speak(msg)
            return False
            
        proc.terminate()
        
        # Wait for process to terminate
        start_time = time.time()
        while time.time() - start_time < 5:
            if not _find_process_by_name(command):
                speak(f"Closed {app_name}")
                
                # Clean up media players
                with MEDIA_CONTROL_LOCK:
                    for player_id, player_info in list(ACTIVE_MEDIA_PLAYERS.items()):
                        if player_info['name'] == command:
                            ACTIVE_MEDIA_PLAYERS.pop(player_id, None)
                return True
            time.sleep(0.5)
            
        raise ProcessNotFoundError(f"Failed to terminate {app_name}")
        
    except psutil.NoSuchProcess:
        msg = f"{app_name} was already closed"
        logging.info(msg)
        speak(msg)
        return True
    except ProcessNotFoundError as e:
        msg = str(e)
        logging.error(msg)
        speak(msg)
    except Exception as e:
        msg = f"Error closing {app_name}: {str(e)}"
        logging.exception(msg)
        speak(msg)
        
    return False

# Browser Management Functions
def search_web(query: str) -> str:
    """Opens the web browser to search for a query with tab registration."""
    try:
        url = f"https://www.google.com/search?q={query}"
        webbrowser.open(url)
        speak(f"Searching for {query}")
        
        # Wait for browser to open
        time.sleep(2)
        
        # Get browser name from user agent
        browser_name = webbrowser.get().name
        if 'chrome' in browser_name.lower():
            browser_name = 'chrome' if platform.system() == 'Windows' else 'Google Chrome'
        elif 'firefox' in browser_name.lower():
            browser_name = 'firefox'
        elif 'safari' in browser_name.lower():
            browser_name = 'Safari'
        else:
            browser_name = 'msedge'
            
        # Register new tab
        tab_id = _register_browser_tab(url, browser_name)
        return tab_id
        
    except Exception as e:
        msg = f"Error performing web search: {str(e)}"
        logging.exception(msg)
        speak(msg)
        return ""

def open_url(url: str) -> str:
    """Opens a specific URL in the browser with tab registration."""
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        webbrowser.open(url)
        speak(f"Opening {url}")
        
        # Wait for browser to open
        time.sleep(2)
        
        # Get browser name
        browser_name = webbrowser.get().name
        if 'chrome' in browser_name.lower():
            browser_name = 'chrome' if platform.system() == 'Windows' else 'Google Chrome'
        elif 'firefox' in browser_name.lower():
            browser_name = 'firefox'
        elif 'safari' in browser_name.lower():
            browser_name = 'Safari'
        else:
            browser_name = 'msedge'
            
        # Register new tab
        tab_id = _register_browser_tab(url, browser_name)
        return tab_id
        
    except Exception as e:
        msg = f"Error opening URL: {str(e)}"
        logging.exception(msg)
        speak(msg)
        return ""

def close_current_tab() -> bool:
    """Closes the currently active browser tab."""
    try:
        # Get current window title to verify browser
        current_window = _get_active_window_title().lower()
        is_browser = any(b in current_window for b in ['chrome', 'firefox', 'safari', 'edge'])
        
        if not is_browser:
            speak("No browser window is currently active")
            return False
            
        # Simulate close tab shortcut
        keys = _get_platform_key('close_tab')
        if not keys:
            raise TabManagementError("Unsupported platform for tab closing")
            
        if not _simulate_keypress(keys):
            raise TabManagementError("Failed to simulate key press")
            
        speak("Closing current tab")
        return True
        
    except TabManagementError as e:
        msg = f"Error closing tab: {str(e)}"
        logging.error(msg)
        speak(msg)
    except Exception as e:
        msg = f"Unexpected error closing tab: {str(e)}"
        logging.exception(msg)
        speak(msg)
    return False

def close_browser_tab(tab_id: str) -> bool:
    """Closes a specific browser tab by ID."""
    try:
        with MEDIA_CONTROL_LOCK:
            tab_info = ACTIVE_BROWSER_TABS.get(tab_id)
            if not tab_info:
                raise TabManagementError("Tab not found")
                
            # Activate the browser window
            if not _activate_window(tab_info['browser']):
                raise TabManagementError("Failed to activate browser")
                
            # Close the tab
            keys = _get_platform_key('close_tab')
            if not _simulate_keypress(keys):
                raise TabManagementError("Failed to simulate key press")
                
            # Remove from tracking
            ACTIVE_BROWSER_TABS.pop(tab_id, None)
            speak("Tab closed")
            return True
            
    except TabManagementError as e:
        msg = f"Error closing tab: {str(e)}"
        logging.error(msg)
        speak(msg)
    except Exception as e:
        msg = f"Unexpected error closing tab: {str(e)}"
        logging.exception(msg)
        speak(msg)
    return False

# Media Control Functions
def play_pause_media(player_id: str = "") -> bool:
    """Toggles play/pause for media player."""
    try:
        with MEDIA_CONTROL_LOCK:
            player_info = None
            if player_id:
                player_info = ACTIVE_MEDIA_PLAYERS.get(player_id)
                
            # If no player specified, find active player
            if not player_info:
                for pid, info in ACTIVE_MEDIA_PLAYERS.items():
                    if info['process'].is_running():
                        player_info = info
                        player_id = pid
                        break
                        
            if not player_info:
                raise MediaControlError("No active media player found")
                
            # Activate the media player window
            if not _activate_window(player_info['name']):
                raise MediaControlError("Failed to activate media player")
                
            # Send play/pause command
            keys = _get_platform_key('play_pause')
            if not _simulate_keypress(keys):
                raise MediaControlError("Failed to simulate key press")
                
            ACTIVE_MEDIA_PLAYERS[player_id]['last_activity'] = time.time()
            speak("Media play/pause toggled")
            return True
            
    except MediaControlError as e:
        msg = f"Error controlling media: {str(e)}"
        logging.error(msg)
        speak(msg)
    except Exception as e:
        msg = f"Unexpected error controlling media: {str(e)}"
        logging.exception(msg)
        speak(msg)
    return False

def next_track(player_id: str = "") -> bool:
    """Skips to next track for media player."""
    try:
        with MEDIA_CONTROL_LOCK:
            player_info = None
            if player_id:
                player_info = ACTIVE_MEDIA_PLAYERS.get(player_id)
                
            if not player_info:
                for pid, info in ACTIVE_MEDIA_PLAYERS.items():
                    if info['process'].is_running():
                        player_info = info
                        player_id = pid
                        break
                        
            if not player_info:
                raise MediaControlError("No active media player found")
                
            # Activate the media player window
            if not _activate_window(player_info['name']):
                raise MediaControlError("Failed to activate media player")
                
            # Send next track command
            keys = _get_platform_key('next_track')
            if not _simulate_keypress(keys):
                raise MediaControlError("Failed to simulate key press")
                
            ACTIVE_MEDIA_PLAYERS[player_id]['last_activity'] = time.time()
            speak("Skipping to next track")
            return True
            
    except MediaControlError as e:
        msg = f"Error controlling media: {str(e)}"
        logging.error(msg)
        speak(msg)
    except Exception as e:
        msg = f"Unexpected error controlling media: {str(e)}"
        logging.exception(msg)
        speak(msg)
    return False

def close_all_media_players() -> bool:
    """Closes all registered media players."""
    try:
        with MEDIA_CONTROL_LOCK:
            if not ACTIVE_MEDIA_PLAYERS:
                speak("No media players are active")
                return True
                
            success = True
            for player_id, player_info in list(ACTIVE_MEDIA_PLAYERS.items()):
                try:
                    if player_info['process'].is_running():
                        player_info['process'].terminate()
                        # Wait for termination
                        for _ in range(5):
                            if not player_info['process'].is_running():
                                break
                            time.sleep(1)
                        else:
                            success = False
                except Exception:
                    success = False
                finally:
                    ACTIVE_MEDIA_PLAYERS.pop(player_id, None)
                    
            speak("All media players closed" if success else "Some media players couldn't be closed")
            return success
            
    except Exception as e:
        msg = f"Error closing media players: {str(e)}"
        logging.exception(msg)
        speak(msg)
        return False

# System Information Functions
def get_system_status() -> str:
    """Returns system status information."""
    try:
        status = []
        # CPU Usage
        cpu_percent = psutil.cpu_percent()
        status.append(f"CPU Usage: {cpu_percent}%")
        
        # Memory Usage
        mem = psutil.virtual_memory()
        status.append(f"Memory Usage: {mem.percent}%")
        
        # Disk Usage
        disk = psutil.disk_usage('/')
        status.append(f"Disk Usage: {disk.percent}%")
        
        # Active applications
        status.append(f"Active Applications: {len(psutil.process_iter())}")
        
        # Media players
        status.append(f"Active Media Players: {len(ACTIVE_MEDIA_PLAYERS)}")
        
        # Browser tabs
        status.append(f"Tracked Browser Tabs: {len(ACTIVE_BROWSER_TABS)}")
        
        return "\n".join(status)
    except Exception as e:
        logging.error(f"Error getting system status: {str(e)}")
        return "System status unavailable"

# Cleanup function
def cleanup_system_actions():
    """Clean up resources when system actions are terminated."""
    SYSTEM_MONITOR.stop()
    logging.info("System actions module cleaned up")

# Register cleanup handler
import atexit
atexit.register(cleanup_system_actions)