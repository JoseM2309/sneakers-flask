from flask import Flask, render_template, request, session, redirect, url_for, jsonify, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2

app = Flask(__name__)
app.secret_key = "sneakersmx_secret_key"

# ==============================
# FLASK LOGIN CONFIG
# ==============================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ==============================
# CONEXIÓN A BD (Render)
# ==============================
def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname="sneakers_db_g0p6",
            user="sneakers_db_g0p6_user",
            password="upV4O9iC3ATKiIWKPpV657s9Qg1nlrZL",
            host="dpg-d4fbdtodl3ps73cr042g-a.oregon-postgres.render.com",
            port=5432,
            sslmode="require"
        )
        return conn
    except Exception as e:
        print("Error conectando a la DB:", e)
        return None


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
# CONSULTAS
# ==============================
def obtener_usuario_por_email(email):
    conn = get_db_connection()
    if not conn:
        return None
    cur = conn.cursor()
    cur.execute("SELECT id, nombre, email, password_hash FROM usuarios WHERE email=%s", (email,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return User(id=row[0], nombre=row[1], email=row[2], password_hash=row[3])
    return None


def obtener_usuario_por_id(user_id):
    conn = get_db_connection()
    if not conn:
        return None
    cur = conn.cursor()
    cur.execute("SELECT id, nombre, email, password_hash FROM usuarios WHERE id=%s", (user_id,))
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
# REGISTRO (SIN CAPTCHA)
# ==============================
@app.route('/registro', methods=['GET', 'POST'])
def registro():

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')

        if not nombre or not email or not password:
            flash("Completa todos los campos.", "error")
            return redirect(url_for('registro'))

        password_hash = generate_password_hash(password)

        conn = get_db_connection()
        if not conn:
            flash("Error al conectar con la base de datos.", "error")
            return redirect(url_for('registro'))

        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO usuarios (nombre, email, password_hash) VALUES (%s, %s, %s)",
                (nombre, email, password_hash)
            )
            conn.commit()
            flash("Registro exitoso.", "success")

        except psycopg2.IntegrityError:
            conn.rollback()
            flash("El correo ya existe.", "error")

        except Exception as e:
            conn.rollback()
            flash("Error al registrar usuario.", "error")
            print(e)

        finally:
            cur.close()
            conn.close()

        return redirect(url_for('login'))

    return render_template("registro.html")


# ==============================
# LOGIN
# ==============================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')

        usuario = obtener_usuario_por_email(email)
        if usuario and check_password_hash(usuario.password_hash, password):
            login_user(usuario)
            flash(f"Bienvenido {usuario.nombre}!", "success")
            return redirect(url_for('index'))
        else:
            flash("Correo o contraseña incorrectos.", "error")
            return redirect(url_for('login'))

    return render_template("login.html")


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
    if not conn:
        flash("Error de conexión a la BD", "error")
        return redirect(url_for("index"))

    cur = conn.cursor()
    try:
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
                {"id": p[0], "nombre": p[1], "descripcion": p[2],
                 "precio": p[3], "imagen": p[4]}
                for p in productos
            ]

            if lista:
                productos_por_marca.append({
                    "marca": marca_nombre,
                    "productos": lista
                })

        return render_template("productos.html", productos_por_marca=productos_por_marca)

    except Exception as e:
        print("Error productos:", e)
        flash("Error al cargar productos.", "error")
        return redirect(url_for("index"))

    finally:
        cur.close()
        conn.close()

# ==============================
# conocenos
# ==============================


@app.route("/conocenos")
def conocenos():
    return render_template("conocenos.html")


# ==============================
# CARRITO
# ==============================
@app.route('/agregar_carrito/<int:id>')
def agregar_carrito(id):
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Error DB"}), 500

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
                "id": fila[0],
                "nombre": fila[1],
                "precio": float(fila[2]),
                "imagen": fila[3],
                "cantidad": 1
            })

        session['carrito'] = carrito

    return jsonify({"mensaje": "agregado"})


@app.route('/carrito')
def carrito():
    carrito = session.get('carrito', [])
    subtotal = sum(item['precio'] * item['cantidad'] for item in carrito)
    envio = 150 if subtotal < 1000 else 0
    total = subtotal + envio

    return render_template(
        'carrito.html',
        carrito=carrito,
        subtotal=subtotal,
        envio=envio,
        total=total
    )


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
# PAGO SIMPLE (SIN CAPTCHA)
# ==============================
@app.post("/pago_completado")
def pago_completado():
    data = request.get_json()
    print("PAGO RECIBIDO:", data)
    session["carrito"] = []
    return jsonify({"status": "ok"})


# ==============================
# RUN
# ==============================
if __name__ == '__main__':
    app.run(debug=True)
