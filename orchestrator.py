"""
Book Generation Orchestrator
Main workflow controller for the Automated Book Generation System.
"""

import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from modules.database import get_database, init_database, DatabaseInterface
from modules.llm import get_llm_client, LLMInterface
from modules.notifications import get_notification_service, NotificationService
from modules.exporter import get_exporter
from modules.input_handler import get_input_handler, create_sample_excel
from modules.stages import OutlineStage, ChapterStage, CompilationStage

import config


class BookGenerationOrchestrator:
    """
    Main orchestrator for the book generation workflow.
    
    Workflow:
    1. Read input (from file or manual entry)
    2. Generate outline (with human feedback loop)
    3. Generate chapters (with context chaining and feedback)
    4. Compile final book
    """
    
    def __init__(self):
        self.db = get_database()
        self.llm = get_llm_client()
        self.notifications = get_notification_service()
        
        # Initialize stages
        self.outline_stage = OutlineStage(self.db, self.llm, self.notifications)
        self.chapter_stage = ChapterStage(self.db, self.llm, self.notifications)
        self.compilation_stage = CompilationStage(self.db, get_exporter(), self.notifications)
    
    def initialize(self) -> bool:
        """Initialize the system (database, etc.)."""
        try:
            self.db.initialize()
            return True
        except Exception as e:
            print(f"✗ Initialization failed: {e}")
            return False
    
    # =========================================================================
    # BOOK MANAGEMENT
    # =========================================================================
    
    def create_book(self, title: str, notes_on_outline_before: str = "") -> Dict[str, Any]:
        """Create a new book entry."""
        if not title:
            return {"success": False, "error": "Title is required"}
        
        if not notes_on_outline_before:
            return {
                "success": False,
                "error": "notes_on_outline_before is required to generate outline"
            }
        
        book_id = self.db.create_book(title, notes_on_outline_before)
        
        self.db.log_event(
            book_id,
            'book_created',
            f"New book created: {title}",
            {'notes_on_outline_before': notes_on_outline_before[:200]}
        )
        
        return {
            "success": True,
            "book_id": book_id,
            "message": f"Book '{title}' created successfully"
        }
    
    def import_books_from_file(self, file_path: str = None) -> Dict[str, Any]:
        """Import books from input file (Excel, CSV, JSON)."""
        try:
            handler = get_input_handler(file_path)
            books = handler.read_books()
            
            created = []
            errors = []
            
            for i, book in enumerate(books):
                is_valid, validation_errors = handler.validate_book(book)
                
                if is_valid:
                    result = self.create_book(
                        book['title'],
                        book.get('notes_on_outline_before', '')
                    )
                    if result['success']:
                        created.append({
                            'book_id': result['book_id'],
                            'title': book['title']
                        })
                    else:
                        errors.append({
                            'row': i + 1,
                            'title': book.get('title', 'Unknown'),
                            'error': result['error']
                        })
                else:
                    errors.append({
                        'row': i + 1,
                        'title': book.get('title', 'Unknown'),
                        'error': '; '.join(validation_errors)
                    })
            
            return {
                "success": True,
                "created": created,
                "errors": errors,
                "message": f"Imported {len(created)} books, {len(errors)} errors"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_book_status(self, book_id: int) -> Dict[str, Any]:
        """Get comprehensive status of a book."""
        book = self.db.get_book(book_id)
        if not book:
            return {"success": False, "error": "Book not found"}
        
        chapters = self.db.get_chapters_by_book(book_id)
        
        # Determine current stage
        if not book.get('outline'):
            stage = "outline_pending"
            next_action = "Generate outline"
        elif book.get('status_outline_notes') != 'no_notes_needed':
            stage = "outline_review"
            next_action = "Review outline and set status"
        elif not chapters:
            stage = "chapters_init"
            next_action = "Initialize chapters from outline"
        else:
            pending_chapters = [c['chapter_number'] for c in chapters if c.get('status') != 'approved']
            if pending_chapters:
                stage = "chapters_in_progress"
                next_action = f"Generate/review chapters: {pending_chapters}"
            elif book.get('final_review_notes_status') != 'no_notes_needed':
                stage = "final_review"
                next_action = "Set final_review_notes_status to proceed"
            elif book.get('book_output_status') == 'completed':
                stage = "completed"
                next_action = "Book generation complete"
            else:
                stage = "compilation"
                next_action = "Compile final book"
        
        return {
            "success": True,
            "book_id": book_id,
            "title": book['title'],
            "stage": stage,
            "next_action": next_action,
            "outline_status": book.get('status_outline_notes', 'no'),
            "chapters": [
                {
                    "number": c['chapter_number'],
                    "title": c['title'],
                    "status": c.get('status', 'pending')
                }
                for c in chapters
            ],
            "chapter_notes_status": book.get('chapter_notes_status', 'no'),
            "final_review_status": book.get('final_review_notes_status', 'no'),
            "output_status": book.get('book_output_status', 'pending'),
            "output_file": book.get('output_file_path', '')
        }
    
    def list_all_books(self) -> List[Dict[str, Any]]:
        """List all books with their status."""
        books = self.db.get_all_books()
        return [
            {
                "id": b['id'],
                "title": b['title'],
                "output_status": b.get('book_output_status', 'pending'),
                "created_at": b.get('created_at')
            }
            for b in books
        ]
    
    # =========================================================================
    # WORKFLOW ACTIONS
    # =========================================================================
    
    def generate_outline(self, book_id: int) -> Dict[str, Any]:
        """Generate outline for a book."""
        return self.outline_stage.generate_outline(book_id)
    
    def regenerate_outline(self, book_id: int) -> Dict[str, Any]:
        """Regenerate outline based on feedback."""
        return self.outline_stage.regenerate_outline(book_id)
    
    def approve_outline(self, book_id: int) -> Dict[str, Any]:
        """Approve outline and proceed to chapters."""
        self.db.update_book(book_id, status_outline_notes='no_notes_needed')
        
        # Initialize chapters
        result = self.chapter_stage.initialize_chapters(book_id)
        
        if result['success']:
            self.db.log_event(book_id, 'outline_approved', "Outline approved, chapters initialized")
            return {
                "success": True,
                "message": "Outline approved. Chapters initialized.",
                "chapters": result['chapters']
            }
        return result
    
    def add_outline_feedback(self, book_id: int, notes: str) -> Dict[str, Any]:
        """Add feedback notes for outline regeneration."""
        self.db.update_book(
            book_id,
            notes_on_outline_after=notes,
            status_outline_notes='yes'
        )
        return {
            "success": True,
            "message": "Feedback notes added. Ready to regenerate outline."
        }
    
    def generate_chapter(self, book_id: int, chapter_number: int) -> Dict[str, Any]:
        """Generate a specific chapter."""
        return self.chapter_stage.generate_chapter(book_id, chapter_number)
    
    def generate_all_chapters(self, book_id: int, auto_approve: bool = False) -> Dict[str, Any]:
        """Generate all chapters sequentially."""
        chapters = self.db.get_chapters_by_book(book_id)
        if not chapters:
            return {"success": False, "error": "No chapters initialized"}
        
        results = []
        for chapter in sorted(chapters, key=lambda x: x['chapter_number']):
            if chapter.get('status') == 'approved':
                results.append({
                    "chapter": chapter['chapter_number'],
                    "status": "skipped",
                    "reason": "Already approved"
                })
                continue
            
            result = self.chapter_stage.generate_chapter(book_id, chapter['chapter_number'])
            
            if result['success'] and auto_approve:
                self.chapter_stage.approve_chapter(chapter['id'])
                result['auto_approved'] = True
            
            results.append({
                "chapter": chapter['chapter_number'],
                "status": "success" if result['success'] else "failed",
                "result": result
            })
        
        return {
            "success": True,
            "results": results,
            "message": f"Processed {len(results)} chapters"
        }
    
    def regenerate_chapter(self, book_id: int, chapter_number: int) -> Dict[str, Any]:
        """Regenerate a chapter based on feedback."""
        return self.chapter_stage.regenerate_chapter(book_id, chapter_number)
    
    def add_chapter_feedback(
        self,
        book_id: int,
        chapter_number: int,
        notes: str
    ) -> Dict[str, Any]:
        """Add feedback notes for a chapter."""
        chapters = self.db.get_chapters_by_book(book_id)
        chapter = next((c for c in chapters if c['chapter_number'] == chapter_number), None)
        
        if not chapter:
            return {"success": False, "error": f"Chapter {chapter_number} not found"}
        
        self.db.update_chapter(chapter['id'], chapter_notes=notes, status='review')
        
        return {
            "success": True,
            "message": f"Feedback added for Chapter {chapter_number}. Ready to regenerate."
        }
    
    def approve_chapter(self, book_id: int, chapter_number: int) -> Dict[str, Any]:
        """Approve a chapter."""
        chapters = self.db.get_chapters_by_book(book_id)
        chapter = next((c for c in chapters if c['chapter_number'] == chapter_number), None)
        
        if not chapter:
            return {"success": False, "error": f"Chapter {chapter_number} not found"}
        
        result = self.chapter_stage.approve_chapter(chapter['id'])
        
        # Check if all chapters are now complete
        all_complete, pending = self.chapter_stage.check_all_chapters_complete(book_id)
        if all_complete:
            book = self.db.get_book(book_id)
            self.notifications.notify_all_chapters_complete(
                book_id, book['title'], len(chapters)
            )
            result['all_chapters_complete'] = True
        
        return result
    
    def compile_book(self, book_id: int, formats: List[str] = None) -> Dict[str, Any]:
        """Compile final book."""
        # First, set final review status if not set
        book = self.db.get_book(book_id)
        if book and book.get('final_review_notes_status') == 'no':
            self.db.update_book(book_id, final_review_notes_status='no_notes_needed')
        
        return self.compilation_stage.compile_book(book_id, formats)
    
    # =========================================================================
    # AUTOMATED WORKFLOW
    # =========================================================================
    
    def run_automated_workflow(
        self,
        book_id: int,
        auto_approve_outline: bool = False,
        auto_approve_chapters: bool = False
    ) -> Dict[str, Any]:
        """
        Run automated workflow for a book.
        
        This will:
        1. Generate outline (auto-approve if specified)
        2. Initialize and generate all chapters
        3. Compile final book
        
        Note: In production, you'd want human review at each stage.
        """
        results = {
            "book_id": book_id,
            "stages": []
        }
        
        # Stage 1: Outline
        print(f"\n{'='*50}")
        print("STAGE 1: Outline Generation")
        print('='*50)
        
        book = self.db.get_book(book_id)
        if not book:
            return {"success": False, "error": "Book not found"}
        
        if not book.get('outline'):
            outline_result = self.generate_outline(book_id)
            results['stages'].append({
                "stage": "outline_generation",
                "result": outline_result
            })
            
            if not outline_result['success']:
                return {"success": False, "error": outline_result['error'], "results": results}
            
            if auto_approve_outline:
                self.approve_outline(book_id)
                results['stages'].append({
                    "stage": "outline_approval",
                    "result": {"auto_approved": True}
                })
        else:
            print("✓ Outline already exists")
            if book.get('status_outline_notes') != 'no_notes_needed' and auto_approve_outline:
                self.approve_outline(book_id)
        
        # Stage 2: Chapters
        print(f"\n{'='*50}")
        print("STAGE 2: Chapter Generation")
        print('='*50)
        
        # Initialize chapters if needed
        chapters = self.db.get_chapters_by_book(book_id)
        if not chapters:
            init_result = self.chapter_stage.initialize_chapters(book_id)
            results['stages'].append({
                "stage": "chapters_initialization",
                "result": init_result
            })
            chapters = self.db.get_chapters_by_book(book_id)
        
        # Generate chapters
        for chapter in sorted(chapters, key=lambda x: x['chapter_number']):
            if chapter.get('status') == 'approved':
                print(f"✓ Chapter {chapter['chapter_number']} already approved")
                continue
            
            print(f"\nGenerating Chapter {chapter['chapter_number']}: {chapter['title']}")
            
            chapter_result = self.generate_chapter(book_id, chapter['chapter_number'])
            results['stages'].append({
                "stage": f"chapter_{chapter['chapter_number']}_generation",
                "result": chapter_result
            })
            
            if chapter_result['success'] and auto_approve_chapters:
                approval = self.approve_chapter(book_id, chapter['chapter_number'])
                results['stages'].append({
                    "stage": f"chapter_{chapter['chapter_number']}_approval",
                    "result": approval
                })
        
        # Stage 3: Compilation
        print(f"\n{'='*50}")
        print("STAGE 3: Final Compilation")
        print('='*50)
        
        # Check if all chapters are approved
        all_complete, pending = self.chapter_stage.check_all_chapters_complete(book_id)
        
        if not all_complete:
            results['stages'].append({
                "stage": "compilation",
                "result": {
                    "success": False,
                    "error": f"Chapters pending approval: {pending}"
                }
            })
            return {
                "success": False,
                "error": f"Cannot compile. Chapters pending: {pending}",
                "results": results
            }
        
        # Compile
        compile_result = self.compile_book(book_id)
        results['stages'].append({
            "stage": "compilation",
            "result": compile_result
        })
        
        print(f"\n{'='*50}")
        print("WORKFLOW COMPLETE")
        print('='*50)
        
        return {
            "success": compile_result['success'],
            "results": results,
            "output_files": compile_result.get('output_files', {})
        }
    
    # =========================================================================
    # POLLING / MONITORING
    # =========================================================================
    
    def check_pending_actions(self) -> List[Dict[str, Any]]:
        """Check all books for pending actions (for notification system)."""
        books = self.db.get_all_books()
        pending_actions = []
        
        for book in books:
            status = self.get_book_status(book['id'])
            
            if status.get('stage') not in ['completed']:
                pending_actions.append({
                    "book_id": book['id'],
                    "title": book['title'],
                    "stage": status.get('stage'),
                    "next_action": status.get('next_action')
                })
        
        return pending_actions
    
    def get_logs(self, book_id: int = None) -> List[Dict[str, Any]]:
        """Get event logs."""
        return self.db.get_logs(book_id)


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def get_orchestrator() -> BookGenerationOrchestrator:
    """Get orchestrator instance."""
    return BookGenerationOrchestrator()


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # Quick test
    orchestrator = BookGenerationOrchestrator()
    orchestrator.initialize()
    
    print("\n✓ Book Generation System initialized")
    print("Use the CLI (main.py) or import this module to use the system.")
