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
                    plan TEXT DEFAULT 'free'.
                    request_count INTEGER DEFAULT 0
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

# Track API request usage
def update_request_count(api_key):
    conn = sqlite3.connect('api_keys.db')
    c = conn.cursor()
    
    # Get the user's current request count and plan
    c.execute("SELECT request_count, plan FROM users WHERE api_key = ?", (api_key,))
    user = c.fetchone()
    
    if user:
        request_count, plan = user

        # Set request limits based on plan
        limits = {"free": 100, "pro": 10000, "enterprise": float("inf")}
        max_requests = limits.get(plan, 100)  # Default to free limit if unknown plan

        if request_count >= max_requests:
            conn.close()
            return False  # Block the request if limit is exceeded
        
        # Update the request count
        c.execute("UPDATE users SET request_count = request_count + 1 WHERE api_key = ?", (api_key,))
        conn.commit()
        conn.close()
        return True  # Allow the request
    
    conn.close()
    return False  # Block request if API key is invalid

# Initialize the database when this script runs
if __name__ == "__main__":
    init_db()
    print("Database initialized. Ready to add users.")
