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
# RUTAS PRINCIPALES
# ==============================
@app.route('/')
def index():
    return render_template('index.html')

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

@app.route('/conocenos')
def conocenos():
    return render_template('conocenos.html')

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

@app.route('/login', methods=['GET', 'POST'])
def login():
    recaptcha_secret_key = "TU_SECRET_KEY"
    if request.method == 'POST':
        email = request.form.get('email')
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
        except Exception as e:
            flash("Error al verificar reCAPTCHA.", "error")
            return redirect(url_for('login'))

        if not result.get("success"):
            flash("reCAPTCHA no verificado.", "error")
            return redirect(url_for('login'))

        usuario = obtener_usuario_por_email(email.strip().lower())
        if not usuario or not check_password_hash(usuario.password_hash, password):
            flash("Correo o contraseña incorrectos.", "error")
            return redirect(url_for('login'))

        login_user(usuario)
        flash(f"Bienvenido {usuario.nombre}!", "success")
        return redirect(url_for('index'))

    recaptcha_site_key = "TU_SITE_KEY"
    return render_template("login.html", recaptcha_site_key=recaptcha_site_key)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# ==============================
# CONTACTO
# ==============================
@app.route('/contacto', methods=['GET', 'POST'])
def contacto():
    recaptcha_site_key = "TU_SITE_KEY"
    recaptcha_secret_key = "TU_SECRET_KEY"

    if request.method == 'POST':
        token = request.form.get('g-recaptcha-response')

        try:
            response = requests.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={"secret": recaptcha_secret_key, "response": token},
                timeout=5
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
        return render_template('contacto.html', mensaje_enviado=True, recaptcha_site_key=recaptcha_site_key)

    return render_template("contacto.html", recaptcha_site_key=recaptcha_site_key)

# ==============================
# CARRITO
# ==============================
@app.route('/carrito')
def carrito():
    carrito = session.get('carrito', [])
    subtotal = sum(item['precio'] * item['cantidad'] for item in carrito)
    envio = 150 if subtotal < 1000 else 0
    total = subtotal + envio
    return render_template('carrito.html', carrito=carrito, subtotal=subtotal, envio=envio, total=total)

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

    return redirect(url_for('carrito'))

@app.route('/vaciar_carrito')
def vaciar_carrito():
    session['carrito'] = []
    return redirect(url_for('carrito'))

@app.route('/eliminar_carrito/<int:id>')
def eliminar_carrito(id):
    carrito = session.get('carrito', [])
    carrito = [item for item in carrito if item['id'] != id]
    session['carrito'] = carrito
    return redirect(url_for('carrito'))

# ==============================
# RUN SERVER
# ==============================
if __name__ == "__main__":
    app.run(debug=True)
