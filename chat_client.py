import socket
import sys
import threading
import signal
import os

running = True


def clear_screen():
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")


def receiver(sock):
    """Receive messages from server asynchronously."""
    global running
    while running:
        try:
            msg = sock.recv(1024).decode()
            if not msg:
                print("\nDisconnected from server.")
                running = False
                break
            print(msg, end="")
        except:
            break


def graceful_exit(sock):
    global running
    running = False
    try:
        sock.send("quit".encode())
    except:
        pass
    sock.close()
    sys.exit(0)


def main():
    global running

    if len(sys.argv) != 3 or sys.argv[1] != "-p":
        print("Usage: python client.py -p <port>")
        return

    port = int(sys.argv[2])

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("127.0.0.1", port))

    print(f"Connected to server on port {port}")

    signal.signal(signal.SIGINT, lambda s, f: graceful_exit(sock))

    threading.Thread(target=receiver, args=(sock,), daemon=True).start()

    try:
        while running:
            msg = input()
            sock.send(msg.encode())
    except KeyboardInterrupt:
        graceful_exit(sock)


if __name__ == "__main__":
    main()


