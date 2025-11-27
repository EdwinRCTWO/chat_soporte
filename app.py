from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from models import db, Usuario, Atencion, Mensaje
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# ===== CONFIGURACIÓN DE LA APP =====
app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu-clave-secreta'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Crear tablas y encargado por defecto
with app.app_context():
    db.create_all()
    if not Usuario.query.filter_by(email='encargado@soporte.com').first():
        encargado = Usuario(
            nombre='Encargado de Soporte',
            email='encargado@soporte.com',
            contrasena=generate_password_hash('admin123'),
            es_encargado=True
        )
        db.session.add(encargado)
        db.session.commit()

# ===== RUTAS DE AUTENTICACIÓN =====

@app.route('/')
def index():
    if 'usuario_id' in session:
        usuario = Usuario.query.get(session['usuario_id'])
        if usuario.es_encargado:
            return redirect(url_for('panel_encargado'))
        else:
            return redirect(url_for('chat_usuario'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        contrasena = request.form['contrasena']
        
        usuario = Usuario.query.filter_by(email=email).first()
        
        if usuario and check_password_hash(usuario.contrasena, contrasena):
            session['usuario_id'] = usuario.id
            session['nombre'] = usuario.nombre
            session['es_encargado'] = usuario.es_encargado

            # Redirigir directo según rol
            if usuario.es_encargado:
                return redirect(url_for('panel_encargado'))
            else:
                return redirect(url_for('chat_usuario'))
        else:
            return render_template('login.html', error='Credenciales incorrectas')
    
    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        contrasena = request.form['contrasena']
        
        if Usuario.query.filter_by(email=email).first():
            return render_template('login.html', error='El email ya existe')
        
        nuevo_usuario = Usuario(
            nombre=nombre,
            email=email,
            contrasena=generate_password_hash(contrasena),
            es_encargado=False
        )
        
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        return redirect(url_for('login'))
    
    return render_template('registro.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ===== CHAT USUARIO =====

@app.route('/chat')
def chat_usuario():
    if 'usuario_id' not in session or session.get('es_encargado'):
        return redirect(url_for('login'))
    
    # Buscar atención activa (pero NO crearla aquí)
    atencion = Atencion.query.filter_by(
        usuario_id=session['usuario_id'],
        estado='abierta'
    ).first()
    
    mensajes = []
    if atencion:
        mensajes = Mensaje.query.filter_by(atencion_id=atencion.id).order_by(Mensaje.fecha).all()
    
    return render_template(
        'chat_usuario.html',
        atencion=atencion,
        mensajes=mensajes
    )

# ===== PANEL ENCARGADO =====

@app.route('/panel-encargado')
def panel_encargado():
    if 'usuario_id' not in session or not session.get('es_encargado'):
        return redirect(url_for('login'))
    
    atenciones_abiertas = Atencion.query.filter_by(estado='abierta').all()
    
    return render_template('chat_encargado.html', 
                         atenciones=atenciones_abiertas)

@app.route('/chat-atencion/<int:atencion_id>')
def ver_atencion(atencion_id):
    if 'usuario_id' not in session or not session.get('es_encargado'):
        return redirect(url_for('login'))
    
    atencion = Atencion.query.get_or_404(atencion_id)
    mensajes = Mensaje.query.filter_by(atencion_id=atencion_id).order_by(Mensaje.fecha).all()
    
    return render_template('chat_encargado.html', 
                         atencion_actual=atencion,
                         mensajes=mensajes,
                         atenciones=Atencion.query.filter_by(estado='abierta').all())

# ===== API PARA MENSAJES =====

@app.route('/api/enviar-mensaje', methods=['POST'])
def enviar_mensaje():
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401

    data = request.get_json(silent=True) or {}
    atencion_id = data.get('atencion_id')
    texto = (data.get('mensaje') or '').strip()

    if not texto:
        return jsonify({'error': 'Mensaje vacío'}), 400

    # Si no hay atención, crearla aquí
    atencion = None
    if not atencion_id:
        atencion = Atencion.query.filter_by(
            usuario_id=session['usuario_id'],
            estado='abierta'
        ).first()
        if not atencion:
            encargado = Usuario.query.filter_by(es_encargado=True).first()
            atencion = Atencion(
                usuario_id=session['usuario_id'],
                encargado_id=encargado.id,
                estado='abierta'
            )
            db.session.add(atencion)
            db.session.commit()
        atencion_id = atencion.id

    nuevo_mensaje = Mensaje(
        atencion_id=atencion_id,
        usuario_id=session['usuario_id'],
        mensaje=texto,
        es_encargado=session.get('es_encargado', False)
    )
    db.session.add(nuevo_mensaje)
    db.session.commit()

    return jsonify({
        'id': nuevo_mensaje.id,
        'mensaje': nuevo_mensaje.mensaje,
        'fecha': nuevo_mensaje.fecha.strftime('%H:%M'),
        'es_encargado': nuevo_mensaje.es_encargado,
        'atencion_id': nuevo_mensaje.atencion_id  # 🔑 ahora siempre se devuelve
    })

@app.route('/api/obtener-mensajes/<int:atencion_id>')
def obtener_mensajes(atencion_id):
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    ultimo_id = request.args.get('ultimo_id', 0, type=int)
    
    mensajes = Mensaje.query.filter(
        Mensaje.atencion_id == atencion_id,
        Mensaje.id > ultimo_id
    ).order_by(Mensaje.id.asc()).all()
    
    return jsonify([{
        'id': m.id,
        'mensaje': m.mensaje,
        'fecha': m.fecha.strftime('%H:%M'),
        'es_encargado': m.es_encargado
    } for m in mensajes])

@app.route('/api/cerrar-atencion/<int:atencion_id>', methods=['POST'])
def cerrar_atencion(atencion_id):
    if 'usuario_id' not in session or not session.get('es_encargado'):
        return jsonify({'error': 'No autorizado'}), 401
    
    atencion = Atencion.query.get_or_404(atencion_id)
    atencion.estado = 'cerrada'
    db.session.commit()
    
    return jsonify({'status': 'ok'})

# ===== HISTORIAL =====

@app.route('/historial')
def historial():
    if 'usuario_id' not in session or not session.get('es_encargado'):
        return redirect(url_for('login'))

    filtro_nombre = request.args.get('nombre', '').strip()
    filtro_estado = request.args.get('estado', '').strip()

    query = Atencion.query

    if filtro_nombre:
        # JOIN explícito para evitar AmbiguousForeignKeysError
        query = query.join(Usuario, Atencion.usuario_id == Usuario.id)\
                     .filter(Usuario.nombre.ilike(f"%{filtro_nombre}%"))
    if filtro_estado:
        query = query.filter(Atencion.estado == filtro_estado)

    atenciones = query.order_by(Atencion.fecha_registro.desc()).all()

    return render_template(
        'historial.html',
        atenciones=atenciones,
        filtro_nombre=filtro_nombre,
        filtro_estado=filtro_estado
    )

# ===== MAIN =====
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
