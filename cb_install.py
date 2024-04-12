import os
import sys
import subprocess
import shutil
from distutils.dir_util import copy_tree
import winshell

# def install_dependencies():
#     requirements_path = os.path.join(sys._MEIPASS, "requirements.txt")
#     subprocess.run(["pip", "install", "-r", requirements_path], check=True)

def copy_files(dest_dir):
    src_dir = sys._MEIPASS
    copy_tree(src_dir, dest_dir)

def create_shortcut(exe_path, shortcut_name, icon_path, shortcut_path):
    try:
        if os.name == 'nt':
            import winshell

            winshell.CreateShortcut(
                Path=shortcut_path,
                Target=exe_path,  # Pointing directly to the .exe file
                Arguments="",  # No arguments needed as everything is bundled
                Icon=(icon_path, 0),
                Description=f"Run {shortcut_name}"
            )
        print(f"Shortcut created at {shortcut_path}")
    except Exception as e:
        print(f"An error occurred while creating the shortcut: {e}")

def main():

    default_target_folder = os.path.expanduser("~/Coolboard")
    target_folder = input(f"Enter the path where you want to install the application [{default_target_folder}] (leave blank for default location): ")
    if not target_folder:
        target_folder = default_target_folder

    if not os.path.exists(target_folder):
        os.makedirs(target_folder)

    # install_dependencies()
    copy_files(target_folder)

    py_script_path = os.path.join(target_folder, "coolboard.exe")
    icon_path = os.path.join(sys._MEIPASS, "icon.ico")  # Assuming you've included icon.ico with PyInstaller

    # Always create a shortcut in the installation folder
    install_folder_shortcut_path = os.path.join(target_folder, "Coolboard.lnk")
    create_shortcut(py_script_path, "Coolboard", icon_path, install_folder_shortcut_path)

    create_desktop_shortcut = input("Do you want to create a desktop shortcut? (y/n): ")
    if create_desktop_shortcut.lower() == 'y':
        desktop_folder = os.path.expanduser("~/Desktop")
        desktop_shortcut_path = os.path.join(desktop_folder, "Coolboard.lnk")
        create_shortcut(py_script_path, "Coolboard", icon_path, desktop_shortcut_path)

    print(f"The application has been installed at {target_folder}")
    input("Press Enter to exit the installer.")

def create_shortcut(exe_path, shortcut_name, icon_path, shortcut_path):
    try:
        if os.name == 'nt':

            winshell.CreateShortcut(
                Path=shortcut_path,
                Target=exe_path,  # Pointing directly to the .exe file
                Arguments="",  # No arguments needed as everything is bundled
                Icon=(icon_path, 0),
                Description=f"Run {shortcut_name}"
            )
        print(f"Shortcut created at {shortcut_path}")
    except Exception as e:
        print(f"An error occurred while creating the shortcut: {e}")


if __name__ == "__main__":
    main()
