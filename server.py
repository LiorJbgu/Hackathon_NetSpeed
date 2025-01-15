import socket
import struct
import threading
import time
from colorama import Fore, Style

# Constants
MAGIC_COOKIE = 0xabcddcba
OFFER_TYPE = 0x2
REQUEST_TYPE = 0x3
PAYLOAD_TYPE = 0x4
UDP_BROADCAST_PORT = 13117  # For broadcasting offers
UDP_LISTEN_PORT = 13118     # For handling client requests
TCP_BROADCAST_PORT = 13119  # For TCP connections
BUFFER_SIZE = 1024
BROAD_CAST_DELAY = 10

# Packet Formats
OFFER_PACKET_FORMAT = "!IBHH"
REQUEST_PACKET_FORMAT = "!IBQ"
PAYLOAD_PACKET_FORMAT = "!IBQI"

def server_broadcast():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    message = struct.pack(OFFER_PACKET_FORMAT, MAGIC_COOKIE, OFFER_TYPE, UDP_LISTEN_PORT, TCP_BROADCAST_PORT)
    while True:
        udp_socket.sendto(message, ('<broadcast>', UDP_BROADCAST_PORT))
        print(f"Broadcasting offer on port UDP: {UDP_BROADCAST_PORT}, TCP: {TCP_BROADCAST_PORT}")
        time.sleep(BROAD_CAST_DELAY)

def handle_tcp_client(client_socket):
    print(f"{Fore.YELLOW}[TCP] Client has connected{Style.RESET_ALL}")
    try:
        data = client_socket.recv(BUFFER_SIZE)
        file_size = int(data.decode().strip())
        print(f"{Fore.LIGHTMAGENTA_EX}[TCP] Received TCP request for file size {file_size} bytes{Style.RESET_ALL}")
        total_sent = 0
        while total_sent < file_size:
            chunk_size = min(BUFFER_SIZE, file_size - total_sent)
            client_socket.send(b'X' * chunk_size)
            total_sent += chunk_size
        print(f"{Fore.GREEN}[TCP] Transfer completed: Sent {file_size} bytes.{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}[TCP] TCP Error: {e}{Style.RESET_ALL}")
    finally:
        client_socket.close()

def handle_udp_client():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(('', UDP_LISTEN_PORT))

    print(f"{Fore.BLUE}[UDP] Server listening on port {UDP_LISTEN_PORT}{Style.RESET_ALL}")

    while True:
        try:
            data, addr = udp_socket.recvfrom(BUFFER_SIZE)
            if len(data) >= struct.calcsize(REQUEST_PACKET_FORMAT):  # Standard request
                magic_cookie, message_type, file_size = struct.unpack(REQUEST_PACKET_FORMAT, data[:struct.calcsize(REQUEST_PACKET_FORMAT)])
                if magic_cookie != MAGIC_COOKIE or message_type != REQUEST_TYPE:
                    print(f"{Fore.RED}[UDP] Invalid magic cookie or message type. Ignoring packet...{Style.RESET_ALL}")
                    continue

                segment_count = (file_size + BUFFER_SIZE - 1) // BUFFER_SIZE
                segment_counter = 0
                while segment_counter < segment_count:
                    chunk_size = min(BUFFER_SIZE - 20, file_size - (segment_counter * (BUFFER_SIZE - 20)))
                    payload = b'X' * chunk_size
                    packet = struct.pack(
                        PAYLOAD_PACKET_FORMAT,
                        MAGIC_COOKIE,
                        PAYLOAD_TYPE,
                        segment_count,
                        segment_counter
                    ) + payload
                    udp_socket.sendto(packet, addr)
                    segment_counter += 1
                    print(f"{Fore.CYAN}[UDP] Sent packet {segment_counter}/{segment_count} to {addr}{Style.RESET_ALL}")

                print(f"{Fore.GREEN}[UDP] UDP Completed Sent: {file_size} bytes.{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}[UDP] Invalid packet length: {len(data)} bytes. Ignoring...{Style.RESET_ALL}")

        except Exception as e:
            print(f"{Fore.RED}UDP Error: {e}{Style.RESET_ALL}")


def server_handler():
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp_socket.bind(('', TCP_BROADCAST_PORT))
    tcp_socket.listen()
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    print(f"{Fore.YELLOW}Server started, listening on IP address {ip_address}{Style.RESET_ALL}")
    threading.Thread(target=server_broadcast, daemon=True).start()
    threading.Thread(target=handle_udp_client, daemon=True).start()

    while True:
        try:
            client_socket, _ = tcp_socket.accept()
            threading.Thread(target=handle_tcp_client, args=(client_socket,), daemon=True).start()
        except Exception as e:
            print(f"{Fore.RED}Server Error: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    ascii_art = f"""
    {Fore.LIGHTMAGENTA_EX}
         █████╗ ██████╗ ███████╗ ║███████╗
        ██╔══██╗██╔══██╗██╔════╝ ║██╔════╝
        ███████║██████╔╝█████╗   ║███████╗
        ██╔══██║██╔═══╝ ██╔══╝   ║╚════██║
        ██║  ██║██║     ███████╗ ║███████║
        ╚═╝  ╚═╝╚═╝     ╚══════╝ ╚══════╝

                             ██████╗ ██████╗ 
                            ██╔═══██╗██╔══██╗
                            ██║   ██║██████╔╝
                            ██║   ██║██╔═══╝ 
                            ╚██████╔╝██║     
                            ╚═════╝ ╚═╝     
    {Style.RESET_ALL}
    """

    welcome_message = f"{Fore.LIGHTCYAN_EX}Welcome to{Style.RESET_ALL}"

    print(welcome_message)
    print(ascii_art)
    server_handler()
