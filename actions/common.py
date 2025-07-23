# actions/common.py - Simplified common utilities
"""
Common utilities for action modules
"""

import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

def get_confirmation(user_response: str, context_question: str) -> str:
    """
    Get confirmation intent from user response.
    
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
        return "deny"