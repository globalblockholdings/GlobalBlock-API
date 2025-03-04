import os
import secrets
import stripe
import sqlite3
import requests
import hashlib
import logging
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_httpauth import HTTPTokenAuth
from web3 import Web3
from dotenv import load_dotenv
from flask_cors import CORS
from cryptography.fernet import Fernet
import threading
import time
from flask_socketio import SocketIO
from redis import Redis

# Load environment variables
load_dotenv()
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
cipher = Fernet(ENCRYPTION_KEY.encode())

# Initialize Flask app
app = Flask(__name__)
socketio = SocketIO(app)
CORS(app, resources={r"/*": {"origins": ["https://dashboard.globalblock-api.com"]}})

# Initialize Redis for Rate Limiting
redis_client = Redis(host="localhost", port=6379, db=0)  # Update if using cloud Redis

# Apply Redis-based rate limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri="redis://localhost:6379"")

# Configure logging
logging.basicConfig(
    filename="api_activity.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s")

# Configure Stripe API
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Configure Web3
ALCHEMY_API_URL = os.getenv("ALCHEMY_API_URL")
PAYMENT_WALLET_ADDRESS = os.getenv("CRYPTO_WALLET")

# Secure API Key Storage
def encrypt_key(api_key):
    return cipher.encrypt(api_key.encode()).decode()

def decrypt_key(encrypted_key):
    return cipher.decrypt(encrypted_key.encode()).decode()

# Database Connection
def get_db_connection():
    conn = sqlite3.connect("api_keys.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.before_request
def apply_rate_limit():
    conn = get_db_connection()
    cursor = conn.cursor()
    user_plan = cursor.execute("SELECT plan FROM users WHERE api_key = ?", 
                               (request.headers.get("Authorization"),)).fetchone()
    conn.close()
    limits = {"free": "10 per minute", "pro": "100 per minute", "enterprise": "1000 per minute"}
    user_plan = user_plan[0] if user_plan else "free"
    limiter.limit(limits.get(user_plan, "10 per minute"))

# Token-based authentication
auth = HTTPTokenAuth(scheme="Bearer")

@auth.verify_token
def verify_token(token):
    hashed_token = hashlib.sha256(token.encode()).hexdigest()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM users WHERE api_key = ?", (hashed_token,))
    user = cursor.fetchone()
    conn.close()
    return user["name"] if user else None

# WebSockets for Real-time Notifications
@socketio.on('connect')
def handle_connect():
    logging.info("Client connected to WebSocket.")

# API Endpoints
@app.route('/get_tx_details', methods=['GET'])
@auth.login_required
@limiter.limit("10 per minute")
def get_tx_details():
    tx_hash = request.args.get('tx_hash')
    if not tx_hash:
        return jsonify({"error": "Transaction hash is required"}), 400
    response = requests.post(ALCHEMY_API_URL, json={
        "jsonrpc": "2.0",
        "method": "eth_getTransactionByHash",
        "params": [tx_hash],
        "id": 1
    })
    if response.status_code != 200:
        return jsonify({"error": "Failed to retrieve data"}), response.status_code
    return jsonify(response.json())

# Dynamic Rate Limiting
@app.route('/dynamic_rate_limit', methods=['GET'])
@auth.login_required
def dynamic_rate_limit():
    api_key = request.headers.get("Authorization")
    user_plan = get_user_plan(api_key)
    return jsonify({"rate_limit": f"{user_plan} requests per minute"})

# Activate API Access
def activate_api_access(email, plan):
    conn = get_db_connection()
    cursor = conn.cursor()
    hashed_key = hashlib.sha256(secrets.token_hex(16).encode()).hexdigest()
    encrypted_key = encrypt_key(hashed_key)
    cursor.execute("UPDATE users SET plan = ?, api_key = ? WHERE email = ?", (plan, encrypted_key, email))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    debug_mode = os.getenv("DEBUG_MODE", "False").lower() == "true"
    socketio.run(app, host="0.0.0.0", port=10000, debug=debug_mode)
