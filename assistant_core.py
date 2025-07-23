
"""
Nirvan Assistant Core - Main conversation and control logic
"""

import time
import logging
import threading
from enum import Enum, auto
from typing import Optional

from speech_handler import SpeechHandler
from command_processor import CommandProcessor

logger = logging.getLogger(__name__)

class AssistantState(Enum):
    """Assistant operational states"""
    IDLE = auto()
    LISTENING = auto()
    THINKING = auto()
    SPEAKING = auto()
    ERROR = auto()

class AssistantCore:
    """Main assistant logic coordinator"""
    
    def __init__(self, socketio):
        self.socketio = socketio
        self.speech_handler = SpeechHandler(socketio)
        self.command_processor = CommandProcessor(socketio)
        
        self.state = AssistantState.IDLE
        self.is_active = False
        self.conversation_timeout = 60  # seconds
        self.last_interaction = time.time()
        self.max_listen_retries = 3
        
        logger.info("Assistant core initialized")
    
    def update_state(self, new_state: AssistantState):
        """Update assistant state and notify UI"""
        if self.state != new_state:
            self.state = new_state
            self.socketio.emit('state_change', {'state': new_state.name.lower()})
            logger.info(f"State changed to: {new_state.name}")
    
    def start_conversation(self):
        """Start a new conversation session"""
        if self.is_active:
            logger.warning("Conversation already active")
            return
        
        self.is_active = True
        self.last_interaction = time.time()
        
        logger.info("Starting conversation")
        self.update_state(AssistantState.SPEAKING)
        
        # Test audio system first
        if not self.speech_handler.test_audio_system():
            self.speech_handler.speak("I'm having trouble with the audio system. Please check your microphone.")
            self.stop_conversation()
            return
        
        # Welcome message
        self.speech_handler.speak("Hello! How can I help you today?")
        self.update_state(AssistantState.IDLE)
        
        # Main conversation loop
        self._conversation_loop()
    
    def stop_conversation(self):
        """Stop the current conversation"""
        self.is_active = False
        self.update_state(AssistantState.IDLE)
        logger.info("Conversation stopped")
        self.socketio.emit('deactivate_window')
    
    def _conversation_loop(self):
        """Main conversation processing loop"""
        listen_failures = 0
        
        while self.is_active:
            # Check for timeout
            if time.time() - self.last_interaction > self.conversation_timeout:
                self.speech_handler.speak("Closing due to inactivity. Just say my name to start again.")
                break
            
            # Listen for command
            self.update_state(AssistantState.LISTENING)
            command = self.speech_handler.listen_for_command()
            
            if command:
                listen_failures = 0
                self.last_interaction = time.time()
                
                # Check for exit commands
                exit_phrases = ["goodbye", "exit", "close", "that's all", "quit", "stop"]
                if any(phrase in command.lower() for phrase in exit_phrases):
                    self.speech_handler.speak("Goodbye! Have a great day.")
                    break
                
                # Process the command
                self.update_state(AssistantState.THINKING)
                success = self.command_processor.process_command(command)
                
                # Provide feedback
                self.update_state(AssistantState.SPEAKING)
                if success:
                    self.speech_handler.speak("Is there anything else I can help you with?")
                else:
                    self.speech_handler.speak("Let me know if there's anything else you need.")
                
                self.update_state(AssistantState.IDLE)
            
            else:
                listen_failures += 1
                if listen_failures >= self.max_listen_retries:
                    self.speech_handler.speak("I'm having trouble hearing you. I'll wait for you to call me again.")
                    break
                else:
                    self.speech_handler.speak("Sorry, I didn't catch that. Could you please repeat?")
        
        # End conversation
        self.stop_conversation()
