import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

IPMI_NODES = [
    {"ip": "192.168.1.224", "user": "ADMIN", "password": "ADMIN"},
    {"ip": "192.168.1.225", "user": "ADMIN", "password": "ADMIN"},
    {"ip": "192.168.1.226", "user": "ADMIN", "password": "ADMIN"},
]

def run_ipmitool_command(ip, user, password, command):
    full_command = f"ipmitool -I lanplus -H {ip} -U {user} -P {password} {command}"
    result = subprocess.run(full_command, shell=True, capture_output=True, text=True)
    return result.returncode == 0

def power_on_nodes():
    with ThreadPoolExecutor(max_workers=len(IPMI_NODES)) as executor:
        futures = [executor.submit(run_ipmitool_command, node['ip'], node['user'], node['password'], "chassis power on") for node in IPMI_NODES]
        for future in futures:
            if not future.result():
                print("failure")
                return
    print("success")

if __name__ == "__main__":
    power_on_nodes()
