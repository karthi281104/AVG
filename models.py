from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import enum

db = SQLAlchemy()


# Enums for types and status
class LoanType(enum.Enum):
    GOLD = 'gold'
    LAND = 'land'


class LoanStatus(enum.Enum):
    ACTIVE = 'active'
    OVERDUE = 'overdue'
    PAID = 'paid'
    DEFAULTED = 'defaulted'
    PENDING = 'pending'


# User model for administrators and staff
class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    role = db.Column(db.String(20), default='staff')  # 'admin', 'staff'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    firebase_uid = db.Column(db.String(128), unique=True, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


# Customer model for borrowers
class Customer(db.Model):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120))
    address = db.Column(db.String(256))
    id_proof_type = db.Column(db.String(50))
    id_proof_number = db.Column(db.String(50))
    id_proof_url = db.Column(db.String(256))  # URL to stored ID proof document
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    profile_photo_url = db.Column(db.String(256))
    kyc_verified = db.Column(db.Boolean, default=False)
    verification_date = db.Column(db.DateTime)
    verification_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='active')  # active, inactive, blacklisted

    # Relationships
    loans = db.relationship('Loan', backref='customer', lazy=True)
    __table_args__ = (
        db.Index('idx_customer_phone', 'phone'),
        db.Index('idx_customer_created_at', 'created_at'),
    )


    def __repr__(self):
        return f'<Customer {self.name}>'


# Loan model
class Loan(db.Model):
    __tablename__ = 'loans'

    id = db.Column(db.Integer, primary_key=True)
    loan_reference = db.Column(db.String(20), unique=True, nullable=False,
                               default=lambda: f"L{uuid.uuid4().hex[:8].upper()}")
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    loan_type = db.Column(db.String(20), nullable=False)  # 'gold' or 'land'
    loan_amount = db.Column(db.Float, nullable=False)
    interest_rate = db.Column(db.Float, nullable=False)
    term_months = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    emi_amount = db.Column(db.Float, nullable=False)
    remaining_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approval_date = db.Column(db.DateTime)
    last_payment_date = db.Column(db.DateTime)
    next_payment_date = db.Column(db.DateTime)
    collateral_verification_status = db.Column(db.String(20), default='pending')  # pending, verified, rejected

    __table_args__ = (
        db.Index('idx_loan_customer', 'customer_id'),
        db.Index('idx_loan_status', 'status'),
        db.Index('idx_loan_due_date', 'due_date'),
    )

    # Gold specific fields
    gold_weight = db.Column(db.Float)
    gold_purity = db.Column(db.Float)
    gold_items = db.Column(db.String(256))

    # Land specific fields
    land_details = db.Column(db.String(500))

    # Relationships
    payments = db.relationship('Payment', backref='loan', lazy=True)
    documents = db.relationship('Document', backref='loan', lazy=True)

    def __repr__(self):
        return f'<Loan {self.loan_reference}>'


# Payment model
class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, db.ForeignKey('loans.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.DateTime, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    reference_number = db.Column(db.String(100))
    notes = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __repr__(self):
        return f'<Payment {self.id} for Loan {self.loan_id}>'


# Document model for storing loan documents
class Document(db.Model):
    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, db.ForeignKey('loans.id'), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)
    document_url = db.Column(db.String(256), nullable=False)  # URL to stored document
    filename = db.Column(db.String(256))
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Document {self.document_type} for Loan {self.loan_id}>'


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    type = db.Column(db.String(50))  # payment_due, payment_received, loan_approved, etc.
    related_id = db.Column(db.Integer)  # Loan ID, Payment ID, etc.
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_notification_user', 'user_id', 'is_read'),
    )

# Gold Price History
class GoldPrice(db.Model):
    __tablename__ = 'gold_prices'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    price_per_gram = db.Column(db.Float, nullable=False)  # Price in INR for 24K gold

    def __repr__(self):
        return f'<GoldPrice {self.date}: {self.price_per_gram}>'