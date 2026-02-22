"""
Workflow Stages Module for the Automated Book Generation System.
Contains the core logic for outline generation, chapter generation, and compilation.
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from modules.database import get_database, DatabaseInterface
from modules.llm import get_llm_client, PromptTemplates, LLMInterface
from modules.notifications import get_notification_service, NotificationService
from modules.exporter import get_exporter, BookExporter


# =============================================================================
# OUTLINE STAGE
# =============================================================================

class OutlineStage:
    """
    Stage 1: Outline Generation
    
    Logic:
    - Only generate outlines if notes_on_outline_before exists
    - After outline: check status_outline_notes
        - yes: wait for notes
        - no_notes_needed: proceed to chapters
        - no/empty: pause
    """
    
    def __init__(
        self,
        db: DatabaseInterface = None,
        llm: LLMInterface = None,
        notifications: NotificationService = None
    ):
        self.db = db or get_database()
        self.llm = llm or get_llm_client()
        self.notifications = notifications or get_notification_service()
    
    def can_generate_outline(self, book: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if outline can be generated."""
        if not book.get('notes_on_outline_before'):
            return False, "notes_on_outline_before is required to generate outline"
        
        if book.get('outline'):
            return False, "Outline already exists"
        
        return True, "Ready to generate outline"
    
    def generate_outline(self, book_id: int) -> Dict[str, Any]:
        """Generate outline for a book."""
        book = self.db.get_book(book_id)
        if not book:
            return {"success": False, "error": "Book not found"}
        
        can_generate, reason = self.can_generate_outline(book)
        if not can_generate:
            return {"success": False, "error": reason}
        
        # Generate outline using LLM
        prompt = PromptTemplates.outline_generation(
            title=book['title'],
            notes=book['notes_on_outline_before']
        )
        
        system_prompt = """You are an expert book outline creator. Create detailed, well-structured 
book outlines that provide a clear roadmap for comprehensive book content. Each chapter should 
have clear objectives and flow logically from one to the next."""
        
        try:
            outline = self.llm.generate(prompt, system_prompt, max_tokens=2000)
            
            # Save outline to database
            self.db.update_book(
                book_id,
                outline=outline,
                status_outline_notes='no',
                book_output_status='in_progress'
            )
            
            # Save outline draft version
            self.db.save_outline_draft(
                book_id,
                outline,
                notes_used=book['notes_on_outline_before']
            )
            
            # Log event
            self.db.log_event(
                book_id,
                'outline_generated',
                f"Outline generated for '{book['title']}'",
                {'outline_length': len(outline)}
            )
            
            # Send notification
            self.notifications.notify_outline_ready(book_id, book['title'])
            
            return {
                "success": True,
                "book_id": book_id,
                "outline": outline,
                "message": "Outline generated successfully. Awaiting review."
            }
            
        except Exception as e:
            self.db.log_event(book_id, 'error', f"Outline generation failed: {str(e)}")
            self.notifications.notify_error(book_id, book['title'], str(e), "Outline Generation")
            return {"success": False, "error": str(e)}
    
    def regenerate_outline(self, book_id: int) -> Dict[str, Any]:
        """Regenerate outline based on feedback notes."""
        book = self.db.get_book(book_id)
        if not book:
            return {"success": False, "error": "Book not found"}
        
        if not book.get('outline'):
            return {"success": False, "error": "No existing outline to regenerate"}
        
        if not book.get('notes_on_outline_after'):
            return {"success": False, "error": "No feedback notes provided for regeneration"}
        
        # Generate improved outline using LLM
        prompt = PromptTemplates.outline_regeneration(
            title=book['title'],
            current_outline=book['outline'],
            feedback_notes=book['notes_on_outline_after']
        )
        
        system_prompt = """You are an expert book outline editor. Improve the outline based on 
the provided feedback while maintaining coherence and structure."""
        
        try:
            new_outline = self.llm.generate(prompt, system_prompt, max_tokens=2000)
            
            # Save new outline
            self.db.update_book(
                book_id,
                outline=new_outline,
                status_outline_notes='no'
            )
            
            # Save outline draft version
            self.db.save_outline_draft(
                book_id,
                new_outline,
                notes_used=book['notes_on_outline_after']
            )
            
            # Log event
            self.db.log_event(
                book_id,
                'outline_regenerated',
                f"Outline regenerated for '{book['title']}' based on feedback",
                {'notes': book['notes_on_outline_after'][:200]}
            )
            
            # Send notification
            self.notifications.notify_outline_ready(book_id, book['title'])
            
            return {
                "success": True,
                "book_id": book_id,
                "outline": new_outline,
                "message": "Outline regenerated successfully. Awaiting review."
            }
            
        except Exception as e:
            self.db.log_event(book_id, 'error', f"Outline regeneration failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def check_outline_status(self, book_id: int) -> Dict[str, Any]:
        """Check outline status and determine next action."""
        book = self.db.get_book(book_id)
        if not book:
            return {"status": "error", "message": "Book not found"}
        
        status = book.get('status_outline_notes', 'no')
        
        if status == 'no_notes_needed':
            return {
                "status": "proceed",
                "message": "Ready to proceed to chapter generation",
                "next_stage": "chapters"
            }
        elif status == 'yes':
            if book.get('notes_on_outline_after'):
                return {
                    "status": "regenerate",
                    "message": "Notes provided. Ready to regenerate outline."
                }
            else:
                return {
                    "status": "waiting",
                    "message": "Waiting for feedback notes on outline"
                }
        else:  # 'no' or empty
            return {
                "status": "paused",
                "message": "Paused. Set status_outline_notes to 'yes' for changes or 'no_notes_needed' to proceed."
            }


# =============================================================================
# CHAPTER STAGE
# =============================================================================

class ChapterStage:
    """
    Stage 2: Chapter Generation
    
    Logic:
    - Parse outline to extract chapters
    - For each chapter:
        - Use summary of all previous chapters as context
        - If chapter_notes_status = yes, wait for notes
        - If no_notes_needed, proceed
        - If no/empty, pause
    """
    
    def __init__(
        self,
        db: DatabaseInterface = None,
        llm: LLMInterface = None,
        notifications: NotificationService = None
    ):
        self.db = db or get_database()
        self.llm = llm or get_llm_client()
        self.notifications = notifications or get_notification_service()
    
    def parse_outline_chapters(self, outline: str) -> List[Dict[str, str]]:
        """Parse outline to extract chapter titles and content."""
        chapters = []
        
        # Pattern to match chapter headings
        # Matches: "Chapter 1:", "1.", "Chapter One:", etc.
        chapter_pattern = r'(?:Chapter\s*)?(\d+|[A-Za-z]+)[.:]\s*(.+?)(?=(?:Chapter\s*)?\d+[.:]|\Z)'
        
        # Try to find structured chapters
        lines = outline.split('\n')
        current_chapter = None
        current_content = []
        chapter_num = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this is a chapter heading
            is_chapter = False
            
            # Pattern 1: "Chapter X: Title" or "Chapter X - Title"
            match1 = re.match(r'^Chapter\s*(\d+)\s*[:\-]\s*(.+)$', line, re.IGNORECASE)
            # Pattern 2: "X. Title" or "X: Title"
            match2 = re.match(r'^(\d+)\s*[.:\-]\s*(.+)$', line)
            # Pattern 3: "# Chapter Title" (markdown)
            match3 = re.match(r'^#+\s*(?:Chapter\s*\d+\s*[:\-]\s*)?(.+)$', line, re.IGNORECASE)
            
            if match1:
                is_chapter = True
                chapter_num = int(match1.group(1))
                chapter_title = match1.group(2).strip()
            elif match2 and int(match2.group(1)) <= 20:  # Assume max 20 chapters
                is_chapter = True
                chapter_num = int(match2.group(1))
                chapter_title = match2.group(2).strip()
            elif match3 and 'chapter' in line.lower():
                is_chapter = True
                chapter_num += 1
                chapter_title = match3.group(1).strip()
            
            if is_chapter:
                # Save previous chapter
                if current_chapter:
                    chapters.append({
                        'number': current_chapter['number'],
                        'title': current_chapter['title'],
                        'outline_content': '\n'.join(current_content)
                    })
                
                # Start new chapter
                current_chapter = {
                    'number': chapter_num,
                    'title': chapter_title
                }
                current_content = []
            elif current_chapter:
                current_content.append(line)
        
        # Save last chapter
        if current_chapter:
            chapters.append({
                'number': current_chapter['number'],
                'title': current_chapter['title'],
                'outline_content': '\n'.join(current_content)
            })
        
        # If no chapters found, create a default structure
        if not chapters:
            chapters = [
                {'number': 1, 'title': 'Introduction', 'outline_content': outline[:500]},
                {'number': 2, 'title': 'Main Content', 'outline_content': outline[500:1000]},
                {'number': 3, 'title': 'Conclusion', 'outline_content': outline[1000:]}
            ]
        
        return chapters
    
    def initialize_chapters(self, book_id: int) -> Dict[str, Any]:
        """Parse outline and create chapter records in database."""
        book = self.db.get_book(book_id)
        if not book:
            return {"success": False, "error": "Book not found"}
        
        if not book.get('outline'):
            return {"success": False, "error": "No outline available"}
        
        # Check if chapters already exist
        existing_chapters = self.db.get_chapters_by_book(book_id)
        if existing_chapters:
            return {"success": False, "error": "Chapters already initialized"}
        
        # Parse outline
        parsed_chapters = self.parse_outline_chapters(book['outline'])
        
        # Create chapter records
        created_chapters = []
        for ch in parsed_chapters:
            chapter_id = self.db.create_chapter(
                book_id=book_id,
                chapter_number=ch['number'],
                title=ch['title']
            )
            created_chapters.append({
                'id': chapter_id,
                'number': ch['number'],
                'title': ch['title']
            })
        
        # Log event
        self.db.log_event(
            book_id,
            'chapters_initialized',
            f"Initialized {len(created_chapters)} chapters",
            {'chapters': created_chapters}
        )
        
        return {
            "success": True,
            "book_id": book_id,
            "chapters": created_chapters,
            "message": f"Created {len(created_chapters)} chapter records"
        }
    
    def get_previous_summaries(self, book_id: int, up_to_chapter: int) -> str:
        """Get summaries of all previous chapters for context."""
        chapters = self.db.get_chapters_by_book(book_id)
        
        summaries = []
        for ch in chapters:
            if ch['chapter_number'] < up_to_chapter and ch.get('summary'):
                summaries.append(
                    f"Chapter {ch['chapter_number']} ({ch['title']}): {ch['summary']}"
                )
        
        if not summaries:
            return ""
        
        return "Summary of previous chapters:\n" + "\n\n".join(summaries)
    
    def generate_chapter(self, book_id: int, chapter_number: int) -> Dict[str, Any]:
        """Generate content for a specific chapter."""
        book = self.db.get_book(book_id)
        if not book:
            return {"success": False, "error": "Book not found"}
        
        chapters = self.db.get_chapters_by_book(book_id)
        chapter = next((c for c in chapters if c['chapter_number'] == chapter_number), None)
        
        if not chapter:
            return {"success": False, "error": f"Chapter {chapter_number} not found"}
        
        if chapter.get('content') and chapter.get('status') == 'approved':
            return {"success": False, "error": "Chapter already approved"}
        
        # Get chapter outline from parsed outline
        parsed_chapters = self.parse_outline_chapters(book['outline'])
        chapter_outline = next(
            (c['outline_content'] for c in parsed_chapters if c['number'] == chapter_number),
            ""
        )
        
        # Get previous chapter summaries
        previous_summaries = self.get_previous_summaries(book_id, chapter_number)
        
        # Get chapter notes if any
        chapter_notes = chapter.get('chapter_notes', '')
        
        # Generate chapter content
        prompt = PromptTemplates.chapter_generation(
            title=book['title'],
            chapter_number=chapter_number,
            chapter_title=chapter['title'],
            chapter_outline=chapter_outline,
            previous_summaries=previous_summaries,
            chapter_notes=chapter_notes
        )
        
        system_prompt = """You are an expert book writer. Write engaging, informative, and 
well-structured chapter content. Maintain consistency with the book's overall tone and 
build upon concepts from previous chapters when applicable."""
        
        try:
            # Update status to generating
            self.db.update_chapter(chapter['id'], status='generating')
            
            # Generate content
            content = self.llm.generate(prompt, system_prompt, max_tokens=4000)
            
            # Generate summary for context chaining
            summary_prompt = PromptTemplates.chapter_summary(
                content, chapter_number, chapter['title']
            )
            summary = self.llm.generate(summary_prompt, max_tokens=500)
            
            # Update chapter in database
            self.db.update_chapter(
                chapter['id'],
                content=content,
                summary=summary,
                status='review'
            )
            
            # Log event
            self.db.log_event(
                book_id,
                'chapter_generated',
                f"Chapter {chapter_number} generated",
                {'chapter_title': chapter['title'], 'content_length': len(content)}
            )
            
            # Send notification
            self.notifications.notify_chapter_ready(
                book_id, book['title'], chapter_number, chapter['title']
            )
            
            return {
                "success": True,
                "book_id": book_id,
                "chapter_id": chapter['id'],
                "chapter_number": chapter_number,
                "content": content,
                "summary": summary,
                "message": "Chapter generated successfully. Awaiting review."
            }
            
        except Exception as e:
            self.db.update_chapter(chapter['id'], status='pending')
            self.db.log_event(book_id, 'error', f"Chapter {chapter_number} generation failed: {str(e)}")
            self.notifications.notify_error(
                book_id, book['title'], str(e), f"Chapter {chapter_number} Generation"
            )
            return {"success": False, "error": str(e)}
    
    def regenerate_chapter(self, book_id: int, chapter_number: int) -> Dict[str, Any]:
        """Regenerate chapter based on feedback notes."""
        book = self.db.get_book(book_id)
        if not book:
            return {"success": False, "error": "Book not found"}
        
        chapters = self.db.get_chapters_by_book(book_id)
        chapter = next((c for c in chapters if c['chapter_number'] == chapter_number), None)
        
        if not chapter:
            return {"success": False, "error": f"Chapter {chapter_number} not found"}
        
        if not chapter.get('content'):
            return {"success": False, "error": "No existing content to regenerate"}
        
        if not chapter.get('chapter_notes'):
            return {"success": False, "error": "No feedback notes provided"}
        
        # Get previous summaries
        previous_summaries = self.get_previous_summaries(book_id, chapter_number)
        
        # Generate improved content
        prompt = PromptTemplates.chapter_regeneration(
            title=book['title'],
            chapter_number=chapter_number,
            chapter_title=chapter['title'],
            current_content=chapter['content'],
            feedback_notes=chapter['chapter_notes'],
            previous_summaries=previous_summaries
        )
        
        system_prompt = """You are an expert book editor. Improve the chapter based on 
the provided feedback while maintaining the book's overall coherence."""
        
        try:
            self.db.update_chapter(chapter['id'], status='regenerating')
            
            # Generate new content
            content = self.llm.generate(prompt, system_prompt, max_tokens=4000)
            
            # Generate new summary
            summary_prompt = PromptTemplates.chapter_summary(
                content, chapter_number, chapter['title']
            )
            summary = self.llm.generate(summary_prompt, max_tokens=500)
            
            # Update chapter
            self.db.update_chapter(
                chapter['id'],
                content=content,
                summary=summary,
                status='review'
            )
            
            # Log event
            self.db.log_event(
                book_id,
                'chapter_regenerated',
                f"Chapter {chapter_number} regenerated based on feedback",
                {'notes': chapter['chapter_notes'][:200]}
            )
            
            # Notification
            self.notifications.notify_chapter_ready(
                book_id, book['title'], chapter_number, chapter['title']
            )
            
            return {
                "success": True,
                "book_id": book_id,
                "chapter_id": chapter['id'],
                "chapter_number": chapter_number,
                "content": content,
                "message": "Chapter regenerated successfully. Awaiting review."
            }
            
        except Exception as e:
            self.db.update_chapter(chapter['id'], status='review')
            self.db.log_event(book_id, 'error', f"Chapter regeneration failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def approve_chapter(self, chapter_id: int) -> Dict[str, Any]:
        """Mark a chapter as approved."""
        chapter = self.db.get_chapter(chapter_id)
        if not chapter:
            return {"success": False, "error": "Chapter not found"}
        
        self.db.update_chapter(chapter_id, status='approved')
        
        # Log event
        self.db.log_event(
            chapter['book_id'],
            'chapter_approved',
            f"Chapter {chapter['chapter_number']} approved",
            {'chapter_title': chapter['title']}
        )
        
        return {
            "success": True,
            "chapter_id": chapter_id,
            "message": f"Chapter {chapter['chapter_number']} approved"
        }
    
    def check_all_chapters_complete(self, book_id: int) -> Tuple[bool, List[int]]:
        """Check if all chapters are approved. Returns (all_complete, pending_chapters)."""
        chapters = self.db.get_chapters_by_book(book_id)
        
        if not chapters:
            return False, []
        
        pending = [c['chapter_number'] for c in chapters if c.get('status') != 'approved']
        return len(pending) == 0, pending


# =============================================================================
# COMPILATION STAGE
# =============================================================================

class CompilationStage:
    """
    Stage 3: Final Compilation
    
    Logic:
    - Compile only if:
        - final_review_notes_status = no_notes_needed
        - OR notes exist for final draft
    - Export as .docx, .pdf, or .txt
    """
    
    def __init__(
        self,
        db: DatabaseInterface = None,
        exporter: BookExporter = None,
        notifications: NotificationService = None
    ):
        self.db = db or get_database()
        self.exporter = exporter or get_exporter()
        self.notifications = notifications or get_notification_service()
    
    def can_compile(self, book_id: int) -> Tuple[bool, str]:
        """Check if book can be compiled."""
        book = self.db.get_book(book_id)
        if not book:
            return False, "Book not found"
        
        # Check all chapters are approved
        chapters = self.db.get_chapters_by_book(book_id)
        if not chapters:
            return False, "No chapters found"
        
        pending = [c['chapter_number'] for c in chapters if c.get('status') != 'approved']
        if pending:
            return False, f"Chapters not approved: {pending}"
        
        # Check final review status
        final_status = book.get('final_review_notes_status', 'no')
        
        if final_status == 'no_notes_needed':
            return True, "Ready to compile"
        elif final_status == 'yes' and book.get('final_review_notes'):
            return True, "Ready to compile with final notes"
        else:
            return False, "Set final_review_notes_status to 'no_notes_needed' or provide final_review_notes"
    
    def compile_book(
        self,
        book_id: int,
        formats: List[str] = None
    ) -> Dict[str, Any]:
        """Compile book into final output files."""
        can_compile, reason = self.can_compile(book_id)
        if not can_compile:
            return {"success": False, "error": reason}
        
        book = self.db.get_book(book_id)
        chapters = self.db.get_chapters_by_book(book_id)
        
        # Sort chapters by number
        chapters = sorted(chapters, key=lambda x: x['chapter_number'])
        
        try:
            # Export to all formats
            results = self.exporter.export_all(
                title=book['title'],
                chapters=chapters,
                outline=book.get('outline'),
                formats=formats
            )
            
            # Get primary output path
            output_path = results.get('docx') or results.get('pdf') or results.get('txt')
            
            # Update book status
            self.db.update_book(
                book_id,
                book_output_status='completed',
                output_file_path=output_path or ''
            )
            
            # Log event
            self.db.log_event(
                book_id,
                'book_compiled',
                f"Book '{book['title']}' compiled successfully",
                {'output_files': results}
            )
            
            # Send notification
            self.notifications.notify_final_draft_ready(
                book_id, book['title'], output_path or 'Multiple formats'
            )
            
            return {
                "success": True,
                "book_id": book_id,
                "output_files": results,
                "message": "Book compiled successfully"
            }
            
        except Exception as e:
            self.db.update_book(book_id, book_output_status='error')
            self.db.log_event(book_id, 'error', f"Compilation failed: {str(e)}")
            self.notifications.notify_error(book_id, book['title'], str(e), "Final Compilation")
            return {"success": False, "error": str(e)}


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_outline_stage() -> OutlineStage:
    return OutlineStage()

def get_chapter_stage() -> ChapterStage:
    return ChapterStage()

def get_compilation_stage() -> CompilationStage:
    return CompilationStage()
