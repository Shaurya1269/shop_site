from flask import Blueprint, request, redirect, session, flash
from app.models.user_model import create_user, get_user_by_email
from app.utils.auth import hash_password, verify_password

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')

    if not name or not email or not password:
        flash("All fields are required.", "danger")
        return redirect('/register')

    if len(password) < 8:
        flash("Password must be at least 8 characters.", "danger")
        return redirect('/register')

    # Basic email format check
    if '@' not in email or '.' not in email.split('@')[-1]:
        flash("Please enter a valid email address.", "danger")
        return redirect('/register')

    existing = get_user_by_email(email)
    if existing:
        flash("An account with that email already exists.", "danger")
        return redirect('/register')

    password_hash = hash_password(password)
    create_user(name, email, password_hash)
    flash("Account created successfully! Please log in.", "success")
    return redirect('/login')


@auth_bp.route('/login', methods=['POST'])
def login():
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')

    # Retrieve the user from the database based on the provided email
    user = get_user_by_email(email)

    # Check if the user exists and if the provided password matches the stored password hash
    if not user or not verify_password(password, user['password_hash']):
        flash("Invalid email or password.", "danger")
        return redirect('/login')

    session['user_id'] = user['id']
    return redirect('/dashboard')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect('/')
