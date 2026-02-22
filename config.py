"""
Configuration file for the Automated Book Generation System.
Update these settings before running the system.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================
# Option 1: SQLite (Default - local database)
DATABASE_TYPE = "sqlite"
SQLITE_DB_PATH = "book_generator.db"

# Option 2: Supabase (uncomment and configure if using Supabase)
# DATABASE_TYPE = "supabase"
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# =============================================================================
# LLM CONFIGURATION
# =============================================================================
# Supported providers: "openai", "anthropic", "gemini", "ollama"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# Anthropic Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

# Google Gemini Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")

# Ollama Configuration (FREE - Local LLM)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")

# =============================================================================
# NOTIFICATION CONFIGURATION
# =============================================================================
# Email (SMTP) Configuration
SMTP_ENABLED = os.getenv("SMTP_ENABLED", "false").lower() == "true"
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "")
SMTP_TO_EMAIL = os.getenv("SMTP_TO_EMAIL", "")

# MS Teams Webhook Configuration
TEAMS_WEBHOOK_ENABLED = os.getenv("TEAMS_WEBHOOK_ENABLED", "false").lower() == "true"
TEAMS_WEBHOOK_URL = os.getenv("TEAMS_WEBHOOK_URL", "")

# =============================================================================
# OUTPUT CONFIGURATION
# =============================================================================
OUTPUT_DIRECTORY = os.getenv("OUTPUT_DIRECTORY", "output")
OUTPUT_FORMATS = ["docx", "pdf", "txt"]  # Supported: docx, pdf, txt

# =============================================================================
# INPUT CONFIGURATION
# =============================================================================
INPUT_FILE_PATH = os.getenv("INPUT_FILE_PATH", "input/books.xlsx")

# =============================================================================
# WEB SEARCH CONFIGURATION (Optional)
# =============================================================================
WEB_SEARCH_ENABLED = os.getenv("WEB_SEARCH_ENABLED", "false").lower() == "true"
SERP_API_KEY = os.getenv("SERP_API_KEY", "")

# =============================================================================
# GENERATION SETTINGS
# =============================================================================
MAX_CHAPTER_TOKENS = int(os.getenv("MAX_CHAPTER_TOKENS", "4000"))
MAX_OUTLINE_TOKENS = int(os.getenv("MAX_OUTLINE_TOKENS", "2000"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
