from flask import Flask, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import uuid
from decimal import Decimal
import pandas as pd
from io import BytesIO
import matplotlib.pyplot as plt
import seaborn as sns
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from flask import url_for
from flask import send_from_directory
from flask import send_file, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from io import BytesIO
import requests
from datetime import datetime



app = Flask(__name__)

# Konfiguratsiya
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:2710@localhost/warehouse_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'your-secret-key-here'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ma'lumotlar bazasi va JWT sozlamalari
db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app)

# Upload papkasini yaratish
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# MODELS
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.Enum('user', 'admin'), default='user')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    products = db.relationship('Product', backref='owner', lazy=True)
    entries = db.relationship('Entry', backref='user', lazy=True)
    exits = db.relationship('Exit', backref='user', lazy=True)
    expenses = db.relationship('Expense', backref='user', lazy=True)

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(100), nullable=True)
    barcode = db.Column(db.String(100), nullable=True)
    unit = db.Column(db.Enum('dona', 'kg', 'litr', 'metr', 'paket'), default='dona')
    purchase_price = db.Column(db.Numeric(10, 2), nullable=False)
    selling_price = db.Column(db.Numeric(10, 2), nullable=False)
    min_stock = db.Column(db.Integer, default=0)
    image_path = db.Column(db.String(255), nullable=True)
    expiry_date = db.Column(db.Date, nullable=True)
    description = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    entries = db.relationship('Entry', backref='product', lazy=True)
    exits = db.relationship('Exit', backref='product', lazy=True)

class Entry(db.Model):
    __tablename__ = 'entries'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    supplier_name = db.Column(db.String(200), nullable=True)
    entry_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date())
    notes = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Exit(db.Model):
    __tablename__ = 'exits'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    customer_name = db.Column(db.String(200), nullable=True)
    exit_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date())
    notes = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Expense(db.Model):
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.Enum('elektr', 'ijara', 'transport', 'ish_haqi', 'boshqa'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    expense_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date())
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)



# UTILITY FUNCTIONS
def get_stock_quantity(product_id):
    """Mahsulot qoldiq miqdorini hisoblash"""
    total_entries = db.session.query(db.func.sum(Entry.quantity)).filter_by(product_id=product_id).scalar() or 0
    total_exits = db.session.query(db.func.sum(Exit.quantity)).filter_by(product_id=product_id).scalar() or 0
    return total_entries - total_exits

def allowed_file(filename):
    """Ruxsat etilgan fayl formatlarini tekshirish"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
from sqlalchemy import func
def get_stock_quantity(product_id):
    total_entries = db.session.query(
        func.coalesce(func.sum(Entry.quantity), 0)
    ).filter_by(product_id=product_id).scalar()

    total_exits = db.session.query(
        func.coalesce(func.sum(Exit.quantity), 0)
    ).filter_by(product_id=product_id).scalar()

    return float(total_entries) - float(total_exits)

# AUTHENTICATION ENDPOINTS
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # Majburiy maydonlarni tekshirish
    if not data.get('email') or not data.get('password') or not data.get('full_name'):
        return jsonify({'error': 'Email, parol va to\'liq ism majburiy'}), 400
    
    # Email mavjudligini tekshirish
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Bu email allaqachon ro\'yxatdan o\'tgan'}), 400
    
    # Telefon mavjudligini tekshirish (agar berilgan bo'lsa)
    if data.get('phone') and User.query.filter_by(phone=data['phone']).first():
        return jsonify({'error': 'Bu telefon raqami allaqachon ro\'yxatdan o\'tgan'}), 400
    
    # Yangi foydalanuvchi yaratish
    user = User(
        email=data['email'],
        phone=data.get('phone'),
        password_hash=generate_password_hash(data['password']),
        full_name=data['full_name']
    )
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'message': 'Muvaffaqiyatli ro\'yxatdan o\'tdingiz'}), 201
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email va parol majburiy'}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({'error': 'Email yoki parol noto\'g\'ri'}), 401
    
    if not user.is_active:
        return jsonify({'error': 'Hisobingiz bloklangan'}), 403
    
    # JWT token yaratish, user.id ni stringga aylantirish
    access_token = create_access_token(identity=str(user.id))
    
    return jsonify({
        'access_token': access_token,
        'user': {
            'id': user.id,
            'email': user.email,
            'full_name': user.full_name,
            'role': user.role
        }
    })
@app.route('/api/profile', methods=['GET'])
@jwt_required()
def get_profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    return jsonify({
        'id': user.id,
        'email': user.email,
        'phone': user.phone,
        'full_name': user.full_name,
        'role': user.role,
        'is_active': user.is_active
    })

# PRODUCT ENDPOINTS
@app.route('/api/products', methods=['GET'])
@jwt_required()
def get_products():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if user.role == 'admin':
        # Admin barcha mahsulotlarni ko'ra oladi
        products = Product.query.all()
    else:
        # Oddiy foydalanuvchi faqat o'z mahsulotlarini ko'radi
        products = Product.query.filter_by(user_id=user_id).all()
    
    products_data = []
    for product in products:
        stock_quantity = get_stock_quantity(product.id)
        products_data.append({
            'id': product.id,
            'name': product.name,
            'code': product.code,
            'barcode': product.barcode,
            'unit': product.unit,
            'purchase_price': float(product.purchase_price),
            'selling_price': float(product.selling_price),
            'min_stock': product.min_stock,
            'current_stock': stock_quantity,
            'low_stock': stock_quantity <= product.min_stock,
            'image_path': product.image_path,
            'expiry_date': product.expiry_date.isoformat() if product.expiry_date else None,
            'description': product.description,
            'owner': product.owner.full_name if user.role == 'admin' else None
        })
    
    return jsonify(products_data)

@app.route('/api/products/<int:product_id>', methods=['GET'])
@jwt_required()
def get_product_by_id(product_id):
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if user.role == 'admin':
        product = Product.query.get(product_id)
    else:
        product = Product.query.filter_by(id=product_id, user_id=user_id).first()

    if not product:
        return jsonify({'error': 'Mahsulot topilmadi'}), 404

    stock_quantity = get_stock_quantity(product.id)
    return jsonify({
        'id': product.id,
        'name': product.name,
        'code': product.code,
        'barcode': product.barcode,
        'unit': product.unit,
        'purchase_price': float(product.purchase_price),
        'selling_price': float(product.selling_price),
        'min_stock': product.min_stock,
        'current_stock': stock_quantity,
        'low_stock': stock_quantity <= product.min_stock,
        'image_path': product.image_path,
        'expiry_date': product.expiry_date.isoformat() if product.expiry_date else None,
        'description': product.description,
        'owner': product.owner.full_name if user.role == 'admin' else None
    })


@app.route('/api/products', methods=['POST'])
@jwt_required()
def create_product():
    user_id = get_jwt_identity()
    data = request.form  # form-data dan o'qiladi
    file = request.files.get('image')  # rasm fayli

    # Majburiy maydonlar
    if not data.get('name') or not data.get('purchase_price') or not data.get('selling_price'):
        return jsonify({'error': 'Mahsulot nomi, kirim narxi va sotuv narxi majburiy'}), 400

    image_path = None
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        image_path = unique_filename  # Faqat fayl nomi saqlanadi

    product = Product(
        name=data['name'],
        code=data.get('code'),
        barcode=data.get('barcode'),
        unit=data.get('unit', 'dona'),
        purchase_price=Decimal(str(data['purchase_price'])),
        selling_price=Decimal(str(data['selling_price'])),
        min_stock=int(data.get('min_stock', 0)),
        description=data.get('description'),
        expiry_date=datetime.strptime(data['expiry_date'], '%Y-%m-%d').date() if data.get('expiry_date') else None,
        user_id=user_id,
        image_path=image_path
    )

    db.session.add(product)
    db.session.commit()

    return jsonify({'message': 'Mahsulot rasm bilan birga qo‘shildi', 'product_id': product.id}), 201


@app.route('/api/products/<int:product_id>', methods=['PUT'])
@jwt_required()
def update_product(product_id):
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if user.role == 'admin':
        product = Product.query.get(product_id)
    else:
        product = Product.query.filter_by(id=product_id, user_id=user_id).first()
    
    if not product:
        return jsonify({'error': 'Mahsulot topilmadi'}), 404
    
    data = request.get_json()
    
    product.name = data.get('name', product.name)
    product.code = data.get('code', product.code)
    product.barcode = data.get('barcode', product.barcode)
    product.unit = data.get('unit', product.unit)
    product.purchase_price = Decimal(str(data.get('purchase_price', product.purchase_price)))
    product.selling_price = Decimal(str(data.get('selling_price', product.selling_price)))
    product.min_stock = data.get('min_stock', product.min_stock)
    product.description = data.get('description', product.description)
    
    if data.get('expiry_date'):
        product.expiry_date = datetime.strptime(data['expiry_date'], '%Y-%m-%d').date()
    
    db.session.commit()
    
    return jsonify({'message': 'Mahsulot muvaffaqiyatli yangilandi'})

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
@jwt_required()
def delete_product(product_id):
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if user.role == 'admin':
        product = Product.query.get(product_id)
    else:
        product = Product.query.filter_by(id=product_id, user_id=user_id).first()
    
    if not product:
        return jsonify({'error': 'Mahsulot topilmadi'}), 404
    
    # Mahsulotga tegishli barcha yozuvlarni o'chirish
    Entry.query.filter_by(product_id=product_id).delete()
    Exit.query.filter_by(product_id=product_id).delete()
    
    db.session.delete(product)
    db.session.commit()
    
    return jsonify({'message': 'Mahsulot muvaffaqiyatli o\'chirildi'})

# ENTRY ENDPOINTS (Kirim)
@app.route('/api/entries', methods=['GET'])
@jwt_required()
def get_entries():
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)  # SQLAlchemy 2.0 usuli

    if user.role == 'admin':
        entries = Entry.query.join(Product).all()
    else:
        entries = Entry.query.filter_by(user_id=user_id).join(Product).all()

    entries_data = []
    for entry in entries:
        entries_data.append({
            'id': entry.id,
            'product_name': entry.product.name,
            'product_id': entry.product_id,
            'quantity': entry.quantity,
            'unit_price': float(entry.unit_price),
            'total_amount': float(entry.quantity) * float(entry.unit_price),  # Fix
            'supplier_name': entry.supplier_name,
            'entry_date': entry.entry_date.isoformat(),
            'notes': entry.notes,
            'user_name': entry.user.full_name if user.role == 'admin' else None
        })

    return jsonify(entries_data)


@app.route('/api/entries', methods=['POST'])
@jwt_required()
def create_entry():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data.get('product_id') or not data.get('quantity') or not data.get('unit_price'):
        return jsonify({'error': 'Mahsulot, miqdor va narx majburiy'}), 400
    
    # Mahsulotni tekshirish
    user = User.query.get(user_id)
    if user.role == 'admin':
        product = Product.query.get(data['product_id'])
    else:
        product = Product.query.filter_by(id=data['product_id'], user_id=user_id).first()
    
    if not product:
        return jsonify({'error': 'Mahsulot topilmadi'}), 404
    
    entry = Entry(
        product_id=data['product_id'],
        quantity=data['quantity'],
        unit_price=Decimal(str(data['unit_price'])),
        supplier_name=data.get('supplier_name'),
        notes=data.get('notes'),
        user_id=user_id
    )
    
    if data.get('entry_date'):
        entry.entry_date = datetime.strptime(data['entry_date'], '%Y-%m-%d').date()
    
    db.session.add(entry)
    db.session.commit()
    
    return jsonify({'message': 'Kirim muvaffaqiyatli qo\'shildi'}), 201

# EXIT ENDPOINTS (Chiqim/Sotish)
@app.route('/api/exits', methods=['GET'])
@jwt_required()
def get_exits():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if user.role == 'admin':
        exits = Exit.query.join(Product).all()
    else:
        exits = Exit.query.filter_by(user_id=user_id).join(Product).all()
    
    exits_data = []
    for exit in exits:
        exits_data.append({
            'id': exit.id,
            'product_name': exit.product.name,
            'product_id': exit.product_id,
            'quantity': exit.quantity,
            'unit_price': float(exit.unit_price),
            'total_amount': float(exit.quantity * exit.unit_price),
            'customer_name': exit.customer_name,
            'exit_date': exit.exit_date.isoformat(),
            'notes': exit.notes,
            'user_name': exit.user.full_name if user.role == 'admin' else None
        })
    
    return jsonify(exits_data)

@app.route('/api/exits', methods=['POST'])
@jwt_required()
def create_exit():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data.get('product_id') or not data.get('quantity') or not data.get('unit_price'):
        return jsonify({'error': 'Mahsulot, miqdor va narx majburiy'}), 400
    
    # Mahsulotni tekshirish
    user = User.query.get(user_id)
    if user.role == 'admin':
        product = Product.query.get(data['product_id'])
    else:
        product = Product.query.filter_by(id=data['product_id'], user_id=user_id).first()
    
    if not product:
        return jsonify({'error': 'Mahsulot topilmadi'}), 404
    
    # Qoldiq tekshirish
    current_stock = get_stock_quantity(data['product_id'])
    if current_stock < data['quantity']:
        return jsonify({'error': f'Omborda yetarli miqdor yo\'q. Mavjud: {current_stock}'}), 400
    
    exit = Exit(
        product_id=data['product_id'],
        quantity=data['quantity'],
        unit_price=Decimal(str(data['unit_price'])),
        customer_name=data.get('customer_name'),
        notes=data.get('notes'),
        user_id=user_id
    )
    
    if data.get('exit_date'):
        exit.exit_date = datetime.strptime(data['exit_date'], '%Y-%m-%d').date()
    
    db.session.add(exit)
    db.session.commit()
    
    return jsonify({'message': 'Chiqim muvaffaqiyatli qo\'shildi'}), 201

# STOCK ENDPOINTS (Qoldiq)
@app.route('/api/stock', methods=['GET'])
@jwt_required()
def get_stock():
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)

    if user.role == 'admin':
        products = Product.query.all()
    else:
        products = Product.query.filter_by(user_id=user_id).all()

    stock_data = []
    for product in products:
        stock_quantity = get_stock_quantity(product.id)
        stock_data.append({
            'product_id': product.id,
            'product_name': product.name,
            'unit': product.unit,
            'current_stock': stock_quantity,
            'min_stock': product.min_stock,
            'low_stock': stock_quantity <= product.min_stock,
            'stock_value': float(stock_quantity * float(product.purchase_price)), 
            'owner': product.owner.full_name if user.role == 'admin' else None
        })

    return jsonify(stock_data)


# EXPENSE ENDPOINTS (Xarajatlar)
@app.route('/api/expenses', methods=['GET'])
@jwt_required()
def get_expenses():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if user.role == 'admin':
        expenses = Expense.query.all()
    else:
        expenses = Expense.query.filter_by(user_id=user_id).all()
    
    expenses_data = []
    for expense in expenses:
        expenses_data.append({
            'id': expense.id,
            'category': expense.category,
            'amount': float(expense.amount),
            'description': expense.description,
            'expense_date': expense.expense_date.isoformat(),
            'user_name': User.query.get(expense.user_id).full_name if user.role == 'admin' else None
        })
    
    return jsonify(expenses_data)

@app.route('/api/expenses', methods=['POST'])
@jwt_required()
def create_expense():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data.get('category') or not data.get('amount'):
        return jsonify({'error': 'Kategoriya va miqdor majburiy'}), 400
    
    expense = Expense(
        category=data['category'],
        amount=Decimal(str(data['amount'])),
        description=data.get('description'),
        user_id=user_id
    )
    
    if data.get('expense_date'):
        expense.expense_date = datetime.strptime(data['expense_date'], '%Y-%m-%d').date()
    
    db.session.add(expense)
    db.session.commit()
    
    return jsonify({'message': 'Xarajat muvaffaqiyatli qo\'shildi'}), 201

# STATISTICS ENDPOINTS
@app.route('/api/statistics/sales', methods=['GET'])
@jwt_required()
def get_sales_statistics():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    period = request.args.get('period', 'monthly')  # daily, weekly, monthly

    # Sana oralig'ini aniqlash
    today = datetime.now().date()
    if period == 'daily':
        start_date = today - timedelta(days=30)
    elif period == 'weekly':
        start_date = today - timedelta(weeks=12)
    else:  # monthly
        start_date = today - timedelta(days=365)

    # Sotuvlarni olish
    if user.role == 'admin':
        exits = Exit.query.filter(Exit.exit_date >= start_date).join(Product).all()
    else:
        exits = Exit.query.filter(Exit.exit_date >= start_date, Exit.user_id == user_id).join(Product).all()

    # Statistikalarni hisoblash
    total_sales = sum(float(exit.quantity * exit.unit_price) for exit in exits)
    total_quantity = sum(exit.quantity for exit in exits)
    total_expense = sum(float(exit.quantity * exit.product.purchase_price) for exit in exits)  # chiqim

    # Top mahsulotlar
    product_sales = {}
    for exit in exits:
        if exit.product_id in product_sales:
            product_sales[exit.product_id]['quantity'] += exit.quantity
            product_sales[exit.product_id]['revenue'] += float(exit.quantity * exit.unit_price)
        else:
            product_sales[exit.product_id] = {
                'name': exit.product.name,
                'quantity': exit.quantity,
                'revenue': float(exit.quantity * exit.unit_price)
            }

    # Top mahsulotlarni saralash
    top_products = sorted(product_sales.items(), key=lambda x: x[1]['revenue'], reverse=True)[:10]

    return jsonify({
        'total_sales': total_sales,
        'total_quantity': total_quantity,
        'total_expense': total_expense,
        'top_products': [{'name': p[1]['name'], 'quantity': p[1]['quantity'], 'revenue': p[1]['revenue']} for p in top_products],
        'period': period
    })


# ADMIN ENDPOINTS
@app.route('/api/admin/users', methods=['GET'])
@jwt_required()
def get_users():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if user.role != 'admin':
        return jsonify({'error': 'Ruxsat etilmagan'}), 403
    
    users = User.query.all()
    users_data = []
    for u in users:
        # Har bir foydalanuvchi uchun statistika
        total_products = Product.query.filter_by(user_id=u.id).count()
        total_sales = db.session.query(db.func.sum(Exit.quantity * Exit.unit_price)).filter_by(user_id=u.id).scalar() or 0
        
        users_data.append({
            'id': u.id,
            'email': u.email,
            'full_name': u.full_name,
            'phone': u.phone,
            'role': u.role,
            'is_active': u.is_active,
            'total_products': total_products,
            'total_sales': float(total_sales),
            'created_at': u.created_at.isoformat()
        })
    
    return jsonify(users_data)

@app.route('/api/admin/users/<int:user_id>/toggle', methods=['PUT'])
@jwt_required()
def toggle_user_status(user_id):
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)

    if current_user.role != 'admin':
        return jsonify({'error': 'Ruxsat etilmagan'}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Foydalanuvchi topilmadi'}), 404

    user.is_active = not user.is_active
    db.session.commit()

    status = "faollashtirildi" if user.is_active else "bloklandi"

    return jsonify({
        'message': f'Foydalanuvchi {status}',
        'is_active': user.is_active  # ← MUHIM
    })


# EXPORT ENDPOINTS
@app.route('/api/export/excel', methods=['GET'])
@jwt_required()
def export_excel():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    export_type = request.args.get('type', 'products')  # products, entries, exits, stock
    
    # Ma'lumotlarni olish
    if export_type == 'products':
        if user.role == 'admin':
            products = Product.query.all()
        else:
            products = Product.query.filter_by(user_id=user_id).all()
        
        data = []
        for product in products:
            stock_quantity = get_stock_quantity(product.id)
            data.append({
                'Nomi': product.name,
                'Kodi': product.code,
                'Barcode': product.barcode,
                'Birlik': product.unit,
                'Kirim narxi': float(product.purchase_price),
                'Sotuv narxi': float(product.selling_price),
                'Joriy qoldiq': stock_quantity,
                'Min qoldiq': product.min_stock,
                'Egasi': product.owner.full_name if user.role == 'admin' else user.full_name
            })
    
    elif export_type == 'entries':
        if user.role == 'admin':
            entries = Entry.query.join(Product).all()
        else:
            entries = Entry.query.filter_by(user_id=user_id).join(Product).all()
        
        data = []
        for entry in entries:
            data.append({
                'Mahsulot': entry.product.name,
                'Miqdori': entry.quantity,
                'Narxi': float(entry.unit_price),
                'Jami': float(entry.quantity * entry.unit_price),
                'Ta\'minotchi': entry.supplier_name,
                'Sana': entry.entry_date.isoformat(),
                'Izoh': entry.notes
            })
    
    # Excel faylini yaratish
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=export_type.title())
    
    output.seek(0)
    filename = f'{export_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

@app.route('/api/export/pdf', methods=['GET'])
@jwt_required()
def export_pdf():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    export_type = request.args.get('type', 'stock')
    
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Sarlavha
    title = Paragraph(f"<b>{export_type.title()} Hisoboti</b>", styles['Title'])
    elements.append(title)
    
    # Sana
    date_para = Paragraph(f"Sana: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal'])
    elements.append(date_para)
    elements.append(Paragraph("<br/>", styles['Normal']))
    
    # Ma'lumotlar
    if export_type == 'stock':
        if user.role == 'admin':
            products = Product.query.all()
        else:
            products = Product.query.filter_by(user_id=user_id).all()
        
        data = [['Mahsulot', 'Birlik', 'Joriy qoldiq', 'Min qoldiq', 'Holat']]
        for product in products:
            stock_quantity = get_stock_quantity(product.id)
            status = "Kam qoldiq" if stock_quantity <= product.min_stock else "Normal"
            data.append([
                product.name,
                product.unit,
                str(stock_quantity),
                str(product.min_stock),
                status
            ])
    
    # Jadval yaratish
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    doc.build(elements)
    
    output.seek(0)
    filename = f'{export_type}_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    
    return send_file(
        output,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

# SEARCH ENDPOINTS
@app.route('/api/search', methods=['GET'])
@jwt_required()
def search():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'products')  # products, entries, exits

    if not query:
        return jsonify({'error': 'Qidiruv so\'zi kiritilmagan'}), 400

    results = []

    if search_type == 'products':
        if user.role == 'admin':
            products = Product.query.filter(
                (Product.name.contains(query)) |
                (Product.code.contains(query)) |
                (Product.barcode.contains(query))
            ).all()
        else:
            products = Product.query.filter(
                Product.user_id == user_id,
                (Product.name.contains(query)) |
                (Product.code.contains(query)) |
                (Product.barcode.contains(query))
            ).all()

        for product in products:
            stock_quantity = get_stock_quantity(product.id)
            results.append({
                'id': product.id,
                'name': product.name,
                'code': product.code,
                'current_stock': stock_quantity,
                'purchase_price': float(product.purchase_price),
                'selling_price': float(product.selling_price),
                'image_path': product.image_path  # ✅ RASM YO‘LI QO‘SHILDI
            })

    return jsonify(results)


# NOTIFICATION ENDPOINTS
@app.route('/api/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    notifications = []

    # Foydalanuvchiga tegishli mahsulotlar
    if user.role == 'admin':
        products = Product.query.all()
    else:
        products = Product.query.filter_by(user_id=user_id).all()

  
    for product in products:
        stock_quantity = get_stock_quantity(product.id)
        if stock_quantity <= product.min_stock:
            notifications.append({
                'type': 'low_stock',
                'title': 'Kam qoldiq',
                'message': f"{product.name} mahsulotidan kam qoldiq: {stock_quantity} {product.unit}",
                'product_id': product.id,
                'priority': 'high' if stock_quantity == 0 else 'medium'
            })

    return jsonify(notifications)


# IMAGE UPLOAD ENDPOINT
@app.route('/api/upload/image', methods=['POST'])
@jwt_required()
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'Fayl tanlanmagan'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Fayl tanlanmagan'}), 400
    
    if file and allowed_file(file.filename):
        # Fayl nomini xavfsiz qilish
        filename = secure_filename(file.filename)
        unique_filename = f"{str(uuid.uuid4())}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        file.save(filepath)
        
        return jsonify({
            'message': 'Rasm muvaffaqiyatli yuklandi',
            'filename': unique_filename,
            'path': filepath
        }), 201
    
    return jsonify({'error': 'Noto\'g\'ri fayl formati'}), 400

# DASHBOARD ANALYTICS
@app.route('/api/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    # Asosiy statistikalar
    if user.role == 'admin':
        total_products = Product.query.count()
        total_users = User.query.count()
        today_sales = Exit.query.filter(Exit.exit_date == datetime.now().date()).all()
        monthly_sales = Exit.query.filter(
            Exit.exit_date >= datetime.now().date().replace(day=1)
        ).all()
    else:
        total_products = Product.query.filter_by(user_id=user_id).count()
        total_users = 1
        today_sales = Exit.query.filter(
            Exit.exit_date == datetime.now().date(),
            Exit.user_id == user_id
        ).all()
        monthly_sales = Exit.query.filter(
            Exit.exit_date >= datetime.now().date().replace(day=1),
            Exit.user_id == user_id
        ).all()
    
    today_revenue = sum(float(sale.quantity * sale.unit_price) for sale in today_sales)
    monthly_revenue = sum(float(sale.quantity * sale.unit_price) for sale in monthly_sales)
    
    # Kam qoldiq mahsulotlar soni
    low_stock_count = 0
    if user.role == 'admin':
        products = Product.query.all()
    else:
        products = Product.query.filter_by(user_id=user_id).all()
    
    for product in products:
        if get_stock_quantity(product.id) <= product.min_stock:
            low_stock_count += 1
    
    # Ombor qiymati
    total_stock_value = 0
    for product in products:
        stock_qty = get_stock_quantity(product.id)
        total_stock_value += float(stock_qty * product.purchase_price)
    
    return jsonify({
        'total_products': total_products,
        'total_users': total_users,
        'today_revenue': today_revenue,
        'monthly_revenue': monthly_revenue,
        'low_stock_count': low_stock_count,
        'total_stock_value': total_stock_value,
        'today_sales_count': len(today_sales),
        'monthly_sales_count': len(monthly_sales)
    })

# CHART DATA ENDPOINTS
@app.route('/api/charts/sales', methods=['GET'])
@jwt_required()
def get_sales_chart():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    period = request.args.get('period', 'weekly')  # daily, weekly, monthly
    
    # So'nggi 30 kunlik ma'lumotlar
    today = datetime.now().date()
    start_date = today - timedelta(days=30)
    
    if user.role == 'admin':
        sales = Exit.query.filter(Exit.exit_date >= start_date).all()
    else:
        sales = Exit.query.filter(
            Exit.exit_date >= start_date,
            Exit.user_id == user_id
        ).all()
    
    # Kunlik sotuvlarni guruhlash
    daily_sales = {}
    current_date = start_date
    while current_date <= today:
        daily_sales[current_date.isoformat()] = 0
        current_date += timedelta(days=1)
    
    for sale in sales:
        date_key = sale.exit_date.isoformat()
        if date_key in daily_sales:
            daily_sales[date_key] += float(sale.quantity * sale.unit_price)
    
    chart_data = [
        {'date': date, 'sales': amount}
        for date, amount in daily_sales.items()
    ]
    
    return jsonify(chart_data)

# ERROR HANDLERS
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Sahifa topilmadi'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Server xatosi'}), 500

@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Noto\'g\'ri so\'rov'}), 400

# DATABASE INITIALIZATION
@app.before_first_request
def create_tables():
    db.create_all()
    
    # Admin foydalanuvchisini yaratish (agar mavjud bo'lmasa)
    admin = User.query.filter_by(email='admin@warehouse.com').first()
    if not admin:
        admin_user = User(
            email='admin@warehouse.com',
            password_hash=generate_password_hash('admin123'),
            full_name='Super Admin',
            role='admin'
        )
        db.session.add(admin_user)
        db.session.commit()
        print("Super Admin yaratildi: admin@warehouse.com / admin123")

# ADDITIONAL UTILITY ENDPOINTS
@app.route('/api/backup', methods=['POST'])
@jwt_required()
def create_backup():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if user.role != 'admin':
        return jsonify({'error': 'Faqat admin zaxira nusxa olishi mumkin'}), 403
    
    # Barcha ma'lumotlarni eksport qilish
    backup_data = {
        'users': [
            {
                'email': u.email,
                'full_name': u.full_name,
                'phone': u.phone,
                'role': u.role,
                'created_at': u.created_at.isoformat()
            }
            for u in User.query.all()
        ],
        'products': [
            {
                'name': p.name,
                'code': p.code,
                'barcode': p.barcode,
                'unit': p.unit,
                'purchase_price': float(p.purchase_price),
                'selling_price': float(p.selling_price),
                'min_stock': p.min_stock,
                'owner_email': p.owner.email
            }
            for p in Product.query.all()
        ],
        'entries': [
            {
                'product_name': e.product.name,
                'quantity': e.quantity,
                'unit_price': float(e.unit_price),
                'supplier_name': e.supplier_name,
                'entry_date': e.entry_date.isoformat(),
                'user_email': e.user.email
            }
            for e in Entry.query.all()
        ],
        'exits': [
            {
                'product_name': e.product.name,
                'quantity': e.quantity,
                'unit_price': float(e.unit_price),
                'customer_name': e.customer_name,
                'exit_date': e.exit_date.isoformat(),
                'user_email': e.user.email
            }
            for e in Exit.query.all()
        ],
        'backup_date': datetime.now().isoformat()
    }
    
    return jsonify({
        'message': 'Zaxira nusxa tayyor',
        'data': backup_data
    })

# CONFIGURATION ENDPOINT
@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify({
        'app_name': 'Ombor Hisoboti',
        'version': '1.0.0',
        'max_file_size': app.config['MAX_CONTENT_LENGTH'],
        'allowed_image_formats': ['png', 'jpg', 'jpeg', 'gif'],
        'currency': 'UZS',
        'date_format': 'YYYY-MM-DD'
    })





@app.route('/api/admin/download/backup', methods=['GET'])
@jwt_required()
def download_admin_backup():
    user = User.query.get(get_jwt_identity())
    if user.role != 'admin':
        return jsonify({'error': 'Faqat admin yuklaydi'}), 403

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    def write_line(text, font="Helvetica", size=10, bold=False):
        nonlocal y
        if y < 80:
            pdf.showPage()
            y = height - 50
        pdf.setFont(font if not bold else "Helvetica-Bold", size)
        pdf.drawString(50, y, text)
        y -= 15

    write_line("📁 ADMIN ZAXIRA HISOBOTI", size=14, bold=True)
    write_line(f"Sana: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 10

    write_line("👤 FOYDALANUVCHILAR:", bold=True)
    for u in User.query.all():
        write_line(f"- {u.full_name} | {u.email} | {u.role} | {u.phone} | {u.created_at.strftime('%Y-%m-%d')}")

    y -= 10
    write_line("📦 MAHSULOTLAR:", bold=True)
    for p in Product.query.all():
        write_line(f"- {p.name} | {p.code} | {p.selling_price} so'm | Min: {p.min_stock}")
        if p.image_path:
            try:
                img_path = os.path.join(app.config['UPLOAD_FOLDER'], p.image_path)
                if os.path.exists(img_path):
                    img = ImageReader(img_path)
                    pdf.drawImage(img, 60, y - 60, width=60, height=60)
                    y -= 65
            except Exception:
                write_line("⛔ Rasm yuklanmadi")

    y -= 10
    write_line("📥 KIRIMLAR:", bold=True)
    for e in Entry.query.all():
        write_line(f"- {e.product.name} | {e.quantity} dona | {e.unit_price} so'm | {e.entry_date.strftime('%Y-%m-%d')}")

    y -= 10
    write_line("📤 CHIQIMLAR:", bold=True)
    for x in Exit.query.all():
        write_line(f"- {x.product.name} | {x.quantity} dona | {x.unit_price} so'm | {x.exit_date.strftime('%Y-%m-%d')}")

    pdf.save()
    buffer.seek(0)

    # ⏳ Telegramga yuborish
    TELEGRAM_BOT_TOKEN = '7505491330:AAHYS2XsTTihFpTSsU7MHexioa2ZgVtqNtI'
    TELEGRAM_CHAT_ID = '7093186163'

    try:
        files = {
            'document': ('admin_backup.pdf', buffer, 'application/pdf')
        }
        data = {
            'chat_id': TELEGRAM_CHAT_ID,
            'caption': '🗂 Admin backup fayli'
        }
        telegram_url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument'
        requests.post(telegram_url, data=data, files=files)
    except Exception as e:
        print("Telegramga yuborishda xatolik:", e)

    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='admin_backup.pdf', mimetype='application/pdf')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)