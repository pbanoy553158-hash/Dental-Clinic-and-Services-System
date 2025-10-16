import sys, traceback
from PyQt6.QtWidgets import QApplication, QMessageBox
from ui.portal_ui import ClinicPortal
from db import seed_defaults

print("Starting application...")

try:
    seed_defaults()
    print("Database check done.")
 
    app = QApplication(sys.argv)
    print("QApplication created.")

    win = ClinicPortal()
    print("Portal UI initialized.")

    win.show()
    print("UI shown.")

    sys.exit(app.exec())
except Exception as e:
    traceback.print_exc()   
    app = QApplication(sys.argv)
    QMessageBox.critical(None, "Error", str(e))
    sys.exit(1)
