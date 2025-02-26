from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

# Replace with your Alchemy API key
ALCHEMY_API_KEY = "YtE1qHS6fv_a3uovCLlwhJ-jimLXqOAr"
ALCHEMY_URL = f"https://eth-mainnet.alchemyapi.io/v2/{ALCHEMY_API_KEY}"

@app.route('/get_tx_details', methods=['GET'])
def get_tx_details():
    tx_hash = request.args.get('tx_hash')  # Transaction hash passed as a query parameter
    if not tx_hash:
        return jsonify({"error": "Transaction hash is required"}), 400

    # Call the Alchemy API to get transaction details
    try:
        response = requests.post(
            ALCHEMY_URL,
            json={
                "jsonrpc": "2.0",
                "method": "eth_getTransactionByHash",
                "params": [tx_hash],
                "id": 1
            }
        )

        result = response.json()

        # Check if the transaction was found
        if 'result' in result and result['result']:
            return jsonify(result['result'])
        else:
            return jsonify({"error": "Transaction not found or invalid hash"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000, debug=False)

