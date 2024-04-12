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


# perm_timer_started = False
keyboard_controller = Controller()  # Initialize keyboard controller
both_keys_pressed = False
overlay_permanent = False
alt_shift_pressed_time = 0
overlay_state = 'hidden'
keys_released = 0
paste_in_progress = False
last_key_press_time = 0  # Initialize to 0
debounce_time = 0.2  # 200 ms debounce time
long_press_time = 0.5  # 700 ms for long press
timer_started = False  # To check if timer is started for long press
valid_keys = '1234567890abcdefghijklmnopqrstuvwxyz-=[]/'
last_active_window = None
cbwindow = None
stop_flag = threading.Event()
show_overlay = threading.Event()
update_event = threading.Event()
current_keys = set()


def hide_overlay(event=None):
    global overlay_state, show_overlay
    overlay_state = 'hidden'
    show_overlay.clear()

# Function to get the resource path for bundled data
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

def save_clipboard_history():
    json_file_path = resource_path("clipboard_history.json")  # Use resource_path function
    with open(json_file_path, "w") as f:
        json.dump(clipboard_history, f)


def clear_clipboard():
    global clipboard_history  # Declare it global to modify it
    clipboard_history.clear()  # Clear the list
    pyperclip.copy("")  # Clear the actual clipboard
    save_clipboard_history()  # Save the changes
    update_event.set()  # Trigger the UI update


def start_long_press_timer():
    global timer_started, overlay_state
    time.sleep(long_press_time)
    if timer_started:  # If timer is still active, it's a long press
        # print("Long press detected")
        overlay_state = 'temp'
        show_overlay.set()
    timer_started = False  # Reset the flag

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')



process_release = False  # New flag
last_alt_shift_time = 0  # Initialize to 0

def on_press(key):
    global alt_shift_pressed_time, overlay_state, both_keys_pressed, last_active_window, cbwindow, paste_in_progress
    current_time = time.time()


    try:
        key_name = key.char
    except AttributeError:
        key_name = str(key)

    current_keys.add(key_name)

    if 'Key.alt_l' in current_keys and 'Key.shift' in current_keys and not both_keys_pressed:
        both_keys_pressed = True
        alt_shift_pressed_time = current_time

        # Store the handle of the currently active window
        last_active_window = win32gui.GetForegroundWindow()

        if overlay_state == 'hidden':
            overlay_state = 'temp'
            show_overlay.set()
            if (cbwindow == None):
                cbwindow = win32gui.GetForegroundWindow()

    elif overlay_state in ['temp', 'perm'] and key_name in valid_keys: 
        index = valid_keys.index(key_name)
        if 0 <= index < len(clipboard_history):
            # Map "1" to the newest (last) item, "2" to the second newest, and so on
            item_to_paste = clipboard_history[-(index + 1)]
            paste_in_progress = True
            pyperclip.copy(item_to_paste)
            # Simulate Backspace and then Ctrl+V
            keyboard_controller.press(keyboard.Key.backspace)
            keyboard_controller.release(keyboard.Key.backspace)
            keyboard_controller.press(keyboard.Key.ctrl)
            keyboard_controller.press('v')
            keyboard_controller.release('v')
            keyboard_controller.release(keyboard.Key.ctrl)
            time.sleep(0.1)
            paste_in_progress = False


def on_release(key):
    global overlay_state, alt_shift_pressed_time, both_keys_pressed
    try:
        key_name = key.char
    except AttributeError:
        key_name = str(key)

    try:
        current_keys.remove(key_name)
    except KeyError:
        pass

    if both_keys_pressed and ('Key.alt_l' in key_name or 'Key.shift' in key_name):
        both_keys_pressed = False  # Reset the flag
        time_diff = time.time() - alt_shift_pressed_time

        if overlay_state == 'temp':
            if time_diff >= 0.5:
                overlay_state = 'hidden'
                show_overlay.clear()  # Hide the overlay
            else:
                overlay_state = 'perm'
                show_overlay.set()
        elif overlay_state == 'perm':
            overlay_state = 'hidden'
            show_overlay.clear()



def get_clipboard():
    try:
        result = subprocess.check_output('powershell Get-Clipboard', stderr=subprocess.STDOUT, text=True)
        return result.strip()
    except subprocess.CalledProcessError as e:
        logging.warning(f"Failed to access clipboard using PowerShell. Error: {e.output}")
        return ""


def clipboard_listener(clipboard_history, update_event, stop_flag):
    global paste_in_progress
    previous_clipboard_content = ""
    while not stop_flag.is_set():
        if not paste_in_progress:
            try:
                new_clipboard_content = get_clipboard()
                if new_clipboard_content != previous_clipboard_content:
                    # If the content already exists, remove it first so it can be appended to the end
                    if new_clipboard_content in clipboard_history:
                        clipboard_history.remove(new_clipboard_content)
                    clipboard_history.append(new_clipboard_content)

                    # Limit the history to 40 entries
                    if len(clipboard_history) > 40:
                        del clipboard_history[0]

                    previous_clipboard_content = new_clipboard_content
                    save_clipboard_history() 
                    update_event.set()
                time.sleep(0.1)
            except Exception as e:
                logging.error(e)


def copy_to_clipboard(content):
    pyperclip.copy(content)

def toggle_overlay(icon, item):
    global overlay_state, show_overlay
    if overlay_state == 'hidden':
        overlay_state = 'perm'
        show_overlay.set()
    else:
        overlay_state = 'hidden'
        show_overlay.clear()

def move_to_top(lst, item):
    global last_active_window
    lst.remove(item)
    lst.append(item)
    copy_to_clipboard(item)
    update_event.set()

    # First, set the focus back to the last active window
    if last_active_window:
        win32gui.BringWindowToTop(last_active_window)

    time.sleep(0.5)

    show_overlay.clear()
    show_overlay.set()


def remove_from_list(lst, item):
    lst.remove(item)
    save_clipboard_history()
    update_event.set()

    if last_active_window:
        win32gui.BringWindowToTop(last_active_window)
    time.sleep(0.5)
    show_overlay.clear()
    show_overlay.set()


def paste_item(item):
    global last_active_window, overlay_state
    
    # First, set the focus back to the last active window
    if last_active_window:
        win32gui.BringWindowToTop(last_active_window)
    
    # Then perform the copy and paste operation as before
    pyperclip.copy(item)
    
    # Simulate Ctrl+V to paste
    keyboard_controller.press(keyboard.Key.ctrl)
    keyboard_controller.press('v')
    keyboard_controller.release('v')
    keyboard_controller.release(keyboard.Key.ctrl)

    # overlay_state = 'hidden'
    # show_overlay.clear()  # Hide the overlay
    time.sleep(0.5)
    show_overlay.clear()
    show_overlay.set()

    # # Optionally, reset last_active_window
    # last_active_window


def exit_program(icon, item):
    if icon is not None:
        icon.stop()
    stop_flag.set()
    save_clipboard_history()
    root.destroy()

def start_keyboard_listener():
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

def clear_clipboard_history():
    global clipboard_history  # Declare it global to modify it
    clipboard_history.clear()  # Clear the list
    save_clipboard_history()  # Save the changes
    update_event.set()  # Trigger the UI update

    if last_active_window:
        win32gui.BringWindowToTop(last_active_window)
    time.sleep(0.5)
    show_overlay.clear()
    show_overlay.set()


class ClipboardUI:
    def __init__(self, clipboard_history):
        self.clipboard_history = clipboard_history
        self.root = tk.Tk()
        self.root.title("Clipboard Manager")
        self.clipboard_history = clipboard_history
        self.update_event = update_event
        self.keyboard_controller = Controller()  # Initialize keyboard controller here
        self.root.attributes('-fullscreen', True)
        self.root.overrideredirect(True)
        self.root.wm_attributes('-alpha', 0.72)
        self.root.bind('<Button-3>', self.hide_overlay)
        self.root.withdraw()

        self.clip_frame = tk.Frame(self.root, bg='black')
        self.clip_frame.pack(fill='both', expand=True, side='top')

        self.footer_frame = tk.Frame(self.root, bg='black', height=30)
        self.footer_frame.pack(fill='x', side='bottom', pady=(0, 5))
        self.footer_frame.pack_propagate(False)

        quit_button = tk.Button(self.footer_frame, text="Quit", command=lambda: self.exit_program(None, None), pady=2)
        quit_button.pack(side='right')

        clear_button = tk.Button(self.footer_frame, text="Clear Clipboard", command=clear_clipboard_history, pady=2)
        clear_button.pack(side='right')

        self.update_event = threading.Event()

    def hide_overlay(self, event=None):
        global overlay_state, show_overlay
        overlay_state = 'hidden'
        show_overlay.clear()

    def exit_program(self, icon, item):
        if icon is not None:
            icon.stop()
        stop_flag.set()
        save_clipboard_history()
        self.root.destroy()

    def update_frame(self):
        for widget in self.clip_frame.winfo_children():
            widget.destroy()

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        num_rows = 6
        num_cols = 5
        total_padding_x = (num_cols + 1) * 5
        total_padding_y = (num_rows + 1) * 5

        cell_width = (screen_width - total_padding_x) // num_cols
        cell_height = (screen_height - total_padding_y) // num_rows

        for i, item in enumerate(reversed(self.clipboard_history)):
            truncated_text = (item[:80] + '...') if len(item) > 80 else item
            note_frame = tk.Frame(self.clip_frame, bg='white', width=cell_width, height=cell_height)
            note_frame.grid(row=i // num_cols, column=i % num_cols, padx=5, pady=5)
            note_frame.grid_propagate(False)

            top_frame = tk.Frame(note_frame, bg='white')
            top_frame.pack(side='top', fill='x')
            
            position_label = tk.Label(top_frame, text=str(valid_keys[i]), bg='white', fg='black', font=("", 11))
            position_label.pack(side='left')
            
            delete_button = tk.Button(top_frame, text="Delete", command=lambda item=item: self.remove_from_list(item))
            delete_button.pack(side='right')

            paste_button = tk.Button(top_frame, text="Paste", command=lambda item=item: self.paste_item(item))
            paste_button.pack(side='right')

            copy_button = tk.Button(top_frame, text="Copy", command=lambda item=item: self.move_to_top(item))
            copy_button.pack(side='right')

            lbl = tk.Label(note_frame, text=truncated_text, bg='white', fg='black', font=("", 10), wraplength=cell_width - 15)
            lbl.pack(side='bottom')

    def periodic_update(self):
        if self.update_event.is_set():
            self.update_frame()
            self.update_event.clear()

        if show_overlay.is_set() or overlay_state == 'perm':
            self.root.deiconify()
        else:
            self.root.withdraw()

        self.root.after(100, self.periodic_update)

    def run(self):
        self.root.after(100, self.periodic_update)
        self.root.mainloop()

    def remove_from_list(self, item):
        # Remove the specified item from the clipboard history
        if item in self.clipboard_history:
            self.clipboard_history.remove(item)
            save_clipboard_history()  # Assuming this is a function to save the history to a file
            self.update_event.set()  # Trigger the UI update

    def paste_item(self, item):
        # Copy the item to the clipboard and simulate a paste action
        pyperclip.copy(item)
        self.keyboard_controller.press('v')  # Simulate pressing 'v'
        self.keyboard_controller.release('v')  # Release 'v'
        # Depending on how you want to handle focus, you might need additional code here

    def move_to_top(self, item):
        # Move the specified item to the top of the clipboard history
        if item in self.clipboard_history:
            self.clipboard_history.remove(item)
            self.clipboard_history.append(item)
            save_clipboard_history()  # Save the updated history
            self.update_event.set()  # Trigger the UI update


if __name__ == '__main__':
    clipboard_history = load_clipboard_history()
    logging.info('Coolboard running')
    
    # Initialize Clipboard UI but do not run it yet
    ui = ClipboardUI(clipboard_history)

    # Start keyboard listener thread
    keyboard_thread = threading.Thread(target=start_keyboard_listener)
    keyboard_thread.daemon = True
    keyboard_thread.start()

    # Start clipboard listener thread
    clipboard_thread = threading.Thread(target=clipboard_listener, args=(clipboard_history, ui.update_event, stop_flag))
    clipboard_thread.daemon = True
    clipboard_thread.start()

    # Function to run pystray icon in a separate thread
    def run_icon():
        icon_path = resource_path("icon.ico")
        image = Image.open(icon_path)
        icon = pystray.Icon("Clipboard Manager", image, "Clipboard Manager", menu=pystray.Menu(
            item('Show/Hide Overlay', toggle_overlay),
            item('Clear Clipboard', lambda icon, item: clear_clipboard()),
            item('Exit', lambda icon, item: ui.exit_program(icon, item))
        ))
        icon.run()

    icon_thread = threading.Thread(target=run_icon)
    icon_thread.daemon = True
    icon_thread.start()

    # Run Clipboard UI in the main thread
    ui.run()
