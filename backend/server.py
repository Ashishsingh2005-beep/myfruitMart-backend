from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import json
import os
import logging
import traceback
import requests
from datetime import datetime
from dotenv import load_dotenv
# import google.generativeai as genai (Removed to use pure REST API)

# Load environment variables
# Load environment variables
load_dotenv()
import random

FALLBACK_RESPONSES = [
    "Hi! I'm Ajay from Ajay Fruit Mart. How can I help you today? 🍎",
    "Our mangoes are very fresh today! Would you like to see them? 🥭",
    "We deliver in 12 minutes within Delhi! 🚀",
    "You can see our full collection on the homepage. Any specific fruit you're looking for?",
    "That sounds delicious! We have the freshest fruits ready for you."
]

# --- CONFIG & GLOBALS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR) # Assumes server.py is in backend/
DATA_DIR = os.path.join(BASE_DIR, 'backend_data')

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# File Paths
PENDING_FILE = os.path.join(DATA_DIR, 'pending_payments.json')
APPROVED_FILE = os.path.join(DATA_DIR, 'approved_payments.json')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
ORDERS_FILE = os.path.join(DATA_DIR, 'orders.json')
COMPLAINTS_FILE = os.path.join(DATA_DIR, 'complaints.json')
FEEDBACK_FILE = os.path.join(DATA_DIR, 'feedback.json')
RATINGS_FILE = os.path.join(DATA_DIR, 'ratings.json')
ACTIVITIES_FILE = os.path.join(DATA_DIR, 'activities.json')
PRODUCTS_FILE = os.path.join(BASE_DIR, 'product.json')
SETTINGS_FILE = os.path.join(DATA_DIR, 'settings.json')

# In-memory database initialization
pending_verifications = []
approved_verifications = []
users_db = {}
orders_db = []
complaints_db = []
feedback_db = []
ratings_db = []
recent_activities = []
admin_sessions = []
products_db = []
otp_storage = {}
settings_db = {}


# --- HELPER FUNCTIONS ---
def safe_print(text):
    try:
        # 1. Try normal print
        print(text)
    except Exception:
        try:
            # 2. Try ASCII forced (removes emojis/unicode)
            s = str(text).encode('ascii', errors='replace').decode('ascii')
            print(s)
        except Exception:
            try:
                # 3. Last resort - simple message
                print("[LOG] Message contains unprintable chars")
            except:
                pass # Give up silently to prevent crash

def safe_load_json(filepath, default_value):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                content = f.read().strip()
                if not content: return default_value
                return json.loads(content)
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
            logging.error(f"Error loading {filepath}: {e}")
    return default_value

def safe_save_json(filepath, data):
    try:
        # Atomic write pattern to prevent corruption
        temp_file = filepath + '.tmp'
        with open(temp_file, 'w') as f:
            json.dump(data, f, indent=4)
        
        # Determine if we can rename (Windows needs remove first)
        if os.path.exists(filepath):
            os.remove(filepath)
        os.rename(temp_file, filepath)
    except Exception as e:
        print(f"Error saving {filepath}: {e}")
        logging.error(f"Error saving {filepath}: {e}")

def load_data():
    global pending_verifications, users_db, orders_db, complaints_db, approved_verifications, feedback_db, ratings_db, products_db, recent_activities, settings_db
    
    pending_verifications = safe_load_json(PENDING_FILE, [])
    users_db = safe_load_json(USERS_FILE, {})
    orders_db = safe_load_json(ORDERS_FILE, [])
    approved_verifications = safe_load_json(APPROVED_FILE, [])
    complaints_db = safe_load_json(COMPLAINTS_FILE, [])
    feedback_db = safe_load_json(FEEDBACK_FILE, [])
    ratings_db = safe_load_json(RATINGS_FILE, [])
    recent_activities = safe_load_json(ACTIVITIES_FILE, [])
    products_db = safe_load_json(PRODUCTS_FILE, [])
    settings_db = safe_load_json(SETTINGS_FILE, {'weekend_discount': 5})
    
    # Init products stock if missing
    if products_db:
        for p in products_db:
            if 'in_stock' not in p: p['in_stock'] = True
    
    print("Data loaded successfully.")

# --- LOGGING SETUP ---
logging.basicConfig(filename=os.path.join(DATA_DIR, 'activity.log'), level=logging.INFO, 
                    format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app) # Enable CORS for all routes

# Log every request
@app.before_request
def log_request():
    if not request.path.startswith('/assets') and not request.path.endswith('.css') and not request.path.endswith('.js'):
        logging.info(f"Page Visit: {request.remote_addr} accessed {request.path}")

@app.errorhandler(500)
def internal_error(exception):
    logging.error(f"500 Internal Server Error: {exception}\n{traceback.format_exc()}")
    return jsonify({"success": False, "message": "Internal Server Error", "details": str(exception)}), 500

@app.errorhandler(404)
def not_found_error(exception):
    if request.path.startswith('/api/'):
        return jsonify({"success": False, "message": "Endpoint not found"}), 404
    return send_from_directory(ROOT_DIR, 'index.html') # Single Page App fallbacks

@app.route('/api/health', methods=['GET', 'POST'])
def health_check():
    return jsonify({"success": True, "status": "online", "message": "Server is running smoothly 🚀"})

# Enable CORS
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    # Disable caching for EVERYTHING (HTML, CSS, JS) to fix update issues
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route('/')
def serve_index():
    return send_from_directory(ROOT_DIR, 'index.html')

@app.route('/api/products')
def api_products():
    try:
        # Reload products if empty (in case of hot reload glitch)
        global products_db
        if not products_db:
            products_db = safe_load_json(PRODUCTS_FILE, [])
        return jsonify(products_db)
    except Exception as e:
        logging.error(f"Products Error: {e}")
        return jsonify([]), 500

@app.route('/api/verify-payment', methods=['POST', 'OPTIONS'])
def api_verify_payment():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    try:
        data = request.json
        req_id = f"PAY-{int(datetime.now().timestamp() * 1000)}"
        
        request_entry = {
           "id": req_id,
           "user": data.get('user', 'Unknown'),
           "amount": data.get('amount', 0),
           "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
           "status": "pending"
        }
        pending_verifications.append(request_entry)
        safe_save_json(PENDING_FILE, pending_verifications)
        
        logging.info(f"Payment Verification Requested: {req_id} by {request_entry['user']}")
        return jsonify({"success": True, "req_id": req_id})
    except Exception as e:
        logging.error(f"Verify Payment Error: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/check-payment-status')
def api_check_payment_status():
    try:
        req_id = request.args.get('req_id')
        
        # Check pending
        for req in pending_verifications:
            if req['id'] == req_id:
                return jsonify({"status": "pending"})
                
        # Check approved
        for req in approved_verifications:
            if req['id'] == req_id:
                return jsonify({"status": "approved"})
                
        # Reload checks from file just in case memory is stale
        disk_approved = safe_load_json(APPROVED_FILE, [])
        for req in disk_approved:
            if req['id'] == req_id:
                return jsonify({"status": "approved"})

        logging.warning(f"Check Payment 404: {req_id} not found in pending/approved")
        return jsonify({"status": "not_found"}), 404
    except Exception as e:
        logging.error(f"Check Status Error: {e}")
        return jsonify({"status": "error"}), 500

@app.route('/api/admin/pending-payments')
def api_pending_payments():
    return jsonify(pending_verifications)

@app.route('/api/admin/approve-payment', methods=['POST', 'OPTIONS'])
def api_approve_payment():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    data = request.json
    req_id = data.get('req_id')
    
    global pending_verifications, approved_verifications
    for req in pending_verifications:
        if req['id'] == req_id:
            req['status'] = 'approved'
            approved_verifications.append(req)
            pending_verifications = [r for r in pending_verifications if r['id'] != req_id]
            
            safe_save_json(PENDING_FILE, pending_verifications)
            safe_save_json(APPROVED_FILE, approved_verifications)
            
            logging.info(f"Payment Approved: {req_id}")
            return jsonify({"success": True})
            
    return jsonify({"success": False, "message": "Request not found"}), 404

# --- OTP SYSTEM ---
import random
import requests

def generate_otp():
    return str(random.randint(100000, 999999))

@app.route('/api/send-otp', methods=['POST', 'OPTIONS'])
def api_send_otp():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    try:
        data = request.json
        phone = data.get('phone')
        
        # Basic validation
        if not phone or len(phone) < 10:
             return jsonify({"success": False, "message": "Invalid phone number"}), 400

        otp = generate_otp()
        otp_storage[phone] = otp
        
        # 1. LOG TO CONSOLE (Always for debugging)
        print(f"\n[OTP SYSTEM] GENERATED OTP FOR {phone}: {otp}\n")
        logging.info(f"OTP Generated for {phone}: {otp}")
        
        # 2. SEND VIA SMS (Fast2SMS or Twilio)
        fast2sms_key = os.getenv("FAST2SMS_API_KEY")
        twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
        twilio_phone = os.getenv("TWILIO_PHONE")

        sms_sent = False
        
        # OPTION A: FAST2SMS (Preferred for India)
        if fast2sms_key and fast2sms_key.strip():
            url = "https://www.fast2sms.com/dev/bulkV2"
            # Using 'q' (Quick SMS) route to bypass strict 'OTP' route verification for Dev accounts
            # Note: 'flash=0' means normal SMS, not flash SMS.
            payload = f"message=Your Fruit Shop Verification Code is: {otp}&language=english&route=q&numbers={phone}"
            
            headers = {
                'authorization': fast2sms_key.strip(),
                'Content-Type': "application/x-www-form-urlencoded",
                'Cache-Control': "no-cache",
            }
            try:
                response = requests.request("POST", url, data=payload, headers=headers)
                logging.info(f"Fast2SMS Response: {response.text}")
                
                # Parse Response
                try:
                    resp_json = response.json()
                except:
                    resp_json = {}

                # Check for success (return: true) or status_code 200
                if '"return":true' in response.text or response.status_code == 200:
                   sms_sent = True
                else:
                    error_msg = resp_json.get('message', 'Unknown SMS API Error')
                    logging.warning(f"Fast2SMS Error: {error_msg}")
            except Exception as f2s_err:
                logging.error(f"Fast2SMS Failed: {f2s_err}")
                error_msg = str(f2s_err)

        # OPTION B: TWILIO (Fallback/International)
        elif twilio_sid and twilio_token and twilio_phone:
            try:
                # Add country code if missing (Assuming India +91 for 10 digits)
                to_number = f"+91{phone}" if len(phone) == 10 and not phone.startswith('+') else phone
                
                url = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json"
                payload = {
                    "From": twilio_phone,
                    "To": to_number,
                    "Body": f"Your Fruit Shop Verification Code is: {otp}"
                }
                response = requests.post(url, data=payload, auth=(twilio_sid, twilio_token))
                logging.info(f"Twilio Response: {response.text}")
                if response.status_code in [200, 201]:
                    sms_sent = True
                else:
                     error_msg = "Twilio Error: " + response.text
            except Exception as tw_err:
                logging.error(f"Twilio Failed: {tw_err}")
                error_msg = str(tw_err)

        if sms_sent:
            return jsonify({"success": True, "message": "OTP sent via SMS"})
        else:
            logging.warning("SMS Provider Failed. Falling back to Dev Mode.")
            return jsonify({
                "success": True, 
                "message": f"SMS Failed ({error_msg}). using Dev Mode.", 
                "debug_otp": otp
            })

    except Exception as e:
        logging.error(f"Send OTP Error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/verify-otp', methods=['POST', 'OPTIONS'])
def api_verify_otp():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    try:
        data = request.json
        phone = data.get('phone')
        user_otp = data.get('otp')
        
        if phone in otp_storage and otp_storage[phone] == user_otp:
            del otp_storage[phone] # One-time use
            return jsonify({"success": True})
        
        return jsonify({"success": False, "message": "Invalid OTP"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/user')
def api_get_user():
    phone = request.args.get('phone')
    if phone in users_db:
        return jsonify({"found": True, "user": users_db[phone]})
    return jsonify({"found": False})

@app.route('/api/login', methods=['POST', 'OPTIONS'])
def api_login():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    data = request.json
    username = data.get('name', 'Anonymous')
    phone = data.get('phone', 'Unknown')
    address = data.get('address', 'Unknown')
    email = data.get('email', 'No email provided')
    
    if phone != 'Unknown':
        users_db[phone] = {
            "name": username,
            "phone": phone,
            "address": address,
            "email": email,
            "last_login": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "is_banned": users_db[phone].get("is_banned", False) if phone in users_db else False
        }
        
        if users_db[phone].get("is_banned", False):
             return jsonify({"success": False, "error": "Account suspended"}), 403
             
        safe_save_json(USERS_FILE, users_db)

    # Convert user object details to string for safe logging
    user_str = f"{username}"
    
    recent_activities.insert(0, {
        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "type": "login",
        "user": user_str,
        "details": f"Logged in from {request.remote_addr}"
    })
    safe_save_json(ACTIVITIES_FILE, recent_activities)
    
    logging.info(f"USER LOGIN: {username} ({phone})")
    
    return jsonify({"success": True, "user": data})

@app.route('/api/order', methods=['POST', 'OPTIONS'])
def api_order_post():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    try:
        data = request.json
        user = data.get('user', {})
        cart = data.get('cart', [])
        total = data.get('total', 0)
        payment = data.get('payment', 'Unknown')
        
        items_str = ", ".join([f"{item['name']} x{item.get('qty', 1)}" for item in cart])
        
        new_order = {
            "id": f"ORD-{int(datetime.now().timestamp() * 1000)}",
            "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "name": user.get('name'),
            "phone": user.get('phone'),
            "address": user.get('address'),
            "total": total,
            "payment": payment,
            "items": items_str,
            "cart_details": cart,
            "delivery_status": "Processing",
            "payment_status": "Paid" if payment == "UPI" else "Pending"
        }
        orders_db.append(new_order)
        safe_save_json(ORDERS_FILE, orders_db)
        
        logging.info(f"USER ORDER: {new_order['id']} by {user.get('name')}")
        return jsonify({"success": True})
    except Exception as e:
        logging.error(f"Order Error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/orders')
def api_orders_get():
    user_phone = request.args.get('phone')
    if user_phone:
        user_orders = [o for o in orders_db if o.get('phone') == user_phone]
        return jsonify(user_orders[::-1])
    return jsonify(orders_db[::-1])

@app.route('/api/admin/login', methods=['POST', 'OPTIONS'])
def api_admin_login():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    data = request.json
    password = data.get('password')
    
    logging.info(f"Admin Login Attempt with password: {password}")
    
    if password == 'admin123':
        token = f"ADM-{int(datetime.now().timestamp() * 1000)}"
        admin_sessions.append(token)
        return jsonify({"success": True, "token": token})
    else:
        return jsonify({"success": False, "message": "Invalid Password"}), 401

@app.route('/api/admin/verify', methods=['POST', 'OPTIONS'])
def api_admin_verify():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    token = request.json.get('token')
    if token in admin_sessions:
        return jsonify({"success": True})
    # Also check if token format is valid to be lenient on restarts
    if token and token.startswith('ADM-'):
        # Re-add to sessions if it looks valid
        admin_sessions.append(token)
        return jsonify({"success": True})
        
    return jsonify({"success": False}), 401

@app.route('/api/admin/stats')
def api_admin_stats():
    try:
        total_orders = len(orders_db)
        total_revenue = sum([float(o.get('total', 0)) for o in orders_db if o.get('delivery_status') != 'Cancelled'])
        pending_orders = len([o for o in orders_db if o.get('delivery_status') == 'Processing'])
        total_users = len(users_db)
        
        return jsonify({
            "totalOrders": total_orders,
            "totalRevenue": total_revenue,
            "pendingOrders": pending_orders,
            "totalUsers": total_users
        })
    except Exception as e:
        logging.error(f"Stats Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/activities')
def api_activity():
    return jsonify(recent_activities)

@app.route('/api/clear-activities', methods=['POST', 'OPTIONS'])
def api_clear_activity():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    global recent_activities
    recent_activities = []
    safe_save_json(ACTIVITIES_FILE, recent_activities)
    return jsonify({"success": True})

# --- OTHER ADMIN ROUTES (Simplified) ---
@app.route('/api/admin/users')
def api_admin_users():
    return jsonify(list(users_db.values()))

@app.route('/api/admin/update-order', methods=['POST', 'OPTIONS'])
def api_admin_update_order():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    data = request.json
    order_id = data.get('order_id')
    status_type = data.get('type')
    new_value = data.get('value')
    
    for order in orders_db:
        if order['id'] == order_id:
            if status_type == 'delivery': order['delivery_status'] = new_value
            elif status_type == 'payment': order['payment_status'] = new_value
            safe_save_json(ORDERS_FILE, orders_db)
            return jsonify({"success": True})
    return jsonify({"success": False}), 404

@app.route('/api/admin/ban-user', methods=['POST', 'OPTIONS'])
def api_admin_ban_user():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    data = request.json
    phone = data.get('phone')
    action = data.get('action') 
    
    if phone in users_db:
        users_db[phone]['is_banned'] = (action == 'ban')
        safe_save_json(USERS_FILE, users_db)
        return jsonify({"success": True})
    return jsonify({"success": False}), 404

@app.route('/api/admin/resolve-complaint', methods=['POST', 'OPTIONS'])
def api_admin_resolve_complaint():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    data = request.json
    try:
        cmp_id = data.get('id')
        reply = data.get('reply')
        for c in complaints_db:
            if c['id'] == cmp_id:
                c['status'] = 'Resolved'
                c['admin_reply'] = reply
                safe_save_json(COMPLAINTS_FILE, complaints_db)
                return jsonify({"success": True})
        return jsonify({"success": False}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/admin/complaints')
def api_admin_complaints():
    return jsonify(complaints_db[::-1])

@app.route('/api/complaint', methods=['GET', 'POST', 'OPTIONS'])
def api_complaint():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    if request.method == 'GET':
        phone = request.args.get('phone')
        user_complaints = [c for c in complaints_db if c.get('phone') == phone]
        return jsonify(user_complaints)
        
    data = request.json
    complaint = {
        "id": f"CMP-{int(datetime.now().timestamp() * 1000)}",
        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "order_id": data.get('order_id'),
        "type": data.get('type'),
        "desc": data.get('description'),
        "phone": data.get('user_phone'),
        "status": "Open", 
        "admin_reply": ""
    }
    complaints_db.append(complaint)
    safe_save_json(COMPLAINTS_FILE, complaints_db)
    return jsonify({"success": True})

@app.route('/api/admin/add-product', methods=['POST', 'OPTIONS'])
def api_add_product():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    try:
        data = request.json
        new_id = max([p['id'] for p in products_db]) + 1 if products_db else 101
        new_product = {
            "id": new_id,
            "name": data.get('name'),
            "price": int(data.get('price', 0)),
            "category": data.get('category', 'Fruits'),
            "subCategory": "Normal",
            "color": data.get('color', '#FF8C00'),
            "description": data.get('description', ''),
            "rating": 5.0,
            "in_stock": True
        }
        if 'originalPrice' in data and data['originalPrice']:
            new_product['originalPrice'] = int(data['originalPrice'])
            
        products_db.append(new_product)
        safe_save_json(PRODUCTS_FILE, products_db)
        return jsonify({"success": True, "product": new_product})
    except Exception as e:
        logging.error(f"Add Product Error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/admin/update-price', methods=['POST', 'OPTIONS'])
def api_update_price():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    try:
        data = request.json
        prod_id = int(data.get('id'))
        new_price = int(data.get('price'))
        for p in products_db:
            if p['id'] == prod_id:
                p['price'] = new_price
                safe_save_json(PRODUCTS_FILE, products_db)
                return jsonify({"success": True})
        return jsonify({"success": False, "message": "Not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/admin/update-original-price', methods=['POST', 'OPTIONS'])
def api_update_original_price():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    try:
        data = request.json
        prod_id = int(data.get('id'))
        original_price = data.get('originalPrice')
        for p in products_db:
            if p['id'] == prod_id:
                if original_price: p['originalPrice'] = int(original_price)
                elif 'originalPrice' in p: del p['originalPrice']
                safe_save_json(PRODUCTS_FILE, products_db)
                return jsonify({"success": True})
        return jsonify({"success": False, "message": "Not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/admin/toggle-stock', methods=['POST', 'OPTIONS'])
def api_toggle_stock():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    try:
        data = request.json
        prod_id = int(data.get('id'))
        for p in products_db:
            if p['id'] == prod_id:
                p['in_stock'] = not p.get('in_stock', True)
                safe_save_json(PRODUCTS_FILE, products_db)
                return jsonify({"success": True, "in_stock": p['in_stock']})
        return jsonify({"success": False}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/settings', methods=['GET', 'POST', 'OPTIONS'])
def handle_settings():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    if request.method == 'POST':
        try:
            data = request.json
            settings_db.update(data)
            safe_save_json(SETTINGS_FILE, settings_db)
            return jsonify({"success": True, "settings": settings_db})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500
    return jsonify(settings_db)
    
@app.route('/api/ai-chat', methods=['POST', 'OPTIONS'])
def ai_chat():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
        
    try:
        safe_print("=== AI CHAT REQUEST RECEIVED ===")
        # Check if request has JSON
        if not request.is_json:
            safe_print("Error: Request missing JSON")
            return jsonify({"success": False, "message": "Missing JSON body"}), 400

        data = request.json
        safe_print(f"Request data: {repr(data)}")
        
        prompt = data.get('prompt')
        history = data.get('history', [])
        
        safe_print(f"Prompt: {repr(prompt)}")
        
        api_key = os.getenv("GEMINI_API_KEY")
        
        # Prepare Context (Feed ALL product data to AI)
        all_products_info = []
        for p in products_db:
            if isinstance(p, dict) and 'name' in p and 'price' in p:
                all_products_info.append(f"{p['name']}: ₹{p['price']}/{p.get('unit', 'kg')}")
        
        product_context = "\n".join(all_products_info)
        
        system_instruction = f"""
        You are 'Ajay', the AI assistant for 'Ajay Fruit Mart', Delhi.
        You know EVERYTHING about our shop and products. 
        Delivery: 12-minute express delivery.
        
        FULL PRODUCT LIST & PRICES:
        {product_context}
        
        Policies: 100% Refund for damage (via Order History > Help). Cancellations allowed if not 'Out for Delivery'.
        Rules: Be helpful, brief, and romantic/friendly.
        """

        # --- MULTI-MODEL FAILOVER SYSTEM ---
        models_to_try = [
            "gemini-2.0-flash", 
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-pro"
        ]
        
        ai_response = None
        last_error = "No models reached"
        
        for model_name in models_to_try:
            try:
                safe_print(f"Trying Gemini Model: {model_name}")
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                
                payload = {
                    "contents": [{
                        "parts": [{"text": f"{system_instruction}\n\nUser Question: {prompt}\nAjay:"}]
                    }],
                    "generationConfig": {
                        "temperature": 0.7,
                        "topP": 0.8,
                        "topK": 40
                    }
                }
                
                r = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload, timeout=12)
                
                if r.status_code == 200:
                    result = r.json()
                    ai_response = result['candidates'][0]['content']['parts'][0]['text']
                    safe_print(f"Success with {model_name}!")
                    break
                else:
                    last_error = f"{model_name} failed (HTTP {r.status_code})"
                    safe_print(last_error)
                    continue
                    
            except Exception as model_err:
                last_error = f"Error with {model_name}: {repr(model_err)}"
                safe_print(last_error)
                continue

        if ai_response:
            logging.info(f"AI CHAT SUCCESS: Prompt: {prompt} | Response: {ai_response[:100]}...")
            return jsonify({
                "success": True, 
                "response": ai_response.replace('*', '').strip(),
                "source": "gemini_failover"
            })
            
        # --- ZOMATO/SWIGGY STYLE ULTIMATE BRAIN (V3 - RANDOMIZED) ---
        safe_print(f"Executing Smart Intelligence for: {prompt}")
        
        lower_prompt = str(prompt or "").lower()
        
        # 1. Dietary Categories
        high_vitamin = [p['name'] for p in products_db if any(x in p['name'].lower() for x in ['orange', 'kiwi', 'lemon', 'papaya', 'amla'])]
        sugar_free = [p['name'] for p in products_db if any(x in p['name'].lower() for x in ['apple', 'berry', 'strawberry', 'pear'])]
        hot_deals = sorted(products_db, key=lambda x: x['price'])[:3]

        # 2. Match Products
        found_products = [p for p in products_db if p['name'].lower() in lower_prompt]
        
        # 3. Randomized Logic
        if found_products:
             p = found_products[0]
             if any(x in lower_prompt for x in ['price', 'how much', 'cost', 'rate']):
                  price_templates = [
                      f"Fresh {p['name']} is available at ₹{p['price']}/{p.get('unit', 'kg')}. We have a 4.8★ rating for this! Would you like to add it? 🛒",
                      f"You can get our premium {p['name']} for just ₹{p['price']}. It's one of our best-sellers today! 🔥",
                      f"The current rate for {p['name']} is ₹{p['price']} per {p.get('unit', 'kg')}. It's direct from the farm! 🚜✨",
                      f"For the finest {p['name']}, it's ₹{p['price']}. It's extraordinarily juicy today! 🍎💖"
                  ]
                  response = random.choice(price_templates)
             elif any(x in lower_prompt for x in ['health', 'benefit', 'good', 'why']):
                  health_templates = [
                      f"Excellent choice! {p['name']} is packed with nutrition and energy. Great for your daily diet! 🥦⚡",
                      f"{p['name']} is a superfood! It boosts immunity and keeps you active all day. 🏃‍♂️🔥",
                      f"Doctors recommend {p['name']} for its high vitamin content. And we deliver the freshest ones in Delhi! 🩺📦"
                  ]
                  response = random.choice(health_templates)
             else:
                  response = f"The {p['name']} we have in stock is perfect right now! Price: ₹{p['price']}. Ready for 12-min delivery! 🚀🔥"
        
        elif any(x in lower_prompt for x in ['vitamin', 'immunity', 'energy']):
             response = f"Boost your health! I recommend {', '.join(high_vitamin[:3])}. These are Delhi's freshest! 🥝🔋"
             
        elif any(x in lower_prompt for x in ['sugar', 'diabetes', 'diet']):
             response = f"For a healthy diet, try {', '.join(sugar_free[:3])}. Low GI and highly recommended! 🥗🍎"
             
        elif any(x in lower_prompt for x in ['deal', 'offer', 'offer', 'cheap']):
             response = f"Today's Deal: {hot_deals[0]['name']} at just ₹{hot_deals[0]['price']}! Plus, use code WELCOME50 for extra savings! 🏷️💰"
             
        elif any(x in lower_prompt for x in ['track', 'status', 'where']):
             response = "Live tracking is active! Go to 'Profile' -> 'Order History' -> 'Track Order'. Our rider is on the way! 🛵📍"
             
        elif any(x in lower_prompt for x in ['best', 'top', 'popular', 'recommend']):
             response = f"Delhi is loving our {', '.join([p['name'] for p in products_db[:3]])} this week! 📈🔥"
             
        elif any(x in lower_prompt for x in ['delivery', 'fast', 'time']):
             response = "We are the fastest in the city! 🚀 12-minute delivery from Ajay Fruit Mart. No delays, just fresh fruits! 🚚💨"
             
        elif any(x in lower_prompt for x in ['hello', 'hi', 'hey', 'ajay']):
             response = "Hey there! Ajay here. Ready for some fresh fruits in 12 minutes? What can I get you? 🥭🍎"

        elif any(x in lower_prompt for x in ['romantic', 'love', 'girlfriend']):
             response = "Love is sweet! ❤️ Gift your special one our premium Fruit Basket. Use code ROMANCE10 for 10% off! 🍓🎁"

        else:
             response = f"I'm Ajay! Ask me about fruit prices (like Mangoes at ₹200), track your order, or check health tips. Trending: {products_db[0]['name']}! 😊"

        # Try Real AI first, if quota remains, otherwise give this smart response
        if ai_response:
            return jsonify({"success": True, "response": ai_response.replace('*', '').strip(), "source": "gemini_failover"})
        else:
            return jsonify({"success": True, "response": response, "source": "shop_intelligence_v3"})

    except Exception as e:
        safe_print(f"CRITICAL SYSTEM ERROR: {repr(e)}")
        safe_print(traceback.format_exc())
        return jsonify({
            "success": True, 
            "response": "Hello! I'm Ajay. How can I help you find the best fruits? 🍎", 
            "source": "critical_emergency_fallback"
        })

# --- SAFE DATA LOADING ---
def init_critical_files():
    # Ensure all DB files exist with valid JSON
    files = {
        PENDING_FILE: [], APPROVED_FILE: [], USERS_FILE: {}, 
        ORDERS_FILE: [], COMPLAINTS_FILE: [], FEEDBACK_FILE: [], 
        RATINGS_FILE: [], ACTIVITIES_FILE: [], PRODUCTS_FILE: [], 
        SETTINGS_FILE: {'weekend_discount': 5}
    }
    for fpath, default_val in files.items():
        if not os.path.exists(fpath):
            safe_save_json(fpath, default_val)
        else:
            # Validate JSON content
            try:
                with open(fpath, 'r') as f:
                    content = f.read().strip()
                    if not content: raise ValueError("Empty file")
                    json.loads(content)
            except:
                logging.error(f"Corrupted file found: {fpath}. Resetting.")
                safe_save_json(fpath, default_val)

init_critical_files()

# --- ADMIN ENDPOINTS ---
@app.route('/api/admin/clear-activity', methods=['POST'])
def clear_activity():
    global recent_activities
    recent_activities = []
    safe_save_json(ACTIVITIES_FILE, [])
    return jsonify({"success": True})

@app.route('/api/admin/delete-product', methods=['POST'])
def delete_product():
    data = request.json
    pid = data.get('id')
    global products_db
    products_db = [p for p in products_db if p['id'] != pid]
    safe_save_json(PRODUCTS_FILE, products_db)
    return jsonify({"success": True})

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    if data.get('password') == 'admin123': # Simple hardcoded for now
        token = f"admin-session-{random.randint(1000,9999)}"
        return jsonify({"success": True, "token": token})
    return jsonify({"success": False}), 401

@app.route('/api/admin/stats', methods=['GET'])
def admin_stats():
    total_revenue = sum(float(o.get('total', 0)) for o in orders_db if o.get('payment_status') == 'Paid')
    return jsonify({
        "totalRevenue": int(total_revenue),
        "totalOrders": len(orders_db),
        "pendingOrders": len([o for o in orders_db if o.get('delivery_status') == 'Processing']),
        "totalUsers": len(users_db)
    })

@app.route('/api/admin/pending-payments', methods=['GET'])
def get_pending_payments():
    return jsonify(pending_verifications)

# Global error handler to prevent HTML errors
@app.errorhandler(500)
def internal_error(error):
    safe_print(f"500 Error caught: {repr(error)}")
    return jsonify({"success": False, "message": "Server encountered an error. Please try again."}), 500

@app.route('/admin')
def serve_admin():
    return send_from_directory(ROOT_DIR, 'admin.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(ROOT_DIR, path)

# --- STARTUP ---
load_data()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    safe_print(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
