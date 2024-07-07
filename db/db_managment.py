# db/db_management.py
from db.connection import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

def get_path_id(channel_id):
    cur.execute("""
        SELECT path_id FROM path_channels WHERE channel_id = %s
    """, (channel_id,))
    result = cur.fetchone()
    return result[0] if result else None

def add_path(name, duration_weeks):
    cur.execute("""
        INSERT INTO paths (name, duration_weeks) 
        VALUES (%s, %s) 
        RETURNING id
    """, (name, duration_weeks))
    path_id = cur.fetchone()[0]
    conn.commit()
    return path_id

def add_channel_to_path(path_id, channel_id):
    cur.execute("""
        INSERT INTO path_channels (path_id, channel_id)
        VALUES (%s, %s)
        ON CONFLICT (channel_id) DO NOTHING
    """, (path_id, channel_id))
    conn.commit()

def add_topic(path_id, week, topic):
    cur.execute("""
        INSERT INTO topics (path_id, week, topic)
        VALUES (%s, %s, %s) 
        RETURNING id
    """, (path_id, week, topic))
    topic_id = cur.fetchone()[0]
    conn.commit()
    return topic_id

def add_task(topic_id, task):
    cur.execute("""
        INSERT INTO tasks (topic_id, task)
        VALUES (%s, %s) 
        RETURNING id
    """, (topic_id, task))
    task_id = cur.fetchone()[0]
    conn.commit()
    return task_id

def get_user_week(user_id, path_id):
    cur.execute("""
        SELECT week FROM user_progress 
        WHERE user_id = %s AND path_id = %s
    """, (user_id, path_id))
    result = cur.fetchone()
    return result[0] if result else 1

def get_topics(path_id, week):
    cur.execute("""
        SELECT id, topic FROM topics 
        WHERE path_id = %s AND week = %s
    """, (path_id, week))
    return cur.fetchall()

def get_topics_by_path(path_id):
    cur.execute("""
        SELECT id, topic FROM topics 
        WHERE path_id = %s
    """, (path_id,))
    return cur.fetchall()

def get_tasks(topic_id):
    cur.execute("""
        SELECT id, task FROM tasks 
        WHERE topic_id = %s
    """, (topic_id,))
    return cur.fetchall()

def get_user_tasks(user_id, path_id):
    cur.execute("""
        SELECT t.id, t.task, ut.completed, ut.proof_url
        FROM tasks t
        JOIN user_tasks ut ON t.id = ut.task_id
        JOIN topics tp ON t.topic_id = tp.id
        WHERE ut.user_id = %s AND tp.path_id = %s
    """, (user_id, path_id))
    return cur.fetchall()

def mark_user_task(user_id, task_id, completed, proof_url):
    cur.execute("""
        INSERT INTO user_tasks (user_id, task_id, completed, proof_url)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id, task_id)
        DO UPDATE SET completed = EXCLUDED.completed, proof_url = EXCLUDED.proof_url
    """, (user_id, task_id, completed, proof_url))
    conn.commit()

def get_all_paths():
    cur.execute("SELECT id, name FROM paths")
    return cur.fetchall()

def get_weeks_for_path(path_id):
    cur.execute("""
        SELECT DISTINCT week FROM topics WHERE path_id = %s ORDER BY week
    """, (path_id,))
    existing_weeks = [row[0] for row in cur.fetchall()]
    return existing_weeks

def get_path_duration(path_id):
    cur.execute("SELECT duration_weeks FROM paths WHERE id = %s", (path_id,))
    result = cur.fetchone()
    return result[0] if result else None

def get_path_by_channel(channel_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT paths.id, paths.name
        FROM paths
        JOIN path_channels ON paths.id = path_channels.path_id
        WHERE path_channels.channel_id = %s
    """, (channel_id,))
    path = cur.fetchone()
    cur.close()
    conn.close()
    return path