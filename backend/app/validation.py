import os
import re
import json
import zipfile
import pandas as pd
from datetime import datetime, timedelta
from app.database import db
from app.models import UploadedBatch, Transaction, ValidationError, CountryRule

ALLOWED_PAYMENT_MODES = {
    'credit card', 'debit card', 'upi', 'net banking', 'paypal', 'cash'
}

ACCEPTED_DATE_FORMATS = [
    '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%Y/%m/%d', '%d/%m/%Y',
    '%Y-%m-%d %H:%M:%S', '%d-%m-%Y %H:%M:%S', '%m/%d/%Y %H:%M:%S',
    '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f'
]

ACCEPTED_TIME_FORMATS = [
    '%H:%M:%S', '%H:%M', '%I:%M:%S %p', '%I:%M %p', '%H:%M:%S.%f'
]

def get_edit_distance(s1, s2):
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i-1] == s2[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
    return dp[m][n]

VALID_PROVIDERS = {'gmail', 'email', 'hotmail', 'yahoo', 'outlook', 'icloud', 'aol', 'zoho', 'protonmail', 'yandex', 'mail'}

def validate_email(email_val, email_required=True):
    if email_val is None or pd.isna(email_val) or str(email_val).strip() == '':
        if email_required:
            return False, "Email field is empty", "MISSING_FIELD", None
        else:
            return True, None, None, None
            
    val_str = str(email_val).strip()
    
    # 1. General email format regex (local-part@domain.tld)
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, val_str):
        return False, f"Email '{val_str}' is invalid.", "EMAIL_FORMAT_INVALID", None
        
    try:
        local_part, domain = val_str.rsplit('@', 1)
    except ValueError:
        return False, f"Email '{val_str}' is invalid.", "EMAIL_FORMAT_INVALID", None
        
    domain_lower = domain.lower()
    provider = domain_lower.split('.')[0]
    
    # 2. Gmail typo check (e.g. gmail.co or gmial.com)
    if domain_lower != 'gmail.com' and provider == 'gmail':
        return False, f"Did you mean gmail.com? Got: {domain}", "LIKELY_DOMAIN_TYPO", f"{local_part}@gmail.com"
        
    if provider != 'gmail':
        dist = get_edit_distance(provider, 'gmail')
        if dist <= 2 and provider not in VALID_PROVIDERS:
            return False, f"Did you mean gmail.com? Got: {domain}", "LIKELY_DOMAIN_TYPO", f"{local_part}@gmail.com"
            
    # 3. Check if domain contains valid mail providers, not names (like balakrishnan)
    if provider not in VALID_PROVIDERS:
        return False, f"Email has invalid domain '{domain}'. Only valid mail services allowed.", "INVALID_EMAIL_DOMAIN", f"{local_part}@gmail.com"
            
    return True, None, None, None

def validate_phone(phone, country, rules_dict):
    if pd.isna(phone) or str(phone).strip() == '':
        return False, "Phone number is empty"
    
    phone_str = str(phone).strip()
    if phone_str.endswith('.0'):
        phone_str = phone_str[:-2]
        
    # Strip spaces, dashes, parentheses
    chars_to_strip = " -()–—"
    stripped_phone = "".join(c for c in phone_str if c not in chars_to_strip)
    
    country_str = str(country).strip().upper() if country and not pd.isna(country) else ''
    rule = rules_dict.get(country_str) if country_str else None
    
    if not rule:
        # Fallback validation: 7-15 digits
        digits_only = "".join(c for c in stripped_phone if c.isdigit())
        if 7 <= len(digits_only) <= 15:
            return True, None
        return False, f"Phone length ({len(digits_only)}) falls outside fallback range of 7-15 digits."
        
    prefix = rule['phone_prefix']        # e.g., "+91"
    expected_len = rule['phone_length']   # e.g., 10
    clean_prefix = prefix.replace('+', '')
    
    if stripped_phone.startswith('+'):
        if not stripped_phone.startswith(prefix):
            return False, f"Phone starts with + but does not match country prefix {prefix}"
        local_part = stripped_phone[len(prefix):]
        digits_only = "".join(c for c in local_part if c.isdigit())
        if len(digits_only) != expected_len:
            return False, f"Phone length after prefix {prefix} is {len(digits_only)}, expected {expected_len}"
        return True, None
    else:
        digits_only = "".join(c for c in stripped_phone if c.isdigit())
        if len(digits_only) == expected_len:
            return True, None
        if stripped_phone.startswith(clean_prefix):
            local_part = stripped_phone[len(clean_prefix):]
            local_digits = "".join(c for c in local_part if c.isdigit())
            if len(local_digits) == expected_len:
                return True, None
                
        return False, f"Phone does not match expected length of {expected_len} digits (prefix: {prefix})"

def validate_date(date_val, earliest_date_str='2000-01-01'):
    if pd.isna(date_val) or str(date_val).strip() == '':
        return False, "Date is empty", "MISSING_FIELD"
    
    if isinstance(date_val, (datetime, pd.Timestamp)):
        dt_res = date_val.strftime('%Y-%m-%d')
    else:
        date_str = str(date_val).strip()
        parsed = False
        dt_res = None
        for fmt in ACCEPTED_DATE_FORMATS:
            try:
                dt = datetime.strptime(date_str, fmt)
                dt_res = dt.strftime('%Y-%m-%d')
                parsed = True
                break
            except ValueError:
                continue
                
        if not parsed:
            try:
                dt = pd.to_datetime(date_str)
                if not pd.isna(dt):
                    dt_res = dt.strftime('%Y-%m-%d')
                    parsed = True
            except Exception:
                pass
                
        if not parsed:
            return False, f"Date '{date_val}' does not match any accepted formats (e.g. YYYY-MM-DD)", "DATE_INVALID"
            
    # Range check
    try:
        dt_obj = datetime.strptime(dt_res, '%Y-%m-%d')
        earliest_dt = datetime.strptime(earliest_date_str, '%Y-%m-%d')
        max_dt = datetime.utcnow() + timedelta(days=1)
        if dt_obj < earliest_dt or dt_obj > max_dt:
            return False, f"Date '{dt_res}' is out of range ({earliest_date_str} to {max_dt.strftime('%Y-%m-%d')}).", "DATE_OUT_OF_RANGE"
    except Exception as e:
        return False, f"Date range check failed: {str(e)}", "DATE_INVALID"
        
    return True, dt_res, None

def validate_time(time_val):
    if pd.isna(time_val) or str(time_val).strip() == '':
        return False, "Time is empty"
        
    if isinstance(time_val, datetime):
        return True, time_val.strftime('%H:%M:%S')
        
    time_str = str(time_val).strip()
    
    for fmt in ACCEPTED_TIME_FORMATS:
        try:
            t = datetime.strptime(time_str, fmt).time()
            return True, t.strftime('%H:%M:%S')
        except ValueError:
            continue
            
    match = re.match(r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])(?::([0-5][0-9]))?$', time_str)
    if match:
        h, m, s = match.groups()
        s = s if s else "00"
        return True, f"{int(h):02d}:{int(m):02d}:{int(s):02d}"
        
    return False, f"Time '{time_str}' does not match any accepted formats (e.g. HH:MM:SS)"

def process_batch(app, batch_id, filepath, row_split_threshold=50000):
    with app.app_context():
        batch = db.session.get(UploadedBatch, batch_id)
        if not batch:
            return
            
        try:
            batch.status = 'VALIDATING'
            db.session.commit()
            
            # Load country rules
            rules = CountryRule.query.all()
            rules_dict = {}
            for r in rules:
                rules_dict[r.country_name.strip().upper()] = {
                    'phone_prefix': r.phone_prefix,
                    'phone_length': r.phone_length
                }
                rules_dict[r.country_code.strip().upper()] = {
                    'phone_prefix': r.phone_prefix,
                    'phone_length': r.phone_length
                }
            
            ext = os.path.splitext(filepath)[1].lower()
            
            if ext == '.csv':
                df_headers = pd.read_csv(filepath, nrows=0)
            elif ext in ['.xlsx', '.xls']:
                df_headers = pd.read_excel(filepath, nrows=0)
            else:
                raise ValueError(f"Unsupported file format: {ext}")
                
            file_cols = list(df_headers.columns)
            
            total_rows = 0
            valid_rows_count = 0
            error_rows_count = 0
            
            # Dynamic Duplicate Tracking: dict of sets mapping column name to seen values
            seen_values = {}
            
            clean_transactions = []
            error_reports = []
                     # Get email requirement setting from config
            email_required = app.config.get('EMAIL_REQUIRED', True)
            
            chunk_size = 10000
            
            # Determine if we stream/chunk
            reader = None
            if ext == '.csv':
                reader = pd.read_csv(filepath, chunksize=chunk_size, keep_default_na=False, na_values=[''], dtype=str)
            else:
                df_excel = pd.read_excel(filepath, keep_default_na=False, na_values=[''], dtype=str)
                # Replace pandas NaN with None so JSON serialization does not crash on NaN
                df_excel = df_excel.where(pd.notnull(df_excel), None)
                reader = [df_excel]
                
            for chunk in reader:
                # Replace NaN with None in chunk if not already done
                if ext == '.csv':
                    chunk = chunk.where(pd.notnull(chunk), None)
                    
                for idx, row in chunk.iterrows():
                    # 1. BLANK/EMPTY ROW HANDLING: Skip row silently if all fields are null or empty strings
                    is_row_blank = True
                    for col in file_cols:
                        val = row[col]
                        if val is not None and not pd.isna(val) and str(val).strip() != '':
                            is_row_blank = False
                            break
                    if is_row_blank:
                        continue
                        
                    row_num = total_rows + 1
                    total_rows += 1
                    
                    row_errors = []
                    
                    # Store dynamic row data
                    row_dict = {}
                    for col in file_cols:
                        val = row[col]
                        if pd.isna(val):
                            val = None
                        elif isinstance(val, (pd.Timestamp, datetime)):
                            val = val.strftime('%Y-%m-%d')
                        row_dict[col] = val
                    
                    # Maintain separate cleaned dictionary for clean output file
                    clean_row_dict = dict(row_dict)
                    
                    # Apply Dynamic Concept Validations
                    for col in file_cols:
                        val = row_dict[col]
                        col_norm = col.strip().lower()
                        
                        # Rule A: ID Columns (Duplicate checks)
                        if 'id' in col_norm:
                            if val is not None and str(val).strip() != '':
                                val_str = str(val).strip()
                                if col not in seen_values:
                                    seen_values[col] = set()
                                if val_str in seen_values[col]:
                                    row_errors.append((col, f"Duplicate ID '{val_str}' in column '{col}'", 'DUPLICATE_ID'))
                                else:
                                    seen_values[col].add(val_str)
                            else:
                                row_errors.append((col, f"Identifier column '{col}' is empty", 'MISSING_FIELD'))
                                
                        # Rule B: Email Columns
                        elif 'email' in col_norm or 'mail' in col_norm:
                            is_em_valid, em_msg, em_err_code, cleaned_em = validate_email(val, email_required)
                            if not is_em_valid:
                                row_errors.append((col, em_msg, em_err_code))
                                if cleaned_em:
                                    clean_row_dict[col] = cleaned_em
                                
                        # Rule C: Date Columns (standardize format and range)
                        elif 'date' in col_norm:
                            if val is not None and str(val).strip() != '':
                                is_dt_valid, dt_res, err_code = validate_date(val)
                                if not is_dt_valid:
                                    row_errors.append((col, dt_res, err_code or 'INVALID_DATE'))
                                else:
                                    clean_row_dict[col] = dt_res
                            else:
                                row_errors.append((col, f"Date field '{col}' is empty", 'MISSING_FIELD'))
                                
                        # Rule D: Time Columns (standardize format)
                        elif 'time' in col_norm:
                            if val is not None and str(val).strip() != '':
                                is_tm_valid, tm_res = validate_time(val)
                                if not is_tm_valid:
                                    row_errors.append((col, f"Time '{val}' in '{col}' is invalid.", 'INVALID_TIME'))
                                else:
                                    clean_row_dict[col] = tm_res
                            else:
                                row_errors.append((col, f"Time field '{col}' is empty", 'MISSING_FIELD'))
                                
                        # Rule E: Phone/Mobile Columns
                        elif 'phone' in col_norm or 'mobile' in col_norm:
                            if val is not None and str(val).strip() != '':
                                val_str = str(val).strip()
                                # Clean phone: strip spaces, dashes, parentheses
                                chars_to_strip = " -()–—"
                                stripped_val = "".join(c for c in val_str if c not in chars_to_strip)
                                clean_row_dict[col] = stripped_val
                                
                                country_col = next((c for c in file_cols if 'country' in c.lower()), None)
                                country_val = row_dict[country_col] if country_col else None
                                is_ph_valid, ph_err = validate_phone(val_str, country_val, rules_dict)
                                if not is_ph_valid:
                                    row_errors.append((col, ph_err, 'INVALID_PHONE'))
                            else:
                                row_errors.append((col, f"Phone field '{col}' is empty", 'MISSING_FIELD'))
                                
                        # Rule F: Name Columns
                        elif 'name' in col_norm:
                            if val is not None and str(val).strip() != '':
                                name_str = str(val).strip()
                                # Collapse spaces
                                name_clean = re.sub(r'\s+', ' ', name_str)
                                clean_row_dict[col] = name_clean
                                
                                # Check characters: only letters, spaces, hyphens, and apostrophes
                                if not re.match(r'^[a-zA-Z\s\-\']+$', name_clean):
                                    row_errors.append((col, f"Name '{name_clean}' contains digits or special symbols.", 'NAME_FORMAT_SUSPICIOUS'))
                            else:
                                row_errors.append((col, f"Name field '{col}' is empty", 'MISSING_FIELD'))
                                
                        # Rule G: City Columns
                        elif 'city' in col_norm:
                            if val is not None and str(val).strip() != '':
                                city_clean = str(val).strip().title()
                                clean_row_dict[col] = city_clean
                            else:
                                row_errors.append((col, f"City field '{col}' is empty", 'MISSING_FIELD'))
                                
                        # Backward compatibility rule audits for hardcoded transaction schema
                        elif col_norm == 'quantity':
                            if val is not None and str(val).strip() != '':
                                try:
                                    q_str = str(val).strip()
                                    q_val = float(q_str) if '.' in q_str else int(q_str)
                                    if isinstance(q_val, float) and not q_val.is_integer():
                                        row_errors.append((col, "Quantity must be a whole number", 'INVALID_TYPE'))
                                    elif q_val <= 0:
                                        row_errors.append((col, "Quantity must be greater than zero", 'NEGATIVE_VALUE'))
                                except ValueError:
                                    row_errors.append((col, f"Quantity '{val}' is not a valid number", 'INVALID_TYPE'))
                            else:
                                row_errors.append((col, "Quantity is empty", 'MISSING_FIELD'))
                                
                        elif col_norm == 'unit_price':
                            if val is not None and str(val).strip() != '':
                                try:
                                    p_val = float(str(val).strip())
                                    if p_val <= 0:
                                        row_errors.append((col, "Unit Price must be greater than zero", 'NEGATIVE_VALUE'))
                                except ValueError:
                                    row_errors.append((col, f"Unit Price '{val}' is not a valid number", 'INVALID_TYPE'))
                            else:
                                row_errors.append((col, "Unit Price is empty", 'MISSING_FIELD'))
                                
                        elif col_norm == 'payment_mode':
                            if val is not None and str(val).strip() != '':
                                val_str = str(val).strip()
                                if val_str.lower() not in ALLOWED_PAYMENT_MODES:
                                    row_errors.append((col, f"Payment Mode '{val_str}' is not allowed", 'INVALID_PAYMENT'))
                            else:
                                row_errors.append((col, "Payment Mode is empty", 'MISSING_FIELD'))
                                
                    is_valid = len(row_errors) == 0
                    
                    if is_valid:
                        valid_rows_count += 1
                    else:
                        error_rows_count += 1
                        
                    # Find backup fields mapping if columns match
                    m_order_id = next((row_dict[c] for c in file_cols if 'order' in c.lower() or c.lower() == 'id' or 'customer_id' in c.lower()), None)
                    m_cust_name = next((row_dict[c] for c in file_cols if 'customer_name' in c.lower() or 'full_name' in c.lower() or 'name' in c.lower()), None)
                    m_phone = next((row_dict[c] for c in file_cols if 'phone' in c.lower() or 'mobile' in c.lower()), None)
                    m_country = next((row_dict[c] for c in file_cols if 'country' in c.lower()), None)
                    m_product = next((row_dict[c] for c in file_cols if 'product' in c.lower()), None)
                    m_qty = next((row_dict[c] for c in file_cols if 'quantity' in c.lower() or c.lower() == 'qty'), None)
                    m_price = next((row_dict[c] for c in file_cols if 'price' in c.lower() or c.lower() == 'rate'), None)
                    m_pay = next((row_dict[c] for c in file_cols if 'payment' in c.lower() or 'pay_mode' in c.lower()), None)
                    m_date = next((row_dict[c] for c in file_cols if 'date' in c.lower()), None)
                    m_time = next((row_dict[c] for c in file_cols if 'time' in c.lower()), None)
                    
                    # Replace empty fields with "null" in clean_row_dict ONLY
                    for col in file_cols:
                        if clean_row_dict[col] is None or str(clean_row_dict[col]).strip() == '':
                            clean_row_dict[col] = "null"
                            
                    tx = Transaction(
                        batch_id=batch_id,
                        row_number=row_num,
                        order_id=str(m_order_id)[:100] if m_order_id else None,
                        customer_name=str(m_cust_name)[:255] if m_cust_name else None,
                        phone_number=str(m_phone)[:100] if m_phone else None,
                        country=str(m_country)[:100] if m_country else None,
                        product_name=str(m_product)[:255] if m_product else None,
                        quantity=str(m_qty)[:50] if m_qty else None,
                        unit_price=str(m_price)[:50] if m_price else None,
                        payment_mode=str(m_pay)[:100] if m_pay else None,
                        transaction_date=str(m_date)[:100] if m_date else None,
                        transaction_time=str(m_time)[:100] if m_time else None,
                        is_valid=is_valid,
                        raw_data=json.dumps(row_dict)
                    )
                    db.session.add(tx)
                    
                    clean_transactions.append(clean_row_dict)
                    
                    if not is_valid:
                        for field, msg, code in row_errors:
                            err_model = ValidationError(
                                batch_id=batch_id,
                                row_number=row_num,
                                field_name=field,
                                error_message=msg,
                                error_code=code
                            )
                            db.session.add(err_model)
                            
                            error_reports.append({
                                'row_number': row_num,
                                'field_name': field,
                                'error_code': code,
                                'error_message': msg,
                                'order_id': str(m_order_id) if m_order_id else f"Row {row_num}"
                            })
                            
                db.session.commit()
                
            # Create Cleaned File(s)
            uploads_dir = os.path.dirname(filepath)
            clean_filename_base = f"clean_batch_{batch_id}"
            
            clean_df = pd.DataFrame(clean_transactions)
            
            if len(clean_df) > row_split_threshold:
                zip_filename = f"{clean_filename_base}.zip"
                zip_filepath = os.path.join(uploads_dir, zip_filename)
                
                with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    num_parts = (len(clean_df) // row_split_threshold) + 1
                    for part in range(num_parts):
                        start_idx = part * row_split_threshold
                        end_idx = start_idx + row_split_threshold
                        part_df = clean_df.iloc[start_idx:end_idx]
                        
                        if part_df.empty:
                            continue
                            
                        part_name = f"{clean_filename_base}_part_{part + 1}.csv"
                        part_path = os.path.join(uploads_dir, part_name)
                        part_df.to_csv(part_path, index=False)
                        
                        zip_file.write(part_path, part_name)
                        os.remove(part_path)
            else:
                csv_filename = f"{clean_filename_base}.csv"
                clean_df.to_csv(os.path.join(uploads_dir, csv_filename), index=False)
                
            # Create Error Report File
            err_df = pd.DataFrame(error_reports)
            err_filename = f"errors_batch_{batch_id}.csv"
            err_df.to_csv(os.path.join(uploads_dir, err_filename), index=False)
            
            batch.status = 'COMPLETED'
            batch.total_rows = total_rows
            batch.valid_rows = valid_rows_count
            batch.error_rows = error_rows_count
            batch.completed_at = datetime.utcnow()
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            batch.status = 'FAILED'
            err_filename = f"errors_batch_{batch_id}.csv"
            error_df = pd.DataFrame([{
                'row_number': 0,
                'field_name': 'file',
                'error_code': 'BATCH_FAILED',
                'error_message': str(e),
                'order_id': ''
            }])
            error_df.to_csv(os.path.join(os.path.dirname(filepath), err_filename), index=False)
            db.session.commit()
            print(f"Error validating batch {batch_id}: {str(e)}")
