import paramiko
import time
import sys 

def ssh_execute_command(ip, user, password, command, send_input=None):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    # Connect to the remote server
    ssh.connect(ip, username=user, password=password)
    
    # Open an interactive shell session
    shell = ssh.invoke_shell()

    # Source the bash profile
    shell.send("source /home/nutanix/.bash_profile\n")
    time.sleep(1)  # Give it some time to source the profile

    # Execute the main command (like cluster stop or acli commands)
    shell.send(f"{command}\n")
    
    # If we need to send input (like "I agree"), wait 5 seconds before sending it
    if send_input:
        time.sleep(5)
        shell.send(f"{send_input}\n")

    # Capture the final output, but minimize displayed output
    time.sleep(2)  # Give it time to finish execution
    output = shell.recv(10000).decode("utf-8")

    # Close the connection
    ssh.close()

    # Optionally print a minimal output or return it
    return output.strip()

if __name__ == "__main__":
    ip = sys.argv[1]
    user = sys.argv[2]
    password = sys.argv[3]
    command = sys.argv[4]
    send_input = sys.argv[5] if len(sys.argv) > 5 else None

    output = ssh_execute_command(ip, user, password, command, send_input)
    
    # Display output only if necessary
    if output:
        print(output)
