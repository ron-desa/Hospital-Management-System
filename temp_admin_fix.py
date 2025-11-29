from app import create_app
from models.models import db, User

app = create_app()  # Call the factory function

with app.app_context():
    admin = User.query.filter_by(email="raunakmukho@gmail.com").first()
    if admin:
        admin.is_admin = True
        db.session.commit()
        print("✅ Admin rights set for raunakmukho@gmail.com")
    else:
        print("❌ User not found")
