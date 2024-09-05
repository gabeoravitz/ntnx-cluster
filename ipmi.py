import subprocess
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed
from colorama import Fore, Style, init

# Initialize colorama for cross-platform compatibility
init(autoreset=True)

# Set your IPMI credentials here
IPMI_USER = "ADMIN"         # Username for IPMI access
IPMI_PASSWORD = "ADMIN"     # Password for IPMI access

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

def run_custom_bash_command(ip):
    """Runs the custom bash command with the current IP address, user, and password."""
    custom_command = f"ipmitool -H {ip} -U {IPMI_USER} -P {IPMI_PASSWORD} raw 0x30 0x70 0x66 0x01 0x00 0x15"
    try:
        result = subprocess.run(custom_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            return f"{Fore.GREEN}Custom slow fan mode command executed successfully on {ip}:\n{result.stdout.decode('utf-8')}"
        else:
            return f"{Fore.RED}Error executing custom slow command on {ip}: {result.stderr.decode('utf-8')}"
    except Exception as e:
        return f"{Fore.RED}Exception occurred while running custom bash command on {ip}: {str(e)}"

def get_power_status(ip):
    """Get power status using IPMI for a specific IP."""
    return run_ipmitool_command(ip, "chassis power status")

def get_cpu_temps(ip):
    """Get CPU1 and CPU2 temperatures using IPMI for a specific IP and format the output."""
    output = run_ipmitool_command(ip, "sdr type temperature")
    cpu_temps = {}
    for line in output.splitlines():
        if "CPU1" in line or "CPU 1" in line:
            cpu_temps['CPU1'] = line.strip()
        elif "CPU2" in line or "CPU 2" in line:
            cpu_temps['CPU2'] = line.strip()
    
    if not cpu_temps:
        return f"{Fore.RED}CPU1 and CPU2 temperatures not found."

    # Pretty formatting for CPU temperature display
    formatted_output = f"{Fore.CYAN}CPU Temperature Readings:\n"
    formatted_output += f"  {Fore.GREEN}{'CPU1':<10}: {cpu_temps.get('CPU1', 'Not Available')}\n"
    formatted_output += f"  {Fore.GREEN}{'CPU2':<10}: {cpu_temps.get('CPU2', 'Not Available')}\n"
    return formatted_output

def get_fan_speeds(ip):
    """Get fan speeds using IPMI for a specific IP, only showing those with RPM."""
    output = run_ipmitool_command(ip, "sdr type fan")
    fan_speeds = []
    for line in output.splitlines():
        if "RPM" in line:  # Match fan speeds that end with "RPM"
            fan_speeds.append(line.strip())
    
    if not fan_speeds:
        return f"{Fore.RED}No fan speed sensors found."

    # Pretty formatting for Fan Speed display
    formatted_output = f"{Fore.CYAN}Fan Speed Readings:\n"
    for fan in fan_speeds:
        formatted_output += f"  {Fore.GREEN}{fan}\n"
    return formatted_output

def control_power(ip, action):
    """Control server power (on, off, reset, cycle) using IPMI for a specific IP."""
    return run_ipmitool_command(ip, f"chassis power {action}")

def set_fan_mode(ip, mode):
    """Set the fan mode (auto) for a specific IP."""
    if mode == "auto":
        return run_ipmitool_command(ip, "raw 0x30 0x30 0x01 0x01")  # Automatic mode
    else:
        return f"{Fore.RED}Invalid fan mode specified."

def gather_status_in_parallel(ip_list, status_func):
    """Gather server statuses in parallel and return the results."""
    results = []
    
    with ThreadPoolExecutor(max_workers=len(ip_list)) as executor:
        # Submit all tasks to be run in parallel
        future_to_ip = {executor.submit(status_func, ip): ip for ip in ip_list}
        
        # As each task completes, retrieve its result
        for future in as_completed(future_to_ip):
            ip = future_to_ip[future]
            try:
                result = future.result()
                results.append(f"{Fore.CYAN}{ip}: {result}")
            except Exception as e:
                results.append(f"{Fore.RED}Error fetching status for {ip}: {e}")
    
    return results

def perform_action_in_parallel(ip_list, action, action_func):
    """Perform an action on all servers in parallel."""
    results = []
    with ThreadPoolExecutor(max_workers=len(ip_list)) as executor:
        future_to_ip = {executor.submit(action_func, ip, action): ip for ip in ip_list}
        for future in as_completed(future_to_ip):
            ip = future_to_ip[future]
            try:
                result = future.result()
                results.append(f"{Fore.GREEN}Result for {ip}: {result}")
            except Exception as e:
                results.append(f"{Fore.RED}Error performing action for {ip}: {e}")
    return results

def perform_fan_mode_control(ip_list):
    """Ask for fan mode (auto/slow) and set it on all servers."""
    mode = input(f"{Fore.GREEN}Enter fan mode ('auto' or 'slow'): ").strip().lower()
    if mode == 'auto':
        print(f"{Fore.CYAN}Setting fan mode to auto on all servers...")
        results = perform_action_in_parallel(ip_list, mode, set_fan_mode)
        for result in results:
            print(result)
            print("-" * 40)
    elif mode == 'slow':
        print(f"{Fore.CYAN}Setting fan mode to slow...")
        # Execute the custom bash command for 'slow' for each IP in the list
        for ip in ip_list:
            print(run_custom_bash_command(ip))
            print("-" * 40)
    else:
        print(f"{Fore.RED}Invalid fan mode input. Please enter 'auto' or 'slow'.")

def show_menu():
    """Display the action menu and return the selected option."""
    print(f"{Fore.CYAN}\nMenu:")
    print(f"{Fore.YELLOW}1. View Server Power Status")
    print(f"{Fore.YELLOW}2. View Server Temperatures (CPU1 and CPU2)")
    print(f"{Fore.YELLOW}3. View Server Fan Speeds")
    print(f"{Fore.YELLOW}4. Power Action (on, off, reset, cycle)")
    print(f"{Fore.YELLOW}5. Set Fan Mode (auto/slow)")  # Updated fan mode control
    print(f"{Fore.YELLOW}6. Exit")
    
    choice = input(f"{Fore.GREEN}Select an option: ").strip()
    return choice

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
            statuses = gather_status_in_parallel(ip_list, get_power_status)
            for status in statuses:
                print(status)
                print("-" * 40)

        elif choice == '2':
            # View server temperatures for CPU1 and CPU2
            print(f"{Fore.CYAN}Gathering CPU1 and CPU2 temperature data in parallel...")
            statuses = gather_status_in_parallel(ip_list, get_cpu_temps)
            for status in statuses:
                print(status)
                print("-" * 40)

        elif choice == '3':
            # View server fan speeds
            print(f"{Fore.CYAN}Gathering fan speed data in parallel...")
            statuses = gather_status_in_parallel(ip_list, get_fan_speeds)
            for status in statuses:
                print(status)
                print("-" * 40)

        elif choice == '4':
            # Perform power action
            action = input(f"{Fore.GREEN}Enter power action (on, off, reset, cycle): ").strip().lower()
            if action in ['on', 'off', 'reset', 'cycle']:
                print(f"{Fore.CYAN}Performing power action '{action}' on all servers...")
                results = perform_action_in_parallel(ip_list, action, control_power)
                for result in results:
                    print(result)
                    print("-" * 40)
            else:
                print(f"{Fore.RED}Invalid power action. Please try again.")

        elif choice == '5':
            # Set fan mode (auto/slow)
            perform_fan_mode_control(ip_list)

        elif choice == '6':
            print(f"{Fore.CYAN}Exiting...")
            break

        else:
            print(f"{Fore.RED}Invalid option. Please select a valid option.")

if __name__ == "__main__":
    main()