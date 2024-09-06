import os
import time

CVM_NODES = [
    {"ip": "192.168.1.184"},
    {"ip": "192.168.1.185"},
    {"ip": "192.168.1.186"},
]

def is_ping_successful(ip):
    response = os.system(f"ping -c 1 -W 1 {ip} > /dev/null 2>&1")
    return response == 0

def wait_for_cvm_ping():
    for cvm in CVM_NODES:
        while not is_ping_successful(cvm['ip']):
            time.sleep(10)
    print("success")

if __name__ == "__main__":
    wait_for_cvm_ping()
