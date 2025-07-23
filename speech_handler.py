
"""
Speech Handler - Text-to-speech and speech recognition
"""

import os
import time
import tempfile
import threading
import logging
from typing import Optional
import speech_recognition as sr
from gtts import gTTS
from playsound import playsound

logger = logging.getLogger(__name__)

class SpeechHandler:
    """Handles all speech input/output operations"""
    
    def __init__(self, socketio):
        self.socketio = socketio
        self.recognizer = sr.Recognizer()
        
        # Configure recognizer
        self.recognizer.pause_threshold = 1.0
        self.recognizer.energy_threshold = 300
        
        # Timeouts
        self.listen_timeout = 10
        self.phrase_time_limit = 12
        
        logger.info("Speech handler initialized")
    
    def speak(self, text: str) -> bool:
        """Convert text to speech and play it"""
        if not text or not text.strip():
            logger.warning("Empty text provided for speech")
            return False
        
        # Emit to UI
        self.socketio.emit('display_message', {
            'who': 'assistant',
            'message': text,
            'timestamp': time.time()
        })
        
        try:
            # Create TTS
            tts = gTTS(text=text, lang='en', slow=False)
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
                temp_path = tmp_file.name
                tts.save(temp_path)
            
            # Play audio
            playsound(temp_path)
            
            # Cleanup
            os.remove(temp_path)
            
            logger.info(f"Spoke: {text[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Speech synthesis error: {e}")
            return False
    
    def listen_for_command(self) -> Optional[str]:
        """Listen for voice command and return recognized text"""
        try:
            self.socketio.emit('listening_status', {'status': 'listening'})
            
            with sr.Microphone() as source:
                # Adjust for ambient noise
                logger.debug("Adjusting for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                
                # Listen for audio
                logger.debug("Listening for command...")
                audio = self.recognizer.listen(
                    source,
                    timeout=self.listen_timeout,
                    phrase_time_limit=self.phrase_time_limit
                )
            
            # Recognize speech
            self.socketio.emit('listening_status', {'status': 'processing'})
            command = self.recognizer.recognize_google(audio, language='en-US')
            command = command.lower().strip()
            
            # Emit to UI
            self.socketio.emit('display_message', {
                'who': 'user',
                'message': command,
                'timestamp': time.time()
            })
            
            logger.info(f"Recognized command: '{command}'")
            return command
            
        except sr.WaitTimeoutError:
            logger.debug("Listen timeout - no speech detected")
            return None
        except sr.UnknownValueError:
            logger.debug("Could not understand audio")
            return None
        except sr.RequestError as e:
            logger.error(f"Speech recognition service error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected listen error: {e}")
            return None
        finally:
            self.socketio.emit('listening_status', {'status': 'idle'})
    
    def test_audio_system(self) -> bool:
        """Test if audio system is working"""
        try:
            # Test microphone
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
            # Test TTS
            tts = gTTS(text="test", lang='en')
            
            logger.info("Audio system test: PASSED")
            return True
            
        except Exception as e:
            logger.error(f"Audio system test: FAILED - {e}")
            return False
