
#Def Now
def now():
    """
    Returns the actual date and hour in string format.
    """
    from datetime import datetime

    return datetime.now().strftime("%Y%m%d")

def db_initialization(path: str):
    """Initializes DB connection, cursor, and sets up the corresponding tables."""
    import sqlite3

    conn = sqlite3.connect(path, check_same_thread=False, timeout=30)
    cur = conn.cursor()
        
    db ={
        "conn": conn,
        "cur": cur,
    }
    
    # Create tables if not exist
    db["cur"].executescript('''
                            
        CREATE TABLE IF NOT EXISTS Urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            date TEXT,
            filename TEXT UNIQUE
        );
                        
        CREATE TABLE IF NOT EXISTS Products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url_id INTEGER,
        name TEXT,
        currency TEXT,                     
        price REAL,
        UNIQUE(url_id, name) 
        );    
                                            
    ''')

    db["conn"].commit()

    return db

def insert_url(url, db):
    """Inserts a URL if it doesn't exist."""
    db["cur"].execute('SELECT date FROM Urls WHERE name=?', (url,))
    row = db["cur"].fetchone()
    if row is None:
        db["cur"].execute('INSERT OR IGNORE INTO Urls (name) VALUES (?)', (url,))
    db["conn"].commit()

def update_url_date(url, db, date):
    """Inserts the date when a specific URL was crawled."""
    db["cur"].execute('SELECT date FROM Urls WHERE name=?', (url,))
    row = db["cur"].fetchone()
    if row[0] is None:
        db["cur"].execute('UPDATE Urls SET date = ? WHERE name = ?', (date, url))
    db["conn"].commit()

def update_filename_for_url(url, db, filename):
    """Insert filename for crawled URL."""
    db["cur"].execute('SELECT filename FROM Urls WHERE name=?', (url,))
    row = db["cur"].fetchone()
    if row[0] is None:
        db["cur"].execute('UPDATE Urls SET filename = ? WHERE name = ?', (filename, url))
    db["conn"].commit()

def insert_url_and_get_id(url, db):
    """Insert a URL if it doesn't exist, and return its ID whether it's new or already in the database."""
    db["cur"].execute('SELECT date, id FROM Urls WHERE name=?', (url,))
    row = db["cur"].fetchone()
    if row is None:
        db["cur"].execute('INSERT OR IGNORE INTO Urls (name) VALUES (?)', (url,))
        db["cur"].execute('SELECT id FROM Urls WHERE name=?', (url,))
        new_row = db["cur"].fetchone()
        id_of_url = new_row[0] if new_row else None
    else:
        id_of_url = row[1]  # id of existing URL

    return id_of_url

def get_url_and_id_using_filename(db, filename):
    """
    Retrieves BOTH the database ID for a given URL and the URL if it exists using the filename inserted in the DB.
    """
    db["cur"].execute('SELECT id, name FROM Urls WHERE filename=?', (filename,))
    row = db["cur"].fetchone()
    if row is None:
        return None, None
    url_id = row[0]
    url = row[1]
    return url_id, url

def get_url_id(db, url):
    """
    Retrieves the database ID for a given URL if it exists.
    """
    db["cur"].execute('SELECT id FROM Urls WHERE name=?', (url,))
    row = db["cur"].fetchone()
    if row is None:
        return None
    if row[0] is not None:
        url_id = row[1]
        return url_id

def insert_product(db, individual_product, url_id):
    """Stores product information related to a URL in the database.
    """
    try:
        db["cur"].execute('''
        INSERT OR IGNORE INTO Products (url_id, name, currency, price)
        VALUES (?, ?, ?, ?)
        ''', (url_id, individual_product["name"], individual_product["currency"], individual_product["price"])
        )
        db["conn"].commit()
        #print(f"Inserted product for {url_id}")
    except Exception as e:
        print(f"Unknown DB error for {url_id}: {e}")