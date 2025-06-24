-- AgentDK Test Database Initialization
-- Creates sample tables for testing EDA agent with MySQL MCP server

USE agentdk_test;

-- Create customers table
CREATE TABLE customers (
    customer_id INT PRIMARY KEY AUTO_INCREMENT,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    date_of_birth DATE,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    customer_status ENUM('active', 'inactive', 'suspended') DEFAULT 'active',
    credit_score INT,
    annual_income DECIMAL(12, 2)
);

-- Create accounts table
CREATE TABLE accounts (
    account_id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,
    account_number VARCHAR(20) UNIQUE NOT NULL,
    account_type ENUM('checking', 'savings', 'credit', 'investment') NOT NULL,
    balance DECIMAL(15, 2) DEFAULT 0.00,
    currency VARCHAR(3) DEFAULT 'USD',
    opened_date DATE NOT NULL,
    status ENUM('active', 'closed', 'frozen') DEFAULT 'active',
    interest_rate DECIMAL(5, 4) DEFAULT 0.0000,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

-- Create transactions table
CREATE TABLE transactions (
    transaction_id INT PRIMARY KEY AUTO_INCREMENT,
    account_id INT NOT NULL,
    transaction_type ENUM('deposit', 'withdrawal', 'transfer', 'payment', 'fee') NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description VARCHAR(255),
    reference_number VARCHAR(50),
    status ENUM('pending', 'completed', 'failed', 'cancelled') DEFAULT 'completed',
    merchant_name VARCHAR(100),
    category VARCHAR(50),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE
);

-- Insert sample customers
INSERT INTO customers (first_name, last_name, email, phone, date_of_birth, customer_status, credit_score, annual_income) VALUES
('John', 'Smith', 'john.smith@email.com', '+1-555-0101', '1985-03-15', 'active', 720, 75000.00),
('Sarah', 'Johnson', 'sarah.johnson@email.com', '+1-555-0102', '1990-07-22', 'active', 680, 52000.00),
('Michael', 'Brown', 'michael.brown@email.com', '+1-555-0103', '1982-11-08', 'active', 750, 95000.00),
('Emily', 'Davis', 'emily.davis@email.com', '+1-555-0104', '1988-12-01', 'active', 695, 68000.00),
('David', 'Wilson', 'david.wilson@email.com', '+1-555-0105', '1975-05-18', 'inactive', 650, 45000.00),
('Lisa', 'Anderson', 'lisa.anderson@email.com', '+1-555-0106', '1993-09-30', 'active', 710, 58000.00),
('Robert', 'Taylor', 'robert.taylor@email.com', '+1-555-0107', '1980-01-12', 'active', 780, 125000.00),
('Jennifer', 'Martinez', 'jennifer.martinez@email.com', '+1-555-0108', '1987-04-25', 'active', 665, 49000.00),
('Christopher', 'Garcia', 'christopher.garcia@email.com', '+1-555-0109', '1991-08-17', 'suspended', 590, 35000.00),
('Amanda', 'Rodriguez', 'amanda.rodriguez@email.com', '+1-555-0110', '1986-02-03', 'active', 725, 82000.00);

-- Insert sample accounts
INSERT INTO accounts (customer_id, account_number, account_type, balance, opened_date, status, interest_rate) VALUES
(1, 'CHK-1001', 'checking', 2500.75, '2023-01-15', 'active', 0.0100),
(1, 'SAV-1001', 'savings', 15000.00, '2023-01-15', 'active', 0.0250),
(2, 'CHK-1002', 'checking', 1875.50, '2023-02-20', 'active', 0.0100),
(2, 'SAV-1002', 'savings', 8500.25, '2023-02-20', 'active', 0.0250),
(3, 'CHK-1003', 'checking', 4200.00, '2022-11-10', 'active', 0.0100),
(3, 'INV-1003', 'investment', 45000.75, '2022-11-10', 'active', 0.0000),
(4, 'CHK-1004', 'checking', 3100.80, '2023-03-05', 'active', 0.0100),
(4, 'SAV-1004', 'savings', 12000.00, '2023-03-05', 'active', 0.0250),
(5, 'CHK-1005', 'checking', 150.25, '2022-08-12', 'frozen', 0.0100),
(6, 'CHK-1006', 'checking', 2750.00, '2023-04-18', 'active', 0.0100),
(6, 'SAV-1006', 'savings', 6800.50, '2023-04-18', 'active', 0.0250),
(7, 'CHK-1007', 'checking', 8500.25, '2022-06-30', 'active', 0.0100),
(7, 'SAV-1007', 'savings', 25000.00, '2022-06-30', 'active', 0.0250),
(7, 'INV-1007', 'investment', 125000.00, '2022-06-30', 'active', 0.0000),
(8, 'CHK-1008', 'checking', 980.75, '2023-05-22', 'active', 0.0100),
(9, 'CHK-1009', 'checking', 425.00, '2023-01-08', 'frozen', 0.0100),
(10, 'CHK-1010', 'checking', 3600.25, '2022-12-15', 'active', 0.0100),
(10, 'SAV-1010', 'savings', 18500.75, '2022-12-15', 'active', 0.0250);

-- Insert sample transactions (recent activity)
INSERT INTO transactions (account_id, transaction_type, amount, transaction_date, description, reference_number, status, merchant_name, category) VALUES
-- Account 1 (John Smith - Checking)
(1, 'deposit', 1200.00, '2024-01-15 09:30:00', 'Payroll deposit', 'PAY-20240115-001', 'completed', NULL, 'salary'),
(1, 'withdrawal', 80.00, '2024-01-16 14:25:00', 'ATM withdrawal', 'ATM-20240116-001', 'completed', NULL, 'cash'),
(1, 'payment', 125.50, '2024-01-17 16:45:00', 'Online purchase', 'ONL-20240117-001', 'completed', 'Amazon', 'shopping'),
(1, 'payment', 45.75, '2024-01-18 12:30:00', 'Coffee shop', 'POS-20240118-001', 'completed', 'Starbucks', 'dining'),

-- Account 2 (John Smith - Savings)
(2, 'transfer', 500.00, '2024-01-16 10:00:00', 'Transfer from checking', 'TRF-20240116-001', 'completed', NULL, 'transfer'),

-- Account 3 (Sarah Johnson - Checking)
(3, 'deposit', 2100.00, '2024-01-14 08:15:00', 'Payroll deposit', 'PAY-20240114-002', 'completed', NULL, 'salary'),
(3, 'payment', 850.00, '2024-01-15 09:00:00', 'Rent payment', 'ACH-20240115-001', 'completed', 'Property Management', 'housing'),
(3, 'payment', 65.25, '2024-01-16 19:20:00', 'Grocery shopping', 'POS-20240116-002', 'completed', 'Whole Foods', 'groceries'),

-- Account 5 (Michael Brown - Checking)
(5, 'deposit', 3200.00, '2024-01-13 07:45:00', 'Payroll deposit', 'PAY-20240113-003', 'completed', NULL, 'salary'),
(5, 'payment', 1200.00, '2024-01-14 11:30:00', 'Mortgage payment', 'ACH-20240114-002', 'completed', 'First National Bank', 'housing'),
(5, 'payment', 250.00, '2024-01-15 15:45:00', 'Utility bill', 'ACH-20240115-003', 'completed', 'Electric Company', 'utilities'),

-- Account 7 (Emily Davis - Checking)
(7, 'deposit', 2600.00, '2024-01-12 08:30:00', 'Payroll deposit', 'PAY-20240112-004', 'completed', NULL, 'salary'),
(7, 'payment', 89.50, '2024-01-13 13:15:00', 'Gas station', 'POS-20240113-003', 'completed', 'Shell', 'transportation'),
(7, 'withdrawal', 100.00, '2024-01-14 16:00:00', 'ATM withdrawal', 'ATM-20240114-002', 'completed', NULL, 'cash'),

-- Account 10 (Lisa Anderson - Checking)
(10, 'deposit', 2400.00, '2024-01-11 09:00:00', 'Payroll deposit', 'PAY-20240111-005', 'completed', NULL, 'salary'),
(10, 'payment', 750.00, '2024-01-12 10:30:00', 'Rent payment', 'ACH-20240112-004', 'completed', 'Downtown Apartments', 'housing'),

-- Account 12 (Robert Taylor - Checking)
(12, 'deposit', 4500.00, '2024-01-10 07:30:00', 'Payroll deposit', 'PAY-20240110-006', 'completed', NULL, 'salary'),
(12, 'payment', 2500.00, '2024-01-11 14:20:00', 'Investment transfer', 'TRF-20240111-002', 'completed', NULL, 'investment'),
(12, 'payment', 150.75, '2024-01-12 18:45:00', 'Restaurant', 'POS-20240112-004', 'completed', 'Fine Dining Co', 'dining'),

-- Account 15 (Jennifer Martinez - Checking)
(15, 'deposit', 1950.00, '2024-01-09 08:45:00', 'Payroll deposit', 'PAY-20240109-007', 'completed', NULL, 'salary'),
(15, 'payment', 325.00, '2024-01-10 12:00:00', 'Car payment', 'ACH-20240110-005', 'completed', 'Auto Finance Corp', 'transportation'),

-- Account 17 (Amanda Rodriguez - Checking)
(17, 'deposit', 3100.00, '2024-01-08 09:15:00', 'Payroll deposit', 'PAY-20240108-008', 'completed', NULL, 'salary'),
(17, 'payment', 950.00, '2024-01-09 11:45:00', 'Rent payment', 'ACH-20240109-006', 'completed', 'City View Apartments', 'housing'),
(17, 'payment', 85.50, '2024-01-10 17:30:00', 'Pharmacy', 'POS-20240110-005', 'completed', 'CVS Pharmacy', 'healthcare');

-- Create indexes for better query performance
CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_status ON customers(customer_status);
CREATE INDEX idx_accounts_customer ON accounts(customer_id);
CREATE INDEX idx_accounts_type ON accounts(account_type);
CREATE INDEX idx_accounts_status ON accounts(status);
CREATE INDEX idx_transactions_account ON transactions(account_id);
CREATE INDEX idx_transactions_date ON transactions(transaction_date);
CREATE INDEX idx_transactions_type ON transactions(transaction_type);
CREATE INDEX idx_transactions_status ON transactions(status);

-- Create a view for customer account summary
CREATE VIEW customer_account_summary AS
SELECT 
    c.customer_id,
    c.first_name,
    c.last_name,
    c.email,
    c.customer_status,
    COUNT(a.account_id) as total_accounts,
    SUM(a.balance) as total_balance,
    AVG(a.balance) as average_balance
FROM customers c
LEFT JOIN accounts a ON c.customer_id = a.customer_id
WHERE a.status = 'active'
GROUP BY c.customer_id, c.first_name, c.last_name, c.email, c.customer_status;

-- Create a view for transaction summary by month
CREATE VIEW monthly_transaction_summary AS
SELECT 
    DATE_FORMAT(t.transaction_date, '%Y-%m') as month,
    t.transaction_type,
    COUNT(*) as transaction_count,
    SUM(t.amount) as total_amount,
    AVG(t.amount) as average_amount
FROM transactions t
WHERE t.status = 'completed'
GROUP BY DATE_FORMAT(t.transaction_date, '%Y-%m'), t.transaction_type
ORDER BY month DESC, t.transaction_type;

-- Display some sample data for verification
SELECT 'Database initialized successfully!' as status;
SELECT COUNT(*) as customer_count FROM customers;
SELECT COUNT(*) as account_count FROM accounts;
SELECT COUNT(*) as transaction_count FROM transactions; 