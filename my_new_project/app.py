import os
import mysql.connector
from flask import Flask, request, render_template_string
import time

# --- Embedded HTML Template (MUST REMAIN at the module level) ---
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>K8s Login Demo</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
    </style>
</head>
<body class="bg-gray-50 min-h-screen flex items-center justify-center p-4">
    <div class="w-full max-w-sm bg-white p-8 rounded-xl shadow-2xl border border-gray-200">
        <h1 class="text-3xl font-extrabold text-center text-blue-600 mb-6">Kubernetes Login Demo</h1>
        <p class="text-center text-sm text-gray-500 mb-8">App connects to the <strong>mysql-service</strong> container.</p>
        
        {% if message %}
        <div class="bg-{{ 'green' if success else 'red' }}-50 border-l-4 border-{{ 'green' if success else 'red' }}-500 text-{{ 'green' if success else 'red' }}-700 p-4 mb-4 rounded-lg shadow-sm" role="alert">
            <p class="font-bold">{{ 'SUCCESS' if success else 'ERROR' }}</p>
            <p>{{ message }}</p>
        </div>
        {% endif %}

        <form action="/login" method="post" class="space-y-6">
            <div>
                <label for="username" class="block text-sm font-medium text-gray-700 mb-1">Username</label>
                <input type="text" id="username" name="username" required
                        class="mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-blue-500 focus:border-blue-500 transition duration-150 ease-in-out"
                        placeholder="admin">
            </div>
            <div>
                <label for="password" class="block text-sm font-medium text-gray-700 mb-1">Password</label>
                <input type="password" id="password" name="password" required
                        class="mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-blue-500 focus:border-blue-500 transition duration-150 ease-in-out"
                        placeholder="secret123">
            </div>
            
            <button type="submit"
                    class="w-full flex justify-center py-2 px-4 border border-transparent rounded-lg shadow-md text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition duration-150 ease-in-out">
                Log In
            </button>
        </form>

        <p class="mt-6 text-center text-xs text-gray-400">DB Host Check: {{ db_host }}</p>
    </div>
</body>
</html>
"""

# --- Database Connection and Setup (Modified to accept app_config) ---
def create_db_connection(app_config):
    """Establishes and returns a MySQL database connection, using app_config."""
    try:
        conn = mysql.connector.connect(
            host=app_config['DB_HOST'],
            user=app_config['DB_USER'],
            password=app_config['DB_PASSWORD'],
            database=app_config['DB_NAME']
        )
        return conn
    except mysql.connector.Error as err:
        # We print the error but do not raise it, allowing retries
        print(f"Error connecting to MySQL at {app_config['DB_HOST']}: {err}")
        return None
#comment test
def initialize_database(app_config):
    """Initializes the database and creates a sample user table/user, using app_config."""
    conn = None
    try:
        # Connect to MySQL server (without specifying the database name initially)
        conn = mysql.connector.connect(
            host=app_config['DB_HOST'],
            user=app_config['DB_USER'],
            password=app_config['DB_PASSWORD'] 
        )
        cursor = conn.cursor()

        # 1. Create Database
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {app_config['DB_NAME']}")
        print(f"Database '{app_config['DB_NAME']}' checked/created.")
        conn.database = app_config['DB_NAME'] # Switch context

        # 2. Create Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL
            )
        """)
        print("Table 'users' checked/created.")

        # 3. Insert Sample User if table is empty
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", ('admin', 'secret123'))
            print("Sample user 'admin' inserted.")

        conn.commit()
        return True # Return True on success

    except mysql.connector.Error as err:
        print(f"Database initialization failed (will retry): {err}")
        return False # Return False on failure

    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def wait_for_db_and_initialize(app_config, max_retries=10, delay_seconds=6):
    """Waits for the MySQL service to be ready and runs initialization."""
    print(f"Attempting database initialization. Host: {app_config['DB_HOST']}")
    for attempt in range(max_retries):
        if initialize_database(app_config):
            print("Database initialization successful! App is ready.")
            return
        
        if attempt < max_retries - 1:
            print(f"Waiting for {delay_seconds} seconds before retrying (Attempt {attempt + 1}/{max_retries})...")
            time.sleep(delay_seconds)
        else:
            print("FATAL ERROR: Max database initialization retries reached. Exiting or continuing uninitialized.")


# --- Application Factory Function ---
def create_app(test_config=None):
    app = Flask(__name__)
    app.secret_key = os.urandom(24)
    app.testing = False # Default unless overridden by test_config

    # 1. Read Configuration
    if test_config is None:
        # Load values from environment or default (for normal run)
        app.config['DB_HOST'] = os.environ.get('DB_HOST', 'localhost')
        app.config['DB_USER'] = os.environ.get('DB_USER', 'user')
        app.config['DB_PASSWORD'] = os.environ.get('DB_PASSWORD', 'password')
        app.config['DB_NAME'] = os.environ.get('DB_NAME', 'testdb')
    else:
        # Load test config (for pytest)
        app.config.update(test_config)
        app.testing = True # Set testing flag if test_config is passed

    # 2. Initialization (only run if not testing)
    if not app.testing:
        wait_for_db_and_initialize(app.config)

    # --- Flask Routes ---
    @app.route('/', methods=['GET'])
    def index():
        """Displays the login form."""
        return render_template_string(LOGIN_HTML, message=None, success=False, db_host=app.config['DB_HOST'])

    @app.route('/login', methods=['POST'])
    def login():
        """Handles the login attempt by checking credentials against the MySQL DB."""
        username = request.form['username']
        password = request.form['password']

        conn = create_db_connection(app.config)
        message = "Login failed: Invalid username or password."
        success = False

        if conn is None:
            message = "Login failed: Database connection could not be established. Initialization may still be pending."
        else:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT username FROM users WHERE username = %s AND password = %s"
            cursor.execute(query, (username, password))
            user = cursor.fetchone()

            if user:
                message = f"Login successful! Welcome, {user['username']}."
                success = True

            cursor.close()
            conn.close()

        return render_template_string(LOGIN_HTML, message=message, success=success, db_host=app.config['DB_HOST'])
        
    return app


# --- Execution Block (No global call to wait_for_db_and_initialize) ---
if __name__ == '__main__':
    # When running normally, create the app and run it
    app_instance = create_app()
    app_instance.run(host='0.0.0.0', port=5000)
