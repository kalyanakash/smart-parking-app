import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime

# Firebase JSON key file path
firebase_key_path = r"C:\Users\hp\Downloads\SmartParkingSystem-master\SmartParkingSystem-master\smart-parking-23ffe-firebase-adminsdk-fbsvc-513aee6fda.json"

# Initialize Firebase if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_key_path)
    firebase_admin.initialize_app(cred, {'databaseURL': 'https://smart-parking-23ffe-default-rtdb.firebaseio.com/'})

# Reference to reservations
reservations_ref = db.reference('smart-parking/reservations')

# Test reservation entry
test_data = {
    "username": "test_user",
    "carMark": "Toyota",
    "carNumber": "ABC123",
    "slot": 5,
    "status": "booked",
    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

# Push data to Firebase
reservations_ref.push(test_data)

print("✅ Test reservation added successfully!")
