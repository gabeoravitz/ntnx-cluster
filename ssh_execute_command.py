import pexpect
import sys

def ssh_execute_command(ip, user, password, command, send_input=None):
    # Create the ssh command using pexpect to handle interactive input
    ssh_command = f"ssh {user}@{ip} {command}"

    # Start the ssh session
    child = pexpect.spawn(ssh_command)

    # Look for the password prompt and provide the password
    child.expect("password:")
    child.sendline(password)

    if send_input:
        # Wait for the cluster stop confirmation prompt and send "I agree"
        child.expect("I agree/[N]:")
        child.sendline(send_input)

    # Wait for the process to finish
    child.expect(pexpect.EOF)
    output = child.before.decode()

    # Close the connection
    child.close()

    return output

if __name__ == "__main__":
    ip = sys.argv[1]
    user = sys.argv[2]
    password = sys.argv[3]
    command = sys.argv[4]
    send_input = sys.argv[5] if len(sys.argv) > 5 else None

    output = ssh_execute_command(ip, user, password, command, send_input)
    print(output)
