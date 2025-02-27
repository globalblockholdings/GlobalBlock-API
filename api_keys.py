import sqlite3
import secrets

# Initialize the database
def init_db():
    conn = sqlite3.connect('api_keys.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    api_key TEXT UNIQUE,
                    plan TEXT DEFAULT 'free'
                )''')
    conn.commit()
    conn.close()

# Generate a new API key for a user
def generate_api_key(name, plan='free'):
    api_key = secrets.token_hex(16)
    conn = sqlite3.connect('api_keys.db')
    c = conn.cursor()
    c.execute("INSERT INTO users (name, api_key, plan) VALUES (?, ?, ?)", (name, api_key, plan))
    conn.commit()
    conn.close()
    return api_key

# Validate an API key
def validate_api_key(api_key):
    conn = sqlite3.connect('api_keys.db')
    c = conn.cursor()
    c.execute("SELECT plan FROM users WHERE api_key = ?", (api_key,))
    user = c.fetchone()
    conn.close()
    return user if user else None

# Initialize the database when this script runs
if __name__ == "__main__":
    init_db()
    print("Database initialized. Ready to add users.")
