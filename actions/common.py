# actions/common.py (Enhanced Version with Better Error Handling)
# Updated to fix timeout issues and improve reliability

import os
import threading
import time
from datetime import datetime
import speech_recognition as sr
from gtts import gTTS
from playsound import playsound
import google.generativeai as genai
import logging
from typing import Optional, Union
import tempfile
import queue

# Setup logging
logger = logging.getLogger(__name__)

# Global socketio instance
SOCKETIO = None

# Configuration constants
class AudioConfig:
    LISTEN_TIMEOUT = 12  # seconds
    PHRASE_TIME_LIMIT = 10  # seconds
    AMBIENT_ADJUSTMENT_DURATION = 1  # seconds
    PAUSE_THRESHOLD = 1.0
    ENERGY_THRESHOLD = 300
    MAX_RETRY_ATTEMPTS = 3
    SPEECH_RECOGNITION_TIMEOUT = 15  # seconds for Google API
    
    # Microphone settings
    SAMPLE_RATE = 16000
    CHUNK_SIZE = 1024

def set_socketio_instance(sio):
    """Links the main SocketIO instance to this module."""
    global SOCKETIO
    SOCKETIO = sio
    logger.info("SocketIO instance set in common.py")

def emit_safe(event: str, data: dict = None):
    """Safely emit socketio events with error handling"""
    try:
        if SOCKETIO:
            SOCKETIO.emit(event, data or {})
            return True
    except Exception as e:
        logger.error(f"Failed to emit {event}: {e}")
    return False

def speak(text: str) -> Optional[threading.Event]:
    """
    Enhanced speak function with better error handling and timeout management.
    Returns an Event that can be used to wait for speech completion.
    """
    if not text or not text.strip():
        logger.warning("Empty text provided to speak function")
        return None
    
    speak_done_event = threading.Event()
    
    # Emit to GUI
    emit_safe('display_message', {
        'who': 'assistant', 
        'message': text,
        'timestamp': datetime.now().isoformat()
    })
    
    def _speak_thread():
        temp_file = None
        try:
            logger.info(f"Speaking: {text[:50]}...")
            
            # Create TTS with error handling
            try:
                tts = gTTS(text=text, lang='en', slow=False)
            except Exception as e:
                logger.error(f"TTS creation failed: {e}")
                emit_safe('speech_error', {'error': 'Failed to create speech'})
                return
            
            # Create temporary file
            try:
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
                    temp_file = tmp.name
                    tts.save(temp_file)
                logger.debug(f"Audio saved to temporary file: {temp_file}")
            except Exception as e:
                logger.error(f"Failed to save audio file: {e}")
                emit_safe('speech_error', {'error': 'Failed to save audio'})
                return
            
            # Play audio with timeout protection
            try:
                # Estimate speech duration (rough calculation)
                estimated_duration = len(text.split()) * 0.6  # ~0.6 seconds per word
                max_play_time = max(estimated_duration + 5, 10)  # minimum 10 seconds
                
                play_thread = threading.Thread(target=lambda: playsound(temp_file))
                play_thread.start()
                play_thread.join(timeout=max_play_time)
                
                if play_thread.is_alive():
                    logger.warning("Audio playback timeout - continuing anyway")
                    
            except Exception as e:
                logger.error(f"Audio playback failed: {e}")
                emit_safe('speech_error', {'error': 'Failed to play audio'})
            
        except Exception as e:
            logger.error(f"Unexpected error in speak thread: {e}")
            emit_safe('speech_error', {'error': str(e)})
        finally:
            # Cleanup
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    logger.debug(f"Cleaned up temporary file: {temp_file}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file: {e}")
            
            speak_done_event.set()
            emit_safe('speech_completed', {'text': text})
    
    # Start speech thread
    thread = threading.Thread(target=_speak_thread, daemon=True, name="SpeechThread")
    thread.start()
    
    return speak_done_event

def listen_for_command(timeout: int = None, phrase_time_limit: int = None, 
                      retries: int = None) -> Optional[str]:
    """
    Enhanced listen function with comprehensive error handling and timeout management.
    
    Args:
        timeout: Maximum time to wait for speech to start (default: AudioConfig.LISTEN_TIMEOUT)
        phrase_time_limit: Maximum time for a single phrase (default: AudioConfig.PHRASE_TIME_LIMIT)
        retries: Number of retry attempts (default: AudioConfig.MAX_RETRY_ATTEMPTS)
    
    Returns:
        Recognized text or None if failed
    """
    timeout = timeout or AudioConfig.LISTEN_TIMEOUT
    phrase_time_limit = phrase_time_limit or AudioConfig.PHRASE_TIME_LIMIT
    retries = retries or AudioConfig.MAX_RETRY_ATTEMPTS
    
    logger.info(f"Starting to listen (timeout={timeout}s, phrase_limit={phrase_time_limit}s)")
    
    # Signal GUI to start listening animation
    emit_safe('start_listening', {
        'timeout': timeout,
        'phrase_time_limit': phrase_time_limit
    })
    
    recognizer = sr.Recognizer()
    command = None
    
    # Configure recognizer
    recognizer.pause_threshold = AudioConfig.PAUSE_THRESHOLD
    recognizer.energy_threshold = AudioConfig.ENERGY_THRESHOLD
    
    for attempt in range(retries):
        try:
            logger.debug(f"Listen attempt {attempt + 1}/{retries}")
            
            # Initialize microphone with error handling
            try:
                with sr.Microphone(sample_rate=AudioConfig.SAMPLE_RATE, 
                                 chunk_size=AudioConfig.CHUNK_SIZE) as source:
                    
                    # Adjust for ambient noise with timeout
                    logger.debug("Adjusting for ambient noise...")
                    emit_safe('listening_status', {'status': 'adjusting_noise'})
                    
                    adjust_start = time.time()
                    recognizer.adjust_for_ambient_noise(
                        source, 
                        duration=AudioConfig.AMBIENT_ADJUSTMENT_DURATION
                    )
                    adjust_time = time.time() - adjust_start
                    logger.debug(f"Ambient noise adjustment completed in {adjust_time:.2f}s")
                    
                    # Listen for audio with timeout
                    emit_safe('listening_status', {'status': 'listening'})
                    logger.debug(f"Listening for speech (timeout={timeout}s)...")
                    
                    listen_start = time.time()
                    audio = recognizer.listen(
                        source, 
                        timeout=timeout, 
                        phrase_time_limit=phrase_time_limit
                    )
                    listen_time = time.time() - listen_start
                    logger.debug(f"Audio captured in {listen_time:.2f}s")
                    
            except sr.WaitTimeoutError:
                logger.warning(f"Listen timeout on attempt {attempt + 1}")
                emit_safe('listening_status', {'status': 'timeout', 'attempt': attempt + 1})
                if attempt == retries - 1:
                    emit_safe('listening_error', {'error': 'No speech detected within timeout period'})
                continue
                
            except Exception as e:
                logger.error(f"Microphone error on attempt {attempt + 1}: {e}")
                emit_safe('listening_status', {'status': 'microphone_error', 'error': str(e)})
                if attempt == retries - 1:
                    emit_safe('listening_error', {'error': f'Microphone error: {str(e)}'})
                time.sleep(1)  # Brief pause before retry
                continue
            
            # Process the audio with Google Speech Recognition
            try:
                emit_safe('listening_status', {'status': 'processing'})
                logger.debug("Processing audio with Google Speech Recognition...")
                
                # Use a timeout for the recognition request
                recognition_start = time.time()
                
                # Create a queue to get the result from the recognition thread
                result_queue = queue.Queue()
                
                def recognize_thread():
                    try:
                        result = recognizer.recognize_google(
                            audio, 
                            language='en-in',
                            show_all=False
                        )
                        result_queue.put(('success', result))
                    except Exception as e:
                        result_queue.put(('error', e))
                
                # Start recognition in a separate thread
                recognition_thread = threading.Thread(target=recognize_thread, daemon=True)
                recognition_thread.start()
                
                # Wait for result with timeout
                try:
                    result_type, result_data = result_queue.get(
                        timeout=AudioConfig.SPEECH_RECOGNITION_TIMEOUT
                    )
                    
                    if result_type == 'success':
                        command = result_data.lower().strip()
                        recognition_time = time.time() - recognition_start
                        logger.info(f"Speech recognized in {recognition_time:.2f}s: '{command}'")
                        
                        # Validate the command
                        if len(command) < 1:
                            logger.warning("Empty command received")
                            continue
                        
                        # Emit successful recognition
                        emit_safe('display_message', {
                            'who': 'user',
                            'message': command,
                            'timestamp': datetime.now().isoformat()
                        })
                        
                        break  # Success - exit retry loop
                        
                    else:  # Error case
                        raise result_data
                        
                except queue.Empty:
                    logger.error("Speech recognition timeout")
                    emit_safe('listening_status', {'status': 'recognition_timeout'})
                    if attempt == retries - 1:
                        emit_safe('listening_error', {'error': 'Speech recognition timeout'})
                    continue
                
            except sr.UnknownValueError:
                logger.warning(f"Could not understand audio on attempt {attempt + 1}")
                emit_safe('listening_status', {'status': 'unknown_speech', 'attempt': attempt + 1})
                if attempt == retries - 1:
                    emit_safe('listening_error', {'error': 'Could not understand speech'})
                continue
                
            except sr.RequestError as e:
                logger.error(f"Google Speech Recognition service error: {e}")
                emit_safe('listening_status', {'status': 'service_error', 'error': str(e)})
                if attempt == retries - 1:
                    emit_safe('listening_error', {'error': f'Speech recognition service error: {str(e)}'})
                time.sleep(2)  # Longer pause for service errors
                continue
                
            except Exception as e:
                logger.error(f"Unexpected recognition error: {e}")
                emit_safe('listening_status', {'status': 'unexpected_error', 'error': str(e)})
                if attempt == retries - 1:
                    emit_safe('listening_error', {'error': f'Unexpected error: {str(e)}'})
                continue
                
        except Exception as e:
            logger.error(f"Unexpected error in listen attempt {attempt + 1}: {e}")
            emit_safe('listening_status', {'status': 'critical_error', 'error': str(e)})
            if attempt == retries - 1:
                emit_safe('listening_error', {'error': f'Critical listening error: {str(e)}'})
            continue
    
    # Cleanup - stop listening animation
    emit_safe('stop_listening', {
        'success': command is not None,
        'command': command,
        'attempts': retries
    })
    
    if command:
        logger.info(f"Listen successful: '{command}'")
    else:
        logger.warning("Listen failed after all attempts")
    
    return command

def get_confirmation(user_response: str, context_question: str) -> str:
    """
    Enhanced confirmation function with better error handling.
    
    Args:
        user_response: The user's response text
        context_question: The original question asked
    
    Returns:
        'confirm', 'deny', or 'cancel'
    """
    if not user_response or not user_response.strip():
        logger.warning("Empty user response for confirmation")
        return "deny"
    
    try:
        logger.debug(f"Getting confirmation for: '{user_response}' (context: '{context_question}')")
        
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = (
            f"User was asked: '{context_question}'\n"
            f"User replied: '{user_response}'\n"
            f"Analyze the user's intent. Respond with exactly one word:\n"
            f"- 'confirm' if they agree/accept/yes\n"
            f"- 'deny' if they disagree/decline/no\n"
            f"- 'cancel' if they want to cancel/stop\n"
            f"If unclear, default to 'deny'."
        )
        
        response = model.generate_content(prompt)
        intent = response.text.strip().lower()
        
        # Validate response
        valid_intents = ['confirm', 'deny', 'cancel']
        if intent in valid_intents:
            logger.info(f"Confirmation intent: {intent}")
            return intent
        else:
            logger.warning(f"Invalid intent received: '{intent}', defaulting to 'deny'")
            return "deny"
            
    except Exception as e:
        logger.error(f"Gemini confirmation error: {e}")
        emit_safe('confirmation_error', {'error': str(e)})
        return "deny"

def test_audio_system() -> dict:
    """
    Test the audio system and return diagnostic information.
    
    Returns:
        Dictionary with test results
    """
    results = {
        'microphone_available': False,
        'speech_recognition_working': False,
        'tts_working': False,
        'errors': []
    }
    
    try:
        # Test microphone
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
        results['microphone_available'] = True
        logger.info("Microphone test: PASSED")
    except Exception as e:
        results['errors'].append(f"Microphone test failed: {e}")
        logger.error(f"Microphone test: FAILED - {e}")
    
    try:
        # Test TTS
        tts = gTTS(text="test", lang='en')
        results['tts_working'] = True
        logger.info("TTS test: PASSED")
    except Exception as e:
        results['errors'].append(f"TTS test failed: {e}")
        logger.error(f"TTS test: FAILED - {e}")
    
    return results

# Initialize logging for this module
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    # Run audio system test
    test_results = test_audio_system()
    print("Audio System Test Results:")
    for key, value in test_results.items():
        print(f"  {key}: {value}")