from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
import logging
import traceback
import requests
from datetime import datetime
from dotenv import load_dotenv
import random

load_dotenv()

app = Flask(__name__)
CORS(app)

# ---------------- CONFIG ---------------- #

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'backend_data')

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

PRODUCTS_FILE = os.path.join(BASE_DIR, 'product.json')

# ---------------- GLOBAL DATA ---------------- #

products_db = []

# ---------------- HELPERS ---------------- #

def safe_load_json(filepath, default_value):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except:
            return default_value
    return default_value


def load_data():
    global products_db
    products_db = safe_load_json(PRODUCTS_FILE, [])
    print("Data loaded successfully.")

# ---------------- ROUTES ---------------- #

@app.route("/")
def home():
    return jsonify({
        "status": "Backend Running",
        "message": "MyFruitMart API Live 🚀"
    })


@app.route("/api/health")
def health():
    return jsonify({
        "success": True,
        "status": "online"
    })


@app.route("/api/products")
def products():
    return jsonify(products_db)


@app.route("/api/ai-chat", methods=["POST"])
def ai_chat():
    try:
        data = request.json
        prompt = data.get("prompt", "")

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            return jsonify({
                "success": False,
                "message": "GEMINI_API_KEY not configured"
            }), 500

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }

        r = requests.post(url, json=payload, timeout=15)

        if r.status_code == 200:
            result = r.json()
            reply = result['candidates'][0]['content']['parts'][0]['text']
            return jsonify({
                "success": True,
                "response": reply
            })

        return jsonify({
            "success": False,
            "message": f"Gemini API Error {r.status_code}"
        }), 500

    except Exception as e:
        print("AI ERROR:", traceback.format_exc())
        return jsonify({
            "success": False,
            "message": "AI system error"
        }), 500


# ---------------- START ---------------- #

load_data()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
