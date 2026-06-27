"""
Shared Flask extension instances.

Importing extensions here (rather than inside create_app) lets other
modules (e.g. blueprints) import them without causing circular imports.
Each extension is initialised against the real app inside create_app()
via extension.init_app(app).
"""
from flask_wtf.csrf import CSRFProtect

# Single, shared CSRF instance — init_app() is called in app/__init__.py
csrf = CSRFProtect()
