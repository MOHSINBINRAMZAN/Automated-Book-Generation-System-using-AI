"""
Modules package for the Automated Book Generation System.
"""

from .database import get_database, init_database, DatabaseInterface
from .llm import get_llm_client, LLMInterface, PromptTemplates
from .notifications import NotificationService, get_notification_service
from .exporter import BookExporter, get_exporter
from .input_handler import InputHandler, get_input_handler
from .stages import OutlineStage, ChapterStage, CompilationStage
