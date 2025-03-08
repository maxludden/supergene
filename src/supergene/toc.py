"""This module contains the functions for reading and writing the table of contents (TOC) file."""
from pathlib import Path
from typing import Generator, List

from yaml import safe_dump, safe_load
from selenium import webdriver
from selenium.webdriver.common.by import By
