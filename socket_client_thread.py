# -*- coding:utf-8 -*-
# Kayla Laufer 

import socket
import select
import sys

ip_port = ('127.0.0.1', 9999)

s = socket.socket()
s.connect(ip_port)

# Set the socket to non-blocking mode to handle server responses and user input concurrently
s.setblocking(False)

# Set a 1-second timeout to periodically check for incoming server messages
s.settimeout(1)  # Timeout of 1 second for recv()

# Refresh the input prompt for the user to input messages
def print_prompt():
    sys.stdout.write("\rinput msg: ")
    sys.stdout.flush()

try:
    while True:
        # Check for server messages and user input without blocking using select
        ready_to_read, _, _ = select.select([s, sys.stdin], [], [])
        if s in ready_to_read:
            try:
                server_reply = s.recv(1024).decode()
                if server_reply:
                    print(f"\n{server_reply}")
                else:
                    # Handle server disconnection if an empty response is received
                    print("Server has disconnected.")
                    break
            except ConnectionError:
                # Server has forcibly closed the connection.
                print("Connection closed by server.")
                break
            print_prompt()

        # Process user input and send it to the server if available
        if sys.stdin in ready_to_read:
            inp = input().strip()

            # Skip processing if user input is empty
            if not inp:
                continue
            s.sendall(inp.encode())

            # Send 'exit' command to inform the server of disconnection
            if inp == "exit":
                server_reply = s.recv(1024).decode()
                print(server_reply)
                break

            server_reply = s.recv(1024).decode()
            print(server_reply)
            print_prompt()

except KeyboardInterrupt:
    # Gracefully handle user interruption with Ctrl+C by sending an 'exit' command
    print("\nClient shutting down...")
    try:
        s.sendall("exit".encode())
    except Exception:
        pass  # Ignore any errors if the server is already disconnected
s.close()