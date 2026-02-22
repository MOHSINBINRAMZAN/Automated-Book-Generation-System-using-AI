"""
Web UI for the Automated Book Generation System
Flask-based interface for managing book generation workflow.
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator import get_orchestrator

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize orchestrator
orchestrator = get_orchestrator()
orchestrator.initialize()


# =============================================================================
# ROUTES - DASHBOARD
# =============================================================================

@app.route('/')
def index():
    """Dashboard - list all books."""
    books = orchestrator.list_all_books()
    pending = orchestrator.check_pending_actions()
    return render_template('index.html', books=books, pending=pending)


# =============================================================================
# ROUTES - BOOKS
# =============================================================================

@app.route('/book/create', methods=['GET', 'POST'])
def create_book():
    """Create a new book."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        notes = request.form.get('notes', '').strip()
        
        if not title or not notes:
            flash('Title and notes are required', 'error')
            return redirect(url_for('create_book'))
        
        result = orchestrator.create_book(title, notes)
        
        if result['success']:
            flash(f'Book created successfully! ID: {result["book_id"]}', 'success')
            return redirect(url_for('book_detail', book_id=result['book_id']))
        else:
            flash(f'Error: {result["error"]}', 'error')
    
    return render_template('create_book.html')


@app.route('/book/<int:book_id>')
def book_detail(book_id):
    """View book details and status."""
    status = orchestrator.get_book_status(book_id)
    if not status['success']:
        flash(f'Book not found', 'error')
        return redirect(url_for('index'))
    
    book = orchestrator.db.get_book(book_id)
    chapters = orchestrator.db.get_chapters_by_book(book_id)
    logs = orchestrator.get_logs(book_id)[:10]
    
    return render_template('book_detail.html', 
                         status=status, 
                         book=book, 
                         chapters=chapters,
                         logs=logs)


# =============================================================================
# ROUTES - OUTLINE
# =============================================================================

@app.route('/book/<int:book_id>/generate-outline', methods=['POST'])
def generate_outline(book_id):
    """Generate outline for a book."""
    result = orchestrator.generate_outline(book_id)
    
    if result['success']:
        flash('Outline generated successfully!', 'success')
    else:
        flash(f'Error: {result["error"]}', 'error')
    
    return redirect(url_for('book_detail', book_id=book_id))


@app.route('/book/<int:book_id>/outline-feedback', methods=['POST'])
def outline_feedback(book_id):
    """Add feedback for outline."""
    notes = request.form.get('notes', '').strip()
    
    if not notes:
        flash('Please provide feedback notes', 'error')
        return redirect(url_for('book_detail', book_id=book_id))
    
    result = orchestrator.add_outline_feedback(book_id, notes)
    flash(result['message'], 'success')
    
    return redirect(url_for('book_detail', book_id=book_id))


@app.route('/book/<int:book_id>/regenerate-outline', methods=['POST'])
def regenerate_outline(book_id):
    """Regenerate outline based on feedback."""
    result = orchestrator.regenerate_outline(book_id)
    
    if result['success']:
        flash('Outline regenerated successfully!', 'success')
    else:
        flash(f'Error: {result["error"]}', 'error')
    
    return redirect(url_for('book_detail', book_id=book_id))


@app.route('/book/<int:book_id>/approve-outline', methods=['POST'])
def approve_outline(book_id):
    """Approve outline and initialize chapters."""
    result = orchestrator.approve_outline(book_id)
    
    if result['success']:
        flash('Outline approved! Chapters initialized.', 'success')
    else:
        flash(f'Error: {result["error"]}', 'error')
    
    return redirect(url_for('book_detail', book_id=book_id))


# =============================================================================
# ROUTES - CHAPTERS
# =============================================================================

@app.route('/book/<int:book_id>/chapter/<int:chapter_num>')
def chapter_detail(book_id, chapter_num):
    """View chapter details."""
    chapters = orchestrator.db.get_chapters_by_book(book_id)
    chapter = next((c for c in chapters if c['chapter_number'] == chapter_num), None)
    
    if not chapter:
        flash('Chapter not found', 'error')
        return redirect(url_for('book_detail', book_id=book_id))
    
    book = orchestrator.db.get_book(book_id)
    return render_template('chapter_detail.html', book=book, chapter=chapter)


@app.route('/book/<int:book_id>/generate-chapter/<int:chapter_num>', methods=['POST'])
def generate_chapter(book_id, chapter_num):
    """Generate a specific chapter."""
    result = orchestrator.generate_chapter(book_id, chapter_num)
    
    if result['success']:
        flash(f'Chapter {chapter_num} generated successfully!', 'success')
    else:
        flash(f'Error: {result["error"]}', 'error')
    
    return redirect(url_for('chapter_detail', book_id=book_id, chapter_num=chapter_num))


@app.route('/book/<int:book_id>/chapter-feedback/<int:chapter_num>', methods=['POST'])
def chapter_feedback(book_id, chapter_num):
    """Add feedback for a chapter."""
    notes = request.form.get('notes', '').strip()
    
    if not notes:
        flash('Please provide feedback notes', 'error')
        return redirect(url_for('chapter_detail', book_id=book_id, chapter_num=chapter_num))
    
    result = orchestrator.add_chapter_feedback(book_id, chapter_num, notes)
    flash(result['message'], 'success')
    
    return redirect(url_for('chapter_detail', book_id=book_id, chapter_num=chapter_num))


@app.route('/book/<int:book_id>/regenerate-chapter/<int:chapter_num>', methods=['POST'])
def regenerate_chapter(book_id, chapter_num):
    """Regenerate chapter based on feedback."""
    result = orchestrator.regenerate_chapter(book_id, chapter_num)
    
    if result['success']:
        flash(f'Chapter {chapter_num} regenerated successfully!', 'success')
    else:
        flash(f'Error: {result["error"]}', 'error')
    
    return redirect(url_for('chapter_detail', book_id=book_id, chapter_num=chapter_num))


@app.route('/book/<int:book_id>/approve-chapter/<int:chapter_num>', methods=['POST'])
def approve_chapter(book_id, chapter_num):
    """Approve a chapter."""
    result = orchestrator.approve_chapter(book_id, chapter_num)
    
    if result['success']:
        flash(f'Chapter {chapter_num} approved!', 'success')
        if result.get('all_chapters_complete'):
            flash('All chapters complete! Ready to compile.', 'info')
    else:
        flash(f'Error: {result["error"]}', 'error')
    
    return redirect(url_for('book_detail', book_id=book_id))


@app.route('/book/<int:book_id>/generate-all-chapters', methods=['POST'])
def generate_all_chapters(book_id):
    """Generate all chapters."""
    auto_approve = request.form.get('auto_approve') == 'on'
    result = orchestrator.generate_all_chapters(book_id, auto_approve)
    
    if result['success']:
        flash(f'All chapters processed!', 'success')
    else:
        flash(f'Error: {result.get("error", "Unknown error")}', 'error')
    
    return redirect(url_for('book_detail', book_id=book_id))


# =============================================================================
# ROUTES - COMPILATION
# =============================================================================

@app.route('/book/<int:book_id>/compile', methods=['POST'])
def compile_book(book_id):
    """Compile the final book."""
    formats = request.form.getlist('formats') or ['docx', 'txt', 'pdf']
    result = orchestrator.compile_book(book_id, formats)
    
    if result['success']:
        flash('Book compiled successfully!', 'success')
    else:
        flash(f'Error: {result["error"]}', 'error')
    
    return redirect(url_for('book_detail', book_id=book_id))


@app.route('/book/<int:book_id>/auto-generate', methods=['POST'])
def auto_generate(book_id):
    """Run full automated workflow."""
    auto_approve = request.form.get('auto_approve') == 'on'
    result = orchestrator.run_automated_workflow(book_id, auto_approve, auto_approve)
    
    if result['success']:
        flash('Book generation complete!', 'success')
    else:
        flash(f'Error: {result.get("error", "Unknown error")}', 'error')
    
    return redirect(url_for('book_detail', book_id=book_id))


# =============================================================================
# API ROUTES
# =============================================================================

@app.route('/api/book/<int:book_id>/status')
def api_book_status(book_id):
    """API: Get book status."""
    return jsonify(orchestrator.get_book_status(book_id))


@app.route('/api/books')
def api_list_books():
    """API: List all books."""
    return jsonify(orchestrator.list_all_books())


@app.route('/api/pending')
def api_pending():
    """API: Get pending actions."""
    return jsonify(orchestrator.check_pending_actions())


# =============================================================================
# TEMPLATES
# =============================================================================

@app.route('/templates')
def create_templates():
    """Create template files (run once)."""
    # This is a helper route - templates should be in templates/ folder
    return "Templates should be in templates/ folder"


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("\n" + "="*50)
    print("BOOK GENERATION SYSTEM - WEB UI")
    print("="*50)
    print("\nStarting web server...")
    print("Open http://localhost:5000 in your browser")
    print("="*50 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
