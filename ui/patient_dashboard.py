from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFrame, QLineEdit, QFormLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QTextEdit, QMessageBox, QDialog,
    QGridLayout, QScrollArea, QCalendarWidget, QDateEdit, QSpinBox, QApplication, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QFont, QColor, QPixmap, QIcon, QPainter
from PyQt6.QtCore import Qt, QDate
from db import DB
from functools import partial
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
import os
import re

# --- Booking Dialog ---
class BookingDialog(QDialog):
    def __init__(self, patient_id, service=None, parent=None):
        super().__init__(parent)
        self.patient_id = patient_id
        self.service = service
        self.setWindowTitle("Book Appointment")
        self.setFixedSize(520, 380)
        self.setStyleSheet("""
            QDialog { background: #fff; border-radius: 12px; }
            QLabel {
                color: black; font-size: 14px; background: transparent; border: none;
            }
            QLineEdit, QTextEdit, QComboBox, QDateEdit, QSpinBox {
                color: black; font-size: 14px; padding: 8px; border: 1px solid #d8eafd; border-radius: 8px; background: #f8fbfd;
                selection-background-color: #02afd2; selection-color: white;
            }
            QLineEdit::placeholder { color: #222; }
            QComboBox QAbstractItemView {
                color: black; background: white; selection-background-color: #02afd2; selection-color: white;
            }
            QPushButton {
                background: #02afd2; color: white; padding: 10px 16px; border-radius: 8px;
                font-weight: bold; font-size: 15px; min-width: 120px;
            }
            QPushButton:hover { background: #0177c2; }
            QMessageBox { color: black; }
        """)
        self.init_ui()

    def showEvent(self, ev):
        parent = self.parentWidget()
        if parent:
            parent_center = parent.frameGeometry().center()
        else:
            parent_center = QApplication.primaryScreen().availableGeometry().center()
        final_geo = self.frameGeometry()
        final_geo.moveCenter(parent_center)
        self.setGeometry(final_geo)
        super().showEvent(ev)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        title = QLabel("Book a New Appointment")
        title.setFont(QFont("Segoe UI", 17, QFont.Weight.Bold))
        title.setStyleSheet("color: #0177c2; border: none;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.service_cb = QComboBox()
        db = DB()
        services = db.query("SELECT id, name, price FROM services ORDER BY name ASC")
        db.close()
        self.service_map = {}
        for s in services:
            self.service_cb.addItem(f"{s['name']} (₱{float(s.get('price') or 0):,.2f})", s['id'])
            self.service_map[s['id']] = s
        if self.service:
            idx = self.service_cb.findData(self.service.get('id'))
            if idx >= 0:
                self.service_cb.setCurrentIndex(idx)
            self.service_cb.setDisabled(True)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.time_input = QLineEdit()
        self.time_input.setPlaceholderText("e.g. 14:30 (24-hour format)")
        self.notes = QTextEdit()
        self.notes.setFixedHeight(60)

        form.addRow("Service:", self.service_cb)
        form.addRow("Date:", self.date_edit)
        form.addRow("Time (HH:MM):", self.time_input)
        form.addRow("Notes:", self.notes)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        book_btn = QPushButton("Book")
        book_btn.setIcon(QIcon("icons/book.png"))  # Assume you have an icon file
        book_btn.clicked.connect(self.book)
        btn_row.addWidget(book_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setIcon(QIcon("icons/cancel.png"))  # Assume you have an icon file
        cancel_btn.setStyleSheet("background: #999; color: white; border-radius:8px; padding:10px;")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def book(self):
        svc_id = self.service_cb.currentData()
        dt = self.date_edit.date().toString("yyyy-MM-dd")
        tm = self.time_input.text().strip()
        notes = self.notes.toPlainText().strip()
        if not tm:
            QMessageBox.warning(self, "Validation", "Please enter a time for the appointment.")
            return
        if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', tm):
            QMessageBox.warning(self, "Validation", "Invalid time format. Use HH:MM (00:00 to 23:59).")
            return
        db = DB()
        try:
            db.query(
                "INSERT INTO appointments (patient_id, service_id, date, time, notes, status) VALUES (%s,%s,%s,%s,%s,'Pending')",
                (self.patient_id, svc_id, dt, tm, notes),
                commit=True
            )
            QMessageBox.information(self, "Booked", "Appointment booked successfully (Pending).")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to book appointment: {e}")
        finally:
            db.close()

# --- Profile Dialog ---
class ProfileDialog(QDialog):
    def __init__(self, patient_id, parent=None):
        super().__init__(parent)
        self.patient_id = patient_id
        self.setWindowTitle("Edit Profile")
        self.setFixedSize(480, 340)
        self.setStyleSheet("""
            QDialog { background: #fff; border-radius: 12px; }
            QLabel {
                color: black; font-size: 14px; background: transparent; border: none;
            }
            QLineEdit, QComboBox, QSpinBox {
                color: black; font-size: 14px; padding: 8px; border: 1px solid #d8eafd; border-radius: 8px; background: #f8fbfd;
                selection-background-color: #02afd2; selection-color: white;
            }
            QComboBox QAbstractItemView {
                color: black; background: white; selection-background-color: #02afd2; selection-color: white;
            }
            QLineEdit::placeholder { color: #222; }
            QPushButton {
                background: #02afd2; color: white; padding: 10px 16px; border-radius: 8px;
                font-weight: bold; min-width: 100px;
            }
            QPushButton:hover { background: #0177c2; }
            QPushButton.cancel { background: #999; }
            QPushButton.cancel:hover { background: #777; }
            QMessageBox { color: black; }
        """)
        self.init_ui()

    def showEvent(self, ev):
        parent = self.parentWidget()
        if parent:
            parent_center = parent.frameGeometry().center()
        else:
            parent_center = QApplication.primaryScreen().availableGeometry().center()
        final_geo = self.frameGeometry()
        final_geo.moveCenter(parent_center)
        self.setGeometry(final_geo)
        super().showEvent(ev)

    def init_ui(self):
        db = DB()
        try:
            rows = db.query("SELECT * FROM patients WHERE id=%s", (self.patient_id,))
            if not rows:
                raise ValueError("Profile not found.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Profile DB error: {e}")
            db.close()
            self.setDisabled(True)
            return
        finally:
            db.close()

        p = rows[0]
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)

        title = QLabel("Edit My Profile")
        title.setFont(QFont("Segoe UI", 17, QFont.Weight.Bold))
        title.setStyleSheet("color: #0177c2; margin-bottom: 6px; border: none;")
        layout.addWidget(title)

        form_layout = QFormLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(14)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.name = QLineEdit(p.get('name') or "")
        self.age = QSpinBox()
        self.age.setRange(0, 150)
        self.age.setValue(int(p.get('age') or 0))

        self.sex = QComboBox()
        self.sex.addItems(["Male", "Female", "Other"])
        self.sex.setCurrentText(p.get('sex') or "Other")

        self.email = QLineEdit(p.get('email') or "")

        self.name.setMinimumWidth(280)
        self.email.setMinimumWidth(280)
        self.age.setFixedWidth(80)
        self.sex.setFixedWidth(140)

        form_layout.addRow("Full Name:", self.name)
        form_layout.addRow("Email:", self.email)

        subrow_grid = QGridLayout()
        subrow_grid.setContentsMargins(0, 0, 0, 0)
        subrow_grid.setSpacing(10)
        subrow_grid.addWidget(self.age, 0, 0)
        subrow_grid.addWidget(QLabel("Sex:"), 0, 1)
        subrow_grid.addWidget(self.sex, 0, 2)
        subrow_grid.setColumnStretch(3, 1)

        form_layout.addRow("Age / Sex:", subrow_grid)
        layout.addLayout(form_layout)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        save_btn = QPushButton("Save")
        save_btn.setIcon(QIcon("icons/save.png"))  # Assume icon
        save_btn.clicked.connect(self.save)
        btn_row.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancel")
        cancel_btn.setIcon(QIcon("icons/cancel.png"))  # Assume icon
        cancel_btn.setStyleSheet("background: #999;")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        layout.addLayout(btn_row)

    def save(self):
        nm = self.name.text().strip()
        em = self.email.text().strip()
        ag = self.age.value()
        sx = self.sex.currentText()
        if not all([nm, em]):
            QMessageBox.warning(self, "Validation", "Name and Email are required.")
            return
        db = DB()
        try:
            db.query("UPDATE patients SET name=%s, age=%s, sex=%s, email=%s WHERE id=%s",
                     (nm, ag or None, sx, em, self.patient_id), commit=True)
            QMessageBox.information(self, "Saved", "Profile saved successfully.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save profile: {e}")
        finally:
            db.close()

# --- Custom Calendar for Appointments ---
class AppointmentCalendar(QCalendarWidget):
    def __init__(self, patient_id, parent=None):
        super().__init__(parent)
        self.patient_id = patient_id
        self.appointment_dates = self.get_appointment_dates()
        self.setGridVisible(False)
        self.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.ShortDayNames)
        self.setStyleSheet("""
            QCalendarWidget { 
                background-color: #2b3440; color: white; border: none; 
                selection-background-color: #475569; selection-color: white; 
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar { background-color: transparent; border: none; }
            QCalendarWidget QToolButton { background-color: transparent; color: white; font-size: 15px; font-weight: bold; border: none; margin: 6px; }
            QCalendarWidget QToolButton:hover { color: #00bcd4; }
            QCalendarWidget QAbstractItemView { outline: 0; background-color: #2b3440; color: white; 
                selection-background-color: #475569; selection-color: white; gridline-color: #3b4758; border: none; }
            QCalendarWidget QAbstractItemView::item:selected { background-color: #475569; }
            QCalendarWidget QAbstractItemView::item:hover { background-color: #3b4758; }
        """)

    def get_appointment_dates(self):
        db = DB()
        try:
            res = db.query("SELECT date FROM appointments WHERE patient_id=%s AND status != 'Cancelled'", (self.patient_id,))
            dates = set(QDate.fromString(str(r['date']), "yyyy-MM-dd") for r in res)
            return dates
        except Exception as e:
            print(f"Error fetching appointment dates: {e}")
            return set()
        finally:
            db.close()

    def paintCell(self, painter, rect, date):
        super().paintCell(painter, rect, date)
        if date in self.appointment_dates:
            painter.setBrush(QColor(0, 255, 0, 100))  # Green highlight for appointments
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(rect.adjusted(2, 2, -2, -2))

# --- Main Patient Dashboard ---
class PatientDashboard(QWidget):
    def __init__(self, patient_id, patient_name, portal_parent=None):
        super().__init__()
        self.patient_id = patient_id
        self.patient_name = patient_name
        self.portal_parent = portal_parent
        self.setWindowTitle("🦷 PureDent Clinic — Patient Dashboard")
        self.resize(1200, 700)
        self.setMinimumSize(1000, 600)
        self.setStyleSheet("""
            QWidget { background-color: #e3f2fd; }
            QMessageBox { color: black; }
        """)
        self.init_ui()

    def init_ui(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet("""
            QFrame { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #02afd2, stop:1 #01777f); }
            QLabel#brand { color: white; font-weight: 800; border: none; }
            QPushButton { background: transparent; border: none; color: white; text-align: left; padding: 10px 18px; font-weight: 600; }
            QPushButton:hover { background: rgba(255,255,255,0.06); }
            QPushButton[selected="true"] { background: rgba(255,255,255,0.08); }
        """)
        s_layout = QVBoxLayout(sidebar)
        s_layout.setContentsMargins(16, 28, 16, 16)
        s_layout.setSpacing(10)

        brand_lbl = QLabel("🦷 PureDent\n       Clinic")
        brand_lbl.setObjectName("brand")
        brand_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.ExtraBold))
        brand_lbl.setStyleSheet("color:white; margin-bottom: 6px; border: none;")
        s_layout.addWidget(brand_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        s_layout.addSpacing(6)

        self.nav_buttons = {}
        nav_items = [
            ("Dashboard", "home", "icons/home.png"),
            ("My Appointments", "my_appointments", "icons/appointments.png"),
            ("Book Appointment", "book_appointments", "icons/book.png"),
            ("Services", "services", "icons/services.png"),
            ("Transactions", "transactions", "icons/transactions.png"),
            ("Profile", "profile", "icons/profile.png"),
            ("Logout", "logout", "icons/logout.png")
        ]
        for label, key, icon_path in nav_items:
            btn = QPushButton(label)
            btn.setIcon(QIcon(icon_path))  # Assume icon files exist
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(partial(self.switch_section, key))
            btn.setProperty("selected", False)
            s_layout.addWidget(btn)
            self.nav_buttons[key] = btn
        s_layout.addStretch(1)
        outer.addWidget(sidebar)

        self.content_frame = QFrame()
        self.content_frame.setStyleSheet("""
            QFrame { background: transparent; }
            QLabel { color: black; font-size: 14px; border: none; }
            QLineEdit, QTableWidget, QHeaderView::section, QComboBox, QTextEdit, QDateEdit, QSpinBox, QPushButton {
                color: black; font-size: 14px;
            }
            QTableWidget, QHeaderView::section, QComboBox QAbstractItemView {
                color: black; background: white; selection-background-color: #02afd2; selection-color: white;
            }
        """)
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(28, 24, 28, 24)
        self.content_layout.setSpacing(18)
        outer.addWidget(self.content_frame, 1)

        self.switch_section("home")

    def set_active_nav(self, active_key):
        for key, btn in self.nav_buttons.items():
            btn.setProperty("selected", key == active_key)
            btn.setStyle(btn.style())

    def clear_content(self):
        while self.content_layout.count():
            it = self.content_layout.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()

    def switch_section(self, section):
        try:
            self.set_active_nav(section)
            if section not in ("book_appointments", "profile"):
                self.clear_content()

            if section == "home":
                self.render_home()
            elif section == "my_appointments":
                self.show_my_appointments()
            elif section == "book_appointments":
                dlg = BookingDialog(self.patient_id, parent=self)
                if dlg.exec():
                    self.switch_section("my_appointments")
                return
            elif section == "services":
                self.show_services()
            elif section == "transactions":
                self.show_transaction()
            elif section == "profile":
                self.show_profile_dialog()
                return
            elif section == "logout":
                self.logout()
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", str(e))

    def show_profile_dialog(self):
        dlg = ProfileDialog(self.patient_id, parent=self)
        dlg.exec()

    def render_home(self):
        card_colors = ["#e3f2fd", "#fffde7", "#e8f5e9"]

        header_card = QFrame()
        header_card.setStyleSheet("QFrame { background:white; border-radius:10px; border:1px solid #d8eafd; }")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 50))
        header_card.setGraphicsEffect(shadow)
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(20, 18, 20, 18)
        title = QLabel("Dashboard")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("border: none;")
        h_layout.addWidget(title)
        h_layout.addStretch(1)
        welcome = QLabel(f"Hi, {self.patient_name.split()[0]}! Remember to brush twice a day! 🪥")
        welcome.setFont(QFont("Segoe UI", 10))
        welcome.setStyleSheet("border: none;")
        h_layout.addWidget(welcome)
        self.content_layout.addWidget(header_card)

        stats_card = QFrame()
        stats_card.setStyleSheet("QFrame { background:white; border-radius:10px; border:1px solid #d8eafd; }")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 50))
        stats_card.setGraphicsEffect(shadow)
        cards_row = QHBoxLayout(stats_card)
        cards_row.setContentsMargins(22, 18, 22, 18)
        cards_row.setSpacing(22)

        upcoming = self.get_next_appointment()
        upcoming_value = upcoming['service'] if upcoming else "None"
        upcoming_details = upcoming.get('when', "") if upcoming else ""
        card_up = self._make_card_rightvalue("Upcoming Appointment", upcoming_value, details=upcoming_details, bg_color=card_colors[0])
        cards_row.addWidget(card_up)

        # Improved Recent Appointment as notification style
        recent_list = self.get_recent_completed(limit=1)
        recent_value = f"{recent_list[0]['service']}" if recent_list else "None"
        recent_details = f"{recent_list[0]['date']} {str(recent_list[0]['time'])}" if recent_list else ""
        card_recent = self._make_notification_card("Recent Appointment", recent_value, details=recent_details, bg_color=card_colors[1])
        cards_row.addWidget(card_recent)

        conf_count = self.get_confirmed_count()
        card_conf = self._make_card_rightvalue("Confirmed Appointments", str(conf_count), bg_color=card_colors[2])
        cards_row.addWidget(card_conf)

        self.content_layout.addWidget(stats_card)

        cards_side_by_side = QHBoxLayout()

        completed_card = QFrame()
        completed_card.setStyleSheet("QFrame { background: white; border: 1px solid #d8eafd; border-radius: 10px; }")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 50))
        completed_card.setGraphicsEffect(shadow)
        completed_layout = QVBoxLayout(completed_card)
        completed_layout.setContentsMargins(18, 12, 18, 12)
        completed_layout.setSpacing(8)

        lbl = QLabel("Completed Appointments")
        lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #333333; margin-bottom: 6px; border: none;")
        completed_layout.addWidget(lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        completed_rows = self.get_recent_completed(limit=50)
        row_colors = ["#f7faf9", "#eef5f2"]

        for idx, r in enumerate(completed_rows):
            row = QFrame()
            row.setFixedHeight(42)
            row.setStyleSheet(f"QFrame {{ background-color: {row_colors[idx % 2]}; border: none; }}")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(14, 0, 14, 0)
            row_layout.setSpacing(0)

            svc = QLabel(r.get('service', '—'))
            svc.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            svc.setStyleSheet("color: #1f2937; border: none;")
            svc.setFixedWidth(150)
            row_layout.addWidget(svc, alignment=Qt.AlignmentFlag.AlignVCenter)

            dt = QLabel(str(r.get('date', '')))
            dt.setFont(QFont("Segoe UI", 8))
            dt.setStyleSheet("color: #6b7280; border: none;")
            dt.setFixedWidth(100)
            row_layout.addWidget(dt, alignment=Qt.AlignmentFlag.AlignVCenter)

            t = str(r.get('time', ''))
            if ":" in t:
                try:
                    parts = t.split(":")
                    h, m = int(parts[0]), parts[1]
                    ampm = "AM" if h < 12 else "PM"
                    h = h if 1 <= h <= 12 else abs(h - 12) or 12
                    t = f"{h}:{m} {ampm}"
                except Exception:
                    pass
            tm = QLabel(t)
            tm.setFont(QFont("Segoe UI", 8))
            tm.setStyleSheet("color: #9ca3af; border: none;")
            tm.setFixedWidth(80)
            row_layout.addWidget(tm, alignment=Qt.AlignmentFlag.AlignVCenter)

            tag = QLabel("Completed")
            tag.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            tag.setStyleSheet("QLabel { background-color: #b8e9c1; color: #166534; padding: 2px 6px; border-radius: 4px; border: none; }")
            row_layout.addStretch()
            row_layout.addWidget(tag, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            container_layout.addWidget(row)

        container_layout.addStretch()
        scroll.setWidget(container)
        completed_layout.addWidget(scroll)

        cal_card = QFrame()
        cal_card.setStyleSheet("QFrame { background-color: #2b3440; border-radius: 10px; border: none; }")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 50))
        cal_card.setGraphicsEffect(shadow)
        cal_layout = QVBoxLayout(cal_card)
        cal_layout.setContentsMargins(20, 18, 20, 18)
        cal_layout.setSpacing(10)

        cal_lbl = QLabel("Calendar")
        cal_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        cal_lbl.setStyleSheet("color: white; margin-bottom: 4px; border: none;")
        cal_layout.addWidget(cal_lbl)

        self.calendar = AppointmentCalendar(self.patient_id)
        cal_layout.addWidget(self.calendar)

        cards_side_by_side.addWidget(completed_card, 2)
        cards_side_by_side.addWidget(cal_card, 1)
        self.content_layout.addLayout(cards_side_by_side)

        # Add Oral Health Tips section for more dental clinic feel
        tips_card = QFrame()
        tips_card.setStyleSheet("QFrame { background: white; border: 1px solid #d8eafd; border-radius: 10px; }")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 50))
        tips_card.setGraphicsEffect(shadow)
        tips_layout = QVBoxLayout(tips_card)
        tips_layout.setContentsMargins(18, 12, 18, 12)
        tips_layout.setSpacing(8)

        tips_lbl = QLabel("Oral Health Tips")
        tips_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        tips_lbl.setStyleSheet("color: #0177c2; margin-bottom: 6px; border: none;")
        tips_layout.addWidget(tips_lbl)

        tips_list = [
            "🪥 Brush your teeth twice a day for two minutes each time.",
            "🧵 Floss daily to remove plaque between teeth.",
            "🍎 Eat a balanced diet and limit sugary snacks.",
            "💧 Drink plenty of water to keep your mouth hydrated.",
            "🦷 Visit your dentist every six months for checkups."
        ]

        for tip in tips_list:
            tip_label = QLabel(tip)
            tip_label.setFont(QFont("Segoe UI", 9))
            tip_label.setStyleSheet("color: #333; border: none;")
            tip_label.setWordWrap(True)
            tips_layout.addWidget(tip_label)

        self.content_layout.addWidget(tips_card)

    def _make_card_rightvalue(self, title, value, details=None, bg_color="#f5f7fb"):
        card = QFrame()
        card.setMinimumWidth(260)
        card.setStyleSheet(f"QFrame {{ background: {bg_color}; border-radius: 12px; border: none; color: #111; }}")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 50))
        card.setGraphicsEffect(shadow)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #0177c2; border: none;")
        layout.addWidget(title_lbl, alignment=Qt.AlignmentFlag.AlignLeft)

        value_lbl = QLabel(value)
        value_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        value_lbl.setStyleSheet("color: #111; border: none;")
        layout.addWidget(value_lbl, alignment=Qt.AlignmentFlag.AlignLeft)

        if details:
            details_lbl = QLabel(details)
            details_lbl.setFont(QFont("Segoe UI", 9))
            details_lbl.setStyleSheet("color: #555; border: none;")
            layout.addWidget(details_lbl, alignment=Qt.AlignmentFlag.AlignLeft)

        return card

    def _make_notification_card(self, title, value, details=None, bg_color="#f5f7fb"):
        card = QFrame()
        card.setMinimumWidth(260)
        card.setStyleSheet(f"QFrame {{ background: {bg_color}; border-radius: 12px; border: 1px solid #ffd54f; color: #111; }}")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 50))
        card.setGraphicsEffect(shadow)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # Add bell icon for notification style
        icon_lbl = QLabel()
        icon_lbl.setPixmap(QPixmap("icons/bell.png").scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio))  # Assume you have a bell icon
        layout.addWidget(icon_lbl)

        content_layout = QVBoxLayout()
        content_layout.setSpacing(4)

        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #f57f17; border: none;")
        content_layout.addWidget(title_lbl)

        value_lbl = QLabel(value)
        value_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        value_lbl.setStyleSheet("color: #111; border: none;")
        content_layout.addWidget(value_lbl)

        if details:
            details_lbl = QLabel(details)
            details_lbl.setFont(QFont("Segoe UI", 9))
            details_lbl.setStyleSheet("color: #555; border: none;")
            content_layout.addWidget(details_lbl)

        layout.addLayout(content_layout)
        return card

    def show_my_appointments(self):
        table_card = QFrame()
        table_card.setStyleSheet("QFrame { background:white; border-radius:10px; border:1px solid #d8eafd; }")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 50))
        table_card.setGraphicsEffect(shadow)
        layout = QVBoxLayout(table_card)
        layout.setContentsMargins(22, 18, 22, 18)
        header = QLabel("My Appointments")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.setStyleSheet("border: none;")
        layout.addWidget(header)

        search_layout = QHBoxLayout()
        self.appointment_search = QLineEdit()
        self.appointment_search.setPlaceholderText("Search...")
        self.appointment_search.setFixedWidth(200)
        self.appointment_search.textChanged.connect(self.filter_appointments)
        search_layout.addWidget(QLabel("🔍"))
        search_layout.addWidget(self.appointment_search)
        search_layout.addStretch(1)
        layout.addLayout(search_layout)

        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(["Service", "Date", "Time", "Status", "Action"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setMinimumHeight(420)

        db = DB()
        try:
            rows = db.query("""
                SELECT a.id, s.name as service, a.date, a.time, a.status, a.notes
                FROM appointments a
                JOIN services s ON a.service_id = s.id
                WHERE a.patient_id = %s
                ORDER BY a.date DESC, a.time DESC
            """, (self.patient_id,))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load appointments: {e}")
            db.close()
            return
        finally:
            db.close()

        table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            table.setItem(i, 0, QTableWidgetItem(r['service']))
            table.setItem(i, 1, QTableWidgetItem(str(r['date'])))
            table.setItem(i, 2, QTableWidgetItem(str(r['time'])))
            status_item = QTableWidgetItem(r['status'])
            st = r['status'].lower()
            if st == "confirmed":
                status_item.setBackground(QColor("#43a047"))
                status_item.setForeground(QColor("white"))
            elif st == "cancelled":
                status_item.setBackground(QColor("#e53935"))
                status_item.setForeground(QColor("white"))
            elif st == "completed":
                status_item.setBackground(QColor("#2fb28a"))
                status_item.setForeground(QColor("white"))
            else:
                status_item.setBackground(QColor("#ffb74d"))
                status_item.setForeground(QColor("black"))
            table.setItem(i, 3, status_item)
            action_btn = QPushButton("Cancel")
            action_btn.setIcon(QIcon("icons/cancel.png"))  # Add icon for beauty
            action_btn.setStyleSheet("""
                QPushButton { background: #e53935; color: white; border-radius: 6px; padding: 6px; font-weight: bold; }
                QPushButton:hover { background: #c62828; }
                QPushButton:disabled { background: #bdbdbd; }
            """)
            if st in ("completed", "cancelled"):
                action_btn.setDisabled(True)
            action_btn.clicked.connect(partial(self.cancel_appointment, r['id']))
            table.setCellWidget(i, 4, action_btn)

        table.setStyleSheet("""
            QTableWidget { background: white; border: 1px solid #e6eefc; }
            QHeaderView::section { background:#f7fdff; color: black; font-weight: bold; border: none; }
        """)
        layout.addWidget(table)
        self.content_layout.addWidget(table_card)

        self.table_appointments_ref = table

    def filter_appointments(self, text):
        query = text.lower()
        table = self.table_appointments_ref
        for row in range(table.rowCount()):
            match = False
            for col in range(table.columnCount() - 1):
                item = table.item(row, col)
                if item and query in item.text().lower():
                    match = True
                    break
            table.setRowHidden(row, not match)

    def cancel_appointment(self, appointment_id):
        db = DB()
        try:
            reply = QMessageBox.question(
                self, "Confirm", "Cancel this appointment?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                db.query(
                    "UPDATE appointments SET status='Cancelled' WHERE id=%s",
                    (appointment_id,), commit=True
                )
                QMessageBox.information(self, "Cancelled", "Appointment cancelled.")
                self.switch_section("my_appointments")  # Refresh
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to cancel appointment: {e}")
        finally:
            db.close()

    def show_services(self):
        services_card = QFrame()
        services_card.setStyleSheet("QFrame { background:white; border-radius:10px; border:1px solid #d8eafd; }")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 50))
        services_card.setGraphicsEffect(shadow)
        layout = QVBoxLayout(services_card)
        layout.setContentsMargins(22, 18, 22, 18)
        header_layout = QHBoxLayout()
        header = QLabel("Services Catalog")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.setStyleSheet("border: none;")
        header_layout.addWidget(header)
        header_layout.addStretch(1)
        search_bar = QLineEdit()
        search_bar.setPlaceholderText("Search services...")
        search_bar.setFixedWidth(150)
        search_bar.setStyleSheet("""
            QLineEdit { padding: 8px; border: 1px solid #d8eafd; border-radius: 8px; background: #f8fbfd; }
        """)
        search_bar.textChanged.connect(self.filter_services)
        header_layout.addWidget(search_bar)
        layout.addLayout(header_layout)

        self.services_scroll = QScrollArea()
        self.services_scroll.setWidgetResizable(True)
        self.services_container = QWidget()
        self.services_grid = QGridLayout(self.services_container)
        self.services_grid.setSpacing(18)
        layout.addWidget(self.services_scroll)
        self.services_scroll.setWidget(self.services_container)
        self.content_layout.addWidget(services_card)

        self.populate_services("")

    def populate_services(self, search_text):
        while self.services_grid.count():
            item = self.services_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        db = DB()
        try:
            query = "SELECT id, name, description, price FROM services WHERE name LIKE %s ORDER BY name ASC"
            rows = db.query(query, (f"%{search_text}%",))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load services: {e}")
            db.close()
            return
        finally:
            db.close()

        for idx, r in enumerate(rows):
            card = QFrame()
            card.setMinimumWidth(260)
            card.setMaximumWidth(320)
            card.setStyleSheet("QFrame { background: #ffffff; border-radius: 18px; border: none; }")
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(10)
            shadow.setOffset(0, 4)
            shadow.setColor(QColor(0, 0, 0, 50))
            card.setGraphicsEffect(shadow)
            v = QVBoxLayout(card)
            v.setContentsMargins(14, 12, 14, 12)

            name = QLabel(r['name'])
            name.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            name.setStyleSheet("color: #111; border: none;")
            v.addWidget(name)

            price = QLabel(f"Price: ₱{float(r.get('price') or 0):,.2f}")
            price.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
            price.setStyleSheet("color:#111; border: none;")
            v.addWidget(price)

            desc = QLabel(r.get('description') or "")
            desc.setWordWrap(True)
            desc.setStyleSheet("color:#111; border: none;")
            v.addWidget(desc)
            v.addStretch(1)

            btn = QPushButton("Book Now")
            btn.setIcon(QIcon("icons/book.png"))  # Add icon
            btn.setStyleSheet("""
                QPushButton { background:#02afd2; color:white; border-radius:8px; padding:8px; font-weight:bold; }
                QPushButton:hover { background:#0177c2; }
            """)
            btn.clicked.connect(partial(self.on_service_book, r))
            v.addWidget(btn)

            self.services_grid.addWidget(card, idx // 3, idx % 3)

    def filter_services(self, text):
        self.populate_services(text.strip())

    def on_service_book(self, service_row):
        dlg = BookingDialog(self.patient_id, service=service_row, parent=self)
        if dlg.exec():
            self.switch_section("my_appointments")

    def show_transaction(self):
        trans_card = QFrame()
        trans_card.setStyleSheet("QFrame { background:white; border-radius:10px; border:1px solid #d8eafd; }")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 50))
        trans_card.setGraphicsEffect(shadow)
        layout = QVBoxLayout(trans_card)
        layout.setContentsMargins(22, 18, 22, 18)
        header = QLabel("Transactions")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.setStyleSheet("border: none;")
        layout.addWidget(header)

        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(["Service", "Date Paid", "Amount", "Action"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setMinimumHeight(420)

        db = DB()
        try:
            rows = db.query("""
                            SELECT s.name as service, t.paid_at as paid, t.amount, t.id
                            FROM transactions t
                            JOIN services s ON t.service_id = s.id
                            WHERE t.patient_id = %s
                            ORDER BY t.paid_at DESC
                            """, (self.patient_id,))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load transactions: {e}")
            db.close()
            return
        finally:
            db.close()

        table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            table.setItem(i, 0, QTableWidgetItem(r['service']))
            table.setItem(i, 1, QTableWidgetItem(str(r['paid'])))
            amt_item = QTableWidgetItem(f"₱{float(r['amount']):,.2f}")
            amt_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(i, 2, amt_item)
            receipt_btn = QPushButton("Print Receipt")
            receipt_btn.setIcon(QIcon("icons/print.png"))  # Add icon
            receipt_btn.setStyleSheet("""
                QPushButton { background: #4caf50; color: white; border-radius: 6px; padding: 6px; font-weight: bold; }
                QPushButton:hover { background: #388e3c; }
            """)
            receipt_btn.clicked.connect(partial(self.generate_receipt, r))
            table.setCellWidget(i, 3, receipt_btn)

        table.setStyleSheet("""
            QTableWidget { background: white; border: 1px solid #e6eefc; }
            QHeaderView::section { background:#f7fdff; color: black; font-weight: bold; border: none; }
        """)
        layout.addWidget(table)
        self.content_layout.addWidget(trans_card)

    def generate_receipt(self, transaction):
        filename = f"receipt_{transaction['id']}.pdf"
        try:
            c = canvas.Canvas(filename, pagesize=letter)
            width, height = letter
            c.drawString(inch, height - inch, "PureDent Clinic Receipt")
            c.drawString(inch, height - 1.5 * inch, f"Transaction ID: {transaction['id']}")
            c.drawString(inch, height - 2 * inch, f"Service: {transaction['service']}")
            c.drawString(inch, height - 2.5 * inch, f"Date Paid: {transaction['paid']}")
            c.drawString(inch, height - 3 * inch, f"Amount: ₱{float(transaction['amount']):,.2f}")
            c.drawString(inch, height - 3.5 * inch, f"Patient: {self.patient_name}")
            c.save()
            os.startfile(filename)
            QMessageBox.information(self, "Receipt Generated", f"Receipt saved as {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate receipt: {e}")

    def get_next_appointment(self):
        db = DB()
        try:
            res = db.query("""
                           SELECT a.date, a.time, s.name as service
                           FROM appointments a
                           JOIN services s ON a.service_id = s.id
                           WHERE a.patient_id = %s
                           AND a.date >= CURDATE()
                           ORDER BY a.date ASC, a.time ASC LIMIT 1
                           """, (self.patient_id,))
            if res:
                r = res[0]
                when = f"{r['date']} {str(r['time'])}"
                return {"when": when, "service": r.get("service")}
            return None
        except Exception as e:
            print(f"Error fetching next appointment: {e}")
            return None
        finally:
            db.close()

    def get_confirmed_count(self):
        db = DB()
        try:
            res = db.query("SELECT COUNT(*) as count FROM appointments WHERE patient_id=%s AND status='Confirmed'",
                           (self.patient_id,))
            return res[0]['count'] if res else 0
        except Exception as e:
            print(f"Error fetching confirmed count: {e}")
            return 0
        finally:
            db.close()

    def get_recent_completed(self, limit=6):
        db = DB()
        try:
            rows = db.query("""
                            SELECT s.name as service, a.date, a.time
                            FROM appointments a
                            JOIN services s ON a.service_id = s.id
                            WHERE a.patient_id = %s
                            AND a.status = 'Completed'
                            ORDER BY a.date DESC, a.time DESC
                            LIMIT %s
                            """, (self.patient_id, limit))
            return rows
        except Exception as e:
            print(f"Error fetching recent completed: {e}")
            return []
        finally:
            db.close()

    def logout(self):
        if self.portal_parent:
            self.portal_parent.show()
        self.close()