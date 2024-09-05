import subprocess
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed

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
            return f"Error on {ip}: {result.stderr.decode('utf-8')}"
    except Exception as e:
        return f"Exception occurred on {ip}: {str(e)}"

def get_power_status(ip):
    """Get power status using IPMI for a specific IP."""
    return run_ipmitool_command(ip, "chassis power status")

def get_cpu_temps(ip):
    """Get CPU1 and CPU2 temperatures using IPMI for a specific IP."""
    output = run_ipmitool_command(ip, "sdr type temperature")
    cpu_temps = []
    for line in output.splitlines():
        if "CPU1" in line or "CPU 1" in line:
            cpu_temps.append(f"CPU1: {line.strip()}")
        elif "CPU2" in line or "CPU 2" in line:
            cpu_temps.append(f"CPU2: {line.strip()}")
    if cpu_temps:
        return "\n".join(cpu_temps)
    return "CPU1 and CPU2 temperatures not found."

def get_fan_speeds(ip):
    """Get fan speeds using IPMI for a specific IP."""
    output = run_ipmitool_command(ip, "sdr type fan")
    fan_speeds = []
    for line in output.splitlines():
        if "Fan" in line or "FAN" in line or "FAN" in line:  # Matching common fan sensor names
            fan_speeds.append(line.strip())
    if fan_speeds:
        return "\n".join(fan_speeds)
    return "No fan speed sensors found."

def control_power(ip, action):
    """Control server power (on, off, reset, cycle) using IPMI for a specific IP."""
    return run_ipmitool_command(ip, f"chassis power {action}")

def percentage_to_hex(speed_percentage):
    """Convert fan speed percentage (0-100%) to a hexadecimal value for IPMI."""
    if 0 <= speed_percentage <= 100:
        hex_value = hex(int((speed_percentage / 100) * 255)).split('x')[-1]
        return f"0x{hex_value.zfill(2)}"  # Ensure two digits in hexadecimal
    else:
        raise ValueError("Fan speed must be between 0 and 100 percent.")

def set_fan_speed(ip, speed_percentage):
    """Set the fan speed for a specific IP (using raw command with percentage)."""
    try:
        hex_speed = percentage_to_hex(speed_percentage)
        return run_ipmitool_command(ip, f"raw 0x30 0x30 0x02 0xff {hex_speed}")
    except ValueError as e:
        return str(e)

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
                results.append(f"{ip}: {result}")
            except Exception as e:
                results.append(f"Error fetching status for {ip}: {e}")
    
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
                results.append(f"Result for {ip}: {result}")
            except Exception as e:
                results.append(f"Error performing action for {ip}: {e}")
    return results

def show_menu():
    """Display the action menu and return the selected option."""
    print("\nMenu:")
    print("1. View Server Power Status")
    print("2. View Server Temperatures (CPU1 and CPU2)")
    print("3. View Server Fan Speeds")
    print("4. Power Action (on, off, reset, cycle)")
    print("5. Set Fan Speed (percentage)")
    print("6. Exit")
    
    choice = input("Select an option: ").strip()
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
    ip_range_str = input("Enter the IP range (e.g., 192.168.1.100-105, 192.168.1.108-110): ")
    
    try:
        ip_list = get_ip_range_from_string(ip_range_str)
        if not ip_list:
            print("No valid IP addresses found in the range.")
            return
    except Exception as e:
        print(f"Error parsing IP range: {e}")
        return

    while True:
        choice = show_menu()

        if choice == '1':
            # View server power status
            print("Gathering power status in parallel...")
            statuses = gather_status_in_parallel(ip_list, get_power_status)
            for status in statuses:
                print(status)
                print("-" * 40)

        elif choice == '2':
            # View server temperatures for CPU1 and CPU2
            print("Gathering CPU1 and CPU2 temperature data in parallel...")
            statuses = gather_status_in_parallel(ip_list, get_cpu_temps)
            for status in statuses:
                print(status)
                print("-" * 40)

        elif choice == '3':
            # View server fan speeds
            print("Gathering fan speed data in parallel...")
            statuses = gather_status_in_parallel(ip_list, get_fan_speeds)
            for status in statuses:
                print(status)
                print("-" * 40)

        elif choice == '4':
            # Perform power action
            action = input("Enter power action (on, off, reset, cycle): ").strip().lower()
            if action in ['on', 'off', 'reset', 'cycle']:
                print(f"Performing power action '{action}' on all servers...")
                results = perform_action_in_parallel(ip_list, action, control_power)
                for result in results:
                    print(result)
                    print("-" * 40)
            else:
                print("Invalid power action. Please try again.")

        elif choice == '5':
            # Set fan speed
            try:
                speed_percentage = int(input("Enter fan speed as a percentage (0-100): ").strip())
                if 0 <= speed_percentage <= 100:
                    print(f"Setting fan speed to {speed_percentage}% on all servers...")
                    results = perform_action_in_parallel(ip_list, speed_percentage, set_fan_speed)
                    for result in results:
                        print(result)
                        print("-" * 40)
                else:
                    print("Fan speed must be between 0 and 100 percent. Please try again.")
            except ValueError:
                print("Invalid fan speed input. Please enter a number.")

        elif choice == '6':
            print("Exiting...")
            break

        else:
            print("Invalid option. Please select a valid option.")

if __name__ == "__main__":
    main()
