import sqlite3

DB_NAME = "leave_system.db"

#Create a database connection to the sqlite database specified by database name
def get_db_connection():
    
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  
    return conn

# create employees and leaves tables
def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS employees (
        employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        position TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        department TEXT NOT NULL
    )''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS leaves (
        leave_id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        leave_type TEXT NOT NULL,
        total_days INTEGER,
        used_days INTEGER,
        remaining_days INTEGER,
        FOREIGN KEY (employee_id) REFERENCES employees (employee_id)
    )''')
    
    conn.commit()
    conn.close()

def insert_sample_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if sample data already exists
    cursor.execute("SELECT COUNT(*) FROM employees")
    if cursor.fetchone()[0] > 0:
        print("Sample data already exists. Skipping insert.")
        conn.close()
        return
    
    # Add employees
    employees = [
        ('KyiKyi', 'Executive' , 'KyiKyi@mabbank.com', 'IT'),
        ('KyawKyaw', 'Employee', 'Kyaw123@mabbank.com', 'Finance')
    ]
    
    cursor.executemany('''
    INSERT INTO employees (name, position, email, department) VALUES (?, ?, ?, ?)''', employees)
    
    cursor.execute("SELECT employee_id FROM employees WHERE name = 'KyiKyi'")
    kyi_kyi_id = cursor.fetchone()[0]
    cursor.execute("SELECT employee_id FROM employees WHERE name = 'KyawKyaw'")
    kyaw_kyaw_id = cursor.fetchone()[0]
    
    
    # Leave type: total_days mapping
    leave_quotas = {
        'CL': 12,              # Casual Leave
        'EL': 18,              # Earned Leave
        'SL': 10,              # Sick Leave
        'ML': 90,              # Maternity Leave
        'COMP-OFF': 5,         # Compensatory Off
        'MARRIAGE': 5,         
        'PATERNITY': 7,        
        'BEREAVEMENT': 3,
        'LOP': 0,              # Leave Without Pay
    }
    
    for leave_type, total_days in leave_quotas.items():
        #KyiKyi's leave data
        used_kyi_kyi_days = 2 if total_days > 0 else 0
        remaining_kyi_kyi_days = total_days - used_kyi_kyi_days
        cursor.execute('''
        INSERT INTO leaves (employee_id, leave_type, total_days, used_days, remaining_days) VALUES (?, ?, ?, ?, ?)''', 
                    (kyi_kyi_id, leave_type, total_days, used_kyi_kyi_days, remaining_kyi_kyi_days))
        #KyawKyaw's leave data
        used_kyaw_kyaw_days = 3 if total_days > 0 else 0
        remaining_kyaw_kyaw_days = total_days - used_kyaw_kyaw_days
        cursor.execute('''
        INSERT INTO leaves (employee_id, leave_type, total_days, used_days, remaining_days) VALUES (?, ?, ?, ?, ?)''', 
                    (kyaw_kyaw_id, leave_type, total_days, used_kyaw_kyaw_days, remaining_kyaw_kyaw_days))
    conn.commit()
    conn.close()
    
def get_leave_balance(employee_name, leave_type):
    
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get employee ID
    cursor.execute("SELECT employee_id FROM employees WHERE LOWER(name) = ?", (employee_name.lower(),))
    result = cursor.fetchone()
    if not result:
        conn.close()
        return None

    employee_id = result[0]

    # Get leave data
    cursor.execute("""
        SELECT used_days, remaining_days
        FROM leaves
        WHERE employee_id = ? AND leave_type = ?
    """, (employee_id, leave_type))

    leave_data = cursor.fetchone()
    conn.close()

    if leave_data:
        return {
            'employee_name': employee_name,
            'leave_type': leave_type,
            'used_days': leave_data[0],
            'remaining_days': leave_data[1]
        }
    else:
        return None
    
def get_all_leaves(employee_name):
    
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get employee ID
    cursor.execute("SELECT employee_id FROM employees WHERE LOWER(name) = ?", (employee_name.lower(),))
    result = cursor.fetchone()
    if not result:
        conn.close()
        return None

    employee_id = result[0]

    # Fetch all leave types and balances
    cursor.execute("""
        SELECT leave_type, used_days, remaining_days
        FROM leaves
        WHERE employee_id = ?
    """, (employee_id,))

    leave_records = cursor.fetchall()
    conn.close()

    return [
        {
            'leave_type': row[0],
            'used_days': row[1],
            'remaining_days': row[2]
        } for row in leave_records
    ]

