import sqlite3
import secrets

# Initialize the database
def init_db():
    conn = sqlite3.connect("api_keys.db")
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            api_key TEXT UNIQUE,
            plan TEXT DEFAULT 'free',
            request_count INTEGER DEFAULT 0
        )"""
    )
    conn.commit()
    conn.close()

# Generate a new API key for a user
def generate_api_key(name, plan="free"):
    conn = sqlite3.connect("api_keys.db")
    c = conn.cursor()
    
    # Check if user already has an API key
    c.execute("SELECT api_key FROM users WHERE name = ?", (name,))
    existing_key = c.fetchone()
    
    if existing_key:
        conn.close()
        return existing_key[0]  # Return the existing key instead of creating a new one

    # Generate a new API key
    api_key = secrets.token_hex(16)
    c.execute("INSERT INTO users (name, api_key, plan) VALUES (?, ?, ?)", (name, api_key, plan))
    conn.commit()
    conn.close()
    return api_key

# Validate an API key
def validate_api_key(api_key):
    conn = sqlite3.connect("api_keys.db")
    c = conn.cursor()
    c.execute("SELECT name, plan, request_count FROM users WHERE api_key = ?", (api_key,))
    user = c.fetchone()
    conn.close()
    return user  # Returns full user info (name, plan, request_count)

# Track API request usage
def update_request_count(api_key):
    conn = sqlite3.connect("api_keys.db")
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
            return {"status": "blocked", "message": "API request limit reached"}

        # Update the request count
        c.execute("UPDATE users SET request_count = request_count + 1 WHERE api_key = ?", (api_key,))
        conn.commit()
        conn.close()
        return {"status": "allowed", "remaining_requests": max_requests - (request_count + 1)}

    conn.close()
    return {"status": "blocked", "message": "Invalid API key"}

# Reset all request counts (to be called daily via a cron job)
def reset_request_counts():
    conn = sqlite3.connect("api_keys.db")
    c = conn.cursor()
    c.execute("UPDATE users SET request_count = 0")
    conn.commit()
    conn.close()
    print("Request counts reset.")

# Initialize the database when this script runs
if __name__ == "__main__":
    init_db()
    print("Database initialized. Ready to add users.")
