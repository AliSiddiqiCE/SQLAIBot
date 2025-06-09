import sqlite3

# Create a new SQLite database
db_path = "example.db"

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create tables
# Example tables: customers, orders, and products
cursor.execute('''
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        address TEXT
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        stock_quantity INTEGER NOT NULL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        order_date DATE,
        total_amount REAL,
        status TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        product_id INTEGER,
        quantity INTEGER NOT NULL,
        price_at_purchase REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    )
''')

# Insert sample data
# Customers
customers_data = [
    ('John Doe', 'john@example.com', '555-0123', '123 Main St'),
    ('Jane Smith', 'jane@example.com', '555-0124', '456 Oak Ave'),
    ('Bob Johnson', 'bob@example.com', '555-0125', '789 Pine St')
]

cursor.executemany('''
    INSERT INTO customers (name, email, phone, address)
    VALUES (?, ?, ?, ?)
''', customers_data)

# Products
products_data = [
    ('Laptop', 'High-performance laptop', 999.99, 10),
    ('Smartphone', 'Latest model smartphone', 699.99, 15),
    ('Tablet', 'Portable tablet device', 499.99, 20),
    ('Headphones', 'Wireless headphones', 199.99, 30)
]

cursor.executemany('''
    INSERT INTO products (name, description, price, stock_quantity)
    VALUES (?, ?, ?, ?)
''', products_data)

# Commit changes and close connection
conn.commit()
conn.close()

print(f"Database created at {db_path}")
