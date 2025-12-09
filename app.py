import os
os.environ.setdefault("WERKZEUG_HASH_METHOD", "pbkdf2:sha256")

from flask import Flask, render_template, request, session, redirect, url_for, jsonify, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import requests

# ==============================
# FLASK APP
# ==============================
app = Flask(__name__)
app.secret_key = "sneakersmx_secret_key"

# ==============================
# FLASK LOGIN CONFIG
# ==============================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ==============================
# CONEXIÓN A BD
# ==============================
def get_db_connection():
    conn = psycopg2.connect(
        host="dpg-d4fbdtodl3ps73cr042g-a.oregon-postgres.render.com",
        database="sneakers_db_g0p6",
        user="sneakers_db_g0p6_user",
        password="upV4O9iC3ATKiIWKPpV657s9Qg1nlrZL",
        port="5432",
        sslmode="require"
    )
    return conn

# ==============================
# CLASE USUARIO
# ==============================
class User(UserMixin):
    def __init__(self, id, nombre, email, password_hash):
        self.id = str(id)
        self.nombre = nombre
        self.email = email
        self.password_hash = password_hash

# ==============================
# FUNCIONES DE CONSULTA
# ==============================
def obtener_usuario_por_email(email):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre, email, password FROM usuarios WHERE email=%s", (email,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if row:
        return User(id=row[0], nombre=row[1], email=row[2], password_hash=row[3])
    return None

def obtener_usuario_por_id(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre, email, password FROM usuarios WHERE id=%s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if row:
        return User(id=row[0], nombre=row[1], email=row[2], password_hash=row[3])
    return None

# ==============================
# LOAD USER
# ==============================
@login_manager.user_loader
def load_user(user_id):
    return obtener_usuario_por_id(user_id)

# ==============================
# LOGIN
# ==============================
@app.route('/login', methods=['GET', 'POST'])
def login():
    recaptcha_secret_key = "6LcH8CUsAAAAACWvVURLaTuluhccnFkGH8Tf7c_-"

    if request.method == 'POST':
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')
        token = request.form.get('g-recaptcha-response')

        if not token:
            flash("Por favor, verifica el reCAPTCHA.", "error")
            return redirect(url_for('login'))

        try:
            response = requests.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={"secret": recaptcha_secret_key, "response": token},
                timeout=5
            )
            result = response.json()
        except:
            flash("Error al verificar reCAPTCHA. Intenta de nuevo.", "error")
            return redirect(url_for('login'))

        if not result.get("success"):
            flash("reCAPTCHA no verificado. Intenta de nuevo.", "error")
            return redirect(url_for('login'))

        usuario = obtener_usuario_por_email(email)
        if usuario and check_password_hash(usuario.password_hash, password):
            login_user(usuario)
            flash(f"Bienvenido {usuario.nombre}!", "success")
            return redirect(url_for('index'))
        else:
            flash("Correo o contraseña incorrectos.", "error")
            return redirect(url_for('login'))

    recaptcha_site_key = "6LcH8CUsAAAAADZ49CVB5T1W9_Z4AiYElGbbqkeU"
    return render_template("login.html", recaptcha_site_key=recaptcha_site_key)

# ==============================
# REGISTRO
# ==============================
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')

        if obtener_usuario_por_email(email):
            flash("El correo ya está registrado.", "error")
            return redirect(url_for('registro'))

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO usuarios (nombre, email, password)
            VALUES (%s, %s, %s)
        """, (nombre, email, generate_password_hash(password)))
        conn.commit()
        cur.close()
        conn.close()

        flash("Registro exitoso. Ahora puedes iniciar sesión.", "success")
        return redirect(url_for('login'))

    return render_template("registro.html")

# ==============================
# LOGOUT
# ==============================
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# ==============================
# HOME
# ==============================
@app.route('/')
def index():
    return render_template('index.html')

# ==============================
# PRODUCTOS
# ==============================
@app.route('/productos')
def productos():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre, descripcion, precio, imagen FROM productos")
    productos = cur.fetchall()
    cur.close()
    conn.close()

    lista_productos = [
        {"id": p[0], "nombre": p[1], "descripcion": p[2], "precio": p[3], "imagen": p[4]}
        for p in productos
    ]
    return render_template("productos.html", productos=lista_productos)

# ==============================
# AGREGAR AL CARRITO
# ==============================
@app.route('/agregar_carrito/<int:id>')
def agregar_carrito(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre, precio, imagen FROM productos WHERE id=%s", (id,))
    fila = cur.fetchone()
    cur.close()
    conn.close()

    if fila:
        carrito = session.get('carrito', [])
        encontrado = next((p for p in carrito if p['id'] == fila[0]), None)

        if encontrado:
            encontrado['cantidad'] += 1
        else:
            carrito.append({
                'id': fila[0],
                'nombre': fila[1],
                'precio': float(fila[2]),
                'imagen': fila[3],
                'cantidad': 1
            })
        session['carrito'] = carrito

    return jsonify({"mensaje": "agregado"})

# ==============================
# TOTAL DEL CARRITO
# ==============================
def calcular_total_carrito():
    carrito = session.get('carrito', [])
    subtotal = sum(item['precio'] * item['cantidad'] for item in carrito)
    envio = 150 if subtotal < 1000 else 0
    total = subtotal + envio
    return subtotal, envio, total

# ==============================
# API CHATBOT DINÁMICO
# ==============================
@app.route("/api/chatbot", methods=["POST"])
def api_chatbot():
    data = request.get_json()
    user_input = data.get("option", "").lower()
    reply = "No entendí tu mensaje 😅. Intenta de nuevo."

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre, precio FROM productos")
    productos = cur.fetchall()  # [(id, nombre, precio)]
    cur.close()
    conn.close()

    # 1️⃣ Producto específico
    for prod_id, nombre, precio in productos:
        if nombre.lower() in user_input:
            reply = f"El producto {nombre} cuesta ${precio:.2f}. Puedes verlo aquí: /productos/{prod_id}"
            return jsonify({"reply": reply})

    # 2️⃣ Precios generales
    if "precio" in user_input or "coste" in user_input:
        reply = "Tenemos AirMax, Jordan y React. Dime el nombre del modelo y te diré su precio."
        return jsonify({"reply": reply})

    # 3️⃣ Envíos
    if "envío" in user_input or "entrega" in user_input:
        reply = "Envíos México: 2-5 días hábiles. Internacional: 7-15 días hábiles."
        return jsonify({"reply": reply})

    # 4️⃣ Métodos de pago
    if "pago" in user_input or "tarjeta" in user_input or "paypal" in user_input or "transferencia" in user_input:
        reply = "Aceptamos Visa, Mastercard, PayPal y transferencias. ¿Cuál quieres usar?"
        return jsonify({"reply": reply})

    # 5️⃣ Total del carrito
    if "total" in user_input or "carrito" in user_input:
        carrito = session.get('carrito', [])
        if carrito:
            subtotal, envio, total = calcular_total_carrito()
            reply = f"Tu carrito tiene {len(carrito)} productos. Subtotal: ${subtotal:.2f}, Envío: ${envio:.2f}, Total: ${total:.2f}"
        else:
            reply = "Tu carrito está vacío."
        return jsonify({"reply": reply})

    return jsonify({"reply": reply})
    
# ==============================
# RUN SERVER
# ==============================
if __name__ == "__main__":
    app.run(debug=True)
