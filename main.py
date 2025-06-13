from modules.config_generator import generate_config_files
from modules.config_applier import apply_configurations_to_switches
import os
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

def main_menu():
    while True:
        print("\n" + "=" * 50)
        print("         ANSIBLE-BASED CONFIGURATION TOOL         ")
        print("=" * 50)
        print("\n")
        print("  [1] Generate configuration files\n")
        print("  [2] Apply configurations to switches\n")
        print("  [3] Exit")
        print("\n" + "=" * 50)
        print("\n")
        choice = input("Enter your choice >>> ").strip()

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
