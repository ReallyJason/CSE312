import json
from datetime import datetime
import os
import uuid

import ffmpeg

from util.response import Response
from util.database import videos_collection, users_collection
from util.multipart import parse_multipart
from util.register import get_user

def post_avatars(request, handler):
    user=get_user(request)
    if not user:
        res=Response()
        res.set_status(401, "ERROR")
        res.json({})
        handler.request.sendall(res.to_data())
        return

    mp=parse_multipart(request)
    name=""
    mimetypes=""
    for p in mp.parts:
        if p.name and p.content and p.headers:
            name=p.name
            img_content=p.content
            mimetypes=p.headers.get("Content-Type")
            mimetypes="."+mimetypes.split("image/")[1]

    avatar_dir=os.path.join("public", "imgs", "avatars")
    os.makedirs(avatar_dir,exist_ok=True)
    filename=f"{uuid.uuid4()}{name}{mimetypes}"
    if "/" in filename:
        res = Response()
        res.set_status(403, "invalid filename")
        res.text("invalid filename")
        handler.request.sendall(res.to_data())
        return

    with open(os.path.join(avatar_dir, filename), "wb") as f:
        f.write(img_content)

    imageURL = os.path.join(avatar_dir, filename)
    users_collection.update_one(
        {"id": user["id"]},
        {"$set": {
            "imageURL": imageURL
        }}
    )

    res=Response()
    res.set_status(200, "OK")
    res.text("Image uploaded")
    handler.request.sendall(res.to_data())

def post_videos(request, handler):
    user=get_user(request)
    if not user:
        res=Response()
        res.set_status(401, "ERROR")
        res.json({})
        handler.request.sendall(res.to_data())
        return

    mp=parse_multipart(request)
    name=""
    mimetypes=".mp4"
    title=""
    description=""
    for p in mp.parts:
        if p.name=="title" and p.content:
            title = p.content.decode("utf-8")
        if p.name=="description" and p.content:
            description = p.content.decode("utf-8")
        if p.name=="video" and p.content and p.headers:
            video_content = p.content

    video_dir=os.path.join("public", "videos")
    os.makedirs(video_dir,exist_ok=True)

    video_id=str(uuid.uuid4())
    filename=f"{video_id}{mimetypes}"
    if "/" in filename:
        res = Response()
        res.set_status(403, "invalid filename")
        res.text("invalid filename")
        handler.request.sendall(res.to_data())
        return

    inputfile=os.path.join(video_dir, filename)
    with open(inputfile, "wb") as f:
        f.write(video_content)

    thing=ffmpeg.probe(inputfile)
    # duration=float(thing ["format"]["duration"])
    thing = next(
        (stream for stream in thing["streams"]  if stream["codec_type"] == "video"), None
    )
    duration=float(thing["duration"])


    thumbnails0=f"public/imgs/thumbnails/{video_id}_0.png"
    thumbnails1=f"public/imgs/thumbnails/{video_id}_1.png"
    thumbnails2=f"public/imgs/thumbnails/{video_id}_2.png"
    thumbnails3=f"public/imgs/thumbnails/{video_id}_3.png"
    thumbnails4=f"public/imgs/thumbnails/{video_id}_4.png"

    ffmpeg.input(inputfile, ss=0).output(thumbnails0, vframes=1, update=1).run()
    ffmpeg.input(inputfile, ss=duration*0.25).output(thumbnails1, vframes=1, update=1).run()
    ffmpeg.input(inputfile, ss=duration*0.5).output(thumbnails2, vframes=1, update=1).run()
    ffmpeg.input(inputfile, ss=duration*0.75).output(thumbnails3, vframes=1, update=1).run()
    ffmpeg.input(inputfile, ss=duration-0.05).output(thumbnails4, vframes=1, update=1).run()

    now = datetime.now()
    created_at=now.ctime()

    thumbnails=[thumbnails0, thumbnails1, thumbnails2, thumbnails3, thumbnails4]

    hls_path=hls_encode(inputfile,video_id)

    details={
        "author_id": user["id"],
        "title": title,
        "description": description,
        "video_path": os.path.join(video_dir, filename),
        "created_at": created_at,
        "id": video_id,
        "thumbnailURL": thumbnails0,
        "thumbnails": thumbnails,
        "hls_path": hls_path,
    }

    videos_collection.insert_one(details)

    res=Response()
    res.set_status(200, "OK")
    res.json({"id": video_id})
    handler.request.sendall(res.to_data())

def get_videos(request, handler):
    alls=[]
    for d in videos_collection.find({}):
        alls.append({
            "author_id": d["author_id"],
            "title": d["title"],
            "description": d["description"],
            "video_path": d["video_path"],
            "created_at": d["created_at"],
            "id": d["id"],
            "thumbnailURL": d["thumbnailURL"],
            "thumbnails": d["thumbnails"],
        })
    res = Response()
    res.set_status(200, "OK")
    res.json({"videos": alls})
    handler.request.sendall(res.to_data())

def get_videos_id(request, handler, video_id):
    d=videos_collection.find_one({"id": video_id})

    video={
        "author_id": d["author_id"],
        "title": d["title"],
        "description": d["description"],
        "video_path": d["video_path"],
        "created_at": d["created_at"],
        "id": d["id"],
        "thumbnailURL": d["thumbnailURL"],
        "thumbnails": d["thumbnails"],
        "hls_path": d["hls_path"],
    }

    res = Response()
    res.json({"video": video})
    res.set_status(200, "OK")
    handler.request.sendall(res.to_data())

def put_thumbnails(request, handler, video_id):
    data=json.loads(request.body.decode('utf-8'))
    new_url=data.get("thumbnailURL")

    videos_collection.update_one(
        {"id": video_id},
        {"$set": {"thumbnailURL": new_url}}
    )

    res = Response()
    res.set_status(200, "OK")
    res.json({"message": "Thumbnail updated"})
    handler.request.sendall(res.to_data())

def hls_encode(path,id):
    output=os.path.join("public", "hls_videos", id)
    audio_avi = os.path.join(output,"audio.avi")

    output_720_dir = os.path.join(output, "720p")
    output_144_dir = os.path.join(output, "144p")
    audio_dir = os.path.join(output,"audio")


    output_720 = os.path.join(output_720_dir, "output_720.m3u8")
    output_144 = os.path.join(output_144_dir, "output_144.m3u8")
    output_audio = os.path.join(audio_dir, "audio.m3u8")

    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(output_720_dir, exist_ok=True)
    os.makedirs(output_144_dir, exist_ok=True)


    ffmpeg.input(path).output(audio_avi).run() #get .avi
    ffmpeg.input(audio_avi).output(output_audio, f="hls",hls_list_size=0).run(overwrite_output=True)

    (
        ffmpeg.input(path).filter('scale','1280','720')
        .output(output_720,f="hls",hls_list_size=0).run(overwrite_output=True)
    )

    (
        ffmpeg.input(path).filter('scale','256','144')
        .output(output_144,f="hls",hls_list_size=0).run(overwrite_output=True)
    )

    absolute_path=os.path.join(output, "main.m3u8")

    main="""#EXTM3U
#EXT-X-VERSION:7
#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="group_A1",NAME="audio_1",DEFAULT=YES,URI="audio/audio.m3u8"
#EXT-X-STREAM-INF:BANDWIDTH=1131049,RESOLUTION=1280x720,CODECS="avc1.64001f,mp4a.40.2",AUDIO="group_A1"
720p/output_720.m3u8

#EXT-X-STREAM-INF:BANDWIDTH=131049,RESOLUTION=256x144,CODECS="avc1.64001e,mp4a.40.2",AUDIO="group_A1"
144p/output_144.m3u8"""

    with open(absolute_path, "w") as f:
        f.write(main)

    return os.path.join(output, "main.m3u8")