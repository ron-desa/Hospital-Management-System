from app import create_app
from models.models import db, User

app = create_app()

with app.app_context():
    super_admin = User.query.filter_by(email="raunakmukho@gmail.com").first()
    if super_admin:
        print(f"✅ Super Admin exists: {super_admin.name}, is_admin={super_admin.is_admin}")
    else:
        print("❌ Super admin does NOT exist.")
