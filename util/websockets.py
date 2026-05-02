import base64
import hashlib
import json
import uuid

from util.database import drawings_collection, rooms_collection
from util.register import get_user
from util.response import Response

connected_users = {} #name:websocket
connected_rooms = {} #name:room_id
socketID_to_websocket = {}
websocket_to_socketID = {}
websoc_to_user = {} #websocket:name

class WebSocketFrame:
    def __init__(self, fin_bit, opcode, payload_length, payload, total):
        self.fin_bit=fin_bit
        self.opcode=opcode
        self.payload_length=payload_length
        self.payload=payload
        self.total=total

def error(handler, body, code):
    res = Response()
    res.set_status(code, "Forbidden")
    res.headers({
        "Content-Type": "text/plain; charset=utf-8",
        "Content-Length": str(len(body.encode('utf-8'))),
        "X-Content-Type-Options": "nosniff"
    })
    res.text(body)
    handler.request.sendall(res.to_data())
    return

def bytesToInt(data):
    payload_length=0
    for byte in data:
        payload_length=(payload_length << 8) | byte
    return payload_length

def compute_accept(key):
    GUID_key=key+"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    sha1_hash=hashlib.sha1(GUID_key.encode("utf-8")).digest()
    base64_hash=base64.b64encode(sha1_hash).decode("utf-8")
    return base64_hash

def parse_ws_frame(data):
    fin_bit=(data[0] & 0b10000000)>>7
    opcode=data[0] & 0b1111
    mask_bit=(data[1] & 0b10000000)>>7
    payload_length=data[1] & 0b01111111

    additional=2
    if payload_length==126:
        payload_length_bytes=data[additional:additional+2]
        payload_length=bytesToInt(payload_length_bytes)
        additional+=2
    elif payload_length==127:
        payload_length_bytes=data[additional:additional+8]
        payload_length=bytesToInt(payload_length_bytes)
        additional+=8

    if mask_bit:
        mask_bytes=data[additional:additional+4]
        additional+=4

    masked_payload=data[additional:additional + payload_length]

    payload=bytearray()
    if mask_bit:
        for i,b in enumerate(masked_payload):
            mask_byte=mask_bytes[i%4]
            byte=b ^ mask_byte
            payload.append(byte)
    else:
        payload=masked_payload

    total=payload_length+additional

    return WebSocketFrame(fin_bit=fin_bit, opcode=opcode, payload_length=payload_length, payload=payload, total=total)

def generate_ws_frame(data):
    first_byte=0b10000001
    payload_length=len(data)
    sending_frame=bytearray([first_byte])

    if payload_length <=125:
        sending_frame.append(payload_length)
    elif payload_length<=65535:
        sending_frame.append(126)
        sending_frame.extend(payload_length.to_bytes(2, byteorder='big'))
    else:
        sending_frame.append(127)
        sending_frame.extend(payload_length.to_bytes(8, byteorder='big'))

    sending_frame.extend(data)
    return sending_frame

def get_connected_drawing_user(handler, request):
    drawings=[]
    for d in drawings_collection.find({}):
        drawings.append({
            "startX": d["startX"],
            "startY": d["startY"],
            "endX": d["endX"],
            "endY": d["endY"],
            "color": d["color"],
        })
    if drawings:
        drawing_message = {
            "messageType": "init_strokes",
            "strokes": drawings
        }
        sending_back_message_binary = json.dumps(drawing_message).encode("utf-8")
        sending_frame = generate_ws_frame(sending_back_message_binary)
        handler.request.sendall(sending_frame)

def broadcast_active_users(handler, request):
    users=[]
    for connected_user in connected_users:
        users.append({
            "username": connected_user,
        })

    user_message = {
        "messageType": "active_users_list",
        "users": users
    }
    sending_back_message_binary = json.dumps(user_message).encode("utf-8")
    sending_frame = generate_ws_frame(sending_back_message_binary)

    for u in connected_users.values():
        u.sendall(sending_frame)

def send_back_frames(handler, request, payload):
    message = json.loads(payload.decode("utf-8"))
    user=get_user(request)
    username=user["username"]

    if message.get("messageType") == "echo_client":
        sending_back_message = {"messageType": "echo_server", "text": message.get("text")}
        sending_back_message_binary = json.dumps(sending_back_message).encode("utf-8")
        sending_frame = generate_ws_frame(sending_back_message_binary)
        handler.request.sendall(sending_frame)

    if message.get("messageType") == "drawing":
        drawings_collection.insert_one({
            "startX": message.get("startX"),
            "startY": message.get("startY"),
            "endX": message.get("endX"),
            "endY": message.get("endY"),
            "color": message.get("color"),
        })
        sending_back_message_binary = json.dumps(message).encode("utf-8")
        sending_frame = generate_ws_frame(sending_back_message_binary)
        for u in connected_users.values():
            u.sendall(sending_frame)

    if message.get("messageType") == "get_calls":
        calls=[]
        for room in rooms_collection.find({}):
            calls.append({
                "id": room["id"],
                "name": room["name"],
            })
        call_list = {
            "messageType": "call_list",
            "calls": calls,
        }
        sending_back_message_binary = json.dumps(call_list).encode("utf-8")
        sending_frame = generate_ws_frame(sending_back_message_binary)
        handler.request.sendall(sending_frame)

    if message.get("messageType") == "join_call":
        call_Id = message.get("callId")
        room = rooms_collection.find_one({"id": call_Id})

        connected_rooms[username] = call_Id #name:room_id

        call_info = {
            "messageType": "call_info",
            "name": room["name"],
        }
        sending_back_message_binary = json.dumps(call_info).encode("utf-8")
        sending_frame = generate_ws_frame(sending_back_message_binary)
        handler.request.sendall(sending_frame)

        socket_username=[]
        for person,id_room in connected_rooms.items():
            if id_room==call_Id and person!=username:
                socket_username.append({
                    "socketId": websocket_to_socketID[connected_users[person]],
                    "username": person,
                })

        existing_participant = {
            "messageType": "existing_participants",
            "participants": socket_username,
        }
        sending_back_message_binary = json.dumps(existing_participant).encode("utf-8")
        sending_frame = generate_ws_frame(sending_back_message_binary)
        handler.request.sendall(sending_frame)

        just_joined_call = {
            "messageType": "user_joined",
            "socketId": websocket_to_socketID[connected_users[username]],
            "username": username,
        }
        sending_back_message_binary = json.dumps(just_joined_call).encode("utf-8")
        sending_frame = generate_ws_frame(sending_back_message_binary)

        for name,id_room in connected_rooms.items():
            if id_room==call_Id and name!=username:
                connected_users[name].sendall(sending_frame)

    if message.get("messageType") in ("offer", "answer", "ice_candidate"):
        target_socketId=message.get("socketId")
        target_socket=socketID_to_websocket.get(target_socketId)

        sender_socket=handler.request
        sender_socketId=websocket_to_socketID[sender_socket]
        sender_user=websoc_to_user[sender_socket]

        sending_back_message=dict(message)
        sending_back_message["socketId"]=sender_socketId
        sending_back_message["username"]=sender_user

        sending_back_message_binary = json.dumps(sending_back_message).encode("utf-8")
        sending_frame = generate_ws_frame(sending_back_message_binary)
        target_socket.sendall(sending_frame)

def disconnected_ws(request, handler):
    username=websoc_to_user.get(handler.request)
    socket_id=websocket_to_socketID.get(handler.request)
    room_id=connected_rooms.get(username)

    connected_users.pop(username, None)
    connected_rooms.pop(username, None)
    socketID_to_websocket.pop(socket_id, None)
    websocket_to_socketID.pop(handler.request, None)
    websoc_to_user.pop(handler.request, None)

    if room_id:
        sending_back_message = {
            "messageType": "user_left",
            "socketId": socket_id,
        }
        sending_back_message_binary = json.dumps(sending_back_message).encode("utf-8")
        sending_frame = generate_ws_frame(sending_back_message_binary)

        for username, room in connected_rooms.items():
            if room == room_id:
                u = connected_users[username]
                u.sendall(sending_frame)

def websocket(request, handler):
    key=request.headers.get('Sec-WebSocket-Key')
    if not key:
        error(handler, "No Sec-Websocket-Key header", 400)
        return

    accept=compute_accept(key)

    websoc = (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
    )
    handler.request.sendall(websoc.encode("utf-8"))

    user=get_user(request)
    username=user["username"]
    connected_users[username]=handler.request
    websoc_to_user[handler.request]=username

    gen_socket_id = str(uuid.uuid4())
    socketID_to_websocket[gen_socket_id]=handler.request
    websocket_to_socketID[handler.request]=gen_socket_id

    get_connected_drawing_user(handler, request)
    broadcast_active_users(handler, request)

    buffer_data = bytearray()
    continuation_data=bytearray()

    while True:
        chunks = handler.request.recv(2048)
        buffer_data += chunks

        while True:
            if len(buffer_data) < 2: #able to read header
                break
            buffer_ws_frame=parse_ws_frame(buffer_data)
            if len(buffer_data) < buffer_ws_frame.total: #buffer data > total data continue
                break

            frame=buffer_data[:buffer_ws_frame.total]
            buffer_data=buffer_data[buffer_ws_frame.total:]
            ws_frame=parse_ws_frame(frame)

            if ws_frame.opcode==0b1000: #0b1000=end, 0b0001=text, 0b0010=binary, 0b0000=continuation
                disconnected_ws(request,handler)
                broadcast_active_users(handler, request)
                handler.request.close()
                return

            if ws_frame.opcode==0b0001 or ws_frame.opcode==0b0010: #start
                if ws_frame.fin_bit==0: #start cont(mutiple frames)
                    continuation_data=bytearray(ws_frame.payload)
                elif ws_frame.fin_bit==1: #start and end(1 frame)
                    send_back_frames(handler, request, ws_frame.payload)
                    continuation_data=bytearray()

            elif ws_frame.opcode==0b0000: #cont
                continuation_data += ws_frame.payload
                if ws_frame.fin_bit==1: #end when 1(0 cont)
                    send_back_frames(handler, request, continuation_data)
                    continuation_data=bytearray()

def video_calls(request, handler):
    body = request.body
    data = json.loads(body.decode("utf-8"))
    name = data.get("name")
    room_id=str(uuid.uuid4())

    rooms_collection.insert_one({
        "name": name,
        "id": room_id,
    })
    send_back_room_id={
        "id":room_id
    }

    res = Response()
    res.set_status(200, "OK")
    res.json(send_back_room_id)
    handler.request.sendall(res.to_data())

def compute_accept_test():
    key="dGhlIHNhbXBsZSBub25jZQ=="
    accept="s3pPLMBiTxaQ9kYGzzhZRbK+xOo="
    my_test=compute_accept(key)
    print(f"compute_accept: {accept==my_test}")

def parse_ws_frame_test():
    frame_bytes = b'\x81\xa9*\x9b\xb4\x07Q\xb9\xd9bY\xe8\xd5`O\xcf\xcdwO\xb9\x8e%O\xf8\xdchu\xf8\xd8nO\xf5\xc0%\x06\xb9\xc0bR\xef\x96=\x08\xf3\xdd%W'
    frame = parse_ws_frame(frame_bytes)
    expected_payload = b'{"messageType":"echo_client","text":"hi"}'
    expected_payload_length = len(expected_payload)
    expected_fin_bit = 1
    expected_opcode = 1
    print("testing parse_ws_frame")
    print(expected_payload)
    print(frame.payload)
    print(frame.payload_length)
    print(expected_payload_length)
    print(frame.fin_bit == expected_fin_bit)
    print(frame.opcode == expected_opcode)
    print(frame.payload == expected_payload)
    print("total: "+str(frame.total))

def generate_ws_frame_test():
    data=b'hi'
    data_length=len(data)
    frame=generate_ws_frame(data)
    expected_frame=bytearray([0b10000001, data_length])+data
    print("testing generate_ws_frame")
    print(frame == expected_frame)

if __name__ == '__main__':
    compute_accept_test()
    parse_ws_frame_test()
    generate_ws_frame_test()