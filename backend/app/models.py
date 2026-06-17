from datetime import datetime
from app.database import db

class CountryRule(db.Model):
    __tablename__ = 'country_rules'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    country_name = db.Column(db.String(100), nullable=False, unique=True)
    country_code = db.Column(db.String(10), nullable=False, unique=True)
    phone_length = db.Column(db.Integer, nullable=False)
    phone_prefix = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'country_name': self.country_name,
            'country_code': self.country_code,
            'phone_length': self.phone_length,
            'phone_prefix': self.phone_prefix,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class UploadedBatch(db.Model):
    __tablename__ = 'uploaded_batches'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    filename = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='PENDING') # PENDING, VALIDATING, COMPLETED, FAILED
    total_rows = db.Column(db.Integer, nullable=False, default=0)
    valid_rows = db.Column(db.Integer, nullable=False, default=0)
    error_rows = db.Column(db.Integer, nullable=False, default=0)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    transactions = db.relationship('Transaction', backref='batch', cascade='all, delete-orphan', lazy=True)
    errors = db.relationship('ValidationError', backref='batch', cascade='all, delete-orphan', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'status': self.status,
            'total_rows': self.total_rows,
            'valid_rows': self.valid_rows,
            'error_rows': self.error_rows,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('uploaded_batches.id', ondelete='CASCADE'), nullable=False)
    row_number = db.Column(db.Integer, nullable=False)
    order_id = db.Column(db.String(100), nullable=True)
    customer_name = db.Column(db.String(255), nullable=True)
    phone_number = db.Column(db.String(100), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    product_name = db.Column(db.String(255), nullable=True)
    quantity = db.Column(db.String(50), nullable=True)
    unit_price = db.Column(db.String(50), nullable=True)
    payment_mode = db.Column(db.String(100), nullable=True)
    transaction_date = db.Column(db.String(100), nullable=True)
    transaction_time = db.Column(db.String(100), nullable=True)
    is_valid = db.Column(db.Boolean, nullable=False, default=True)
    raw_data = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        import json
        d = {
            'id': self.id,
            'batch_id': self.batch_id,
            'row_number': self.row_number,
            'order_id': self.order_id,
            'customer_name': self.customer_name,
            'phone_number': self.phone_number,
            'country': self.country,
            'product_name': self.product_name,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'payment_mode': self.payment_mode,
            'transaction_date': self.transaction_date,
            'transaction_time': self.transaction_time,
            'is_valid': self.is_valid,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        if self.raw_data:
            try:
                d['raw_data'] = json.loads(self.raw_data)
            except Exception:
                d['raw_data'] = {}
        else:
            d['raw_data'] = {
                'order_id': self.order_id,
                'customer_name': self.customer_name,
                'phone_number': self.phone_number,
                'country': self.country,
                'product_name': self.product_name,
                'quantity': self.quantity,
                'unit_price': self.unit_price,
                'payment_mode': self.payment_mode,
                'transaction_date': self.transaction_date,
                'transaction_time': self.transaction_time
            }
        return d

class ValidationError(db.Model):
    __tablename__ = 'validation_errors'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('uploaded_batches.id', ondelete='CASCADE'), nullable=False)
    row_number = db.Column(db.Integer, nullable=False)
    field_name = db.Column(db.String(100), nullable=False)
    error_message = db.Column(db.String(255), nullable=False)
    error_code = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'batch_id': self.batch_id,
            'row_number': self.row_number,
            'field_name': self.field_name,
            'error_message': self.error_message,
            'error_code': self.error_code,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
