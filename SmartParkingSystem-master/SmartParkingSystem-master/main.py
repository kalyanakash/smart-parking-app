from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime, timedelta
from math import ceil

# Firebase JSON key file path
firebase_key_path = r"D:\SmartParkingSystem-master\smartparkingsystem-7d591-firebase-adminsdk-fbsvc-daf250beb0.json"

# Initialize Firebase app (only if not already initialized)
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_key_path)
    firebase_admin.initialize_app(cred, {'databaseURL': 'https://smartparkingsystem-7d591-default-rtdb.firebaseio.com/'})

app = Flask(__name__)

# Secret key for session management
app.secret_key = 'canada$God7972#'

# Define Firebase reference
ref = db.reference('smart-parking')

# Define total parking slots
TOTAL_SLOTS = 10  # Adjust based on your parking lot size

# Admin Credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_loggedin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid admin credentials!", "danger")

    return render_template('admin_login.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin_loggedin' not in session:
        return redirect(url_for('admin_login'))

    # Fetch reservations from Firebase
    reservations = ref.child("reservations").get() or {}

    # Debug: Print reservations from Firebase
    print("Reservations from Firebase:", reservations)

    booked_slots = []
    
    for res_id, reservation in reservations.items():
        if reservation.get("status") == "booked":
            booked_slots.append({
                "slot": reservation.get("slot", "N/A"),
                "username": reservation.get("username", "Unknown"),  # Directly from reservation
                "carNumber": reservation.get("carNumber", "N/A"),
                "parkingTime": reservation.get("parkingTime", "N/A"),
                "parkingDate": reservation.get("parkingDate", "N/A"),
                "hours": reservation.get("hours", "N/A"),
                "reservation_id": res_id
            })

    # Fetch users from Firebase
    users_ref = ref.child("users").get() or {}

    # Debug: Print users from Firebase
    print("Users from Firebase:", users_ref)

    return render_template('admin_dashboard.html', booked_slots=booked_slots, users=users_ref)





@app.route('/admin/delete_user/<user_id>', methods=['POST'])
def delete_user(user_id):
    if 'admin_loggedin' not in session:
        return redirect(url_for('admin_login'))

    ref.child(f"users/{user_id}").delete()
    flash("User deleted successfully.", "success")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/delete_reservation/<reservation_id>', methods=['POST'])
def delete_reservation(reservation_id):
    if 'admin_loggedin' not in session:
        return redirect(url_for('admin_login'))

    ref.child(f"reservations/{reservation_id}").delete()
    flash("Reservation deleted successfully.", "success")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_loggedin', None)
    flash("Admin logged out successfully.", "info")
    return redirect(url_for('admin_login'))


@app.route('/')
def index():
    return render_template('index.html')
@app.route('/dashboard')
def dashboard():
    if 'loggedin' not in session:
        return redirect(url_for('login'))  # Redirect to login if not authenticated

    # Fetch reservations from Firebase
    parking_data = ref.child("reservations").get() or {}

    booked_slots = []
    empty_slots = list(range(1, TOTAL_SLOTS + 1))  # All slots start as available

    for value in parking_data.values():
        if value.get("status") == "booked":
            slot = value.get("slot")
            if slot and slot in empty_slots:
                booked_slots.append(slot)
                empty_slots.remove(slot)

    # Dynamic Pricing: If 5 or more slots are booked, increase rate
    if len(booked_slots) >= 5:
        rate = 30  # Increased rate per hour
    else:
        rate = 20  # Default rate per hour

    # Get last updated timestamp
    lastupdated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return render_template(
        'dashboard.html',
        username=session['username'],
        booked_slots=booked_slots,
        empty_slots=empty_slots,
        lastupdated=lastupdated,
        rate=rate  # Dynamic Rate applied here
    )




@app.route('/login', methods=['GET', 'POST'])
def login():
    success_msg = ''
    error_msg = ''

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        users_data = ref.child("users").get() or {}

        account = next(
            (user for user_id, user in users_data.items() if user.get("username") == username),
            None
        )

        if account and account.get("password") == password:
            session['loggedin'] = True
            session['username'] = username
            session['user_id'] = next(user_id for user_id, user in users_data.items() if user.get("username") == username)

            # Update Firebase to mark user as logged in
            ref.child(f"users/{session['user_id']}").update({"logged_in": True})

            flash("Login successful!", "success")
            return redirect(url_for('dashboard'))  # Redirecting to dashboard
        else:
            error_msg = 'Incorrect username or password!'

    return render_template('login.html', success_msg=success_msg, error_msg=error_msg)

@app.route('/register', methods=['GET', 'POST'])
def register():
    success_msg = ''
    error_msg = ''

    if request.method == 'POST':
        username = request.form.get('username')
        phone = request.form.get('phone')  # Get phone number
        password = request.form.get('password')

        users_ref = ref.child("users")
        users_data = users_ref.get() or {}

        # Check if username already exists
        if any(user.get("username") == username for user in users_data.values()):
            error_msg = 'Username already exists!'
        else:
            # Save user details including phone number
            users_ref.push({"username": username, "phone": phone, "password": password})
            success_msg = 'Signed up successfully! Please log in.'
            return render_template('login.html', success_msg=success_msg, error_msg=error_msg)

    return render_template('login.html', success_msg=success_msg, error_msg=error_msg)

@app.route('/reservation', methods=['GET'])
def reservation():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    BASE_HOURLY_RATE = 20

    # Fetch available slots
    reservations = ref.child("reservations").get() or {}
    booked_slots = {value["slot"] for value in reservations.values() if value.get("status") == "booked"}
    empty_slots = [slot for slot in range(1, TOTAL_SLOTS + 1) if slot not in booked_slots]

    # Count booked slots and calculate dynamic price
    booked_slots_count = len(booked_slots)
    if booked_slots_count >= 5:
        extra_slots = booked_slots_count - 5
        price_multiplier = 1 + (extra_slots * 0.2)   # 20% increase per extra slot after 5
        hourly_rate = ceil(BASE_HOURLY_RATE * price_multiplier)
    else:
        hourly_rate = BASE_HOURLY_RATE

    return render_template(
        'reservation.html',
        username=session['username'],
        empty_slots=empty_slots,
        reservations=[value for value in reservations.values() if value.get("status") == "booked"],
        hourly_rate=hourly_rate   # 👈 passing dynamic price to template
    )


@app.route('/submit_reservation', methods=['POST'])
def submit_reservation():
    if 'loggedin' not in session:
        flash("Please log in to make a reservation.", "danger")
        return redirect(url_for('login'))

    username = session['username']
    car_mark = request.form.get('carMake')
    car_number = request.form.get('carNumber')
    slot = request.form.get('slot')
    parking_time = request.form.get('parkingTime')
    parking_date = request.form.get('parkingDate')
    hours = request.form.get('hours')

    print(f"DEBUG: Received form data - carMark: {car_mark}, carNumber: {car_number}, Slot: {slot}, Time: {parking_time}, Date: {parking_date}, Hours: {hours}")

    # Validate input fields
    if not car_mark or not car_number or not slot or not parking_time or not parking_date or not hours:
        flash("Error: All fields are required!", "danger")
        return redirect(url_for('reservation'))

    try:
        slot = int(slot)
        hours = int(hours)
    except ValueError:
        flash("Error: Invalid input values!", "danger")
        return redirect(url_for('reservation'))

    print(f"DEBUG: Selected slot: {slot}, Parking Time: {parking_time}, Parking Date: {parking_date}, Hours: {hours}")

    # Fetch existing reservations
    reservations_ref = ref.child("reservations")
    reservations = reservations_ref.get() or {}

    # Check if slot is already booked
    for value in reservations.values():
        if value.get("slot") == slot and value.get("status") == "booked":
            print(f"❌ DEBUG: Slot {slot} is already booked!")
            flash("Error: Slot already booked!", "danger")
            return redirect(url_for('reservation'))

    try:
        # Store reservation
        new_reservation_ref = reservations_ref.push()
        new_reservation_ref.set({
            "username": username,
            "carMark": car_mark,
            "carNumber": car_number,
            "slot": slot,
            "parkingTime": parking_time,
            "parkingDate": parking_date,
            "hours": hours,
            "status": "booked",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        print(f"✅ DEBUG: Reservation successful! Slot {slot} booked for {username}")
        flash("Reservation successful!", "success")
        return redirect(url_for('reservation'))

    except Exception as e:
        print(f"❌ ERROR: Failed to save reservation: {e}")
        flash("Error saving reservation. Please try again.", "danger")
        return redirect(url_for('reservation'))
@app.route('/payment')
def payment():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    username = session['username']
    slot = request.args.get("slot")  # Get the selected slot from URL parameter
    BASE_HOURLY_RATE = 20  # Base rate per hour

    if not slot:
        flash("Invalid slot selection!", "danger")
        return redirect(url_for('dashboard'))

    try:
        slot = int(slot)  # Convert slot to integer
    except ValueError:
        flash("Invalid slot number!", "danger")
        return redirect(url_for('dashboard'))

    reservations = ref.child("reservations").get() or {}

    # Find the specific reservation for the selected slot
    user_reservation = None
    booked_slots_count = 0

    for key, value in reservations.items():
        if value.get("status") == "booked":
            booked_slots_count += 1  # Count booked slots
        if (
            value.get("username") == username and
            value.get("slot") == slot and
            value.get("status") == "booked"
        ):
            user_reservation = value

    if not user_reservation:
        flash("No active reservation found for this slot!", "danger")
        return redirect(url_for('dashboard'))

    start_time_str = user_reservation.get("timestamp")
    booked_hours = user_reservation.get("hours")  # Get hours booked from reservation data

    # Validate booked hours
    try:
        booked_hours = int(booked_hours)  # Convert to integer
    except (ValueError, TypeError):
        booked_hours = 1  # Default to 1 hour if invalid

    # Dynamic pricing logic
    if booked_slots_count > 5:
        extra_slots = booked_slots_count - 5  # Number of extra booked slots beyond 5
        price_multiplier = 1 + (extra_slots * 0.2)  # Increase price by 20% per extra slot
        hourly_rate = ceil(BASE_HOURLY_RATE * price_multiplier)  # Round up the price
    else:
        hourly_rate = BASE_HOURLY_RATE

    total_price = booked_hours * hourly_rate  # Calculate total cost

    return render_template(
        'payment.html',
        slot=slot,
        start_time=start_time_str,
        hours_parked=booked_hours,
        total_price=total_price,
        hourly_rate=hourly_rate  # Send updated rate to the template
    )




@app.route('/process_payment', methods=['POST'])
def process_payment():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    username = session['username']
    slot = request.form.get('slot')
    total_price = request.form.get('total_price')

    if not slot or not total_price:
        flash("Invalid payment details!", "danger")
        return redirect(url_for('dashboard'))

    try:
        slot = int(slot)
    except ValueError:
        flash("Invalid slot number!", "danger")
        return redirect(url_for('dashboard'))

    reservations = ref.child("reservations").get() or {}

    # Find the user's reservation
    for key, value in reservations.items():
        if (
            value.get("username") == username and
            value.get("slot") == slot and
            value.get("status") == "booked"
        ):
            # Remove the reservation (or update status)
            ref.child(f"reservations/{key}").delete()

            # Mark the slot as available again
            ref.child(f"slots/{slot}").set({"status": "available"})

            flash(f"Payment successful for Slot {slot}. Amount Paid: ₹{total_price}", "success")
            return redirect(url_for('dashboard'))

    flash("No active reservation found!", "danger")
    return redirect(url_for('dashboard'))



@app.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id:
        ref.child(f"users/{user_id}").update({"logged_in": False})  # Update Firebase

    session.pop('loggedin', None)
    session.pop('username', None)
    session.pop('user_id', None)

    flash("Logged out successfully.", "info")
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)