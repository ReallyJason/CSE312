import hashlib
import html
import json
import uuid

from util.response import Response
from util.database import chat_collection, users_collection

def get_session(request):
    session_id=request.cookies.get("session")
    new=False

    if not session_id:
        session_id=str(uuid.uuid4())
        new=True
    return session_id, new

def get_user(request, handler):
    not_hashed_token=request.cookies.get("auth_token")
    if not not_hashed_token:
        return None
    token=hashlib.sha256(not_hashed_token.encode('utf-8')).hexdigest()
    user=users_collection.find_one({"auth_token_hashed":token})
    return user

def error(code,body,handler):
    res=Response()
    res.set_status(code, "ERROR")
    res.headers({
        "Content-Type": "text/plain; charset=utf-8",
        "Content-Length": str(len(body.encode('utf-8'))),
        "X-Content-Type-Options": "nosniff"
    })
    res.text(body)
    handler.request.sendall(res.to_data())
    return

def post_chat(request, handler):
    user = get_user(request, handler)
    session_id, new = get_session(request)

    if user:
        author=user["username"]
    else:
        author="Guest"+str(session_id)[:8:]

    data=json.loads(request.body.decode('utf-8'))
    content=data['content']
    contents=html.escape(content)
    msg_id=str(uuid.uuid4())

    message={
        "author": author,
        "id": msg_id,
        "content": contents,
        "session": session_id,
        "updated": False,
        "deleted": False,
    }

    chat_collection.insert_one(message)

    res=Response()
    res.set_status(200, "OK")
    res.text("OK")

    if new:
        res.headers({"Set-Cookie": f"session={session_id}; Max-Age=3600"})
    handler.request.sendall(res.to_data())

def get_chats(request, handler):
    alls=chat_collection.find({"deleted": {"$ne": True}})
    messages=[]

    for msg in alls:
        avatar_user=users_collection.find_one({
            "username": msg["author"]
        })
        if avatar_user:
            imageURL=avatar_user.get("imageURL")
        else:
            imageURL=None

        messages.append({
            "author": msg["author"],
            "id": msg["id"],
            "content": msg["content"],
            "updated": msg["updated"],
            "imageURL": imageURL,
            "deleted": False,
        })
    playload={
        "messages": messages,
    }
    res=Response()
    res.set_status(200, "OK")
    res.json(playload)
    handler.request.sendall(res.to_data())

def patch_chat(request,handler,msg_id):
    user=get_user(request, handler)

    data=json.loads(request.body.decode('utf-8'))
    content=data['content']
    contents=html.escape(content)

    message=chat_collection.find_one({"id": msg_id})

    if user:
        if not message or message["author"] != user["username"]:
            error(403, "Id not found or message not found", handler)
            return
    else:
        session_id = request.cookies.get("session")
        if not message or message["session"] != session_id:
            error(403, "Error", handler)
            return

    chat_collection.update_one(
        {"id": msg_id},
        {"$set": {"content":contents, "updated":True}},
    )

    res=Response()
    res.set_status(200, "OK")
    res.text("updated message")
    handler.request.sendall(res.to_data())

def delete_chat(request,handler,msg_id):
    user=get_user(request, handler)

    message=chat_collection.find_one({"id": msg_id})
    if user:
        if not message or message.get("author") != user["username"]:
            error(403, "Error", handler)
            return
    else:
        session_id = request.cookies.get("session")
        if not message or message["session"] != session_id:
            error(403, "Error", handler)
            return

    chat_collection.update_one(
        {"id": msg_id},
        {"$set": {"deleted": True}},
    )
    res=Response()
    res.set_status(200, "OK")
    res.text("deleted message")
    handler.request.sendall(res.to_data())
