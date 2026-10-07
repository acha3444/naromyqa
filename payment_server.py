import urllib.request
import urllib.parse
import json
import base64
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from http.server import HTTPServer, SimpleHTTPRequestHandler
import random
import os

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "sk_live_votre_cle_secrete_ici")

# --- CONFIGURATION MAILING (KLAVIYO) ---
# Vous avez fait le choix royal pour l'e-commerce !
# 1. Créez votre compte sur Klaviyo.com
# 2. Allez dans Settings > API Keys et créez une Private API Key
KLAVIYO_PRIVATE_KEY = "votre_cle_api_privee_klaviyo"

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
    
    # Appel de l'API REST officielle de Klaviyo (v3) pour déclencher votre Flux d'e-mail
    try:
        url = 'https://a.klaviyo.com/api/events/'
        payload = {
            "data": {
                "type": "event",
                "attributes": {
                    "profile": {
                        "email": user_email
                    },
                    "metric": {
                        "name": "Placed Order"
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
            # Endpoint appelé APRÈS le succès du paiement Stripe
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            order_id = 'NRM-' + str(random.randint(10000, 99999))
            email = data.get('email', '')
            amount = data.get('amount', 0)
            items = json.dumps(data.get('items', []))
            date_str = datetime.now().strftime("%d/%m/%Y")
            
            # Enregistrement dans la vraie base de données locale (SQLite)
            conn = sqlite3.connect('naromyqa_orders.db')
            c = conn.cursor()
            c.execute("INSERT INTO orders (id, email, status, amount, date, items) VALUES (?, ?, ?, ?, ?, ?)",
                      (order_id, email, 1, amount, date_str, items)) # Status 1 = Confirmée
            conn.commit()
            conn.close()
            
            # Déclenchement de l'email
            send_confirmation_email(order_id, email, amount)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'orderId': order_id}).encode('utf-8'))
            
        elif self.path == '/track-order':
            # Endpoint pour la page suivi.html
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
    print("Backend de paiement + Mailing + Base de données démarré sur http://localhost:8083 ...")
    server.serve_forever()
