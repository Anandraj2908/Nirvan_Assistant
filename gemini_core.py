# gemini_core.py
# This module is the "brain" of the assistant. Its only job is to
# communicate with the Google Gemini API.

import os
import json
import google.generativeai as genai

# --- Configure Gemini API ---
try:
    genai.configure(api_key="")
except (AttributeError, KeyError):
    print("FATAL ERROR: GEMINI_API_KEY environment variable not found.")
    exit()

def process_command_with_gemini(command_text):
    """Sends the user's command to Gemini and returns a structured JSON object."""
    model = genai.GenerativeModel('gemini-2.0-flash')
    prompt = f"""
    You are the intelligent core of a Windows desktop AI assistant.
    Analyze the user's command and respond with a JSON object.
    The JSON object must have "command" and "parameters" keys.

    Available commands:
    1. "open_app": {{"app_name": "name"}}
    2. "search_web": {{"query": "term"}}
    3. "search_youtube": {{"query": "term"}}
    4. "play_video": {{"video_identifier": "partial title or position"}}
    5. "send_email": {{"recipient": "person", "subject": "topic"}}
    6. "exit": {{}} (Though this is handled by the GUI, it's good to have)
    7. "unsupported": {{"reason": "explanation"}}

    User's command: "{command_text}"
    ---
    Strictly output only the JSON object.
    """
    try:
        response = model.generate_content(prompt)
        json_text = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(json_text)
    except Exception as e:
        print(f"Error processing command with Gemini: {e}")
        return None
