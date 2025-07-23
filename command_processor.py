
"""
Command Processor - Handles command interpretation and action execution
"""

import logging
from typing import Dict, Callable, Any, Optional

from gemini_core import process_command_with_gemini
from actions.system_actions import open_application, search_web
from actions.youtube_actions import search_youtube, play_video
from actions.email_actions import send_email

logger = logging.getLogger(__name__)

class CommandProcessor:
    """Processes voice commands and executes appropriate actions"""
    
    def __init__(self, socketio):
        self.socketio = socketio
        
        # Map of available commands to their handler functions
        self.action_handlers: Dict[str, Callable] = {
            "open_app": self._handle_open_app,
            "search_web": self._handle_search_web,
            "search_youtube": self._handle_search_youtube,
            "play_video": self._handle_play_video,
            "send_email": self._handle_send_email,
            "unsupported": self._handle_unsupported
        }
        
        logger.info("Command processor initialized")
    
    def process_command(self, command_text: str) -> bool:
        """Process a voice command and execute the appropriate action"""
        try:
            logger.info(f"Processing command: '{command_text}'")
            
            # Use Gemini to interpret the command
            action_details = process_command_with_gemini(command_text)
            
            if not action_details:
                logger.warning("No action details returned from Gemini")
                return False
            
            command_name = action_details.get("command")
            parameters = action_details.get("parameters", {})
            
            logger.info(f"Interpreted as: {command_name} with params: {parameters}")
            
            # Execute the appropriate handler
            handler = self.action_handlers.get(command_name)
            if handler:
                return handler(parameters)
            else:
                logger.warning(f"No handler found for command: {command_name}")
                return False
                
        except Exception as e:
            logger.error(f"Command processing error: {e}")
            return False
    
    def _handle_open_app(self, params: Dict[str, Any]) -> bool:
        """Handle application opening requests"""
        try:
            app_name = params.get("app_name", "")
            if app_name:
                open_application(app_name)
                return True
            return False
        except Exception as e:
            logger.error(f"Error opening app: {e}")
            return False
    
    def _handle_search_web(self, params: Dict[str, Any]) -> bool:
        """Handle web search requests"""
        try:
            query = params.get("query", "")
            if query:
                search_web(query)
                return True
            return False
        except Exception as e:
            logger.error(f"Error searching web: {e}")
            return False
    
    def _handle_search_youtube(self, params: Dict[str, Any]) -> bool:
        """Handle YouTube search requests"""
        try:
            query = params.get("query", "")
            if query:
                search_youtube(query)
                return True
            return False
        except Exception as e:
            logger.error(f"Error searching YouTube: {e}")
            return False
    
    def _handle_play_video(self, params: Dict[str, Any]) -> bool:
        """Handle video playback requests"""
        try:
            video_identifier = params.get("video_identifier", "")
            if video_identifier:
                play_video(video_identifier)
                return True
            return False
        except Exception as e:
            logger.error(f"Error playing video: {e}")
            return False
    
    def _handle_send_email(self, params: Dict[str, Any]) -> bool:
        """Handle email sending requests"""
        try:
            recipient = params.get("recipient", "")
            subject = params.get("subject", "")
            if recipient:
                send_email(recipient=recipient, subject=subject)
                return True
            return False
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    def _handle_unsupported(self, params: Dict[str, Any]) -> bool:
        """Handle unsupported command requests"""
        reason = params.get("reason", "I'm not sure how to help with that.")
        logger.info(f"Unsupported command: {reason}")
        return False
