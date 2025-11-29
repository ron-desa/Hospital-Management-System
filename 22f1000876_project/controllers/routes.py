from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask import render_template, request, redirect, url_for, session
from models.models import db, User, ParkingLot, ParkingSpot, Reservation


from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from models.models import db, User

routes = Blueprint("routes", __name__)

@routes.route('/')
def index():
    return redirect(url_for('routes.login'))

# ------------------ REGISTER ------------------
@routes.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered. Please login.')
            return redirect(url_for('routes.login'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(name=name, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful. Please login.')
        return redirect(url_for('routes.login'))

    return render_template('register.html')

# ------------------ LOGIN ------------------
@routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        login_type = request.form.get('login_type', 'user')

        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password, password):
            flash('Invalid credentials. Please try again.')
            return redirect(url_for('routes.login'))

        login_user(user)
        session['user_id'] = user.id

        if login_type == 'admin':
            if user.email != 'raunakmukho@gmail.com' and not user.is_admin:
                flash('You are not authorized to log in as admin.')
                return redirect(url_for('routes.login'))
            flash('Admin login successful.')
            return redirect(url_for('routes.admin_dashboard'))

        flash('Login successful.')
        return redirect(url_for('routes.dashboard'))

    return render_template('login.html')



# ----------------super admin-------------
@routes.route('/make-super-admin')
@login_required
def make_super_admin():
    if current_user.email != 'raunakmukho@gmail.com':
        flash('Unauthorized.')
        return redirect(url_for('routes.dashboard'))

    user = User.query.filter_by(email='raunakmukho@gmail.com').first()
    if user:
        user.is_admin = True
        db.session.commit()
        return "Super admin set successfully."
    return "User not found."




# ------------------admin choice-----------------
@routes.route('/admin-choice')
@login_required
def admin_choice():
    return render_template('admin_choice.html')



# ------------------ DASHBOARD ------------------
# @routes.route('/dashboard')
# @login_required
# def dashboard():
#     return f"Welcome {current_user.name}! You are logged in."

# routes.py
# @routes.route('/dashboard')
# def dashboard():
#     if 'user_id' not in session:
#         return redirect('/login')
    
#     conn = sqlite3.connect('parking.db')
#     cursor = conn.cursor()
#     cursor.execute("SELECT * FROM slots")
#     slots = cursor.fetchall()
#     conn.close()

#     return render_template('dashboard_user.html', slots=slots)

@routes.route('/dashboard')
@login_required
def dashboard():
    lots = ParkingLot.query.all()  # Get all lots (with their slots)
    return render_template('dashboard_user.html', lots=lots, user=current_user)



#  -------------------------Book slot--------------------

from datetime import datetime

from flask import session, redirect, url_for, flash
from flask_login import login_required

from datetime import datetime  # put at the top of routes.py

@routes.route('/book/<int:slot_id>')
@login_required
def book_slot(slot_id):
    spot = ParkingSpot.query.get_or_404(slot_id)

    if not spot.is_booked:
        spot.is_booked = True
        spot.status = 1
        spot.booked_by = current_user.email
        spot.user_id = current_user.id
        spot.timestamp = datetime.now()

        db.session.commit()
        flash(f'Slot {spot.slot_number} successfully booked!')
    else:
        flash('Slot is already booked!')

    return redirect(url_for('routes.dashboard'))




# --------------------Cancel Slot------------------------

# @routes.route('/cancel/<int:slot_id>')
# @login_required
# def cancel_slot(slot_id):
#     
#     conn = sqlite3.connect('parking.db')
#     cursor = conn.cursor()

#     # Check if the slot is booked by current user
#     cursor.execute("SELECT user_id FROM slots WHERE id = ?", (slot_id,))
#     result = cursor.fetchone()

#     if result and result[0] == current_user.id:
#         cursor.execute("UPDATE slots SET status = 0, user_id = NULL WHERE id = ?", (slot_id,))
#         conn.commit()
#         flash('Booking canceled successfully!')
#     else:
#         flash('You are not authorized to cancel this slot.')

#     conn.close()
#     return redirect(url_for('routes.dashboard'))

@routes.route('/cancel/<int:slot_id>')
@login_required
def cancel_slot(slot_id):
    spot = ParkingSpot.query.get_or_404(slot_id)

    if spot.is_booked and spot.booked_by == current_user.email:
        spot.is_booked = False
        spot.status = 0
        spot.booked_by = None
        spot.user_id = None
        spot.timestamp = None

        db.session.commit()
        flash('Booking cancelled.')
    else:
        flash('You are not authorized to cancel this booking.')

    return redirect(url_for('routes.dashboard'))


# -----------------My Bookings----------------

@routes.route("/my_bookings")
@login_required
def my_bookings():
    bookings = ParkingSpot.query.filter_by(user_id=current_user.id).all()
    return render_template("my_bookings.html", bookings=bookings)




# 

#  -----------------ADMIN DASHBOARD------------

# @routes.route('/admin/dashboard')
# @login_required
# def admin_dashboard():
#     if not current_user.is_admin:
#         flash('Access denied: Admins only.')
#         return redirect(url_for('routes.dashboard'))

#     users = User.query.all()
#     conn = sqlite3.connect('parking.db')
#     c = conn.cursor()
#     c.execute("SELECT * FROM slots")
#     slots = c.fetchall()
#     conn.close()

#     return render_template('dashboard_admin.html', users=users, slots=slots, super_admin_email='raunakmukho@gmail.com')

@routes.route('/admin/dashboard')
@login_required
def admin_dashboard():
    # ✅ Ensure only authorized admin or super admin can access
    if current_user.email != 'raunakmukho@gmail.com' and not current_user.is_admin:
        flash('Access denied: Admins only.')
        return redirect(url_for('routes.dashboard'))

    is_super_admin = current_user.email == 'raunakmukho@gmail.com'

    users = User.query.all() if is_super_admin else User.query.filter(User.email != 'raunakmukho@gmail.com').all()
    lots = ParkingLot.query.all() if is_super_admin else current_user.managed_lots

    return render_template(
        'dashboard_admin.html',
        users=users,
        lots=lots,
        super_admin_email='raunakmukho@gmail.com',
        is_super_admin=is_super_admin
    )




# ------------------MAKE ADMIN-----------------
@routes.route('/make_admin/<int:user_id>')
@login_required
def make_admin(user_id):
    if not current_user.is_admin:
        flash("Access denied.")
        return redirect(url_for('routes.dashboard'))

    user = User.query.get(user_id)
    if user and user.email != 'raunakmukho@gmail.com':
        user.is_admin = True
        db.session.commit()

    return redirect(url_for('routes.admin_dashboard'))

@routes.route('/revoke_admin/<int:user_id>')
@login_required
def revoke_admin(user_id):
    if not current_user.is_admin:
        flash("Access denied.")
        return redirect(url_for('routes.dashboard'))

    user = User.query.get(user_id)
    if user and user.email != 'raunakmukho@gmail.com':
        user.is_admin = False
        db.session.commit()

    return redirect(url_for('routes.admin_dashboard'))

# --------Lot---------------
from sqlalchemy.orm import joinedload

@routes.route('/admin/lot/<int:lot_id>')
@login_required
def view_lot(lot_id):
    lot = ParkingLot.query.options(
        joinedload(ParkingLot.spots).joinedload(ParkingSpot.lot)
    ).get_or_404(lot_id)

    # Check access
    if current_user.email != 'raunakmukho@gmail.com' and lot not in current_user.managed_lots:
        flash('Access denied: You are not authorized to view this lot.')
        return redirect(url_for('routes.admin_dashboard'))

    # Get booked_by info directly from ParkingSpot.user_id
    spot_user_map = {}
    for spot in lot.spots:
        if spot.user_id:
            user = User.query.get(spot.user_id)
            spot_user_map[spot.id] = f"{user.name} ({user.email})" if user else '-'
        else:
            spot_user_map[spot.id] = '-'

    spots = sorted(lot.spots, key=lambda s: s.slot_number)

    return render_template(
        'view_lot.html',
        lot=lot,
        spots=spots,
        spot_user_map=spot_user_map
    )





# ---------------Add Lot--------------------------
@routes.route('/admin/add_lot', methods=['POST'])
@login_required
def add_lot():
    if not current_user.is_admin:
        flash("Access denied.")
        return redirect(url_for('routes.dashboard'))

    lot_name = request.form.get('lot_name')
    location = request.form.get('location')  # 🔥 get location from form
    slot_count = int(request.form.get('slot_count', 0))

    if not lot_name or slot_count <= 0:
        flash("Invalid input.")
        return redirect(url_for('routes.admin_dashboard'))

    # Create new lot
    lot = ParkingLot(name=lot_name, location=location, total_spots=slot_count)
    db.session.add(lot)
    db.session.commit()

    # Add slots
    for i in range(1, slot_count + 1):
        spot = ParkingSpot(slot_number=i, lot_id=lot.id, is_booked=False)
        db.session.add(spot)
    
    # Assign this lot to current admin
    current_user.managed_lots.append(lot)
    db.session.commit()

    flash(f"Lot '{lot_name}' with {slot_count} slots added.")
    return redirect(url_for('routes.admin_dashboard'))


# ------------------ LOGOUT ------------------
@routes.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.')
    return redirect(url_for('routes.login'))
