import os
import uuid
import json
from datetime import datetime, date, time
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, session, abort
)

from models import (
    db, Admin, Category, MenuItem, MenuItemModifier, Order, OrderItem,
    Reservation, Review, ContactMessage, PromoCode, GiftCard,
    Newsletter, GalleryImage, FAQ
)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'spice-garden-secret-key-2024')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///restaurant.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Fix for PostgreSQL URL (starts with postgres:// instead of postgresql://)
if app.config['SQLALCHEMY_DATABASE_URI'] and app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)
app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db.init_app(app)

RESTAURANT_NAME = "Spice Garden"
RESTAURANT_TAGLINE = "Authentic Pakistani Cuisine"
RESTAURANT_ADDRESS = "42 Food Street, Gulberg, Lahore, Pakistan"
RESTAURANT_PHONE = "+92 300 1234567"
RESTAURANT_EMAIL = "info@spicegarden.pk"
RESTAURANT_HOURS = "Mon-Sun: 11:00 AM - 11:00 PM"
WHATSAPP_NUMBER = "923001234567"

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_globals():
    return {
        'restaurant_name': RESTAURANT_NAME,
        'restaurant_tagline': RESTAURANT_TAGLINE,
        'restaurant_address': RESTAURANT_ADDRESS,
        'restaurant_phone': RESTAURANT_PHONE,
        'restaurant_email': RESTAURANT_EMAIL,
        'restaurant_hours': RESTAURANT_HOURS,
        'whatsapp_number': WHATSAPP_NUMBER,
        'current_year': datetime.now().year,
    }

@app.route('/')
def index():
    categories = Category.query.order_by(Category.display_order).all()
    featured_items = MenuItem.query.filter_by(is_featured=True, is_available=True).limit(6).all()
    reviews = Review.query.filter_by(is_approved=True).order_by(Review.created_at.desc()).limit(4).all()
    return render_template('index.html', categories=categories, featured_items=featured_items, reviews=reviews)

@app.route('/menu')
def menu_page():
    categories = Category.query.order_by(Category.display_order).all()
    menu_by_category = {}
    for cat in categories:
        items = MenuItem.query.filter_by(category_id=cat.id, is_available=True).all()
        if items:
            menu_by_category[cat] = items
    return render_template('menu.html', menu_by_category=menu_by_category, categories=categories)

@app.route('/cart')
def cart_page():
    promo_code = session.get('promo_code', {})
    return render_template('cart.html', promo_code=promo_code)

@app.route('/api/menu/search')
def api_menu_search():
    q = request.args.get('q', '').strip()
    veg = request.args.get('veg', type=int)
    spicy = request.args.get('spicy', type=int)
    gluten_free = request.args.get('gluten_free', type=int)
    bestseller = request.args.get('bestseller', type=int)
    sort = request.args.get('sort', 'name')
    query = MenuItem.query.filter_by(is_available=True)
    if q:
        query = query.filter(db.or_(MenuItem.name.ilike(f'%{q}%'), MenuItem.description.ilike(f'%{q}%')))
    if veg is not None:
        query = query.filter_by(is_vegetarian=bool(veg))
    if spicy is not None:
        query = query.filter_by(is_spicy=bool(spicy))
    if gluten_free is not None:
        query = query.filter_by(is_gluten_free=bool(gluten_free))
    if bestseller is not None:
        query = query.filter_by(is_bestseller=bool(bestseller))
    if sort == 'price_low':
        query = query.order_by(MenuItem.price.asc())
    elif sort == 'price_high':
        query = query.order_by(MenuItem.price.desc())
    else:
        query = query.order_by(MenuItem.name.asc())
    items = query.all()
    return jsonify([{
        'id': item.id, 'name': item.name, 'description': item.description,
        'price': item.price, 'image_url': item.image_url,
        'category_name': item.category.name if item.category else '',
        'is_vegetarian': item.is_vegetarian, 'is_spicy': item.is_spicy,
        'is_gluten_free': item.is_gluten_free, 'is_bestseller': item.is_bestseller,
        'calories': item.calories, 'preparation_time': item.preparation_time,
    } for item in items])

@app.route('/api/menu-item/<int:item_id>/modifiers')
def api_item_modifiers(item_id):
    item = MenuItem.query.get_or_404(item_id)
    modifiers = MenuItemModifier.query.filter_by(menu_item_id=item_id).all()
    groups = {}
    for m in modifiers:
        g = m.group_name or 'Add-ons'
        if g not in groups:
            groups[g] = []
        groups[g].append({'id': m.id, 'name': m.name, 'price_adjustment': m.price_adjustment})
    return jsonify({'item_id': item.id, 'item_name': item.name, 'base_price': item.price, 'modifier_groups': groups})

@app.route('/api/cart/add', methods=['POST'])
def cart_add():
    data = request.get_json()
    item_id = data.get('item_id')
    quantity = data.get('quantity', 1)
    modifiers = data.get('modifiers', [])
    special_instructions = data.get('special_instructions', '')
    menu_item = MenuItem.query.get_or_404(item_id)
    modifier_total = 0
    modifier_names = []
    for mod_id in modifiers:
        mod = MenuItemModifier.query.get(mod_id)
        if mod:
            modifier_total += mod.price_adjustment
            modifier_names.append(mod.name)
    final_price = menu_item.price + modifier_total
    modifier_key = json.dumps(sorted(modifiers))
    cart = session.get('cart', [])
    found = False
    for c in cart:
        if c['item_id'] == item_id and c.get('modifier_key') == modifier_key:
            c['quantity'] += quantity
            found = True
            break
    if not found:
        cart.append({
            'item_id': item_id, 'name': menu_item.name, 'price': final_price,
            'base_price': menu_item.price, 'image_url': menu_item.image_url,
            'quantity': quantity, 'modifiers': modifier_names,
            'modifier_key': modifier_key, 'special_instructions': special_instructions,
        })
    session['cart'] = cart
    return jsonify({'success': True, 'cart': cart, 'cart_count': sum(c['quantity'] for c in cart)})

@app.route('/api/cart/update', methods=['POST'])
def cart_update():
    data = request.get_json()
    item_id = data.get('item_id')
    quantity = data.get('quantity', 1)
    cart = session.get('cart', [])
    for c in cart:
        if c['item_id'] == item_id:
            c['quantity'] = max(0, quantity)
            break
    cart = [c for c in cart if c['quantity'] > 0]
    session['cart'] = cart
    return jsonify({'success': True, 'cart': cart, 'cart_count': sum(c['quantity'] for c in cart)})

@app.route('/api/cart/remove', methods=['POST'])
def cart_remove():
    data = request.get_json()
    item_id = data.get('item_id')
    cart = [c for c in session.get('cart', []) if c['item_id'] != item_id]
    session['cart'] = cart
    return jsonify({'success': True, 'cart': cart, 'cart_count': sum(c['quantity'] for c in cart)})

@app.route('/api/cart/clear', methods=['POST'])
def cart_clear():
    session['cart'] = []
    session.pop('promo_code', None)
    return jsonify({'success': True, 'cart': [], 'cart_count': 0})

@app.route('/api/cart')
def api_cart():
    cart = session.get('cart', [])
    subtotal = sum(c['price'] * c['quantity'] for c in cart)
    promo = session.get('promo_code', {})
    discount = promo.get('discount_amount', 0)
    delivery_fee = 0 if subtotal >= 1000 else 100
    total = subtotal - discount + delivery_fee
    return jsonify({'cart': cart, 'subtotal': subtotal, 'discount': discount, 'delivery_fee': delivery_fee, 'total': max(0, total), 'cart_count': sum(c['quantity'] for c in cart)})

@app.route('/api/promo/apply', methods=['POST'])
def api_promo_apply():
    data = request.get_json()
    code = data.get('code', '').strip().upper()
    if not code:
        return jsonify({'error': 'Please enter a promo code'}), 400
    promo = PromoCode.query.filter_by(code=code, is_active=True).first()
    if not promo:
        return jsonify({'error': 'Invalid promo code'}), 400
    if promo.valid_until and promo.valid_until < datetime.utcnow():
        return jsonify({'error': 'This promo code has expired'}), 400
    if promo.current_uses >= promo.max_uses:
        return jsonify({'error': 'This promo code has been fully used'}), 400
    cart = session.get('cart', [])
    subtotal = sum(c['price'] * c['quantity'] for c in cart)
    if subtotal < promo.min_order:
        return jsonify({'error': f'Minimum order of Rs. {promo.min_order:.0f} required'}), 400
    discount = subtotal * (promo.discount_value / 100) if promo.discount_type == 'percentage' else promo.discount_value
    discount = min(discount, subtotal)
    session['promo_code'] = {'code': promo.code, 'discount_type': promo.discount_type, 'discount_value': promo.discount_value, 'discount_amount': discount}
    return jsonify({'success': True, 'discount': discount, 'message': f'Promo code applied! You save Rs. {discount:.0f}'})

@app.route('/api/promo/remove', methods=['POST'])
def api_promo_remove():
    session.pop('promo_code', None)
    return jsonify({'success': True})

@app.route('/checkout', methods=['POST'])
def checkout():
    cart = session.get('cart', [])
    if not cart:
        flash('Your cart is empty!', 'error')
        return redirect(url_for('cart_page'))
    name = request.form.get('customer_name', '').strip()
    phone = request.form.get('customer_phone', '').strip()
    email = request.form.get('customer_email', '').strip()
    address = request.form.get('delivery_address', '').strip()
    payment_method = request.form.get('payment_method', 'cod')
    notes = request.form.get('notes', '').strip()
    order_type = request.form.get('order_type', 'delivery')
    tip = request.form.get('tip', 0, type=float)
    scheduled = request.form.get('scheduled_time', '').strip()
    if not name or not phone:
        flash('Please provide your name and phone number.', 'error')
        return redirect(url_for('cart_page'))
    if order_type == 'delivery' and not address:
        flash('Please provide a delivery address.', 'error')
        return redirect(url_for('cart_page'))
    order_number = f"ORD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    subtotal = sum(c['price'] * c['quantity'] for c in cart)
    promo = session.get('promo_code', {})
    discount = promo.get('discount_amount', 0)
    promo_code_str = promo.get('code', '')
    delivery_fee = 0 if subtotal >= 1000 else 100
    total_amount = subtotal - discount + delivery_fee + tip
    scheduled_time = None
    if scheduled:
        try:
            scheduled_time = datetime.strptime(scheduled, '%Y-%m-%dT%H:%M')
        except ValueError:
            pass
    order = Order(order_number=order_number, customer_name=name, customer_phone=phone, customer_email=email, total_amount=total_amount, payment_method=payment_method, delivery_address=address, notes=notes, tip_amount=tip, discount_amount=discount, promo_code=promo_code_str, order_type=order_type, scheduled_time=scheduled_time)
    db.session.add(order)
    db.session.flush()
    for c in cart:
        db.session.add(OrderItem(order_id=order.id, menu_item_id=c['item_id'], item_name=c['name'], quantity=c['quantity'], unit_price=c['price'], modifiers_json=json.dumps(c.get('modifiers', []))))
    if promo_code_str:
        p = PromoCode.query.filter_by(code=promo_code_str).first()
        if p:
            p.current_uses += 1
    db.session.commit()
    session['cart'] = []
    session.pop('promo_code', None)
    return redirect(url_for('order_confirmation', order_number=order_number))

@app.route('/order/<order_number>')
def order_confirmation(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    return render_template('order-tracking.html', order=order)

@app.route('/api/order/<order_number>')
def api_order_status(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    return jsonify({
        'order_number': order.order_number, 'status': order.status, 'customer_name': order.customer_name,
        'total_amount': order.total_amount, 'tip_amount': order.tip_amount, 'discount_amount': order.discount_amount,
        'payment_method': order.payment_method, 'order_date': order.order_date.strftime('%Y-%m-%d %H:%M'), 'order_type': order.order_type,
        'items': [{'item_name': i.item_name, 'quantity': i.quantity, 'unit_price': i.unit_price, 'modifiers': json.loads(i.modifiers_json) if i.modifiers_json else []} for i in order.items],
        'status_history': get_status_history(order.status)
    })

def get_status_history(current_status):
    stages = ['pending', 'confirmed', 'preparing', 'ready', 'delivered']
    history = []
    for i, s in enumerate(stages):
        if s == current_status:
            history.append({'status': s, 'active': True, 'completed': True})
            break
        elif stages.index(current_status) > i:
            history.append({'status': s, 'active': False, 'completed': True})
        else:
            history.append({'status': s, 'active': False, 'completed': False})
    if current_status == 'cancelled':
        for h in history:
            h['completed'] = False
    return history

@app.route('/order-tracking')
def order_tracking_page():
    return render_template('order-tracking.html', order=None)

@app.route('/api/reorder/<order_number>', methods=['POST'])
def api_reorder(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    cart = session.get('cart', [])
    for item in order.items:
        menu_item = MenuItem.query.get(item.menu_item_id) if item.menu_item_id else None
        if menu_item and menu_item.is_available:
            cart.append({'item_id': item.menu_item_id, 'name': item.item_name, 'price': item.unit_price, 'base_price': item.unit_price, 'image_url': menu_item.image_url, 'quantity': item.quantity, 'modifiers': json.loads(item.modifiers_json) if item.modifiers_json else [], 'modifier_key': item.modifiers_json or '', 'special_instructions': ''})
    session['cart'] = cart
    return jsonify({'success': True, 'cart_count': sum(c['quantity'] for c in cart), 'message': 'Items added to cart!'})

@app.route('/reservations', methods=['GET', 'POST'])
def reservations():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        res_date = request.form.get('date', '').strip()
        res_time = request.form.get('time', '').strip()
        guests = request.form.get('guests', 1, type=int)
        special = request.form.get('special_requests', '').strip()
        if not name or not phone or not res_date or not res_time:
            flash('Please fill all required fields.', 'error')
            return redirect(url_for('reservations'))
        try:
            res_date_obj = datetime.strptime(res_date, '%Y-%m-%d').date()
            res_time_obj = datetime.strptime(res_time, '%H:%M').time()
        except ValueError:
            flash('Invalid date or time format.', 'error')
            return redirect(url_for('reservations'))
        db.session.add(Reservation(customer_name=name, customer_phone=phone, customer_email=email, reservation_date=res_date_obj, reservation_time=res_time_obj, num_guests=guests, special_requests=special))
        db.session.commit()
        flash('Your table reservation has been submitted!', 'success')
        return redirect(url_for('reservations'))
    return render_template('reservations.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()
        if not name or not email or not message:
            flash('Please fill your name, email, and message.', 'error')
            return redirect(url_for('contact'))
        db.session.add(ContactMessage(name=name, email=email, phone=phone, subject=subject, message=message))
        db.session.commit()
        flash('Thank you! Your message has been sent.', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html')

@app.route('/about')
def about():
    return render_template('about.html', reviews=Review.query.filter_by(is_approved=True).order_by(Review.created_at.desc()).limit(6).all())

@app.route('/api/reviews', methods=['POST'])
def submit_review():
    data = request.get_json()
    name = data.get('name', '').strip()
    rating = data.get('rating', 5)
    comment = data.get('comment', '').strip()
    if not name or not comment:
        return jsonify({'error': 'Name and comment are required.'}), 400
    db.session.add(Review(customer_name=name, rating=max(1, min(5, rating)), comment=comment))
    db.session.commit()
    return jsonify({'success': True, 'message': 'Thank you for your review!'})

@app.route('/api/newsletter/subscribe', methods=['POST'])
def api_newsletter_subscribe():
    data = request.get_json()
    email = data.get('email', '').strip()
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    existing = Newsletter.query.filter_by(email=email).first()
    if existing:
        if existing.is_active:
            return jsonify({'message': 'You are already subscribed!'})
        existing.is_active = True
        db.session.commit()
        return jsonify({'success': True, 'message': 'Welcome back!'})
    db.session.add(Newsletter(email=email))
    db.session.commit()
    return jsonify({'success': True, 'message': 'Thank you for subscribing!'})

@app.route('/gift-cards')
def gift_cards_page():
    return render_template('giftcards.html')

@app.route('/api/gift-card/purchase', methods=['POST'])
def api_gift_card_purchase():
    data = request.get_json()
    amount = data.get('amount', 0, type=float)
    buyer_name = data.get('buyer_name', '').strip()
    buyer_email = data.get('buyer_email', '').strip()
    recipient_name = data.get('recipient_name', '').strip()
    if amount < 500:
        return jsonify({'error': 'Minimum gift card amount is Rs. 500'}), 400
    if not buyer_name or not buyer_email or not recipient_name:
        return jsonify({'error': 'Please fill all required fields'}), 400
    code = f"GC-{uuid.uuid4().hex[:8].upper()}"
    db.session.add(GiftCard(code=code, initial_amount=amount, remaining_amount=amount, buyer_name=buyer_name, buyer_email=buyer_email, recipient_name=recipient_name, recipient_email=data.get('recipient_email', '').strip(), message=data.get('message', '').strip()))
    db.session.commit()
    return jsonify({'success': True, 'code': code, 'message': f'Gift card purchased! Code: {code}'})

@app.route('/api/gift-card/check', methods=['POST'])
def api_gift_card_check():
    data = request.get_json()
    card = GiftCard.query.filter_by(code=data.get('code', '').strip().upper(), is_active=True).first()
    if not card:
        return jsonify({'error': 'Invalid gift card code'}), 400
    return jsonify({'success': True, 'remaining': card.remaining_amount, 'initial': card.initial_amount, 'recipient': card.recipient_name})

@app.route('/faq')
def faq():
    faqs = FAQ.query.filter_by(is_active=True).order_by(FAQ.display_order).all()
    faq_by_category = {}
    for f in faqs:
        cat = f.category or 'General'
        if cat not in faq_by_category:
            faq_by_category[cat] = []
        faq_by_category[cat].append(f)
    return render_template('faq.html', faq_by_category=faq_by_category)

@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/gallery')
def gallery():
    return render_template('gallery.html', images=GalleryImage.query.order_by(GalleryImage.display_order).all())

@app.route('/catering', methods=['GET', 'POST'])
def catering():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        event_type = request.form.get('event_type', '').strip()
        event_date = request.form.get('event_date', '').strip()
        guests = request.form.get('guests', '')
        budget = request.form.get('budget', '').strip()
        details = request.form.get('details', '').strip()
        if not name or not email or not phone:
            flash('Please fill all required fields.', 'error')
            return redirect(url_for('catering'))
        msg = ContactMessage(name=name, email=email, phone=phone, subject=f'Catering Inquiry - {event_type}', message=f"Event: {event_type}\nDate: {event_date}\nGuests: {guests}\nBudget: {budget}\n\n{details}")
        db.session.add(msg)
        db.session.commit()
        flash('Thank you! Your catering inquiry has been submitted.', 'success')
        return redirect(url_for('catering'))
    return render_template('catering.html')

# ════════════════════════════════════════════
# IMAGE UPLOAD
# ════════════════════════════════════════════

@app.route('/health')
def health_check():
    """Health check that also verifies database connectivity."""
    db_ok = False
    try:
        # Quick DB ping
        db.session.execute(db.text('SELECT 1'))
        db_ok = True
    except Exception:
        pass
    return jsonify({
        'status': 'ok' if db_ok else 'degraded',
        'database': 'connected' if db_ok else 'connecting',
        'service': RESTAURANT_NAME
    })


@app.route('/api/upload', methods=['POST'])
@admin_required
def api_upload_image():
    """Upload an image and return the URL."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed. Use PNG, JPG, JPEG, GIF, or WEBP'}), 400
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    url = url_for('static', filename=f'uploads/{filename}')
    return jsonify({'success': True, 'url': url, 'filename': filename})


# ════════════════════════════════════════════
# ADMIN ROUTES
# ════════════════════════════════════════════

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        admin = Admin.query.filter_by(username=request.form.get('username', '').strip()).first()
        if admin and admin.check_password(request.form.get('password', '')):
            session['admin_logged_in'] = True
            session['admin_username'] = admin.username
            return redirect(url_for('admin_dashboard'))
        flash('Invalid username or password.', 'error')
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/')
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    return render_template('admin/dashboard.html',
        total_orders=Order.query.count(),
        pending_orders=Order.query.filter_by(status='pending').count(),
        preparing_orders=Order.query.filter_by(status='preparing').count(),
        total_revenue=db.session.query(db.func.sum(Order.total_amount)).filter(Order.status != 'cancelled').scalar() or 0,
        total_reservations=Reservation.query.count(),
        total_messages=ContactMessage.query.count(),
        unread_messages=ContactMessage.query.filter_by(is_read=False).count(),
        total_reviews=Review.query.count(),
        pending_reviews=Review.query.filter_by(is_approved=False).count(),
        total_subscribers=Newsletter.query.filter_by(is_active=True).count(),
        recent_orders=Order.query.order_by(Order.order_date.desc()).limit(5).all()
    )

@app.route('/admin/menu')
@admin_required
def admin_menu():
    cats = Category.query.order_by(Category.display_order).all()
    menu_by_category = {cat: MenuItem.query.filter_by(category_id=cat.id).all() for cat in cats}
    return render_template('admin/menu.html', categories=cats, menu_by_category=menu_by_category)

@app.route('/admin/menu/category/add', methods=['POST'])
@admin_required
def admin_add_category():
    name = request.form.get('name', '').strip()
    if name:
        db.session.add(Category(name=name, description=request.form.get('description', '').strip()))
        db.session.commit()
        flash(f'Category "{name}" added!', 'success')
    return redirect(url_for('admin_menu'))

@app.route('/admin/menu/category/delete/<int:id>', methods=['POST'])
@admin_required
def admin_delete_category(id):
    db.session.delete(Category.query.get_or_404(id))
    db.session.commit()
    flash('Category deleted.', 'success')
    return redirect(url_for('admin_menu'))

@app.route('/admin/menu/add', methods=['POST'])
@admin_required
def admin_add_item():
    name = request.form.get('name', '').strip()
    price = request.form.get('price', 0, type=float)
    category_id = request.form.get('category_id', 0, type=int)
    if name and price > 0 and category_id:
        item = MenuItem(
            name=name, description=request.form.get('description', '').strip(), price=price,
            category_id=category_id, image_url=request.form.get('image_url', '').strip(),
            is_featured=request.form.get('is_featured') == 'on',
            is_vegetarian=request.form.get('is_vegetarian') == 'on',
            is_spicy=request.form.get('is_spicy') == 'on',
            is_gluten_free=request.form.get('is_gluten_free') == 'on',
            is_bestseller=request.form.get('is_bestseller') == 'on',
            calories=request.form.get('calories', 0, type=int),
            preparation_time=request.form.get('preparation_time', 15, type=int)
        )
        db.session.add(item)
        db.session.commit()
        flash(f'"{name}" added to menu!', 'success')
    return redirect(url_for('admin_menu'))

@app.route('/admin/menu/edit/<int:id>', methods=['POST'])
@admin_required
def admin_edit_item(id):
    item = MenuItem.query.get_or_404(id)
    item.name = request.form.get('name', item.name).strip()
    item.description = request.form.get('description', item.description).strip()
    item.price = request.form.get('price', item.price, type=float)
    item.category_id = request.form.get('category_id', item.category_id, type=int)
    item.image_url = request.form.get('image_url', item.image_url).strip()
    item.is_available = request.form.get('is_available') == 'on'
    item.is_featured = request.form.get('is_featured') == 'on'
    item.is_vegetarian = request.form.get('is_vegetarian') == 'on'
    item.is_spicy = request.form.get('is_spicy') == 'on'
    item.is_gluten_free = request.form.get('is_gluten_free') == 'on'
    item.is_bestseller = request.form.get('is_bestseller') == 'on'
    item.calories = request.form.get('calories', item.calories, type=int)
    item.preparation_time = request.form.get('preparation_time', item.preparation_time, type=int)
    db.session.commit()
    flash(f'"{item.name}" updated!', 'success')
    return redirect(url_for('admin_menu'))

@app.route('/admin/menu/delete/<int:id>', methods=['POST'])
@admin_required
def admin_delete_item(id):
    db.session.delete(MenuItem.query.get_or_404(id))
    db.session.commit()
    flash('Menu item deleted.', 'success')
    return redirect(url_for('admin_menu'))

@app.route('/admin/menu/item/<int:item_id>/modifiers')
@admin_required
def admin_item_modifiers(item_id):
    item = MenuItem.query.get_or_404(item_id)
    return render_template('admin/modifiers.html', item=item, modifiers=MenuItemModifier.query.filter_by(menu_item_id=item_id).all())

@app.route('/admin/menu/item/<int:item_id>/modifiers/add', methods=['POST'])
@admin_required
def admin_add_modifier(item_id):
    name = request.form.get('name', '').strip()
    if name:
        db.session.add(MenuItemModifier(menu_item_id=item_id, name=name, price_adjustment=request.form.get('price_adjustment', 0, type=float), group_name=request.form.get('group_name', 'Add-ons').strip()))
        db.session.commit()
        flash(f'Modifier "{name}" added!', 'success')
    return redirect(url_for('admin_item_modifiers', item_id=item_id))

@app.route('/admin/menu/modifier/<int:mod_id>/delete', methods=['POST'])
@admin_required
def admin_delete_modifier(mod_id):
    mod = MenuItemModifier.query.get_or_404(mod_id)
    item_id = mod.menu_item_id
    db.session.delete(mod)
    db.session.commit()
    flash('Modifier deleted.', 'success')
    return redirect(url_for('admin_item_modifiers', item_id=item_id))

@app.route('/admin/orders')
@admin_required
def admin_orders():
    q = Order.query.order_by(Order.order_date.desc())
    status_filter = request.args.get('status', '')
    if status_filter:
        q = q.filter_by(status=status_filter)
    return render_template('admin/orders.html', orders=q.all(), current_filter=status_filter)

@app.route('/admin/orders/<int:id>/status', methods=['POST'])
@admin_required
def admin_update_order_status(id):
    o = Order.query.get_or_404(id)
    o.status = request.form.get('status', o.status)
    db.session.commit()
    flash(f'Order {o.order_number} updated.', 'success')
    return redirect(url_for('admin_orders'))

@app.route('/admin/orders/<int:id>/delete', methods=['POST'])
@admin_required
def admin_delete_order(id):
    db.session.delete(Order.query.get_or_404(id))
    db.session.commit()
    flash('Order deleted.', 'success')
    return redirect(url_for('admin_orders'))

@app.route('/admin/reservations')
@admin_required
def admin_reservations():
    q = Reservation.query.order_by(Reservation.reservation_date.desc())
    sf = request.args.get('status', '')
    if sf:
        q = q.filter_by(status=sf)
    return render_template('admin/reservations.html', reservations=q.all(), current_filter=sf)

@app.route('/admin/reservations/<int:id>/status', methods=['POST'])
@admin_required
def admin_update_reservation_status(id):
    r = Reservation.query.get_or_404(id)
    r.status = request.form.get('status', r.status)
    db.session.commit()
    flash('Reservation updated.', 'success')
    return redirect(url_for('admin_reservations'))

@app.route('/admin/messages')
@admin_required
def admin_messages():
    return render_template('admin/messages.html', messages=ContactMessage.query.order_by(ContactMessage.created_at.desc()).all())

@app.route('/admin/messages/<int:id>/read', methods=['POST'])
@admin_required
def admin_mark_read(id):
    msg = ContactMessage.query.get_or_404(id)
    msg.is_read = True
    db.session.commit()
    return redirect(url_for('admin_messages'))

@app.route('/admin/messages/<int:id>/delete', methods=['POST'])
@admin_required
def admin_delete_message(id):
    db.session.delete(ContactMessage.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('admin_messages'))

@app.route('/admin/reviews')
@admin_required
def admin_reviews():
    return render_template('admin/reviews.html', reviews=Review.query.order_by(Review.created_at.desc()).all())

@app.route('/admin/reviews/<int:id>/approve', methods=['POST'])
@admin_required
def admin_approve_review(id):
    r = Review.query.get_or_404(id)
    r.is_approved = not r.is_approved
    db.session.commit()
    return redirect(url_for('admin_reviews'))

@app.route('/admin/reviews/<int:id>/delete', methods=['POST'])
@admin_required
def admin_delete_review(id):
    db.session.delete(Review.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('admin_reviews'))

@app.route('/admin/promo-codes')
@admin_required
def admin_promo_codes():
    return render_template('admin/promo_codes.html', promos=PromoCode.query.order_by(PromoCode.created_at.desc()).all())

@app.route('/admin/promo-codes/add', methods=['POST'])
@admin_required
def admin_add_promo():
    code = request.form.get('code', '').strip().upper()
    if code:
        valid_date = None
        vu = request.form.get('valid_until', '').strip()
        if vu:
            try:
                valid_date = datetime.strptime(vu, '%Y-%m-%d')
            except ValueError:
                pass
        db.session.add(PromoCode(code=code, discount_type=request.form.get('discount_type', 'percentage'), discount_value=request.form.get('discount_value', 0, type=float), min_order=request.form.get('min_order', 0, type=float), max_uses=request.form.get('max_uses', 100, type=int), valid_until=valid_date))
        db.session.commit()
        flash(f'Promo code "{code}" created!', 'success')
    return redirect(url_for('admin_promo_codes'))

@app.route('/admin/promo-codes/<int:id>/toggle', methods=['POST'])
@admin_required
def admin_toggle_promo(id):
    p = PromoCode.query.get_or_404(id)
    p.is_active = not p.is_active
    db.session.commit()
    flash(f'Promo "{p.code}" {"activated" if p.is_active else "deactivated"}.', 'success')
    return redirect(url_for('admin_promo_codes'))

@app.route('/admin/promo-codes/<int:id>/delete', methods=['POST'])
@admin_required
def admin_delete_promo(id):
    db.session.delete(PromoCode.query.get_or_404(id))
    db.session.commit()
    flash('Promo deleted.', 'success')
    return redirect(url_for('admin_promo_codes'))

@app.route('/admin/gift-cards')
@admin_required
def admin_gift_cards():
    return render_template('admin/gift_cards.html', cards=GiftCard.query.order_by(GiftCard.created_at.desc()).all())

@app.route('/admin/gift-cards/<int:id>/deactivate', methods=['POST'])
@admin_required
def admin_deactivate_gift_card(id):
    c = GiftCard.query.get_or_404(id)
    c.is_active = not c.is_active
    db.session.commit()
    flash(f'Gift card {"activated" if c.is_active else "deactivated"}.', 'success')
    return redirect(url_for('admin_gift_cards'))

@app.route('/admin/faq')
@admin_required
def admin_faq():
    return render_template('admin/faq.html', faqs=FAQ.query.order_by(FAQ.display_order).all())

@app.route('/admin/faq/add', methods=['POST'])
@admin_required
def admin_add_faq():
    q = request.form.get('question', '').strip()
    a = request.form.get('answer', '').strip()
    if q and a:
        db.session.add(FAQ(question=q, answer=a, category=request.form.get('category', 'General').strip()))
        db.session.commit()
        flash('FAQ added!', 'success')
    return redirect(url_for('admin_faq'))

@app.route('/admin/faq/<int:id>/delete', methods=['POST'])
@admin_required
def admin_delete_faq(id):
    db.session.delete(FAQ.query.get_or_404(id))
    db.session.commit()
    flash('FAQ deleted.', 'success')
    return redirect(url_for('admin_faq'))

@app.route('/admin/gallery')
@admin_required
def admin_gallery():
    return render_template('admin/gallery.html', images=GalleryImage.query.order_by(GalleryImage.display_order).all())

@app.route('/admin/gallery/add', methods=['POST'])
@admin_required
def admin_add_gallery_image():
    url = request.form.get('image_url', '').strip()
    if url:
        db.session.add(GalleryImage(image_url=url, title=request.form.get('title', '').strip(), description=request.form.get('description', '').strip()))
        db.session.commit()
        flash('Image added!', 'success')
    return redirect(url_for('admin_gallery'))

@app.route('/admin/gallery/<int:id>/delete', methods=['POST'])
@admin_required
def admin_delete_gallery_image(id):
    db.session.delete(GalleryImage.query.get_or_404(id))
    db.session.commit()
    flash('Image deleted.', 'success')
    return redirect(url_for('admin_gallery'))

@app.route('/admin/admins')
@admin_required
def admin_admins():
    admins = Admin.query.order_by(Admin.created_at).all()
    return render_template('admin/admins.html', admins=admins)

@app.route('/admin/admins/add', methods=['POST'])
@admin_required
def admin_add_admin():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    confirm = request.form.get('confirm_password', '')
    if not username or len(username) < 3:
        flash('Username must be at least 3 characters.', 'error')
        return redirect(url_for('admin_admins'))
    if not password or len(password) < 6:
        flash('Password must be at least 6 characters.', 'error')
        return redirect(url_for('admin_admins'))
    if password != confirm:
        flash('Passwords do not match.', 'error')
        return redirect(url_for('admin_admins'))
    existing = Admin.query.filter_by(username=username).first()
    if existing:
        flash(f'Username "{username}" already exists.', 'error')
        return redirect(url_for('admin_admins'))
    admin = Admin(username=username)
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    flash(f'Admin "{username}" created successfully!', 'success')
    return redirect(url_for('admin_admins'))

@app.route('/admin/admins/change-password', methods=['POST'])
@admin_required
def admin_change_password():
    current = request.form.get('current_password', '')
    new_pass = request.form.get('new_password', '')
    confirm = request.form.get('confirm_new_password', '')
    admin = Admin.query.filter_by(username=session.get('admin_username')).first()
    if not admin or not admin.check_password(current):
        flash('Current password is incorrect.', 'error')
        return redirect(url_for('admin_admins'))
    if not new_pass or len(new_pass) < 6:
        flash('New password must be at least 6 characters.', 'error')
        return redirect(url_for('admin_admins'))
    if new_pass != confirm:
        flash('New passwords do not match.', 'error')
        return redirect(url_for('admin_admins'))
    admin.set_password(new_pass)
    db.session.commit()
    flash('Password changed successfully!', 'success')
    return redirect(url_for('admin_admins'))

@app.route('/admin/admins/delete/<int:id>', methods=['POST'])
@admin_required
def admin_delete_admin(id):
    admin = Admin.query.get_or_404(id)
    if admin.username == session.get('admin_username'):
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('admin_admins'))
    db.session.delete(admin)
    db.session.commit()
    flash(f'Admin "{admin.username}" deleted.', 'success')
    return redirect(url_for('admin_admins'))

@app.route('/admin/newsletter')
@admin_required
def admin_newsletter():
    return render_template('admin/newsletter.html', subscribers=Newsletter.query.order_by(Newsletter.created_at.desc()).all())

@app.route('/admin/newsletter/<int:id>/toggle', methods=['POST'])
@admin_required
def admin_toggle_subscriber(id):
    s = Newsletter.query.get_or_404(id)
    s.is_active = not s.is_active
    db.session.commit()
    return redirect(url_for('admin_newsletter'))

# ════════════════════════════════════════════
# SEED DATABASE
# ════════════════════════════════════════════

def seed_database():
    if Admin.query.first() is None:
        admin = Admin(username='admin')
        admin.set_password('admin123')
        db.session.add(admin)

    if Category.query.first() is None:
        categories_data = [
            ('Starters', 'Delicious appetizers', 1),
            ('Main Course', 'Authentic main dishes', 2),
            ('Desserts', 'Sweet treats', 3),
            ('Drinks', 'Refreshing beverages', 4),
        ]
        for name, desc, order in categories_data:
            db.session.add(Category(name=name, description=desc, display_order=order))
        db.session.flush()
        cats = {c.name: c.id for c in Category.query.all()}

        menu_items_data = [
            ('Chicken Samosa (4 pcs)', 'Crispy fried pastries filled with spiced chicken', 250, 'Starters', 'https://images.unsplash.com/photo-1659439549764-8c1e5b5f7c3f?w=400&h=300&fit=crop', True, False, False, True, False, 180, 20),
            ('Seekh Kebab (6 pcs)', 'Minced beef skewers with traditional spices', 350, 'Starters', 'https://images.unsplash.com/photo-1603360946369-dc9bb6258143?w=400&h=300&fit=crop', True, False, False, False, True, 250, 25),
            ('Chicken Tikka', 'Marinated chicken pieces grilled to perfection', 320, 'Starters', 'https://images.unsplash.com/photo-1565557623262-b51c2513a641?w=400&h=300&fit=crop', False, False, True, False, False, 220, 20),
            ('Spring Rolls (6 pcs)', 'Crispy vegetable spring rolls with sweet chili sauce', 220, 'Starters', 'https://images.unsplash.com/photo-1606525437817-0055ae15b7f6?w=400&h=300&fit=crop', False, True, False, False, False, 150, 15),
            ('Chicken Biryani', 'Fragrant basmati rice layered with spiced chicken', 380, 'Main Course', 'https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=400&h=300&fit=crop', True, False, True, True, True, 450, 30),
            ('Beef Nihari', 'Slow-cooked beef shank in rich gravy', 450, 'Main Course', 'https://images.unsplash.com/photo-1545247181-516773c36c2c?w=400&h=300&fit=crop', True, False, True, True, True, 520, 40),
            ('Chicken Karahi', 'Traditional wok-cooked chicken with tomatoes and ginger', 420, 'Main Course', 'https://images.unsplash.com/photo-1603034201644-0c9b6c0e6e3c?w=400&h=300&fit=crop', True, False, True, False, True, 380, 25),
            ('Daal Makhni', 'Slow-cooked black lentils in creamy butter sauce', 280, 'Main Course', 'https://images.unsplash.com/photo-1546833998-877b37c2e5c6?w=400&h=300&fit=crop', False, True, False, False, False, 320, 20),
            ('Butter Chicken', 'Creamy tomato-based curry with tender chicken', 400, 'Main Course', 'https://images.unsplash.com/photo-1603894584373-5ac82b2ae7c9?w=400&h=300&fit=crop', True, False, True, True, True, 420, 25),
            ('Mixed Vegetable Curry', 'Seasonal vegetables in aromatic curry sauce', 250, 'Main Course', 'https://images.unsplash.com/photo-1603073163308-9654c3fb70b7?w=400&h=300&fit=crop', False, True, False, False, False, 200, 20),
            ('Garlic Naan (2 pcs)', 'Oven-baked flatbread with garlic butter', 80, 'Main Course', 'https://images.unsplash.com/photo-1565557623262-b51c2513a641?w=400&h=300&fit=crop', False, True, False, False, False, 250, 10),
            ('Gulab Jamun (4 pcs)', 'Deep-fried milk dumplings in rose syrup', 200, 'Desserts', 'https://images.unsplash.com/photo-1666190050265-af93752b5658?w=400&h=300&fit=crop', True, False, False, True, False, 300, 10),
            ('Kheer', 'Traditional rice pudding with cardamom and nuts', 180, 'Desserts', 'https://images.unsplash.com/photo-1631452180519-c014fe946bc7?w=400&h=300&fit=crop', False, True, False, False, False, 220, 10),
            ('Ice Cream (2 scoops)', 'Choice of vanilla, chocolate, or mango', 150, 'Desserts', 'https://images.unsplash.com/photo-1501443762994-82bd5dace89a?w=400&h=300&fit=crop', False, True, False, False, False, 180, 5),
            ('Mango Lassi', 'Creamy yogurt drink blended with mango pulp', 180, 'Drinks', 'https://images.unsplash.com/photo-1579954115545-a95591f28bfc?w=400&h=300&fit=crop', True, True, False, True, False, 150, 5),
            ('Masala Chai', 'Traditional spiced milk tea', 120, 'Drinks', 'https://images.unsplash.com/photo-1563822249366-3efb23b8e0c7?w=400&h=300&fit=crop', True, True, False, True, False, 100, 5),
            ('Fresh Lime Water', 'Refreshing sweet and salty lime drink', 100, 'Drinks', 'https://images.unsplash.com/photo-1544145945-f90425340c7e?w=400&h=300&fit=crop', False, True, False, False, False, 80, 3),
            ('Soft Drinks', 'Coca-Cola, Sprite, Fanta, or 7-Up', 80, 'Drinks', 'https://images.unsplash.com/photo-1596803244618-8c702e3d227e?w=400&h=300&fit=crop', False, False, False, False, False, 140, 2),
        ]

        for item_data in menu_items_data:
            name, desc, price, cat_name, img, feat, veg, spicy, best, gf, cals, prep = item_data
            db.session.add(MenuItem(
                name=name, description=desc, price=price,
                category_id=cats[cat_name], image_url=img,
                is_featured=feat, is_vegetarian=veg,
                is_spicy=spicy, is_bestseller=best,
                is_gluten_free=gf, calories=cals,
                preparation_time=prep
            ))
        db.session.flush()

        items = {item.name: item.id for item in MenuItem.query.all()}

        modifier_data = [
            ('Chicken Biryani', [
                ('Extra Raita', 30, 'Add-ons'),
                ('Extra Green Salad', 40, 'Add-ons'),
                ('Half Portion', -100, 'Size'),
            ]),
            ('Butter Chicken', [
                ('Extra Naan', 40, 'Add-ons'),
                ('Extra Cheese', 50, 'Add-ons'),
            ]),
            ('Chicken Karahi', [
                ('Boneless', 50, 'Preference'),
                ('Extra Green Chilies', 0, 'Add-ons'),
            ]),
        ]

        for item_name, mods in modifier_data:
            if item_name in items:
                for mod_name, mod_price, mod_group in mods:
                    db.session.add(MenuItemModifier(
                        menu_item_id=items[item_name],
                        name=mod_name,
                        price_adjustment=mod_price,
                        group_name=mod_group
                    ))

    if FAQ.query.first() is None:
        faq_data = [
            ('What are your opening hours?', 'We are open Monday to Sunday from 11:00 AM to 11:00 PM.', 'General'),
            ('Do you offer home delivery?', 'Yes! Free delivery on orders above Rs. 1,000 within Lahore.', 'Orders'),
            ('How can I track my order?', 'Use your order number on our Track Order page.', 'Orders'),
            ('What payment methods do you accept?', 'Cash on Delivery and Online Payment.', 'Orders'),
            ('Do you accommodate dietary restrictions?', 'Yes! Our menu is labeled for vegetarian, gluten-free, and spicy options.', 'Menu'),
            ('Can I customize my order?', 'Yes! Many items have customization options like extra cheese and spice levels.', 'Menu'),
            ('Do you offer catering services?', 'Yes! Visit our Catering page for weddings, corporate events, and parties.', 'Events'),
            ('How do I make a table reservation?', 'Book through our Reservations page with date, time, and guests.', 'Reservations'),
            ('Do you have gift cards?', 'Yes! Available from Rs. 500 on our Gift Cards page.', 'Gift Cards'),
        ]
        for i, (q, a, c) in enumerate(faq_data):
            db.session.add(FAQ(question=q, answer=a, category=c, display_order=i))

    if GalleryImage.query.first() is None:
        gallery_data = [
            ('https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800&h=600&fit=crop', 'Our Restaurant', 'Elegant dining area'),
            ('https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=800&h=600&fit=crop', 'The Kitchen', 'Where chefs work magic'),
            ('https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=800&h=600&fit=crop', 'Fine Dining', 'Best Pakistani hospitality'),
            ('https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800&h=600&fit=crop', 'Signature Dishes', 'Award-winning cuisine'),
        ]
        for i, (url, title, desc) in enumerate(gallery_data):
            db.session.add(GalleryImage(image_url=url, title=title, description=desc, display_order=i))

    db.session.commit()

# Initialize database tables and seed data on startup (for Render/gunicorn)
# Startup: create tables and seed data (with error handling for Render/free tier)
with app.app_context():
    try:
        db.create_all()
        seed_database()
        print("✓ Database tables created and seeded successfully")
    except Exception as e:
        print(f"⚠ Database init warning (app will still start): {e}")
        # Tables might already exist, or DB might not be ready yet

if __name__ == '__main__':
    app.run(debug=True)

