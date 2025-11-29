# models/models.py
import os
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)

DB_PATH = os.path.join(INSTANCE_DIR, "hospital.db")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    conn = get_db_connection()
    cur = conn.cursor()

    # Users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            role TEXT NOT NULL CHECK(role IN ('admin', 'doctor', 'patient')),
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
    """)

    # Departments table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL
        );
    """)

    # Doctors table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            department_id INTEGER,
            bio TEXT,
            room_no TEXT,
            is_blacklisted INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(department_id) REFERENCES departments(id)
        );
    """)

    # Patients table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            age INTEGER,
            gender TEXT,
            address TEXT,
            emergency_contact TEXT,
            is_blacklisted INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
    """)

    # Doctor availability
    cur.execute("""
        CREATE TABLE IF NOT EXISTS doctor_availability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id INTEGER NOT NULL,
            date TEXT NOT NULL,       -- YYYY-MM-DD
            start_time TEXT NOT NULL, -- HH:MM
            end_time TEXT NOT NULL,   -- HH:MM
            max_appointments INTEGER DEFAULT 10,
            is_available INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(doctor_id) REFERENCES doctors(id)
        );
    """)

    # Appointments
    cur.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            date TEXT NOT NULL, -- YYYY-MM-DD
            time TEXT NOT NULL, -- HH:MM
            status TEXT NOT NULL CHECK(status IN ('Booked', 'Completed', 'Cancelled')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(patient_id) REFERENCES patients(id),
            FOREIGN KEY(doctor_id) REFERENCES doctors(id),
            UNIQUE(doctor_id, date, time) -- prevent double booking
        );
    """)

    # Treatments
    cur.execute("""
        CREATE TABLE IF NOT EXISTS treatments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id INTEGER NOT NULL,
            diagnosis TEXT,
            prescription TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(appointment_id) REFERENCES appointments(id)
        );
    """)

    conn.commit()
    conn.close()


def seed_admin_and_defaults():
    """
    Create default admin + some departments if they don't already exist.
    Admin must be pre-existing and programmatically created.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # Check if an admin already exists
    cur.execute("SELECT id FROM users WHERE role='admin';")
    admin = cur.fetchone()

    if not admin:
        now = datetime.utcnow().isoformat()
        admin_username = "admin"
        admin_password = "admin123"  # You can change this later in UI or code
        password_hash = generate_password_hash(admin_password)

        cur.execute("""
            INSERT INTO users (username, password_hash, full_name, email, phone, role, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, 'admin', 1, ?);
        """, (
            admin_username,
            password_hash,
            "Default Admin",
            "admin@hospital.com",
            "0000000000",
            now
        ))

        print("Default admin created: username='admin', password='admin123'")

    # Seed a few default departments
    now = datetime.utcnow().isoformat()
    default_depts = [
        ("General Medicine", "General physician and common ailments."),
        ("Cardiology", "Heart and cardiovascular system."),
        ("Orthopedics", "Bones, joints, and musculoskeletal system."),
        ("Pediatrics", "Healthcare for infants and children.")
    ]

    for name, desc in default_depts:
        cur.execute("SELECT id FROM departments WHERE name = ?;", (name,))
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO departments (name, description, created_at)
                VALUES (?, ?, ?);
            """, (name, desc, now))

    conn.commit()
    conn.close()
