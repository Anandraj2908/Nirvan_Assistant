# Nirvan_Assistant/app.py
# V3 - Fully state-managed, robust conversation engine based on your logic.

import sys
import threading
import webview
import time
import random
import logging
from enum import Enum, auto

from flask import Flask, render_template
from flask_socketio import SocketIO

# --- Assistant Logic Imports ---
import gemini_core
from actions import system_actions, youtube_actions, email_actions
from actions.common import (
    speak,
    listen_for_command,
    set_socketio_instance,
    test_audio_system # New import
)

# --- Basic Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# --- Core Application Components ---
app = Flask(__name__, static_folder='static', template_folder='templates')
socketio = SocketIO(app)
set_socketio_instance(socketio) # Provide the socketio instance to common functions
window = None

# --- Configuration Class ---
class Config:
    """Holds all static configuration for the assistant."""
    # Timing
    LISTEN_TIMEOUT = 10
    PHRASE_TIME_LIMIT = 12
    CONVERSATION_TIMEOUT = 60  # seconds
    ERROR_RECOVERY_DELAY = 3
    
    # Retries
    MAX_LISTEN_RETRIES = 2
    
    # Speech
    SPEECH_DELAY_MIN = 0.2
    SPEECH_DELAY_MAX = 0.8

# --- State Management ---
class AssistantState(Enum):
    """Defines the possible operational states of the assistant."""
    IDLE = auto()
    LISTENING = auto()
    THINKING = auto()
    SPEAKING = auto()

class AssistantManager:
    """A central class to manage the assistant's state, history, and errors."""
    def __init__(self, socketio_instance):
        self.socketio = socketio_instance
        self.state = AssistantState.IDLE
        self.is_active = False
        self.last_interaction_time = time.time()
        self.conversation_history = []
        self.consecutive_errors = 0

    def update_state(self, new_state: AssistantState):
        if self.state == new_state: return
        self.state = new_state
        self.socketio.emit('state_change', {'state': new_state.name.lower()})
        logging.info(f"State changed to: {new_state.name}")

    def reset_interaction_timer(self):
        self.last_interaction_time = time.time()
    
    def add_to_history(self, entry: dict):
        self.conversation_history.append(entry)

    def handle_error(self, error, context="General"):
        self.consecutive_errors += 1
        logging.error(f"Error in {context}: {error}")
        if self.consecutive_errors > 3:
            logging.critical("Too many consecutive errors, stopping conversation.")
            safe_speak("I'm facing a critical issue and need to stop. Please restart me.")
            self.is_active = False

# Create a single instance of the manager
assistant_manager = AssistantManager(socketio)

# --- Enhanced Speech & Listen Functions (Your Code, Integrated) ---
def safe_speak(text: str, delay_before: bool = True, timeout: float = 30.0) -> bool:
    if not text or not text.strip():
        logging.warning("Empty text provided to safe_speak")
        return False
        
    try:
        if delay_before:
            time.sleep(random.uniform(Config.SPEECH_DELAY_MIN, Config.SPEECH_DELAY_MAX))
        
        assistant_manager.update_state(AssistantState.SPEAKING)
        assistant_manager.add_to_history({'type': 'assistant', 'text': text, 'timestamp': time.time()})
        
        speech_event = speak(text) # Use the function from common.py
        if speech_event:
            speech_event.wait(timeout=timeout)
            assistant_manager.consecutive_errors = 0
            return True
        return False
    except Exception as e:
        assistant_manager.handle_error(e, "safe_speak")
        return False
    finally:
        assistant_manager.update_state(AssistantState.IDLE)

def safe_listen() -> str | None:
    assistant_manager.update_state(AssistantState.LISTENING)
    try:
        command_text = listen_for_command(
            timeout=Config.LISTEN_TIMEOUT,
            phrase_time_limit=Config.PHRASE_TIME_LIMIT
        )
        if command_text:
            command_text = command_text.strip()
            assistant_manager.add_to_history({'type': 'user', 'text': command_text, 'timestamp': time.time()})
            logging.info(f"Received command: '{command_text}'")
            return command_text
        logging.info("No command received.")
        return None
    except Exception as e:
        assistant_manager.handle_error(e, "safe_listen")
        return None
    finally:
        assistant_manager.update_state(AssistantState.THINKING)

def process_command_safely(command_text: str) -> bool:
    """Processes a command and returns True on success, False on failure."""
    assistant_manager.update_state(AssistantState.THINKING)
    action_map = {
        "open_app": system_actions.open_application,
        "search_web": system_actions.search_web,
        "search_youtube": youtube_actions.search_youtube,
        "play_video": youtube_actions.play_video,
        "send_email": email_actions.send_email,
    }
    
    try:
        action_details = gemini_core.process_command_with_gemini(command_text)
        if action_details:
            command_name = action_details.get("command")
            parameters = action_details.get("parameters", {})
            action_function = action_map.get(command_name)

            if action_function:
                action_function(**parameters)
                return True
            else: # Unsupported command
                reason = parameters.get("reason", "I'm not able to help with that.")
                safe_speak(reason)
                return False
        else:
            safe_speak("I had trouble understanding that. Could you rephrase?")
            return False
    except Exception as e:
        assistant_manager.handle_error(e, "process_command_safely")
        safe_speak("I ran into an unexpected problem while trying to do that.")
        return False

# --- Main Conversation Loop (Your Logic, Restructured) ---
def run_assistant_logic():
    assistant_manager.is_active = True
    listen_failures = 0

    if not test_audio_system().get('microphone_available'):
        safe_speak("I can't access your microphone. Please check your system settings.")
        assistant_manager.is_active = False
        return

    safe_speak("Hello! How can I help you today?")
    assistant_manager.reset_interaction_timer()

    while assistant_manager.is_active:
        if time.time() - assistant_manager.last_interaction_time > Config.CONVERSATION_TIMEOUT:
            safe_speak("Closing due to inactivity. Just say my name to start again.")
            break

        command = safe_listen()

        if command:
            listen_failures = 0
            assistant_manager.reset_interaction_timer()

            exit_phrases = ["goodbye", "exit", "close", "that's all", "quit"]
            if any(phrase in command.lower() for phrase in exit_phrases):
                safe_speak("Goodbye! Have a great day.")
                break
            
            if process_command_safely(command):
                safe_speak("Is there anything else?")
            else:
                safe_speak("What else can I do for you?")
        else:
            listen_failures += 1
            if listen_failures >= Config.MAX_LISTEN_RETRIES:
                safe_speak("I'm having trouble hearing you. I'll wait for you to call me again.")
                break
            else:
                safe_speak("Sorry, I didn't catch that. Could you please say it again?")
    
    # End of loop
    assistant_manager.is_active = False
    socketio.emit('deactivate_window')
    logging.info("Assistant conversation logic ended.")

# --- Webview API and Server Setup ---
class Api:
    def start_logic(self):
        if not assistant_manager.is_active:
            threading.Thread(target=run_assistant_logic, daemon=True).start()

    def show_window(self):
        if window: window.show()

    def hide_window(self):
        if window: window.hide()

@app.route('/')
def index():
    return render_template('index.html')

def start_server():
    socketio.run(app, host='127.0.0.1', port=5000)

if __name__ == '__main__':
    api = Api()
    threading.Thread(target=start_server, daemon=True).start()
    
    window = webview.create_window(
        'Nirvan Assistant', 'http://127.0.0.1:5000', js_api=api,
        width=400, height=600, frameless=True, easy_drag=True,
        on_top=True, hidden=True, transparent=True, resizable=False,
    )

    threading.Thread(target=run_wake_word_detector, args=(socketio,), daemon=True).start()
    webview.start(debug=False)
    sys.exit()