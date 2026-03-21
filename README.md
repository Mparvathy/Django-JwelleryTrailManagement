# 💎 Jewellery Trail Management

A full-stack **Django** web application for a jewellery e-commerce platform with **AI-powered Virtual Try-On** using MediaPipe pose detection. Inspired by Tanishq's design language.

---

## ✨ Features

### 👤 User
- Register & Login with custom user model
- Personal Dashboard — cart summary, stats, quick links
- Browse jewellery by category
- Add to Cart / Remove / Update quantity
- **Virtual Try-On** — live camera with AI overlay of necklaces & earrings
- Size adjustment slider for jewellery overlay
- Capture & download try-on photo

### 🛡️ Admin
- Secure admin login (superuser only)
- Add / Edit / Delete Categories
- Add / Edit / Delete Products (with image upload)
- Manage product stock & active status

### 🤖 AI Try-On
- Real-time pose detection using **MediaPipe**
- Necklace overlay on shoulder/neck landmarks
- Earring overlay on ear landmarks
- White background removal from jewellery images
- Live camera stream via MJPEG

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 5.2 |
| Database | PostgreSQL |
| AI / CV | MediaPipe, OpenCV, Pillow |
| Frontend | HTML, CSS |
| Auth | Django Custom User Model |
| Media | Django Media Files |

---

## 📁 Project Structure

```
Jwellery Trail Management/
└── project/
    ├── app/
    │   ├── models.py          # customuser, Category, Product, Cart
    │   ├── views.py           # All views including AI stream
    │   ├── urls.py            # URL routing
    │   ├── context_processors.py
    │   └── migrations/
    ├── templates/
    │   ├── base.html          # Public base (guest users)
    │   ├── base2.html         # User base with navbar
    │   ├── home.html
    │   ├── menu.html          # Shop page with sidebar + product grid
    │   ├── tryon.html         # Virtual try-on with camera
    │   ├── tryon_page.html    # Single product try-on page
    │   ├── userdashboard.html # User dashboard
    │   ├── cart.html
    │   ├── register.html
    │   ├── userlogin.html
    │   ├── adminlogin.html
    │   ├── base1.html         # Admin base
    │   ├── add_category.html
    │   ├── manage_categories.html
    │   ├── add_product.html
    │   ├── manage_products.html
    │   └── edit_product.html
    ├── media/
    │   └── products/          # Uploaded product images
    ├── project/
    │   ├── settings.py
    │   └── urls.py
    └── manage.py
```

---

## ⚙️ Setup & Installation

### 1. Clone the repository
```bash
git clone <your-repo-url>
cd "Jwellery Trail Management"
```

### 2. Create virtual environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
```

### 3. Install dependencies
```bash
pip install django psycopg2-binary opencv-python mediapipe pillow numpy
```

### 4. Configure PostgreSQL

Create a database and update `project/settings.py`:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'tanishq_db',
        'USER': '<your_db_user>',
        'PASSWORD': '<your_db_password>',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### 5. Run migrations
```bash
cd project
python manage.py makemigrations
python manage.py migrate
```

### 6. Create superuser (Admin)
```bash
python manage.py createsuperuser
```
> After creating, set `is_superuser=True` via Django shell or admin panel.

### 7. Run the server
```bash
python manage.py runserver
```

Visit: **http://127.0.0.1:8000**

---

## 🔗 URL Routes

| URL | View | Description |
|-----|------|-------------|
| `/` | `home` | Landing page |
| `/menu/` | `menu` | Shop collections |
| `/tryon/` | `tryon` | Virtual try-on page |
| `/tryon/stream/<id>/` | `tryon_stream` | MJPEG camera stream |
| `/tryon/stop/` | `tryon_stop` | Stop camera |
| `/cart/` | `cart` | View cart |
| `/cart/add/<id>/` | `add_to_cart` | Add product to cart |
| `/cart/remove/<id>/` | `remove_from_cart` | Remove from cart |
| `/cart/update/<id>/` | `update_cart` | Update quantity |
| `/register/` | `register` | User registration |
| `/login/` | `userlogin` | User login |
| `/dashboard/` | `userdashboard` | User dashboard |
| `/logout/` | `userlogout` | User logout |
| `/adminlogin/` | `adminlogin` | Admin login |
| `/admindashboard/` | `admindashboard` | Admin dashboard |
| `/add-category/` | `add_category` | Add category |
| `/manage-categories/` | `manage_categories` | Manage categories |
| `/myadmin/add-product/` | `add_product` | Add product |
| `/manage-products/` | `manage_products` | Manage products |

---

## 🗄️ Database Models

### `customuser`
| Field | Type |
|-------|------|
| username | CharField |
| email | EmailField |
| phone | CharField |
| first_name | CharField |
| is_user | BooleanField |
| is_admin | BooleanField |

### `Category`
| Field | Type |
|-------|------|
| name | CharField (unique) |
| description | TextField |
| created_at | DateTimeField |

### `Product`
| Field | Type |
|-------|------|
| category | ForeignKey → Category |
| name | CharField |
| description | TextField |
| price | DecimalField |
| stock | PositiveIntegerField |
| image | ImageField |
| is_active | BooleanField |

### `Cart`
| Field | Type |
|-------|------|
| user | ForeignKey → customuser |
| product | ForeignKey → Product |
| quantity | PositiveIntegerField |
| added_at | DateTimeField |

---

## 🤖 Virtual Try-On — How It Works

1. User clicks **Try On** on any product
2. Camera opens and streams via `/tryon/stream/<product_id>/`
3. Each frame is processed:
   - **MediaPipe Pose Landmarker** detects body landmarks
   - Product name is checked → `earring` keywords → earring mode, else necklace mode
   - **Necklace**: overlay placed between mouth and shoulders using landmarks 9, 10, 11, 12
   - **Earring**: overlay placed at ear lobes using landmarks 7, 8
   - White background removed from jewellery image using PIL
4. Frames are JPEG-encoded and streamed as MJPEG
5. User can adjust size with slider and capture a photo

---

## 🎨 Design

- Inspired by **Tanishq** jewellery brand
- Dark gold (`#FFD700`, `#B8860B`) + black navbar
- Warm brown (`#8B5E3C`) accent for user pages
- Sidebar + product grid layout for shop/try-on pages
- Responsive — works on mobile, tablet, desktop
- Smooth animations, ripple effects, page loader

---

## 📦 Requirements

```
django>=5.2
psycopg2-binary
opencv-python
mediapipe
pillow
numpy
```

---

## 🔒 Security Notes

> Before deploying to production:
- Change `SECRET_KEY` in `settings.py`
- Set `DEBUG = False`
- Add your domain to `ALLOWED_HOSTS`
- Use environment variables for DB credentials
- Run `python manage.py collectstatic`

---

## 👩‍💻 Author

Built with ❤️ using Django + MediaPipe
