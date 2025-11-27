from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    contrasena = db.Column(db.String(200))
    es_encargado = db.Column(db.Boolean, default=False)

class Atencion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    encargado_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.String(20), default='abierta')
    
    usuario = db.relationship('Usuario', foreign_keys=[usuario_id])
    encargado = db.relationship('Usuario', foreign_keys=[encargado_id])

class Mensaje(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    atencion_id = db.Column(db.Integer, db.ForeignKey('atencion.id'))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))

    mensaje = db.Column(db.Text, nullable=True)           # texto opcional
    archivo = db.Column(db.String(255), nullable=True)    # nuevo campo para adjunto

    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    es_encargado = db.Column(db.Boolean, default=False)
    
    atencion = db.relationship('Atencion', backref='mensajes')
    usuario = db.relationship('Usuario')
