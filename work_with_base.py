import sqlite3

conn = sqlite3.connect('santas.db')

cur = conn.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS users(
   tg_id INT PRIMARY KEY UNIQUE NOT NULL,
   full_name TEXT,
   telephone TEXT,
   address TEXT,
   comment TEXT
   );
""")
conn.commit()