#!/usr/bin/expect

# Define variables
set CVM_IP "192.168.1.184"   ;# Replace with the correct CVM IP
set USERNAME "nutanix"
set PASSWORD "nutanix/4u"

# Set timeout for expect commands
set timeout 60

# Start SSH session and run the cluster stop command
spawn ssh -o StrictHostKeyChecking=no $USERNAME@$CVM_IP "/usr/local/nutanix/cluster/bin/cluster stop"

# Expect the password prompt and send the password
expect "password:"
send "$PASSWORD\r"

# Wait 10 seconds to allow the system to prompt for confirmation
sleep 10

# Send "I agree" and press Enter
send "I agree\r"

# Wait for the process to complete
expect eof

# Print completion message
puts "Cluster stop initiated and 'I agree' sent after 10-second delay."