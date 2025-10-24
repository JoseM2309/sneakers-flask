from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import psycopg2

app = Flask(__name__)
app.secret_key = "sneakersmx_secret_key"

# --- Conexión a PostgreSQL ---
conn = psycopg2.connect(
    dbname="sneakers",
    user="alfredo",
    password="12345",
    host="localhost",
    port="5433"
)
cursor = conn.cursor()

# --- Página principal ---
@app.route('/')
def index():
    return render_template('index.html')

# --- Página Conócenos ---
@app.route('/conocenos')
def conocenos():
    return render_template('conocenos.html')

# --- Página Productos ---
@app.route('/productos')
def productos():
    # Seleccionamos id, nombre, descripcion, precio e imagen
    cursor.execute("SELECT id, nombre, descripcion, precio, imagen FROM productos;")
    filas = cursor.fetchall()

    # Convertimos a lista de diccionarios
    productos = [
        {
            "id": row[0],
            "nombre": row[1],
            "descripcion": row[2],
            "precio": row[3],
            "imagen": row[4]
        }
        for row in filas
    ]

    return render_template('productos.html', productos=productos)

# --- Agregar al carrito por id (opcional) ---
@app.route('/agregar_carrito/<int:id>')
def agregar_carrito(id):
    # Buscamos el producto por id
    cursor.execute("SELECT id, nombre, precio FROM productos WHERE id=%s;", (id,))
    fila = cursor.fetchone()
    if fila:
        carrito = session.get('carrito', [])
        # Verificamos si ya existe el producto
        encontrado = False
        for item in carrito:
            if item['id'] == fila[0]:
                item['cantidad'] += 1
                encontrado = True
                break
        if not encontrado:
            carrito.append({'id': fila[0], 'nombre': fila[1], 'precio': float(fila[2]), 'cantidad': 1})
        session['carrito'] = carrito
    return redirect(url_for('carrito'))

# --- Guardar carrito desde el flotante ---
@app.route('/guardar_carrito', methods=['POST'])
def guardar_carrito():
    datos = request.get_json()
    if datos:
        session_carrito = session.get('carrito', [])
        for item in datos:
            # Verificar si ya existe en session
            existente = next((p for p in session_carrito if p['nombre'] == item['nombre']), None)
            if existente:
                existente['cantidad'] += item['cantidad']
            else:
                session_carrito.append(item)
        session['carrito'] = session_carrito
    return jsonify({"status": "ok"})

# --- Página de contacto ---
@app.route('/contacto', methods=['GET', 'POST'])
def contacto():
    if request.method == 'POST':
        nombre = request.form['nombre']
        correo = request.form['correo']
        mensaje = request.form['mensaje']
        print(f"Nuevo mensaje de {nombre} ({correo}): {mensaje}")
        return render_template('contacto.html', mensaje_enviado=True)
    return render_template('contacto.html')

# --- Página del carrito ---
@app.route('/carrito')
def carrito():
    carrito = session.get('carrito', [])
    total = sum(item['precio'] * item['cantidad'] for item in carrito)
    return render_template('carrito.html', carrito=carrito, total=total)

# --- Vaciar carrito ---
@app.route('/vaciar_carrito')
def vaciar_carrito():
    session['carrito'] = []
    return redirect(url_for('carrito'))

# --- Eliminar un producto del carrito ---
@app.route('/eliminar_carrito/<int:id>')
def eliminar_carrito(id):
    carrito = session.get('carrito', [])
    carrito = [item for item in carrito if item['id'] != id]
    session['carrito'] = carrito
    return redirect(url_for('carrito'))

# --- Ejecutar servidor ---
if __name__ == '__main__':
    app.run(debug=True)


