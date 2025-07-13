import sys
import json
from datetime import date, datetime
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QWidget, QFormLayout, QLineEdit, QPushButton,
    QHBoxLayout, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QMessageBox, QLabel, QComboBox, QCheckBox, QSpinBox, QDateEdit,
    QHeaderView
)
from PyQt5.QtCore import Qt, QTimer

INTEREST_RATE = 0.025
DB_PATH = Path(__file__).parent / "pawn.db"

try:
    import pymysql
    USE_MYSQL = True
except ImportError:
    USE_MYSQL = False

class PawnDB:
    def __init__(self):
        self.conn = None
        self.connect()
        self.create_tables()

    def connect(self):
        config_path = Path(__file__).parent / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                conf = json.load(f).get("remote")
            try:
                self.conn = pymysql.connect(
                    host=conf["host"], user=conf["user"], password=conf["password"],
                    database=conf["database"], cursorclass=pymysql.cursors.DictCursor,
                    charset="utf8mb4", autocommit=True
                )
                self.db_type = "mysql"
                return
            except Exception as e:
                print("Lỗi kết nối MySQL:", e)
        import sqlite3
        self.conn = sqlite3.connect(str(DB_PATH))
        self.conn.row_factory = sqlite3.Row
        self.db_type = "sqlite"

    def execute(self, sql, args=()):
        cur = self.conn.cursor()
        cur.execute(sql, args)
        return cur

    def create_tables(self):
        if self.db_type == "mysql":
            self.execute('''
                CREATE TABLE IF NOT EXISTS pawn_records (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name TEXT,
                    cccd TEXT,
                    items TEXT,
                    total_amount DOUBLE,
                    date_pawn TEXT,
                    date_redeemed TEXT,
                    status TEXT
                )''')
        else:
            self.execute('''
                CREATE TABLE IF NOT EXISTS pawn_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    cccd TEXT,
                    items TEXT,
                    total_amount REAL,
                    date_pawn TEXT,
                    date_redeemed TEXT,
                    status TEXT
                )''')

    def add_record(self, name, cccd, items, total_amount, date_pawn):
        sql = "INSERT INTO pawn_records (name, cccd, items, total_amount, date_pawn, status) VALUES (%s, %s, %s, %s, %s, 'Chưa Chuộc')"
        self.execute(sql, (name, cccd, json.dumps(items), total_amount, date_pawn))

    def update_status(self, record_id, new_status):
        now = date.today().isoformat()
        sql = "UPDATE pawn_records SET status = %s, date_redeemed = %s WHERE id = %s"
        self.execute(sql, (new_status, now, record_id))
        return now

    def all_records(self):
        cur = self.execute("SELECT * FROM pawn_records")
        return cur.fetchall()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.db = PawnDB()
        self.init_ui()
        self.load_records()
        self.update_footer()

    # ... không thay đổi phần còn lại của MainWindow ...

if __name__ == '__main__':
    app = QApplication(sys.argv); win = MainWindow(); win.show(); sys.exit(app.exec_())
