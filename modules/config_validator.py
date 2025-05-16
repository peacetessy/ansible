import yaml
import re
import ipaddress
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

def is_valid_ip(ip_str):
    """
    Validates an IP address.
    """
    try:
        ip = ipaddress.IPv4Address(ip_str)

        # Reject loopback, multicast, or reserved addresses
        if ip.is_loopback or ip.is_multicast or ip.is_reserved:
            return False

        # Reject common network or broadcast addresses
        if ip_str.endswith('.0') or ip_str.endswith('.255'):
            return False

        return True
    except ipaddress.AddressValueError:
        return False

def is_valid_vlan(vlan):
    """
    Validates a VLAN ID.
    Ensures it is an integer between 1 and 4094.
    """
    try:
        vlan = int(vlan)
        return 1 <= vlan <= 4094
    except ValueError:
        return False

def is_valid_update_period(value):
    """
    Validates the accounting update period.
    Ensures it is a positive integer.
    """
    try:
        period = int(value)
        return period > 0
    except (ValueError, TypeError):
        return False



def validate_switches_and_servers(config, secrets):
    """
    Validates that the switches and ISE servers in the configuration file match those in the secrets file.
    Handles cases where either 'global_ssh_credentials' or 'per_switch_ssh_credentials' is used.
    :param config: Configuration data containing switches and ISE servers.
    :param secrets: Secrets data containing SSH credentials and RADIUS secrets.
    :return: True if validation passes, False otherwise.
    """
    errors = []

    # Check if global SSH credentials are used
    has_global_ssh = "global_ssh_credentials" in secrets and secrets["global_ssh_credentials"]
    has_per_switch = "per_switch_credentials" in secrets and secrets["per_switch_credentials"]

    # Validate switches only if per_switch_credentials is used
    if has_per_switch:
        per_switch = secrets.get("per_switch_credentials", [])
        for i, switch in enumerate(per_switch_ssh):
            if not switch.get("hostname") or switch["hostname"].strip() == "":
                errors.append(f"#Switch {i + 1} in 'per_switch_credentials' is missing or has an empty 'hostname'.")
            if not switch.get("username") or switch["username"].strip() == "":
                errors.append(f"#Switch {i + 1} in 'per_switch_credentials' is missing or has an empty 'username'.")
            if not switch.get("ssh_password") or switch["ssh_password"].strip() == "":
                errors.append(f"#Switch {i + 1} in 'per_switch_credentials' is missing or has an empty 'password'.")

        # Stop validation if there are errors in per_switch_credentials
        if errors:
            print(Fore.RED + "\n[ERROR] Validation failed with the following issues:")
            for error in errors:
                print(Fore.RED + f"  - {error}")
            return False

        # Create sets for comparison
        config_switches = {(switch["hostname"]) for switch in config.get("switches", [])}
        secrets_switches = {(switch["hostname"]) for switch in per_switch}

        if config_switches != secrets_switches:
            missing_in_secrets = config_switches - secrets_switches
            missing_in_config = secrets_switches - config_switches

            if missing_in_secrets:
                errors.append(f"The following switches are missing in the secrets file: {', '.join([f'{host}' for host in missing_in_secrets])}")
            if missing_in_config:
                errors.append(f"The following switches are extra in the secrets file: {', '.join([f'{host}' for host in missing_in_config])}")

    elif not has_global_ssh:
        # If neither global_ssh_credentials nor per_switch_credentials is defined, it's an error
        errors.append("Neither 'global_ssh_credentials' nor 'per_switch_credentials' is defined in the secrets file.")

    # Validate ISE servers
    config_servers = {server["name"] for server in config.get("ise_servers", [])}
    secrets_servers = {secret["server_name"] for secret in secrets.get("radius_secrets", [])}

    if config_servers != secrets_servers:
        missing_in_secrets = config_servers - secrets_servers
        missing_in_config = secrets_servers - config_servers

        if missing_in_secrets:
            errors.append(f"The following ISE servers are missing in the secrets file: {', '.join(missing_in_secrets)}")
        if missing_in_config:
            errors.append(f"The following ISE servers are extra in the secrets file: {', '.join(missing_in_config)}")

    # Display errors if any
    if errors:
        print(Fore.RED + "\n[ERROR] Validation failed with the following issues:")
        for error in errors:
            print(Fore.RED + f"  - {error}")
        return False

    #print(Fore.GREEN + "[OK] Switches and ISE servers are consistent between the configuration and secrets files.")
    return True



def validate_config_file(config_path):
    """
    Validates the configuration file.
    Collects all errors and displays them at the end of the validation process.
    """
    errors = []  # List to collect all validation errors
    warnings = []  # List to collect warnings

    try:
        # Load the YAML file
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)

        # Check if the file is empty
        if not config:
            errors.append("The configuration file is empty.")
            return False

        # Required fields for validation
        required_fields = [
            'switches', 'aaa_group_name', 'ise_servers',
            'radius_test_username', 'accounting_update_period',
            'source_interface', 'radius_dead_vlan'
        ]

        # Check for missing fields
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            errors.append("Missing required fields:")
            for field in missing_fields:
                errors.append(f"  - {field}")

        # Check for empty fields
        empty_fields = [field for field in required_fields if field in config and not config[field]]
        if empty_fields:
            errors.append("The following fields are empty:")
            for field in empty_fields:
                errors.append(f"  - {field}")

        # Check for unnecessary fields
        extra_fields = [field for field in config if field not in required_fields]
        if extra_fields:
            warnings.append("Unnecessary fields detected (these will be ignored):")
            for field in extra_fields:
                warnings.append(f"  - {field}")

        # Validate switches
        for i, switch in enumerate(config.get("switches", [])):
            if "hostname" not in switch or not switch["hostname"].strip():
                errors.append(f"Switch #{i + 1} is missing a 'hostname'.")
            if "management_ip" not in switch or not is_valid_ip(switch["management_ip"]):
                errors.append(f"Switch #{i + 1} has an invalid or missing 'management_ip'.")

        # Validate ISE/RADIUS servers
        for i, server in enumerate(config.get("ise_servers", [])):
            if "name" not in server or not server["name"].strip():
                errors.append(f"ISE server #{i + 1} is missing a 'name'.")
            if "ip" not in server or not is_valid_ip(server["ip"]):
                errors.append(f"ISE server #{i + 1} has an invalid or missing 'ip'.")

        # Validate VLANs
        if "radius_dead_vlan" in config and not is_valid_vlan(config["radius_dead_vlan"]):
            errors.append("'radius_dead_vlan' must be a valid VLAN ID (1-4094).")

        # Validate accounting update period
        if "accounting_update_period" in config and not is_valid_update_period(config["accounting_update_period"]):
            errors.append("'accounting_update_period' must be a positive integer.")

        # Display warnings
        if warnings:
            print(Fore.YELLOW + "\n[WARNING] The following warnings were detected in :" + config_path)
            for warning in warnings:
                print(Fore.YELLOW + f" {warning}")

        # Display all errors at the end
        if errors:
            print(Fore.RED + "\n[ERROR] Validation failed with the following issues in :" + config_path)
            for error in errors:
                print(Fore.RED + f" {error}")
            return False

        # If all validations pass
        print(Fore.GREEN + "\n[OK] Configuration file is valid.")
        return True

    except yaml.YAMLError as e:
        print(Fore.RED + f"\n[ERROR] YAML syntax error: {e}")
        return False
    except FileNotFoundError:
        print(Fore.RED + "\n[ERROR] Configuration file not found.")
        return False
    except Exception as e:
        print(Fore.RED + f"\n[ERROR] Unexpected error during validation: {e}")
        return False

def validate_secrets_file_ssh(secrets_path):
    """
    Validates the sensitive data file for SSH credentials.
    Ensures that only one of 'global_ssh_credentials' or 'per_switch_ssh_credentials' is used.
    Collects all errors and displays them at the end of the validation process.
    """
    errors = []  # List to collect all errors

    try:
        # Load the YAML file
        with open(secrets_path, 'r') as file:
            secrets = yaml.safe_load(file)

        if not secrets:
            errors.append("The sensitive data file is empty.")
            return False

        # Check if both SSH blocks are filled
        has_global_ssh = "global_ssh_credentials" in secrets and secrets["global_ssh_credentials"]
        has_per_switch = "per_switch_credentials" in secrets and secrets["per_switch_credentials"]

        if has_global_ssh and has_per_switch:
            errors.append("Both 'global_ssh_credentials' and 'per_switch_credentials' are defined.")
            errors.append("Please choose only one method for SSH authentication.")

        # Validate global_ssh_credentials
        if has_global_ssh:
            global_ssh = secrets["global_ssh_credentials"]
            if not global_ssh.get("username"):
                errors.append("'global_ssh_credentials' is missing 'username'.")
            if not global_ssh.get("password"):
                errors.append("'global_ssh_credentials' is missing 'password'.")

        # Validate per_switch__credentials
        if has_per_switch:
            per_switch = secrets["per_switch_credentials"]
            if not isinstance(per_switch, list) or len(per_switch) == 0:
                errors.append("'per_switch_credentials' must be a non-empty list.")
            else:
                for i, switch_cred in enumerate(per_switch):
                    if not switch_cred.get("hostname"):
                        errors.append(f"Switch #{i + 1} in 'per_switch_credentials' is missing 'hostname'.")
                    if not switch_cred.get("username"):
                        errors.append(f"Switch #{i + 1} in 'per_switch_credentials' is missing 'username'.")
                    if not switch_cred.get("password"):
                        errors.append(f"Switch #{i + 1} in 'per_switch_credentials' is missing 'password'.")

        # Checks for the existence of enable passwords
        has_global_enable = secrets.get("global_enable_password")


        # Validate global_enable_password
        if not has_global_enable:
            errors.append("'global_enable_password' is missing'.")

        # Check radius_test_password
        if "radius_test_password" not in secrets or not secrets["radius_test_password"]:
            errors.append("Missing or empty 'radius_test_password'.")

        # Display all errors at the end
        if errors:
            print(Fore.RED + "\n[ERROR] Validation failed with the following issues:")
            for error in errors:
                print(Fore.RED + f"  - {error}")
            return False

        # If all validations pass
        print(Fore.GREEN + "\n[OK] Sensitive data file is valid.")
        return True

    except yaml.YAMLError as e:
        print(Fore.RED + f"\n[ERROR] YAML syntax error in sensitive data file: {e}")
        return False
    except FileNotFoundError:
        print(Fore.RED + "\n[ERROR] Sensitive data file not found.")
        return False
    except Exception as e:
        print(Fore.RED + f"\n[ERROR] Unexpected error during validation of sensitive data file: {e}")
        return False

        
def validate_secrets_file_tacacs_plus(secrets_path):
    """
    Validates the sensitive data file for TACACS+ credentials.
    Ensures that the required fields for TACACS+ are present and valid.
    """
    errors = []  # List to collect all errors

    try:
        # Load the YAML file
        with open(secrets_path, 'r') as file:
            secrets = yaml.safe_load(file)

        if not secrets:
            errors.append("The sensitive data file is empty.")
            return False

        # Required fields for TACACS+
        required_fields = ["tacacs_username", "tacacs_password"]

        # Check for missing fields
        for field in required_fields:
            if field not in secrets or not secrets[field]:
                errors.append(f"Missing or empty field: '{field}'.")

        # Display all errors at the end
        if errors:
            print(Fore.RED + "\n[ERROR] Validation failed with the following issues in :" + secrets_path)
            for error in errors:
                print(Fore.RED + f"  - {error}")
            return False

        # If all validations pass
        print(Fore.GREEN + "\n[OK] Sensitive data file is valid.")
        return True

    except yaml.YAMLError as e:
        print(Fore.RED + f"\n[ERROR] YAML syntax error in sensitive data file: {e}")
        return False
    except FileNotFoundError:
        print(Fore.RED + "\n[ERROR] Sensitive data file not found.")
        return False
    except Exception as e:
        print(Fore.RED + f"\n[ERROR] Unexpected error during validation of sensitive data file: {e}")
        return False
