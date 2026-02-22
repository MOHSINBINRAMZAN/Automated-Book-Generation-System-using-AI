"""
Input Handler Module for the Automated Book Generation System.
Supports reading book data from Excel, CSV, and JSON files.
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

import config


# =============================================================================
# INPUT HANDLER
# =============================================================================

class InputHandler:
    """Handles reading book input from various file formats."""
    
    def __init__(self, input_path: str = None):
        self.input_path = input_path or config.INPUT_FILE_PATH
    
    def read_books(self) -> List[Dict[str, Any]]:
        """Read books from input file based on extension."""
        if not os.path.exists(self.input_path):
            raise FileNotFoundError(f"Input file not found: {self.input_path}")
        
        ext = os.path.splitext(self.input_path)[1].lower()
        
        if ext in ['.xlsx', '.xls']:
            return self._read_excel()
        elif ext == '.csv':
            return self._read_csv()
        elif ext == '.json':
            return self._read_json()
        else:
            raise ValueError(f"Unsupported input file format: {ext}")
    
    def _read_excel(self) -> List[Dict[str, Any]]:
        """Read books from Excel file."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("Please install pandas and openpyxl: pip install pandas openpyxl")
        
        df = pd.read_excel(self.input_path, engine='openpyxl')
        return self._process_dataframe(df)
    
    def _read_csv(self) -> List[Dict[str, Any]]:
        """Read books from CSV file."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("Please install pandas: pip install pandas")
        
        df = pd.read_csv(self.input_path)
        return self._process_dataframe(df)
    
    def _read_json(self) -> List[Dict[str, Any]]:
        """Read books from JSON file."""
        with open(self.input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle both list and single book object
        if isinstance(data, list):
            return data
        return [data]
    
    def _process_dataframe(self, df) -> List[Dict[str, Any]]:
        """Process pandas DataFrame into list of book dictionaries."""
        import pandas as pd
        
        # Clean column names
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        
        books = []
        for _, row in df.iterrows():
            book = {
                'title': str(row.get('title', '')).strip(),
                'notes_on_outline_before': str(row.get('notes_on_outline_before', '') or '').strip(),
            }
            
            # Only add books with valid titles
            if book['title'] and book['title'].lower() != 'nan':
                books.append(book)
        
        return books
    
    def validate_book(self, book: Dict[str, Any]) -> tuple:
        """Validate a book entry. Returns (is_valid, errors)."""
        errors = []
        
        # Title is mandatory
        if not book.get('title'):
            errors.append("Title is required")
        
        # Notes on outline before is required (as per spec)
        if not book.get('notes_on_outline_before'):
            errors.append("notes_on_outline_before is required to generate outline")
        
        return len(errors) == 0, errors


# =============================================================================
# INPUT FILE TEMPLATES
# =============================================================================

def create_sample_excel():
    """Create a sample Excel input file."""
    try:
        import pandas as pd
    except ImportError:
        print("Please install pandas: pip install pandas openpyxl")
        return None
    
    # Ensure input directory exists
    input_dir = os.path.dirname(config.INPUT_FILE_PATH)
    if input_dir and not os.path.exists(input_dir):
        os.makedirs(input_dir)
    
    # Sample data
    data = {
        'title': [
            'The Complete Guide to Python Programming',
            'Artificial Intelligence: From Basics to Advanced'
        ],
        'notes_on_outline_before': [
            'Focus on practical examples. Target audience: beginners to intermediate developers. Include chapters on data structures, OOP, and web development.',
            'Cover machine learning, deep learning, and neural networks. Include real-world case studies. Target: tech professionals wanting to understand AI.'
        ]
    }
    
    df = pd.DataFrame(data)
    filepath = config.INPUT_FILE_PATH
    
    if filepath.endswith('.xlsx'):
        df.to_excel(filepath, index=False, engine='openpyxl')
    else:
        # Default to xlsx
        filepath = filepath.rsplit('.', 1)[0] + '.xlsx'
        df.to_excel(filepath, index=False, engine='openpyxl')
    
    print(f"✓ Sample input file created: {filepath}")
    return filepath


def create_sample_json():
    """Create a sample JSON input file."""
    input_dir = os.path.dirname(config.INPUT_FILE_PATH)
    if input_dir and not os.path.exists(input_dir):
        os.makedirs(input_dir)
    
    sample_data = [
        {
            "title": "The Complete Guide to Python Programming",
            "notes_on_outline_before": "Focus on practical examples. Target audience: beginners to intermediate developers. Include chapters on data structures, OOP, and web development."
        },
        {
            "title": "Artificial Intelligence: From Basics to Advanced",
            "notes_on_outline_before": "Cover machine learning, deep learning, and neural networks. Include real-world case studies. Target: tech professionals wanting to understand AI."
        }
    ]
    
    filepath = os.path.join(os.path.dirname(config.INPUT_FILE_PATH) or '.', 'books.json')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2)
    
    print(f"✓ Sample input file created: {filepath}")
    return filepath


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def get_input_handler(input_path: str = None) -> InputHandler:
    """Get input handler instance."""
    return InputHandler(input_path)
