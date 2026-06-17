# TransactionGuard

TransactionGuard is a bulk transaction data validation and processing platform. It ingests CSV/XLSX transaction datasets containing order, customer, product, and payment details, validates them against dynamic configurations, and generates cleaned downloads alongside audit logs.

---

## Technical Stack & Configuration

- **Backend**: Python 3.13, Flask, SQLAlchemy ORM, Pandas, and PyMySQL.
- **Frontend**: React (Vite), Vanilla CSS, and custom SVG visual charts.
- **Database**: MySQL.

---

## Local Development Setup

### 1. Database Setup
Ensure you have a local MySQL server running.
1. Open MySQL Workbench (or your preferred SQL client).
2. Import the DDL schema by opening and running the `schema.sql` file located in the root of this project.
3. This creates the database `transaction_guard` and seeds the default rules.
*(Note: The Flask backend will also attempt to auto-create tables and seed rules automatically on startup if they do not exist).*

### 2. Backend Setup
1. Open a terminal and navigate to the `/backend` folder:
   ```bash
   cd backend
   ```
2. Install the Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a configuration file named `.env` in the `/backend` folder (you can copy `.env.example` as a template):
   ```ini
   FLASK_APP=run.py
   FLASK_ENV=development
   DATABASE_URL=mysql+pymysql://<username>:<password>@localhost:3306/transaction_guard
   UPLOAD_FOLDER=uploads
   MAX_CONTENT_LENGTH=16777216  # 16MB file limit
   ROW_SPLIT_THRESHOLD=50000     # Lines limit to split cleaned output
   ```
4. Start the Flask server:
   ```bash
   python run.py
   ```
   The backend will start running on `http://127.0.0.1:5000/`.

### 3. Frontend Setup
1. Open a new terminal and navigate to the `/frontend` folder:
   ```bash
   cd frontend
   ```
2. Install the Node.js packages:
   ```bash
   npm install
   ```
3. Start the Vite React development server:
   ```bash
   npm run dev
   ```
   The frontend will start running on `http://localhost:5173/`. Open this address in your browser to interact with the platform.

---

## How the Ingestion Validation Rules Work

Each uploaded transaction row is validated using dynamic rule parameters:
1. **Header Validation**: Check that all required columns (`order_id`, `customer_name`, `phone_number`, `country`, `product_name`, `quantity`, `unit_price`, `payment_mode`, `transaction_date`, `transaction_time`) are present.
2. **Missing Fields**: Ensure no cell values are null or empty.
3. **Data Types & Signs**: Verify that `quantity` is a positive integer and `unit_price` is a positive float/decimal.
4. **Allowed Payment Modes**: Validates values against: `Credit Card`, `Debit Card`, `UPI`, `Net Banking`, `PayPal`, `Cash` (case-insensitive).
5. **Format Validation**: Dates and times are parsed against standard ISO, US, and UK formats (e.g. `YYYY-MM-DD`, `DD-MM-YYYY`, `HH:MM:SS`, `HH:MM AM/PM`).
6. **Order Duplicates**: Duplicate `order_id` occurrences in the same batch are automatically flagged.
7. **Phone Validation**: Standardizes phone values (removes formatting) and checks prefixes and lengths matching active country settings.

### How to Add a New Country Phone Validation Rule
New countries can be configured dynamically without restarting or modifying any backend Python code:

#### Option A: Via the Web UI (Easiest)
1. Navigate to the **Validation Rules** tab in the top navigation bar.
2. In the form, enter:
   - **Country Name**: e.g., `Australia`
   - **Country Code (ISO 2-letter)**: e.g., `AU`
   - **Dialing Prefix**: e.g., `+61`
   - **Local Number Digits**: e.g., `9` (the length of local numbers in Australia excluding the prefix)
3. Click **Apply Validation Rule**. It will be saved immediately to MySQL.

#### Option B: Via SQL Seed DDL
You can insert rules directly into the `country_rules` table:
```sql
INSERT INTO country_rules (country_name, country_code, phone_length, phone_prefix) 
VALUES ('Australia', 'AU', 9, '+61');
```

---

## Hosting Options for Public Demo Deployment

To deploy this application publicly (for submission reviews), we recommend the following three options:

### Option 1: Railway (Recommended - Easiest & Single Repo Setup)
Railway provides instant deployment for web applications and databases with a single git push.
1. **Create Database**: On Railway, click "New Project" and choose "Provision MySQL".
2. **Deploy Backend**: Click "New Service" -> "Github Repo" -> Select this repository. Set the root directory to `backend`.
3. **Set Variables**: In the backend service settings, add environment variables:
   - `DATABASE_URL`: `${{MySQL.MYSQL_URL}}` (Railway automatically injects the connection string).
   - `ROW_SPLIT_THRESHOLD`: `50000`
4. **Deploy Frontend**: Click "New Service" -> "Github Repo" -> Select this repository. Set root directory to `frontend`. Add env variable `VITE_BACKEND_URL` pointing to your Railway backend URL.
5. **Public Access**: Expose both services. Railway will generate public URLs.

### Option 2: Render + Aiven MySQL (Free / Low Cost)
Render is an excellent option for free hosting of static frontends and Python web apps.
1. **MySQL Database**: Sign up for a free MySQL database on [Aiven.io](https://aiven.io/). Copy the connection string.
2. **Backend**: On Render, create a new "Web Service", connect this repository, and set the build command to `pip install -r requirements.txt` and start command to `gunicorn run:app`. Add the environment variable `DATABASE_URL` with your Aiven connection string.
3. **Frontend**: Create a new "Static Site" on Render, connect this repository, set root directory to `frontend`, build command to `npm run build`, and publish directory to `dist`.

### Option 3: PythonAnywhere (Free Tier Dedicated Python Host)
PythonAnywhere specializes in hosting Flask/Django projects and provides a built-in free MySQL database.
1. Sign up on [PythonAnywhere](https://www.pythonanywhere.com/).
2. In the "Databases" tab, enable a free MySQL database, set a password, and create a database called `yourusername$transaction_guard`.
3. In the "Console" tab, open a Bash terminal, clone your GitHub repository, and install packages using `pip install -r requirements.txt`.
4. In the "Web" tab, configure a new Flask app pointing to `run.py`, and update your WSGI file. Set your connection string in the environment variables configuration.
