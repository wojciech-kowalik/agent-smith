"""
Smith Assistant Configuration
Contains Smith-specific factory function.
"""

from .assistent import Assistant

def create_smith_assistant() -> Assistant:
    """
    Creates and returns an Smith assistant instance with default configuration.
    
    Returns:
        Assistant: Configured Smith assistant instance
    """
    # Assistant name displayed in the chat
    assistant_name = "SMITH"
    
    # System role/prompt for the assistant
    system_role = "You are a helpful assistant named Smith. Your task is to help the user solve problems, answer questions and provide information in a polite and understandable way. Reply in the language the user writes in."
    
    return Assistant(
        system_prompt=system_role,
        name=assistant_name
    )
