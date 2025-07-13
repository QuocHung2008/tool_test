import sys
import json
import sqlite3
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
        self.connect()
        self.create_tables()

    def connect(self):
        config = Path(__file__).parent / "config.json"
        if config.exists() and USE_MYSQL:
            with open(config) as f:
                conf = json.load(f).get("remote", {})
            try:
                self.conn = pymysql.connect(
                    host=conf["host"], user=conf["user"], password=conf["password"],
                    database=conf["database"], cursorclass=pymysql.cursors.DictCursor,
                    charset="utf8mb4", autocommit=True
                )
                self.db_type = "mysql"
                return
            except:
                pass
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
                    name TEXT, cccd TEXT, items TEXT,
                    total_amount DOUBLE, date_pawn TEXT,
                    date_redeemed TEXT, status TEXT
                )''')
        else:
            self.execute('''
                CREATE TABLE IF NOT EXISTS pawn_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT, cccd TEXT, items TEXT,
                    total_amount REAL, date_pawn TEXT,
                    date_redeemed TEXT, status TEXT
                )''')

    def add_record(self, name, cccd, items, total_amount, date_pawn):
        args = (name, cccd, json.dumps(items), total_amount, date_pawn)
        if self.db_type == "mysql":
            sql = "INSERT INTO pawn_records (name, cccd, items, total_amount, date_pawn, status) VALUES (%s,%s,%s,%s,%s,'Chưa Chuộc')"
        else:
            sql = "INSERT INTO pawn_records (name, cccd, items, total_amount, date_pawn, status) VALUES (?,?,?,?,?,'Chưa Chuộc')"
        self.execute(sql, args)

    def update_status(self, record_id, new_status):
        now = date.today().isoformat()
        args = (new_status, now, record_id)
        if self.db_type == "mysql":
            sql = "UPDATE pawn_records SET status=%s, date_redeemed=%s WHERE id=%s"
        else:
            sql = "UPDATE pawn_records SET status=?, date_redeemed=? WHERE id=?"
        self.execute(sql, args)
        return now

    def all_records(self):
        cur = self.execute("SELECT * FROM pawn_records")
        rows = cur.fetchall()
        normalized = []
        for row in rows:
            if self.db_type == "mysql":
                normalized.append((
                    row['id'], row['name'], row['cccd'], row['items'],
                    float(row['total_amount']), row['date_pawn'], row['date_redeemed'], row['status']
                ))
            else:
                normalized.append((
                    row['id'], row['name'], row['cccd'], row['items'],
                    row['total_amount'], row['date_pawn'], row['date_redeemed'], row['status']
                ))
        return normalized

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.db = PawnDB()
        self.init_ui()
        self.load_records()
        self.update_footer()

    def init_ui(self):
        self.setWindowTitle("Phần mềm Quản lý Cầm cố")
        self.setGeometry(100, 100, 1200, 650)

        form = QFormLayout()
        self.name_input = QLineEdit(); self.name_input.setMinimumWidth(300)
        self.cccd_input = QLineEdit(); self.cccd_input.setMinimumWidth(300)
        form.addRow("Họ và tên:", self.name_input)
        form.addRow("Số CCCD:", self.cccd_input)

        self.total_input = QSpinBox(); self.total_input.setMaximum(10**9); self.total_input.setPrefix("VNĐ "); self.total_input.setMinimumWidth(200)
        form.addRow("Tổng số tiền cầm:", self.total_input)

        self.items_table = QTableWidget(0, 5)
        self.items_table.setHorizontalHeaderLabels(["SL","Món hàng","Trọng lượng (Chỉ)","15K","23K"])
        hdr = self.items_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Fixed); self.items_table.setColumnWidth(0,50)
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        for i in (2,3,4): hdr.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        add_item_btn = QPushButton("Thêm Món"); add_item_btn.clicked.connect(self.add_item_row)
        remove_item_btn = QPushButton("Xóa Món Được Chọn"); remove_item_btn.clicked.connect(self.remove_selected_item)
        form.addRow(add_item_btn, remove_item_btn)
        form.addRow(self.items_table)

        self.add_btn = QPushButton("Thêm Khách"); self.add_btn.clicked.connect(self.add_record)

        ctrl = QHBoxLayout()
        self.search_field = QComboBox(); self.search_field.addItems(["name","cccd","item"])
        self.search_input = QLineEdit(); self.search_input.setPlaceholderText("Tìm từ khóa")
        self.date_from = QDateEdit(); self.date_from.setCalendarPopup(True); self.date_from.setDisplayFormat("yyyy-MM-dd"); self.date_from.setDate(date.today().replace(day=1))
        self.date_to = QDateEdit(); self.date_to.setCalendarPopup(True); self.date_to.setDisplayFormat("yyyy-MM-dd"); self.date_to.setDate(date.today())
        self.sort_status = QComboBox(); self.sort_status.addItems(["Không","Chưa Chuộc lên trước","Đã Chuộc lên trước"]);
        self.search_btn = QPushButton("Áp dụng"); self.search_btn.clicked.connect(self.load_records)
        for w in [QLabel("Tìm theo:"),self.search_field,self.search_input,QLabel("Từ ngày:"),self.date_from,QLabel("Đến ngày:"),self.date_to,QLabel("Sắp xếp"),self.sort_status,self.search_btn]: ctrl.addWidget(w)

        self.table = QTableWidget(0,9)
        self.table.setHorizontalHeaderLabels(["ID","Khách","CCCD","Món (SL,Chỉ)","Tổng tiền","Ngày cầm","Ngày chuộc","Trạng thái","Lãi (VNĐ)"])
        th = self.table.horizontalHeader()
        th.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        th.setSectionResizeMode(1, QHeaderView.Stretch)
        th.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        th.setSectionResizeMode(3, QHeaderView.Stretch)
        for i in (4,5,6,7,8): th.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.table.cellDoubleClicked.connect(self.change_status)

        self.footer = QLabel()
        timer = QTimer(self); timer.timeout.connect(self.update_footer); timer.start(60000)

        main = QVBoxLayout(); main.addLayout(form); main.addWidget(self.add_btn); main.addLayout(ctrl); main.addWidget(self.table); main.addWidget(self.footer)
        self.setLayout(main)

    def add_item_row(self):
        r = self.items_table.rowCount(); self.items_table.insertRow(r)
        self.items_table.setItem(r,0,QTableWidgetItem("1")); self.items_table.setItem(r,1,QTableWidgetItem("")); self.items_table.setItem(r,2,QTableWidgetItem(""))
        self.items_table.setCellWidget(r,3,QCheckBox()); self.items_table.setCellWidget(r,4,QCheckBox())

    def remove_selected_item(self):
        r = self.items_table.currentRow()
        if r >= 0: self.items_table.removeRow(r)

    def clear_inputs(self):
        self.name_input.clear(); self.cccd_input.clear(); self.total_input.setValue(0); self.items_table.setRowCount(0)

    def add_record(self):
        name = self.name_input.text().strip(); cccd = self.cccd_input.text().strip()
        if not name or not cccd or self.items_table.rowCount() == 0: QMessageBox.warning(self,"Lỗi","Thiếu thông tin."); return
        items = []
        for r in range(self.items_table.rowCount()):
            qty = int(self.items_table.item(r,0).text()); desc = self.items_table.item(r,1).text(); wt = float(self.items_table.item(r,2).text())
            purity = '15K' if self.items_table.cellWidget(r,3).isChecked() else ('23K' if self.items_table.cellWidget(r,4).isChecked() else '')
            items.append({"qty":qty,"desc":desc,"wt":wt,"purity":purity})
        total = self.total_input.value(); dp = date.today().isoformat()
        self.db.add_record(name,cccd,items,total,dp)
        self.load_records(); self.update_footer(); self.clear_inputs()

    def compute_interest(self, principal, start, end):
        d1 = datetime.fromisoformat(start); d2 = datetime.fromisoformat(end)
        days = (d2-d1).days or 1
        return principal * INTEREST_RATE * days / 30

    def load_records(self):
        recs = self.db.all_records(); key = self.search_input.text().strip().lower(); sf = self.search_field.currentText()
        df = self.date_from.date().toString("yyyy-MM-dd"); dt = self.date_to.date().toString("yyyy-MM-dd"); order = self.sort_status.currentText(); data = []
        for r in recs:
            id_, nm, cc, items_json, total, dp, dr, st = r
            if not (df <= dp <= dt): continue
            try: items = json.loads(items_json)
            except: continue
            if sf == 'item' and not any(key in it['desc'].lower() for it in items): continue
            if sf == 'name' and key not in nm.lower(): continue
            if sf == 'cccd' and key not in cc: continue
            data.append((id_,nm,cc,items,total,dp,dr,st))
        if order == 'Chưa Chuộc lên trước': data.sort(key=lambda x:x[7] != 'Chưa Chuộc')
        elif order == 'Đã Chuộc lên trước': data.sort(key=lambda x:x[7] != 'Đã Chuộc')

        self.table.setRowCount(0)
        for id_, nm, cc, items, total, dp, dr, st in data:
            descs = [f"{it['qty']}x{it['desc']}({it['wt']}Chỉ)" for it in items]
            dr_display = dr if st == 'Đã Chuộc' else ''
            intr = self.compute_interest(total, dp, dr_display or dp)
            row = self.table.rowCount(); self.table.insertRow(row)
            vals = [id_, nm, cc, "; ".join(descs), f"{total:,.0f}".replace(',', '.'), dp, dr_display, st, f"{intr:,.0f}".replace(',', '.')]
            for i, v in enumerate(vals): self.table.setItem(row, i, QTableWidgetItem(str(v)))

    def change_status(self, row, _):
        id_ = int(self.table.item(row, 0).text()); cur = self.table.item(row, 7).text()
        nxt = 'Đã Chuộc' if cur == 'Chưa Chuộc' else 'Chưa Chuộc'
        if QMessageBox.question(self, 'Xác nhận', f'Chuyển thành {nxt}?', QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            rd = self.db.update_status(id_, nxt)
            self.load_records(); self.update_footer()
            rec = [r for r in self.db.all_records() if r['id'] == id_][0]
            intr = self.compute_interest(rec['total_amount'], rec['date_pawn'], rd)
            QMessageBox.information(self, 'Thông tin chuộc',
                f"ID: {id_}\nKhách: {rec['name']}\nTổng tiền: {rec['total_amount']:,.0f}\nNgày cầm: {rec['date_pawn']}\nNgày chuộc: {rd}\nLãi: {intr:,.0f}".replace(',', '.')
            )

    def update_footer(self):
        today = date.today()
        first_date = today.replace(day=1)
        first = first_date.isoformat()
        if self.db.db_type == "mysql":
            sql = "SELECT total_amount, status, date_pawn, date_redeemed FROM pawn_records WHERE date_pawn >= %s"
        else:
            sql = "SELECT total_amount, status, date_pawn, date_redeemed FROM pawn_records WHERE date_pawn >= ?"
        rows = self.db.execute(sql, (first,)).fetchall()
        tp = ti = 0.0
        for row in rows:
            if self.db.db_type == "mysql":
                tot = float(row['total_amount'])
                st = row['status']
                dp = row['date_pawn']
                dr = row['date_redeemed']
            else:
                tot, st, dp, dr = row
            tp += tot
            pd = datetime.fromisoformat(dp).date()
            if st == 'Chưa Chuộc':
                days = (today - pd).days + 1
            else:
                days = 0
                if dr:
                    rd = datetime.fromisoformat(dr).date()
                    fd = first_date
                    if rd >= fd:
                        days = (rd - fd).days + 1
            ti += tot * INTEREST_RATE * days / 30
        self.footer.setText(
            f"Tổng cầm: {tp:,.0f}".replace(",", ".") +
            f" VNĐ  |  Lãi tháng: {ti:,.0f}".replace(",", ".")
        )

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
