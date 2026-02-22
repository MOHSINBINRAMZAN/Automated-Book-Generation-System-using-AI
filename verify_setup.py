"""
Setup Verification Script for the Automated Book Generation System.
Run this to check if everything is configured correctly.
"""

import os
import sys

def check_mark(passed: bool) -> str:
    return "✓" if passed else "✗"

def print_section(title: str):
    print(f"\n{'='*50}")
    print(f"  {title}")
    print('='*50)

def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║         AUTOMATED BOOK GENERATION SYSTEM                     ║
║         Setup Verification                                   ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    all_passed = True
    warnings = []
    
    # Check Python version
    print_section("Python Environment")
    py_version = sys.version_info
    py_ok = py_version.major >= 3 and py_version.minor >= 9
    print(f"  {check_mark(py_ok)} Python {py_version.major}.{py_version.minor}.{py_version.micro}")
    if not py_ok:
        all_passed = False
        print("    → Python 3.9+ required")
    
    # Check required packages
    print_section("Required Packages")
    
    packages = [
        ("python-dotenv", "dotenv"),
        ("openai", "openai"),
        ("python-docx", "docx"),
        ("reportlab", "reportlab"),
        ("pandas", "pandas"),
        ("openpyxl", "openpyxl"),
        ("requests", "requests"),
    ]
    
    optional_packages = [
        ("anthropic", "anthropic"),
        ("google-generativeai", "google.generativeai"),
        ("supabase", "supabase"),
        ("flask", "flask"),
        ("google-search-results", "serpapi"),
    ]
    
    for name, import_name in packages:
        try:
            __import__(import_name)
            print(f"  {check_mark(True)} {name}")
        except ImportError:
            print(f"  {check_mark(False)} {name} (run: pip install {name})")
            all_passed = False
    
    print("\n  Optional packages:")
    for name, import_name in optional_packages:
        try:
            __import__(import_name)
            print(f"  {check_mark(True)} {name}")
        except ImportError:
            print(f"  ○ {name} (optional)")
    
    # Check environment configuration
    print_section("Environment Configuration")
    
    env_file = os.path.exists(".env")
    print(f"  {check_mark(env_file)} .env file exists")
    
    if env_file:
        from dotenv import load_dotenv
        load_dotenv()
        
        # Check LLM provider
        llm_provider = os.getenv("LLM_PROVIDER", "")
        print(f"  {check_mark(bool(llm_provider))} LLM_PROVIDER: {llm_provider or 'not set'}")
        
        # Check API keys based on provider
        if llm_provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY", "")
            has_key = bool(api_key) and api_key != "your_openai_api_key_here"
            print(f"  {check_mark(has_key)} OPENAI_API_KEY: {'configured' if has_key else 'not set'}")
            if not has_key:
                all_passed = False
                
        elif llm_provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY", "")
            has_key = bool(api_key) and "your_" not in api_key
            print(f"  {check_mark(has_key)} ANTHROPIC_API_KEY: {'configured' if has_key else 'not set'}")
            if not has_key:
                all_passed = False
                
        elif llm_provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY", "")
            has_key = bool(api_key) and "your_" not in api_key
            print(f"  {check_mark(has_key)} GEMINI_API_KEY: {'configured' if has_key else 'not set'}")
            if not has_key:
                all_passed = False
        
        # Check optional configs
        smtp_enabled = os.getenv("SMTP_ENABLED", "false").lower() == "true"
        teams_enabled = os.getenv("TEAMS_WEBHOOK_ENABLED", "false").lower() == "true"
        
        print(f"\n  Notifications:")
        print(f"  ○ Email (SMTP): {'enabled' if smtp_enabled else 'disabled'}")
        print(f"  ○ MS Teams: {'enabled' if teams_enabled else 'disabled'}")
    else:
        all_passed = False
        print("    → Copy .env.example to .env and add your API keys")
    
    # Check directories
    print_section("Directories")
    
    dirs = ["input", "output", "modules", "templates"]
    for d in dirs:
        exists = os.path.isdir(d)
        print(f"  {check_mark(exists)} {d}/")
        if not exists:
            warnings.append(f"Create {d}/ directory")
    
    # Check key files
    print_section("Key Files")
    
    files = [
        "main.py",
        "orchestrator.py",
        "config.py",
        "web_ui.py",
        "modules/database.py",
        "modules/llm.py",
        "modules/stages.py",
    ]
    
    for f in files:
        exists = os.path.isfile(f)
        print(f"  {check_mark(exists)} {f}")
    
    # Test database initialization
    print_section("Database Test")
    
    try:
        from modules.database import init_database
        db = init_database()
        print(f"  {check_mark(True)} Database initialized successfully")
    except Exception as e:
        print(f"  {check_mark(False)} Database error: {e}")
        all_passed = False
    
    # Summary
    print_section("Summary")
    
    if all_passed:
        print("""
  ✅ All checks passed! The system is ready to use.
  
  Quick Start:
    1. CLI:     python main.py create "Book Title" "notes..."
    2. Web UI:  python web_ui.py (then open http://localhost:5000)
    3. Import:  python main.py import input/sample_books.json
        """)
    else:
        print("""
  ⚠️ Some checks failed. Please fix the issues above.
  
  Common fixes:
    1. Install missing packages: pip install -r requirements.txt
    2. Add API keys to .env file
    3. Ensure directories exist
        """)
    
    if warnings:
        print("\n  Warnings:")
        for w in warnings:
            print(f"    - {w}")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
