# Shop Site - E-commerce Platform

A full-featured e-commerce platform built with Flask, PostgreSQL, and modern web technologies.

## Features

- User authentication and registration
- Shop creation and management
- Product catalog management
- Shopping cart functionality
- Order processing and history
- Responsive web interface

## Setup Instructions

### Prerequisites

- Python 3.8+
- PostgreSQL database
- Git

### Installation

1. **Clone the repository:**

   ```bash
   git clone <your-repo-url>
   cd shop-site
   ```

2. **Create a virtual environment:**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**

   ```bash
   cp .env.example .env
   ```

   Edit the `.env` file with your actual configuration:

   ```env
   SECRET_KEY=your_secret_key_here
   DATABASE_URL=postgresql://username:password@localhost:5432/database_name
   FLASK_ENV=development
   FLASK_DEBUG=True
   ```

5. **Set up the database:**
   - Create a PostgreSQL database
   - Run the schema file to create tables:
     ```bash
     psql -U username -d database_name -f database/schema.sql
     ```

6. **Run the application:**

   ```bash
   python run.py
   ```

   The application will be available at `http://localhost:5000`

## Project Structure

```
shop-site/
├── app/
│   ├── __init__.py
│   ├── app.py              # Flask application factory
│   ├── config.py           # Configuration settings
│   ├── models/             # Database models
│   ├── routes/             # Route handlers
│   ├── templates/          # Jinja2 templates
│   ├── static/             # CSS, JS, images
│   └── utils/              # Utility functions
├── database/
│   └── schema.sql          # Database schema
├── .env.example            # Environment variables template
├── requirements.txt        # Python dependencies
├── run.py                  # Application entry point
└── README.md
```

## Environment Variables

The application uses the following environment variables:

- `SECRET_KEY`: Flask secret key for session management
- `DATABASE_URL`: PostgreSQL connection string
- `FLASK_ENV`: Flask environment (development/production)
- `FLASK_DEBUG`: Enable/disable debug mode

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.
