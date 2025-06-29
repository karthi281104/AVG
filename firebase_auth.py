import firebase_admin
from firebase_admin import credentials, auth
from functools import wraps
from flask import request, jsonify, session, redirect, url_for
import json
import os

# Initialize Firebase Admin SDK
try:
    cred_path = os.path.join(os.path.dirname(__file__), 'service-account.json')

    if os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        FIREBASE_ENABLED = True
        print("Firebase Admin SDK initialized successfully")
    else:
        print("Warning: service-account.json not found.")
        FIREBASE_ENABLED = False
except Exception as e:
    print(f"Error initializing Firebase Admin SDK: {e}")
    FIREBASE_ENABLED = False


def verify_firebase_token(id_token):
    """Verify the Firebase ID token and return user info"""
    try:
        if not FIREBASE_ENABLED:
            # Return dummy verification for development
            return {"uid": "dev_user", "email": "dev@example.com"}

        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        print(f"Error verifying token: {e}")
        return None


def firebase_auth_required(f):
    """Decorator to protect routes with Firebase Authentication"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # For development without Firebase Admin SDK, always allow access
        if not FIREBASE_ENABLED:
            request.user = {"uid": "dev_user", "email": "dev@example.com"}
            return f(*args, **kwargs)

        # Check for ID token
        id_token = None

        # Check Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            id_token = auth_header.split('Bearer ')[1]

        # Check session
        if not id_token and 'firebase_token' in session:
            id_token = session['firebase_token']

        # Check cookies
        if not id_token and request.cookies.get('firebase_token'):
            id_token = request.cookies.get('firebase_token')

        if not id_token:
            return jsonify({'error': 'Unauthorized access'}), 401

        # Verify the token
        try:
            decoded_token = auth.verify_id_token(id_token)
            request.user = decoded_token
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'error': 'Invalid authentication token', 'details': str(e)}), 401

    return decorated_function


def create_firebase_user(email, password):
    """Create a new user in Firebase Authentication"""
    try:
        if not FIREBASE_ENABLED:
            # Return dummy user for development
            return {"uid": f"dev_{email.split('@')[0]}", "email": email}

        user = auth.create_user(
            email=email,
            password=password
        )
        return user
    except Exception as e:
        print(f"Error creating user: {e}")
        return None