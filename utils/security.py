from functools import wraps
from flask import session, redirect, url_for, flash, current_app, abort
from flask_login import current_user, login_required
import uuid
import os
from werkzeug.utils import secure_filename
from datetime import datetime


def admin_required(f):
    """Decorator to check if user is an admin"""

    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.role == 'admin':
            flash('Admin privileges required to access this page', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)

    return decorated_function


def allowed_file(filename):
    """Check if the file extension is allowed"""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def save_file(file, folder='uploads'):
    """Save a file with secure filename and return the path"""
    if not file or file.filename == '':
        return None

    # Additional security checks
    if file.content_length and file.content_length > current_app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024):
        raise ValueError("File size exceeds maximum allowed size")

    # Check file extension
    if not allowed_file(file.filename):
        allowed_exts = ', '.join(current_app.config.get('ALLOWED_EXTENSIONS', {'jpg', 'jpeg', 'png', 'pdf'}))
        raise ValueError(f"File type not allowed. Allowed types: {allowed_exts}")

    # Read first few bytes to check for malicious content
    file.seek(0)
    file_header = file.read(512)
    file.seek(0)  # Reset file pointer
    
    # Basic check for script content in uploads
    dangerous_patterns = [b'<script', b'javascript:', b'<?php', b'<%', b'<html']
    for pattern in dangerous_patterns:
        if pattern in file_header.lower():
            raise ValueError("File contains potentially dangerous content")

    # Create secure filename with unique identifier
    filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")

    # Create date-based subfolder for better organization
    today = datetime.now().strftime('%Y%m%d')
    subfolder = os.path.join(current_app.config['UPLOAD_FOLDER'], folder, today)
    os.makedirs(subfolder, exist_ok=True)

    filepath = os.path.join(subfolder, filename)
    file.save(filepath)

    # Return relative path from UPLOAD_FOLDER
    return os.path.join(folder, today, filename)


def validate_loan_application(form_data):
    """Validate loan application data and return errors if any"""
    errors = {}

    # Basic validation
    required_fields = ['customer_id', 'loan_type', 'loan_amount', 'interest_rate', 'term_months']
    for field in required_fields:
        if not form_data.get(field):
            errors[field] = f"{field.replace('_', ' ').title()} is required"

    # Numeric validation
    numeric_fields = ['loan_amount', 'interest_rate', 'term_months']
    for field in numeric_fields:
        if form_data.get(field):
            try:
                float(form_data[field])
            except ValueError:
                errors[field] = f"{field.replace('_', ' ').title()} must be a number"

    # Specific validations
    if form_data.get('loan_amount') and float(form_data['loan_amount']) <= 0:
        errors['loan_amount'] = "Loan amount must be greater than zero"

    if form_data.get('interest_rate') and (
            float(form_data['interest_rate']) < 0 or float(form_data['interest_rate']) > 100):
        errors['interest_rate'] = "Interest rate must be between 0 and 100"

    if form_data.get('term_months') and int(float(form_data['term_months'])) <= 0:
        errors['term_months'] = "Loan term must be at least 1 month"

    # Type-specific validation
    if form_data.get('loan_type') == 'gold':
        if not form_data.get('gold_weight'):
            errors['gold_weight'] = "Gold weight is required for gold loans"
        if not form_data.get('gold_purity'):
            errors['gold_purity'] = "Gold purity is required for gold loans"

    elif form_data.get('loan_type') == 'land':
        if not form_data.get('land_details'):
            errors['land_details'] = "Land details are required for land loans"

    return errors

