from flask import Blueprint, request, redirect, session
from app.models.user_model import create_user, get_user_by_email
from app.utils.auth import hash_password, verify_password

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')

    if not name or not email or not password:
        return "All fields required", 400

    existing = get_user_by_email(email)
    if existing:
        return "User already exists", 409

    password_hash = hash_password(password)
    # Create a new user in the database with the provided name, email, and hashed password
    create_user(name, email, password_hash)
    return redirect('/login')


@auth_bp.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')

    # Retrieve the user from the database based on the provided email
    user = get_user_by_email(email)

    # Check if the user exists and if the provided password matches the stored password hash
    if not user or not verify_password(password, user['password_hash']):
        return "Invalid credentials"

    session['user_id'] = user['id']
    return redirect('/dashboard')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect('/')
