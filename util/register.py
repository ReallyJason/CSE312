import hashlib
import uuid
import bcrypt
import pyotp

from util.auth import extract_credentials, validate_password
from util.database import users_collection
from util.response import Response

def error(code,body,handler):
    res = Response()
    res.set_status(code, "ERROR")
    res.headers({
        "Content-Type": "text/plain; charset=utf-8",
        "Content-Length": str(len(body.encode('utf-8'))),
        "X-Content-Type-Options": "nosniff"
    })
    res.text(body)
    handler.request.sendall(res.to_data())
    return

def get_user(request):
    not_hashed_token=request.cookies.get("auth_token")
    if not not_hashed_token:
        return None
    token=hashlib.sha256(not_hashed_token.encode('utf-8')).hexdigest()
    user=users_collection.find_one({"auth_token_hashed":token})
    return user

def post_register(request,handler):
    username,password=extract_credentials(request)
    if not password or not username:
        error(400,"missing credentials",handler)
        return
    if not validate_password(password):
        error(400,"Invalid password",handler)
        return
    if users_collection.find_one({"username":username}):
        error(400, "username is already taken", handler)
        return

    user_id=str(uuid.uuid4())
    pw=bcrypt.hashpw(password.encode('utf-8'),bcrypt.gensalt())

    users_collection.insert_one({
        "id": user_id,
        "username":username,
        "hashed_password":pw,
    })
    res=Response().set_status(200, "OK")
    res.text("Registered")
    handler.request.sendall(res.to_data())

def post_login(request,handler):
    credentials=extract_credentials(request)
    if len(credentials)==2:
        username,password=credentials
        totpCode=""
    else:
        username,password,totpCode=credentials

    if not password or not username:
        error(400,"messing credentials",handler)
        return
    if not validate_password(password):
        error(400,"Invalid password",handler)
        return

    user=users_collection.find_one({"username":username})
    if not user:
        error(400, "Incorrect username", handler)
        return

    hashed_pw=user.get("hashed_password")
    if not hashed_pw or not bcrypt.checkpw(password.encode('utf-8'),hashed_pw):
        error(400, "Incorrect password", handler)
        return

    secret=user.get("secret")
    if secret:
        if not totpCode:
            error(401, "2FA is enabled for this account", handler)
            return
        if not pyotp.TOTP(secret).verify(totpCode):
            error(400, "Invalid TOTP code", handler)
            return

    not_hashed_token=str(uuid.uuid4())
    token=hashlib.sha256(not_hashed_token.encode('utf-8')).hexdigest()
    users_collection.update_one({
        "id": user["id"]},
        {"$set":{
            "auth_token_hashed":token,
        }}
    )
    res=Response().set_status(200, "OK")
    res.text("Successfully logged in")
    res.headers({
        "Set-Cookie":   f"auth_token={not_hashed_token}; "
                        f"HttpOnly; "
                        f"Secure; "
                        f"Max-Age=600; "
    })
    handler.request.sendall(res.to_data())

def get_logout(request,handler):
    not_hashed_token=request.cookies.get("auth_token")
    if not_hashed_token:
        token=hashlib.sha256(not_hashed_token.encode('utf-8')).hexdigest()
        users_collection.find_one_and_update({
            "auth_token_hashed": token},
            {"$set":{
                "auth_token_hashed": "deleted"
            }}
        )

    res=Response().set_status(302, "OK")
    res.headers({
        "Location": "/",
        "Content-Length": "0",
    })
    res.text("Successfully logged out")
    res.headers({
        "Set-Cookie":   f"auth_token=deleted; "
                        f"HttpOnly; "
                        f"Secure; "
                        f"Max-Age=0; "
                        f"Path=/; "
    })
    handler.request.sendall(res.to_data())

def get_me(request,handler):
    user=get_user(request)
    if not user or not user.get("id"):
        res=Response()
        res.set_status(401, "Unauthorized")
        res.json({})
        handler.request.sendall(res.to_data())
        return
    if user.get("imageURL"):
        payload={
            "username": user["username"],
            "id": user["id"],
            "imageURL": user["imageURL"],
        }
    else:
        payload={
            "username": user["username"],
            "id": user["id"],
        }
    res = Response()
    res.set_status(200, "OK")
    res.json(payload)
    handler.request.sendall(res.to_data())

def get_search(request,handler):
    search=request.path.split("=", 1)[1]
    all_usernames=[]
    if search:
        for username in users_collection.find({}):
            if search in username["username"]:
                all_usernames.append({
                    "id":username["id"],
                    "username":username["username"],
                })
    res=Response()
    res.set_status(200, "OK")
    res.json({"users":all_usernames})
    handler.request.sendall(res.to_data())

def post_settings(request,handler):
    user=get_user(request)
    if not user:
        error(400,"missing user",handler)
        return

    username,password=extract_credentials(request)

    if not username:
        error(400,"missing credentials",handler)
        return
    if password:
        if not validate_password(password):
            error(400,"Invalid password",handler)
            return
        pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    else:
        pw=user.get("hashed_password")
    if username!=user["username"]:
        if users_collection.find_one({"username": username}):
            error(400, "username is already taken", handler)
            return

    users_collection.update_one(
        {"id": user["id"]},
        {"$set": {
            "username":username,
            "hashed_password":pw,
        }},
    )
    res=Response()
    res.set_status(200, "OK")
    res.text("Updated user and password")
    handler.request.sendall(res.to_data())

def post_twofa(request,handler):
    user=get_user(request)
    secret=pyotp.random_base32()

    users_collection.update_one({
        "id": user["id"]},
        {"$set":{
            "secret":secret,
        }}
    )
    res=Response()
    res.set_status(200, "OK")
    res.json({"secret":secret})
    handler.request.sendall(res.to_data())