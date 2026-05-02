import base64
import hashlib
import os
import urllib.parse
import uuid

from dotenv import dotenv_values
import requests

from util.database import users_collection
from util.response import Response

config = dotenv_values(".env")

def get_authgithub(request, handler):
    client_id = os.environ.get("GITHUB_CLIENT_ID")
    scope = os.environ.get("SCOPE")
    redirect_uri = os.environ.get("REDIRECT_URI")

    params = {
        "response_type": "code",
        "client_id": client_id,
        "scope": scope,
        "redirect_uri": redirect_uri,
    }

    p_encoded_str = "https://github.com/login/oauth/authorize" + "?" + urllib.parse.urlencode(params)

    res = Response()
    res.set_status(302, "FOUND")
    res.headers({"Location": p_encoded_str})
    res.text("Updated user and password")
    handler.request.sendall(res.to_data())


def git_callback(request, handler):
    code = request.path.split("code=", 1)[1]
    print("code", code)
    if not code:
        res=Response()
        res.set_status(401, "ERROR")
        res.json({"error": "missing code"})
        handler.request.sendall(res.to_data())
        return

    client_id = os.environ.get("GITHUB_CLIENT_ID")
    client_secret = os.environ.get("GITHUB_CLIENT_SECRET")

    auth = f"{client_id}:{client_secret}"
    auth = auth.encode("utf-8")
    auth_header = base64.b64encode(auth).decode("utf-8")

    headers={
        "Authorization": f"Basic {auth_header}",
        "Accept": "application/vnd.github.v3+json",
    }
    data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": os.environ.get("REDIRECT_URI"),
    }
    response = requests.post("https://github.com/login/oauth/access_token",data=data,headers=headers)

    tok=response.json()
    access_token=tok.get("access_token")
    if not access_token:
        res=Response()
        res.set_status(401, "ERROR")
        res.json({"error": "missing access_token"})
        handler.request.sendall(res.to_data())
        return
    access_headers={
        "Authorization": f"Bearer {access_token}",
    }

    email=None
    r=requests.get("https://api.github.com/user", headers=access_headers)
    if r.status_code == 200:
        rj=r.json()
        email=rj.get("email") or rj.get("login")
    gh_username=email

    user_id=str(uuid.uuid4())
    not_hashed_token=str(uuid.uuid4())
    token=hashlib.sha256(not_hashed_token.encode('utf-8')).hexdigest()

    existing_user=users_collection.find_one({"username": gh_username})
    if existing_user:
        users_collection.update_one({
            "id": existing_user["id"]},
            {"$set": {
                "auth_token_hashed": token,
            }}
        )
    else:
        users_collection.insert_one({
            "id": user_id,
            "username": gh_username,
            "auth_token_hashed": token,
        })
    res=Response()
    res.headers({
        "Set-Cookie":   f"auth_token={not_hashed_token}; "
                        f"HttpOnly; "
                        f"Secure; "
                        f"Max-Age=600",

        "Location": "http://localhost:8080/"
    })
    res.set_status(302, "Found")
    handler.request.sendall(res.to_data())