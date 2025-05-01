from modules.config_generator import generate_config_files
from modules.config_applier import apply_configurations_to_switches
import os
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

def main_menu():
    while True:
        print("\n==================== Main Menu ====================")
        print("\n 1. Generate configuration files")
        print("\n 2. Apply configurations to switches")
        print("\n 3. Exit")
        print("\n===================================================")

        choice = input("\nEnter your choice >>>>>> ").strip()

        if choice == "1":
            generate_config_files()
            input("\nPress ENTER to return to the menu...")  # Pause avant de nettoyer l'écran
            os.system('cls' if os.name == 'nt' else 'clear')
        elif choice == "2":
            apply_configurations_to_switches()
            input("\nPress ENTER to return to the menu...")  # Pause avant de nettoyer l'écran
            os.system('cls' if os.name == 'nt' else 'clear')
        elif choice == "3":
            print(Fore.YELLOW + "\n[INFO] Exiting the program. Goodbye!\n")
            break
        else:
            print(Fore.RED + "\n[ERROR] Invalid choice. Please enter a number between 1 and 3.")
            input("\nPress ENTER to return to the menu...")  # Pause avant de nettoyer l'écran
            os.system('cls' if os.name == 'nt' else 'clear')

if __name__ == "__main__":
    main_menu()