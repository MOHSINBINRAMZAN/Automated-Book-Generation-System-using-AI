import sqlite3
conn = sqlite3.connect('book_generator.db')
c = conn.cursor()
c.execute("DELETE FROM chapters WHERE book_id=3 AND status='pending'")
conn.commit()
print("Fixed - deleted duplicate pending chapters")
c.execute("SELECT chapter_number, status FROM chapters WHERE book_id=3")
for r in c.fetchall():
    print(r)
conn.close()
