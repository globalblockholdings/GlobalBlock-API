from dotenv import load_dotenv
import os
import requests
import sqlite3
import sys
from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_httpauth import HTTPTokenAuth
from loguru import logger
from flask_cors import CORS

# Load environment variables
load_dotenv()

# Get Alchemy API Key from .env
ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY")
if not ALCHEMY_API_KEY:
    raise ValueError("Missing ALCHEMY_API_KEY in environment variables.")

ALCHEMY_URL = f"https://eth-mainnet.alchemyapi.io/v2/{ALCHEMY_API_KEY}"

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing

# Configure logging
logger.remove()
logger.add(sys.stderr, format="{time} {level} {message}", level="INFO")
logger.add("api_logs.log", rotation="10 MB", level="INFO")
logger.info("Logging system initialized.")

# Set up rate limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per hour"],
)

# Token-based authentication
auth = HTTPTokenAuth(scheme="Bearer")

# Database connection function
def get_db_connection():
    conn = sqlite3.connect("api_keys.db")
    conn.row_factory = sqlite3.Row
    return conn

# Verify API key from the database
@auth.verify_token
def verify_token(token):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM users WHERE api_key = ?", (token,))
    user = cursor.fetchone()
    conn.close()
    return user["name"] if user else None

# Get Ethereum transaction details
@app.route('/get_tx_details', methods=['GET'])
@auth.login_required
@limiter.limit("10 per minute")
def get_tx_details():
    tx_hash = request.args.get('tx_hash')
    if not tx_hash:
        return jsonify({"error": "Transaction hash is required"}), 400

    try:
        response = requests.post(
            ALCHEMY_URL,
            json={
                "jsonrpc": "2.0",
                "method": "eth_getTransactionByHash",
                "params": [tx_hash],
                "id": 1
            },
            timeout=10  # Prevent long wait times
        )

        if response.status_code != 200:
            logger.error(f"Alchemy API error: {response.text}")
            return jsonify({"error": "Alchemy API error"}), response.status_code

        result = response.json()

        if 'result' in result and result['result']:
            return jsonify(result['result'])
        else:
            return jsonify({"error": "Transaction not found or invalid hash"}), 404
    except requests.exceptions.Timeout:
        return jsonify({"error": "Request timed out"}), 504
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

# Get Gas Fee Estimates
@app.route('/get_gas_fees', methods=['GET'])
@auth.login_required
def get_gas_fees():
    try:
        response = requests.post(
            ALCHEMY_URL,
            json={"jsonrpc": "2.0", "method": "eth_gasPrice", "params": [], "id": 1},
            timeout=10
        )
        result = response.json()
        return jsonify({"gas_price": result.get("result")})
    except Exception as e:
        logger.error(f"Gas Fee API error: {str(e)}")
        return jsonify({"error": "Failed to fetch gas fees"}), 500

# Decode Smart Contract Interaction
@app.route('/decode_contract', methods=['POST'])
@auth.login_required
def decode_contract():
    data = request.json
    contract_address = data.get('contract_address')
    function_data = data.get('function_data')

    if not contract_address or not function_data:
        return jsonify({"error": "Missing contract address or function data"}), 400

    try:
        response = requests.post(
            ALCHEMY_URL,
            json={
                "jsonrpc": "2.0",
                "method": "eth_call",
                "params": [{"to": contract_address, "data": function_data}, "latest"],
                "id": 1
            },
            timeout=10
        )
        return jsonify(response.json())
    except Exception as e:
        logger.error(f"Contract decoding error: {str(e)}")
        return jsonify({"error": "Failed to decode contract interaction"}), 500

# Get NFT Metadata
@app.route('/get_nft_metadata', methods=['GET'])
@auth.login_required
def get_nft_metadata():
    token_address = request.args.get('token_address')
    token_id = request.args.get('token_id')
    if not token_address or not token_id:
        return jsonify({"error": "Missing token address or token ID"}), 400

    url = f"https://api.opensea.io/api/v1/asset/{token_address}/{token_id}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return jsonify({"error": "Failed to fetch NFT metadata"}), 502
        return jsonify(response.json())
    except requests.exceptions.Timeout:
        return jsonify({"error": "Request to OpenSea API timed out"}), 504
    except Exception as e:
        logger.error(f"NFT Metadata API error: {str(e)}")
        return jsonify({"error": "Failed to fetch NFT metadata"}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000, debug=False)
    