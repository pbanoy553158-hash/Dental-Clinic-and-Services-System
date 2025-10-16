from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QFormLayout,
    QComboBox, QTextEdit, QMessageBox, QDialog, QDateEdit, QApplication,
    QScrollArea,
)
from PyQt6.QtGui import QFont, QColor, QTextDocument
from PyQt6.QtCore import Qt
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from functools import partial
from db import DB, hash_password
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib
matplotlib.use('Agg')  # Avoid backend issues
from datetime import datetime
import base64
from io import BytesIO

# ----------------------------------------------------------------------
# Utility helpers
# ----------------------------------------------------------------------
def format_currency(amount):
    """
    Format a numeric amount as Philippine Peso string.
    Example: 1200.5 -> "₱1,200.50"
    """
    try:
        return f"₱{float(amount):,.2f}"
    except Exception:
        return str(amount)

def safe_str(val):
    """Return a safe string for display in table cells."""
    if val is None:
        return ""
    return str(val)

def format_time_12h(time_str):
    """Format time from HH:MM(:SS) to 12-hour with AM/PM."""
    try:
        if time_str:
            dt = datetime.strptime(time_str, "%H:%M:%S") if ':' in time_str and time_str.count(':') == 2 else datetime.strptime(time_str, "%H:%M")
            return dt.strftime("%I:%M %p")
        return ""
    except Exception:
        return safe_str(time_str)

# ----------------------------------------------------------------------
# Chart Helpers
# ----------------------------------------------------------------------
class ChartWidget(QWidget):
    """
    Wrapper for matplotlib chart as a QWidget.
    """
    def __init__(self, fig: Figure, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

# ----------------------------------------------------------------------
# Edit Patient Dialog
# ----------------------------------------------------------------------
class EditPatientDialog(QDialog):
    """
    Modal dialog to edit a patient's record.
    - Allows changing name, age, sex, email, and optionally password.
    - Uses db.DB to persist changes.
    """
    def __init__(self, patient, parent=None):
        super().__init__(parent)
        self.patient = patient
        self.setWindowTitle("Edit Patient Record")
        self.setFixedSize(420, 320)
        layout = QFormLayout(self)

        # Input fields
        self.name_edit = QLineEdit(patient.get("name", ""))
        self.age_edit = QLineEdit(str(patient.get("age") or ""))
        self.sex_edit = QComboBox()
        self.sex_edit.addItems(["Male", "Female", "Other"])
        if patient.get("sex"):
            try:
                self.sex_edit.setCurrentText(patient["sex"])
            except Exception:
                pass
        self.email_edit = QLineEdit(patient.get("email") or "")
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.EchoMode.Password)

        # Layout rows
        layout.addRow("Name:", self.name_edit)
        layout.addRow("Age:", self.age_edit)
        layout.addRow("Sex:", self.sex_edit)
        layout.addRow("Email:", self.email_edit)
        layout.addRow("New Password:", self.pass_edit)

        save_btn = QPushButton("Save")
        save_btn.setStyleSheet("background-color:#02afd2;color:white;padding:8px;border-radius:6px;")
        save_btn.clicked.connect(self.save)
        layout.addRow(save_btn)

    def save(self):
        """
        Persist edited patient data to the database.
        If a new password was provided, hash it before saving.
        """
        db = DB()
        try:
            new_pw = self.pass_edit.text().strip()
            hashed = hash_password(new_pw) if new_pw else self.patient.get("password")
            db.query(
                "UPDATE patients SET name=%s, age=%s, sex=%s, email=%s, password=%s WHERE id=%s",
                (
                    self.name_edit.text(),
                    self.age_edit.text() or None,
                    self.sex_edit.currentText(),
                    self.email_edit.text(),
                    hashed,
                    self.patient["id"],
                ),
                commit=True,
            )
            QMessageBox.information(self, "Saved", "Patient record updated.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save patient: {e}")
        finally:
            db.close()

# ----------------------------------------------------------------------
# Edit Service Dialog
# ----------------------------------------------------------------------
class EditServiceDialog(QDialog):
    """
    Dialog for adding or editing a service.
    - If `service` is None: it's an Add dialog.
    - Otherwise: pre-fills fields and updates existing record.
    """
    def __init__(self, service=None, parent=None):
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("Edit Service" if service else "Add Service")
        self.setFixedSize(420, 300)
        layout = QFormLayout(self)

        self.name_edit = QLineEdit(service["name"] if service else "")
        self.desc_edit = QTextEdit(service["description"] if service else "")
        self.price_edit = QLineEdit(str(service["price"]) if service else "")
        layout.addRow("Name:", self.name_edit)
        layout.addRow("Description:", self.desc_edit)
        layout.addRow("Price:", self.price_edit)

        save_btn = QPushButton("Save")
        save_btn.setStyleSheet("background-color:#02afd2;color:white;padding:8px;border-radius:6px;")
        save_btn.clicked.connect(self.save)
        layout.addRow(save_btn)

    def save(self):
        """
        Validate and insert/update the service record.
        Generates a simple code for new services (based on name).
        """
        try:
            price = float(self.price_edit.text())
        except ValueError:
            QMessageBox.warning(self, "Error", "Price must be numeric.")
            return

        db = DB()
        try:
            if self.service:
                db.query(
                    "UPDATE services SET name=%s, description=%s, price=%s WHERE id=%s",
                    (
                        self.name_edit.text(),
                        self.desc_edit.toPlainText(),
                        price,
                        self.service["id"],
                    ),
                    commit=True,
                )
            else:
                # generate a code, make uppercase and replace spaces
                base_code = self.name_edit.text().strip().upper().replace(" ", "-")[:20]
                # attempt to insert using generated code; if duplicate codes exist, let DB handle unique constraint
                db.query(
                    "INSERT INTO services (code, name, description, price) VALUES (%s,%s,%s,%s)",
                    (base_code, self.name_edit.text(), self.desc_edit.toPlainText(), price),
                    commit=True,
                )
            QMessageBox.information(self, "Saved", "Service saved successfully.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save service: {e}")
        finally:
            db.close()

# ----------------------------------------------------------------------
# Edit Appointment Dialog
# ----------------------------------------------------------------------
class EditAppointmentDialog(QDialog):
    """
    Dialog for editing appointment status and notes.
    When status is changed to 'Completed', a related transaction is auto-inserted
    if it doesn't already exist for that patient/service pair.
    """
    def __init__(self, appointment, parent=None):
        super().__init__(parent)
        self.app = appointment
        self.setWindowTitle("Edit Appointment")
        self.setFixedSize(420, 320)
        layout = QFormLayout(self)

        self.status = QComboBox()
        self.status.addItems(["Pending", "Confirmed", "Completed", "Cancelled"])
        self.status.setCurrentText(self.app.get("status", "Pending"))
        self.notes = QTextEdit(self.app.get("notes") or "")
        layout.addRow("Status:", self.status)
        layout.addRow("Notes:", self.notes)

        save_btn = QPushButton("Save")
        save_btn.setStyleSheet("background-color:#02afd2;color:white;padding:8px;border-radius:6px;")
        save_btn.clicked.connect(self.save)
        layout.addRow(save_btn)

    def save(self):
        db = DB()
        try:
            new_status = self.status.currentText()
            db.query(
                "UPDATE appointments SET status=%s, notes=%s WHERE id=%s",
                (new_status, self.notes.toPlainText(), self.app["id"]),
                commit=True,
            )

            # auto transaction insertion on completed
            if new_status == "Completed":
                # check whether transaction exists for that appointment's patient and service
                existing = db.query(
                    "SELECT id FROM transactions WHERE patient_id=%s AND service_id=%s",
                    (self.app['patient_id'], self.app['service_id'])
                )
                if not existing:
                    price_row = db.query("SELECT price FROM services WHERE id=%s", (self.app['service_id'],))
                    price = price_row[0]['price'] if price_row else 0
                    db.query(
                        "INSERT INTO transactions (patient_id, service_id, amount) VALUES (%s, %s, %s)",
                        (self.app['patient_id'], self.app['service_id'], price),
                        commit=True
                    )
            QMessageBox.information(self, "Updated", "Appointment updated.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update appointment: {e}")
        finally:
            db.close()

# ----------------------------------------------------------------------
# Edit Profile Dialog
# ----------------------------------------------------------------------
class EditProfileDialog(QDialog):
    def __init__(self, staff_id, staff_name, parent=None):
        super().__init__(parent)
        self.staff_id = staff_id
        self.staff_name = staff_name
        self.setWindowTitle("My Profile")
        self.setFixedSize(520, 400)
        layout = QFormLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        db = DB()
        try:
            rows = db.query("SELECT * FROM staff WHERE id=%s", (self.staff_id,))
            self.staff = rows[0] if rows else {}
        finally:
            db.close()

        self.name_edit = QLineEdit(self.staff.get("name") or "")
        self.email_edit = QLineEdit(self.staff.get("email") or "")
        self.phone_edit = QLineEdit(self.staff.get("phone") or "")
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.EchoMode.Password)

        layout.addRow("Full Name:", self.name_edit)
        layout.addRow("Email:", self.email_edit)
        layout.addRow("Phone:", self.phone_edit)
        layout.addRow("New Password:", self.pass_edit)

        save_btn = QPushButton("Save Changes")
        save_btn.setStyleSheet("background-color:#02afd2;color:white;padding:10px;border-radius:6px;")
        save_btn.clicked.connect(self.save_profile)
        layout.addRow(save_btn)

    def save_profile(self):
        new_pw = self.pass_edit.text().strip()
        hashed = hash_password(new_pw) if new_pw else self.staff.get("password")
        db = DB()
        try:
            db.query(
                "UPDATE staff SET name=%s, email=%s, phone=%s, password=%s WHERE id=%s",
                (self.name_edit.text(), self.email_edit.text(), self.phone_edit.text(), hashed, self.staff_id),
                commit=True,
            )
            QMessageBox.information(self, "Saved", "Profile updated successfully.")
            self.staff_name = self.name_edit.text()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save profile: {e}")
        finally:
            db.close()

# ----------------------------------------------------------------------
# Staff Dashboard - Main Widget
# ----------------------------------------------------------------------
class StaffDashboard(QWidget):
    """
    Main staff dashboard window. Contains:
    - Sidebar navigation
    - Content area with sections: Home, Patients, Appointments, Services, Transactions, Reports, Profile
    """
    def __init__(self, staff_id, staff_name, portal_parent=None):
        super().__init__()
        self.staff_id = staff_id
        self.staff_name = staff_name
        self.portal_parent = portal_parent

        # Window properties
        self.setWindowTitle("🦷 PureDent Clinic — Staff Dashboard")
        self.resize(1200, 700)
        self.setMinimumSize(1000, 600)

        # Styling
        self.setStyleSheet("""
            QWidget { background-color: #f7fdff; font-family: Arial, sans-serif; color: #222; }
            QFrame#sidebar { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #02afd2, stop:1 #0298b8); border-right: none; }
            QLabel { background: transparent; }
            QPushButton.nav { text-align:left; padding:10px 14px; border:none; color:white; background:transparent; }
            QPushButton.nav:hover { background:#0298b8; }
            QPushButton.nav:pressed { background:#02afd2; }
            QPushButton.primary { background-color:#02afd2; color:white; padding:8px 12px; border-radius:6px; }
            QTableWidget { 
                background:white; 
                border:1px solid #dfeafc; 
                gridline-color:#eaf4ff; 
                alternate-background-color: #f9fafb;
            }
            QHeaderView::section { background:#e9faff; padding:6px; font-weight:600; border:none; }
            QLineEdit, QTextEdit, QComboBox { background:white; border:1px solid #dfeafc; padding:6px; border-radius:4px; }
            QFrame.card { 
                background:white; 
                border:1px solid #e6eefc; 
                border-radius:8px; 
                box-shadow: 0 2px 6px rgba(0,0,0,0.15);
            }
            QLineEdit.search { max-width: 200px; }
            QTableWidgetItem.status { padding: 4px 10px; border-radius: 4px; }
            QTableWidget::item { padding: 4px; font-size: 10px; }
            QFrame.notification { 
                background:white; 
                border:1px solid #e6eefc; 
                border-radius:6px; 
                padding:8px; 
                margin-bottom:8px;
            }
            QFrame.notification:hover { 
                background:#f0f9ff; 
                border-color:#bfdbfe;
            }
            QLabel.status { 
                padding:4px 8px; 
                border-radius:4px; 
                font-size:10px; 
                color:#333; 
            }
        """)

        # initialize UI and center window
        self.init_ui()
        self.center_window()

    # --------------------------------------------
    # Window utilities
    # --------------------------------------------
    def center_window(self):
        """
        Center the window on the primary screen.
        """
        try:
            screen_geo = QApplication.primaryScreen().availableGeometry().center()
            frame = self.frameGeometry()
            frame.moveCenter(screen_geo)
            self.move(frame.topLeft())
        except Exception:
            # fallback: do nothing if centering fails
            pass

    def print_content(self, section):
        """
        Generate printable HTML for the specified section and open print dialog.
        """
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        document = QTextDocument()
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                h1 {{ color: #02afd2; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #e9faff; }}
                img {{ max-width: 100%; }}
            </style>
        </head>
        <body>
        """

        db = DB()
        try:
            if section == "reports":
                # Service popularity
                pop_rows = db.query("""
                    SELECT s.name, COUNT(*) AS count
                    FROM appointments a JOIN services s ON a.service_id = s.id
                    WHERE a.status = 'Completed'
                    GROUP BY s.id
                    ORDER BY count DESC
                """)
                # Revenue per service
                rev_rows = db.query("""
                    SELECT s.name, SUM(t.amount) AS revenue
                    FROM transactions t JOIN services s ON t.service_id = s.id
                    GROUP BY s.id
                    ORDER BY revenue DESC
                """)

                # Generate pie chart image
                fig1 = Figure(figsize=(6, 4.5))
                ax1 = fig1.add_subplot(111)
                color_palette = [
                    "#0284c7", "#15803d", "#b45309", "#b91c1c",
                    "#1e40af", "#7e22ce", "#0f766e", "#c2410c"
                ]
                pop_names = [r['name'] for r in pop_rows]
                pop_counts = [r['count'] for r in pop_rows]
                if pop_names:
                    ax1.pie(
                        pop_counts,
                        colors=[color_palette[i % len(color_palette)] for i in range(len(pop_names))],
                        startangle=120,
                        autopct=lambda pct: f"{pct:.1f}%" if pct >= 5 else "",
                        textprops={'fontsize': 7, 'color': 'white', 'weight': 'bold'},
                    )
                    ax1.set_aspect("equal")
                else:
                    ax1.text(0.5, 0.5, "No Data", ha="center", va="center", fontsize=9)
                fig1.subplots_adjust(left=0.02, right=0.98, top=0.94, bottom=0.06)
                pie_buffer = BytesIO()
                fig1.savefig(pie_buffer, format='png')
                pie_data = base64.b64encode(pie_buffer.getvalue()).decode('utf-8')
                pie_buffer.close()

                # Generate bar chart image
                fig2 = Figure(figsize=(8, 4))
                ax2 = fig2.add_subplot(111)
                rev_names = [r['name'] for r in rev_rows]
                rev_values = [float(r['revenue'] or 0) for r in rev_rows]
                if rev_names:
                    zipped = sorted(zip(rev_names, rev_values), key=lambda x: x[1], reverse=True)
                    names_sorted, values_sorted = zip(*zipped)
                    bars = ax2.bar(names_sorted, values_sorted, color="#02afd2", edgecolor="#17707c", width=0.55)
                    ax2.set_title("Revenue per Service", fontsize=11, fontweight='bold')
                    ax2.set_ylabel("Revenue (₱)", fontsize=7)
                    ax2.set_xlabel("Service", fontsize=7)
                    ax2.tick_params(axis="x", labelrotation=40, labelsize=6)
                    ax2.tick_params(axis="y", labelsize=6)
                    for bar in bars:
                        h = bar.get_height()
                        ax2.annotate(
                            f"₱{h:,.0f}",
                            xy=(bar.get_x() + bar.get_width() / 2, h),
                            xytext=(0, 2),
                            textcoords="offset points",
                            ha="center", va="bottom",
                            fontsize=6, color="#333"
                        )
                    fig2.subplots_adjust(bottom=0.32, left=0.12, right=0.96, top=0.9)
                else:
                    ax2.text(0.5, 0.5, "No Data", ha="center", va="center", fontsize=9)
                bar_buffer = BytesIO()
                fig2.savefig(bar_buffer, format='png')
                bar_data = base64.b64encode(bar_buffer.getvalue()).decode('utf-8')
                bar_buffer.close()

                html += """
                <h1>Reports</h1>
                <h2>Service Popularity</h2>
                <img src="data:image/png;base64,{}" alt="Service Popularity Pie Chart">
                <table>
                    <tr><th>Service</th><th>Appointments</th></tr>
                """.format(pie_data)
                for row in pop_rows:
                    html += f"<tr><td>{safe_str(row['name'])}</td><td>{safe_str(row['count'])}</td></tr>"
                html += """
                </table>
                <h2>Revenue per Service</h2>
                <img src="data:image/png;base64,{}" alt="Revenue Bar Chart">
                <table>
                    <tr><th>Service</th><th>Revenue (₱)</th></tr>
                """.format(bar_data)
                for row in rev_rows:
                    html += f"<tr><td>{safe_str(row['name'])}</td><td>{format_currency(row['revenue'])}</td></tr>"
                html += "</table>"

            elif section == "transactions":
                rows = db.query("""
                    SELECT t.id, t.paid_at, p.name AS patient, s.name AS service, t.amount
                    FROM transactions t
                    JOIN patients p ON t.patient_id=p.id
                    JOIN services s ON t.service_id=s.id
                    ORDER BY t.paid_at DESC
                """)
                total = sum(float(row.get("amount") or 0) for row in rows)
                html += f"""
                <h1>Transactions</h1>
                <p><strong>Total Revenue:</strong> {format_currency(total)}</p>
                <table>
                    <tr><th>Date</th><th>Patient</th><th>Service</th><th>Amount</th></tr>
                """
                for row in rows:
                    html += f"""
                    <tr>
                        <td>{safe_str(row.get('paid_at', ''))}</td>
                        <td>{safe_str(row.get('patient', ''))}</td>
                        <td>{safe_str(row.get('service', ''))}</td>
                        <td>{format_currency(row.get('amount', 0))}</td>
                    </tr>
                    """
                html += "</table>"

        finally:
            db.close()

        html += "</body></html>"
        document.setHtml(html)
        document.print(printer)

    # --------------------------------------------
    # UI Initialization
    # --------------------------------------------
    def init_ui(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Sidebar (left)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(260)
        s_layout = QVBoxLayout(sidebar)
        s_layout.setContentsMargins(18, 18, 18, 18)
        s_layout.setSpacing(5)

        # Brand label
        brand = QLabel("🦷 PureDent\nClinic")
        brand_font = QFont("Arial", 22, QFont.Weight.Bold)
        brand.setFont(brand_font)
        brand.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        brand.setStyleSheet("""
            color: white;
            background: transparent;
            margin-top: 4px;
            margin-bottom: 2px;
        """)
        s_layout.addWidget(brand, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        # Sub-brand label
        sub = QLabel("Staff Portal")
        sub_font = QFont("Arial", 10, QFont.Weight.DemiBold)
        sub.setFont(sub_font)
        sub.setStyleSheet("""
            color: rgba(255, 255, 255, 0.9);
            background: transparent;
            margin-top: 0px;
        """)
        s_layout.addWidget(sub, alignment=Qt.AlignmentFlag.AlignHCenter)

        s_layout.addSpacing(8)

        # Navigation buttons
        self.nav_buttons = {}
        nav_items = [
            ("Home", "home"),
            ("Patients", "patients"),
            ("Appointments", "appointments"),
            ("Services", "services"),
            ("Transactions", "transactions"),
            ("Reports", "reports"),
            ("Profile", "profile"),
            ("Logout", "logout"),
        ]
        for label, key in nav_items:
            btn = QPushButton(label)
            btn.setProperty("class", "nav")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFont(QFont("Arial", 11))
            btn.clicked.connect(partial(self.switch_section, key))
            btn.setStyleSheet("QPushButton { text-align: left; padding: 10px 12px; border: none; color: white; background: transparent; }")
            s_layout.addWidget(btn)
            self.nav_buttons[key] = btn

        s_layout.addStretch(1)
        # Footer showing logged in staff
        logged_label = QLabel(f"Logged in: {self.staff_name}")
        logged_label.setFont(QFont("Arial", 10))
        logged_label.setStyleSheet("color: rgba(255,255,255,0.95);")
        s_layout.addWidget(logged_label)
        s_layout.addSpacing(4)

        outer.addWidget(sidebar)

        # Main content wrapper (right)
        content_wrapper = QFrame()
        content_layout = QVBoxLayout(content_wrapper)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(12)
        self.content_layout = content_layout
        outer.addWidget(content_wrapper, 1)

        # Open default section
        self.switch_section("home")

    # --------------------------------------------
    # Content management and navigation
    # --------------------------------------------
    def clear_content(self):
        """
        Remove all widgets/layouts from the content area cleanly.
        """
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            else:
                layout = item.layout()
                if layout:
                    while layout.count():
                        sub = layout.takeAt(0)
                        w = sub.widget()
                        if w:
                            w.deleteLater()

    def switch_section(self, section):
        """
        Main navigation handler — switches content based on section key.
        """
        try:
            # Style active nav button and reset others
            for k, btn in self.nav_buttons.items():
                if k == section:
                    btn.setStyleSheet("background:#02afd2; color:white; text-align:left; padding:10px 12px;")
                else:
                    btn.setStyleSheet("QPushButton { text-align:left; padding:10px 12px; background:transparent; color: white; }")

            # Clear content area and render selected section
            self.clear_content()
            match section:
                case "home":
                    self.render_home()
                case "patients":
                    self.render_patients()
                case "appointments":
                    self.render_appointments()
                case "services":
                    self.render_services()
                case "transactions":
                    self.render_transactions()
                case "reports":
                    self.render_reports()
                case "profile":
                    self.render_profile()
                case "logout":
                    self.logout()
                case _:
                    self.render_home()
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Navigation error: {e}")

    # --------------------------------------------
    # Home (Dashboard) section
    # --------------------------------------------
    def render_home(self):
        """
        Dashboard home view.
        Shows summary cards, upcoming appointments (left), and appointment status pie (right).
        """
        # Header row
        top = QHBoxLayout()
        title = QLabel("Dashboard")
        title.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        top.addWidget(title)
        top.addStretch(1)
        welcome = QLabel(f"Hi, Dr. {self.staff_name.split()[0]}")
        welcome.setFont(QFont("Arial", 12))
        top.addWidget(welcome)
        self.content_layout.addLayout(top)

        # Stats cards row
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        stats = [
            ("Total Patients", self.get_count("patients")),
            ("Appointments", self.get_count("appointments")),
            ("Services", self.get_count("services")),
            ("Transactions", self.get_count("transactions")),
        ]
        gradient_colors = [
            "qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #02afd2, stop:1 #5ecbe0)",
            "qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #16a34a, stop:1 #86efac)",
            "qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #fbbf24, stop:1 #fde68a)",
            "qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #ef4444, stop:1 #fca5a5)",
        ]
        for i, (label, value) in enumerate(stats):
            card = QFrame()
            card.setProperty("class", "card")
            card.setFixedHeight(120)
            card.setStyleSheet(
                f"QFrame {{ background: {gradient_colors[i]}; "
                "color: white; border-radius:8px; }}"
            )
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(12, 8, 12, 8)
            lbl = QLabel(label)
            lbl.setFont(QFont("Arial", 14))
            c_layout.addWidget(lbl)
            val_lbl = QLabel(str(value))
            val_lbl.setFont(QFont("Arial", 24, QFont.Weight.Bold))
            c_layout.addStretch(1)
            c_layout.addWidget(val_lbl, alignment=Qt.AlignmentFlag.AlignRight)
            cards_row.addWidget(card)
        self.content_layout.addLayout(cards_row)

        # ---- Upcoming + Pie row ----
        bottom = QHBoxLayout()
        bottom.setSpacing(12)

        # Upcoming appointments (left)
        upcoming_frame = QFrame()
        upcoming_frame.setProperty("class", "card")
        upcoming_frame.setStyleSheet("QFrame.card { background:white; border:1px solid #e6eefc; border-radius:8px; box-shadow: 0 2px 6px rgba(0,0,0,0.15); }")
        upcoming_layout = QVBoxLayout(upcoming_frame)
        upcoming_layout.setContentsMargins(12, 12, 12, 12)
        upcoming_title = QLabel("Upcoming Appointments")
        upcoming_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        upcoming_layout.addWidget(upcoming_title)
        self.populate_upcoming_notifications(upcoming_layout)
        bottom.addWidget(upcoming_frame, 1)

        # Appointment Status Overview (right)
        status_frame = QFrame()
        status_frame.setProperty("class", "card")
        status_layout = QVBoxLayout(status_frame)
        status_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_title = QLabel("Appointment Status Overview")
        status_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        status_layout.addWidget(status_title, alignment=Qt.AlignmentFlag.AlignCenter)
        self.render_appointment_status_pie(status_layout)
        bottom.addWidget(status_frame, 1)

        self.content_layout.addLayout(bottom)
        self.content_layout.addStretch(1)

    def render_appointment_status_pie(self, parent_layout):
        """
        Displays a solid, fully-colored pie chart (right)
        with visible percentages and horizontal color bars (left).
        """
        db = DB()
        try:
            rows = db.query("""
                            SELECT status, COUNT(*) as count
                            FROM appointments
                            GROUP BY status
                            """)
            statuses = [r['status'] for r in rows]
            counts = [r['count'] for r in rows]
        finally:
            db.close()

        # Define consistent order + darker color palette
        order = ["Pending", "Confirmed", "Completed", "Cancelled"]
        color_map = {
            "Pending": "#ca8a04",  # darker yellow
            "Confirmed": "#1e40af",  # darker blue
            "Completed": "#15803d",  # darker green
            "Cancelled": "#b91c1c"   # darker red
        }

        # Sort and filter
        sorted_statuses, sorted_counts, sorted_colors = [], [], []
        for k in order:
            if k in statuses:
                idx = statuses.index(k)
                sorted_statuses.append(k)
                sorted_counts.append(counts[idx])
                sorted_colors.append(color_map[k])

        chart_row = QHBoxLayout()
        chart_row.setSpacing(20)
        chart_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ---------------------- STATUS BARS ----------------------
        left_layout = QVBoxLayout()
        left_layout.setSpacing(8)
        left_layout.setContentsMargins(6, 6, 6, 6)

        if sorted_statuses:
            for status, color in zip(sorted_statuses, sorted_colors):
                bar_container = QHBoxLayout()
                bar_container.setSpacing(6)

                color_bar = QFrame()
                color_bar.setFixedSize(28, 10)
                color_bar.setStyleSheet(f"background-color: {color}; border-radius: 3px;")

                label = QLabel(status)
                label.setFont(QFont("Arial", 9, QFont.Weight.DemiBold))
                label.setStyleSheet("color: #333;")

                bar_container.addWidget(color_bar)
                bar_container.addWidget(label)
                bar_container.addStretch(1)
                left_layout.addLayout(bar_container)
        else:
            lbl = QLabel("No data available")
            lbl.setFont(QFont("Arial", 9))
            left_layout.addWidget(lbl)

        left_layout.addStretch(1)
        chart_row.addLayout(left_layout, 1)

        # ---------------------- PIE CHART ----------------------
        pie_layout = QVBoxLayout()
        pie_layout.setSpacing(6)
        pie_layout.setContentsMargins(0, 0, 0, 0)
        pie_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        fig = Figure(figsize=(8, 8))  # Increased size for larger chart
        ax = fig.add_subplot(111)

        if sorted_statuses:
            wedges, texts, autotexts = ax.pie(
                sorted_counts,
                colors=sorted_colors,
                startangle=120,
                autopct=lambda pct: f"{pct:.1f}%" if pct >= 5 else "",
                textprops={'fontsize': 10, 'color': 'white', 'weight': 'bold'},
                radius=1.2,
                wedgeprops=dict(edgecolor="white", linewidth=1.5)
            )
            ax.set_aspect("equal")
        else:
            ax.text(0.5, 0.5, "No Data",
                    ha="center", va="center", fontsize=12, fontweight="bold")

        fig.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)
        pie_chart_widget = ChartWidget(fig)
        pie_layout.addWidget(pie_chart_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        chart_row.addLayout(pie_layout, 2)

        # Add to parent
        parent_layout.addLayout(chart_row)

    def populate_upcoming_notifications(self, parent_layout):
        """
        Displays upcoming appointments as notification-style cards.
        Shows only Confirmed and Pending statuses with colored badges.
        """
        db = DB()
        try:
            rows_upcoming = db.query(
                "SELECT a.id, p.name as patient, s.name as service, a.date, a.time, a.status "
                "FROM appointments a JOIN patients p ON a.patient_id=p.id "
                "JOIN services s ON a.service_id=s.id "
                "WHERE a.date >= CURDATE() AND a.status IN ('Confirmed', 'Pending') "
                "ORDER BY a.date ASC, a.time ASC LIMIT 10"
            )
        finally:
            db.close()

        # Scroll area for notifications
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(8)

        # Define status colors (same as appointments table)
        status_colors = {
            "Pending": "#ca8a04",
            "Confirmed": "#1e40af",
            "Completed": "#15803d",
            "Cancelled": "#b91c1c"
        }

        if rows_upcoming:
            for r in rows_upcoming:
                card = QFrame()
                card.setProperty("class", "notification")
                card_layout = QHBoxLayout(card)
                card_layout.setContentsMargins(10, 10, 10, 10)
                card_layout.setSpacing(12)

                # Left: Details
                details_layout = QVBoxLayout()
                patient_label = QLabel(f"<b>Patient:</b> {safe_str(r.get('patient'))}")
                patient_label.setFont(QFont("Arial", 10))
                service_label = QLabel(f"<b>Service:</b> {safe_str(r.get('service'))}")
                service_label.setFont(QFont("Arial", 10))
                date_label = QLabel(f"<b>Date:</b> {safe_str(r.get('date'))} {format_time_12h(r.get('time'))}")
                date_label.setFont(QFont("Arial", 10))
                details_layout.addWidget(patient_label)
                details_layout.addWidget(service_label)
                details_layout.addWidget(date_label)
                card_layout.addLayout(details_layout, 1)

                # Right: Status
                status_label = QLabel(safe_str(r.get("status")))
                status_label.setProperty("class", "status")
                status_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                status_color = status_colors.get(r.get("status"), "#ffffff")
                status_label.setStyleSheet(f"QLabel.status {{ background-color: {status_color}; padding:4px 8px; border-radius:4px; color: #fff; }}")
                card_layout.addWidget(status_label)

                scroll_layout.addWidget(card)

        else:
            no_data = QLabel("No upcoming appointments")
            no_data.setFont(QFont("Arial", 10))
            scroll_layout.addWidget(no_data)

        scroll_layout.addStretch(1)
        scroll.setWidget(scroll_content)
        parent_layout.addWidget(scroll)

    # --------------------------------------------
    # Reports section
    # --------------------------------------------
    def render_reports(self):
        """
        Reports section:
        - Left: Legend with colored squares, service names, counts in a straight line
        - Right: Clean full-color pie chart (no inside labels for small segments)
        - Below: Revenue per Service bar chart
        """
        top = QHBoxLayout()
        title = QLabel("Reports")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        top.addWidget(title)
        top.addStretch(1)
        print_btn = QPushButton("Print")
        print_btn.setStyleSheet("background-color:#02afd2;color:white;padding:8px;border-radius:6px;")
        print_btn.clicked.connect(lambda: self.print_content("reports"))
        top.addWidget(print_btn)
        self.content_layout.addLayout(top)

        db = DB()
        try:
            # Service popularity (completed appointments)
            pop_rows = db.query("""
                                SELECT s.name, COUNT(*) AS count
                                FROM appointments a
                                    JOIN services s
                                ON a.service_id = s.id
                                WHERE a.status = 'Completed'
                                GROUP BY s.id
                                ORDER BY count DESC
                                """)
            pop_names = [r['name'] for r in pop_rows]
            pop_counts = [r['count'] for r in pop_rows]

            # Revenue per service (from transactions)
            rev_rows = db.query("""
                                SELECT s.name, SUM(t.amount) AS revenue
                                FROM transactions t
                                         JOIN services s ON t.service_id = s.id
                                GROUP BY s.id
                                ORDER BY revenue DESC
                                """)
            rev_names = [r['name'] for r in rev_rows]
            rev_values = [float(r['revenue'] or 0) for r in rev_rows]
        finally:
            db.close()

        # Outer layout
        report_layout = QVBoxLayout()
        report_layout.setSpacing(18)

        # ---------------- PIE CHART SECTION ----------------
        pie_card = QFrame()
        pie_card.setProperty("class", "card")
        pie_layout = QHBoxLayout(pie_card)
        pie_layout.setContentsMargins(10, 10, 10, 10)
        pie_layout.setSpacing(14)

        color_palette = [
            "#0284c7", "#15803d", "#b45309", "#b91c1c",
            "#1e40af", "#7e22ce", "#0f766e", "#c2410c"
        ]

        # Left legend
        legend_box = QVBoxLayout()
        legend_box.setSpacing(5)
        legend_label = QLabel("Service Popularity")
        legend_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        legend_box.addWidget(legend_label)

        if pop_names:
            total = sum(pop_counts)
            for i, (name, count) in enumerate(zip(pop_names, pop_counts)):
                color = color_palette[i % len(color_palette)]

                row = QHBoxLayout()
                row.setSpacing(8)

                # Color square
                square = QFrame()
                square.setFixedSize(14, 14)
                square.setStyleSheet(f"background-color:{color}; border-radius:3px;")

                # Name label
                lbl_name = QLabel(name)
                lbl_name.setFont(QFont("Arial", 9))

                # Count label
                lbl_value = QLabel(f"{count}")
                lbl_value.setFont(QFont("Arial", 9))
                lbl_value.setStyleSheet("color:#555;")

                row.addWidget(square)
                row.addWidget(lbl_name)
                row.addStretch(1)
                row.addWidget(lbl_value)
                legend_box.addLayout(row)
        else:
            no_lbl = QLabel("No data available")
            no_lbl.setFont(QFont("Arial", 9))
            legend_box.addWidget(no_lbl)

        legend_box.addStretch(1)
        pie_layout.addLayout(legend_box, 1)

        # Right pie chart
        fig1 = Figure(figsize=(6, 4.5))
        ax1 = fig1.add_subplot(111)

        if pop_names:
            ax1.pie(
                pop_counts,
                colors=[color_palette[i % len(color_palette)] for i in range(len(pop_names))],
                startangle=120,
                autopct=lambda pct: f"{pct:.1f}%" if pct >= 5 else "",
                textprops={'fontsize': 7, 'color': 'white', 'weight': 'bold'},
                wedgeprops=dict(edgecolor="white", width=1.0)
            )
            ax1.set_aspect("equal", adjustable="datalim")
        else:
            ax1.text(0.5, 0.5, "No Data", ha="center", va="center", fontsize=9)

        fig1.subplots_adjust(left=0.02, right=0.98, top=0.94, bottom=0.06)
        pie_layout.addWidget(ChartWidget(fig1), 2)
        report_layout.addWidget(pie_card, 1)

        # ---------------- BAR CHART SECTION ----------------
        bar_card = QFrame()
        bar_card.setProperty("class", "card")
        bar_layout = QVBoxLayout(bar_card)
        bar_layout.setContentsMargins(12, 12, 12, 12)
        bar_layout.setSpacing(6)

        fig2 = Figure(figsize=(8, 4))
        ax2 = fig2.add_subplot(111)

        if rev_names:
            zipped = sorted(zip(rev_names, rev_values), key=lambda x: x[1], reverse=True)
            names_sorted, values_sorted = zip(*zipped)
            bars = ax2.bar(
                names_sorted,
                values_sorted,
                color="#02afd2",
                edgecolor="#17707c",
                width=0.55
            )

            ax2.set_title("Revenue per Service", fontsize=11, fontweight='bold', pad=8)
            ax2.set_ylabel("Revenue (₱)", fontsize=7)
            ax2.set_xlabel("Service", fontsize=7)
            ax2.tick_params(axis="x", labelrotation=40, labelsize=6)
            ax2.tick_params(axis="y", labelsize=6)

            # Labels above bars
            for bar in bars:
                h = bar.get_height()
                ax2.annotate(
                    f"₱{h:,.0f}",
                    xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 2),
                    textcoords="offset points",
                    ha="center", va="bottom",
                    fontsize=6, color="#333"
                )

            fig2.subplots_adjust(bottom=0.32, left=0.12, right=0.96, top=0.9)
        else:
            ax2.text(0.5, 0.5, "No Data", ha="center", va="center", fontsize=9)

        fig2.tight_layout()
        bar_layout.addWidget(ChartWidget(fig2))
        report_layout.addWidget(bar_card, 2)

        self.content_layout.addLayout(report_layout)
        self.content_layout.addStretch(1)

    # --------------------------------------------
    # Patients section
    # --------------------------------------------
    def render_patients(self):
        title = QLabel("Patients")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        self.content_layout.addWidget(title)

        # Search bar with add button, aligned to the right
        search_layout = QHBoxLayout()
        search_layout.addStretch(1)
        self.patient_search = QLineEdit()
        self.patient_search.setPlaceholderText("Search patients...")
        self.patient_search.setProperty("class", "search")
        self.patient_search.textChanged.connect(self.filter_patients)
        search_layout.addWidget(QLabel("🔍"))
        search_layout.addWidget(self.patient_search)
        add_btn = QPushButton("Add Patient")
        add_btn.setStyleSheet("background-color:#02afd2;color:white;padding:8px;border-radius:6px;")
        search_layout.addWidget(add_btn)
        self.content_layout.addLayout(search_layout)

        table = QTableWidget(0, 6)
        table.setHorizontalHeaderLabels(["ID", "Name", "Age", "Sex", "Email", "Actions"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(5, 60)
        table.setColumnHidden(0, True)
        table.setStyleSheet("QTableWidget { background:white; border:1px solid #dfeafc; }")
        self.content_layout.addWidget(table)
        self.table_patients_ref = table

        def load():
            db = DB()
            try:
                rows = db.query("SELECT * FROM patients ORDER BY id DESC")
            finally:
                db.close()
            table.setRowCount(len(rows))
            for i, r in enumerate(rows):
                table.setItem(i, 0, QTableWidgetItem(safe_str(r.get("id", ""))))
                table.setItem(i, 1, QTableWidgetItem(safe_str(r.get("name", ""))))
                table.setItem(i, 2, QTableWidgetItem(safe_str(r.get("age") or "")))
                table.setItem(i, 3, QTableWidgetItem(safe_str(r.get("sex") or "")))
                table.setItem(i, 4, QTableWidgetItem(safe_str(r.get("email") or "")))

                edit_btn = QPushButton("✏️")
                edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                edit_btn.clicked.connect(partial(self.open_edit_patient, r))
                del_btn = QPushButton("🗑")
                del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                del_btn.clicked.connect(partial(self.delete_patient, r.get("id")))
                holder_layout = QHBoxLayout()
                holder_layout.setContentsMargins(0, 0, 0, 0)
                holder_layout.setSpacing(6)
                holder_layout.addWidget(edit_btn)
                holder_layout.addWidget(del_btn)
                holder = QFrame()
                holder.setLayout(holder_layout)
                table.setCellWidget(i, 5, holder)

        load()

        def on_add():
            dlg = QDialog(self)
            dlg.setWindowTitle("Add Patient")
            dlg.setFixedSize(420, 320)
            form = QFormLayout(dlg)
            n, a, s, e, p = QLineEdit(), QLineEdit(), QComboBox(), QLineEdit(), QLineEdit()
            s.addItems(["Male", "Female", "Other"])
            p.setEchoMode(QLineEdit.EchoMode.Password)
            form.addRow("Name:", n)
            form.addRow("Age:", a)
            form.addRow("Sex:", s)
            form.addRow("Email:", e)
            form.addRow("Password:", p)
            btn = QPushButton("Save")
            btn.setStyleSheet("background-color:#02afd2;color:white;padding:8px;border-radius:6px;")
            form.addRow(btn)

            def save():
                db = DB()
                try:
                    db.query(
                        "INSERT INTO patients (name, age, sex, email, password) VALUES (%s,%s,%s,%s,%s)",
                        (n.text(), a.text() or None, s.currentText(), e.text(), hash_password(p.text())),
                        commit=True,
                    )
                    dlg.accept()
                    load()
                except Exception as ex:
                    QMessageBox.critical(self, "Error", f"Failed to add patient: {ex}")
                finally:
                    db.close()

            btn.clicked.connect(save)
            dlg.exec()

        add_btn.clicked.connect(on_add)

    def filter_patients(self):
        """
        Filter visible rows in the patients table based on search query.
        Excludes the actions column from search matching.
        """
        query = self.patient_search.text().lower()
        table = getattr(self, "table_patients_ref", None)
        if table is None:
            return
        for row in range(table.rowCount()):
            match = False
            for col in range(1, table.columnCount() - 1):
                item = table.item(row, col)
                if item and query in item.text().lower():
                    match = True
                    break
            table.setRowHidden(row, not match)

    def open_edit_patient(self, patient_row):
        """
        Open the EditPatientDialog. After dialog closes, refresh patients section.
        """
        dlg = EditPatientDialog(patient_row, self)
        dlg.exec()
        self.switch_section("patients")

    def delete_patient(self, pid):
        """
        Delete a patient after confirmation.
        """
        if pid is None:
            return
        ok = QMessageBox.question(self, "Confirm", "Delete this patient?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ok == QMessageBox.StandardButton.Yes:
            db = DB()
            try:
                db.query("DELETE FROM patients WHERE id=%s", (pid,), commit=True)
                QMessageBox.information(self, "Deleted", "Patient deleted.")
                self.switch_section("patients")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete patient: {e}")
            finally:
                db.close()

    # --------------------------------------------
    # Appointments section
    # --------------------------------------------
    def render_appointments(self):
        title = QLabel("Appointments")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        self.content_layout.addWidget(title)

        # Search bar with add button, aligned to the right
        search_layout = QHBoxLayout()
        search_layout.addStretch(1)
        self.appointment_search = QLineEdit()
        self.appointment_search.setPlaceholderText("Search appointments...")
        self.appointment_search.setProperty("class", "search")
        self.appointment_search.textChanged.connect(self.filter_appointments)
        search_layout.addWidget(QLabel("🔍"))
        search_layout.addWidget(self.appointment_search)
        add_btn = QPushButton("Add Appointment")
        add_btn.setStyleSheet("background-color:#02afd2;color:white;padding:8px;border-radius:6px;")
        search_layout.addWidget(add_btn)
        self.content_layout.addLayout(search_layout)

        table = QTableWidget(0, 8)
        table.setHorizontalHeaderLabels(["ID", "Patient", "Service", "Date", "Time", "Notes", "Status", "Actions"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(7, 60)
        table.setColumnHidden(0, True)
        table.setStyleSheet("QTableWidget { background:white; border:1px solid #dfeafc; }")
        self.content_layout.addWidget(table)
        self.table_appointments_ref = table

        def load():
            db = DB()
            try:
                rows = db.query(
                    "SELECT a.*, p.name AS patient, s.name AS service FROM appointments a "
                    "JOIN patients p ON a.patient_id=p.id JOIN services s ON a.service_id=s.id ORDER BY a.date DESC, a.time DESC"
                )
            finally:
                db.close()
            table.setRowCount(len(rows))

            status_colors = {
                "Pending": "#ca8a04",
                "Confirmed": "#1e40af",
                "Completed": "#15803d",
                "Cancelled": "#b91c1c"
            }

            for i, r in enumerate(rows):
                table.setItem(i, 0, QTableWidgetItem(safe_str(r.get("id", ""))))
                table.setItem(i, 1, QTableWidgetItem(safe_str(r.get("patient") or "")))
                table.setItem(i, 2, QTableWidgetItem(safe_str(r.get("service") or "")))
                table.setItem(i, 3, QTableWidgetItem(safe_str(r.get("date") or "")))
                time_item = QTableWidgetItem(format_time_12h(r.get("time")))
                table.setItem(i, 4, time_item)
                table.setItem(i, 5, QTableWidgetItem(safe_str(r.get("notes") or "")))
                status_item = QTableWidgetItem(safe_str(r.get("status") or ""))
                status_item.setFont(QFont("Arial", 9))
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                status_color = status_colors.get(r.get("status"), "#ffffff")
                status_item.setBackground(QColor(status_color))
                table.setItem(i, 6, status_item)

                edit_btn = QPushButton("✏️")
                edit_btn.clicked.connect(partial(self.open_edit_appointment, r))
                del_btn = QPushButton("🗑")
                del_btn.clicked.connect(partial(self.delete_appointment, r.get("id")))
                for b in (edit_btn, del_btn):
                    b.setCursor(Qt.CursorShape.PointingHandCursor)
                holder = QFrame()
                holder_layout = QHBoxLayout(holder)
                holder_layout.setContentsMargins(0, 0, 0, 0)
                holder_layout.setSpacing(6)
                holder_layout.addWidget(edit_btn)
                holder_layout.addWidget(del_btn)
                table.setCellWidget(i, 7, holder)

        load()

        def on_add():
            dlg = QDialog(self)
            dlg.setWindowTitle("Add Appointment")
            dlg.setFixedSize(480, 360)
            form = QFormLayout(dlg)
            db = DB()
            try:
                patients = db.query("SELECT id, name FROM patients")
                services = db.query("SELECT id, name FROM services")
            finally:
                db.close()
            patient_cb = QComboBox()
            service_cb = QComboBox()
            for p in patients:
                patient_cb.addItem(f"{p['name']} (#{p['id']})", p['id'])
            for s in services:
                service_cb.addItem(f"{s['name']} (#{s['id']})", s['id'])
            date_edit = QDateEdit()
            date_edit.setCalendarPopup(True)
            time_edit = QLineEdit()
            notes = QTextEdit()
            form.addRow("Patient:", patient_cb)
            form.addRow("Service:", service_cb)
            form.addRow("Date:", date_edit)
            form.addRow("Time (HH:MM):", time_edit)
            form.addRow("Notes:", notes)
            btn = QPushButton("Save")
            btn.setStyleSheet("background-color:#02afd2;color:white;padding:8px;border-radius:6px;")
            form.addRow(btn)

            def save():
                pid = patient_cb.currentData()
                sid = service_cb.currentData()
                dt = date_edit.date().toString("yyyy-MM-dd")
                tm = time_edit.text().strip()
                db = DB()
                try:
                    db.query(
                        "INSERT INTO appointments (patient_id, service_id, date, time, notes) VALUES (%s,%s,%s,%s,%s)",
                        (pid, sid, dt, tm, notes.toPlainText()), commit=True
                    )
                    dlg.accept()
                    load()
                except Exception as ex:
                    QMessageBox.critical(self, "Error", f"Failed to add appointment: {ex}")
                finally:
                    db.close()

            btn.clicked.connect(save)
            dlg.exec()

        add_btn.clicked.connect(on_add)

    def filter_appointments(self):
        """
        Filter rows in the appointments table based on search query.
        Excludes actions column from matching.
        """
        query = self.appointment_search.text().lower()
        table = getattr(self, "table_appointments_ref", None)
        if table is None:
            return
        for row in range(table.rowCount()):
            match = False
            for col in range(1, table.columnCount() - 1):
                item = table.item(row, col)
                if item and query in item.text().lower():
                    match = True
                    break
            table.setRowHidden(row, not match)

    def open_edit_appointment(self, appt_row):
        """
        Open the EditAppointmentDialog and refresh appointments
        after the dialog is closed.
        """
        dlg = EditAppointmentDialog(appt_row, self)
        dlg.exec()
        self.switch_section("appointments")

    def delete_appointment(self, aid):
        """
        Delete appointment after confirmation.
        """
        if aid is None:
            return
        ok = QMessageBox.question(self, "Confirm", "Delete this appointment?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ok == QMessageBox.StandardButton.Yes:
            db = DB()
            try:
                db.query("DELETE FROM appointments WHERE id=%s", (aid,), commit=True)
                QMessageBox.information(self, "Deleted", "Appointment deleted.")
                self.switch_section("appointments")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete appointment: {e}")
            finally:
                db.close()

    # --------------------------------------------
    # Services section
    # --------------------------------------------
    def render_services(self):
        title = QLabel("Services")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        self.content_layout.addWidget(title)

        # Search bar with add button, aligned to the right
        search_layout = QHBoxLayout()
        search_layout.addStretch(1)
        self.service_search = QLineEdit()
        self.service_search.setPlaceholderText("Search services...")
        self.service_search.setProperty("class", "search")
        self.service_search.textChanged.connect(self.filter_services)
        search_layout.addWidget(QLabel("🔍"))
        search_layout.addWidget(self.service_search)
        add_btn = QPushButton("Add Service")
        add_btn.setStyleSheet("background-color:#02afd2;color:white;padding:8px;border-radius:6px;")
        search_layout.addWidget(add_btn)
        self.content_layout.addLayout(search_layout)

        table = QTableWidget(0, 6)
        table.setHorizontalHeaderLabels(["ID", "Code", "Name", "Description", "Price", "Actions"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(5, 60)
        table.setColumnHidden(0, True)
        table.setStyleSheet("QTableWidget { background:white; border:1px solid #dfeafc; }")
        self.content_layout.addWidget(table)
        self.table_services_ref = table

        def load():
            db = DB()
            try:
                rows = db.query("SELECT id, code, name, description, price FROM services ORDER BY id DESC")
            finally:
                db.close()
            table.setRowCount(len(rows))
            for i, r in enumerate(rows):
                table.setItem(i, 0, QTableWidgetItem(safe_str(r.get("id", ""))))
                table.setItem(i, 1, QTableWidgetItem(safe_str(r.get("code") or "")))
                table.setItem(i, 2, QTableWidgetItem(safe_str(r.get("name") or "")))
                table.setItem(i, 3, QTableWidgetItem(safe_str(r.get("description") or "")))
                price_val = format_currency(r.get("price", 0))
                table.setItem(i, 4, QTableWidgetItem(price_val))

                edit_btn = QPushButton("✏️")
                edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                edit_btn.clicked.connect(partial(self.open_edit_service, r))
                del_btn = QPushButton("🗑")
                del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                del_btn.clicked.connect(partial(self.delete_service, r.get("id")))
                holder_layout = QHBoxLayout()
                holder_layout.setContentsMargins(0, 0, 0, 0)
                holder_layout.setSpacing(6)
                holder_layout.addWidget(edit_btn)
                holder_layout.addWidget(del_btn)
                holder = QFrame()
                holder.setLayout(holder_layout)
                table.setCellWidget(i, 5, holder)

        load()

        def on_add():
            dlg = EditServiceDialog(parent=self)
            dlg.exec()
            load()

        add_btn.clicked.connect(on_add)

    def filter_services(self):
        """
        Filter rows in the services table based on search query.
        Excludes actions column from matching.
        """
        query = self.service_search.text().lower()
        table = getattr(self, "table_services_ref", None)
        if table is None:
            return
        for row in range(table.rowCount()):
            match = False
            for col in range(1, table.columnCount() - 1):
                item = table.item(row, col)
                if item and query in item.text().lower():
                    match = True
                    break
            table.setRowHidden(row, not match)

    def open_edit_service(self, svc):
        dlg = EditServiceDialog(svc, self)
        dlg.exec()
        self.switch_section("services")

    def delete_service(self, sid):
        if sid is None:
            return
        ok = QMessageBox.question(self, "Confirm", "Delete this service?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ok == QMessageBox.StandardButton.Yes:
            db = DB()
            try:
                db.query("DELETE FROM services WHERE id=%s", (sid,), commit=True)
                QMessageBox.information(self, "Deleted", "Service deleted.")
                self.switch_section("services")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete service: {e}")
            finally:
                db.close()

    # --------------------------------------------
    # Transactions section
    # --------------------------------------------
    def render_transactions(self):
        top = QHBoxLayout()
        title = QLabel("Transactions")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        top.addWidget(title)
        top.addStretch(1)
        self.content_layout.addLayout(top)

        db = DB()
        try:
            rows = db.query("""
                SELECT t.id, t.paid_at, p.name AS patient, s.name AS service, t.amount
                FROM transactions t
                JOIN patients p ON t.patient_id=p.id
                JOIN services s ON t.service_id=s.id
                ORDER BY t.paid_at DESC
            """)
        finally:
            db.close()

        # Sub-top layout for total revenue and print button below title
        sub_top = QHBoxLayout()
        sub_top.addStretch(1)
        total = 0.0
        for r in rows:
            amt = float(r.get("amount") or 0)
            total += amt
        total_lbl = QLabel(f"💰 Total Revenue: {format_currency(total)}")
        total_lbl.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        sub_top.addWidget(total_lbl)
        print_btn = QPushButton("Print")
        print_btn.setStyleSheet("background-color:#02afd2;color:white;padding:8px;border-radius:6px;")
        print_btn.clicked.connect(lambda: self.print_content("transactions"))
        sub_top.addWidget(print_btn)
        self.content_layout.addLayout(sub_top)

        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(["ID", "Date", "Patient", "Service", "Amount"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setColumnHidden(0, True)
        table.setStyleSheet("QTableWidget { background:white; border:1px solid #dfeafc; }")
        self.content_layout.addWidget(table)
        self.table_transactions_ref = table

        def load():
            table.setRowCount(len(rows))
            for i, r in enumerate(rows):
                table.setItem(i, 0, QTableWidgetItem(safe_str(r.get("id", ""))))
                table.setItem(i, 1, QTableWidgetItem(safe_str(r.get("paid_at", ""))))
                table.setItem(i, 2, QTableWidgetItem(safe_str(r.get("patient", ""))))
                table.setItem(i, 3, QTableWidgetItem(safe_str(r.get("service", ""))))
                amt = float(r.get("amount") or 0)
                table.setItem(i, 4, QTableWidgetItem(format_currency(amt)))

        load()

    def filter_transactions(self):
        """
        Filter rows in the transactions table based on search query.
        """
        query = getattr(self, "transaction_search", None)
        if query is None:
            return
        query_text = query.text().lower()
        table = getattr(self, "table_transactions_ref", None)
        if table is None:
            return
        for row in range(table.rowCount()):
            match = False
            for col in range(1, table.columnCount()):
                item = table.item(row, col)
                if item and query_text in item.text().lower():
                    match = True
                    break
            table.setRowHidden(row, not match)

    # --------------------------------------------
    # Profile section
    # --------------------------------------------
    def render_profile(self):
        dlg = EditProfileDialog(self.staff_id, self.staff_name, self)
        dlg.exec()

    # --------------------------------------------
    # Utilities
    # --------------------------------------------
    def get_count(self, table):
        db = DB()
        try:
            res = db.query(f"SELECT COUNT(*) AS count FROM {table}")
        finally:
            db.close()
        if res and isinstance(res, list) and len(res) > 0:
            return res[0].get("count") or 0
        return 0

    def logout(self):
        if self.portal_parent:
            self.portal_parent.show()
        self.close()