"""
Nirvan AI Assistant - Simplified Version
A clean, well-structured AI assistant that runs with: python app.py
"""

import sys
import threading
import webview
import time
import logging
from flask import Flask, render_template
from flask_socketio import SocketIO

# Import our core modules
from assistant_core import AssistantCore
from wake_word_detector import run_wake_word_detector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nirvan_assistant.log'),
        logging.StreamHandler()
    ]
)

# Suppress Flask logs
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = 'nirvan_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize assistant core
assistant = AssistantCore(socketio)

class WebAPI:
    """API for webview integration"""

    def start_assistant(self):
        """Start the assistant conversation"""
        if not assistant.is_active:
            threading.Thread(target=assistant.start_conversation, daemon=True).start()
            return "Assistant started"
        return "Assistant already active"

    def stop_assistant(self):
        """Stop the assistant"""
        assistant.stop_conversation()
        return "Assistant stopped"

    def show_window(self):
        """Show the assistant window"""
        if hasattr(self, 'window') and self.window:
            self.window.show()

    def hide_window(self):
        """Hide the assistant window"""
        if hasattr(self, 'window') and self.window:
            self.window.hide()

# Web routes
@app.route('/')
def index():
    return render_template('index.html')

# Socket events
@socketio.on('start_assistant')
def handle_start_assistant():
    if not assistant.is_active:
        threading.Thread(target=assistant.start_conversation, daemon=True).start()
        socketio.emit('assistant_status', {'status': 'started'})

@socketio.on('stop_assistant')
def handle_stop_assistant():
    assistant.stop_conversation()
    socketio.emit('assistant_status', {'status': 'stopped'})

@socketio.on('activate_window')
def handle_activate_window():
    socketio.emit('show_window')

@socketio.on('deactivate_window')
def handle_deactivate_window():
    socketio.emit('hide_window')

def start_server():
    """Start the Flask server"""
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)

def main():
    """Main application entry point"""
    print("Starting Nirvan AI Assistant...")

    # Start Flask server in background
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # Give server time to start
    time.sleep(2)

    # Create webview window
    api = WebAPI()
    window = webview.create_window(
        'Nirvan Assistant',
        'http://127.0.0.1:5000',
        js_api=api,
        width=400,
        height=600,
        frameless=True,
        easy_drag=True,
        on_top=True,
        hidden=True,
        transparent=True,
        resizable=False
    )
    api.window = window

    # Start wake word detector
    wake_thread = threading.Thread(
        target=run_wake_word_detector, 
        args=(socketio,), 
        daemon=True
    )
    wake_thread.start()

    print("Nirvan Assistant is ready!")
    print("Say 'Nirvan' to activate or click the window.")

    # Start webview (blocking)
    webview.start(debug=False)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nShutting down Nirvan Assistant...")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting assistant: {e}")
        sys.exit(1)