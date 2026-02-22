"""
Automated Book Generation System - Command Line Interface
Main entry point for the application.
"""

import argparse
import sys
import json
from typing import Optional

from orchestrator import BookGenerationOrchestrator, get_orchestrator
from modules.input_handler import create_sample_excel, create_sample_json
from modules.database import init_database


def print_header():
    """Print application header."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║         AUTOMATED BOOK GENERATION SYSTEM                     ║
║         Human-in-the-Loop AI Book Writer                     ║
╚══════════════════════════════════════════════════════════════╝
    """)


def print_book_status(status: dict):
    """Pretty print book status."""
    print(f"\n{'─'*50}")
    print(f"📚 Book: {status['title']} (ID: {status['book_id']})")
    print(f"{'─'*50}")
    print(f"Stage: {status['stage']}")
    print(f"Next Action: {status['next_action']}")
    print(f"\nOutline Status: {status['outline_status']}")
    print(f"Chapter Notes Status: {status['chapter_notes_status']}")
    print(f"Final Review Status: {status['final_review_status']}")
    print(f"Output Status: {status['output_status']}")
    
    if status.get('chapters'):
        print(f"\nChapters:")
        for ch in status['chapters']:
            status_icon = "✓" if ch['status'] == 'approved' else "○"
            print(f"  {status_icon} Ch {ch['number']}: {ch['title']} [{ch['status']}]")
    
    if status.get('output_file'):
        print(f"\nOutput: {status['output_file']}")
    print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Automated Book Generation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py init                          Initialize database
  python main.py create "My Book" "notes..."   Create a new book
  python main.py import input/books.xlsx       Import books from file
  python main.py status 1                      Check book status
  python main.py outline 1                     Generate outline for book 1
  python main.py approve-outline 1             Approve outline
  python main.py chapter 1 1                   Generate chapter 1 of book 1
  python main.py approve-chapter 1 1           Approve chapter 1
  python main.py compile 1                     Compile book 1
  python main.py auto 1                        Run full automated workflow
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Init command
    subparsers.add_parser('init', help='Initialize the database')
    
    # Create sample input
    subparsers.add_parser('sample', help='Create sample input file')
    
    # Create book
    create_parser = subparsers.add_parser('create', help='Create a new book')
    create_parser.add_argument('title', help='Book title')
    create_parser.add_argument('notes', help='Notes for outline generation')
    
    # Import books
    import_parser = subparsers.add_parser('import', help='Import books from file')
    import_parser.add_argument('file', help='Path to input file (Excel/CSV/JSON)')
    
    # List books
    subparsers.add_parser('list', help='List all books')
    
    # Book status
    status_parser = subparsers.add_parser('status', help='Get book status')
    status_parser.add_argument('book_id', type=int, help='Book ID')
    
    # Generate outline
    outline_parser = subparsers.add_parser('outline', help='Generate outline')
    outline_parser.add_argument('book_id', type=int, help='Book ID')
    
    # Approve outline
    approve_outline_parser = subparsers.add_parser('approve-outline', help='Approve outline')
    approve_outline_parser.add_argument('book_id', type=int, help='Book ID')
    
    # Add outline feedback
    outline_feedback_parser = subparsers.add_parser('outline-feedback', help='Add outline feedback')
    outline_feedback_parser.add_argument('book_id', type=int, help='Book ID')
    outline_feedback_parser.add_argument('notes', help='Feedback notes')
    
    # Regenerate outline
    regen_outline_parser = subparsers.add_parser('regen-outline', help='Regenerate outline')
    regen_outline_parser.add_argument('book_id', type=int, help='Book ID')
    
    # Generate chapter
    chapter_parser = subparsers.add_parser('chapter', help='Generate a chapter')
    chapter_parser.add_argument('book_id', type=int, help='Book ID')
    chapter_parser.add_argument('chapter_num', type=int, help='Chapter number')
    
    # Generate all chapters
    all_chapters_parser = subparsers.add_parser('all-chapters', help='Generate all chapters')
    all_chapters_parser.add_argument('book_id', type=int, help='Book ID')
    all_chapters_parser.add_argument('--auto-approve', action='store_true', help='Auto-approve chapters')
    
    # Approve chapter
    approve_chapter_parser = subparsers.add_parser('approve-chapter', help='Approve chapter')
    approve_chapter_parser.add_argument('book_id', type=int, help='Book ID')
    approve_chapter_parser.add_argument('chapter_num', type=int, help='Chapter number')
    
    # Add chapter feedback
    chapter_feedback_parser = subparsers.add_parser('chapter-feedback', help='Add chapter feedback')
    chapter_feedback_parser.add_argument('book_id', type=int, help='Book ID')
    chapter_feedback_parser.add_argument('chapter_num', type=int, help='Chapter number')
    chapter_feedback_parser.add_argument('notes', help='Feedback notes')
    
    # Regenerate chapter
    regen_chapter_parser = subparsers.add_parser('regen-chapter', help='Regenerate chapter')
    regen_chapter_parser.add_argument('book_id', type=int, help='Book ID')
    regen_chapter_parser.add_argument('chapter_num', type=int, help='Chapter number')
    
    # Compile book
    compile_parser = subparsers.add_parser('compile', help='Compile final book')
    compile_parser.add_argument('book_id', type=int, help='Book ID')
    compile_parser.add_argument('--formats', nargs='+', choices=['txt', 'docx', 'pdf'], 
                                help='Output formats')
    
    # Full automated workflow
    auto_parser = subparsers.add_parser('auto', help='Run full automated workflow')
    auto_parser.add_argument('book_id', type=int, help='Book ID')
    auto_parser.add_argument('--auto-approve', action='store_true', 
                            help='Auto-approve outline and chapters')
    
    # View logs
    logs_parser = subparsers.add_parser('logs', help='View event logs')
    logs_parser.add_argument('--book-id', type=int, help='Filter by book ID')
    
    # Pending actions
    subparsers.add_parser('pending', help='Check pending actions')
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        print_header()
        parser.print_help()
        return
    
    # Initialize orchestrator
    orchestrator = get_orchestrator()
    
    # Handle commands
    try:
        if args.command == 'init':
            print_header()
            print("Initializing database...")
            orchestrator.initialize()
            print("\n✓ System initialized successfully!")
            print("\nNext steps:")
            print("  1. Copy .env.example to .env and add your API keys")
            print("  2. Create a book: python main.py create \"Book Title\" \"outline notes\"")
            print("  3. Or import from file: python main.py import books.xlsx")
        
        elif args.command == 'sample':
            print("Creating sample input files...")
            create_sample_excel()
            create_sample_json()
            print("\n✓ Sample files created in 'input/' directory")
        
        elif args.command == 'create':
            orchestrator.initialize()
            result = orchestrator.create_book(args.title, args.notes)
            if result['success']:
                print(f"\n✓ Book created: ID {result['book_id']}")
                print(f"  Next: python main.py outline {result['book_id']}")
            else:
                print(f"\n✗ Error: {result['error']}")
        
        elif args.command == 'import':
            orchestrator.initialize()
            result = orchestrator.import_books_from_file(args.file)
            if result['success']:
                print(f"\n✓ Imported {len(result['created'])} books")
                for book in result['created']:
                    print(f"  - ID {book['book_id']}: {book['title']}")
                if result['errors']:
                    print(f"\n⚠ {len(result['errors'])} errors:")
                    for err in result['errors']:
                        print(f"  - Row {err['row']}: {err['error']}")
            else:
                print(f"\n✗ Error: {result['error']}")
        
        elif args.command == 'list':
            orchestrator.initialize()
            books = orchestrator.list_all_books()
            print(f"\n{'─'*60}")
            print(f"{'ID':<5} {'Title':<35} {'Status':<15}")
            print(f"{'─'*60}")
            for book in books:
                print(f"{book['id']:<5} {book['title'][:33]:<35} {book['output_status']:<15}")
            print(f"{'─'*60}")
            print(f"Total: {len(books)} books")
        
        elif args.command == 'status':
            orchestrator.initialize()
            result = orchestrator.get_book_status(args.book_id)
            if result['success']:
                print_book_status(result)
            else:
                print(f"\n✗ Error: {result['error']}")
        
        elif args.command == 'outline':
            orchestrator.initialize()
            print(f"\nGenerating outline for book {args.book_id}...")
            result = orchestrator.generate_outline(args.book_id)
            if result['success']:
                print(f"\n✓ Outline generated!")
                print(f"\nOutline Preview:\n{'-'*40}")
                print(result['outline'][:500] + "..." if len(result['outline']) > 500 else result['outline'])
                print(f"\n  Next: Review and run 'python main.py approve-outline {args.book_id}'")
            else:
                print(f"\n✗ Error: {result['error']}")
        
        elif args.command == 'approve-outline':
            orchestrator.initialize()
            result = orchestrator.approve_outline(args.book_id)
            if result['success']:
                print(f"\n✓ Outline approved!")
                print(f"  Chapters initialized: {len(result.get('chapters', []))}")
                print(f"\n  Next: python main.py chapter {args.book_id} 1")
            else:
                print(f"\n✗ Error: {result['error']}")
        
        elif args.command == 'outline-feedback':
            orchestrator.initialize()
            result = orchestrator.add_outline_feedback(args.book_id, args.notes)
            print(f"\n✓ {result['message']}")
            print(f"  Next: python main.py regen-outline {args.book_id}")
        
        elif args.command == 'regen-outline':
            orchestrator.initialize()
            print(f"\nRegenerating outline for book {args.book_id}...")
            result = orchestrator.regenerate_outline(args.book_id)
            if result['success']:
                print(f"\n✓ Outline regenerated!")
            else:
                print(f"\n✗ Error: {result['error']}")
        
        elif args.command == 'chapter':
            orchestrator.initialize()
            print(f"\nGenerating chapter {args.chapter_num} for book {args.book_id}...")
            result = orchestrator.generate_chapter(args.book_id, args.chapter_num)
            if result['success']:
                print(f"\n✓ Chapter {args.chapter_num} generated!")
                print(f"\n  Next: Review and run 'python main.py approve-chapter {args.book_id} {args.chapter_num}'")
            else:
                print(f"\n✗ Error: {result['error']}")
        
        elif args.command == 'all-chapters':
            orchestrator.initialize()
            print(f"\nGenerating all chapters for book {args.book_id}...")
            result = orchestrator.generate_all_chapters(args.book_id, args.auto_approve)
            if result['success']:
                print(f"\n✓ Processed {len(result['results'])} chapters")
                for r in result['results']:
                    icon = "✓" if r['status'] == 'success' else "○" if r['status'] == 'skipped' else "✗"
                    print(f"  {icon} Chapter {r['chapter']}: {r['status']}")
        
        elif args.command == 'approve-chapter':
            orchestrator.initialize()
            result = orchestrator.approve_chapter(args.book_id, args.chapter_num)
            if result['success']:
                print(f"\n✓ Chapter {args.chapter_num} approved!")
                if result.get('all_chapters_complete'):
                    print(f"  All chapters complete! Ready to compile.")
                    print(f"\n  Next: python main.py compile {args.book_id}")
            else:
                print(f"\n✗ Error: {result['error']}")
        
        elif args.command == 'chapter-feedback':
            orchestrator.initialize()
            result = orchestrator.add_chapter_feedback(args.book_id, args.chapter_num, args.notes)
            print(f"\n✓ {result['message']}")
            print(f"  Next: python main.py regen-chapter {args.book_id} {args.chapter_num}")
        
        elif args.command == 'regen-chapter':
            orchestrator.initialize()
            print(f"\nRegenerating chapter {args.chapter_num}...")
            result = orchestrator.regenerate_chapter(args.book_id, args.chapter_num)
            if result['success']:
                print(f"\n✓ Chapter {args.chapter_num} regenerated!")
            else:
                print(f"\n✗ Error: {result['error']}")
        
        elif args.command == 'compile':
            orchestrator.initialize()
            print(f"\nCompiling book {args.book_id}...")
            result = orchestrator.compile_book(args.book_id, args.formats)
            if result['success']:
                print(f"\n✓ Book compiled successfully!")
                print(f"\nOutput files:")
                for fmt, path in result['output_files'].items():
                    if path:
                        print(f"  - {fmt.upper()}: {path}")
            else:
                print(f"\n✗ Error: {result['error']}")
        
        elif args.command == 'auto':
            orchestrator.initialize()
            print_header()
            print(f"Running automated workflow for book {args.book_id}...")
            result = orchestrator.run_automated_workflow(
                args.book_id,
                auto_approve_outline=args.auto_approve,
                auto_approve_chapters=args.auto_approve
            )
            if result['success']:
                print(f"\n✓ Workflow complete!")
                if result.get('output_files'):
                    print(f"\nOutput files:")
                    for fmt, path in result['output_files'].items():
                        if path:
                            print(f"  - {fmt.upper()}: {path}")
            else:
                print(f"\n✗ Error: {result.get('error')}")
        
        elif args.command == 'logs':
            orchestrator.initialize()
            logs = orchestrator.get_logs(getattr(args, 'book_id', None))
            print(f"\n{'─'*70}")
            print(f"{'Time':<20} {'Event':<20} {'Message':<30}")
            print(f"{'─'*70}")
            for log in logs[:20]:  # Show last 20
                print(f"{log.get('created_at', '')[:19]:<20} {log['event_type']:<20} {log['message'][:28]:<30}")
            if len(logs) > 20:
                print(f"... and {len(logs) - 20} more logs")
        
        elif args.command == 'pending':
            orchestrator.initialize()
            pending = orchestrator.check_pending_actions()
            if pending:
                print(f"\n📋 Pending Actions:")
                print(f"{'─'*60}")
                for p in pending:
                    print(f"\nBook {p['book_id']}: {p['title']}")
                    print(f"  Stage: {p['stage']}")
                    print(f"  Action: {p['next_action']}")
            else:
                print("\n✓ No pending actions!")
    
    except KeyboardInterrupt:
        print("\n\nOperation cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
