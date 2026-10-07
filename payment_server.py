import urllib.request
import urllib.parse
import json
import base64
import sqlite3
import random
import os
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Chargement ultra-léger du fichier .env pour protéger les clés secrètes
try:
    with open('.env', 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                os.environ[k] = v
except FileNotFoundError:
    pass

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "sk_live_votre_cle_secrete_ici")
KLAVIYO_PRIVATE_KEY = os.environ.get("KLAVIYO_PRIVATE_KEY", "votre_cle_api_privee_klaviyo")
SENDCLOUD_PUBLIC = os.environ.get("SENDCLOUD_PUBLIC", "votre_cle_publique_sendcloud")
SENDCLOUD_SECRET = os.environ.get("SENDCLOUD_SECRET", "votre_cle_secrete_sendcloud")

def init_db():
    conn = sqlite3.connect('naromyqa_orders.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS orders
                 (id TEXT PRIMARY KEY, email TEXT, status INTEGER, amount REAL, date TEXT, items TEXT)''')
    conn.commit()
    conn.close()

def send_confirmation_email(order_id, user_email, amount):
    if KLAVIYO_PRIVATE_KEY == "votre_cle_api_privee_klaviyo":
        print(f"[KLAVIYO] ⚠️ Événement non envoyé: Veuillez configurer votre Clé API Privée Klaviyo dans payment_server.py.")
        print(f"[KLAVIYO] Simulation: Événement 'Placed Order' théorique envoyé pour {user_email} (Commande {order_id})")
        return
    
    try:
        url = 'https://a.klaviyo.com/api/events/'
        payload = {
            "data": {
                "type": "event",
                "attributes": {
                    "profile": {
                        "data": {
                            "type": "profile",
                            "attributes": {
                                "email": user_email
                            }
                        }
                    },
                    "metric": {
                        "data": {
                            "type": "metric",
                            "attributes": {
                                "name": "Placed Order"
                            }
                        }
                    },
                    "properties": {
                        "OrderId": order_id,
                        "Value": amount,
                        "Currency": "EUR"
                    }
                }
            }
        }
        
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'))
        req.add_header('Authorization', f'Klaviyo-API-Key {KLAVIYO_PRIVATE_KEY}')
        req.add_header('Content-Type', 'application/json')
        req.add_header('revision', '2023-12-15')
        
        urllib.request.urlopen(req)
        print(f"[KLAVIYO] Succès: Événement 'Placed Order' envoyé pour {user_email}. Le mail va partir via votre flux Klaviyo !")
    except Exception as e:
        print(f"[KLAVIYO] Erreur lors de l'envoi à Klaviyo: {e}")

def create_sendcloud_parcel(order_id, email, shipping):
    if SENDCLOUD_PUBLIC == "votre_cle_publique_sendcloud":
        print(f"[SENDCLOUD] ⚠️ Colis non créé: Identifiants Sendcloud manquants.")
        return
        
    try:
        url = 'https://panel.sendcloud.sc/api/v2/parcels'
        payload = {
            "parcel": {
                "name": f"{shipping.get('first_name', '')} {shipping.get('last_name', '')}",
                "address": shipping.get('address', ''),
                "house_number": shipping.get('apartment', ' '), # Sendcloud requires something here usually, or parses it
                "city": shipping.get('city', ''),
                "postal_code": shipping.get('postal_code', ''),
                "country": shipping.get('country', 'FR'),
                "telephone": shipping.get('phone', ''),
                "email": email,
                "order_number": order_id,
                "request_label": False
            }
        }
        
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'))
        auth_str = f"{SENDCLOUD_PUBLIC}:{SENDCLOUD_SECRET}"
        auth_b64 = base64.b64encode(auth_str.encode('ascii')).decode('ascii')
        req.add_header('Authorization', f'Basic {auth_b64}')
        req.add_header('Content-Type', 'application/json')
        
        urllib.request.urlopen(req)
        print(f"[SENDCLOUD] Succès: Commande {order_id} transmise à Sendcloud pour expédition.")
    except Exception as e:
        print(f"[SENDCLOUD] Erreur lors de la création du colis: {e}")

class CORSRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.end_headers()

    def do_POST(self):
        if self.path == '/create-payment-intent':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            amount = data.get('amount', 1000)

            url = 'https://api.stripe.com/v1/payment_intents'
            req_data = urllib.parse.urlencode({
                'amount': amount,
                'currency': 'eur',
                'automatic_payment_methods[enabled]': 'true'
            }).encode('utf-8')
            
            req = urllib.request.Request(url, data=req_data)
            auth_str = f"{STRIPE_SECRET_KEY}:"
            auth_b64 = base64.b64encode(auth_str.encode('ascii')).decode('ascii')
            req.add_header('Authorization', f'Basic {auth_b64}')
            
            try:
                response = urllib.request.urlopen(req)
                resp_data = json.loads(response.read())
                client_secret = resp_data.get('client_secret')
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'clientSecret': client_secret}).encode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
                
        elif self.path == '/create-order':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            order_id = 'NRM-' + str(random.randint(10000, 99999))
            email = data.get('email', '')
            amount = data.get('amount', 0)
            items = json.dumps(data.get('items', []))
            shipping = data.get('shipping', {})
            date_str = datetime.now().strftime("%d/%m/%Y")
            
            conn = sqlite3.connect('naromyqa_orders.db')
            c = conn.cursor()
            c.execute("INSERT INTO orders (id, email, status, amount, date, items) VALUES (?, ?, ?, ?, ?, ?)",
                      (order_id, email, 1, amount, date_str, items))
            conn.commit()
            conn.close()
            
            # Déclencheurs Asynchrones/Externes
            send_confirmation_email(order_id, email, amount)
            create_sendcloud_parcel(order_id, email, shipping)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'orderId': order_id}).encode('utf-8'))
            
        elif self.path == '/track-order':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            order_id = data.get('orderId', '')
            email = data.get('email', '')
            
            conn = sqlite3.connect('naromyqa_orders.db')
            c = conn.cursor()
            c.execute("SELECT status, date FROM orders WHERE id=? AND email=?", (order_id, email))
            result = c.fetchone()
            conn.close()
            
            if result:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': result[0], 'date': result[1]}).encode('utf-8'))
            else:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Not found'}).encode('utf-8'))

if __name__ == '__main__':
    init_db()
    server = HTTPServer(('localhost', 8083), CORSRequestHandler)
    print("Backend de paiement + Klaviyo + Base de données démarré sur http://localhost:8083 ...")
    server.serve_forever()
