from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from . import db  # from models/__init__.py

# Association table for many-to-many: Admin ↔ ParkingLots
admin_lot = db.Table(
    'admin_lot',
    db.Column('admin_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('lot_id', db.Integer, db.ForeignKey('parking_lot.id'), primary_key=True)
)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    # Lots managed by this admin (if admin)
    managed_lots = db.relationship(
        'ParkingLot',
        secondary=admin_lot,
        back_populates='admins'
    )

class ParkingLot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    total_spots = db.Column(db.Integer, nullable=False)

    # Relationship to spots
    spots = db.relationship('ParkingSpot', backref='lot', lazy=True)

    # Admins managing this lot
    admins = db.relationship(
        'User',
        secondary=admin_lot,
        back_populates='managed_lots'
    )

class ParkingSpot(db.Model):
    __tablename__ = 'parking_spot'

    id = db.Column(db.Integer, primary_key=True)
    slot_number = db.Column(db.String(50), nullable=False)
    is_booked = db.Column(db.Boolean, default=False)
    status = db.Column(db.Integer, default=0)
    timestamp = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    booked_by = db.Column(db.String(100))
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lot.id'), nullable=False)
    

    __table_args__ = (
        db.UniqueConstraint('slot_number', 'lot_id', name='uq_slot_per_lot'),
    )

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spot.id'), nullable=False)
    booked_at = db.Column(db.DateTime, default=datetime.utcnow)
    released_at = db.Column(db.DateTime, nullable=True)
    user = db.relationship('User', backref='reservations')

