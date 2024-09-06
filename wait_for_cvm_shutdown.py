import paramiko
import sys
import time

def ssh_execute_command(ip, user, password, command):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    # Connect to the remote server
    ssh.connect(ip, username=user, password=password)
    
    # Open an interactive shell session
    shell = ssh.invoke_shell()

    # Source the bash profile
    shell.send("source /home/nutanix/.bash_profile\n")
    time.sleep(1)  # Give it some time to source the profile

    # Execute the main command
    shell.send(f"{command}\n")

    # Capture the final output
    time.sleep(2)  # Give it time to finish execution
    output = shell.recv(10000).decode("utf-8")

    # Close the connection
    ssh.close()

    return output.strip()

def wait_for_cvm_shutdown(ahv_ip, user, password, cvm_name):
    while True:
        # Run virsh list --all on AHV node to check CVM state
        output = ssh_execute_command(ahv_ip, user, password, "virsh list --all")
        
        if f"{cvm_name} shut off" in output:
            print(f"{cvm_name} has powered off.")
            break
        else:
            print(f"{cvm_name} is still running. Waiting for shutdown...")
            time.sleep(10)  # Wait for 10 seconds before checking again

if __name__ == "__main__":
    action = sys.argv[1]

    if action == "check_cvm":
        ahv_ip = sys.argv[2]  # AHV IP address
        user = sys.argv[3]     # AHV user (usually "root")
        password = sys.argv[4] # AHV password
        cvm_name = sys.argv[5] # CVM name to check for shutdown

        wait_for_cvm_shutdown(ahv_ip, user, password, cvm_name)

