import sqlite3
import threading

from contextlib import contextmanager
from pathlib import Path

class Database:
    """Coherent SQLite persistence boundary for the crawler pipeline."""

    def __init__(self, path: str | Path): # constructor de la clase. pide los parámetros path para iniciar una base de datos ahi. De hecho es el unico parametro que pide al iniciar.

        self.path = path
        self._conn = sqlite3.connect(path, check_same_thread=False, timeout=30) # conn es inicializado al iniciar la clase, como un conector sqlite en el path que se pasó por parámetro
        self._cur = self._conn.cursor() #cur es inicializado al inciiar la clase, conectándose a la conn. Ambos tienen la convención de python de _, que significa "campos internos a la clase"
        self._closed = False # boolean flag que indica si la db está cerrada o no
        self._in_transaction = False # es un booleano que indica si ya hay una transacción activa
        self._has_uncommitted_product_update = False # boolean flag que todavia no se pa que sirve
        self._lock = threading.RLock()
        self._initialize_schema() # al iniciar el objeto Database esto iniciializa una db con el esquema indicado.

    def _initialize_schema(self) -> None:

        with self._lock: # lock que todavia no se pa que sirve

            self._cur.executescript('''

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
            self._conn.commit() # esto inicializa el esquema y lo commitea

    @property
    def is_closed(self) -> bool:
        return self._closed # está hecho property así después puedo hacer if db.is_closed, llamándolo como un atributo y no como una funcion (xq tiene que ver con devolver/leer un estado, y no con una acción que cambia estado o calcula algo)

    def close(self) -> None:
        """
        Método que cierra el cursor y la conn. Primero cierra el cur, luego siempre cierra la conn con finally.
        """
        with self._lock:
            if self._closed:
                return

            try:
                self._cur.close()
            except sqlite3.ProgrammingError:
                pass
            finally:
                try:
                    self._conn.close()
                finally:
                    self._closed = True

    def __enter__(self) -> "Database":
        return self # método para usar con el context manager, que dice que cuando se entre al with, se usa esta misma instancia como valor asociado a "as db"

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close() # Al salir del with, cerrá siempre la base, pero no ocultes ningún error que haya ocurrido. Por eso en los params está el param para el tipo de excepcion prodcida, su valor, y el traceback.

    def _discard_uncommitted_product_update(self) -> None:
        if not self._in_transaction and self._has_uncommitted_product_update:
            self._conn.rollback()
            self._has_uncommitted_product_update = False

    @contextmanager # esto se trata de una operacion y no un objeto, y por eso no creamos una clase para esto y usamos los dunder methods __enter__ y __exit__ sino que usamos el decorator @context manager
    def transaction(self):
        """
        → Método que busca hacer atómica toda una serie de operaciones con la db. O todas tienen éxito o ninguna lo tiene.
        → Transaction() no se ejecuta para cada operación de DB. Se usa solo cuando varias operaciones deben comportarse como una unidad atómica.
        """
        # comportamiento de __enter__
        with self._lock:
            outermost = not self._in_transaction # outermost significa “la transacción más externa”
            if outermost:
                self._discard_uncommitted_product_update()
                self._in_transaction = True
            try:
                yield self # cede el objeto DB para que las operaciones individuales stackeadas en el context manager realicen sus acciones
            # comportamiento de __exit__
            except Exception:
                if outermost: 
                    #sólo hacer rollback si la llamada a transaction está sola, o es la más externa de unas llamadas en varios context manager stackeados
                    self._in_transaction = False
                    self._has_uncommitted_product_update = False
                    self._conn.rollback()
                raise
            else:
                if outermost:
                    #sólo hacer commit si la llamada a transaction está sola, o es la más externa de unas llamadas en varios context manager stackeados
                    self._in_transaction = False
                    self._has_uncommitted_product_update = False
                    self._conn.commit()

    def commit(self) -> None:
        with self._lock:
            self._has_uncommitted_product_update = False
            self._conn.commit()

    def rollback(self) -> None:
        with self._lock:
            self._in_transaction = False
            self._has_uncommitted_product_update = False
            self._conn.rollback()

    def get_pending_url_and_update(self, status: str = "in_progress") -> tuple[int, str] | tuple[None, None]:
        """
        Retrieves a pending URL and atomically claims it with the given status. Solves the secure claiming of jobs by two or more workers.
        """
        with self._lock:
            self._discard_uncommitted_product_update()
            attempted_ids: set[int] = set()

            while True:
                self._cur.execute(
                    'SELECT id, url_name FROM Urls WHERE status=? ORDER BY id LIMIT 1',
                    ("pending",),
                ) # seleccionar urls por id y nombre de la tabla Urls pero sii el status es "pending"
                row = self._cur.fetchone() # intentar reclamarla
                if row is None:
                    return None, None # si no hay row, devolver None, None
                url_id = row[0]
                url = row[1]
                if url_id in attempted_ids:
                    return None, None # si la url ya se intentó, devolver none, none y salir del loop
                attempted_ids.add(url_id) # si no se intentó, añadirla al set
                self._cur.execute(
                    'UPDATE Urls SET status=? WHERE id=? AND status=?',
                    (status, url_id, "pending"),
                ) # actualizar el status de la url con el id extraído antes, pero sii el status de la misma es 'pending'
                self._conn.commit()
                if self._cur.rowcount == 1: # esto chequea si el trabajador seleccionó con éxito, i. e. reclamó para sí, una url marcada como pendiente y la actualizó a in_progress (o lo que fuera se está pasando por el parámetro status de la función). Si la reclamó, entonces devolverla para que el resto del código prosiga con sus tareas.
                    return url_id, url

    claim_pending_url = get_pending_url_and_update

    def update_filename_for_url(self, url: str, filename: str) -> None:
        """Inserts filename for crawled URL if not already set."""
        with self._lock:
            self._discard_uncommitted_product_update()
            try:
                self._cur.execute('SELECT filename FROM Urls WHERE url_name=?', (url,))
                row = self._cur.fetchone()
                if row[0] is None:
                    self._cur.execute(
                        'UPDATE Urls SET filename = ? WHERE url_name = ?',
                        (filename, url),
                    )
                if not self._in_transaction:
                    self._conn.commit()
            except Exception:
                if not self._in_transaction:
                    self._conn.rollback()
                raise

    # ------------------------------------------------------------------
    # Search URL operations (Urls table)
    # ------------------------------------------------------------------

    def insert_url(self, url: str, date: str) -> None:
        """Inserts a URL if it doesn't exist."""
        with self._lock:
            self._discard_uncommitted_product_update()
            try:
                self._cur.execute('SELECT id FROM Urls WHERE url_name=?', (url,))
                row = self._cur.fetchone()
                if row is None:
                    self._cur.execute(
                        'INSERT OR IGNORE INTO Urls (url_name, date) VALUES (?, ? )',
                        (url, date),
                    )
                if not self._in_transaction:
                    self._conn.commit()
            except Exception:
                if not self._in_transaction:
                    self._conn.rollback()
                raise

    def already_pending_or_fetched_url(self, url: str) -> bool:
        """Checks if the URL is already pending or fetched."""
        with self._lock:
            self._cur.execute('SELECT status FROM Urls WHERE url_name=?', (url,))
            row = self._cur.fetchone()

            if row is None:
                return False

            if row[0] == 'pending':
                return True
            elif row[0] == 'fetched':
                return True
            else:
                return False

    def update_url_status(self, url: str, status: str) -> None:
        """Sets the crawling status of an URL: pending / fetched / failed."""
        with self._lock:
            self._discard_uncommitted_product_update()
            try:
                self._cur.execute(
                    'UPDATE Urls SET status = ? WHERE url_name = ?',
                    (status, url),
                )
                if not self._in_transaction:
                    self._conn.commit()
            except Exception:
                if not self._in_transaction:
                    self._conn.rollback()
                raise

    claim_pending_url = get_pending_url_and_update

    # ------------------------------------------------------------------
    # Product operations (ProductPages table)
    # ------------------------------------------------------------------

    def insert_product_url(self, individual_product: dict) -> None:
        """Stores product information related to a product URL in the database."""
        with self._lock:
            self._discard_uncommitted_product_update()
            try:
                self._cur.execute(
                    '''
                    INSERT OR IGNORE INTO ProductPages (product_url, fetch_status)
                    VALUES ( ?, ?)
                    ''',
                    (individual_product["link"], "pending"),
                )
                if not self._in_transaction:
                    self._conn.commit()
            except Exception:
                if not self._in_transaction:
                    self._conn.rollback()
                raise

    def get_pending_product_url(self) -> tuple[int, str] | tuple[None, None]:
        """Gets 1 pending product webpage and atomically claims it as fetching."""
        with self._lock:
            self._discard_uncommitted_product_update()
            attempted_ids: set[int] = set()
            while True:
                self._cur.execute(
                    '''
                    SELECT id, product_url
                    FROM ProductPages
                    WHERE fetch_status = ?
                    ORDER BY id
                    LIMIT 1
                    ''',
                    ('pending',),
                )
                row = self._cur.fetchone()

                if row is None:
                    return None, None

                row_id, product_url = row
                if row_id in attempted_ids:
                    return None, None
                attempted_ids.add(row_id)

                self._cur.execute(
                    'UPDATE ProductPages SET fetch_status = ? WHERE id = ? AND fetch_status = ?',
                    ('fetching', row_id, 'pending'),
                )
                self._conn.commit()

                if self._cur.rowcount == 1:
                    return row_id, product_url

    claim_pending_product_url = get_pending_product_url

    def update_fetch_status_in_product_pages(
        self, row_id: int, filename: str | None, status: str
    ) -> None:
        """Updates fetch_status and filename for a product row."""
        with self._lock:
            self._discard_uncommitted_product_update()
            try:
                self._cur.execute(
                    "UPDATE ProductPages SET fetch_status = ?, filename = ? WHERE id = ?",
                    (status, filename, row_id),
                )
                if not self._in_transaction:
                    self._conn.commit()
            except Exception:
                if not self._in_transaction:
                    self._conn.rollback()
                raise

    update_product_fetch_status = update_fetch_status_in_product_pages

    def reset_stuck_jobs_in_urls_table(self) -> None:
        """Resets stuck Urls in_progress jobs back to pending."""
        with self._lock:
            self._discard_uncommitted_product_update()
            self._cur.execute(
            '''
            UPDATE Urls
            SET status = 'pending'
            WHERE status = 'in_progress'
            '''
            )
            if not self._in_transaction:
                self._conn.commit()


    def reset_stuck_jobs(self) -> None:
        """Resets stuck product fetching jobs back to pending."""
        with self._lock:
            self._discard_uncommitted_product_update()
            self._cur.execute(
                '''
                UPDATE ProductPages
                SET fetch_status = 'pending'
                WHERE fetch_status = 'fetching'
                '''
            )
            if not self._in_transaction:
                self._conn.commit()

    reset_stuck_product_fetch_jobs = reset_stuck_jobs

    def get_fetched_product(
        self,
    ) -> tuple[int, str, str, str] | tuple[None, None, None, None]:
        """Gets 1 fetched, unparsed product webpage and atomically claims it as parsing."""
        with self._lock:
            self._discard_uncommitted_product_update()
            attempted_ids: set[int] = set()
            while True:
                self._cur.execute(
                    '''
                    SELECT id, product_url, product_name, filename
                    FROM ProductPages
                    WHERE fetch_status = ?
                    AND parse_status IS NULL
                    ORDER BY id
                    LIMIT 1
                    ''',
                    ('fetched',),
                )
                row = self._cur.fetchone()

                if row is None:
                    return None, None, None, None

                row_id, product_url, product_name, filename = row
                if row_id in attempted_ids:
                    return None, None, None, None
                attempted_ids.add(row_id)

                self._cur.execute(
                    'UPDATE ProductPages SET parse_status = ? WHERE id = ? AND fetch_status = ? AND parse_status IS NULL',
                    ('parsing', row_id, 'fetched'),
                )
                self._conn.commit()

                if self._cur.rowcount == 1:
                    return row_id, product_url, product_name, filename

    claim_fetched_product = get_fetched_product

    def update_product_data(self, row_id: int, product: dict, date: str) -> bool:
        """Updates parsed product data fields within the current transaction."""
        with self._lock:
            self._discard_uncommitted_product_update()
            self._cur.execute(
                '''
                UPDATE ProductPages
                SET
                    product_name = ?,
                    currency = ?,
                    price = ?,
                    product_code = ?,
                    reviews = ?,
                    images = ?,
                    fetched_at = ?
                WHERE id = ?
                ''',
                (
                    product["slug"],
                    product["currency"],
                    product["price"],
                    product["product_code"],
                    product['reviews'],
                    product['images'][0],
                    date,
                    row_id,
                ),
            )
            self._has_uncommitted_product_update = True
            return True

    def update_parse_status(self, row_id: int, status: str) -> None:
        """Updates parse_status of a product page in the DB."""
        with self._lock:
            if status != "parsed_succeeded":
                self._discard_uncommitted_product_update()
            try:
                self._cur.execute(
                    'UPDATE ProductPages SET parse_status = ? WHERE id = ?',
                    (status, row_id),
                )
                if not self._in_transaction:
                    self._conn.commit()
                    self._has_uncommitted_product_update = False
            except Exception:
                if not self._in_transaction:
                    self._conn.rollback()
                    self._has_uncommitted_product_update = False
                raise

    def save_parsed_product(self, row_id: int, product: dict, date: str) -> bool:
        """Transactionally updates parsed product data and marks parse_status as parsed_succeeded."""
        with self.transaction():
            self.update_product_data(row_id, product, date)
            self.update_parse_status(row_id, status="parsed_succeeded")
        return True

    def reset_stuck_parsing_jobs(self) -> None:
        """Resets stuck parsing jobs back to NULL parse_status."""
        with self._lock:
            self._discard_uncommitted_product_update()
            self._cur.execute(
                '''
                UPDATE ProductPages
                SET parse_status = NULL
                WHERE parse_status = "parsing"
                '''
            )
            if not self._in_transaction:
                self._conn.commit()

    # ------------------------------------------------------------------
    # Public inspection helpers
    # ------------------------------------------------------------------

    def get_table_names(self) -> list[str]:
        """Returns the list of table names in the database."""
        with self._lock:
            self._cur.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            return [row[0] for row in self._cur.fetchall()]

    def get_url_record(self, url: str) -> tuple | None:
        """Returns (id, url_name, date, filename, status) for a URL."""
        with self._lock:
            self._cur.execute(
                "SELECT id, url_name, date, filename, status FROM Urls WHERE url_name = ?",
                (url,),
            )
            return self._cur.fetchone()

    def get_all_urls(self) -> list[tuple[str | None, str | None]]:
        """Returns (url_name, status) for all URLs ordered by url_name."""
        with self._lock:
            self._cur.execute("SELECT url_name, status FROM Urls ORDER BY url_name")
            return self._cur.fetchall()

    def count_urls(self, url: str) -> int:
        """Returns the number of rows in Urls matching url_name."""
        with self._lock:
            self._cur.execute("SELECT Count(*) FROM Urls WHERE url_name = ?", (url,))
            row = self._cur.fetchone()
            return row[0] if row else 0

    def get_product_status(
        self, product_url: str | None = None
    ) -> tuple[str | None, str | None] | None:
        """Returns (fetch_status, parse_status) for the given product_url (or NULL product_url)."""
        with self._lock:
            if product_url is None:
                self._cur.execute(
                    "SELECT fetch_status, parse_status FROM ProductPages WHERE product_url IS NULL"
                )
            else:
                self._cur.execute(
                    "SELECT fetch_status, parse_status FROM ProductPages WHERE product_url = ?",
                    (product_url,),
                )
            return self._cur.fetchone()

    def get_product_record(self, product_url: str) -> tuple | None:
        """Returns full row for a product_url from ProductPages."""
        with self._lock:
            self._cur.execute(
                """
                SELECT id, product_url, product_code, product_name, price, currency,
                    description, fetch_status, parse_status, condition, seller,
                    reviews, images, fetched_at, filename
                FROM ProductPages
                WHERE product_url = ?
                """,
                (product_url,),
            )
            return self._cur.fetchone()

CrawlerDatabase = Database

def db_initialization(path: str | Path) -> Database:
    """Initializes the database abstraction and sets up the corresponding tables."""
    return Database(path)

def insert_url(url: str, db: Database, date: str) -> None:
    """Inserts a URL if it doesn't exist."""
    db.insert_url(url, date)

def already_pending_or_fetched_url(url: str, db: Database) -> bool:
    """Checks if the URL is already pending or fetched."""
    return db.already_pending_or_fetched_url(url)

def update_url_status(url: str, db: Database, status: str) -> None:
    """Sets the crawling status of an URL: pending / fetched / failed."""
    db.update_url_status(url, status)

def db_cur_and_conn_closer(db: Database | None) -> None:
    """Closes the database resources."""
    if db is not None:
        db.close()

def insert_product_url(db: Database, individual_product: dict) -> None:
    """Stores product information related to a product URL in the database."""
    db.insert_product_url(individual_product)


