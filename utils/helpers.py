from datetime import datetime, timedelta
import calendar
from flask import current_app
import requests
import json
import os
import math


def calculate_emi(principal, interest_rate, tenure_months):
    """Calculate Equated Monthly Installment (EMI)"""
    if interest_rate == 0:
        return principal / tenure_months

    # Convert annual interest rate to monthly and decimal form
    monthly_interest = interest_rate / 100 / 12

    # Calculate EMI
    emi = principal * monthly_interest * (1 + monthly_interest) ** tenure_months / (
                (1 + monthly_interest) ** tenure_months - 1)

    return emi


def generate_amortization_schedule(principal, interest_rate, tenure_months):
    """Generate complete loan amortization schedule"""
    monthly_interest = interest_rate / 100 / 12
    emi = calculate_emi(principal, interest_rate, tenure_months)

    schedule = []
    remaining_principal = principal

    for month in range(1, tenure_months + 1):
        interest_payment = remaining_principal * monthly_interest
        principal_payment = emi - interest_payment

        # Ensure we don't have negative balance due to rounding
        if remaining_principal < principal_payment:
            principal_payment = remaining_principal
            interest_payment = emi - principal_payment if principal_payment < emi else 0

        remaining_principal -= principal_payment

        # Ensure remaining principal doesn't go below zero
        remaining_principal = 0 if remaining_principal < 0 else remaining_principal

        schedule.append({
            'month': month,
            'emi': round(emi, 2),
            'principal_payment': round(principal_payment, 2),
            'interest_payment': round(interest_payment, 2),
            'remaining_principal': round(remaining_principal, 2)
        })

    return {
        'monthly_emi': round(emi, 2),
        'total_payment': round(emi * tenure_months, 2),
        'total_interest': round((emi * tenure_months) - principal, 2),
        'schedule': schedule
    }


def calculate_gold_loan(weight, purity, rate_per_gram, loan_to_value=75):
    """Calculate gold loan amount based on weight, purity, and current rate"""
    # Calculate actual gold value
    gold_value = weight * (purity / 100) * rate_per_gram

    # Calculate loan amount based on LTV (Loan-to-Value) ratio
    max_loan_amount = gold_value * (loan_to_value / 100)

    return {
        'gold_value': round(gold_value, 2),
        'max_loan_amount': round(max_loan_amount, 2),
        'loan_to_value': loan_to_value
    }


def convert_gold_measurement(value, conversion_type):
    """Convert between gold carat and percentage purity"""
    if conversion_type == 'carat_to_percentage':
        # 24K is 99.9% pure gold
        percentage = (value / 24) * 100
        return round(percentage, 2)
    else:  # 'percentage_to_carat'
        # Convert percentage purity to carat
        carat = (value * 24) / 100
        return round(carat, 2)


def get_current_gold_rate():
    """Get current gold rate from an API or local database"""
    # Try to get from API if API key is available
    api_key = current_app.config.get('GOLD_API_KEY')

    if api_key:
        try:
            response = requests.get(
                f"https://www.goldapi.io/api/XAU/INR",
                headers={'x-access-token': api_key, 'Content-Type': 'application/json'}
            )
            if response.status_code == 200:
                data = response.json()
                # Convert from per troy ounce to per gram
                # (1 troy ounce = 31.1034768 grams)
                return data['price'] / 31.1034768
        except Exception as e:
            current_app.logger.error(f"Error fetching gold rate from API: {e}")

    # Fallback to a reasonable default value for India
    # This should ideally come from a database that is updated regularly
    return 5000  # Default value in INR per gram for 24K gold


def format_currency(amount, currency='₹'):
    """Format amount as currency"""
    if amount is None:
        return f"{currency} 0.00"

    return f"{currency} {amount:,.2f}"


def get_overdue_loans(days_overdue=0):
    """Get loans that are overdue by specified number of days"""
    from models import Loan, LoanStatus

    today = datetime.now().date()
    overdue_date = today - timedelta(days=days_overdue)

    return Loan.query.filter(
        Loan.status != LoanStatus.PAID.value,
        Loan.due_date <= overdue_date
    ).all()


def calculate_upcoming_payments(days=30):
    """Get upcoming payments due in the next specified days"""
    from models import Loan, LoanStatus

    today = datetime.now().date()
    future_date = today + timedelta(days=days)

    # This is a simplified approach, a more accurate one would consider
    # the actual payment schedule of each loan
    return Loan.query.filter(
        Loan.status != LoanStatus.PAID.value,
        Loan.due_date > today,
        Loan.due_date <= future_date
    ).all()


def format_date(date, format_str='%d-%m-%Y'):
    """Format a date object as string"""
    if isinstance(date, str):
        try:
            date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            return date

    return date.strftime(format_str) if date else ''