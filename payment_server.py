import urllib.request
import urllib.parse
import json
import base64
import sqlite3
import random
import os
import time
from datetime import datetime
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Rate limiting simple en mémoire (IP -> [timestamps])
RATE_LIMIT_DATA = {}
RATE_LIMIT_WINDOW = 60 # 60 secondes
RATE_LIMIT_MAX_REQUESTS = 10 # 10 requêtes par minute par IP

# Chargement ultra-léger du fichier .env pour protéger les clés secrètes
try:
    with open('.env', 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                os.environ[k] = v
except FileNotFoundError:
    pass

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
KLAVIYO_PRIVATE_KEY = os.environ.get("KLAVIYO_PRIVATE_KEY")
SENDCLOUD_PUBLIC = os.environ.get("SENDCLOUD_PUBLIC", "votre_cle_publique_sendcloud")
SENDCLOUD_SECRET = os.environ.get("SENDCLOUD_SECRET", "votre_cle_secrete_sendcloud")

if not STRIPE_SECRET_KEY or STRIPE_SECRET_KEY == "sk_live_votre_cle_secrete_ici":
    print("[CRITICAL] La clé STRIPE_SECRET_KEY est manquante dans l'environnement !")
    # sys.exit(1) # Commenté pour éviter de casser le serveur de démo, mais fortement recommandé en prod

if not KLAVIYO_PRIVATE_KEY or KLAVIYO_PRIVATE_KEY == "votre_cle_api_privee_klaviyo":
    print("[WARNING] La clé KLAVIYO_PRIVATE_KEY est manquante !")

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

def send_welcome_event(user_email, first_name):
    if KLAVIYO_PRIVATE_KEY == "votre_cle_api_privee_klaviyo":
        print(f"[KLAVIYO] Simulation: Événement 'Account Created' envoyé pour {user_email}")
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
                                "email": user_email,
                                "first_name": first_name
                            }
                        }
                    },
                    "metric": {
                        "data": {
                            "type": "metric",
                            "attributes": {
                                "name": "Account Created"
                            }
                        }
                    },
                    "properties": {
                        "AccountType": "Customer"
                    }
                }
            }
        }
        
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'))
        req.add_header('Authorization', f'Klaviyo-API-Key {KLAVIYO_PRIVATE_KEY}')
        req.add_header('Content-Type', 'application/json')
        req.add_header('revision', '2023-12-15')
        
        urllib.request.urlopen(req)
        print(f"[KLAVIYO] Succès: Événement 'Account Created' envoyé pour {user_email}.")
    except Exception as e:
        print(f"[KLAVIYO] Erreur lors de l'envoi de l'événement de bienvenue: {e}")

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
        origin = self.headers.get('Origin', '')
        allowed_origins = ['http://localhost:8082', 'https://naromyqa-3umj.vercel.app']
        if origin in allowed_origins:
            self.send_header('Access-Control-Allow-Origin', origin)
        else:
            self.send_header('Access-Control-Allow-Origin', 'https://naromyqa-3umj.vercel.app')
            
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.end_headers()
        
    def check_rate_limit(self):
        client_ip = self.client_address[0]
        now = time.time()
        
        if client_ip not in RATE_LIMIT_DATA:
            RATE_LIMIT_DATA[client_ip] = []
            
        # Nettoyer les vieilles requêtes
        RATE_LIMIT_DATA[client_ip] = [t for t in RATE_LIMIT_DATA[client_ip] if now - t < RATE_LIMIT_WINDOW]
        
        if len(RATE_LIMIT_DATA[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
            return False
            
        RATE_LIMIT_DATA[client_ip].append(now)
        return True

    def do_GET(self):
        if not self.check_rate_limit():
            self.send_response(429)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Too many requests'}).encode('utf-8'))
            return
            
        if self.path == '/products':
            url = 'https://api.stripe.com/v1/products?active=true&expand[]=data.default_price'
            req = urllib.request.Request(url)
            auth_str = f"{STRIPE_SECRET_KEY}:"
            auth_b64 = base64.b64encode(auth_str.encode('ascii')).decode('ascii')
            req.add_header('Authorization', f'Basic {auth_b64}')
            
            try:
                response = urllib.request.urlopen(req)
                resp_data = json.loads(response.read())
                
                products = []
                for p in resp_data.get('data', []):
                    price_obj = p.get('default_price')
                    if price_obj and not isinstance(price_obj, str):
                        price = price_obj.get('unit_amount', 0) / 100.0
                    else:
                        price = 0
                        
                    image = p.get('images')[0] if p.get('images') else 'assets/khimar-noir.jpg'
                    
                    products.append({
                        'id': p.get('id'),
                        'name': p.get('name'),
                        'description': p.get('description'),
                        'price': price,
                        'image': image
                    })
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(products).encode('utf-8'))
            except Exception as e:
                print(f"[ERROR] /products: {e}")
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Erreur interne du serveur'}).encode('utf-8'))

    def do_POST(self):
        if not self.check_rate_limit():
            self.send_response(429)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Too many requests'}).encode('utf-8'))
            return
            
        if self.path == '/create-payment-intent':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            cart = data.get('cart', [])
            
            # Recalculer le montant côté serveur pour la sécurité !
            calculated_amount = 0
            if not cart:
                # Fallback non sécurisé si l'ancien frontend ne donne pas le panier
                calculated_amount = data.get('amount', 1000)
            else:
                try:
                    # Interroger Stripe pour avoir les vrais prix
                    url_products = 'https://api.stripe.com/v1/products?active=true&expand[]=data.default_price'
                    req_p = urllib.request.Request(url_products)
                    auth_b64 = base64.b64encode(f"{STRIPE_SECRET_KEY}:".encode('ascii')).decode('ascii')
                    req_p.add_header('Authorization', f'Basic {auth_b64}')
                    resp_p = urllib.request.urlopen(req_p)
                    stripe_data = json.loads(resp_p.read()).get('data', [])
                    
                    price_map = {}
                    for p in stripe_data:
                        price_obj = p.get('default_price')
                        if price_obj and not isinstance(price_obj, str):
                            price_map[p.get('name')] = price_obj.get('unit_amount', 0)
                            
                    for item in cart:
                        name = item.get('name')
                        qty = int(item.get('quantity', 1))
                        # Prix depuis Stripe, sinon fallback à 3490 (34.90€) par défaut
                        real_price = price_map.get(name, 3490)
                        calculated_amount += real_price * qty
                        
                    # Ajouter livraison si besoin (80€ = 8000 centimes)
                    if calculated_amount > 0 and calculated_amount < 8000:
                        calculated_amount += 490 # Frais de port de 4.90€
                except Exception as e:
                    print(f"[SECURITY] Erreur de vérification des prix Stripe, fallback au prix client: {e}")
                    calculated_amount = data.get('amount', 1000)

            url = 'https://api.stripe.com/v1/payment_intents'
            req_data = urllib.parse.urlencode({
                'amount': calculated_amount,
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
                print(f"[ERROR] /create-payment-intent: {e}")
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Erreur interne du serveur'}).encode('utf-8'))
                
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
            
        elif self.path == '/welcome-event':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            email = data.get('email', '')
            first_name = data.get('first_name', '')
            
            send_welcome_event(email, first_name)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))
            
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
    # Render (et autres hébergeurs) utilise la variable d'environnement PORT
    port = int(os.environ.get('PORT', 8083))
    # Il faut absolument écouter sur '0.0.0.0' (toutes les adresses) et non pas 'localhost' pour le cloud
    server = HTTPServer(('0.0.0.0', port), CORSRequestHandler)
    print(f"Backend de paiement + Klaviyo + Base de données démarré sur le port {port} ...")
    server.serve_forever()
