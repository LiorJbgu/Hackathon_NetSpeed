import socket
import struct
import threading
import time
from tqdm import tqdm
from colorama import Fore, Style

# Constants
MAGIC_COOKIE = 0xabcddcba
OFFER_TYPE = 0x2
REQUEST_TYPE = 0x3
PAYLOAD_TYPE = 0x4
UDP_BROADCAST_PORT = 13117
BUFFER_SIZE = 1024
UDP_TIMEOUT = 1

# Packet Formats
OFFER_PACKET_FORMAT = "!IBHH"
REQUEST_PACKET_FORMAT = "!IBQ"
PAYLOAD_PACKET_FORMAT = "!IBQI"

def client_listen():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_socket.bind(('', UDP_BROADCAST_PORT))

    print("Listening for server offers...")
    while True:
        try:
            data, addr = udp_socket.recvfrom(BUFFER_SIZE)
            magic_cookie, message_type, udp_port, tcp_port = struct.unpack('!IBHH', data)
            if magic_cookie == MAGIC_COOKIE and message_type == OFFER_TYPE:
                print(f"Offer received from {addr[0]}: UDP port {udp_port}, TCP port {tcp_port}")
                return addr[0], udp_port, tcp_port
        except Exception as e:
            print(f"Error listening for offers: {e}")

def handle_tcp_transfer(server_ip, tcp_port, file_size, transfer_id):
    try:
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.connect((server_ip, tcp_port))
        tcp_socket.send(str(file_size).encode())
        total_received = 0
        start_time = time.time()

        while total_received < file_size:
            data = tcp_socket.recv(BUFFER_SIZE)
            total_received += len(data)

        elapsed_time = time.time() - start_time
        speed = (file_size * 8) / elapsed_time
        print(f"{Fore.GREEN}[TCP] Transfer #{transfer_id} finished: {elapsed_time:.4f}s, {speed:.2f} bps{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}TCP Error: {e}{Style.RESET_ALL}")
    finally:
        tcp_socket.close()

def handle_udp_transfer(server_ip, udp_port, file_size, transfer_id):
    try:
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.settimeout(UDP_TIMEOUT)

        # Send the request packet
        request_packet = struct.pack(REQUEST_PACKET_FORMAT, MAGIC_COOKIE, REQUEST_TYPE, file_size)
        udp_socket.sendto(request_packet, (server_ip, udp_port))

        received_segments = 0
        total_segments = None
        start_time = time.time()
        prev_packet_time = time.time()
        lost_packets = 0
        success_packets = 0

        # Progress bar setup

        while True:
            try:
                data, _ = udp_socket.recvfrom(BUFFER_SIZE + 20)
                
                magic_cookie, message_type, total_segments, segment_number = struct.unpack(PAYLOAD_PACKET_FORMAT, data[:17])

                # Validate the payload
                if magic_cookie == MAGIC_COOKIE and message_type == PAYLOAD_TYPE:
                    received_segments += 1
                    success_packets += 1
                    prev_packet_time = time.time()
            except socket.timeout:
                if time.time() - prev_packet_time > UDP_TIMEOUT:
                    break
                lost_packets += 1
        elapsed_time = time.time() - start_time
        speed = (file_size * 8) / elapsed_time
        if success_packets + lost_packets == 0:
            success_rate = 0
        else:
            success_rate = (success_packets / (success_packets + lost_packets)) * 100.0

        print(f"{Fore.GREEN}[UDP] Transfer #{transfer_id} finished: {elapsed_time - UDP_TIMEOUT:.4f}s, {speed:.2f} bps, Success Rate: {success_rate:.4f}%{Style.RESET_ALL}")


    except Exception as e:
        print(f"{Fore.RED}UDP Error: {e}{Style.RESET_ALL}")
    finally:
        udp_socket.close()

def client_handler():
    print(f"{Fore.LIGHTCYAN_EX}Client started, listening for offer requests...{Style.RESET_ALL}")

    while True:
        file_size = int(input("Enter file size (bytes): "))
        tcp_count = int(input("Enter number of TCP connections: "))
        udp_count = int(input("Enter number of UDP connections: "))
        server_ip, udp_port, tcp_port = client_listen()
        threads = []
        # transfer_id = 1 should check if handlers must use it
        for i in range(tcp_count):
            t = threading.Thread(target=handle_tcp_transfer, args=(server_ip, tcp_port, file_size, i + 1))
            t.start()
            threads.append(t)
        for i in range(udp_count):
            t = threading.Thread(target=handle_udp_transfer, args=(server_ip, udp_port, file_size, i + 1))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        print(f"{Fore.YELLOW}All transfers complete, listening to offer requests...{Style.RESET_ALL}")
        choice = input(f"{Fore.BLUE}Do you want to listen for new offers? (Yes/No): {Style.RESET_ALL}").strip().lower()
        if choice != 'yes':
            print("Exiting client...")
            break

if __name__ == "__main__":
    client_handler()
