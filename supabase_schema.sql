-- =============================================================================
-- AUTOMATED BOOK GENERATION SYSTEM - SUPABASE SCHEMA
-- =============================================================================
-- Run this SQL in Supabase SQL Editor to create the required tables
-- =============================================================================

-- Books table
CREATE TABLE IF NOT EXISTS books (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    notes_on_outline_before TEXT DEFAULT '',
    outline TEXT DEFAULT '',
    notes_on_outline_after TEXT DEFAULT '',
    status_outline_notes TEXT DEFAULT 'no' CHECK(status_outline_notes IN ('yes', 'no', 'no_notes_needed')),
    chapter_notes_status TEXT DEFAULT 'no' CHECK(chapter_notes_status IN ('yes', 'no', 'no_notes_needed')),
    final_review_notes_status TEXT DEFAULT 'no' CHECK(final_review_notes_status IN ('yes', 'no', 'no_notes_needed')),
    final_review_notes TEXT DEFAULT '',
    book_output_status TEXT DEFAULT 'pending' CHECK(book_output_status IN ('pending', 'in_progress', 'paused', 'completed', 'error')),
    output_file_path TEXT DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Chapters table
CREATE TABLE IF NOT EXISTS chapters (
    id SERIAL PRIMARY KEY,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    chapter_number INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    chapter_notes TEXT DEFAULT '',
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'generating', 'review', 'approved', 'regenerating')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Outline drafts table (for version history)
CREATE TABLE IF NOT EXISTS outline_drafts (
    id SERIAL PRIMARY KEY,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    outline_content TEXT NOT NULL,
    notes_used TEXT DEFAULT '',
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Event logs table
CREATE TABLE IF NOT EXISTS event_logs (
    id SERIAL PRIMARY KEY,
    book_id INTEGER REFERENCES books(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- INDEXES
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_chapters_book_id ON chapters(book_id);
CREATE INDEX IF NOT EXISTS idx_chapters_book_chapter ON chapters(book_id, chapter_number);
CREATE INDEX IF NOT EXISTS idx_outline_drafts_book_id ON outline_drafts(book_id);
CREATE INDEX IF NOT EXISTS idx_event_logs_book_id ON event_logs(book_id);
CREATE INDEX IF NOT EXISTS idx_event_logs_created_at ON event_logs(created_at DESC);

-- =============================================================================
-- ROW LEVEL SECURITY (Optional - enable if needed)
-- =============================================================================

-- ALTER TABLE books ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE chapters ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE outline_drafts ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE event_logs ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to books table
DROP TRIGGER IF EXISTS update_books_updated_at ON books;
CREATE TRIGGER update_books_updated_at
    BEFORE UPDATE ON books
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to chapters table
DROP TRIGGER IF EXISTS update_chapters_updated_at ON chapters;
CREATE TRIGGER update_chapters_updated_at
    BEFORE UPDATE ON chapters
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- SAMPLE DATA (Optional - for testing)
-- =============================================================================

-- INSERT INTO books (title, notes_on_outline_before) VALUES 
-- ('Python Programming Guide', 'Create a comprehensive guide for beginners covering basics, OOP, and web development'),
-- ('Machine Learning Fundamentals', 'Cover supervised and unsupervised learning, neural networks, and practical applications');
