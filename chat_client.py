
"""
ChatClient - interactive text client for the chat servers.
"""

import socket, threading, json, sys, select

# active connection socket
sock = None          
# background thread that listens for server messages
recv_thread = None   
current_channel = None
nick = None

# sends a JSON object to the server
def send_obj(obj):
    global sock
    if not sock:
        print("Not connected.")
        return
    try:
        
        sock.sendall((json.dumps(obj, separators=(",",":")) + "\n").encode('utf-8'))
    except Exception as e:
        print("Send failed:", e)

# receives server messages
def reader():
    global sock
    buf = b""  
    while True:
        try:
            data = sock.recv(4096)
            if not data:
                print("Disconnected from server.")
                break

            buf += data

            # processes complete JSON messages
            while b'\n' in buf:
                line, buf = buf.split(b'\n',1)
                if not line:
                    continue
                try:
                    obj = json.loads(line.decode('utf-8'))
                except:
                    print("Malformed JSON from server")
                    continue

                # handles server messages/events
                handle_server_obj(obj)

        except Exception as e:
            print("Reader exception:", e)
            break

# handles any object the server sends
def handle_server_obj(obj):
    t = obj.get("type")

    # server response
    if t == "response":
        status = obj.get("status")
        msg = obj.get("message","")

        # /list shows channel info
        if obj.get("channels") is not None:
            print("Channels:")
            for c in obj["channels"]:
                print(f"  {c['channel']} ({c['users']} users)")
        else:
            print(f"[{status}] {msg}")

    # server event
    elif t == "event":
        evt = obj.get("event")

        if evt == "message":
            # chat message from another user
            print(f"[{obj.get('channel')}] {obj.get('from')}: {obj.get('text')}")

        elif evt == "user_joined":
            print(f"[{obj.get('channel')}] *** {obj.get('nick')} joined")

        elif evt == "user_left":
            print(f"[{obj.get('channel')}] *** {obj.get('nick')} left")

        else:
            print("Event:", obj)

    else:
        print("Server:", obj)

# user's input loop
def repl():
    global sock, recv_thread, current_channel, nick
    print("Type /help for commands.")

    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            line = "/quit"

        if not line:
            continue

        # handles commands starting with "/"
        if line.startswith("/"):
            parts = line.split()
            # remove "/"
            cmd = parts[0][1:]  
            args = parts[1:]

            # /connects host
            if cmd == "connect":
                if sock:
                    print("Already connected.")
                    continue

                if len(args) == 0:
                    print("Usage: /connect host [port]")
                    continue

                host = args[0]
                port = int(args[1]) if len(args) > 1 else 12345

                try:
                    # creates connection to server
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect((host, port))

                    # starts reader thread
                    recv_thread = threading.Thread(target=reader, daemon=True)
                    recv_thread.start()

                    # tells server that we connected
                    send_obj({"type":"command","command":"connect","args":[]})

                    print("Connected to", host, port)

                except Exception as e:
                    print("Connect failed:", e)
                    sock = None

            # /nick
            elif cmd == "nick":
                if not sock:
                    print("Not connected.")
                    continue
                if not args:
                    print("Usage: /nick <nick>")
                    continue

                nick = args[0]
                send_obj({"type":"command","command":"nick","args":[nick]})

            # /list
            elif cmd == "list":
                send_obj({"type":"command","command":"list","args":[]})

            # /join
            elif cmd == "join":
                if not sock:
                    print("Not connected.")
                    continue
                if not args:
                    print("Usage: /join <channel>")
                    continue

                current_channel = args[0]
                send_obj({"type":"command","command":"join","args":[current_channel]})

            # /leave
            elif cmd == "leave":
                ch = args[0] if args else current_channel

                if not ch:
                    print("Not in any channel.")
                    continue

                send_obj({"type":"command","command":"leave","args":[ch]})

                if ch == current_channel:
                    current_channel = None

            # /quit
            elif cmd == "quit":
                if sock:
                    send_obj({"type":"command","command":"quit","args":[]})
                    sock.close()
                    sock = None
                print("Bye.")
                break

            # /help
            elif cmd == "help":
                print("Commands:\n"
                      " /connect host [port]\n"
                      " /nick <nickname>\n"
                      " /list\n"
                      " /join <channel>\n"
                      " /leave [channel]\n"
                      " /quit\n"
                      "Anything else (no leading /) is sent as message to current channel.")

            # unknown command
            else:
                print("Unknown command. Type /help")

        else:
            # user typed a normal chat message
            if not sock:
                print("Not connected.")
                continue

            if not current_channel:
                print("Not in a channel. Use /join <channel>")
                continue

            # send message: channel + text
            send_obj({"type":"command","command":"message","args":[current_channel, line]})


if __name__ == "__main__":
    try:
        repl()
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")
        try:
            if sock:
                sock.close()
        except:
            pass
        sys.exit(0)
