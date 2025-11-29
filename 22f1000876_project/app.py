from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from models.models import db, User, ParkingLot, ParkingSpot, Reservation  # ✅ Use this only
from controllers.routes import routes
from werkzeug.security import generate_password_hash

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking_app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'routes.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    app.register_blueprint(routes)

    with app.app_context():
        db.create_all()

        # ✅ Create super admin if not exists
        super_admin_email = 'raunakmukho@gmail.com'
        if not User.query.filter_by(email=super_admin_email).first():
            super_admin = User(
                email=super_admin_email,
                name='Super Admin',
                password=generate_password_hash('admin123'),  # default password
                is_admin=True
            )
            db.session.add(super_admin)
            db.session.commit()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
