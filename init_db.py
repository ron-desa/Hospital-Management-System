# init_db.py
from models.models import create_tables, seed_admin_and_defaults

if __name__ == "__main__":
    print("Creating tables...")
    create_tables()
    print("Seeding admin and default data...")
    seed_admin_and_defaults()
    print("Done. Database initialized.")
