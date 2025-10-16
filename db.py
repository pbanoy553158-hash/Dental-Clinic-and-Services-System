# db.py
# MySQL + bcrypt password management
# Auto-creates and synchronizes `clinic_management` database schema

import mysql.connector
from mysql.connector import errorcode
import bcrypt
import sys
import traceback
from datetime import datetime

# === Configure your MySQL connection ===
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = ""   # change if you set a MySQL password
DB_NAME = "clinic_management"


# ---------------- Database Connection ----------------
def get_conn(database=None):
    """Return a live MySQL connection."""
    args = dict(host=DB_HOST, user=DB_USER, password=DB_PASSWORD)
    if database:
        args["database"] = database
    return mysql.connector.connect(**args)


# ---------------- Password Hashing Helpers ----------------
def hash_password(plain: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(plain: str, hashed: str) -> bool:
    """Verify a bcrypt-hashed password."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ---------------- Simple DB Wrapper ----------------
class DB:
    """Simple MySQL wrapper with automatic reconnect and query helpers."""
    def __init__(self, use_db=True):
        try:
            if use_db:
                self.conn = get_conn(DB_NAME)
            else:
                self.conn = get_conn()
            self.cur = self.conn.cursor(dictionary=True)
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_BAD_DB_ERROR:
                self._create_db()
                self.conn = get_conn(DB_NAME)
                self.cur = self.conn.cursor(dictionary=True)
            else:
                raise

    def _create_db(self):
        tmp = get_conn()
        c = tmp.cursor()
        c.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} DEFAULT CHARACTER SET 'utf8mb4'")
        tmp.commit()
        c.close()
        tmp.close()

    def query(self, sql, params=None, commit=False):
        """Execute SQL query and optionally commit changes."""
        self.cur.execute(sql, params or ())
        if sql.strip().lower().startswith("select"):
            return self.cur.fetchall()
        if commit:
            self.conn.commit()
        return True

    def close(self):
        """Safely close connection and cursor."""
        try:
            self.cur.close()
            self.conn.close()
        except Exception:
            pass


# ---------------- Schema Creation ----------------
def create_tables():
    """Create or sync all tables used by the clinic system."""
    db = DB(use_db=False)
    db._create_db()
    db.close()

    db = DB()

    # --- Staff ---
    db.query("""
        CREATE TABLE IF NOT EXISTS staff (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(150),
            email VARCHAR(200) UNIQUE,
            password VARCHAR(255),
            role VARCHAR(50),
            phone VARCHAR(30),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """, commit=True)

    # --- Patients ---
    db.query("""
        CREATE TABLE IF NOT EXISTS patients (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(150),
            age INT,
            sex ENUM('Male','Female','Other'),
            email VARCHAR(200) UNIQUE,
            password VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """, commit=True)

    # --- Services ---
    db.query("""
        CREATE TABLE IF NOT EXISTS services (
            id INT AUTO_INCREMENT PRIMARY KEY,
            code VARCHAR(64) UNIQUE,
            name VARCHAR(150),
            description TEXT,
            price DECIMAL(10,2),
            active TINYINT(1) DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """, commit=True)

    # --- Appointments ---
    db.query("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            patient_id INT,
            service_id INT,
            date DATE,
            time TIME,
            notes TEXT,
            status ENUM('Pending','Confirmed','Completed','Cancelled') DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(id),
            FOREIGN KEY (service_id) REFERENCES services(id)
        )
    """, commit=True)

    # --- Transactions ---
    db.query("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            patient_id INT,
            service_id INT,
            amount DECIMAL(10,2),
            paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(id),
            FOREIGN KEY (service_id) REFERENCES services(id)
        )
    """, commit=True)

    db.close()


# ---------------- Seeder ----------------
def seed_defaults():
    """Insert default data: staff, patient, and 15 dental services."""
    create_tables()
    db = DB()

    # ✅ Seed Staff
    if not db.query("SELECT id FROM staff"):
        staff_members = [
            ("Dr. Maria Santos", "Dentist", "maria.santos@clinic.local", hash_password("staff123"), "09171234567"),
            ("Dr. John Reyes", "Dentist", "john.reyes@clinic.local", hash_password("staff123"), "09181234567"),
            ("Ana Cruz", "Assistant", "ana.cruz@clinic.local", hash_password("staff123"), "09281234567"),
            ("Carla Dizon", "Receptionist", "carla.dizon@clinic.local", hash_password("staff123"), "09391234567"),
        ]
        for s in staff_members:
            db.query(
                "INSERT INTO staff (name, role, email, password, phone) VALUES (%s,%s,%s,%s,%s)",
                s,
                commit=True,
            )

    # ✅ Seed Sample Patient
    if not db.query("SELECT id FROM patients"):
        db.query(
            "INSERT INTO patients (name, age, sex, email, password) VALUES (%s,%s,%s,%s,%s)",
            ("Juan Dela Cruz", 35, "Male", "patient1@clinic.local", hash_password("patient123")),
            commit=True,
        )

    # ✅ Seed 15 Services
    if not db.query("SELECT id FROM services"):
        services = [
            ("CM-OPH", "Oral Prophylaxis", "Cleaning & polishing", 1200.00),
            ("CM-FILL", "Dental Filling", "Composite filling for cavities", 2500.00),
            ("CM-EXT", "Tooth Extraction", "Simple extraction", 1800.00),
            ("CM-RCT", "Root Canal", "Therapy for infected tooth", 4500.00),
            ("CM-WHT", "Teeth Whitening", "In-office bleaching", 3500.00),
            ("CM-IMP", "Dental Implant", "Implant placement", 20000.00),
            ("CM-BRAC", "Orthodontic Braces", "Braces installation", 25000.00),
            ("CM-RTN", "Retainer Adjustment", "Adjustment or fitting", 2000.00),
            ("CM-WIS", "Wisdom Tooth Removal", "Surgical extraction", 6500.00),
            ("CM-GUM", "Gum Treatment", "Scaling & root planing", 3200.00),
            ("CM-XRAY", "Dental X-Ray", "Panoramic imaging", 800.00),
            ("CM-PED", "Pediatric Check-Up", "Child dental exam", 1000.00),
            ("CM-DEN", "Dentures Fitting", "Removable dentures", 12000.00),
            ("CM-EMR", "Emergency Visit", "Urgent dental care", 900.00),
            ("CM-VEN", "Veneers", "Porcelain veneer restoration", 8000.00)
        ]
        for s in services:
            db.query("INSERT INTO services (code, name, description, price) VALUES (%s,%s,%s,%s)", s, commit=True)

    db.close()


# ---------------- Run Directly ----------------
if __name__ == "__main__":
    try:
        seed_defaults()
        print("✅ Database initialized and synced successfully.")
    except Exception as e:
        print("❌ Database initialization error:", e)
        traceback.print_exc()
        sys.exit(1)
