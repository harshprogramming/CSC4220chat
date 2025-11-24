import socket, json

HOST = ""
PORT = 12345

# sends a JSON object to a connection
def send_obj(conn, obj):
    conn.sendall((json.dumps(obj) + "\n").encode("utf-8"))

# broadcasts a message to every user in a channel
def broadcast(channels, channel_name, obj):
    for user in channels[channel_name]["users"]:
        send_obj(user, obj)

def main():
    print("Stage 2 Server: Multi-channel, single-thread running…")

    sock = socket.socket()
    sock.bind((HOST, PORT))
    sock.listen(10)

    channels = {
        "main": {"users": [], "names": {}}
    }

    users = {}

    while True:
        conn, addr = sock.accept()
        print("Client connected:", addr)

        # initializes user state
        users[conn] = {"nick": None, "channel": None}

        buf = b""

        # processes a single client until quit/disconnect
        with conn:
            while True:
                data = conn.recv(1024)
                if not data:
                    break  # client disconnected
                buf += data

                # reads each JSON line
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    obj = json.loads(line.decode("utf-8"))

                    if obj["type"] != "command":
                        send_obj(conn, {"type":"response","status":"error","message":"Expected command"})
                        continue

                    cmd = obj["command"]
                    args = obj.get("args", [])
                    user = users[conn]

                    # fix added here: handle /connect command
                    if cmd == "connect":
                        send_obj(conn, {"type":"response","status":"ok","message":"Connected"})
                        continue

                    # /nick
                    if cmd == "nick":
                        user["nick"] = args[0]
                        send_obj(conn, {"type":"response","status":"ok","message":"Nick set"})

                    # /join <channel>
                    elif cmd == "join":
                        new_channel = args[0]

                        # creates a channel if it doesn't exist
                        if new_channel not in channels:
                            channels[new_channel] = {"users": [], "names": {}}

                        # if a user is already in a channel leave it
                        if user["channel"]:
                            old_chan = user["channel"]
                            channels[old_chan]["users"].remove(conn)
                            broadcast(channels, old_chan, {
                                "type":"event",
                                "event":"user_left",
                                "channel": old_chan,
                                "nick": user["nick"]
                            })

                        # join new channel
                        user["channel"] = new_channel
                        channels[new_channel]["users"].append(conn)
                        channels[new_channel]["names"][conn] = user["nick"]

                        send_obj(conn, {"type":"response","status":"ok","message":f"Joined {new_channel}"})

                        # broadcasts join event
                        broadcast(channels, new_channel, {
                            "type":"event",
                            "event":"user_joined",
                            "channel": new_channel,
                            "nick": user["nick"]
                        })

                    # /leave
                    elif cmd == "leave":
                        ch = user["channel"]
                        if not ch:
                            send_obj(conn, {"type":"response","status":"error","message":"Not in a channel"})
                            continue

                        channels[ch]["users"].remove(conn)

                        broadcast(channels, ch, {
                            "type":"event",
                            "event":"user_left",
                            "nick": user["nick"],
                            "channel": ch
                        })

                        user["channel"] = None
                        send_obj(conn, {"type":"response","status":"ok","message":"Left channel"})

                    # /list
                    elif cmd == "list":
                        result = []
                        for name, ch in channels.items():
                            result.append({"channel": name, "users": len(ch["users"])})
                        send_obj(conn, {"type":"response","status":"ok","channels": result})

                    # /message
                    elif cmd == "message":
                        channel = args[0]
                        text = args[1]

                        broadcast(channels, channel, {
                            "type":"event",
                            "event":"message",
                            "channel": channel,
                            "from": user["nick"],
                            "text": text
                        })

                        send_obj(conn, {"type":"response","status":"ok","message":"Sent"})

                    # /quit
                    elif cmd == "quit":
                        send_obj(conn, {"type":"response","status":"ok","message":"Goodbye"})
                        return

                    # unknown command
                    else:
                        send_obj(conn, {"type":"response","status":"error","message":"Unknown command"})

        # cleanup on disconnect
        if users[conn]["channel"]:
            ch = users[conn]["channel"]
            channels[ch]["users"].remove(conn)

        del users[conn]

if __name__ == "__main__":
    main()
