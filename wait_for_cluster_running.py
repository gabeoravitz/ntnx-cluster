from ssh_execute_command import ssh_execute_command
import re
import time

CVM_NODES = [{"ip": "192.168.1.184", "user": "nutanix", "password": "nutanix/4u"}]

def check_services_up(output):
    services_up = True
    service_pattern = re.compile(r"(\w+)\s+(\d+)\s+(UP|DOWN)")
    
    for line in output.splitlines():
        match = service_pattern.search(line)
        if match:
            service_name, pid, status = match.groups()
            if status != "UP" or not pid.isdigit():
                services_up = False
                break  # Stop checking further, one service is not UP
    
    return services_up

def wait_for_cluster_running():
    cvm = CVM_NODES[0]
    while True:
        # Use the updated full path for the cluster command
        output, errors = ssh_execute_command(cvm['ip'], cvm['user'], cvm['password'], "/usr/local/nutanix/cluster/bin/cluster status")
        
        # Check for errors
        if errors:
            print(f"Error running cluster status: {errors}")
            break
        
        # Check if all services are UP
        if check_services_up(output):
            print("Cluster Running")
            break
        
        time.sleep(30)

if __name__ == "__main__":
    wait_for_cluster_running()
