from dotenv import load_dotenv
load_dotenv()

import sys
import os

# Add the root directory (where this script is) to the Python path
sys.path.append(os.path.abspath("."))

from gui.main_window import launch_gui

if __name__ == "__main__":
    launch_gui()
