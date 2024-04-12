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
from PIL import ImageGrab,Image, ImageTk

import io
import win32clipboard


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



def create_thumbnail(image_path, max_size=(100, 100)):
    """Create a thumbnail of the image at the given path."""
    try:
        img = Image.open(image_path)
        img.thumbnail(max_size)
        return ImageTk.PhotoImage(img)  # Convert the PIL Image to a displayable image
    except IOError as e:
        logging.error(f"Unable to create thumbnail for {image_path}: {e}")
        # Return a default 'image not found' thumbnail
        default_img = Image.open(resource_path('image_not_found.png'))
        default_img.thumbnail(max_size)
        return ImageTk.PhotoImage(default_img)


def update_frame(parent_frame, clipboard_history):
    # Clear existing widgets
    for widget in parent_frame.winfo_children():
        widget.destroy()

    # Get screen dimensions
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Number of rows and columns
    num_rows = 6
    num_cols = 5

    # Calculate space for padding (padding is 5 pixels on each side of a cell)
    total_padding_x = (num_cols + 1) * 5  # total horizontal padding
    total_padding_y = (num_rows + 1) * 5  # total vertical padding

    # Calculate grid dimensions
    cell_width = (screen_width - total_padding_x) // num_cols
    cell_height = (screen_height - total_padding_y) // num_rows
    # Other UI update code remains unchanged...

    for i, item in enumerate(reversed(clipboard_history)):
        note_frame = tk.Frame(parent_frame, bg='white', width=cell_width, height=cell_height)
        # Other frame setup code remains unchanged...
        top_frame = tk.Frame(note_frame, bg='white')
        top_frame.pack(side='top', fill='x')
        
        position_label = tk.Label(top_frame, text=str(valid_keys[i]), bg='white', fg='black', font=("", 11))
        position_label.pack(side='left')
        
        # Delete button
        delete_button = tk.Button(top_frame, text="Delete", command=lambda item=item: remove_from_list(clipboard_history, item))
        delete_button.pack(side='right')

        # Paste button
        paste_button = tk.Button(top_frame, text="Paste", command=lambda item=item: paste_item(item))
        paste_button.pack(side='right')

        # Copy button
        copy_button = tk.Button(top_frame, text="Copy", command=lambda item=item: move_to_top(clipboard_history, item))
        copy_button.pack(side='right')
        # Check the type of the clipboard item and handle accordingly
        if item['type'] == 'text':
            truncated_text = (item['content'][:80] + '...') if len(item['content']) > 80 else item['content']
            lbl = tk.Label(note_frame, text=truncated_text, bg='white', fg='black', font=("", 10), wraplength=cell_width - 15)
            lbl.pack(side='bottom')
        elif item['type'] == 'image':
            # For image items, show a thumbnail
            thumbnail = create_thumbnail(item['content'])
            img_lbl = tk.Label(note_frame, image=thumbnail)
            img_lbl.image = thumbnail  # Keep a reference to avoid garbage collection
            img_lbl.pack(side='bottom')

        # Position, Copy, Delete buttons code remains unchanged...


# Function to save the PIL image object to a file in the cbimg folder
def save_clipboard_image(img, filename):
    # Define the directory to save images
    image_dir = os.path.join(resource_path(''), 'cbimg')
    # Create the directory if it doesn't exist
    if not os.path.exists(image_dir):
        os.makedirs(image_dir)
    
    # Define the full path to save the image
    image_path = os.path.join(image_dir, filename)
    # Save the image to the specified path
    img.save(image_path, 'PNG')
    return image_path  # Return the path where the image was saved

def get_clipboard_content_type():
    # This function will try to determine the type of content currently in the clipboard
    # Possible return values are 'text', 'image', or 'unknown'

    try:
        # First, we try to grab the image from the clipboard
        img = ImageGrab.grabclipboard()
        if img is not None:
            return 'image'
        else:
            # If no image was found, let's assume it's text for now
            # More types (like files, etc.) can be added here in the future
            return 'text'
    except Exception as e:
        logging.error(f"Error determining clipboard content type: {e}")
        return 'unknown'



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

# Modified save_clipboard_history function
def save_clipboard_history():
    # Save the clipboard history to a JSON file, with images referenced by paths
    json_file_path = resource_path("clipboard_history.json")
    with open(json_file_path, "w") as f:
        # Convert image objects to paths before saving
        to_save_history = []
        for item in clipboard_history:
            # Since images are already saved to file when copied to clipboard,
            # we just need to store the path in the history.
            to_save_history.append(item)
        json.dump(to_save_history, f)
        
def cleanup_temp_images():
    for item in clipboard_history:
        if item['type'] == 'image' and 'temp_image_' in item['content']:
            try:
                os.remove(item['content'])  # Attempt to remove temp image files
                logging.info(f"Removed temporary image file: {item['content']}")
            except OSError as e:
                logging.error(f"Error removing file {item['content']}: {e}")
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

stop_flag = threading.Event()
show_overlay = threading.Event()
update_event = threading.Event()
current_keys = set()

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
    # This function will return the clipboard content based on its type
    content_type = get_clipboard_content_type()
    if content_type == 'text':
        try:
            result = subprocess.check_output('powershell Get-Clipboard', stderr=subprocess.STDOUT, text=True)
            return {'type': 'text', 'content': result.strip()}
        except subprocess.CalledProcessError as e:
            logging.warning(f"Failed to access clipboard using PowerShell. Error: {e.output}")
            return {'type': 'unknown', 'content': ''}
    elif content_type == 'image':
        try:
            img = ImageGrab.grabclipboard()
            if img is not None:
                # Save the image temporarily and return the file path
                image_filename = f'temp_image_{int(time.time())}.png'
                image_path = os.path.join('cbimg', image_filename)
                img.save(image_path, 'PNG')
                return {'type': 'image', 'content': image_path}
        except Exception as e:
            logging.error(f"Error accessing image from clipboard: {e}")
            return {'type': 'unknown', 'content': ''}
    else:
        return {'type': 'unknown', 'content': ''}



def clipboard_listener(clipboard_history, update_event, stop_flag):
    global paste_in_progress
    previous_clipboard_content = {"type": "", "content": ""}
    while not stop_flag.is_set():
        if not paste_in_progress:
            current_clipboard = get_clipboard()
            if current_clipboard['content'] != previous_clipboard_content['content']:
                # If the content already exists, remove it first so it can be appended to the end
                clipboard_history[:] = [item for item in clipboard_history if item['content'] != current_clipboard['content']]
                clipboard_history.append(current_clipboard)

                # Limit the history to 40 entries
                if len(clipboard_history) > 40:
                    clipboard_history.pop(0)

                previous_clipboard_content = current_clipboard
                save_clipboard_history()
                update_event.set()
            time.sleep(0.1)



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
    
    # Set the focus back to the last active window
    if last_active_window:
        win32gui.BringWindowToTop(last_active_window)
    
    # Check the type of the item and handle accordingly
    if item['type'] == 'text':
        # Perform the existing text copy and paste operation
        pyperclip.copy(item['content'])
        # Simulate Ctrl+V to paste
        keyboard_controller.press(keyboard.Key.ctrl)
        keyboard_controller.press('v')
        keyboard_controller.release('v')
        keyboard_controller.release(keyboard.Key.ctrl)
    elif item['type'] == 'image':
        # For image items, load the image and set it to the clipboard
        try:
            image = Image.open(item['content'])
            output = io.BytesIO()
            image.save(output, format='BMP')
            data = output.getvalue()[14:]  # Remove the BMP header
            output.close()
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
            win32clipboard.CloseClipboard()
        except Exception as e:
            logging.error(f"Failed to paste image from clipboard: {e}")
    
    time.sleep(0.5)
    show_overlay.clear()
    show_overlay.set()



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
    # Go through the clipboard history and delete image files
    for item in clipboard_history:
        if item['type'] == 'image':
            try:
                os.remove(item['content'])  # Attempt to remove image files
                logging.info(f"Removed image file: {item['content']}")
            except OSError as e:
                logging.error(f"Error removing file {item['content']}: {e}")
    clipboard_history.clear()  # Clear the list
    save_clipboard_history()  # Save the changes
    update_event.set()  # Trigger the UI update

    # Restore focus to the last active window if it exists
    if last_active_window:
        win32gui.BringWindowToTop(last_active_window)
    
    # Clear the overlay and trigger it to be set again if necessary
    time.sleep(0.5)
    show_overlay.clear()
    show_overlay.set()



if __name__ == '__main__':
    
    clipboard_history = load_clipboard_history()
    keyboard_thread = threading.Thread(target=start_keyboard_listener)
    keyboard_thread.daemon = True
    keyboard_thread.start()
    # logging.info('Keyboard listener thread started.')

    # logging.info('Starting main function...')
    logging.info('Coolboard running')
    
    root = tk.Tk()
    root.title("Clipboard Manager")
    root.attributes('-fullscreen', True)  # Make it full screen
    root.overrideredirect(True)
    root.wm_attributes('-alpha', 0.72)
    # root.configure(bg='rgba(0, 0, 0, 0.5)')  # Darken the background
    root.bind('<Button-3>', hide_overlay)
    root.withdraw()
    

    update_event = threading.Event()
    # clipboard_history = []

    clip_frame = tk.Frame(root, bg='black')
    clip_frame.pack(fill='both', expand=True, side='top')

    # Initialize the footer frame with controlled height
    footer_frame = tk.Frame(root, bg='black', height=30)
    footer_frame.pack(fill='x', side='bottom', pady=(0, 5))

    # This line is used to set the frame height
    footer_frame.pack_propagate(False)

    # Add a Quit button to the footer frame with reduced padding
    quit_button = tk.Button(footer_frame, text="Quit", command=lambda: exit_program(None, None), pady=2)
    quit_button.pack(side='right')

    # Add a Clear Clipboard button to the footer frame with reduced padding
    clear_button = tk.Button(footer_frame, text="Clear Clipboard", command=clear_clipboard_history, pady=2)
    clear_button.pack(side='right')

    # This line is used to set the frame height
    footer_frame.pack_propagate(False)

    clipboard_thread = threading.Thread(target=clipboard_listener, args=(clipboard_history, update_event, stop_flag))
    clipboard_thread.daemon = True
    clipboard_thread.start()





    def periodic_update():
        if update_event.is_set():
            update_frame(clip_frame, clipboard_history)
            update_event.clear()

        if show_overlay.is_set() or overlay_state == 'perm':
            root.deiconify()
        else:
            root.withdraw()

        root.after(100, periodic_update)

    # Schedule the periodic update function to run
    root.after(100, periodic_update)

    # Function to run pystray icon
    def run_icon():
        global icon
        icon_path = resource_path("icon.ico")  # Use resource_path function
        image = Image.open(icon_path)
        icon = pystray.Icon("Clipboard Manager", image, "Clipboard Manager", menu=pystray.Menu(
            item('Show/Hide Overlay', toggle_overlay),
            item('Clear Clipboard', lambda icon, item: clear_clipboard()),  # New menu item
            item('Exit', exit_program)
        ))
        icon.run()

    # Run the pystray icon in a separate thread
    icon_thread = threading.Thread(target=run_icon)
    icon_thread.daemon = True
    icon_thread.start()

    root.mainloop()