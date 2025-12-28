
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
            filename TEXT UNIQUE,
            status TEXT
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

def insert_url(url: str, db):
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

def get_url_id(url, db):
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
    
def get_and_update_pending_url(db):
    """
    Retrieves URLs and their IDs stored in the DB marked as pending, and stamps them as in progress.
    """
    db["cur"].execute('SELECT id, name FROM Urls WHERE status=? ORDER BY id LIMIT 1', ("pending",))
    row = db["cur"].fetchone()
    if row is None:
        return None, None
    url_id = row[0]
    url = row[1]
    db["cur"].execute('UPDATE Urls SET status=? WHERE id=?', ('in_progress', url_id))
    db["conn"].commit()
    return url_id, url

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

def already_fetched_checker(url, db):
    """Checks if the URL is already fetched."""
    db["cur"].execute('SELECT status FROM Urls WHERE name=?', (url,))
    row = db["cur"].fetchone()
    if row is None:
        # URL doesn't exist in the DB
        return False
    # If the status is 'fetched', return True; else return False
    if row[0] == 'fetched':
        return True
    else:
        return False

def update_url_status(url, db: dict, status: str):
    """Sets the crawling status of a URL: pending / fetched / failed."""
    db["cur"].execute(
        'UPDATE Urls SET status = ? WHERE name = ?',
        (status, url)
    )
    db["conn"].commit()

def mark_url_as_failed(db, url):
    """
    Mark URL as failed.
    """
    status = 'failed'
    db["cur"].execute(
        'UPDATE Urls SET status = ? WHERE name = ?',
        (status, url)
    )
    db["conn"].commit()

