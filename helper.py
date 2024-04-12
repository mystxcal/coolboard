import tkinter as tk
from pynput import keyboard
import pyperclip
import threading
import logging
import time
import subprocess
import pystray
from pystray import MenuItem as item
from PIL import Image
from pynput.keyboard import Controller
import sys
import os
import json
import win32gui
from ctypes import windll

VK_MENU = 0x12  # Alt key
VK_SHIFT = 0x10  # Shift key

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_clipboard_history():
    json_file_path = resource_path("clipboard_history.json")  # Use resource_path function
    try:
        with open(json_file_path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_clipboard_history(clipboard_history):

    json_file_path = resource_path("clipboard_history.json")  # Use resource_path function
    with open(json_file_path, "w") as f:
        json.dump(clipboard_history, f)

def simulate_paste(backspace_before_paste=False,keyboard_controller=None):
    if (backspace_before_paste==True):
        keyboard_controller.release(keyboard.Key.backspace)
    keyboard_controller.press(keyboard.Key.ctrl)
    keyboard_controller.press('v')
    keyboard_controller.release('v')
    keyboard_controller.release(keyboard.Key.ctrl)


def copy_to_clipboard(content):
    pyperclip.copy(content)

def move_to_top(lst, item, update_event):
    lst.remove(item)
    lst.append(item)
    copy_to_clipboard(item)
    update_event.set()

def remove_from_list(clipboard_history, item, update_event):
    lst.remove(item)
    save_clipboard_history(clipboard_history)
    update_event.set()

def get_clipboard():
    try:
        result = subprocess.check_output('powershell Get-Clipboard', stderr=subprocess.STDOUT, text=True)
        return result.strip()
    except subprocess.CalledProcessError as e:
        logging.warning(f"Failed to access clipboard using PowerShell. Error: {e.output}")
        return ""
    

def create_button(frame, text, command):
    button = tk.Button(frame, text=text, command=command)
    button.pack(side='right')
    return button

def create_label(frame, text, font, bg='white', fg='black'):
    label = tk.Label(frame, text=text, bg=bg, fg=fg, font=font)
    label.pack(side='left')
    return label

def add_note_content(note_frame, text, cell_width):
    lbl = tk.Label(note_frame, text=text, bg='white', fg='black', font=("", 10), wraplength=cell_width - 15)
    lbl.pack(side='bottom')

def calculate_cell_dimensions(screen_width, screen_height, num_cols, num_rows):
    total_padding_x = (num_cols + 1) * 5  # total horizontal padding
    total_padding_y = (num_rows + 1) * 5  # total vertical padding
    cell_width = (screen_width - total_padding_x) // num_cols
    cell_height = (screen_height - total_padding_y) // num_rows
    return cell_width, cell_height

def create_note_frame(parent_frame, text, i, num_cols, cell_width, cell_height, clipboard_history, valid_keys, update_event, paste_item, item):
    note_frame = tk.Frame(parent_frame, bg='white', width=cell_width, height=cell_height)
    note_frame.grid(row=i // num_cols, column=i % num_cols, padx=5, pady=5)
    note_frame.grid_propagate(False)

    # Create top frame for buttons
    top_frame = tk.Frame(note_frame, bg='white')
    top_frame.pack(side='top', fill='x')

    # Add label and buttons
    create_label(top_frame, text=str(valid_keys[i]), font=("", 11))
    create_button(top_frame, "Delete", lambda: remove_from_list(clipboard_history, item, update_event))
    create_button(top_frame, "Paste", lambda: paste_item(text))
    create_button(top_frame, "Copy", lambda: move_to_top(clipboard_history, item, update_event))

    # Add note content
    add_note_content(note_frame, text, cell_width)