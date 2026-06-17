-- TransactionGuard MySQL Workbench DDL Schema
-- Create Database
CREATE DATABASE IF NOT EXISTS transaction_guard;
USE transaction_guard;

-- Table to configure validation rules by country
DROP TABLE IF EXISTS country_rules;
CREATE TABLE country_rules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    country_name VARCHAR(100) NOT NULL UNIQUE,
    country_code VARCHAR(10) NOT NULL UNIQUE, -- e.g., IN, SG, US, GB
    phone_length INT NOT NULL,                -- Expected phone number length
    phone_prefix VARCHAR(10) NOT NULL,        -- Country code dial prefix, e.g. +91, +65
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Table to track file uploads and validation summary
DROP TABLE IF EXISTS uploaded_batches;
CREATE TABLE uploaded_batches (
    id INT AUTO_INCREMENT PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING', -- PENDING, PROCESSING, COMPLETED, FAILED
    total_rows INT NOT NULL DEFAULT 0,
    valid_rows INT NOT NULL DEFAULT 0,
    error_rows INT NOT NULL DEFAULT 0,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Table to store transaction records
DROP TABLE IF EXISTS transactions;
CREATE TABLE transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    batch_id INT NOT NULL,
    row_number INT NOT NULL,                     -- Row index in the uploaded spreadsheet (1-based)
    order_id VARCHAR(100),
    customer_name VARCHAR(255),
    phone_number VARCHAR(100),
    country VARCHAR(100),
    product_name VARCHAR(255),
    quantity VARCHAR(50),                        -- Kept as string to retain invalid input data
    unit_price VARCHAR(50),                      -- Kept as string to retain invalid input data
    payment_mode VARCHAR(100),
    transaction_date VARCHAR(100),
    transaction_time VARCHAR(100),
    is_valid BOOLEAN NOT NULL DEFAULT TRUE,      -- Quick filter for cleaned export
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES uploaded_batches(id) ON DELETE CASCADE,
    INDEX idx_batch_valid (batch_id, is_valid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Table to store specific validation failure reports per cell/row
DROP TABLE IF EXISTS validation_errors;
CREATE TABLE validation_errors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    batch_id INT NOT NULL,
    row_number INT NOT NULL,
    field_name VARCHAR(100) NOT NULL,            -- e.g., phone_number, unit_price, quantity
    error_message VARCHAR(255) NOT NULL,          -- Plain-language error description
    error_code VARCHAR(50) NOT NULL,             -- MISSING_FIELD, INVALID_PHONE, INVALID_DATE, NEGATIVE_VALUE, INVALID_PAYMENT, DUPLICATE_ORDER
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES uploaded_batches(id) ON DELETE CASCADE,
    INDEX idx_batch_row (batch_id, row_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Seed initial rules for testing
INSERT INTO country_rules (country_name, country_code, phone_length, phone_prefix) VALUES
('India', 'IN', 10, '+91'),
('Singapore', 'SG', 8, '+65'),
('United States', 'US', 10, '+1'),
('United Kingdom', 'GB', 10, '+44');
