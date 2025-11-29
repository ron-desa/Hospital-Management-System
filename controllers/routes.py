# controllers/routes.py
from flask import Blueprint, render_template, redirect, url_for, request, session, flash
from models.models import get_db_connection
from werkzeug.security import check_password_hash

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    # You can redirect based on role if logged in
    if "user_id" in session and "role" in session:
        role = session["role"]
        if role == "admin":
            return redirect(url_for("main.admin_dashboard"))
        elif role == "doctor":
            return redirect(url_for("main.doctor_dashboard"))
        elif role == "patient":
            return redirect(url_for("main.patient_dashboard"))
    return render_template("login.html")


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


@main_bp.route("/admin/dashboard")
def admin_dashboard():
    # TODO: query counts of doctors, patients, appointments
    return render_template("dashboard_admin.html")


@main_bp.route("/doctor/dashboard")
def doctor_dashboard():
    # TODO: show upcoming appointments for doctor, list of patients
    return render_template("dashboard_doctor.html")


@main_bp.route("/patient/dashboard")
def patient_dashboard():
    # TODO: show departments, availability, upcoming appointments, history
    return render_template("dashboard_patient.html")
