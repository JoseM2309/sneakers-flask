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
    print("📩 Entrando a /login")
    recaptcha_secret_key = "6LcH8CUsAAAAACWvVURLaTuluhccnFkGH8Tf7c_-"

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        token = request.form.get('g-recaptcha-response')  # <-- Captura token

        print("Email recibido:", email)
        print("Password recibido:", password)
        print("Token reCAPTCHA:", token)

        
        # Verificar reCAPTCHA
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
            print("Resultado reCAPTCHA:", result)
        except Exception as e:
            print("Error reCAPTCHA:", e)
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
        print("Usuario encontrado:", usuario)

        if not usuario:
            flash("Correo o contraseña incorrectos.", "error")
            return redirect(url_for('login'))

        # IMPORTANTE: verifica que tu campo exista
        password_hash = usuario.password_hash if hasattr(usuario, 'password_hash') else usuario.password

        if check_password_hash(password_hash, password):
            login_user(usuario)
            flash(f"Bienvenido {usuario.nombre}!", "success")
            return redirect(url_for('index'))
        else:
            flash("Correo o contraseña incorrectos.", "error")
            return redirect(url_for('login'))

    return render_template("login.html")


@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')

        # Revisar si ya existe
        usuario = obtener_usuario_por_email(email)
        if usuario:
            flash("El correo ya está registrado.", "error")
            return redirect(url_for('registro'))

        # Guardar usuario
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
# CONÓCENOS
# ==============================
@app.route('/conocenos')
def conocenos():
    return render_template('conocenos.html')

# ==============================
# PRODUCTOS
# ==============================
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

        lista = [
            {"id": p[0], "nombre": p[1], "descripcion": p[2], "precio": p[3], "imagen": p[4]}
            for p in productos
        ]

        if lista:
            productos_por_marca.append({
                "marca": marca_nombre,
                "productos": lista
            })

    cur.close()
    conn.close()

    return render_template("productos.html", productos_por_marca=productos_por_marca)

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
# ACTUALIZAR CANTIDAD
# ==============================
@app.route('/actualizar_cantidad/<int:id>/<string:accion>')
def actualizar_cantidad(id, accion):
    carrito = session.get('carrito', [])

    for item in carrito:
        if item['id'] == id:
            if accion == "sumar":
                item['cantidad'] += 1
            elif accion == "restar":
                item['cantidad'] -= 1
                if item['cantidad'] <= 0:
                    carrito = [p for p in carrito if p['id'] != id]
            break

    session['carrito'] = carrito
    return ("", 204)

# ==============================
# CARRITO
# ==============================
@app.route('/carrito')
def carrito():
    carrito = session.get('carrito', [])
    subtotal = sum(item['precio'] * item['cantidad'] for item in carrito)
    envio = 150 if subtotal < 1000 else 0
    total = subtotal + envio

    recaptcha_site_key = os.environ.get('RECAPTCHA_SITE_KEY')

    return render_template(
        'carrito.html',
        carrito=carrito,
        subtotal=subtotal,
        envio=envio,
        total=total,
        recaptcha_site_key=recaptcha_site_key
    )

# ==============================
# VACIAR CARRITO
# ==============================
@app.route('/vaciar_carrito')
def vaciar_carrito():
    session['carrito'] = []
    return redirect(url_for('carrito'))

# ==============================
# ELIMINAR DEL CARRITO
# ==============================
@app.route('/eliminar_carrito/<int:id>')
def eliminar_carrito(id):
    carrito = session.get('carrito', [])
    carrito = [item for item in carrito if item['id'] != id]
    session['carrito'] = carrito
    return redirect(url_for('carrito'))

# ==============================
# CONTACTO (reCAPTCHA FIX)
# ==============================
@app.route('/contacto', methods=['GET', 'POST'])
def contacto():
    recaptcha_site_key = "6LfgThQsAAAAAKBIskJdPoTp_e9DeehR4fWAOZQc"
    recaptcha_secret_key = "6LfgThQsAAAAANgjrKYNTDeOT9kwDhWpz2vAqbC4"

    if request.method == 'POST':
        token = request.form.get('g-recaptcha-response')

        try:
            response = requests.post(
                'https://www.google.com/recaptcha/api/siteverify',
                data={'secret': recaptcha_secret_key, 'response': token},
                timeout=5  # <---- FIX RENDER
            )
            result = response.json()
        except:
            flash("Error al verificar reCAPTCHA. Intenta de nuevo.", "error")
            return redirect(url_for('contacto'))

        if not result.get('success'):
            flash("reCAPTCHA no verificado. Intenta de nuevo.", "error")
            return redirect(url_for('contacto'))

        nombre = request.form.get('nombre')
        email = request.form.get('email')
        mensaje = request.form.get('mensaje')

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO mensajes_contacto (nombre, email, mensaje)
            VALUES (%s, %s, %s)
        """, (nombre, email, mensaje))
        conn.commit()
        cur.close()
        conn.close()

        flash("Mensaje enviado con éxito", "success")
        return render_template(
            'contacto.html', 
            mensaje_enviado=True, 
            recaptcha_site_key=recaptcha_site_key
        )

    return render_template("contacto.html", recaptcha_site_key=recaptcha_site_key)

# ==============================
# MENÚ CHATBOT
# ==============================
chat_menu = {
    "inicio": {
        "Precios": "Consulta los precios de nuestros productos de manera rápida.",
        "Envíos": "Información sobre envíos y tiempos de entrega.",
        "Métodos de pago": "Aceptamos tarjetas, PayPal y transferencia bancaria.",
        "Disponibilidad": "Verifica si un producto está disponible.",
        "Productos destacados": "Aquí están nuestros productos más populares."
    },
    "Precios": ["Tallas", "Modelos", "Inicio"],
    "Envíos": ["México", "Internacional", "Inicio"],
    "Métodos de pago": ["Tarjeta", "PayPal", "Transferencia", "Inicio"],
    "Disponibilidad": ["AirMax", "Jordan", "React", "Inicio"],
    "Productos destacados": ["AirMax", "Jordan", "React", "Inicio"]
}

# ==============================
# API CHATBOT
# ==============================
@app.route("/api/chatbot", methods=["POST"])
def api_chatbot():
    data = request.get_json()
    option = data.get("option")

    if option in chat_menu["inicio"]:
        reply = chat_menu["inicio"][option]
        options = chat_menu.get(option, ["Inicio"])
        if option == "Productos destacados":
            reply += "\nHaz clic en el producto para verlo."
        return jsonify({"reply": reply, "options": options})

    if option == "Tallas":
        return jsonify({"reply": "Disponemos de tallas del 24 al 30 para todos los modelos.", 
                        "options": ["Precios", "Inicio"]})

    if option == "Modelos":
        return jsonify({"reply": "Tenemos modelos AirMax, Jordan y React disponibles.", 
                        "options": ["Precios", "Inicio"]})

    if option == "México":
        return jsonify({"reply": "Los envíos dentro de México tardan 2-5 días hábiles.", 
                        "options": ["Envíos", "Inicio"]})

    if option == "Internacional":
        return jsonify({"reply": "Los envíos internacionales tardan 7-15 días hábiles.", 
                        "options": ["Envíos", "Inicio"]})

    if option == "Tarjeta":
        return jsonify({"reply": "Aceptamos Visa, Mastercard y American Express.", 
                        "options": ["Métodos de pago", "Inicio"]})

    if option == "PayPal":
        return jsonify({"reply": "Puedes pagar de forma segura con PayPal.", 
                        "options": ["Métodos de pago", "Inicio"]})

    if option == "Transferencia":
        return jsonify({"reply": "También aceptamos transferencias bancarias.", 
                        "options": ["Métodos de pago", "Inicio"]})

    if option in ["AirMax", "Jordan", "React"]:
        return jsonify({"reply": f"Puedes ver los {option} aquí: /productos/{option}", 
                        "options": ["Disponibilidad", "Inicio"]})

    if option == "Inicio":
        return jsonify({"reply": "Menú principal:", 
                        "options": list(chat_menu["inicio"].keys())})

    return jsonify({"reply": "Opción no reconocida 😅 Por favor elige una opción del menú.", 
                    "options": ["Inicio"]})

# ==============================
# PAGO COMPLETADO
# ==============================
@app.post("/pago_completado")
def pago_completado():
    data = request.get_json()
    recaptcha_token = data.get("recaptcha_token")
    recaptcha_secret = os.environ.get("RECAPTCHA_SECRET_KEY")

    try:
        response = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={"secret": recaptcha_secret, "response": recaptcha_token},
            timeout=5   # <---- FIX RENDER
        )
        result = response.json()
    except:
        return jsonify({"status": "error", "mensaje": "Error verificando reCAPTCHA"}), 400

    if not result.get("success") or result.get("score", 0) < 0.5:
        return jsonify({"status": "error", "mensaje": "reCAPTCHA fallido"}), 400

    print("PAGO RECIBIDO:", data["detalles"]["id"])
    print("COMPRADOR:", data["detalles"]["payer"]["name"]["given_name"])

    session['carrito'] = []

    return jsonify({"status": "ok"})

# ==============================
# RUN SERVER
# ==============================
if __name__ == "__main__":
    app.run(debug=True)

