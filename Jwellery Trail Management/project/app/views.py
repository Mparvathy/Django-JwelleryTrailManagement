from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import StreamingHttpResponse, JsonResponse
from django.db import models
from django.db.models import Prefetch
from  .models import Category, Product, customuser, Cart
import cv2
import numpy as np
from PIL import Image
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
import mediapipe as mp

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


# ── Process necklace overlay ──────────────────────────────────
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

# ── Process earring overlay ───────────────────────────────────
def process_earring(frame, landmarks, jewelry_img, size_scale, W, H):
    lm      = landmarks.landmark
    l_ear   = lm[7]    
    r_ear   = lm[8]   
    l_mouth = lm[9]
    r_mouth = lm[10]
    lEarX  = int(l_ear.x * W)
    rEarX  = int(r_ear.x * W)
    lEarY  = int(l_ear.y * H)
    rEarY  = int(r_ear.y * H)
    mouthY = int(((l_mouth.y + r_mouth.y) / 2) * H)
    l_lobe_y = int(lEarY + (mouthY - lEarY) * 0.30)
    r_lobe_y = int(rEarY + (mouthY - rEarY) * 0.30)
    ear_dist = abs(lEarX - rEarX)
    jw_w = max(int(ear_dist * 0.18 * size_scale), 20)
    jw_h = int(jw_w * (jewelry_img.height / max(jewelry_img.width, 1)))
    frame = overlay_image(frame, jewelry_img,lEarX - jw_w // 2, l_lobe_y,jw_w, jw_h, flip=False)
    frame = overlay_image(frame, jewelry_img, rEarX - jw_w // 2, r_lobe_y,jw_w, jw_h, flip=True)
    return frame

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

def generate_frames(product_id, jewelry_type, size_scale=1.0):
    import time
    product = get_object_or_404(Product, pk=product_id)
    try:
        jewelry_img = remove_white_bg(product.image.path)
    except Exception as e:
        print(f"Image load error: {e}")
        jewelry_img = Image.open(product.image.path).convert("RGBA")
    pose = _build_pose_landmarker()
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("ERROR: Cannot open camera!")
        pose.close()
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    print(f"Camera opened. Running stream for product_id={product_id}")
    try:
        while camera_state['running']:
            ret, frame = cap.read()
            if not ret:
                print("Frame read failed")
                time.sleep(0.05)
                continue
            frame   = cv2.flip(frame, 1)
            H, W    = frame.shape[:2]
            rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            ts_ms  = int(time.time() * 1000)
            results = pose.detect_for_video(mp_img, ts_ms)
            if results.pose_landmarks:
                class _LM:
                    def __init__(self, lms): self.landmark = lms
                landmarks = _LM(results.pose_landmarks[0])
                if jewelry_type == 'earring':
                    frame = process_earring(
                        frame, landmarks,
                        jewelry_img, size_scale, W, H
                    )
                else:
                    frame = process_necklace(
                        frame, landmarks,
                        jewelry_img, size_scale, W, H
                    )
            ret2, buffer = cv2.imencode(
                '.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80]
            )
            if not ret2:
                continue

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' +
                   buffer.tobytes() + b'\r\n')
            time.sleep(0.03)
    except Exception as e:
        print(f"Stream error: {e}")
    finally:
        print("Camera released")
        cap.release()
        pose.close()  

# ================== Home Page ==================================

def home(request):
    categories = Category.objects.prefetch_related('products').all()
    return render(request, 'home.html', {'categories': categories})

# =================  Menu Collection Page ======================================

def menu(request):
    categories = Category.objects.prefetch_related(
        Prefetch('products', queryset=Product.objects.filter(is_active=True), to_attr='active_products')
    ).all()
    base = 'base2.html' if request.user.is_authenticated and request.user.is_user else 'base.html'
    return render(request, 'menu.html', {'categories': categories, 'base_template': base})

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

# =============================== Display the  Products if respected Category Products ==================================

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
    return render(request, 'base1.html')

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

# =====================================  Try On =================================================================

def tryon(request):
    from django.db.models import Prefetch
    active_products = Product.objects.filter(is_active=True)
    categories = Category.objects.prefetch_related(
        Prefetch('products', queryset=active_products)
    ).all()
    return render(request, 'tryon.html', {'categories': categories})

def tryon_stream(request, product_id):
    size_scale   = float(request.GET.get('size', 1.0))
    product      = get_object_or_404(Product, pk=product_id)
    name         = product.name.lower()
    jewelry_type = 'earring' if any(
        w in name for w in ['ear', 'jhumka', 'stud', 'hoop']
    ) else 'necklace'
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

def tryon_stop(request):
    camera_state['running'] = False
    return JsonResponse({'status': 'stopped'})

# ====================  User Registartion and Login  =========================================================
def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        first_name= request.POST.get('first_name')
        email    = request.POST.get('email')
        phone    = request.POST.get('phone')
        password = request.POST.get('password')
        if customuser.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error': 'Username already taken.'})
        user = customuser.objects.create_user(
            username=username, email=email, password=password,
            phone=phone,first_name=first_name, is_user=True
        )
        login(request, user)
        return redirect('userlogin')
    return render(request, 'register.html')

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
