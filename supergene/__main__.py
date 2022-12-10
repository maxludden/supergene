from pathlib import Path
from dotenv import load_dotenv
from mongoengine import connect

from maxconsole import get_console, get_theme
from maxprogress import get_progress
from maxcolor import gradient, gradient_panel
from maxsetup import new_run