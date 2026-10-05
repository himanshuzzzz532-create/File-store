import sqlite3
import random
import string
from datetime import datetime

DB_PATH = "filestore.db"

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        c = self.conn.cursor()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                coins       INTEGER DEFAULT 0,
                joined_at   TEXT
            );

            CREATE TABLE IF NOT EXISTS files (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                price       INTEGER NOT NULL,
                content     TEXT NOT NULL,
                created_at  TEXT
            );

            CREATE TABLE IF NOT EXISTS purchases (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER,
                file_id     INTEGER,
                purchased_at TEXT
            );

            CREATE TABLE IF NOT EXISTS referrals (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER,
                created_at  TEXT
            );

            CREATE TABLE IF NOT EXISTS redeem_codes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                code        TEXT UNIQUE,
                coins       INTEGER,
                max_uses    INTEGER,
                used_count  INTEGER DEFAULT 0,
                created_at  TEXT
            );

            CREATE TABLE IF NOT EXISTS code_uses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                code_id     INTEGER,
                user_id     INTEGER,
                used_at     TEXT
            );
        """)
        self.conn.commit()

    # ── USERS ──────────────────────────────────────────────────────────────
    def add_user(self, user_id, username):
        """Returns True if new user, False if existing."""
        c = self.conn.cursor()
        c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        if c.fetchone():
            return False
        c.execute(
            "INSERT INTO users (user_id, username, coins, joined_at) VALUES (?,?,?,?)",
            (user_id, username, 0, datetime.now().isoformat())
        )
        self.conn.commit()
        return True

    def user_exists(self, user_id):
        c = self.conn.cursor()
        c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        return c.fetchone() is not None

    def find_user(self, uid_or_name):
        c = self.conn.cursor()
        if str(uid_or_name).isdigit():
            c.execute("SELECT * FROM users WHERE user_id=?", (int(uid_or_name),))
        else:
            c.execute("SELECT * FROM users WHERE username=?", (uid_or_name,))
        row = c.fetchone()
        return dict(row) if row else None

    def get_all_users(self):
        c = self.conn.cursor()
        c.execute("SELECT * FROM users ORDER BY coins DESC")
        return [dict(r) for r in c.fetchall()]

    # ── COINS ──────────────────────────────────────────────────────────────
    def get_coins(self, user_id):
        c = self.conn.cursor()
        c.execute("SELECT coins FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        return row['coins'] if row else 0

    def add_coins(self, user_id, amount):
        c = self.conn.cursor()
        c.execute("UPDATE users SET coins = coins + ? WHERE user_id=?", (amount, user_id))
        self.conn.commit()

    def deduct_coins(self, user_id, amount):
        c = self.conn.cursor()
        c.execute("UPDATE users SET coins = coins - ? WHERE user_id=?", (amount, user_id))
        self.conn.commit()

    # ── FILES ──────────────────────────────────────────────────────────────
    def add_file(self, name, price, content):
        c = self.conn.cursor()
        c.execute(
            "INSERT INTO files (name, price, content, created_at) VALUES (?,?,?,?)",
            (name, price, content, datetime.now().isoformat())
        )
        self.conn.commit()

    def get_all_files(self):
        c = self.conn.cursor()
        c.execute("SELECT * FROM files ORDER BY id")
        return [dict(r) for r in c.fetchall()]

    def get_file(self, file_id):
        c = self.conn.cursor()
        c.execute("SELECT * FROM files WHERE id=?", (file_id,))
        row = c.fetchone()
        return dict(row) if row else None

    def remove_file(self, file_id):
        c = self.conn.cursor()
        c.execute("DELETE FROM files WHERE id=?", (file_id,))
        self.conn.commit()

    # ── PURCHASES ──────────────────────────────────────────────────────────
    def record_purchase(self, user_id, file_id):
        c = self.conn.cursor()
        c.execute(
            "INSERT INTO purchases (user_id, file_id, purchased_at) VALUES (?,?,?)",
            (user_id, file_id, datetime.now().isoformat())
        )
        self.conn.commit()

    def already_purchased(self, user_id, file_id):
        c = self.conn.cursor()
        c.execute(
            "SELECT id FROM purchases WHERE user_id=? AND file_id=?",
            (user_id, file_id)
        )
        return c.fetchone() is not None

    def get_purchase_count(self, user_id):
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) as cnt FROM purchases WHERE user_id=?", (user_id,))
        return c.fetchone()['cnt']

    # ── REFERRALS ──────────────────────────────────────────────────────────
    def record_referral(self, referrer_id, referred_id):
        c = self.conn.cursor()
        c.execute(
            "INSERT INTO referrals (referrer_id, referred_id, created_at) VALUES (?,?,?)",
            (referrer_id, referred_id, datetime.now().isoformat())
        )
        self.conn.commit()

    def get_referral_count(self, user_id):
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) as cnt FROM referrals WHERE referrer_id=?", (user_id,))
        return c.fetchone()['cnt']

    # ── REDEEM CODES ───────────────────────────────────────────────────────
    def create_redeem_code(self, coins, max_uses):
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        c = self.conn.cursor()
        c.execute(
            "INSERT INTO redeem_codes (code, coins, max_uses, created_at) VALUES (?,?,?,?)",
            (code, coins, max_uses, datetime.now().isoformat())
        )
        self.conn.commit()
        return code

    def use_redeem_code(self, code, user_id):
        c = self.conn.cursor()
        c.execute("SELECT * FROM redeem_codes WHERE code=?", (code,))
        row = c.fetchone()

        if not row:
            return "not_found"

        row = dict(row)
        if row['used_count'] >= row['max_uses']:
            return "expired"

        c.execute(
            "SELECT id FROM code_uses WHERE code_id=? AND user_id=?",
            (row['id'], user_id)
        )
        if c.fetchone():
            return "already_used"

        c.execute(
            "UPDATE redeem_codes SET used_count = used_count + 1 WHERE id=?",
            (row['id'],)
        )
        c.execute(
            "INSERT INTO code_uses (code_id, user_id, used_at) VALUES (?,?,?)",
            (row['id'], user_id, datetime.now().isoformat())
        )
        self.conn.commit()
        self.add_coins(user_id, row['coins'])
        return row['coins']

    # ── LEADERBOARD ────────────────────────────────────────────────────────
    def get_leaderboard(self):
        c = self.conn.cursor()
        c.execute("SELECT username, coins FROM users ORDER BY coins DESC LIMIT 10")
        return [dict(r) for r in c.fetchall()]

    # ── STATS ──────────────────────────────────────────────────────────────
    def get_stats(self):
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) as cnt FROM users")
        users = c.fetchone()['cnt']
        c.execute("SELECT COUNT(*) as cnt FROM files")
        files = c.fetchone()['cnt']
        c.execute("SELECT COUNT(*) as cnt FROM purchases")
        purchases = c.fetchone()['cnt']
        c.execute("SELECT COUNT(*) as cnt FROM redeem_codes WHERE used_count < max_uses")
        codes = c.fetchone()['cnt']
        return {"users": users, "files": files, "purchases": purchases, "codes": codes}
