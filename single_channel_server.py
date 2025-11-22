import socket, json

HOST = ""
PORT = 12345

# sends a JSON object to the client
def send_obj(conn, obj):
    conn.sendall((json.dumps(obj) + "\n").encode("utf-8"))

# processes commands sent from the client
def handle_command(obj, state):
    cmd = obj.get("command")
    args = obj.get("args", [])

    # handles /connect
    if cmd == "connect":
        return {"type":"response","status":"ok","message":"Connected"}

    # handles /nick 
    if cmd == "nick":
        if len(args) < 1:
            return {"type":"response","status":"error","message":"Missing nickname"}
        state["nick"] = args[0]     # store nickname
        return {"type":"response","status":"ok","message":f"Nickname set to {state['nick']}"}

    # handles /list
    if cmd == "list":
        return {
            "type":"response",
            "status":"ok",
            "channels":[{"channel":"main","users":1}]
        }

    # handles /join
    if cmd == "join":
        state["channel"] = "main"   # always join "main"
        return {"type":"response","status":"ok","message":"Joined main"}

    # handles /leave
    if cmd == "leave":
        state["channel"] = None
        return {"type":"response","status":"ok","message":"Left channel"}

    # handles /message
    if cmd == "message":
        if len(args) < 2:
            return {"type":"response","status":"error","message":"Bad message args"}

        # message text is always the second argument
        text = args[1]

        # Return an event to echo message back to client
        return {
            "type":"event",
            "event":"message",
            "channel":"main",
            "from": state.get("nick","?"),
            "text": text
        }

    # handles /quit
    if cmd == "quit":
        return {"type":"response","status":"ok","message":"Goodbye","quit":True}

    # unknown command
    return {"type":"response","status":"error","message":"Unknown command"}

def main():
    print("Stage 1 Server: Single-channel, single-thread running…")

    # creates server socket
    sock = socket.socket()
    sock.bind((HOST, PORT))
    sock.listen(1)  

    # waits for a client to connect
    conn, addr = sock.accept()
    print("Client connected:", addr)

    # simple state for a single client
    state = {"nick": None, "channel": None}

    with conn:
        buf = b""  

        while True:
            data = conn.recv(1024)
            if not data:
                print("Client disconnected.")
                break

            buf += data

            # processes each JSON message
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)

                if not line:
                    continue

                # decodes JSON message
                try:
                    obj = json.loads(line.decode("utf-8"))
                except:
                    send_obj(conn, {"type":"response","status":"error","message":"Bad JSON"})
                    continue

                # commands must be type="command"
                if obj.get("type") != "command":
                    send_obj(conn, {"type":"response","status":"error","message":"Expected command"})
                    continue

                # processes the command
                response = handle_command(obj, state)

                # sends back response or event
                send_obj(conn, response)

                # if quit command is received, exit server
                if response.get("quit"):
                    print("Client requested quit.")
                    return

if __name__ == "__main__":
    main()
