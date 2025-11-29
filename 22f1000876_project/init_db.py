from app import create_app
from models.models import db

app = create_app()

with app.app_context():
    db.drop_all()
    db.create_all()
    print("✅ Database initialized!")
