# Jewelry Trail Management System

A comprehensive Django-based e-commerce platform for jewelry sales with an innovative **AR Virtual Try-On** feature that allows customers to visualize products before purchasing.

## 🎯 Overview

This project is a full-featured jewelry e-commerce management system designed for both customers and administrators. It includes product catalog management, shopping cart functionality, order processing, and a unique augmented reality (AR) feature for virtually trying on jewelry items using a webcam.

## ✨ Key Features

### For Customers
- **User Authentication**: Secure registration, login, and OTP verification
- **Product Browsing**: Browse jewelry products by category with detailed descriptions
- **Shopping Cart**: Add/remove products and manage quantities
- **Wishlist**: Save favorite items for later purchase
- **Virtual Try-On (AR)**: Try on jewelry items in real-time using your webcam:
  - 👗 **Necklace Try-On**: Realistic necklace placement around the neck
  - 💍 **Earrings Try-On**: Individual earring visualization on both ears
  - 🎀 **Maang Tikka Try-On**: Traditional Indian jewelry placement
- **Checkout & Payments**: Complete purchase process with multiple payment methods
- **Order Management**: View order history, track orders, and download invoices
- **User Profile**: Manage personal information and shipping addresses

### For Administrators
- **Dashboard**: Overview of sales, users, and orders
- **Product Management**: Add, edit, and delete products with image uploads
- **Category Management**: Organize products into categories
- **Order Management**: View all orders, update order status, and add comments
- **User Management**: View all registered users and their details
- **Invoice Generation**: Generate and print PDF invoices for orders

## 🛠 Tech Stack

**Backend**
- Django 3.x/4.x - Web framework
- Python 3.8+ - Programming language
- SQLite - Database (development)

**Frontend**
- HTML5 / CSS3
- JavaScript
- Bootstrap (implied from template structure)

**AI/Computer Vision Libraries**
- MediaPipe - Pose and face detection for AR features
- OpenCV (cv2) - Video processing
- PIL (Pillow) - Image manipulation
- NumPy - Numerical computations

**Additional Libraries**
- ReportLab - PDF generation for invoices
- Requests - HTTP requests

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment (recommended)

### Setup Instructions

1. **Clone the repository**
   ```bash
   cd "Jwellery Trail Management -Latest"
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment**
   - **Windows**:
     ```bash
     venv\Scripts\activate
     ```
   - **macOS/Linux**:
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies**
   ```bash
   pip install django pillow opencv-python mediapipe numpy reportlab requests
   ```

5. **Run migrations**
   ```bash
   cd project
   python manage.py migrate
   ```

6. **Create superuser (admin account)**
   ```bash
   python manage.py createsuperuser
   ```

7. **Start development server**
   ```bash
   python manage.py runserver
   ```

8. **Access the application**
   - User portal: `http://localhost:8000/`
   - Admin portal: `http://localhost:8000/adminlogin/`

## 📁 Project Structure

```
project/
├── manage.py                 # Django management script
├── db.sqlite3               # SQLite database
├── app/                     # Main application
│   ├── models.py           # Database models
│   ├── views.py            # View functions and AR logic
│   ├── urls.py             # URL routing
│   ├── admin.py            # Admin configuration
│   ├── email_utils.py      # Email notification functions
│   ├── signals.py          # Django signals
│   ├── migrations/         # Database migrations
│   └── tests.py            # Unit tests
├── project/                # Django settings
│   ├── settings.py         # Project configuration
│   ├── urls.py             # Main URL patterns
│   ├── wsgi.py             # WSGI configuration
│   └── asgi.py             # ASGI configuration
├── templates/              # HTML templates
│   ├── base.html           # Base template
│   ├── home.html           # Homepage
│   ├── cart.html           # Shopping cart
│   ├── checkout.html       # Checkout page
│   ├── tryon.html          # AR try-on interface
│   ├── admindashboard.html # Admin dashboard
│   ├── manage_products.html # Product management
│   ├── manage_categories.html # Category management
│   ├── admin_orders.html   # Order management
│   ├── emails/             # Email templates
│   └── ...
└── media/                  # User-uploaded files
    └── products/           # Product images
```

## 💾 Database Models

### User Model (customuser)
- Extends Django's AbstractUser
- Additional fields: phone, is_admin, is_user

### Category Model
- name, description, created_at
- For organizing jewelry products

### Product Model
- category, name, description, price, stock
- image, is_active, created_at, updated_at
- Methods: is_in_stock()

### Cart Model
- user, product, quantity, added_at
- Unique constraint on (user, product)
- Method: subtotal()

### Wishlist Model
- user, product, added_at
- Unique constraint on (user, product)

### Order Model
- user, total_amount, payment_method, status
- shipping_address, city, state, pincode, phone_number
- admin_comment, created_at
- Payment methods: UPI, Credit/Debit Card, Cash on Delivery

### OrderItem Model
- order, product, quantity, price
- Links products to orders with purchase details

## 🎥 AR Try-On Features

The system includes computer vision-based AR features that use MediaPipe for real-time pose and face detection:

### Supported Jewelry Types
1. **Necklace**: Places jewelry around the neck area based on shoulder landmarks
2. **Earrings**: Displays separate earrings on both ears with mirror effect support
3. **Maang Tikka**: Traditional Indian jewelry positioned on the forehead

### Technical Implementation
- Real-time video streaming using webcam
- Face and pose landmark detection using MediaPipe
- Image overlay with alpha blending for realistic appearance
- Adjustable jewelry size scaling
- Automatic background removal for better visualization

## 🔐 User Authentication

- **Registration**: New users can register with email verification (OTP)
- **Login**: Secure login with email and password
- **Admin Login**: Separate authentication for administrators
- **Role-Based Access**: Different permissions for users and admins

## 📧 Email Notifications

The system sends automated emails for:
- Order placed confirmation
- Order status updates
- Product back-in-stock notifications
- Price drop alerts
- Wishlist additions

## 💳 Payment Methods

- **UPI**: Unified Payments Interface
- **Credit/Debit Card**: Online card payments
- **Cash on Delivery (COD)**: Pay at delivery

## 📄 Invoice Generation

- Generate PDF invoices for orders
- Print-friendly invoice format
- Contains order details, items, and total amount
- Uses ReportLab for PDF generation

## 🚀 Usage Guide

### For Customers

1. **Register/Login**: Create an account or log in
2. **Browse Products**: Explore jewelry by category
3. **Virtual Try-On**: Click the try-on button to see jewelry in AR
4. **Add to Cart**: Add desired items to shopping cart
5. **Checkout**: Proceed to payment
6. **Track Orders**: View order history and status

### For Administrators

1. **Login**: Use admin credentials
2. **Manage Inventory**: Add, edit, or delete products
3. **Manage Categories**: Organize products into categories
4. **View Orders**: Monitor all customer orders
5. **Update Status**: Update order fulfillment status
6. **View Users**: See all registered customers
7. **Print Orders**: Generate batch invoices

## 🔧 Configuration

Key settings in `project/settings.py`:
- Database configuration
- Installed apps
- Middleware
- Template settings
- Static files and media directories
- Email configuration
- Authentication backend

## 📱 Responsive Design

The application uses a multi-template approach for different user experiences:
- `base.html` - Main layout
- `base1.html`, `base2.html`, `base3.html` - Alternative layouts for different sections

## 🐛 Troubleshooting

### Webcam Issues
- Ensure your browser has permission to access the webcam
- Check camera driver installation
- Try a different browser

### Image Upload Issues
- Verify media directory permissions
- Check disk space availability
- Ensure supported image formats (JPEG, PNG, AVIF)

### Database Issues
- Run migrations: `python manage.py migrate`
- Clear cache if experiencing stale data issues

## 📝 Future Enhancements

- Payment gateway integration (Razorpay, Stripe)
- Real 3D model rendering for jewelry
- Inventory alerts and reorder automation
- Advanced analytics dashboard
- Mobile app version
- Video tutorials for try-on feature

## 📄 License

This project is developed for jewelry store management and AR visualization.

## 👥 Support

For issues, questions, or suggestions, please refer to the project documentation or contact the development team.

---

**Version**: 1.0.0  
**Last Updated**: May 2026  
**Status**: Active Development
