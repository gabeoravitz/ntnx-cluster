import subprocess
import ipaddress
import os  # For clearing the screen
import sys
import termios
import tty
import select  # For non-blocking input checking
from colorama import Fore, Style, init
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Initialize colorama for cross-platform compatibility
init(autoreset=True)

# Set your IPMI credentials here
IPMI_USER = "admin"         # Username for IPMI access
IPMI_PASSWORD = "admin"     # Password for IPMI access

PASTEL_PINK = "\033[38;5;207m"  # Define pastel pink color
RESET_COLOR = "\033[0m"  # Reset to default terminal color

def run_ipmitool_command(ip, command):
    """Runs an ipmitool command for a specific IP address and returns the output."""
    try:
        full_command = f"ipmitool -I lanplus -H {ip} -U {IPMI_USER} -P {IPMI_PASSWORD} {command}"
        result = subprocess.run(full_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            return result.stdout.decode('utf-8')
        else:
            return f"{Fore.RED}Error on {ip}: {result.stderr.decode('utf-8')}"
    except Exception as e:
        return f"{Fore.RED}Exception occurred on {ip}: {str(e)}"

def get_temperature_color(temp_value):
    """Return a color based on the temperature range."""
    return PASTEL_PINK  # Use pastel pink for all temperatures

def parse_temperature(temp_str):
    """Extract temperature value from a string using regex and convert to int."""
    temp_match = re.search(r"(\d+)\s*degrees", temp_str)
    if temp_match:
        try:
            return int(temp_match.group(1))  # Return temperature value
        except (IndexError, ValueError):
            return None
    return None

def parse_fan_speed(fan_str):
    """Extract fan speed value from a string using regex and convert to int."""
    fan_match = re.search(r"(\d+)\s*RPM", fan_str)
    if fan_match:
        try:
            return int(fan_match.group(1))  # Return fan speed value
        except (IndexError, ValueError):
            return None
    return None

def check_power_status(ip):
    """Check if the node is powered on or off."""
    power_status = run_ipmitool_command(ip, "chassis power status")
    if "off" in power_status.lower():
        return False
    return True

def get_cpu_temps(ip):
    """Get CPU1 and CPU2 temperatures using IPMI for a specific IP and format the output."""
    if not check_power_status(ip):
        return f"{Fore.RED}Node Powered Off"

    output = run_ipmitool_command(ip, "sdr type temperature")
    cpu_temps = {}
    for line in output.splitlines():
        if "CPU1" in line or "CPU 1" in line:
            cpu_temps['CPU1'] = line.strip()
        elif "CPU2" in line or "CPU 2" in line:
            cpu_temps['CPU2'] = line.strip()
    
    if not cpu_temps:
        return f"{Fore.RED}CPU1 and CPU2 temperatures not found."

    # Simplified formatting for CPU temperature display with pastel pink
    formatted_output = ""
    
    for cpu_label, temp_info in cpu_temps.items():
        temp_value = parse_temperature(temp_info)
        if temp_value is not None:
            temp_color = get_temperature_color(temp_value)
            formatted_output += f"{Fore.GREEN}{cpu_label:<10}: {temp_color}{temp_value} Celsius{RESET_COLOR}\n"
        else:
            formatted_output += f"{Fore.RED}{cpu_label:<10}: No Valid Temp\n"
    
    return formatted_output

def get_fan_speeds(ip):
    """Get FAN1 and FAN2 fan speeds using IPMI for a specific IP and format the output."""
    if not check_power_status(ip):
        return f"{Fore.RED}Node Powered Off"

    output = run_ipmitool_command(ip, "sdr type fan")
    fan_speeds = {}
    for line in output.splitlines():
        if "FAN1" in line or "Fan 1" in line:
            fan_speeds['FAN1'] = line.strip()
        elif "FAN2" in line or "Fan 2" in line:
            fan_speeds['FAN2'] = line.strip()
    
    if not fan_speeds:
        return f"{Fore.RED}FAN1 and FAN2 fan speeds not found."

    # Simplified formatting for Fan Speed display with pastel pink
    formatted_output = ""
    
    for fan_label, fan_info in fan_speeds.items():
        fan_speed = parse_fan_speed(fan_info)
        if fan_speed is not None:
            formatted_output += f"{Fore.GREEN}{fan_label:<10}: {PASTEL_PINK}{fan_speed} RPM{RESET_COLOR}\n"
        else:
            formatted_output += f"{Fore.RED}{fan_label:<10}: No Valid Fan Speed\n"
    
    return formatted_output

def power_action(ip, action):
    """Perform power actions (on, off, reset, cycle) on a specific server."""
    power_commands = {
        'on': 'chassis power on',
        'off': 'chassis power off',
        'reset': 'chassis power reset',
        'cycle': 'chassis power cycle'
    }
    
    if action in power_commands:
        result = run_ipmitool_command(ip, power_commands[action])
        return result.strip()
    else:
        return f"{Fore.RED}Invalid power action"

def perform_power_action(ip_list, action):
    """Perform the selected power action on all servers in parallel."""
    results = fetch_data_in_parallel(ip_list, lambda ip: power_action(ip, action))
    for ip, result in results.items():
        print(f"{Fore.CYAN}{ip}: {result}")
        print("-" * 40)

def fetch_data_in_parallel(ip_list, status_func):
    """Fetch data (temperature, fan speeds, power) from servers in parallel."""
    results = {}
    with ThreadPoolExecutor(max_workers=len(ip_list)) as executor:
        futures = {executor.submit(status_func, ip): ip for ip in ip_list}
        for future in as_completed(futures):
            ip = futures[future]
            try:
                results[ip] = future.result()
            except Exception as e:
                results[ip] = f"{Fore.RED}Error occurred: {str(e)}"
    return results

def display_real_time_output(ip_list, status_func, description):
    """Displays real-time output for CPU temperatures or fan speeds, refreshing every 2 seconds."""
    previous_lines = 0

    # Sort the IP list by the last octet for consistent output order
    sorted_ip_list = sorted(ip_list, key=lambda ip: int(ip.split('.')[-1]))

    # Print the static header once
    print(f"{Fore.CYAN}Real-Time {description} Readings\n")
    print(f"Press CTRL-C to return to the menu.\n")

    try:
        while True:
            # Move the cursor up to the previous data block and overwrite it
            if previous_lines > 0:
                sys.stdout.write(f"\033[{previous_lines}F")  # Move cursor to the top of previous output
            
            # Fetch data in parallel
            results = fetch_data_in_parallel(sorted_ip_list, status_func)
            
            # Print new output and count the number of lines printed
            previous_lines = 0  # Reset line counter
            for ip in sorted_ip_list:  # Ensure the order is maintained during output
                result = results[ip]  # Print the result in the same order as sorted IPs
                sys.stdout.write(f"{Fore.CYAN}{ip}:\n")
                sys.stdout.write(result + "\n")
                sys.stdout.write("-" * 40 + "\n")
                previous_lines += result.count('\n') + 3  # Each block has 3 lines (header, content, divider)
            
            time.sleep(2)  # Refresh every 2 seconds

    except KeyboardInterrupt:
        pass  # Handle CTRL-C gracefully

    # Clear screen before returning to the menu
    os.system('clear')

def show_menu():
    """Display the action menu and return the selected option."""
    print(f"{Fore.CYAN}\nMenu:")
    print(f"{Fore.YELLOW}1. View Server Power Status")
    print(f"{Fore.YELLOW}2. View Real-Time Server Temperatures (CPU1 and CPU2)")
    print(f"{Fore.YELLOW}3. View Real-Time Server Fan Speeds")
    print(f"{Fore.YELLOW}4. Power Action (on, off, reset, cycle)")
    print(f"{Fore.YELLOW}5. Exit")
    
    choice = input(f"{Fore.GREEN}Select an option: ").strip()
    return choice

def main():
    ip_range_str = input(f"{Fore.GREEN}Enter the IP range (e.g., 192.168.1.100-105, 192.168.1.108-110): ")
    
    try:
        ip_list = get_ip_range_from_string(ip_range_str)
        if not ip_list:
            print(f"{Fore.RED}No valid IP addresses found in the range.")
            return
    except Exception as e:
        print(f"{Fore.RED}Error parsing IP range: {e}")
        return

    while True:
        choice = show_menu()

        if choice == '1':
            # View server power status
            print(f"{Fore.CYAN}Gathering power status in parallel...")
            results = fetch_data_in_parallel(ip_list, check_power_status)
            for ip, result in results.items():
                status = "ON" if result else "OFF"
                print(f"{Fore.CYAN}{ip}: {status}")
                print("-" * 40)

        elif choice == '2':
            # View real-time server temperatures for CPU1 and CPU2 using a Python loop
            display_real_time_output(ip_list, get_cpu_temps, "CPU Temperature")

        elif choice == '3':
            # View real-time server fan speeds using a Python loop
            display_real_time_output(ip_list, get_fan_speeds, "Fan Speed")

        elif choice == '4':
            # Power action menu
            print(f"{Fore.YELLOW}Select a power action:")
            print(f"{Fore.CYAN}1. Power On")
            print(f"{Fore.CYAN}2. Power Off")
            print(f"{Fore.CYAN}3. Power Reset")
            print(f"{Fore.CYAN}4. Power Cycle")
            power_choice = input(f"{Fore.GREEN}Select an option: ").strip()

            power_actions = {
                '1': 'on',
                '2': 'off',
                '3': 'reset',
                '4': 'cycle'
            }

            if power_choice in power_actions:
                perform_power_action(ip_list, power_actions[power_choice])
            else:
                print(f"{Fore.RED}Invalid option.")

        elif choice == '5':
            print(f"{Fore.CYAN}Exiting...")
            break

        else:
            print(f"{Fore.RED}Invalid option. Please select a valid option.")

def get_ip_range_from_string(ip_range_str):
    """Parse an IP range string and return a list of IP addresses."""
    ip_list = []
    ranges = ip_range_str.split(',')
    
    for ip_range in ranges:
        ip_range = ip_range.strip()  # Remove leading/trailing spaces
        if '-' in ip_range:
            start_ip, end_ip = ip_range.split('-')
            start_ip = ipaddress.IPv4Address(start_ip.strip())
            if '.' not in end_ip:
                end_ip = ipaddress.IPv4Address(f"{start_ip.exploded.rsplit('.', 1)[0]}.{end_ip.strip()}")
            else:
                end_ip = ipaddress.IPv4Address(end_ip.strip())
            for ip in range(int(start_ip), int(end_ip) + 1):
                ip_list.append(str(ipaddress.IPv4Address(ip)))
        else:
            ip_list.append(ip_range.strip())
    
    return ip_list

if __name__ == "__main__":
    main()
