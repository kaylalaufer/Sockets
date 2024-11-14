# -*- coding:utf-8 -*-
# Kayla Laufer 

import socket
import threading
import signal

client_id_counter = 0
client_list = {}
lock = threading.Lock()
history = {}

class ClientNotFoundError(Exception):
    """Exception raised when the target client is not found."""
    pass

def link_handler(link, client, client_id):
    link.sendall(f"Your ID is {client_id}".encode())
    print('server start to receiving msg from [%s:%s]....' % (client[0], client[1]))
    
    while not shutdown_event.is_set():
        try:
            client_data = link.recv(1024).decode()
            if not client_data:
                break
            if client_data == "exit":
                with lock:
                    link.sendall('Goodbye'.encode())
                    del client_list[client_id]  # Remove the client from the client list to update active clients
                break
            elif client_data == "list":
                id_list = ""
                with lock:
                    for key in client_list.keys():
                        id_list += str(key) + " "
                link.sendall(id_list.encode())
            elif client_data.startswith("Forward"):
                forward(client_data, link, client_id)
            elif client_data.startswith("history"):
                history_command(client_data, link, client_id)
            else:
                print('client from [%s:%s] send a msg：%s' % (client[0], client[1], client_data))
                link.sendall('server had received your msg'.encode())
        except (ConnectionError, OSError):
            break
        except ConnectionResetError:
            with lock:
                del client_list[client_id]  # delete the client from the client list
            break

    link.close()

    # After the client disconnects, check if it's the last one
    with lock:
        if len(client_list) == 0:
            print('No more clients, shutting down the server.')
            shutdown_event.set()  # Signal shutdown if no clients are left

def forward(client_data, link, client_id):
    try:
        # Extract target client ID and message content
        _, target_id_str, message = client_data.split(' ', 2)
        target_id = int(target_id_str)

        # Check if message is empty
        if not message.strip():
            link.sendall("Message cannot be empty.".encode())
            return

        formatted_message = f"{client_id}: {message}"

        # Use a lock to ensure thread-safe updates to history and client list
        with lock:
            # Check if the target client exists in the client list
            if target_id not in client_list:
                raise ClientNotFoundError(f"Client {target_id} not found.")

            # Get the conversation history key
            client_pair = (min(client_id, target_id), max(client_id, target_id))
            
            # Initialize history if not already present
            if client_pair not in history:
                history[client_pair] = []

            # Add the message to the history
            history[client_pair].append(formatted_message)

            # Get the target client connection
            target_conn, target_addr = client_list[target_id]

        # Send the message to the target client
        target_conn.sendall(formatted_message.encode())
        print(f"Message sent to client {target_id}: {formatted_message}")

        # Send acknowledgment to the sender
        link.sendall(f"Message forwarded to client {target_id}".encode())

        # Display the conversation history
        print(history[client_pair])

    except ClientNotFoundError as e:
        link.sendall(str(e).encode())
        print(str(e))

    except ValueError:
        link.sendall("Invalid command format. Use: Forward <ID> <message>".encode())
        print("Invalid command format received.")

    except Exception as e:
        print(f"Error handling 'Forward' command: {e}")
        link.sendall(f"An error occurred: {str(e)}".encode())


def history_command(client_data, link, client_id):
    try:
        # Extract the target client ID from the 'history' command
        _, target_id_str = client_data.split()  # Splits into ['history', 'ID']
        target_id = int(target_id_str)  # Converts ID to integer 

        # Use a lock to ensure thread-safe updates to history and client list
        with lock:
            if target_id == client_id:
                raise ClientNotFoundError(f"Current and target client are the same.")

            # Get the conversation history key
            client_pair = (min(client_id, target_id), max(client_id, target_id))

            # Fetch the conversation history
            history_convo = history.get(client_pair)

            if not history_convo:
                raise ClientNotFoundError(f"History with client {target_id} not found.")

        
        # Send each message in the conversation back to the client
        for message in history_convo:
            link.sendall((message + "\n").encode())
    except ClientNotFoundError as e:
        link.sendall(str(e).encode())
        print(str(e))
    except ValueError:
        link.sendall("Invalid command format. Use: history <ID>".encode())
        print("Invalid command format received.")

def shutdown_server(signal_received, frame):
    print("\nServer is shutting down...")
    with lock:
        for client_id, (link, _) in client_list.items():
            try:
                link.sendall("Server is shutting down. Goodbye!".encode())
                link.close()
            except Exception:
                pass
        client_list.clear()
    shutdown_event.set()  # Set the shutdown event to stop the server loop
        

signal.signal(signal.SIGINT, shutdown_server)
# Create a shutdown event to stop the server when all clients disconnect
shutdown_event = threading.Event()

ip_port = ('127.0.0.1', 9999)
sk = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # TCP socket
sk.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow address reuse
sk.bind(ip_port)
sk.listen(5)

# Set a timeout to allow periodic shutdown checks, avoiding blocking
sk.settimeout(1)

print('start socket server，waiting for clients...')

# Main loop to accept and manage client connections until shutdown is triggered
while not shutdown_event.is_set():
    try:
        conn, address = sk.accept()

        with lock:
            client_id_counter += 1
            client_id = client_id_counter
            client_list[client_id] = (conn, address)
        print('create a new thread to receive msg from [%s:%s]' % (address[0], address[1]))
        t = threading.Thread(target=link_handler, args=(conn, address, client_id))
        t.start()

    except socket.timeout:
        continue  # Continue the loop and periodically check for shutdown_event

# Close the server socket
sk.close()
print('Server gracefully shutdown.')
