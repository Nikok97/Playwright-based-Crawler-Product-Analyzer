import sqlite3

def db_initialization(path: str) -> dict:

    """Initializes DB connection, cursor, and sets up the corresponding tables."""

    conn = sqlite3.connect(path, check_same_thread=False, timeout=30)
    cur = conn.cursor()
        
    db = {
        "conn": conn,
        "cur": cur,
    }
    
    # Create tables if not exist
    db["cur"].executescript('''
                            
        CREATE TABLE IF NOT EXISTS Urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url_name TEXT UNIQUE,
            date TEXT,
            filename TEXT UNIQUE,
            status TEXT
        );
                            
        CREATE TABLE IF NOT EXISTS ProductPages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_url TEXT UNIQUE,
            product_code TEXT,
            product_name TEXT,
            price REAL,
            currency TEXT,
            description TEXT,
            fetch_status TEXT,
            parse_status TEXT,
            condition TEXT,
            seller TEXT,
            reviews INTEGER,
            images TEXT,
            fetched_at TEXT,
            filename TEXT
        );
                                            
    ''')

    db["conn"].commit()

    return db

def insert_url(url: str, db: dict, date: str):
    """Inserts a URL if it doesn't exist."""
    db["cur"].execute('SELECT id FROM Urls WHERE url_name=?', (url,))
    row = db["cur"].fetchone()
    if row is None:
        db["cur"].execute('INSERT OR IGNORE INTO Urls (url_name, date) VALUES (?, ? )', (url, date))
    db["conn"].commit()

def already_pending_or_fetched_url(url: str, db: dict) -> bool:
    """Checks if the URL is already pending or fetched."""
    db["cur"].execute('SELECT status FROM Urls WHERE url_name=?', (url,))
    row = db["cur"].fetchone()
    if row is None:
        # URL doesn't exist in the DB
        return False
    # If the status is 'pending' or status is 'pending', return True; else return False
    if row[0] == 'pending':
        return True
    elif row[0] == 'fetched':
        return True
    else:
        return False