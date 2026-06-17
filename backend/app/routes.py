import os
import threading
from flask import Blueprint, request, jsonify, send_from_directory, current_app, Response
from werkzeug.utils import secure_filename
from app.database import db
from app.models import UploadedBatch, Transaction, ValidationError, CountryRule
from app.validation import process_batch

api = Blueprint('api', __name__)

ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@api.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected for uploading'}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        
        # Save placeholder batch
        batch = UploadedBatch(filename=filename, status='PENDING')
        db.session.add(batch)
        db.session.commit()
        
        # Save file to uploads folder
        file_ext = os.path.splitext(filename)[1].lower()
        saved_filename = f"batch_{batch.id}{file_ext}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], saved_filename)
        file.save(filepath)
        
        # Start validation in a separate thread
        app = current_app._get_current_object()
        threshold = current_app.config['ROW_SPLIT_THRESHOLD']
        
        thread = threading.Thread(target=process_batch, args=(app, batch.id, filepath, threshold))
        thread.start()
        
        return jsonify({
            'message': 'File uploaded successfully, validation started in the background.',
            'batch': batch.to_dict()
        }), 202
        
    return jsonify({'error': 'Allowed file types are CSV, XLSX, and XLS'}), 400

@api.route('/upload/demo-intern', methods=['POST'])
def upload_demo_intern():
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    project_root = os.path.dirname(base_dir)
    excel_path = os.path.join(project_root, 'excel', 'TAM_INTERN_TABLE.xlsx')
    
    if not os.path.exists(excel_path):
        excel_path = os.path.join(base_dir, 'excel', 'TAM_INTERN_TABLE.xlsx')
        if not os.path.exists(excel_path):
            return jsonify({'error': 'Sample TAM_INTERN_TABLE.xlsx not found on server disk'}), 404
            
    batch = UploadedBatch(filename='TAM_INTERN_TABLE.xlsx', status='PENDING')
    db.session.add(batch)
    db.session.commit()
    
    saved_filename = f"batch_{batch.id}.xlsx"
    dest_path = os.path.join(current_app.config['UPLOAD_FOLDER'], saved_filename)
    import shutil
    shutil.copy(excel_path, dest_path)
    
    app = current_app._get_current_object()
    threshold = current_app.config['ROW_SPLIT_THRESHOLD']
    
    thread = threading.Thread(target=process_batch, args=(app, batch.id, dest_path, threshold))
    thread.start()
    
    return jsonify({
        'message': 'TAM Intern Spreadsheet loaded successfully, validation started in the background.',
        'batch': batch.to_dict()
    }), 202

@api.route('/batches', methods=['GET'])
def get_batches():
    batches = UploadedBatch.query.order_by(UploadedBatch.uploaded_at.desc()).all()
    return jsonify([b.to_dict() for b in batches]), 200

@api.route('/batches/<int:batch_id>', methods=['GET'])
def get_batch(batch_id):
    batch = db.session.get(UploadedBatch, batch_id)
    if not batch:
        return jsonify({'error': f'Batch with ID {batch_id} not found'}), 404
    return jsonify(batch.to_dict()), 200

@api.route('/batches/<int:batch_id>/errors', methods=['GET'])
def get_batch_errors(batch_id):
    batch = db.session.get(UploadedBatch, batch_id)
    if not batch:
        return jsonify({'error': f'Batch with ID {batch_id} not found'}), 404
        
    errors = ValidationError.query.filter_by(batch_id=batch_id).order_by(ValidationError.row_number.asc()).all()
    return jsonify([e.to_dict() for e in errors]), 200

@api.route('/batches/<int:batch_id>/transactions', methods=['GET'])
def get_batch_transactions(batch_id):
    batch = db.session.get(UploadedBatch, batch_id)
    if not batch:
        return jsonify({'error': f'Batch with ID {batch_id} not found'}), 404
        
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    is_valid_filter = request.args.get('is_valid', None)
    
    query = Transaction.query.filter_by(batch_id=batch_id)
    
    if is_valid_filter is not None:
        is_valid_bool = is_valid_filter.lower() == 'true'
        query = query.filter_by(is_valid=is_valid_bool)
        
    paginated_results = query.order_by(Transaction.row_number.asc()).paginate(page=page, per_page=per_page, error_out=False)
    
    # Extract headers list dynamically from the first transaction in this batch
    first_tx = Transaction.query.filter_by(batch_id=batch_id).first()
    headers = []
    if first_tx and first_tx.raw_data:
        try:
            import json
            headers = list(json.loads(first_tx.raw_data).keys())
        except Exception:
            pass
            
    return jsonify({
        'transactions': [t.to_dict() for t in paginated_results.items],
        'headers': headers,
        'total_items': paginated_results.total,
        'page': page,
        'per_page': per_page,
        'pages': paginated_results.pages
    }), 200

@api.route('/batches/<int:batch_id>/download/clean', methods=['GET'])
def download_clean_file(batch_id):
    batch = db.session.get(UploadedBatch, batch_id)
    if not batch:
        return jsonify({'error': f'Batch with ID {batch_id} not found'}), 404
        
    if batch.status != 'COMPLETED':
        return jsonify({'error': 'Batch validation is not complete or failed'}), 400
        
    threshold = current_app.config['ROW_SPLIT_THRESHOLD']
    uploads_dir = current_app.config['UPLOAD_FOLDER']
    
    if batch.total_rows > threshold:
        # Deliver ZIP file containing chunked CSVs
        filename = f"clean_batch_{batch_id}.zip"
    else:
        # Deliver single CSV file
        filename = f"clean_batch_{batch_id}.csv"
        
    filepath = os.path.join(uploads_dir, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'Cleaned output file not found on disk'}), 404
        
    return send_from_directory(
        directory=uploads_dir,
        path=filename,
        as_attachment=True,
        download_name=f"cleaned_transactions_batch_{batch_id}{os.path.splitext(filename)[1]}"
    )

@api.route('/batches/<int:batch_id>/download/errors', methods=['GET'])
def download_errors_file(batch_id):
    batch = db.session.get(UploadedBatch, batch_id)
    if not batch:
        return jsonify({'error': f'Batch with ID {batch_id} not found'}), 404
        
    uploads_dir = current_app.config['UPLOAD_FOLDER']
    filename = f"errors_batch_{batch_id}.csv"
    filepath = os.path.join(uploads_dir, filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'Error report file not found on disk'}), 404
        
    return send_from_directory(
        directory=uploads_dir,
        path=filename,
        as_attachment=True,
        download_name=f"error_report_batch_{batch_id}.csv"
    )

@api.route('/rules', methods=['GET', 'POST'])
def manage_rules():
    if request.method == 'GET':
        rules = CountryRule.query.order_by(CountryRule.country_name.asc()).all()
        return jsonify([r.to_dict() for r in rules]), 200
        
    elif request.method == 'POST':
        data = request.json or {}
        country_name = data.get('country_name', '').strip()
        country_code = data.get('country_code', '').strip().upper()
        phone_length = data.get('phone_length')
        phone_prefix = data.get('phone_prefix', '').strip()
        
        if not country_name or not country_code or phone_length is None or not phone_prefix:
            return jsonify({'error': 'country_name, country_code, phone_length, and phone_prefix are required'}), 400
            
        try:
            phone_length = int(phone_length)
            if phone_length <= 0:
                raise ValueError()
        except ValueError:
            return jsonify({'error': 'phone_length must be a positive integer'}), 400
            
        # Add + to prefix if missing
        if not phone_prefix.startswith('+'):
            phone_prefix = '+' + phone_prefix
            
        # Check if rule already exists (either by name or code)
        rule = CountryRule.query.filter(
            (CountryRule.country_name == country_name) | 
            (CountryRule.country_code == country_code)
        ).first()
        
        if rule:
            rule.country_name = country_name
            rule.country_code = country_code
            rule.phone_length = phone_length
            rule.phone_prefix = phone_prefix
            message = 'Country rule updated successfully.'
        else:
            rule = CountryRule(
                country_name=country_name,
                country_code=country_code,
                phone_length=phone_length,
                phone_prefix=phone_prefix
            )
            db.session.add(rule)
            message = 'Country rule created successfully.'
            
        db.session.commit()
        return jsonify({'message': message, 'rule': rule.to_dict()}), 200

@api.route('/batches/<int:batch_id>', methods=['DELETE'])
def delete_batch(batch_id):
    batch = db.session.get(UploadedBatch, batch_id)
    if not batch:
        return jsonify({'error': f'Batch with ID {batch_id} not found'}), 404
        
    # Delete uploaded files on disk if they exist
    uploads_dir = current_app.config['UPLOAD_FOLDER']
    
    # 1. Raw file
    file_ext = os.path.splitext(batch.filename)[1].lower()
    raw_file = f"batch_{batch_id}{file_ext}"
    raw_path = os.path.join(uploads_dir, raw_file)
    if os.path.exists(raw_path):
        try: os.remove(raw_path)
        except Exception: pass
        
    # 2. Cleaned file
    clean_csv = f"clean_batch_{batch_id}.csv"
    clean_csv_path = os.path.join(uploads_dir, clean_csv)
    if os.path.exists(clean_csv_path):
        try: os.remove(clean_csv_path)
        except Exception: pass
        
    # 3. Cleaned ZIP file
    clean_zip = f"clean_batch_{batch_id}.zip"
    clean_zip_path = os.path.join(uploads_dir, clean_zip)
    if os.path.exists(clean_zip_path):
        try: os.remove(clean_zip_path)
        except Exception: pass
        
    # 4. Errors report file
    err_csv = f"errors_batch_{batch_id}.csv"
    err_csv_path = os.path.join(uploads_dir, err_csv)
    if os.path.exists(err_csv_path):
        try: os.remove(err_csv_path)
        except Exception: pass
        
    # Delete from database (cascade will handle Transactions and ValidationErrors)
    db.session.delete(batch)
    db.session.commit()
    
    return jsonify({'message': 'Batch audit log and files deleted successfully'}), 200

@api.route('/template', methods=['GET'])
def download_template():
    # Generate static sample template on the fly and return as attachment
    headers = "order_id,customer_name,phone_number,country,product_name,quantity,unit_price,payment_mode,transaction_date,transaction_time\n"
    # Example rows demonstrating validation behavior
    row1 = "TXN10001,Rajesh Kumar,+919876543210,India,Wireless Mouse,2,15.50,UPI,2026-06-15,14:30:00\n"
    row2 = "TXN10002,Li Wei,81234567,Singapore,Mechanical Keyboard,1,85.00,Credit Card,15-06-2026,09:15 AM\n"
    row3 = "TXN10003,Sarah Connor,+12135550199,United States,Gaming Monitor,1,299.99,PayPal,06/15/2026,18:45:30\n"
    row4 = "TXN10004,Invalid Quantity User,+919876543210,India,Mousepad,-5,10.00,UPI,2026-06-15,10:00:00\n" # quantity <= 0
    row5 = "TXN10005,Wrong Phone User,+91123,India,Headset,1,50.00,Cash,2026-06-15,10:30:00\n" # wrong phone len
    
    csv_content = headers + row1 + row2 + row3 + row4 + row5
    
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=transaction_template_sample.csv"}
    )
