import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import sys
import getpass
from threading import Lock
import requests
from yt_dlp import YoutubeDL
from mutagen.easyid3 import EasyID3
from concurrency_limiter import concurrency_limiter

if not os.path.isfile("settings.json"):
    with open("settings.json", mode="w") as f:
        f.write(
"""
{
    "apiKey": "",
    "playlistIds": [
        
    ],
    "browser": ""
}
"""
        )
    print("You must configure on settings.json")
    sys.exit()

with open("settings.json", mode="r") as f:
    d = json.load(f)
    API_KEY = str(d["apiKey"])
    PLAYLIST_IDS = [str(pId) for pId in d["playlistIds"]]
    BROWSER = str(d["browser"])

def getPlaylistTitle(playlistId:str) -> str:
    r = requests.get(
        "https://www.googleapis.com/youtube/v3/playlists",
        params={
            "part": "snippet",
            "id": playlistId,
            "key": API_KEY
        }
    )
    return r.json()["items"][0]["snippet"]["title"]

def getVideoIdsByPlaylist(playlistId:str) -> list[str]:
    first = True
    nextPageToken = None
    ids = []
    while first or nextPageToken:
        first = False
        params = {
            "part": "snippet",
            "playlistId": playlistId,
            "key": API_KEY,
            "maxResults": 50
        }
        if nextPageToken:
            params["pageToken"] = nextPageToken
        r = requests.get(
            "https://www.googleapis.com/youtube/v3/playlistItems",
            params=params
        )
        r.raise_for_status()
        d = r.json()
        for item in d["items"]:
            ids.append(item["snippet"]["resourceId"]["videoId"])
        nextPageToken = d.get("nextPageToken")
    return ids

def getVideoTitle(videoId:str) -> str:
    r = requests.get(
        "https://www.googleapis.com/youtube/v3/videos",
        params={
            "part": "snippet",
            "id": videoId,
            "key": API_KEY
        }
    )
    r.raise_for_status()
    return r.json()["items"][0]["snippet"]["title"]

WALKMAN_MUSIC_PATHS = [f"/media/{getpass.getuser()}/WALKMAN/MUSIC", "/mnt/WALKMAN/MUSIC"]
walkmanMusicPath = None

for p in WALKMAN_MUSIC_PATHS:
    if os.path.isdir(p):
        walkmanMusicPath = p

if not walkmanMusicPath:
    print("You must connect to your walkman and mount it on your system.")
    sys.exit()

for playlistId in PLAYLIST_IDS:
    playlistTitle = getPlaylistTitle(playlistId)
    print(f"\033cStarting downloading a playlist \"{playlistTitle}\"")
    ids = getVideoIdsByPlaylist(playlistId)
    oIds = ids.copy()

    for fN in os.listdir(walkmanMusicPath):
        p = f"{walkmanMusicPath}/{fN}"
        s = fN.split(".")
        if len(s) != 3:
            os.remove(p)
            continue
        if s[-1] == "mp3" and os.path.isfile(".".join(s[:-1])):
            os.remove(p)
            os.remove(p[:-1])
        elif s[-1] == "part":
            os.remove(p)

        if s[-2] == playlistId:
            if not s[-3] in oIds:
                os.remove(p)
                continue
            ids.remove(s[-3])

    finisheds = 0
    finishedsLock = Lock()

    print("Downloading videos and send them to walkman")
    def dl(i):
        global finisheds
        global finishedsLock
        try:
            with YoutubeDL(params={
                "cookiesfrombrowser": (BROWSER, None, None, None),
                "extractaudio": True,
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "320",
                }],
                "remote_components": ["ejs:github"],
                "outtmpl": f"{walkmanMusicPath}/%(id)s.{playlistId}",
                "noprogress": True,
                "quiet": True
            }) as dler:
                dler.download(f"https://www.youtube.com/watch?v={i}")
        finally:
            with finishedsLock:
                finisheds += 1
                print(f"Finished to downloading {finisheds}/{len(ids)}", flush=True)
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(dl, i) for i in ids]
        for future in as_completed(futures):
            pass
    
    print("Setting album")
    for fN in os.listdir(walkmanMusicPath):
        p = f"{walkmanMusicPath}/{fN}"
        s = fN.split(".")
        if len(s) != 3:
            continue
        if s[-2] == playlistId:
            mp3 = EasyID3(p)
            mp3["album"] = playlistTitle
            mp3["title"] = getVideoTitle(s[-3])
            mp3["tracknumber"] = str(oIds.index(s[-3])+1)
            mp3.save(v1=0, v2_version=3)
print("\033cCompleted.")