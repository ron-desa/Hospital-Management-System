# controllers/routes.py
from flask import Blueprint, render_template, redirect, url_for, request, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from datetime import datetime

from models.models import get_db_connection

main_bp = Blueprint("main", __name__)


# --------- Helpers ---------
def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("main.login"))
        return view_func(*args, **kwargs)
    return wrapped


def role_required(role):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if "user_id" not in session or session.get("role") != role:
                flash("Unauthorized access.", "danger")
                return redirect(url_for("main.login"))
            return view_func(*args, **kwargs)
        return wrapped
    return decorator


# --------- Routes ---------
@main_bp.route("/")
def index():
    if "user_id" in session and "role" in session:
        role = session["role"]
        if role == "admin":
            return redirect(url_for("main.admin_dashboard"))
        elif role == "doctor":
            return redirect(url_for("main.doctor_dashboard"))
        elif role == "patient":
            return redirect(url_for("main.patient_dashboard"))
    return redirect(url_for("main.login"))


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ? AND is_active = 1;", (username,))
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            session["full_name"] = user["full_name"]
            flash("Logged in successfully.", "success")

            if user["role"] == "admin":
                return redirect(url_for("main.admin_dashboard"))
            elif user["role"] == "doctor":
                return redirect(url_for("main.doctor_dashboard"))
            else:
                return redirect(url_for("main.patient_dashboard"))
        else:
            flash("Invalid username or password", "danger")

    return render_template("login.html")


@main_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("main.login"))


@main_bp.route("/register", methods=["GET", "POST"])
def register():
    # Only patient self-registration allowed
    if request.method == "POST":
        full_name = request.form.get("full_name")
        username = request.form.get("username")
        email = request.form.get("email")
        phone = request.form.get("phone")
        age = request.form.get("age") or None
        gender = request.form.get("gender")
        address = request.form.get("address")
        emergency_contact = request.form.get("emergency_contact")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        conn = get_db_connection()
        cur = conn.cursor()

        # Check if username exists
        cur.execute("SELECT id FROM users WHERE username = ?;", (username,))
        if cur.fetchone():
            conn.close()
            flash("Username already taken.", "warning")
            return render_template("register.html")

        now = datetime.utcnow().isoformat()
        password_hash = generate_password_hash(password)

        # Insert into users
        cur.execute("""
            INSERT INTO users (username, password_hash, full_name, email, phone, role, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, 'patient', 1, ?);
        """, (username, password_hash, full_name, email, phone, now))
        user_id = cur.lastrowid

        # Insert into patients
        cur.execute("""
            INSERT INTO patients (user_id, age, gender, address, emergency_contact, is_blacklisted)
            VALUES (?, ?, ?, ?, ?, 0);
        """, (user_id, age, gender, address, emergency_contact))

        conn.commit()
        conn.close()

        flash("Registration successful. You can now log in.", "success")
        return redirect(url_for("main.login"))

    return render_template("register.html")


# --------- Dashboards ---------
@main_bp.route("/admin/dashboard")
@login_required
@role_required("admin")
def admin_dashboard():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS c FROM doctors;")
    total_doctors = cur.fetchone()["c"]

    cur.execute("SELECT COUNT(*) AS c FROM patients;")
    total_patients = cur.fetchone()["c"]

    cur.execute("SELECT COUNT(*) AS c FROM appointments;")
    total_appointments = cur.fetchone()["c"]

    conn.close()

    stats = {
        "total_doctors": total_doctors,
        "total_patients": total_patients,
        "total_appointments": total_appointments
    }

    return render_template("dashboard_admin.html", stats=stats)


@main_bp.route("/doctor/dashboard")
@login_required
@role_required("doctor")
def doctor_dashboard():
    # TODO: show upcoming appointments for this doctor, list of patients
    return render_template("dashboard_doctor.html")


@main_bp.route("/patient/dashboard")
@login_required
@role_required("patient")
def patient_dashboard():
    # fetch departments for listing
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM departments ORDER BY name;")
    departments = cur.fetchall()
    conn.close()

    return render_template("dashboard_patient.html", departments=departments)
