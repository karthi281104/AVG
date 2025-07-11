from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, g, current_app
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from flask_cors import CORS
import os
import json

from config import config
from models import db, User, Customer, Loan, Payment, Document, LoanType, LoanStatus
from utils.security import admin_required, save_file, validate_loan_application
from utils.helpers import (calculate_emi, generate_amortization_schedule,
                           calculate_gold_loan, convert_gold_measurement,
                           get_current_gold_rate, format_currency)

# Import Firebase auth functions - with proper initialization
try:
    import firebase_admin
    from firebase_admin import credentials, auth as firebase_auth

    if not firebase_admin._apps:
        # This is the change: point directly to your file
        cred = credentials.Certificate("service-account.json")
        firebase_admin.initialize_app(cred)

    FIREBASE_ENABLED = True
    print("Firebase Admin SDK initialized successfully")

except Exception as e:
    print(f"Error initializing Firebase: {e}")
    FIREBASE_ENABLED = False


    # Define fallback functions for when Firebase is not available
    class MockFirebaseAuth:
        @staticmethod
        def verify_id_token(token):
            return {"uid": "dev_user", "email": "dev@example.com"}


    firebase_auth = MockFirebaseAuth()


# Define the auth decorator
def firebase_auth_required(f):
    def decorated_function(*args, **kwargs):
        if not FIREBASE_ENABLED:
            return f(*args, **kwargs)

        # Add your Firebase auth logic here if needed
        return f(*args, **kwargs)

    return decorated_function


# Helper functions
def verify_firebase_token(token):
    if not FIREBASE_ENABLED:
        return {"uid": "dev_user", "email": "dev@example.com"}

    try:
        decoded_token = firebase_auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        print(f"Error verifying Firebase token: {e}")
        return None


def create_firebase_user(email, password):
    if not FIREBASE_ENABLED:
        return {"uid": "new_dev_user", "email": email}

    try:
        user = firebase_auth.create_user(
            email=email,
            password=password
        )
        return {"uid": user.uid, "email": email}
    except Exception as e:
        print(f"Error creating Firebase user: {e}")
        return None


def create_app(config_name='default'):
    app = Flask(__name__)
    # csrf = CSRFProtect(app)

    # Exempt Firebase auth endpoint from CSRF protection
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # Initialize extensions
    db.init_app(app)
    # csrf = CSRFProtect(app)

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
    # Replace your existing /api/auth/verify route with this enhanced version
    @app.route('/api/auth/verify', methods=['POST'])
    # @csrf.exempt
    def verify_auth():
        try:
            # Debug: Print request details
            print(f"Request method: {request.method}")
            print(f"Request headers: {dict(request.headers)}")
            print(f"Request content type: {request.content_type}")

            # Try to get JSON data FIRST
            try:
                data = request.get_json()
                # Now it's safe to print the parsed data for debugging
                print(f"Request Body (Parsed JSON): {data}")
            except Exception as json_error:
                print(f"JSON parsing error: {json_error}")
                # You can also log the raw data here if parsing fails, but be careful
                # print(f"Raw data on error: {request.data}") # This might still cause issues
                return jsonify({'status': 'error', 'message': 'Invalid JSON format'}), 400

            if not data:
                print("No JSON data received")
                return jsonify({'status': 'error', 'message': 'No data provided'}), 400

            # ... rest of your function logic ...

            # Debug: Check what fields are present
            print(f"Data keys: {list(data.keys()) if data else 'None'}")
            print(f"UID: {data.get('uid')}")
            print(f"Email: {data.get('email')}")
            print(f"idToken present: {'idToken' in data if data else False}")

            # Check required fields
            missing_fields = []
            if not data.get('uid'):
                missing_fields.append('uid')
            if not data.get('email'):
                missing_fields.append('email')
            if not data.get('idToken'):
                missing_fields.append('idToken')

            if missing_fields:
                error_msg = f'Missing required fields: {", ".join(missing_fields)}'
                print(f"Validation error: {error_msg}")
                return jsonify({'status': 'error', 'message': error_msg}), 400

            # Continue with existing logic...
            # Verify Firebase token
            try:
                if FIREBASE_ENABLED:
                    decoded_token = firebase_auth.verify_id_token(data['idToken'])
                    print(f"Decoded token: {decoded_token}")

                    # Verify UID matches
                    if decoded_token['uid'] != data['uid']:
                        return jsonify({'status': 'error', 'message': 'UID mismatch'}), 401

                else:
                    # Fallback for testing
                    decoded_token = {"uid": data['uid'], "email": data['email']}
                    print("Using fallback authentication (Firebase disabled)")

            except Exception as e:
                print(f"Token verification error: {e}")
                return jsonify({'status': 'error', 'message': 'Invalid Firebase ID token'}), 401

            # Check if user exists in our database
            user = User.query.filter_by(email=data['email']).first()

            if not user:
                try:
                    # Create new user
                    username = data['email'].split('@')[0]

                    # Make sure username is unique
                    counter = 1
                    original_username = username
                    while User.query.filter_by(username=username).first():
                        username = f"{original_username}_{counter}"
                        counter += 1

                    user = User(
                        username=username,
                        email=data['email'],
                        first_name=data.get('first_name', ''),
                        last_name=data.get('last_name', ''),
                        role='user'  # Default role for new users
                    )

                    # Set a default password (won't be used for Firebase auth)
                    if hasattr(user, 'set_password'):
                        user.set_password('firebase_user_no_password')

                    db.session.add(user)
                    db.session.commit()
                    print(f"Created new user: {user.username} ({user.email})")

                except Exception as e:
                    db.session.rollback()
                    print(f"Error creating user: {e}")
                    return jsonify({'status': 'error', 'message': f'Error creating user: {str(e)}'}), 500

            # Update user's last login
            user.last_login = datetime.utcnow()
            db.session.commit()

            # Set session data
            session['user_id'] = user.id
            session['firebase_uid'] = data['uid']
            session['firebase_token'] = data['idToken']
            session['authenticated'] = True

            # Also login the user with Flask-Login for compatibility
            login_user(user, remember=True)

            print(f"User authenticated successfully: {user.email}")

            return jsonify({
                'status': 'success',
                'user_id': user.id,
                'role': user.role,
                'username': user.username,
                'email': user.email,
                'message': 'Authentication successful'
            })

        except Exception as e:
            print(f"Authentication error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'status': 'error', 'message': f'Authentication failed: {str(e)}'}), 500

    # Calculator routes
    @app.route('/calculators')
    def calculators():
        """Main calculators page"""
        return render_template('calculator.html')

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

    @app.route('/api/calculate/emi', methods=['POST'])
    def calculate_emi_api():
        """API endpoint for EMI calculation"""
        data = request.json

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Extract parameters
        principal = data.get('principal', 0)
        interest_rate = data.get('interest_rate', 0)
        tenure_months = data.get('tenure_months', 0)

        if principal <= 0 or interest_rate < 0 or tenure_months <= 0:
            return jsonify({'error': 'Invalid parameters'}), 400

        # Generate amortization schedule
        result = generate_amortization_schedule(principal, interest_rate, tenure_months)

        return jsonify(result)

    @app.route('/api/calculate/gold_conversion', methods=['POST'])
    def calculate_gold_conversion_api():
        """API endpoint for gold carat/percentage conversion"""
        data = request.json

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Extract parameters
        value = data.get('value', 0)
        conversion_type = data.get('conversion_type', 'carat_to_percentage')

        if value <= 0:
            return jsonify({'error': 'Invalid value'}), 400

        if conversion_type not in ['carat_to_percentage', 'percentage_to_carat']:
            return jsonify({'error': 'Invalid conversion type'}), 400

        # Perform conversion
        result = convert_gold_measurement(value, conversion_type)

        return jsonify({'converted_value': result})

    # Customer Management Routes
    @app.route('/customers')
    @login_required
    def list_customers():
        """List all customers with pagination"""
        page = request.args.get('page', 1, type=int)
        per_page = 20  # Number of customers per page

        customers = Customer.query.order_by(Customer.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return render_template('customers/list.html', customers=customers)

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
            notes = request.form.get('notes')
            kyc_verified = 'kyc_verified' in request.form

            # Validate required fields
            if not all([name, phone, id_proof_type, id_proof_number]):
                flash('Please fill in all required fields', 'error')
                return render_template('customers/new.html')

            # Handle ID proof document upload
            id_proof_file = request.files.get('id_proof_file')
            id_proof_url = None
            if id_proof_file and id_proof_file.filename:
                try:
                    id_proof_url = save_file(id_proof_file, 'customer_id_proofs')
                except ValueError as e:
                    flash(f'ID proof upload error: {str(e)}', 'error')
                    return render_template('customers/new.html')

            # Handle profile photo upload
            profile_photo_file = request.files.get('profile_photo')
            profile_photo_url = None
            if profile_photo_file and profile_photo_file.filename:
                try:
                    profile_photo_url = save_file(profile_photo_file, 'customer_photos')
                except ValueError as e:
                    flash(f'Profile photo upload error: {str(e)}', 'error')
                    return render_template('customers/new.html')

            customer = Customer(
                name=name,
                phone=phone,
                email=email,
                address=address,
                id_proof_type=id_proof_type,
                id_proof_number=id_proof_number,
                id_proof_url=id_proof_url,
                profile_photo_url=profile_photo_url,
                notes=notes,
                kyc_verified=kyc_verified,
                verification_date=datetime.utcnow() if kyc_verified else None,
                verification_by=current_user.id if kyc_verified else None
            )

            try:
                db.session.add(customer)
                db.session.commit()
                flash('Customer created successfully', 'success')
                return redirect(url_for('list_customers'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error creating customer: {str(e)}', 'error')

        return render_template('customers/new.html')

    @app.route('/customers/<int:customer_id>')
    @login_required
    def view_customer(customer_id):
        """View customer details"""
        customer = Customer.query.get_or_404(customer_id)
        loans = Loan.query.filter_by(customer_id=customer.id).all()
        return render_template('customers/view.html', customer=customer, loans=loans)

    # Loan Management Routes
    @app.route('/loans')
    @login_required
    def list_loans():
        """List all loans with pagination"""
        page = request.args.get('page', 1, type=int)
        per_page = 20  # Number of loans per page

        loans = Loan.query.order_by(Loan.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return render_template('loans/list.html', loans=loans)

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

        return redirect(url_for('view_customer', customer_id=loan.customer_id))

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
        print(f"Dashboard access attempt:")
        print(f"  - current_user.is_authenticated: {current_user.is_authenticated}")
        print(f"  - 'user_id' in session: {'user_id' in session}")
        print(f"  - session contents: {dict(session)}")

        # Check if user is authenticated either by Flask-Login or Firebase
        if not current_user.is_authenticated and 'user_id' not in session:
            print("User not authenticated, redirecting to login")
            return redirect(url_for('login'))

        # Get user info
        if current_user.is_authenticated:
            user = current_user
        else:
            user = User.query.get(session['user_id'])
            if not user:
                print("User not found in database, clearing session")
                session.clear()
                return redirect(url_for('login'))

        print(f"User authenticated: {user.email}")

        # Get summary statistics
        try:
            total_loans = Loan.query.count()
            active_loans = Loan.query.filter_by(status='active').count()
            total_customers = Customer.query.count()

            # Calculate total loan amount and outstanding amount
            loans = Loan.query.all()
            total_loan_amount = sum(loan.loan_amount for loan in loans)
            outstanding_amount = sum(loan.remaining_amount for loan in loans if loan.status != LoanStatus.PAID.value)

            # Calculate average interest rate
            if loans:
                total_interest = sum(loan.interest_rate for loan in loans)
                average_interest_rate = total_interest / len(loans)
            else:
                average_interest_rate = 0

            # Calculate monthly collections (current month)
            from datetime import datetime
            current_month = datetime.now().month
            current_year = datetime.now().year
            
            monthly_payments = Payment.query.filter(
                Payment.payment_date >= datetime(current_year, current_month, 1)
            ).all()
            monthly_collection = sum(payment.amount for payment in monthly_payments)

            # Get recent loans
            recent_loans = Loan.query.order_by(Loan.created_at.desc()).limit(5).all()

            # Get recent customers
            recent_customers = Customer.query.order_by(Customer.created_at.desc()).limit(5).all()

            # Get overdue loans
            overdue_loans = Loan.query.filter_by(status=LoanStatus.OVERDUE.value).count()

            stats = {
                'total_customers': total_customers,
                'total_loan_amount': format_currency(total_loan_amount),
                'average_interest_rate': f"{average_interest_rate:.1f}%",
                'active_loans': active_loans,
                'monthly_collection': format_currency(monthly_collection),
                'overdue_loans': overdue_loans,
                'outstanding_amount': format_currency(outstanding_amount),
            }

            return render_template('dashboard.html',
                                   stats=stats,
                                   recent_loans=recent_loans,
                                   recent_customers=recent_customers,
                                   user=user)
        except Exception as e:
            print(f"Error loading dashboard: {e}")
            # Return dashboard with empty stats if there's an error
            return render_template('dashboard.html',
                                   stats={},
                                   recent_loans=[],
                                   recent_customers=[],
                                   user=user)

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

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    @app.errorhandler(413)
    def too_large(error):
        flash('File too large. Maximum file size is 16MB.', 'error')
        return redirect(request.url)

    return app


if __name__ == '__main__':
    app = create_app(os.getenv('FLASK_CONFIG') or 'default')
    print(f"Firebase Authentication: {'Enabled' if FIREBASE_ENABLED else 'Disabled'}")
    app.run(host='0.0.0.0', port=5000, debug=True)