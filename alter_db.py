import sqlite3

conn = sqlite3.connect('parking.db')
cursor = conn.cursor()

# Add the 'status' column to the existing 'slots' table
cursor.execute("ALTER TABLE slots ADD COLUMN status INTEGER DEFAULT 0")
cursor.execute("ALTER TABLE slots ADD COLUMN user_id INTEGER")

conn.commit()
conn.close()
