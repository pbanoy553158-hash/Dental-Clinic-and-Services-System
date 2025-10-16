# ------------------ LIBRARY IMPORTS ------------------
from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QApplication, QGraphicsDropShadowEffect, QMessageBox, QComboBox
)
from PyQt6.QtGui import QFont, QColor, QIntValidator
from PyQt6.QtCore import Qt
import logging

from db import DB, check_password, hash_password

from ui.staff_dashboard import StaffDashboard
from ui.patient_dashboard import PatientDashboard
logging.basicConfig(level=logging.DEBUG, filename='app.log', format='%(asctime)s - %(levelname)s - %(message)s')

class ClinicPortal(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PureDent Clinic Portal")
        self.setFixedSize(600, 680)
        self.center_window()
        self.setup_ui()

    def center_window(self):
        screen = QApplication.primaryScreen().availableGeometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2
        )

    # ------------------------------------------------------
    # Method: setup_ui()
    def setup_ui(self):
        self.setStyleSheet("background-color: #e6f0f5;")

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # ---------------- LEFT PANEL ----------------
        self.left_panel = QFrame()
        self.left_panel.setFixedWidth(200)
        self.left_panel.setStyleSheet("""
            QFrame {
                background-color: qlineargradient(
                    x1:0, y1:0, x1:0, y1:0,
                    stop:0 #0288d1, stop:1 #01579b
                );
                border-top-left-radius: 25px;
                border-bottom-left-radius: 25px;
            }
        """)

        # Left side branding (logo and clinic name)
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        left_layout.setContentsMargins(20, 20, 20, 20)

        logo = QLabel("🦷")
        logo.setFont(QFont("Segoe UI Emoji", 80))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet("color: white; margin-bottom: 15px;")
        left_layout.addWidget(logo)

        clinic_name = QLabel("PureDent")
        clinic_name.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        clinic_name.setStyleSheet("color: white;")
        clinic_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(clinic_name)

        sub = QLabel("Clinic Portal")
        sub.setFont(QFont("Segoe UI", 16))
        sub.setStyleSheet("color: rgba(255, 255, 255, 0.8); margin-top: -5px;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(sub)

        left_layout.addStretch()
        self.main_layout.addWidget(self.left_panel)

        # ---------------- RIGHT PANEL ----------------
        self.right_panel = QFrame()
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(50, 60, 50, 50)  # Increased margins
        right_layout.setSpacing(20)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create all cards
        self.login_card = self.create_login_card()
        self.register_step1 = self.create_register_step1()
        self.register_step2 = self.create_register_step2()
        self.success_card = self.create_success_card()

        # Show login by default
        for c in [self.register_step1, self.register_step2, self.success_card]:
            c.setVisible(False)

        right_layout.addWidget(self.login_card)
        right_layout.addWidget(self.register_step1)
        right_layout.addWidget(self.register_step2)
        right_layout.addWidget(self.success_card)
        self.main_layout.addWidget(self.right_panel)

    # LOGIN CARD
    # Displays email/password fields and login buttons
    # ------------------------------------------------------
    def create_login_card(self):
        card = self.create_card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(18)

        title = QLabel("Welcome Back")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title.setStyleSheet("color: #01579b;")  # Darker blue for title
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Sign in to access your account")
        subtitle.setFont(QFont("Segoe UI", 12))
        subtitle.setStyleSheet("color: #37474f;")  # Softer gray
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(10)

        # --- Email Field ---
        layout.addWidget(self.create_label("Email"))
        self.login_email = self.create_input("Enter your email")
        layout.addWidget(self.login_email)

        # --- Password Field ---
        layout.addWidget(self.create_label("Password"))
        self.login_password = self.create_input("Enter your password", password=True)
        layout.addWidget(self.login_password)

        # --- Buttons ---
        self.login_btn = QPushButton("Sign In")
        self.login_btn.setMinimumHeight(45)
        self.login_btn.setStyleSheet(self.button_style("#0288d1", "#01579b"))
        self.login_btn.clicked.connect(self.login_action)
        layout.addWidget(self.login_btn)

        self.goto_register_btn = QPushButton("Create Account")
        self.goto_register_btn.setMinimumHeight(45)
        self.goto_register_btn.setStyleSheet(self.button_style("#4fc3f7", "#0288d1"))
        self.goto_register_btn.clicked.connect(self.show_register_step1)
        layout.addWidget(self.goto_register_btn)

        return card

    # REGISTRATION STEP 1
    # Collects personal details (Name, Age, Sex, Email)
    # ------------------------------------------------------
    def create_register_step1(self):
        card = self.create_card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        title = QLabel("Create Account")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title.setStyleSheet("color: #01579b;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Personal Details")
        subtitle.setFont(QFont("Segoe UI", 12))
        subtitle.setStyleSheet("color: #37474f;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # --- Full Name Field ---
        layout.addWidget(self.create_label("Full Name"))
        self.reg_name = self.create_input("Enter your full name")
        layout.addWidget(self.reg_name)

        # --- Age and Sex Fields (side by side) ---
        row = QHBoxLayout()
        row.setSpacing(15)

        # AGE FIELD
        age_layout = QVBoxLayout()
        age_layout.addWidget(self.create_label("Age"))
        self.reg_age = self.create_input("Enter age")
        self.reg_age.setFixedWidth(120)
        self.reg_age.setMaxLength(3)
        self.reg_age.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.reg_age.setValidator(QIntValidator(1, 120))
        age_layout.addWidget(self.reg_age)
        row.addLayout(age_layout)

        # SEX DROPDOWN
        sex_layout = QVBoxLayout()
        sex_layout.addWidget(self.create_label("Sex"))
        self.reg_sex = QComboBox()
        self.reg_sex.addItems(["Male", "Female", "Other"])
        self.reg_sex.setFixedWidth(120)
        self.reg_sex.setStyleSheet("""
            QComboBox {
                background-color: #ffffff;
                border: 1px solid #bbdefb;
                border-radius: 10px;
                min-height: 40px;
                padding-left: 12px;
                color: #263238;
                font-size: 12pt;
                transition: all 0.2s ease;
            }
            QComboBox QAbstractItemView {
                background-color: black;
                selection-background-color: #4fc3f7;
                selection-color: #ffffff;
                border: none;
            }
            QComboBox:focus, QComboBox::drop-down {
                border: 2px solid #0288d1;
                background-color: #e3f2fd;
            }
        """)
        sex_layout.addWidget(self.reg_sex)
        row.addLayout(sex_layout)
        layout.addLayout(row)

        # --- Email Field ---
        layout.addWidget(self.create_label("Email"))
        self.reg_email = self.create_input("Enter your email")
        layout.addWidget(self.reg_email)

        # --- Buttons ---
        next_btn = QPushButton("Next Step")
        next_btn.setStyleSheet(self.button_style("#4fc3f7", "#0288d1"))
        next_btn.setMinimumHeight(45)
        next_btn.clicked.connect(self.show_register_step2)
        layout.addWidget(next_btn)

        back_btn = QPushButton("Back to Login")
        back_btn.setStyleSheet(self.button_style("#0288d1", "#01579b"))
        back_btn.setMinimumHeight(45)
        back_btn.clicked.connect(self.show_login)
        layout.addWidget(back_btn)

        return card

    # REGISTRATION STEP 2
    # Sets up user password and confirmation
    # ------------------------------------------------------
    def create_register_step2(self):
        card = self.create_card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        title = QLabel("Set Password")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title.setStyleSheet("color: #01579b;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Account Security")
        subtitle.setFont(QFont("Segoe UI", 12))
        subtitle.setStyleSheet("color: #37474f;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # Password Fields
        layout.addWidget(self.create_label("Password"))
        self.reg_password = self.create_input("Enter password", password=True)
        layout.addWidget(self.reg_password)

        layout.addWidget(self.create_label("Confirm Password"))
        self.reg_confirm = self.create_input("Confirm password", password=True)
        layout.addWidget(self.reg_confirm)

        # Buttons
        reg_btn = QPushButton("Complete Registration")
        reg_btn.setStyleSheet(self.button_style("#0288d1", "#01579b"))
        reg_btn.setMinimumHeight(45)
        reg_btn.clicked.connect(self.register_action)
        layout.addWidget(reg_btn)

        back_btn = QPushButton("Back")
        back_btn.setStyleSheet(self.button_style("#4fc3f7", "#0288d1"))
        back_btn.setMinimumHeight(45)
        back_btn.clicked.connect(self.show_register_step1)
        layout.addWidget(back_btn)

        return card

    def create_success_card(self):
        card = self.create_card_frame()
        layout = QVBoxLayout(card)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        check_icon = QLabel("✅")
        check_icon.setFont(QFont("Segoe UI Emoji", 70))
        check_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(check_icon)

        msg = QLabel("Registration Successful!")
        msg.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        msg.setStyleSheet("color: #01579b;")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(msg)

        sub_msg = QLabel("You can now sign in to your account")
        sub_msg.setFont(QFont("Segoe UI", 12))
        sub_msg.setStyleSheet("color: #37474f;")
        sub_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub_msg)

        back_btn = QPushButton("Back to Login")
        back_btn.setStyleSheet(self.button_style("#4fc3f7", "#0288d1"))
        back_btn.setMinimumHeight(45)
        back_btn.clicked.connect(self.show_login)
        layout.addWidget(back_btn)

        return card

    # UI HELPER FUNCTIONS (Reusable elements)
    # ------------------------------------------------------
    def create_card_frame(self):
        """Creates a white rounded card with shadow (used for all content panels)."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 20px;
                transition: all 0.3s ease;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setYOffset(5)
        shadow.setXOffset(0)
        shadow.setColor(QColor(0, 0, 0, 60))
        card.setGraphicsEffect(shadow)
        return card

    def create_label(self, text):
        """Creates a label for form field titles."""
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #263238; margin-bottom: 5px;")
        return lbl

    def create_input(self, placeholder="", password=False):
        """Creates a styled input box for text or password."""
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        field.setMinimumHeight(42)
        field.setStyleSheet("""
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #bbdefb;
                border-radius: 10px;
                padding-left: 12px;
                color: #263238;
                font-size: 12pt;
                transition: all 0.2s ease;
            }
            QLineEdit::placeholder {
                color: #78909c;
                font-weight: normal;
            }
            QLineEdit:focus {
                border: 2px solid #0288d1;
                background-color: #e3f2fd;
            }
        """)
        if password:
            field.setEchoMode(QLineEdit.EchoMode.Password)
        return field

    def button_style(self, bg, hover):
        """Returns consistent button style (normal and hover colors)."""
        return f"""
            QPushButton {{
                background-color: {bg};
                color: white;
                font-weight: bold;
                border-radius: 12px;
                font-size: 14px;
                min-height: 45px;
                transition: all 0.2s ease;
            }}
            QPushButton:hover {{
                background-color: {hover};
                transform: scale(1.02);
            }}
            QPushButton:pressed {{
                background-color: {hover};
                transform: scale(0.98);
            }}
        """

    # CARD NAVIGATION (switch between screens)
    # ------------------------------------------------------
    def show_login(self):
        for c in [self.register_step1, self.register_step2, self.success_card]:
            c.setVisible(False)
        self.login_card.setVisible(True)

    def show_register_step1(self):
        for c in [self.login_card, self.register_step2, self.success_card]:
            c.setVisible(False)
        self.register_step1.setVisible(True)

    def show_register_step2(self):
        if not all([self.reg_name.text(), self.reg_age.text(), self.reg_email.text()]):
            msg = QMessageBox()
            msg.setWindowTitle("Error")
            msg.setText("Please fill all fields before proceeding.")
            msg.setStyleSheet("""
                QMessageBox { 
                    background-color: #ffffff; 
                } 
                QLabel { 
                    color: #263238; 
                }
                QPushButton {
                    background-color: #0288d1;
                    color: white;
                    border-radius: 8px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #01579b;
                }
            """)
            msg.exec()
            return
        self.register_step1.setVisible(False)
        self.register_step2.setVisible(True)

    def show_success(self):
        """Display success confirmation card."""
        for c in [self.login_card, self.register_step1, self.register_step2]:
            c.setVisible(False)
        self.success_card.setVisible(True)

    # LOGIN AND REGISTRATION LOGIC
    # --------------------------------------------
    def login_action(self):
        """
        Handles login for both staff and patients.
        Validates credentials and redirects to the correct dashboard.
        """
        email = self.login_email.text().strip()
        pw = self.login_password.text().strip()

        if not email or not pw:
            msg = QMessageBox()
            msg.setWindowTitle("Login")
            msg.setText("Enter email and password.")
            msg.setStyleSheet("""
                QMessageBox { 
                    background-color: #ffffff; 
                } 
                QLabel { 
                    color: #263238; 
                }
                QPushButton {
                    background-color: #0288d1;
                    color: white;
                    border-radius: 8px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #01579b;
                }
            """)
            msg.exec()
            return

        db = DB()
        try:
            # --- Staff login ---
            staff = db.query("SELECT * FROM staff WHERE email=%s", (email,))
            if staff and check_password(pw, staff[0]["password"]):
                db.close()
                self.hide()
                self.staff_win = StaffDashboard(staff[0]["id"], staff[0]["name"])
                self.staff_win.show()
                return

            # --- Patient login ---
            patient = db.query("SELECT * FROM patients WHERE email=%s", (email,))
            if patient and check_password(pw, patient[0]["password"]):
                db.close()
                self.hide()
                self.patient_win = PatientDashboard(patient[0]["id"], patient[0]["name"])
                self.patient_win.show()
                return

            # --- Invalid credentials ---
            msg = QMessageBox()
            msg.setWindowTitle("Login")
            msg.setText("Invalid credentials.")
            msg.setStyleSheet("""
                QMessageBox { 
                    background-color: #ffffff; 
                } 
                QLabel { 
                    color: #263238; 
                }
                QPushButton {
                    background-color: #0288d1;
                    color: white;
                    border-radius: 8px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #01579b;
                }
            """)
            msg.exec()
        except Exception as e:
            logging.error(f"Login failed: {str(e)}", exc_info=True)
            msg = QMessageBox()
            msg.setWindowTitle("Error")
            msg.setText(f"Login failed: {str(e)}")
            msg.setStyleSheet("""
                QMessageBox { 
                    background-color: #ffffff; 
                } 
                QLabel { 
                    color: #263238; 
                }
                QPushButton {
                    background-color: #0288d1;
                    color: white;
                    border-radius: 8px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #01579b;
                }
            """)
            msg.exec()
        finally:
            db.close()

    def register_action(self):
        """
        Handles patient registration.
        1. Validates inputs.
        2. Checks for existing email.
        3. Hashes password and saves to database.
        """
        logging.debug("Starting registration process")
        name = self.reg_name.text().strip()
        age = self.reg_age.text().strip()
        sex = self.reg_sex.currentText()
        email = self.reg_email.text().strip()
        pw = self.reg_password.text().strip()
        confirm = self.reg_confirm.text().strip()

        # Input validation
        if not all([name, email, pw, confirm]):
            logging.warning("Registration failed: Missing required fields")
            msg = QMessageBox()
            msg.setWindowTitle("Error")
            msg.setText("Please fill all required fields.")
            msg.setStyleSheet("""
                QMessageBox { 
                    background-color: #ffffff; 
                } 
                QLabel { 
                    color: #263238; 
                }
                QPushButton {
                    background-color: #0288d1;
                    color: white;
                    border-radius: 8px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #01579b;
                }
            """)
            msg.exec()
            return
        if pw != confirm:
            logging.warning("Registration failed: Passwords do not match")
            msg = QMessageBox()
            msg.setWindowTitle("Error")
            msg.setText("Passwords do not match.")
            msg.setStyleSheet("""
                QMessageBox { 
                    background-color: #ffffff; 
                } 
                QLabel { 
                    color: #263238; 
                }
                QPushButton {
                    background-color: #0288d1;
                    color: white;
                    border-radius: 8px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #01579b;
                }
            """)
            msg.exec()
            return
        if not age.isdigit() or not (1 <= int(age) <= 120):
            logging.warning("Registration failed: Invalid age")
            msg = QMessageBox()
            msg.setWindowTitle("Error")
            msg.setText("Please enter a valid age between 1 and 120.")
            msg.setStyleSheet("""
                QMessageBox { 
                    background-color: #ffffff; 
                } 
                QLabel { 
                    color: #263238; 
                }
                QPushButton {
                    background-color: #0288d1;
                    color: white;
                    border-radius: 8px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #01579b;
                }
            """)
            msg.exec()
            return

        db = DB()
        try:
            logging.debug(f"Checking if email {email} exists")
            exists = db.query("SELECT id FROM patients WHERE email=%s", (email,))
            if exists:
                logging.warning(f"Registration failed: Email {email} already registered")
                msg = QMessageBox()
                msg.setWindowTitle("Error")
                msg.setText("Email already registered.")
                msg.setStyleSheet("""
                    QMessageBox { 
                        background-color: #ffffff; 
                    } 
                    QLabel { 
                        color: #263238; 
                    }
                    QPushButton {
                        background-color: #0288d1;
                        color: white;
                        border-radius: 8px;
                        padding: 8px 16px;
                    }
                    QPushButton:hover {
                        background-color: #01579b;
                    }
                """)
                msg.exec()
                return

            logging.debug("Hashing password")
            hashed_pw = hash_password(pw)
            age_value = int(age) if age else None
            logging.debug(f"Inserting patient: name={name}, age={age_value}, sex={sex}, email={email}")
            db.query(
                "INSERT INTO patients (name, age, sex, email, password) VALUES (%s, %s, %s, %s, %s)",
                (name, age_value, sex, email, hashed_pw),
                commit=True
            )
            logging.info("Registration successful")
            msg = QMessageBox()
            msg.setWindowTitle("Success")
            msg.setText("Registration completed successfully.")
            msg.setStyleSheet("""
                QMessageBox { 
                    background-color: #ffffff; 
                } 
                QLabel { 
                    color: #263238; 
                }
                QPushButton {
                    background-color: #0288d1;
                    color: white;
                    border-radius: 8px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #01579b;
                }
            """)
            msg.exec()
            self.show_success()
        except Exception as e:
            logging.error(f"Registration failed: {str(e)}", exc_info=True)
            msg = QMessageBox()
            msg.setWindowTitle("Error")
            msg.setText(f"Registration failed: {str(e)}")
            msg.setStyleSheet("""
                QMessageBox { 
                    background-color: #ffffff; 
                } 
                QLabel { 
                    color: #263238; 
                }
                QPushButton {
                    background-color: #0288d1;
                    color: white;
                    border-radius: 8px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #01579b;
                }
            """)
            msg.exec()
        finally:
            db.close()