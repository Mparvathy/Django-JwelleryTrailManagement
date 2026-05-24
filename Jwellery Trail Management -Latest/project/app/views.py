from django.shortcuts import render, redirect, get_object_or_404
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
import requests
from django.http import StreamingHttpResponse, JsonResponse, HttpResponse
from django.db import models
from django.db.models import Prefetch
from  .models import Category, Product, customuser, Cart, Wishlist, Order, OrderItem
from .email_utils import send_order_confirmation_email, send_order_status_email
import cv2
import numpy as np
from PIL import Image
import re
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
import mediapipe as mp
import random

camera_state = {'running': False}

def remove_white_bg(img_path, threshold=230):
    img  = Image.open(img_path).convert("RGBA")
    data = np.array(img)
    r, g, b, a = data[:,:,0], data[:,:,1], data[:,:,2], data[:,:,3]
    mask = (r > threshold) & (g > threshold) & (b > threshold)
    data[mask, 3] = 0
    return Image.fromarray(data)

def overlay_image(frame, overlay_pil, x, y, w, h, flip=False):
    if w <= 0 or h <= 0:
        return frame
    overlay = overlay_pil.resize((w, h), Image.LANCZOS)
    if flip:
        overlay = overlay.transpose(Image.FLIP_LEFT_RIGHT)
    ov = np.array(overlay)
    x1, y1 = max(x, 0), max(y, 0)
    x2, y2 = min(x + w, frame.shape[1]), min(y + h, frame.shape[0])
    ow1 = x1 - x
    oy1 = y1 - y
    ow2 = ow1 + (x2 - x1)
    oh2 = oy1 + (y2 - y1)
    if x2 <= x1 or y2 <= y1:
        return frame
    region = frame[y1:y2, x1:x2].astype(float)
    crop   = ov[oy1:oh2, ow1:ow2]
    alpha  = crop[:, :, 3:4] / 255.0
    rgb    = crop[:, :, :3][:, :, ::-1].astype(float)
    frame[y1:y2, x1:x2] = (alpha * rgb + (1 - alpha) * region).astype(np.uint8)
    return frame

def process_necklace(frame, landmarks, jewelry_img, size_scale, W, H):
    lm   = landmarks.landmark
    ls   = lm[11]   
    rs   = lm[12]  
    l_mouth = lm[9]
    r_mouth = lm[10]
    lsX, lsY = int(ls.x * W), int(ls.y * H)
    rsX, rsY = int(rs.x * W), int(rs.y * H)
    mouthY    = int(((l_mouth.y + r_mouth.y) / 2) * H)
    shoulderY = (lsY + rsY) // 2
    neck_cx    = (lsX + rsX) // 2
    shoulder_w = abs(lsX - rsX)
    jw_w = int(shoulder_w * 0.75 * size_scale)
    jw_h = int(jw_w * (jewelry_img.height / max(jewelry_img.width, 1)))
    neck_base_y = mouthY + int((shoulderY - mouthY) * 0.05)
    jw_x = neck_cx - jw_w // 2
    return overlay_image(frame, jewelry_img, jw_x, neck_base_y, jw_w, jw_h)

def process_maang_tikka(frame, landmarks, jewelry_img, size_scale, W, H):
    lm = landmarks.landmark
    
    # Use MediaPipe Face Mesh forehead landmarks
    # lm[10] is the top of the forehead/hairline
    # lm[8] is the point between the eyebrows
    # lm[127] and lm[356] are the left and right sides of the upper face
    
    top_forehead = lm[10]
    between_eyes = lm[8]
    left_side = lm[127]
    right_side = lm[356]
    
    # Calculate forehead center and width
    center_x = int(((top_forehead.x + between_eyes.x) / 2) * W)
    bottom_y = int(between_eyes.y * H)
    
    left_x = int(left_side.x * W)
    right_x = int(right_side.x * W)
    face_width = abs(right_x - left_x)
    
    if face_width < 50:
        return frame
    tikka_w = max(int(face_width * 0.15 * size_scale), 15)
    tikka_h = int(tikka_w * (jewelry_img.height / max(jewelry_img.width, 1)))
    bottom_anchor_y = bottom_y - int(face_width * 0.15)
    tikka_x = center_x - (tikka_w // 2)
    tikka_y = bottom_anchor_y - tikka_h
    return overlay_image(frame, jewelry_img, tikka_x, tikka_y, tikka_w, tikka_h)

def process_earring(frame, face_landmarks, pose_landmarks, jewelry_img, size_scale, W, H):
    try:
        if face_landmarks is None:
            return frame
        lm = face_landmarks.landmark
        left_ear  = lm[234]
        right_ear = lm[454]
        nose_tip  = lm[1]
        top_forehead = lm[10]
        chin = lm[152]
        left_x  = int(left_ear.x * W)
        left_y  = int(left_ear.y * H)
        right_x = int(right_ear.x * W)
        right_y = int(right_ear.y * H)
        nose_x  = int(nose_tip.x * W)
        face_h = abs(chin.y - top_forehead.y) * H
        stable_face_w = face_h * 0.75       
        if stable_face_w < 40:
            return frame
        earring_w = max(int(stable_face_w * 0.12 * size_scale), 15)
        earring_h = int(earring_w * jewelry_img.height / max(jewelry_img.width // 2, 1))
        left_half, right_half = split_earring_image(jewelry_img)
        dist_left = abs(nose_x - left_x)
        dist_right = abs(nose_x - right_x)
        is_frontal = abs(dist_left - dist_right) < stable_face_w * 0.2
        if is_frontal:
            frame = overlay_image(frame, left_half,
                                  left_x - earring_w // 2, left_y + int(stable_face_w * 0.1),
                                  earring_w, earring_h, flip=False)
            frame = overlay_image(frame, right_half,
                                  right_x - earring_w // 2, right_y + int(stable_face_w * 0.1),
                                  earring_w, earring_h, flip=True)
        elif dist_left > dist_right:
            # Left ear is visible
            frame = overlay_image(frame, left_half,
                                  left_x - earring_w // 2, left_y + int(stable_face_w * 0.1),
                                  earring_w, earring_h, flip=False)
        else:
            frame = overlay_image(frame, right_half,
                                  right_x - earring_w // 2, right_y + int(stable_face_w * 0.1),
                                  earring_w, earring_h, flip=True)
        return frame

    except Exception as e:
        print(f"Error in process_earring: {e}")
        return frame


    
def _build_face_landmarker():
    import urllib.request, os, tempfile
    model_path = os.path.join(tempfile.gettempdir(), 'face_landmarker.task')
    if not os.path.exists(model_path):
        print("Downloading face landmarker model...")
        urllib.request.urlretrieve('https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task', model_path)
    base_opts = mp_python.BaseOptions(model_asset_path=model_path)
    opts = mp_vision.FaceLandmarkerOptions(
        base_options=base_opts,
        running_mode=mp_vision.RunningMode.VIDEO,
        num_faces=1,
        min_face_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    return mp_vision.FaceLandmarker.create_from_options(opts)

def _build_pose_landmarker():
    import urllib.request, os, tempfile
    model_path = os.path.join(tempfile.gettempdir(), 'pose_landmarker_lite.task')
    if not os.path.exists(model_path):
        print("Downloading pose landmarker model...")
        urllib.request.urlretrieve('https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task',model_path)
    base_opts = mp_python.BaseOptions(model_asset_path=model_path)
    opts = mp_vision.PoseLandmarkerOptions(
        base_options=base_opts,
        running_mode=mp_vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    return mp_vision.PoseLandmarker.create_from_options(opts)

def split_earring_image(jewelry_img):
    w, h = jewelry_img.size
    mid = w // 2
    left  = jewelry_img.crop((0, 0, mid, h))
    right = jewelry_img.crop((mid, 0, w, h))
    return left, right

# def generate_frames(product_id, jewelry_type, size_scale=1.0):
#     import time
#     product = get_object_or_404(Product, pk=product_id)
#     try:
#         jewelry_img = remove_white_bg(product.image.path)
#     except Exception as e:
#         jewelry_img = Image.open(product.image.path).convert("RGBA")

#     pose = _build_pose_landmarker()
#     face = _build_face_landmarker() if jewelry_type == 'earring' else None  # only build if needed

#     cap = cv2.VideoCapture(0)
#     if not cap.isOpened():
#         cap = cv2.VideoCapture(1)
#     cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
#     cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
#     cap.set(cv2.CAP_PROP_FPS, 30)

#     try:
#         while camera_state['running']:
#             ret, frame = cap.read()
#             if not ret:
#                 time.sleep(0.05)
#                 continue

#             frame  = cv2.flip(frame, 1)
#             H, W   = frame.shape[:2]
#             rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#             mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
#             ts_ms  = int(time.time() * 1000)

#             if jewelry_type == 'earring' and face is not None:
#                 face_results = face.detect_for_video(mp_img, ts_ms)
#                 if face_results.face_landmarks:
#                     class _LM:
#                         def __init__(self, lms): self.landmark = lms
#                     face_lm = _LM(face_results.face_landmarks[0])
#                     frame = process_earring(frame, face_lm, None, jewelry_img, size_scale, W, H)
#             else:
#                 pose_results = pose.detect_for_video(mp_img, ts_ms)
#                 if pose_results.pose_landmarks:
#                     class _LM:
#                         def __init__(self, lms): self.landmark = lms
#                     landmarks = _LM(pose_results.pose_landmarks[0])
#                     frame = process_necklace(frame, landmarks, jewelry_img, size_scale, W, H)

#             ret2, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
#             if not ret2:
#                 continue
#             yield (b'--frame\r\n'
#                    b'Content-Type: image/jpeg\r\n\r\n' +
#                    buffer.tobytes() + b'\r\n')
#             time.sleep(0.03)

#     except Exception as e:
#         print(f"Stream error: {e}")
#     finally:
#         cap.release()
#         pose.close()
#         if face:
#             face.close()

def generate_frames(product_id, jewelry_type, size_scale=1.0):
    import time
    product = get_object_or_404(Product, pk=product_id)
    try:
        jewelry_img = remove_white_bg(product.image.path)
    except Exception as e:
        jewelry_img = Image.open(product.image.path).convert("RGBA")

    pose = _build_pose_landmarker()
    face = None
    if jewelry_type in ['earring', 'maang_tikka']:
        try:
            face = _build_face_landmarker()
        except Exception as e:
            print(f"Face landmarker build failed: {e}")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        cap = cv2.VideoCapture(1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    start_time = time.time()  

    try:
        while camera_state['running']:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.05)
                continue
            frame  = cv2.flip(frame, 1)
            H, W   = frame.shape[:2]
            rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            ts_ms  = int((time.time() - start_time) * 1000) 
            try:
                if jewelry_type in ['earring', 'maang_tikka'] and face is not None:
                    face_results = face.detect_for_video(mp_img, ts_ms)
                    if face_results.face_landmarks:
                        class _LM:
                            def __init__(self, lms): self.landmark = lms
                        face_lm = _LM(face_results.face_landmarks[0])
                        if jewelry_type == 'earring':
                            frame = process_earring(frame, face_lm, None, jewelry_img, size_scale, W, H)
                        else:
                            frame = process_maang_tikka(frame, face_lm, jewelry_img, size_scale, W, H)
                else:
                    pose_results = pose.detect_for_video(mp_img, ts_ms)
                    if pose_results.pose_landmarks:
                        class _LM:
                            def __init__(self, lms): self.landmark = lms
                        landmarks = _LM(pose_results.pose_landmarks[0])
                        frame = process_necklace(frame, landmarks, jewelry_img, size_scale, W, H)
            except Exception as e:
                print(f"Detection error (skipping frame): {e}")

            ret2, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ret2:
                continue
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' +
                   buffer.tobytes() + b'\r\n')
            time.sleep(0.03)

    except Exception as e:
        print(f"Stream error: {e}")
    finally:
        cap.release()
        pose.close()
        if face:
            face.close()
        print("Camera released")
            
# ================== Home Page ==================================

def home(request):
    categories = Category.objects.prefetch_related('products').all()
    return render(request, 'home.html', {'categories': categories})

# =================  Menu Collection Page ======================================

def menu(request):
    categories = Category.objects.prefetch_related(
        Prefetch('products', queryset=Product.objects.filter(is_active=True), to_attr='active_products')
    ).all()
    
    wishlist_product_ids = []
    if request.user.is_authenticated:
        wishlist_product_ids = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)
    
    base = 'base3.html' if request.user.is_authenticated and request.user.is_user else 'base.html'
    return render(request, 'menu.html', {
        'categories': categories, 
        'base_template': base,
        'wishlist_product_ids': wishlist_product_ids
    })

# =========================== Cart Functionality ==============================

@login_required(login_url='userlogin')
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    cart_item, created = Cart.objects.get_or_create(user=request.user, product=product)
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    return redirect('cart')

@login_required(login_url='userlogin')
def cart(request):
    items = Cart.objects.filter(user=request.user).select_related('product')
    total = sum(i.subtotal() for i in items)
    return render(request, 'cart.html', {'items': items, 'total': total})

@login_required(login_url='userlogin')
def remove_from_cart(request, cart_id):
    Cart.objects.filter(pk=cart_id, user=request.user).delete()
    return redirect('cart')

@login_required(login_url='userlogin')
def update_cart(request, cart_id):
    if request.method == 'POST':
        qty = int(request.POST.get('quantity', 1))
        item = get_object_or_404(Cart, pk=cart_id, user=request.user)
        if qty > 0:
            item.quantity = qty
            item.save()
        else:
            item.delete()
    return redirect('cart')

# =============================== Display the  Products in respected Category Products ==================================

@login_required(login_url='userlogin')
def category_products(request, category_name):
    category = get_object_or_404(Category, name__iexact=category_name)
    products = Product.objects.filter(category=category, is_active=True)
    return render(request, 'category_products.html', {
        'category': category,
        'products': products,
    })

# ============================= About Page =================================================

def about(request):
    return render(request, 'about.html')

# ==============  Admin login / logout =========================================================

def adminlogin(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admindashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        print(f"Trying login: username={username}")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            print(f"User found: {user}, is_superuser={user.is_superuser}")
            if user.is_superuser:
                login(request, user)
                return redirect('admindashboard')
            else:
                print("User is not superuser")
                return render(request, 'adminlogin.html', {'error': 'You are not authorized as admin.'})
        else:
            print("Authentication failed — wrong username or password")
            return render(request, 'adminlogin.html', {'error': 'Invalid username or password.'})
    return render(request, 'adminlogin.html')

def adminlogout(request):
    logout(request)
    return redirect('adminlogin')

#======================= Admin dashboard ================================================

@login_required(login_url='adminlogin')
def admindashboard(request):
    if not request.user.is_superuser:
        logout(request)
        return redirect('adminlogin')
    
    # Basic Stats
    total_users = customuser.objects.filter(is_user=True).count()
    total_products = Product.objects.count()
    total_categories = Category.objects.count()
    active_products = Product.objects.filter(is_active=True).count()
    
    # Chart Data: Products per Category
    categories_data = Category.objects.annotate(product_count=models.Count('products'))
    category_labels = [cat.name for cat in categories_data]
    category_counts = [cat.product_count for cat in categories_data]
    
    # Chart Data: Stock Distribution (Active vs Inactive)
    stock_status_labels = ['Active', 'Inactive']
    stock_status_counts = [active_products, total_products - active_products]
    
    # Chart Data: Cart vs Wishlist
    total_cart_items = Cart.objects.count()
    total_wishlist_items = Wishlist.objects.count()
    engagement_labels = ['Cart Items', 'Wishlist Items']
    engagement_counts = [total_cart_items, total_wishlist_items]

    context = {
        'total_users': total_users,
        'total_products': total_products,
        'total_categories': total_categories,
        'active_products': active_products,
        'category_labels': category_labels,
        'category_counts': category_counts,
        'stock_status_labels': stock_status_labels,
        'stock_status_counts': stock_status_counts,
        'engagement_labels': engagement_labels,
        'engagement_counts': engagement_counts,
    }
    
    return render(request, 'admindashboard.html', context)

# =======================  Category  =============================================

@login_required(login_url='adminlogin')
def add_category(request):
    if not request.user.is_superuser:
        return redirect('adminlogin')
    if request.method == 'POST':
        name        = request.POST.get('name')
        description = request.POST.get('description')
        if name:
            if Category.objects.filter(name=name).exists():
                return render(request, 'add_category.html', {
                    'error': f'Category "{name}" already exists!'
                })
            Category.objects.create(name=name, description=description)
            return render(request, 'add_category.html', {
                'success': f'Category "{name}" added successfully!'
            })
        else:
            return render(request, 'add_category.html', {
                'error': 'Category name is required.'
            })
    return render(request, 'add_category.html')

@login_required(login_url='adminlogin')
def manage_categories(request):
    if not request.user.is_superuser:
        return redirect('adminlogin')
    categories = Category.objects.all().order_by('-created_at')
    return render(request, 'manage_categories.html', {'categories': categories})

@login_required(login_url='adminlogin')
def edit_category(request, pk):
    if not request.user.is_superuser:
        return redirect('adminlogin')
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        name        = request.POST.get('name')
        description = request.POST.get('description')
        if name:
            if Category.objects.filter(name=name).exclude(pk=pk).exists():
                return render(request, 'manage_categories.html', {
                    'categories': Category.objects.all().order_by('-created_at'),
                    'error': f'Category "{name}" already exists!',
                    'edit_cat': category,
                })
            category.name        = name
            category.description = description
            category.save()
            return render(request, 'manage_categories.html', {
                'categories': Category.objects.all().order_by('-created_at'),
                'success': f'Category "{name}" updated successfully!',
            })
    return render(request, 'manage_categories.html', {
        'categories': Category.objects.all().order_by('-created_at'),
        'edit_cat': category,
    })

@login_required(login_url='adminlogin')
def delete_category(request, pk):
    if not request.user.is_superuser:
        return redirect('adminlogin')
    category = get_object_or_404(Category, pk=pk)
    name = category.name
    category.delete()
    return render(request, 'manage_categories.html', {
        'categories': Category.objects.all().order_by('-created_at'),
        'success': f'Category "{name}" deleted successfully!',
    })

# ========================================    Product  =================================================================

@login_required(login_url='adminlogin')
def add_product(request):
    if not request.user.is_superuser:
        return redirect('adminlogin')
    categories = Category.objects.all()
    if request.method == 'POST':
        name        = request.POST.get('name')
        category_id = request.POST.get('category')
        description = request.POST.get('description')
        price       = request.POST.get('price')
        stock       = request.POST.get('stock')
        image       = request.FILES.get('image')
        is_active   = request.POST.get('is_active') == 'on'
        if name and category_id and price:
            category = get_object_or_404(Category, pk=category_id)
            Product.objects.create(
                name=name, category=category,
                description=description, price=price,
                stock=stock or 0, image=image, is_active=is_active,
            )
            return render(request, 'add_product.html', {
                'categories': categories,
                'success': f'Product "{name}" added successfully!'
            })
        else:
            return render(request, 'add_product.html', {
                'categories': categories,
                'error': 'Name, Category and Price are required.'
            })
    return render(request, 'add_product.html', {'categories': categories})

@login_required(login_url='adminlogin')
def edit_product(request, pk):
    if not request.user.is_superuser:
        return redirect('adminlogin')
    product    = get_object_or_404(Product, pk=pk)
    categories = Category.objects.all()
    if request.method == 'POST':
        product.name        = request.POST.get('name')
        product.description = request.POST.get('description')
        product.price       = request.POST.get('price')
        product.stock       = request.POST.get('stock', 0)
        product.is_active   = request.POST.get('is_active') == 'on'
        cat_id = request.POST.get('category')
        if cat_id:
            product.category = get_object_or_404(Category, pk=cat_id)
        if request.FILES.get('image'):
            product.image = request.FILES.get('image')
        product.save()
        return render(request, 'manage_products.html', {
            'products': Product.objects.all().select_related('category').order_by('-created_at'),
            'success': f'Product "{product.name}" updated successfully!'
        })
    return render(request, 'edit_product.html', {
        'product': product, 'categories': categories
    })

@login_required(login_url='adminlogin')
def manage_products(request):
    if not request.user.is_superuser:
        return redirect('adminlogin')
    products = Product.objects.all().select_related('category').order_by('-created_at')
    return render(request, 'manage_products.html', {'products': products})


@login_required(login_url='adminlogin')
def delete_product(request, pk):
    if not request.user.is_superuser:
        return redirect('adminlogin')
    product = get_object_or_404(Product, pk=pk)
    name = product.name
    product.delete()
    return render(request, 'manage_products.html', {
        'products': Product.objects.all().select_related('category').order_by('-created_at'),
        'success': f'Product "{name}" deleted successfully!'
    })

# ============================ Admin Users.html ==================================================

@login_required(login_url='adminlogin')
def admin_users(request):
    if not request.user.is_superuser:
        return redirect('adminlogin')
    users = customuser.objects.filter(is_user=True).order_by('-date_joined')
    return render(request, 'admin_users.html', {'users': users})

@login_required(login_url='adminlogin')
def admin_orders(request):
    if not request.user.is_superuser:
        return redirect('adminlogin')
    orders = Order.objects.all().select_related('user').prefetch_related('items__product').order_by('-created_at')
    return render(request, 'admin_orders.html', {'orders': orders})

@login_required(login_url='adminlogin')
def update_order_status(request, order_id):
    if not request.user.is_superuser:
        return redirect('adminlogin')
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        previous_status = order.status
        new_status = request.POST.get('status')
        admin_comment = request.POST.get('admin_comment', '').strip()
        if new_status:
            order.status = new_status
        order.admin_comment = admin_comment
        order.save()
        if new_status and new_status != previous_status:
            send_order_status_email(order)
    return redirect('admin_orders')


# =====================================  Try On =================================================================

def tryon(request):
    from django.db.models import Prefetch
    active_products = Product.objects.filter(is_active=True)
    categories = Category.objects.prefetch_related(
        Prefetch('products', queryset=active_products)
    ).all()
    base = 'base3.html' if request.user.is_authenticated and request.user.is_user else 'base.html'
    return render(request, 'tryon.html', {'categories': categories, 'base_template': base})

@login_required(login_url='userlogin')
def tryon_stream(request, product_id):
    size_scale   = float(request.GET.get('size', 1.0))
    product      = get_object_or_404(Product, pk=product_id)
    name         = product.name.lower()
    if any(w in name for w in ['maang', 'tikka', 'tika', 'head']):
        jewelry_type = 'maang_tikka'
    elif any(w in name for w in ['ear', 'jhumka', 'stud', 'hoop']):
        jewelry_type = 'earring'
    else:
        jewelry_type = 'necklace'     
    camera_state['running'] = True
    def stream():
        yield from generate_frames(product_id, jewelry_type, size_scale)
    response = StreamingHttpResponse(
        stream(),
        content_type='multipart/x-mixed-replace; boundary=frame'
    )
    response['Cache-Control']   = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response

@login_required(login_url='userlogin')
def tryon_stop(request):
    camera_state['running'] = False
    return JsonResponse({'status': 'stopped'})

# ====================  User Registartion and Login  =========================================================

def send_otp_email(email, otp):
    """
    Helper function to send OTP via Email.
    Uses the SMTP settings configured in settings.py.
    """
    subject = "Your Registration OTP - Jwellery Trail Management"
    message = f"Hello,\n\nYour OTP for registration is: {otp}\n\nPlease enter this code on the verification page to complete your registration.\n\nThank you!"
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [email]
    
    try:
        send_mail(subject, message, from_email, recipient_list)
        print(f"DEBUG: OTP sent to email {email}")
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')

        if customuser.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error': 'Username already taken.'})

        # Generate OTP
        otp = str(random.randint(100000, 999999))
        
        # Store data in session
        request.session['pending_user_data'] = {
            'username': username,
            'first_name': first_name,
            'email': email,
            'phone': phone,
            'password': password,
            'otp': otp
        }
        # Send OTP via Email
        send_otp_email(email, otp)
        
        # Log OTP to console for debugging
        print(f"DEBUG: OTP for {email} is {otp}")
        return redirect('verify_otp')
    return render(request, 'register.html')

def verify_otp(request):
    pending_data = request.session.get('pending_user_data')
    if not pending_data:
        return redirect('register')
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        if entered_otp == pending_data['otp']:
            user = customuser.objects.create_user(
                username=pending_data['username'],
                email=pending_data['email'],
                password=pending_data['password'],
                phone=pending_data['phone'],
                first_name=pending_data['first_name'],
                is_user=True
            )
            # Clear session
            del request.session['pending_user_data']
            return redirect('userlogin')
        else:
            return render(request, 'verify_otp.html', {'error': 'Invalid OTP. Please try again.'})

    return render(request, 'verify_otp.html', {'email': pending_data['email']})

def userlogin(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_user:
            login(request, user)
            next_url = request.POST.get('next') or request.GET.get('next') or 'userdashboard'
            return redirect(next_url)
        return render(request, 'userlogin.html', {'error': 'Invalid username or password.'})
    return render(request, 'userlogin.html', {'next': request.GET.get('next', '')})

@login_required(login_url='userlogin')
def userdashboard(request):
    if not request.user.is_user:
        logout(request)
        return redirect('userlogin')
    cart_items  = Cart.objects.filter(user=request.user).select_related('product')
    cart_count  = cart_items.count()
    cart_total  = sum(i.subtotal() for i in cart_items)
    recent_cart = cart_items.order_by('-added_at')[:3]
    categories  = Category.objects.prefetch_related('products').all()
    total_products = Product.objects.filter(is_active=True).count()
    return render(request, 'userdashboard.html', {
        'cart_items':     cart_items,
        'cart_count':     cart_count,
        'cart_total':     cart_total,
        'recent_cart':    recent_cart,
        'categories':     categories,
        'total_products': total_products,
    })

def userlogout(request):
    logout(request)
    return redirect('userlogin')

# ====================== Wishlist=================================================================

@login_required(login_url='userlogin')
def wishlist(request):
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    return render(request, 'wishlist.html', {'wishlist_items': wishlist_items})

@login_required(login_url='userlogin')
def toggle_wishlist(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, product=product)
    if not created:
        wishlist_item.delete()
    return redirect(request.META.get('HTTP_REFERER', 'menu'))


# ====================== Profile ===================================================================
@login_required(login_url='userlogin')
def profile(request):
    if not request.user.is_user:
        return redirect('userlogin')
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.phone = request.POST.get('phone', user.phone)
        user.save()
        return render(request, 'profile.html', {'success': 'Profile updated successfully!'})
    return render(request, 'profile.html')

# ====================== Checkout & Payment ========================================================

@login_required(login_url='userlogin')
def checkout(request):
    cart_items = Cart.objects.filter(user=request.user).select_related('product')
    if not cart_items:
        return redirect('cart')

    total = sum(item.subtotal() for item in cart_items)
    return render(request, 'checkout.html', build_checkout_context(
        request,
        cart_items,
        total,
        selected_payment_method='UPI',
    ))


def build_checkout_context(request, cart_items, total, **extra):
    last_order = Order.objects.filter(user=request.user).order_by('-created_at').first()
    
    context = {
        'cart_items': cart_items,
        'total': total,
        'selected_payment_method': extra.get('selected_payment_method', 'UPI'),
        'entered_upi_id': extra.get('entered_upi_id', ''),
        'entered_shipping_address': extra.get('entered_shipping_address', last_order.shipping_address if last_order else ''),
        'entered_city': extra.get('entered_city', last_order.city if last_order else ''),
        'entered_state': extra.get('entered_state', last_order.state if last_order else ''),
        'entered_pincode': extra.get('entered_pincode', last_order.pincode if last_order else ''),
        'entered_phone_number': extra.get(
            'entered_phone_number',
            (last_order.phone_number if last_order else None) or getattr(request.user, 'phone', '') or ''
        ),
        'checkout_error': extra.get('checkout_error', ''),
    }
    return context

@login_required(login_url='userlogin')
def process_payment(request):
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        upi_id = request.POST.get('upi_id', '').strip()
        shipping_address = request.POST.get('shipping_address', '').strip()
        city = request.POST.get('city', '').strip()
        state = request.POST.get('state', '').strip()
        pincode = request.POST.get('pincode', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        cart_items = Cart.objects.filter(user=request.user).select_related('product')
        if not cart_items:
            return redirect('cart')
        total = sum(item.subtotal() for item in cart_items)

        checkout_state = {
            'selected_payment_method': payment_method or 'UPI',
            'entered_upi_id': upi_id,
            'entered_shipping_address': shipping_address,
            'entered_city': city,
            'entered_state': state,
            'entered_pincode': pincode,
            'entered_phone_number': phone_number,
        }

        if not shipping_address or not city or not state or not pincode or not phone_number:
            return render(request, 'checkout.html', build_checkout_context(
                request,
                cart_items,
                total,
                checkout_error='Please fill in all shipping details before placing the order.',
                **checkout_state,
            ))

        if not re.fullmatch(r'\d{6}', pincode):
            return render(request, 'checkout.html', build_checkout_context(
                request,
                cart_items,
                total,
                checkout_error='Enter a valid 6-digit pincode.',
                **checkout_state,
            ))

        if not re.fullmatch(r'\d{10,15}', phone_number):
            return render(request, 'checkout.html', build_checkout_context(
                request,
                cart_items,
                total,
                checkout_error='Enter a valid phone number using 10 to 15 digits.',
                **checkout_state,
            ))

        if payment_method == 'UPI':
            if not upi_id:
                return render(request, 'checkout.html', build_checkout_context(
                    request,
                    cart_items,
                    total,
                    checkout_error='Please enter your UPI ID to continue.',
                    **checkout_state,
                ))
            if not re.fullmatch(r'[\w.\-]{2,}@[A-Za-z]{2,}', upi_id):
                return render(request, 'checkout.html', build_checkout_context(
                    request,
                    cart_items,
                    total,
                    checkout_error='Enter a valid UPI ID like name@bank.',
                    **checkout_state,
                ))

        order = Order.objects.create(
            user=request.user,
            total_amount=total,
            payment_method=payment_method,
            status='Success',
            shipping_address=shipping_address,
            city=city,
            state=state,
            pincode=pincode,
            phone_number=phone_number,
        )
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )
            # Update Stock
            if item.product.stock >= item.quantity:
                item.product.stock -= item.quantity
                item.product.save()
        send_order_confirmation_email(order)
        cart_items.delete() 
        return redirect('order_success', order_id=order.id)
    
    return redirect('checkout')

@login_required(login_url='userlogin')
def my_orders(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items__product').order_by('-created_at')
    return render(request, 'my_orders.html', {'orders': orders})

@login_required(login_url='userlogin')
def order_details(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product'),
        id=order_id,
        user=request.user
    )
    return render(request, 'order_detail.html', {'order': order})

@login_required(login_url='userlogin')
def download_invoice(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product'),
        id=order_id,
        user=request.user
    )
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice-ORD-{order.id}.pdf"'

    pdf = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    y = height - 50

    pdf.setTitle(f'Invoice ORD-{order.id}')
    pdf.setFont('Helvetica-Bold', 20)
    pdf.drawString(40, y, 'Invoice')
    pdf.setFont('Helvetica', 10)
    pdf.drawRightString(width - 40, y, f'Order No: ORD-{order.id}')
    y -= 30

    pdf.setFont('Helvetica', 11)
    pdf.drawString(40, y, f'Date: {order.created_at.strftime("%d %b %Y, %I:%M %p")}')
    y -= 18
    pdf.drawString(40, y, f'Status: {order.status}')
    y -= 18
    pdf.drawString(40, y, f'Payment Method: {order.payment_method}')
    y -= 28

    pdf.setFont('Helvetica-Bold', 12)
    pdf.drawString(40, y, 'Billing and Shipping Details')
    y -= 20
    pdf.setFont('Helvetica', 11)
    pdf.drawString(40, y, f'Customer: {order.user.get_full_name() or order.user.username}')
    y -= 18
    pdf.drawString(40, y, f'Phone: {order.phone_number or "Not provided"}')
    y -= 18
    address_lines = [
        order.shipping_address or 'Not provided',
        ', '.join(filter(None, [order.city, order.state])) or '',
        order.pincode or '',
    ]
    for line in address_lines:
        if line:
            pdf.drawString(40, y, line)
            y -= 18

    y -= 12
    pdf.setFont('Helvetica-Bold', 12)
    pdf.drawString(40, y, 'Items')
    y -= 20

    pdf.setFont('Helvetica-Bold', 11)
    pdf.drawString(40, y, 'Product')
    pdf.drawString(290, y, 'Qty')
    pdf.drawString(340, y, 'Rate')
    pdf.drawRightString(width - 40, y, 'Amount')
    y -= 10
    pdf.line(40, y, width - 40, y)
    y -= 18

    pdf.setFont('Helvetica', 11)
    for item in order.items.all():
        line_total = item.price * item.quantity
        if y < 90:
            pdf.showPage()
            y = height - 50
            pdf.setFont('Helvetica', 11)
        pdf.drawString(40, y, item.product.name[:38])
        pdf.drawString(290, y, str(item.quantity))
        pdf.drawString(340, y, f'Rs. {item.price:.2f}')
        pdf.drawRightString(width - 40, y, f'Rs. {line_total:.2f}')
        y -= 20

    y -= 8
    pdf.line(40, y, width - 40, y)
    y -= 24
    pdf.setFont('Helvetica-Bold', 12)
    pdf.drawRightString(width - 40, y, f'Grand Total: Rs. {order.total_amount:.2f}')

    pdf.showPage()
    pdf.save()
    return response

@login_required(login_url='userlogin')
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'order_success.html', {'order': order})

@login_required(login_url='userlogin')

@login_required(login_url='adminlogin')
def print_all_orders(request):
    """Return a simple printable list of all orders for admin."""
    orders = Order.objects.all().select_related('user').prefetch_related('items__product').order_by('-created_at')
    # Build a plain‑text representation
    lines = []
    lines.append('=== All Orders Report ===\n')
    for order in orders:
        lines.append(f'Order ID: {order.id} | User: {order.user.username} | Total: ₹{order.total_amount} | Method: {order.payment_method} | Status: {order.status} | Date: {order.created_at.strftime("%Y-%m-%d %H:%M")}')
        for item in order.items.all():
            lines.append(f'    - {item.product.name} x{item.quantity} @ ₹{item.price}')
        lines.append('')
    response_text = '\n'.join(lines)
    return HttpResponse(response_text, content_type='text/plain')
