"""
Assistant module initialization
Exports the Assistant class and assistant factory functions.
"""

from .assistent import Assistant
from .smith import create_smith_assistant

__all__ = ['Assistant', 'create_smith_assistant']
