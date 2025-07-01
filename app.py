from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, g
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import json

from config import config
from models import db, User, Customer, Loan, Payment, Document, LoanType, LoanStatus
from utils.security import admin_required, save_file, validate_loan_application
from utils.helpers import (calculate_emi, generate_amortization_schedule,
                           calculate_gold_loan, convert_gold_measurement,
                           get_current_gold_rate, format_currency)

# Import Firebase auth functions - with graceful fallback
try:
    from firebase_auth import firebase_auth_required, verify_firebase_token, create_firebase_user, FIREBASE_ENABLED
except Exception as e:
    print(f"Error importing firebase_auth: {e}")


    # Define fallback functions
    def firebase_auth_required(f):
        return f


    def verify_firebase_token(token):
        return {"uid": "dev_user", "email": "dev@example.com"}


    def create_firebase_user(email, password):
        return {"uid": "new_dev_user", "email": email}


    FIREBASE_ENABLED = False


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # Initialize extensions
    db.init_app(app)

    # Initialize login manager
    login_manager = LoginManager()
    login_manager.login_view = 'login'
    login_manager.login_message_category = 'info'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Create database tables
    with app.app_context():
        db.create_all()

        # Create admin user if it doesn't exist
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@example.com',
                first_name='Admin',
                last_name='User',
                role='admin'
            )
            admin.set_password('admin123')  # Change this in production
            db.session.add(admin)
            db.session.commit()

    # Routes
    @app.route('/')
    def home():
        return render_template('index.html')

    # Enhanced file storage function
    def save_file(file, folder, allowed_extensions=None):
        """
        Save uploaded file securely with validation

        Args:
            file: The file object from request.files
            folder: Subfolder to save the file in
            allowed_extensions: List of allowed file extensions

        Returns:
            URL path to the saved file
        """
        if allowed_extensions is None:
            allowed_extensions = ['jpg', 'jpeg', 'png', 'pdf', 'doc', 'docx']

        # Validate file extension
        if '.' not in file.filename:
            raise ValueError("File has no extension")

        ext = file.filename.rsplit('.', 1)[1].lower()
        if ext not in allowed_extensions:
            raise ValueError(f"File extension not allowed. Allowed types: {', '.join(allowed_extensions)}")

        # Generate secure filename
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_filename = f"{timestamp}_{filename}"

        # Create directory if it doesn't exist
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], folder)
        os.makedirs(upload_path, exist_ok=True)

        # Save file
        file_path = os.path.join(upload_path, unique_filename)
        file.save(file_path)

        # Return URL path
        return f"/uploads/{folder}/{unique_filename}"
    # Enhanced login security
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            remember = 'remember' in request.form

            user = User.query.filter_by(username=username).first()

            # Check if account is locked
            if user and user.is_locked:
                flash('Account is locked. Please contact administrator.', 'danger')
                return render_template('login.html', firebase_enabled=FIREBASE_ENABLED)

            # Check credentials
            if user and user.check_password(password):
                # Reset login attempts on successful login
                user.login_attempts = 0
                user.last_login = datetime.utcnow()
                db.session.commit()

                login_user(user, remember=remember)
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard'))
            else:
                # Increment login attempts
                if user:
                    user.login_attempts += 1

                    # Lock account after 5 failed attempts
                    if user.login_attempts >= 5:
                        user.is_locked = True
                        flash('Too many failed login attempts. Account locked.', 'danger')
                    else:
                        flash('Invalid username or password', 'danger')

                    db.session.commit()
                else:
                    flash('Invalid username or password', 'danger')

        return render_template('login.html', firebase_enabled=FIREBASE_ENABLED)

    # Firebase Auth API endpoint
    @app.route('/api/auth/verify', methods=['POST'])
    def verify_auth():
        """Verify Firebase authentication and link to local user"""
        data = request.json

        if not data or not data.get('uid') or not data.get('email'):
            return jsonify({'status': 'error', 'message': 'Invalid data'}), 400

        # Check if user exists in our database
        user = User.query.filter_by(email=data['email']).first()

        if not user:
            try:
                # Create user in database if doesn't exist
                # Remove firebase_uid since it's not in your model
                user = User(
                    username=data['email'].split('@')[0],
                    email=data['email'],
                    role='admin'  # Default role for new users
                )

                # Set password for Flask login
                if hasattr(user, 'set_password'):
                    user.set_password('default_password')  # Should be changed

                db.session.add(user)
                db.session.commit()
                print(f"Created new user: {user.username}")
            except Exception as e:
                db.session.rollback()
                print(f"Error creating user: {e}")
                return jsonify({'status': 'error', 'message': str(e)}), 500

        # Set session data for Flask authentication
        session['user_id'] = user.id
        session['firebase_uid'] = data.get('uid')
        session['firebase_token'] = data.get('idToken')

        return jsonify({
            'status': 'success',
            'user_id': user.id,
            'role': user.role
        })

    # Calculator routes (as provided earlier)
    @app.route('/calculators')
    def calculators():
        """Main calculators page"""
        return render_template('calculators.html')

    @app.route('/calculators/emi')
    def emi_calculator():
        """EMI Calculator page"""
        return render_template('emi_calculator.html')

    @app.route('/calculators/gold')
    def gold_calculator():
        """Gold Loan Calculator page"""
        gold_rate = get_current_gold_rate()
        return render_template('gold_calculator.html', gold_rate=gold_rate)

    @app.route('/calculators/gold_conversion')
    def gold_conversion():
        """Gold conversion calculator page"""
        return render_template('gold_conversion.html')

    # API endpoints for calculators
    @app.route('/api/calculate/gold', methods=['POST'])
    def calculate_gold_loan_api():
        """API endpoint for gold loan calculation"""
        data = request.json

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Extract parameters
        weight = data.get('weight', 0)
        purity = data.get('purity', 0)
        rate_per_gram = data.get('rate_per_gram', 0)
        loan_to_value = data.get('loan_to_value', 75)

        # Calculate loan details
        result = calculate_gold_loan(weight, purity, rate_per_gram, loan_to_value)

        return jsonify(result)

    # Customer Management Routes
    @app.route('/customers')
    @login_required
    def list_customers():
        """List all customers"""
        customers = Customer.query.order_by(Customer.created_at.desc()).all()
        return render_template('customers/index.html', customers=customers)

    @app.route('/customers/new', methods=['GET', 'POST'])
    @login_required
    def new_customer():
        """Create a new customer"""
        if request.method == 'POST':
            # Validate and create new customer
            name = request.form.get('name')
            phone = request.form.get('phone')
            email = request.form.get('email')
            address = request.form.get('address')
            id_proof_type = request.form.get('id_proof_type')
            id_proof_number = request.form.get('id_proof_number')

            # Handle ID proof document upload
            id_proof_file = request.files.get('id_proof_file')
            id_proof_url = None

            if id_proof_file and id_proof_file.filename:
                id_proof_url = save_file(id_proof_file, 'customer_id_proofs')

            customer = Customer(
                name=name,
                phone=phone,
                email=email,
                address=address,
                id_proof_type=id_proof_type,
                id_proof_number=id_proof_number,
                id_proof_url=id_proof_url,
            )

            db.session.add(customer)
            db.session.commit()

            flash('Customer created successfully', 'success')
            return redirect(url_for('list_customers'))

        return render_template('customers/new.html')

    @app.route('/customers/<int:customer_id>')
    @login_required
    def view_customer(customer_id):
        """View customer details"""
        customer = Customer.query.get_or_404(customer_id)
        loans = Loan.query.filter_by(customer_id=customer.id).all()
        return render_template('customers/view.html', customer=customer, loans=loans)

    # Loan Management Routes
    @app.route('/loans/new/<int:customer_id>', methods=['GET', 'POST'])
    @login_required
    def new_loan(customer_id):
        """Create a new loan for a customer"""
        customer = Customer.query.get_or_404(customer_id)

        if request.method == 'POST':
            loan_type = request.form.get('loan_type')
            loan_amount = float(request.form.get('loan_amount'))
            interest_rate = float(request.form.get('interest_rate'))
            term_months = int(request.form.get('term_months'))

            # Calculate loan details
            start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
            due_date = start_date + timedelta(days=30 * term_months)

            # Calculate EMI
            emi_amount = calculate_emi(loan_amount, interest_rate, term_months)

            # Create the loan
            loan = Loan(
                customer_id=customer.id,
                loan_type=loan_type,
                loan_amount=loan_amount,
                interest_rate=interest_rate,
                term_months=term_months,
                start_date=start_date,
                due_date=due_date,
                emi_amount=emi_amount,
                remaining_amount=loan_amount,
                status='active'
            )

            # Add gold specific details if applicable
            if loan_type == LoanType.GOLD.value:
                loan.gold_weight = float(request.form.get('gold_weight'))
                loan.gold_purity = float(request.form.get('gold_purity'))
                loan.gold_items = request.form.get('gold_items')

            # Add land specific details if applicable
            if loan_type == LoanType.LAND.value:
                loan.land_details = request.form.get('land_details')

            db.session.add(loan)
            db.session.commit()

            # Upload documents
            documents = request.files.getlist('documents')
            for document in documents:
                if document and document.filename:
                    document_url = save_file(document, 'loan_documents')
                    doc = Document(
                        loan_id=loan.id,
                        document_type=request.form.get('document_type'),
                        document_url=document_url,
                        filename=document.filename
                    )
                    db.session.add(doc)

            db.session.commit()

            flash('Loan created successfully', 'success')
            return redirect(url_for('view_customer', customer_id=customer.id))

        return render_template('loans/new.html', customer=customer)

    # Document Management Routes
    @app.route('/documents/upload/<int:loan_id>', methods=['POST'])
    @login_required
    def upload_document(loan_id):
        """Upload document for a loan"""
        loan = Loan.query.get_or_404(loan_id)

        document_file = request.files.get('document')
        if document_file and document_file.filename:
            document_url = save_file(document_file, 'loan_documents')
            doc = Document(
                loan_id=loan.id,
                document_type=request.form.get('document_type'),
                document_url=document_url,
                filename=document_file.filename
            )
            db.session.add(doc)
            db.session.commit()

            flash('Document uploaded successfully', 'success')

        return redirect(url_for('view_loan', loan_id=loan.id))

    @app.route('/documents/view/<int:document_id>')
    @login_required
    def view_document(document_id):
        """View a document"""
        document = Document.query.get_or_404(document_id)
        return render_template('documents/view.html', document=document)

    @app.route('/api/auth/logout', methods=['POST'])
    def api_logout():
        """Clear server-side session when user logs out"""
        session.clear()
        return jsonify({'status': 'success'})

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('home'))

    # Add the dashboard route
    @app.route('/dashboard')
    def dashboard():
        # Check if user is authenticated either by Flask-Login or Firebase
        if not current_user.is_authenticated and 'user_id' not in session:
            return redirect(url_for('login'))

        # Get summary statistics
        total_loans = Loan.query.count()
        active_loans = Loan.query.filter_by(status='active').count()
        total_customers = Customer.query.count()

        # Calculate total loan amount and outstanding amount
        loans = Loan.query.all()
        total_loan_amount = sum(loan.loan_amount for loan in loans)
        outstanding_amount = sum(loan.remaining_amount for loan in loans if loan.status != LoanStatus.PAID.value)

        # Get recent loans
        recent_loans = Loan.query.order_by(Loan.created_at.desc()).limit(5).all()

        # Get recent customers
        recent_customers = Customer.query.order_by(Customer.created_at.desc()).limit(5).all()

        # Get overdue loans
        overdue_loans = Loan.query.filter_by(status=LoanStatus.OVERDUE.value).count()

        stats = {
            'total_loans': total_loans,
            'active_loans': active_loans,
            'total_customers': total_customers,
            'total_loan_amount': format_currency(total_loan_amount),
            'outstanding_amount': format_currency(outstanding_amount),
            'overdue_loans': overdue_loans
        }

        return render_template('dashboard.html',
                               stats=stats,
                               recent_loans=recent_loans,
                               recent_customers=recent_customers)

    # API endpoint to get user info
    @app.route('/api/user/info')
    def get_user_info():
        if current_user.is_authenticated:
            # User authenticated with Flask-Login
            return jsonify({
                'authenticated': True,
                'username': current_user.username,
                'email': current_user.email,
                'role': current_user.role
            })
        elif 'user_id' in session:
            # User authenticated with Firebase
            user = User.query.get(session['user_id'])
            if user:
                return jsonify({
                    'authenticated': True,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role
                })

        return jsonify({'authenticated': False}), 401

    return app


if __name__ == '__main__':
    app = create_app(os.getenv('FLASK_CONFIG') or 'default')
    print(f"Firebase Authentication: {'Enabled' if FIREBASE_ENABLED else 'Disabled'}")
    app.run(host='0.0.0.0', port=5000, debug=True)