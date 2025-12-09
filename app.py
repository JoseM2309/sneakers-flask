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
        email = request.form.get('email')
        password = request.form.get('password')
        token = request.form.get('g-recaptcha-response')  # Captura token

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
        except Exception as e:
            flash("Error al verificar reCAPTCHA. Intenta de nuevo.", "error")
            return redirect(url_for('login'))

        if not result.get("success"):
            flash("reCAPTCHA no verificado. Intenta de nuevo.", "error")
            return redirect(url_for('login'))

        if not email or not password:
            flash("Correo o contraseña incorrectos.", "error")
            return redirect(url_for('login'))

        email = email.strip().lower()
        usuario = obtener_usuario_por_email(email)

        if not usuario or not check_password_hash(usuario.password_hash, password):
            flash("Correo o contraseña incorrectos.", "error")
            return redirect(url_for('login'))

        login_user(usuario)
        flash(f"Bienvenido {usuario.nombre}!", "success")
        return redirect(url_for('index'))

    recaptcha_site_key = "6LcH8CUsAAAAADZ49CVB5T1W9_Z4AiYElGbbqkeU"
    return render_template("login.html", recaptcha_site_key=recaptcha_site_key)


@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')

        usuario = obtener_usuario_por_email(email)
        if usuario:
            flash("El correo ya está registrado.", "error")
            return redirect(url_for('registro'))

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO usuarios (nombre, email, password) VALUES (%s,%s,%s)",
                    (nombre, email, generate_password_hash(password)))
        conn.commit()
        cur.close()
        conn.close()

        flash("Registro exitoso. Ahora puedes iniciar sesión.", "success")
        return redirect(url_for('login'))

    return render_template("registro.html")


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/conocenos')
def conocenos():
    return render_template('conocenos.html')


@app.route('/productos')
def productos():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre FROM marcas;")
    marcas_filas = cur.fetchall()

    productos_por_marca = []
    for marca_id, marca_nombre in marcas_filas:
        cur.execute("""
            SELECT id, nombre, descripcion, precio, imagen
            FROM productos
            WHERE marca_id = %s
        """, (marca_id,))
        productos = cur.fetchall()
        lista = [{"id": p[0], "nombre": p[1], "descripcion": p[2], "precio": p[3], "imagen": p[4]} for p in productos]

        if lista:
            productos_por_marca.append({"marca": marca_nombre, "productos": lista})

    cur.close()
    conn.close()
    return render_template("productos.html", productos_por_marca=productos_por_marca)


@app.route('/carrito')
def carrito():
    carrito = session.get('carrito', [])
    subtotal = sum(item['precio'] * item['cantidad'] for item in carrito)
    envio = 150 if subtotal < 1000 else 0
    total = subtotal + envio
    return render_template('carrito.html', carrito=carrito, subtotal=subtotal, envio=envio, total=total)


# ==============================
# CHATBOT API (TEXTO LIBRE)
# ==============================
chat_menu = {
    "Precios": "Consulta los precios de nuestros productos.",
    "Envíos": "Información sobre envíos y tiempos de entrega.",
    "Métodos de pago": "Aceptamos tarjetas, PayPal y transferencia bancaria.",
    "Disponibilidad": "Verifica si un producto está disponible.",
    "Productos destacados": "Nuestros productos más populares: AirMax, Jordan, React."
}

keywords = {
    "precio": "Precios",
    "coste": "Precios",
    "envío": "Envíos",
    "entrega": "Envíos",
    "pago": "Métodos de pago",
    "tarjeta": "Métodos de pago",
    "paypal": "Métodos de pago",
    "transferencia": "Métodos de pago",
    "disponible": "Disponibilidad",
    "productos": "Productos destacados",
    "airmax": "Productos destacados",
    "jordan": "Productos destacados",
    "react": "Productos destacados"
}

@app.route("/api/chatbot", methods=["POST"])
def api_chatbot():
    data = request.get_json()
    user_input = data.get("option", "").lower()

    matched_option = None
    for key, option in keywords.items():
        if key in user_input:
            matched_option = option
            break

    if matched_option:
        reply = chat_menu.get(matched_option, "Lo siento, no tengo información sobre eso.")
        return jsonify({"reply": reply})

    return jsonify({"reply": "No entendí tu mensaje 😅 Por favor escribe otra cosa relacionada con nuestros productos o servicios."})


# ==============================
# RUN SERVER
# ==============================
if __name__ == "__main__":
    app.run(debug=True)
