# db/create_tables.py
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../')

from db.connection import get_db_connection

def create_tables():
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS paths (
        id SERIAL PRIMARY KEY,
        name TEXT,
        duration_weeks INT
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS path_channels (
        id SERIAL PRIMARY KEY,
        path_id INT REFERENCES paths(id),
        channel_id BIGINT UNIQUE
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS topics (
        id SERIAL PRIMARY KEY,
        path_id INT REFERENCES paths(id),
        week INT,
        topic TEXT
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id SERIAL PRIMARY KEY,
        topic_id INT REFERENCES topics(id),
        task TEXT
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_tasks (
        id SERIAL PRIMARY KEY,
        user_id BIGINT,
        task_id INT REFERENCES tasks(id),
        completed BOOLEAN DEFAULT FALSE,
        proof_url TEXT,
        UNIQUE (user_id, task_id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_progress (
        user_id BIGINT,
        path_id INT REFERENCES paths(id),
        week INT DEFAULT 1,
        PRIMARY KEY (user_id, path_id)
    );
    """)
    
    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    create_tables()