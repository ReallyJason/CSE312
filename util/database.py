import json
import sys
import os

from pymongo import MongoClient

mongo_uri = os.environ.get("MONGO_URI")

if mongo_uri:
    print("using MONGO_URI from env")
    mongo_client = MongoClient(mongo_uri)
else:
    docker_db = os.environ.get('DOCKER_DB', "false")

    if docker_db == "true":
        print("using docker compose db")
        mongo_client = MongoClient("mongo")
    else:
        print("using local db")
        mongo_client = MongoClient("localhost")

db = mongo_client["cse312"]

chat_collection = db["chat"]
users_collection = db["users"]
videos_collection = db["videos"]
drawings_collection = db["drawings"]
rooms_collection = db["rooms"]
