# wake_word_detector.py (Corrected Version)
# This version is simplified to only emit a socket event.

import os
import pvporcupine
import pyaudio
import struct

PICOVOICE_ACCESS_KEY = ""
WAKE_WORD_MODEL_PATH = "Nirvan_windows.ppn"

def run_wake_word_detector(socketio_instance):
    """Listens for the wake word and emits a socket event to the frontend."""
    porcupine, pa, audio_stream = None, None, None
    try:
        if not os.path.exists(WAKE_WORD_MODEL_PATH):
            print(f"FATAL ERROR: Wake word model file not found at '{WAKE_WORD_MODEL_PATH}'")
            return

        porcupine = pvporcupine.create(access_key=PICOVOICE_ACCESS_KEY, keyword_paths=[WAKE_WORD_MODEL_PATH])
        pa = pyaudio.PyAudio()
        audio_stream = pa.open(
            rate=porcupine.sample_rate, channels=1, format=pyaudio.paInt16,
            input=True, frames_per_buffer=porcupine.frame_length
        )
        print("Wake word engine running... Say 'Nirvan' to activate.")
        
        while True:
            pcm = audio_stream.read(porcupine.frame_length)
            pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
            
            if porcupine.process(pcm) >= 0:
                print("Wake word 'Nirvan' detected!")
                # Emit an event to all connected clients (our React app)
                socketio_instance.emit('activate_window')
                
    except Exception as e:
        print(f"Error with wake word engine: {e}")
    finally:
        if audio_stream: audio_stream.close()
        if pa: pa.terminate()
        if porcupine: porcupine.delete()
