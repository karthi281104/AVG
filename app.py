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

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            remember = 'remember' in request.form

            user = User.query.filter_by(username=username).first()

            if user and user.check_password(password):
                login_user(user, remember=remember)

                # Update last login time
                user.last_login = datetime.utcnow()
                db.session.commit()

                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard'))
            else:
                flash('Invalid username or password', 'danger')

        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('home'))

    # Public calculator routes
    @app.route('/calculators')
    def calculators():
        return render_template('calculators.html')

    @app.route('/calculators/emi')
    def emi_calculator():
        return render_template('emi_calculator.html')

    @app.route('/calculators/gold')
    def gold_calculator():
        gold_rate = get_current_gold_rate()
        return render_template('gold_calculator.html', gold_rate=gold_rate)

    @app.route('/calculators/gold-conversion')
    def gold_conversion():
        return render_template('gold_conversion.html')

    # Protected routes
    @app.route('/dashboard')
    @login_required
    def dashboard():
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

    @app.route('/customers')
    @login_required
    def customers_list():
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        query = Customer.query.order_by(Customer.name)

        # Handle search query
        search = request.args.get('search')
        if search:
            query = query.filter(
                (Customer.name.ilike(f'%{search}%')) |
                (Customer.phone.ilike(f'%{search}%')) |
                (Customer.email.ilike(f'%{search}%'))
            )

        # Paginate results
        pagination = query.paginate(page=page, per_page=per_page)
        customers = pagination.items

        return render_template('customers/list.html',
                               customers=customers,
                               pagination=pagination,
                               search=search)

    @app.route('/customers/add', methods=['GET', 'POST'])
    @login_required
    def add_customer():
        if request.method == 'POST':
            # Extract form data
            name = request.form.get('name')
            phone = request.form.get('phone')
            email = request.form.get('email')
            address = request.form.get('address')
            id_proof_type = request.form.get('id_proof_type')
            id_proof_number = request.form.get('id_proof_number')

            # Validation
            if not name or not phone:
                flash('Name and phone number are required', 'danger')
                return redirect(url_for('add_customer'))

            # Create new customer object
            customer = Customer(
                name=name,
                phone=phone,
                email=email,
                address=address,
                id_proof_type=id_proof_type,
                id_proof_number=id_proof_number
            )

            # Handle ID proof document upload
            id_proof_doc = request.files.get('id_proof_doc')
            if id_proof_doc and id_proof_doc.filename:
                file_path = save_file(id_proof_doc, folder='id_proofs')
                if file_path:
                    customer.id_proof_url = file_path

            # Save to database
            db.session.add(customer)
            db.session.commit()

            flash('Customer added successfully!', 'success')
            return redirect(url_for('customers_list'))

        return render_template('customers/add.html')

    @app.route('/customers/<int:id>')
    @login_required
    def view_customer(id):
        customer = Customer.query.get_or_404(id)
        loans = Loan.query.filter_by(customer_id=id).all()

        return render_template('customers/view.html', customer=customer, loans=loans)

    @app.route('/customers/<int:id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_customer(id):
        customer = Customer.query.get_or_404(id)

        if request.method == 'POST':
            customer.name = request.form.get('name')
            customer.phone = request.form.get('phone')
            customer.email = request.form.get('email')
            customer.address = request.form.get('address')
            customer.id_proof_type = request.form.get('id_proof_type')
            customer.id_proof_number = request.form.get('id_proof_number')

            # Handle ID proof document update
            id_proof_doc = request.files.get('id_proof_doc')
            if id_proof_doc and id_proof_doc.filename:
                file_path = save_file(id_proof_doc, folder='id_proofs')
                if file_path:
                    customer.id_proof_url = file_path

            db.session.commit()
            flash('Customer updated successfully!', 'success')
            return redirect(url_for('view_customer', id=customer.id))

        return render_template('customers/edit.html', customer=customer)

    @app.route('/loans')
    @login_required
    def loans_list():
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        query = Loan.query.order_by(Loan.created_at.desc())

        # Handle filtering
        status = request.args.get('status')
        loan_type = request.args.get('type')

        if status:
            query = query.filter(Loan.status == status)

        if loan_type:
            query = query.filter(Loan.loan_type == loan_type)

        # Handle search
        search = request.args.get('search')
        if search:
            query = query.join(Customer).filter(
                (Customer.name.ilike(f'%{search}%')) |
                (Loan.loan_reference.ilike(f'%{search}%'))
            )

        pagination = query.paginate(page=page, per_page=per_page)
        loans = pagination.items

        return render_template('loans/list.html',
                               loans=loans,
                               pagination=pagination,
                               status=status,
                               loan_type=loan_type,
                               search=search)

    @app.route('/loans/add', methods=['GET', 'POST'])
    @login_required
    def add_loan():
        if request.method == 'POST':
            # Extract basic loan details
            customer_id = request.form.get('customer_id')
            loan_type = request.form.get('loan_type')
            loan_amount = float(request.form.get('loan_amount'))
            interest_rate = float(request.form.get('interest_rate'))
            term_months = int(request.form.get('term_months'))
            start_date_str = request.form.get('start_date')

            # Convert start date string to date object
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()

            # Calculate due date and EMI
            due_date = start_date + timedelta(days=30 * term_months)
            emi = calculate_emi(loan_amount, interest_rate, term_months)

            # Create loan object
            loan = Loan(
                customer_id=customer_id,
                loan_type=loan_type,
                loan_amount=loan_amount,
                interest_rate=interest_rate,
                term_months=term_months,
                start_date=start_date,
                due_date=due_date,
                emi_amount=emi,
                remaining_amount=loan_amount,
                status=LoanStatus.ACTIVE.value
            )

            # Handle type-specific data
            if loan_type == LoanType.GOLD.value:
                loan.gold_weight = float(request.form.get('gold_weight'))
                loan.gold_purity = float(request.form.get('gold_purity'))
                loan.gold_items = request.form.get('gold_items')

                # Handle gold photos
                gold_photos = request.files.getlist('gold_photos')
                for photo in gold_photos:
                    if photo and photo.filename:
                        file_path = save_file(photo, folder='gold_photos')
                        if file_path:
                            document = Document(
                                loan=loan,
                                document_type='gold_photo',
                                document_url=file_path,
                                filename=photo.filename
                            )
                            db.session.add(document)

            elif loan_type == LoanType.LAND.value:
                loan.land_details = request.form.get('land_details')

                # Handle land documents
                land_docs = request.files.getlist('land_documents')
                for doc in land_docs:
                    if doc and doc.filename:
                        file_path = save_file(doc, folder='land_documents')
                        if file_path:
                            document = Document(
                                loan=loan,
                                document_type='land_document',
                                document_url=file_path,
                                filename=doc.filename
                            )
                            db.session.add(document)

            # Save the loan
            db.session.add(loan)
            db.session.commit()

            flash('Loan added successfully!', 'success')
            return redirect(url_for('view_loan', id=loan.id))

        # Get all customers for dropdown
        customers = Customer.query.order_by(Customer.name).all()
        gold_rate = get_current_gold_rate()

        return render_template('loans/add.html',
                               customers=customers,
                               loan_types=[t.value for t in LoanType],
                               gold_rate=gold_rate)

    @app.route('/loans/<int:id>')
    @login_required
    def view_loan(id):
        loan = Loan.query.get_or_404(id)
        customer = Customer.query.get(loan.customer_id)
        payments = Payment.query.filter_by(loan_id=loan.id).order_by(Payment.payment_date.desc()).all()
        documents = Document.query.filter_by(loan_id=loan.id).all()

        # Calculate loan statistics
        total_paid = sum(payment.amount for payment in payments)
        payment_progress = (total_paid / loan.loan_amount) * 100 if loan.loan_amount > 0 else 0

        # Generate amortization schedule for display
        schedule = generate_amortization_schedule(
            loan.loan_amount,
            loan.interest_rate,
            loan.term_months
        )

        return render_template('loans/view.html',
                               loan=loan,
                               customer=customer,
                               payments=payments,
                               documents=documents,
                               total_paid=total_paid,
                               payment_progress=payment_progress,
                               schedule=schedule)

    @app.route('/loans/<int:id>/payment', methods=['POST'])
    @login_required
    def add_payment(id):
        loan = Loan.query.get_or_404(id)

        amount = float(request.form.get('amount'))
        payment_date_str = request.form.get('payment_date')
        payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d')
        payment_method = request.form.get('payment_method')
        reference_number = request.form.get('reference_number')
        notes = request.form.get('notes')

        # Create payment record
        payment = Payment(
            loan_id=loan.id,
            amount=amount,
            payment_date=payment_date,
            payment_method=payment_method,
            reference_number=reference_number,
            notes=notes,
            created_by=current_user.id if current_user.is_authenticated else None
        )
        db.session.add(payment)

        # Update loan remaining amount
        loan.remaining_amount -= amount

        # Update loan status if fully paid
        if loan.remaining_amount <= 0:
            loan.remaining_amount = 0
            loan.status = LoanStatus.PAID.value

        db.session.commit()

        flash('Payment recorded successfully!', 'success')
        return redirect(url_for('view_loan', id=loan.id))

    @app.route('/reports')
    @login_required
    def reports():
        return render_template('reports/index.html')

    @app.route('/reports/customer/<int:id>')
    @login_required
    def customer_report(id):
        customer = Customer.query.get_or_404(id)
        loans = Loan.query.filter_by(customer_id=id).all()

        total_borrowed = sum(loan.loan_amount for loan in loans)
        total_remaining = sum(loan.remaining_amount for loan in loans)
        total_paid = total_borrowed - total_remaining

        return render_template('reports/customer.html',
                               customer=customer,
                               loans=loans,
                               total_borrowed=total_borrowed,
                               total_paid=total_paid,
                               total_remaining=total_remaining)

    @app.route('/reports/overdue')
    @login_required
    def overdue_report():
        today = datetime.now().date()
        overdue_loans = Loan.query.filter(
            Loan.status != LoanStatus.PAID.value,
            Loan.due_date < today
        ).all()

        for loan in overdue_loans:
            loan.days_overdue = (today - loan.due_date).days

        return render_template('reports/overdue.html', loans=overdue_loans)

    # API endpoints for calculators
    @app.route('/api/calculate/emi', methods=['POST'])
    def api_calculate_emi():
        data = request.get_json()
        principal = float(data.get('principal', 0))
        interest_rate = float(data.get('interest_rate', 0))
        tenure_months = int(data.get('tenure_months', 1))

        result = generate_amortization_schedule(principal, interest_rate, tenure_months)
        return jsonify(result)

    @app.route('/api/calculate/gold', methods=['POST'])
    def api_calculate_gold_loan():
        data = request.get_json()
        weight = float(data.get('weight', 0))
        purity = float(data.get('purity', 0))
        rate_per_gram = float(data.get('rate_per_gram', get_current_gold_rate()))
        loan_to_value = float(data.get('loan_to_value', 75))

        result = calculate_gold_loan(weight, purity, rate_per_gram, loan_to_value)
        return jsonify(result)

    @app.route('/api/convert/gold', methods=['POST'])
    def api_convert_gold_measure():
        data = request.get_json()
        value = float(data.get('value', 0))
        conversion_type = data.get('conversion_type')

        result = convert_gold_measurement(value, conversion_type)
        if conversion_type == 'carat_to_percentage':
            return jsonify({'percentage': result})
        else:
            return jsonify({'carat': result})

    @app.route('/api/customers/search')
    @login_required
    def api_search_customers():
        query = request.args.get('query', '')
        if not query or len(query) < 2:
            return jsonify([])

        customers = Customer.query.filter(
            (Customer.name.ilike(f'%{query}%')) |
            (Customer.phone.ilike(f'%{query}%'))
        ).limit(10).all()

        results = [
            {
                'id': customer.id,
                'name': customer.name,
                'phone': customer.phone,
                'text': f"{customer.name} ({customer.phone})"
            }
            for customer in customers
        ]

        return jsonify(results)

    # Error handlers
    @app.errorhandler(404)
    def page_not_found(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template('errors/500.html'), 500

    # Add a context processor for common data
    @app.context_processor
    def utility_processor():
        return {
            'now': datetime.utcnow(),
            'format_currency': format_currency
        }

    return app


if __name__ == '__main__':
    app = create_app(os.getenv('FLASK_CONFIG') or 'default')
    app.run(host='0.0.0.0', port=5000)