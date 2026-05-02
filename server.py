import os
from dotenv import load_dotenv
import socketserver
import time

load_dotenv()

from util.response import Response
from util.request import Request
from util.router import Router
from util.hello_path import hello_path
from util.chat import post_chat, get_chats , patch_chat, delete_chat
from util.register import post_register, post_login, get_logout, get_me,get_search, post_settings, post_twofa
from util.github import get_authgithub,git_callback
from util.avatar import post_avatars, post_videos, get_videos, get_videos_id, put_thumbnails
from util.websockets import websocket, video_calls

MIME={
    ".html": "text/html",
    ".css": "text/css",
    ".txt": "text/plain",
    ".js": "text/javascript",
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".ico": "image/x-icon",
    ".webp": "image/webp",
    ".mp4": "video/mp4",
    ".m3u8": "application/x-mpegURL",
    ".ts": "video/mp2t",
}
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

def static(request, handler):
    file_path="."+request.path

    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        body="The requested content does not exist"

        res=Response()
        res.set_status(404, "Not Found")
        res.headers({
            "Content-Type": "text/plain; charset=utf-8",
            "Content-Length": str(len(body.encode('utf-8'))),
            "X-Content-Type-Options": "nosniff"
        })
        res.text(body)
        handler.request.sendall(res.to_data())
        return

    ext=os.path.splitext(file_path)[1]
    mime_type=MIME[ext]

    with open(file_path, "rb") as f:
        content=f.read()

    res=Response()
    res.headers({
        "Content-Type": mime_type+"; charset=utf-8",
        "Content-Length": str(len(content)),
        "X-Content-Type-Options": "nosniff"
    })
    res.bytes(content)
    handler.request.sendall(res.to_data())

def render(request, handler, page_name):
    layout_path = "./public/layout/layout.html"
    page_path = "./public/"+page_name

    if not os.path.exists(layout_path) or not os.path.exists(page_path):
        body="The requested content does not exist"
        error(handler,body,404)
        return

    with open(layout_path, "r", encoding="utf-8") as f:
        layout=f.read()

    with open(page_path, "r", encoding="utf-8") as f:
        content=f.read()

    replaced=layout.replace("{{content}}", content)

    res=Response()
    res.headers({
        "Content-Type": "text/html; charset=utf-8",
        "Content-Length": str(len(replaced)),
        "X-Content-Type-Options": "nosniff"
    })
    res.text(replaced)
    handler.request.sendall(res.to_data())

def index_path(request, handler):
    render(request, handler, "index.html")

def chat_path(request, handler):
    render(request, handler, "chat.html")

def patch_chat_path(request, handler):
    msg_id=request.path[len("/api/chats/"):]
    patch_chat(request, handler, msg_id)

def delete_chat_path(request, handler):
    msg_id=request.path[len("/api/chats/"):]
    delete_chat(request, handler, msg_id)

def get_videos_ids(request, handler):
    video_id = request.path[len("/api/videos/"):]
    get_videos_id(request, handler, video_id)

def put_thumbnail(request, handler):
    video_id = request.path[len("/api/thumbnails/"):]
    put_thumbnails(request, handler, video_id)

def register_path(request, handler):
    render(request, handler, "register.html")

def login_path(request, handler):
    render(request, handler, "login.html")

def settings_path(request, handler):
    render(request, handler, "settings.html")

def search_users_path(request, handler):
    render(request, handler, "search-users.html")

def change_avatar_path(request, handler):
    render(request, handler, "change-avatar.html")

def videotube_path(request, handler):
    render(request, handler, "videotube.html")

def videotube_upload_path(request, handler):
    render(request, handler, "upload.html")

def videotube_videos_path(request, handler):
    render(request, handler, "view-video.html")

def thumbnail_path(request, handler):
    render(request, handler, "set-thumbnail.html")

def test_websocket_path(request, handler):
    render(request, handler, "test-websocket.html")

def drawing_board_path(request, handler):
    render(request, handler, "drawing-board.html")

def video_call_path(request, handler):
    render(request, handler, "video-call.html")

def video_call_room_path(request, handler):
    render(request, handler, "video-call-room.html")


class MyTCPHandler(socketserver.BaseRequestHandler):

    def __init__(self, request, client_address, server):
        self.router = Router()
        self.router.add_route("GET", "/hello", hello_path, True)

        self.router.add_route("GET", "/api/users/@me", get_me, False)
        self.router.add_route("POST", "/api/users/settings", post_settings, True)
        self.router.add_route("GET", "/api/users/search", get_search, False)
        self.router.add_route("GET", "/logout", get_logout, True)
        self.router.add_route("POST", "/login", post_login, True)
        self.router.add_route("POST", "/register", post_register, True)
        self.router.add_route("POST", "/api/totp/enable", post_twofa, True)
        self.router.add_route("GET", "/authgithub", get_authgithub, True)
        self.router.add_route("GET", "/authcallback", git_callback, False)
        self.router.add_route("POST", "/api/users/avatar", post_avatars, True)
        self.router.add_route("POST", "/api/videos", post_videos, True)
        self.router.add_route("GET", "/api/videos", get_videos, True)
        self.router.add_route("GET", "/api/videos/", get_videos_ids, False)
        self.router.add_route("PUT", "/api/thumbnails/", put_thumbnail, False)
        self.router.add_route("GET", "/websocket", websocket , True)
        self.router.add_route("POST", "/api/video-calls", video_calls , True)


        self.router.add_route("POST", "/api/chats", post_chat, True)
        self.router.add_route("GET", "/api/chats", get_chats, True)

        self.router.add_route("PATCH", "/api/chats/", patch_chat_path, False)
        self.router.add_route("DELETE", "/api/chats/",delete_chat_path, False)

        self.router.add_route("GET", "/public/", static, False)

        self.router.add_route("GET", "/", index_path, True)
        self.router.add_route("GET", "/chat", chat_path, True)

        self.router.add_route("GET", "/register", register_path, True)
        self.router.add_route("GET", "/login", login_path, True)
        self.router.add_route("GET", "/settings", settings_path, True)
        self.router.add_route("GET", "/search-users", search_users_path, True)
        self.router.add_route("GET", "/change-avatar", change_avatar_path, True)
        self.router.add_route("GET", "/videotube", videotube_path, True)
        self.router.add_route("GET", "/videotube/upload", videotube_upload_path, True)
        self.router.add_route("GET", "/videotube/videos/", videotube_videos_path , False)
        self.router.add_route("GET", "/videotube/set-thumbnail", thumbnail_path , False)
        self.router.add_route("GET", "/test-websocket", test_websocket_path , True)
        self.router.add_route("GET", "/drawing-board", drawing_board_path , True)
        self.router.add_route("GET", "/video-call", video_call_path , True)
        self.router.add_route("GET", "/video-call/", video_call_room_path , False)



        super().__init__(request, client_address, server)

    def handle(self):
        first_data = self.request.recv(2048)

        head_end=first_data.find(b"\r\n\r\n")
        head_bytes=first_data[:head_end]
        body=first_data[head_end+4:]

        lines=head_bytes.decode("utf-8").split("\r\n")
        header={}
        for line in lines[1:]:
            if ":" in line:
                key,value=line.split(":",1)
                header[key.strip().lower()]=value.strip()

        content_length=0
        if "content-length" in header:
            content_length = int(header["content-length"])

        data=bytearray()
        data.extend(body)

        more_read=max(0, content_length-len(data))
        while more_read > 0:
            last_time=time.time()

            chunk = self.request.recv(2048)
            if time.time() - last_time > 0.1:
                self.request.close()
                break


            if not chunk:
                break
            data.extend(chunk)
            more_read -= len(chunk)

        received_data = head_bytes + b"\r\n\r\n" + bytes(data)

        print(self.client_address)
        print("--- received data ---")
        print(received_data)
        print("--- end of data ---\n\n")
        request = Request(received_data)

        self.router.route_request(request, self)


def main():
    host = "0.0.0.0"
    port = 8080
    socketserver.ThreadingTCPServer.allow_reuse_address = True

    server = socketserver.ThreadingTCPServer((host, port), MyTCPHandler)

    print("Listening on port " + str(port))
    server.serve_forever()


if __name__ == "__main__":
    main()
