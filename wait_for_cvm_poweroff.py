from ssh_execute_command import ssh_execute_command
import time

AHV_NODES = [
    {"ip": "192.168.1.180", "user": "root", "password": "nutanix/4u"},
    {"ip": "192.168.1.181", "user": "root", "password": "nutanix/4u"},
    {"ip": "192.168.1.182", "user": "root", "password": "nutanix/4u"},
]

def wait_for_cvm_poweroff():
    for ahv_node in AHV_NODES:
        while True:
            output, _ = ssh_execute_command(ahv_node['ip'], ahv_node['user'], ahv_node['password'], "virsh list --all")
            if "shut off" in output:
                print("success")
                break
            time.sleep(30)

if __name__ == "__main__":
    wait_for_cvm_poweroff()
