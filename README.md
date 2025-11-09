# College Bus Reservation System

A web-based bus reservation system for college students and staff, allowing them to book bus seats, manage their reservations, and handle payments through a QR code-based system.

## Features

- User Registration and Login
- Bus Seat Booking
- QR Code-based Fare Payment
- Transaction History
- Balance Top-up
- Real-time Notifications
- Responsive Design

## Prerequisites

- Python 3.8 or higher
- MySQL 5.7 or higher
- pip (Python package manager)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd bus-reservation-system
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up the MySQL database:
- Create a new database named `bus_management`
- Import the database schema from `database.sql`

5. Configure the application:
- Update the MySQL configuration in `app.py` with your database credentials
- Set a secure secret key in the Flask application

## Running the Application

1. Start the Flask development server:
```bash
python app.py
```

2. Open your web browser and navigate to:
```
http://localhost:5000
```

## Usage

1. Register a new account using your USN
2. Log in to access the dashboard
3. Book bus seats from available buses
4. Top up your balance for fare payments
5. Scan QR codes at bus stops to pay fares
6. View your transaction history
7. Respond to boarding notifications

## Security Features

- Password hashing
- Session management
- Input validation
- SQL injection prevention
- XSS protection

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 