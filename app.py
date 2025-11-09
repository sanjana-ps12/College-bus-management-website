from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
import qrcode
from io import BytesIO
import json
import pymysql

# Load environment variables from .env file (only for local development)
# On Vercel/Render, environment variables are set in the dashboard
try:
    from dotenv import load_dotenv
    load_dotenv()  # This will silently fail if .env doesn't exist (which is fine for Vercel)
except ImportError:
    pass  # python-dotenv not available, use system environment variables

app = Flask(__name__)
# Secret key is required for sessions - use a default if not set (not secure for production!)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# MySQL Configuration using PyMySQL
class MySQL:
    """Custom MySQL wrapper using PyMySQL to replace Flask-MySQLdb"""
    def __init__(self, app=None):
        self.app = app
        self._connection = None
        self.config = {}
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        self.app = app
        self.config = {
            'host': app.config.get('MYSQL_HOST', 'localhost'),
            'user': app.config.get('MYSQL_USER', 'root'),
            'password': app.config.get('MYSQL_PASSWORD', ''),
            'database': app.config.get('MYSQL_DB', ''),
            'charset': 'utf8mb4',
            'autocommit': False
        }
    
    def connect(self):
        """Create a new database connection"""
        try:
            self._connection = pymysql.connect(**self.config)
        except Exception as e:
            print(f"Error connecting to MySQL: {str(e)}")
            raise
    
    def get_connection(self):
        """Get or create database connection (serverless-friendly)"""
        try:
            if self._connection is None:
                self.connect()
            else:
                # Test if connection is still alive
                # In serverless, connections may be closed between invocations
                try:
                    self._connection.ping(reconnect=False)
                except Exception:
                    # Connection lost, reconnect
                    self._connection = None
                    self.connect()
        except Exception as e:
            # Connection lost, reconnect
            print(f"Connection error, reconnecting: {str(e)}")
            self._connection = None
            try:
                self.connect()
            except Exception as reconnect_error:
                # If reconnection fails, raise a more descriptive error
                print(f"Failed to reconnect to database: {str(reconnect_error)}")
                raise ConnectionError(f"Database connection failed: {str(reconnect_error)}") from reconnect_error
        return self._connection
    
    def commit(self):
        """Commit the current transaction"""
        conn = self.get_connection()
        if conn:
            conn.commit()
    
    def rollback(self):
        """Rollback the current transaction"""
        conn = self.get_connection()
        if conn:
            conn.rollback()
    
    def close(self):
        """Close the database connection"""
        if self._connection:
            try:
                self._connection.close()
            except:
                pass
            self._connection = None

# MySQL Configuration
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', '1239')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'bus_management')

mysql = MySQL(app)

# Connection wrapper to make mysql.connection work like Flask-MySQLdb
class ConnectionWrapper:
    """Wrapper to make mysql.connection work like Flask-MySQLdb"""
    def __init__(self, mysql_instance):
        self.mysql = mysql_instance
    
    def cursor(self):
        """Get a cursor from the connection"""
        try:
            conn = self.mysql.get_connection()
            return conn.cursor()
        except Exception as e:
            print(f"Error getting cursor: {str(e)}")
            raise
    
    def commit(self):
        """Commit the transaction"""
        self.mysql.commit()
    
    def rollback(self):
        """Rollback the transaction"""
        self.mysql.rollback()

# Replace mysql.connection with wrapper
mysql.connection = ConnectionWrapper(mysql)

# Create required tables if they don't exist
def init_db():
    with app.app_context():
        cur = mysql.connection.cursor()
        try:
            # Drop existing transactions table if it exists
            cur.execute('DROP TABLE IF EXISTS transactions')
            
            # Create transactions table
            cur.execute('''
                CREATE TABLE transactions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    amount DECIMAL(10,2) NOT NULL,
                    transaction_type ENUM('credit', 'debit') NOT NULL,
                    description VARCHAR(255),
                    bus_number VARCHAR(20),
                    location VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user(id)
                )
            ''')

            # Create feedback table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS feedback (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    feedback_type ENUM('service', 'bus', 'driver', 'schedule', 'other') NOT NULL,
                    rating INT NOT NULL,
                    feedback_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user(id)
                )
            ''')
            mysql.connection.commit()
            print("Database tables initialized successfully")
        except Exception as e:
            print(f"Error creating tables: {str(e)}")
        finally:
            cur.close()

# Initialize database tables only once (lazy initialization for serverless)
# Don't call init_db() at module level - it will fail in serverless cold starts
# Instead, initialize on first request or use a separate migration script
_db_initialized = False

def ensure_db_initialized():
    """Lazy initialization of database tables - only runs when needed"""
    global _db_initialized
    if not _db_initialized:
        try:
            init_db()
            _db_initialized = True
        except Exception as e:
            print(f"Warning: Database initialization failed: {str(e)}")
            # Don't fail the app if DB init fails - tables might already exist

# Flask before_request hook to ensure DB is initialized for routes that need it
@app.before_request
def before_request():
    """Ensure database is initialized before handling requests"""
    # Only initialize if we're accessing a route that needs the database
    # Skip for static files and simple routes
    # Wrap in try-except to prevent function invocation failures
    try:
        if request.endpoint and request.endpoint not in ['static', 'generate_qr']:
            ensure_db_initialized()
    except Exception as e:
        # Log error but don't fail the request - let individual routes handle DB errors
        print(f"Warning: Database initialization skipped: {str(e)}")
        # Don't raise - allow the request to continue
        # Individual routes will handle their own DB connection errors

# Helper function to calculate distance
def calculate_distance(address):
    distances = {
        'Kundapura': 30,
        'Udupi': 8.5,
        'Manipal': 12,
        'Brahmavar': 15,
        'Mangalore': 25
    }
    for location, distance in distances.items():
        if location.lower() in address.lower():
            return distance
    return 10

@app.route('/')
def index():
    return render_template('base.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            usn = request.form['usn']
            name = request.form['name']
            phone = request.form['phone']
            email = request.form['email']
            password = request.form['password']
            bus_number = request.form.get('bus_number')
            address = request.form['address']
            
            distance = calculate_distance(address)
            hashed_password = generate_password_hash(password)
            
            cur = mysql.connection.cursor()
            cur.execute('''
                INSERT INTO user (usn, name, phone, email, password, bus_number, address, distance, balance)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (usn, name, phone, email, hashed_password, bus_number, address, distance, 0))
            mysql.connection.commit()
            cur.close()
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash('Registration failed. Please try again.', 'error')
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usn = request.form['usn']
        password = request.form['password']
        
        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM user WHERE usn = %s', (usn,))
        user = cur.fetchone()
        cur.close()
        
        if user and check_password_hash(user[5], password):
            session['user_id'] = user[0]
            session['usn'] = user[1]
            session['name'] = user[2]
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid USN or password', 'error')
    
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    
    try:
        # Get user details
        cur.execute('''
            SELECT id, usn, name, phone, email, bus_number, address, balance 
            FROM user 
            WHERE id = %s
        ''', (session['user_id'],))
        user = cur.fetchone()
        
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('login'))
        
        # Get all available buses
        cur.execute('''
            SELECT bus_number, starting_point, ending_point, total_seats, available_seats, fare
            FROM bus 
            WHERE available_seats > 0
        ''')
        buses = cur.fetchall()
        
        # Convert user tuple to dictionary for easier template access
        user_dict = {
            'id': user[0],
            'usn': user[1],
            'name': user[2],
            'phone': user[3],
            'email': user[4],
            'bus_number': user[5],
            'address': user[6],
            'balance': user[7]
        }
        
        # Convert bus tuples to dictionaries
        bus_list = []
        for bus in buses:
            bus_dict = {
                'bus_number': bus[0],
                'starting_point': bus[1],
                'ending_point': bus[2],
                'total_seats': bus[3],
                'seats_left': bus[4],
                'fare': bus[5]
            }
            bus_list.append(bus_dict)
        
        return render_template('dashboard.html', user=user_dict, buses=bus_list)
        
    except Exception as e:
        print(f"Error in dashboard: {str(e)}")
        flash('An error occurred while loading the dashboard', 'error')
        return redirect(url_for('login'))
    finally:
        cur.close()

@app.route('/topup', methods=['GET', 'POST'])
def topup():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    try:
        # Get current balance
        cur.execute('SELECT balance FROM user WHERE id = %s', (session['user_id'],))
        result = cur.fetchone()
        if not result:
            flash('User not found', 'error')
            return redirect(url_for('login'))
        
        current_balance = float(result[0]) if result[0] is not None else 0.0
        
        if request.method == 'POST':
            try:
                amount = float(request.form['amount'])
                payment_method = request.form.get('payment_method', 'UPI')
                
                if amount <= 0:
                    flash('Please enter a valid amount greater than 0', 'error')
                    return render_template('topup.html', balance=current_balance)
                
                # Update balance
                new_balance = current_balance + amount
                cur.execute('UPDATE user SET balance = %s WHERE id = %s', (new_balance, session['user_id']))
                
                # Add to transaction history
                cur.execute('''
                    INSERT INTO transactions 
                    (user_id, amount, transaction_type, description, bus_number, location, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ''', (session['user_id'], amount, 'credit', f'Top up via {payment_method}', 'N/A', 'N/A'))
                
                mysql.connection.commit()
                
                # Update session with new balance
                session['balance'] = new_balance
                
                # Show success message and stay on the same page
                flash(f'Top up successful! ₹{amount:.2f} added to your account. New balance: ₹{new_balance:.2f}', 'success')
                return render_template('topup.html', balance=new_balance)
                
            except ValueError:
                flash('Please enter a valid amount', 'error')
            except Exception as e:
                print(f"Error in topup: {str(e)}")
                flash('An error occurred. Please try again.', 'error')
                mysql.connection.rollback()
        
        return render_template('topup.html', balance=current_balance)
    except Exception as e:
        print(f"Error in topup route: {str(e)}")
        flash('An error occurred. Please try again.', 'error')
        return redirect(url_for('dashboard'))
    finally:
        cur.close()

@app.route('/qr_scan')
def qr_scan():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('qr.html')

@app.route('/view_transactions')
def view_transactions():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    try:
        # Get all transactions with full details
        cur.execute('''
            SELECT 
                id,
                amount,
                transaction_type,
                description,
                bus_number,
                location,
                created_at
            FROM transactions 
            WHERE user_id = %s 
            ORDER BY created_at DESC
        ''', (session['user_id'],))
        
        transactions = []
        for t in cur.fetchall():
            transaction = {
                'id': t[0],
                'amount': float(t[1]),
                'transaction_type': t[2],
                'description': t[3],
                'bus_number': t[4],
                'location': t[5],
                'created_at': t[6]
            }
            transactions.append(transaction)
            print(f"Found transaction: {transaction}")  # Debug logging
        
        if not transactions:
            print("No transactions found for user")  # Debug logging
            flash('No transactions found', 'info')
        
        return render_template('transaction.html', transactions=transactions)
    except Exception as e:
        print(f"Error in view_transactions: {str(e)}")  # Debug logging
        flash('An error occurred while loading transactions', 'error')
        return redirect(url_for('dashboard'))
    finally:
        cur.close()

@app.route('/view_bus_location')
def view_bus_location():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('map.html')

@app.route('/book_bus/<int:bus_id>', methods=['GET', 'POST'])
def book_bus(bus_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    try:
        # Get bus details
        cur.execute('SELECT * FROM bus WHERE bus_number = %s', (bus_id,))
        bus = cur.fetchone()
        
        if not bus:
            flash('Bus not found', 'error')
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            try:
                seats = int(request.form['seats'])
                
                # Validate seats
                if seats <= 0:
                    flash('Please enter a valid number of seats', 'error')
                    return render_template('booking.html', bus=bus)
                
                if seats > bus[4]:  # available_seats
                    flash(f'Only {bus[4]} seats available', 'error')
                    return render_template('booking.html', bus=bus)
                
                # Update available seats
                cur.execute('UPDATE bus SET available_seats = available_seats - %s WHERE bus_number = %s', 
                          (seats, bus_id))
                
                mysql.connection.commit()
                
                # Show success message and updated bus info
                flash(f'Successfully booked {seats} seat(s) for Bus {bus_id}! Remember to scan the QR code at the bus stop to pay the fare.', 'success')
                
                # Get updated bus info
                cur.execute('SELECT * FROM bus WHERE bus_number = %s', (bus_id,))
                updated_bus = cur.fetchone()
                
                return render_template('booking.html', bus=updated_bus)
                
            except ValueError:
                flash('Please enter a valid number of seats', 'error')
            except Exception as e:
                print(f"Error in booking: {str(e)}")
                flash('An error occurred while booking. Please try again.', 'error')
                mysql.connection.rollback()
        
        return render_template('booking.html', bus=bus)
        
    except Exception as e:
        print(f"Error in book_bus route: {str(e)}")
        flash('An error occurred. Please try again.', 'error')
        return redirect(url_for('dashboard'))
    finally:
        cur.close()

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/generate-qr')
def generate_qr():
    # Create QR code with bus information
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    # Bus information to encode
    bus_info = {
        'bus_number': '1',
        'location': 'Udupi'
    }
    
    # Convert to JSON string
    qr.add_data(json.dumps(bus_info))
    qr.make(fit=True)
    
    # Create an image from the QR Code
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save the image to a BytesIO object
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    return send_file(img_io, mimetype='image/png')

@app.route('/scan-qr', methods=['POST'])
def scan_qr():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first'})
    
    try:
        data = request.get_json()
        if not data or 'bus_number' not in data:
            return jsonify({'success': False, 'message': 'Invalid request data'})
        
        # Parse the QR code data safely
        try:
            # The QR code data should be a string representation of a dictionary
            bus_info_str = data['bus_number'].replace("'", '"')  # Replace single quotes with double quotes
            bus_info = json.loads(bus_info_str)
        except json.JSONDecodeError:
            return jsonify({'success': False, 'message': 'Invalid QR code format'})
        
        if not isinstance(bus_info, dict) or 'bus_number' not in bus_info:
            return jsonify({'success': False, 'message': 'Invalid QR code data'})
        
        cur = mysql.connection.cursor()
        
        # Get user's current balance
        cur.execute('SELECT balance FROM user WHERE id = %s', (session['user_id'],))
        user_data = cur.fetchone()
        if not user_data:
            return jsonify({'success': False, 'message': 'User not found'})
        
        current_balance = float(user_data[0]) if user_data[0] is not None else 0.0
        
        # Get bus fare from database
        cur.execute('SELECT fare FROM bus WHERE bus_number = %s', (bus_info['bus_number'],))
        bus_data = cur.fetchone()
        if not bus_data:
            return jsonify({'success': False, 'message': 'Bus not found'})
        
        fare = float(bus_data[0])
        location = bus_info.get('location', 'Unknown')
        bus_number = bus_info.get('bus_number', 'Unknown')
        
        if current_balance < fare:
            return jsonify({'success': False, 'message': f'Insufficient balance. Required: ₹{fare}, Available: ₹{current_balance}'})
        
        # Deduct fare and record transaction
        new_balance = current_balance - fare
        cur.execute('UPDATE user SET balance = %s WHERE id = %s', (new_balance, session['user_id']))
        
        # Record transaction
        cur.execute('''
            INSERT INTO transactions (user_id, amount, transaction_type, description, bus_number, location)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (session['user_id'], fare, 'debit', f'Bus fare payment - {location}', bus_number, location))
        
        mysql.connection.commit()
        cur.close()
        
        return jsonify({
            'success': True, 
            'message': f'Fare of ₹{fare} deducted successfully for Bus {bus_number} from {location}'
        })
        
    except Exception as e:
        print(f"Error in scan_qr: {str(e)}")
        return jsonify({'success': False, 'message': f'Error processing QR code: {str(e)}'})

@app.route('/view-qr-code')
def view_qr_code():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('qr_code.html')

@app.route('/respond-notification', methods=['POST'])
def respond_notification():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    notification_id = request.form.get('notification_id')
    response = request.form.get('response')
    
    cur = mysql.connection.cursor()
    try:
        if response == 'yes':
            # Check if seats are available
            cur.execute('SELECT available_seats FROM bus WHERE bus_number = %s', (session.get('bus_number'),))
            available_seats = cur.fetchone()[0]
            
            if available_seats > 0:
                # Update available seats
                cur.execute('UPDATE bus SET available_seats = available_seats - 1 WHERE bus_number = %s', 
                          (session.get('bus_number'),))
                mysql.connection.commit()
                flash('Your seat has been confirmed!', 'success')
            else:
                # Show alternative buses
                cur.execute('SELECT * FROM bus WHERE route_from = %s AND route_to = %s AND bus_number != %s AND available_seats > 0', 
                          (session.get('route_from'), session.get('route_to'), session.get('bus_number')))
                alternative_buses = cur.fetchall()
                flash('Your regular bus is full. Please select an alternative bus.', 'warning')
                return render_template('notification.html', alternative_buses=alternative_buses)
        else:
            flash('You have declined to board the bus today.', 'info')
        
        return redirect(url_for('notification'))
        
    except Exception as e:
        print(f"Error in respond_notification: {str(e)}")
        flash('An error occurred. Please try again.', 'error')
        return redirect(url_for('notification'))
    finally:
        cur.close()

@app.route('/select-alternative-bus/<int:bus_number>', methods=['POST'])
def select_alternative_bus(bus_number):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    try:
        # Check if seats are available in the alternative bus
        cur.execute('SELECT available_seats FROM bus WHERE bus_number = %s', (bus_number,))
        available_seats = cur.fetchone()[0]
        
        if available_seats > 0:
            # Update available seats
            cur.execute('UPDATE bus SET available_seats = available_seats - 1 WHERE bus_number = %s', 
                      (bus_number,))
            mysql.connection.commit()
            flash(f'Successfully booked seat in Bus {bus_number}!', 'success')
        else:
            flash('Sorry, this bus is now full. Please try another alternative.', 'error')
        
        return redirect(url_for('notification'))
        
    except Exception as e:
        print(f"Error in select_alternative_bus: {str(e)}")
        flash('An error occurred. Please try again.', 'error')
        return redirect(url_for('notification'))
    finally:
        cur.close()

@app.route('/notification')
def notification():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    try:
        # Get user's bus details
        cur.execute('SELECT bus_number FROM user WHERE id = %s', (session['user_id'],))
        user_bus = cur.fetchone()
        
        if user_bus:
            session['bus_number'] = user_bus[0]
        
        return render_template('notification.html')
    except Exception as e:
        print(f"Error in notification route: {str(e)}")
        flash('An error occurred while loading notifications', 'error')
        return redirect(url_for('dashboard'))
    finally:
        cur.close()

@app.route('/test-db')
def test_db():
    try:
        cur = mysql.connection.cursor()
        cur.execute('SELECT 1')
        result = cur.fetchone()
        cur.close()
        return jsonify({'status': 'success', 'message': 'Database connection successful'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/view-db')
def view_db():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    try:
        # Get user table contents
        cur.execute('SELECT * FROM user')
        users = cur.fetchall()
        
        # Get transactions table contents
        cur.execute('SELECT * FROM transactions')
        transactions = cur.fetchall()
        
        # Get bus table contents
        cur.execute('SELECT * FROM bus')
        buses = cur.fetchall()
        
        return render_template('view_db.html', 
                             users=users, 
                             transactions=transactions, 
                             buses=buses)
    except Exception as e:
        print(f"Error viewing database: {str(e)}")
        flash('Error viewing database', 'error')
        return redirect(url_for('dashboard'))
    finally:
        cur.close()

@app.route('/print-db')
def print_db():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    try:
        print("\n=== USERS TABLE ===")
        cur.execute('SELECT * FROM user')
        users = cur.fetchall()
        for user in users:
            print(f"ID: {user[0]}, USN: {user[1]}, Name: {user[2]}, Phone: {user[3]}, Email: {user[4]}, Bus: {user[6]}, Balance: {user[8]}")
        
        print("\n=== TRANSACTIONS TABLE ===")
        cur.execute('SELECT * FROM transactions')
        transactions = cur.fetchall()
        for trans in transactions:
            print(f"ID: {trans[0]}, User: {trans[1]}, Amount: {trans[2]}, Type: {trans[3]}, Desc: {trans[4]}, Bus: {trans[5]}, Location: {trans[6]}, Date: {trans[7]}")
        
        print("\n=== BUS TABLE ===")
        cur.execute('SELECT * FROM bus')
        buses = cur.fetchall()
        for bus in buses:
            print(f"Bus: {bus[0]}, From: {bus[1]}, To: {bus[2]}, Total Seats: {bus[3]}, Available: {bus[4]}, Fare: {bus[5]}")
        
        return "Database contents printed to console. Check your terminal."
    except Exception as e:
        print(f"Error printing database: {str(e)}")
        return f"Error: {str(e)}"
    finally:
        cur.close()

@app.route('/submit-feedback', methods=['POST'])
def submit_feedback():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        feedback_type = request.form['feedback_type']
        rating = int(request.form['rating'])
        feedback_text = request.form['feedback_text']
        
        cur = mysql.connection.cursor()
        cur.execute('''
            INSERT INTO feedback (user_id, feedback_type, rating, feedback_text)
            VALUES (%s, %s, %s, %s)
        ''', (session['user_id'], feedback_type, rating, feedback_text))
        
        mysql.connection.commit()
        cur.close()
        
        flash('Thank you for your feedback!', 'success')
    except Exception as e:
        print(f"Error submitting feedback: {str(e)}")
        flash('Error submitting feedback. Please try again.', 'error')
    
    return redirect(url_for('dashboard'))

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle internal server errors gracefully"""
    print(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred'}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Global exception handler to prevent FUNCTION_INVOCATION_FAILED"""
    print(f"Unhandled exception: {str(e)}")
    # Return a proper response instead of letting the exception propagate
    # This prevents FUNCTION_INVOCATION_FAILED errors on Vercel
    try:
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({'error': 'An error occurred', 'message': str(e)}), 500
        flash('An error occurred. Please try again.', 'error')
        return redirect(url_for('index'))
    except Exception:
        # Fallback if even error handling fails
        return jsonify({'error': 'Internal server error'}), 500

# Export handler for Vercel serverless functions
# Vercel Python runtime expects a WSGI application
# The handler must be the Flask app instance
# For Render, gunicorn will use: gunicorn app:app
handler = app

# For local development
if __name__ == '__main__':
    app.run(debug=True) 