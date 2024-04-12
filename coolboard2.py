from helper import *
from helper import resource_path, load_clipboard_history, save_clipboard_history, simulate_paste, move_to_top, remove_from_list, get_clipboard

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

process_release = False  # New flag
last_alt_shift_time = 0  # Initialize to 0

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def hide_overlay(event=None):
    global overlay_state, show_overlay
    overlay_state = 'hidden'
    show_overlay.clear()

def clear_clipboard():
    clipboard_history.clear()  # Clear the list
    pyperclip.copy("")  # Clear the actual clipboard
    save_clipboard_history(clipboard_history)  # Save the changes
    update_event.set()  # Trigger the UI update

def start_long_press_timer():
    global timer_started, overlay_state
    time.sleep(long_press_time)
    if timer_started:  # If timer is still active, it's a long press
        # print("Long press detected")
        overlay_state = 'temp'
        show_overlay.set()
    timer_started = False  # Reset the flag

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
            simulate_paste(backspace_before_paste=True, keyboard_controller=keyboard_controller)
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
                    save_clipboard_history(clipboard_history) 
                    update_event.set()
                time.sleep(0.1)
            except Exception as e:
                logging.error(e)


def copy_to_clipboard(content):
    pyperclip.copy(content)

def toggle_overlay():
    global overlay_state, show_overlay
    if overlay_state == 'hidden':
        overlay_state = 'perm'
        show_overlay.set()
    else:
        overlay_state = 'hidden'
        show_overlay.clear()


def paste_item(item):
    global last_active_window, overlay_state
    
    temp_window = win32gui.GetActiveWindow()
    # First, set the focus back to the last active window
    if last_active_window:
        win32gui.BringWindowToTop(last_active_window)
    
    # Then perform the copy and paste operation as before
    pyperclip.copy(item)
    
    # Simulate Ctrl+V to paste
    simulate_paste(backspace_before_paste=False, keyboard_controller=keyboard_controller)

    # overlay_state = 'hidden'
    # show_overlay.clear()  # Hide the overlay
    time.sleep(0.2)
    win32gui.BringWindowToTop(temp_window)


def update_frame(parent_frame, clipboard_history):
    # Clear existing widgets
    for widget in parent_frame.winfo_children():
        widget.destroy()

    # Get screen dimensions and calculate grid dimensions
    screen_width = parent_frame.winfo_screenwidth()
    screen_height = parent_frame.winfo_screenheight()
    num_rows, num_cols = 6, 5
    cell_width, cell_height = calculate_cell_dimensions(screen_width, screen_height, num_cols, num_rows)

    # Create frames and widgets for each item in the clipboard history
    for i, item in enumerate(reversed(clipboard_history)):
        truncated_text = (item[:80] + '...') if len(item) > 80 else item
        create_note_frame(parent_frame, truncated_text, i, num_cols, cell_width, cell_height, clipboard_history, valid_keys, update_event, paste_item, item)

def exit_program(icon, item):
    if icon is not None:
        icon.stop()
    stop_flag.set()
    save_clipboard_history(clipboard_history)
    root.destroy()

def start_keyboard_listener():
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

def clear_clipboard_history():
    global clipboard_history  # Declare it global to modify it
    clipboard_history.clear()  # Clear the list
    save_clipboard_history(clipboard_history)  # Save the changes
    update_event.set()  # Trigger the UI update


if __name__ == '__main__':
    clipboard_history = load_clipboard_history()
    keyboard_thread = threading.Thread(target=start_keyboard_listener)
    keyboard_thread.daemon = True
    keyboard_thread.start()

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
    def run_systray():
        icon_path = resource_path("icon.ico")  # Use resource_path function
        image = Image.open(icon_path)
        icon = pystray.Icon("Clipboard Manager", image, "Clipboard Manager", menu=pystray.Menu(
            item('Show/Hide Overlay', toggle_overlay),
            item('Clear Clipboard', lambda icon, item: clear_clipboard()),  # New menu item
            item('Exit', exit_program)
        ))
        icon.run()

    # Run the pystray icon in a separate thread
    icon_thread = threading.Thread(target=run_systray)
    icon_thread.daemon = True
    icon_thread.start()

    root.mainloop()