import os
import sys
import getpass
from yt_dlp import YoutubeDL
import requests

if not os.path.isfile(".APIKEY"):
    with open(".APIKEY", mode="w") as f:
        pass
    print("you must set api key")
    sys.exit()

with open(".APIKEY", mode="r") as f:
    API_KEY = f.read()

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

WALKMAN_MUSIC_PATHS = [f"/media/{getpass.getuser()}/WALKMAN/MUSIC", "/mnt/WALKMAN/MUSIC"]
walkmanMusicPath = None

for p in WALKMAN_MUSIC_PATHS:
    if os.path.isdir(p):
        walkmanMusicPath = p

if not walkmanMusicPath:
    print("You must connect your walkman.")
    sys.exit()

playlistId = input("Playlist Id:")
browserForCookies = input("Your browser:")

print("Get video ids")
ids = getVideoIdsByPlaylist(playlistId)

for fN in os.listdir(walkmanMusicPath):
    s = fN.split(".")
    if len(s) < 2:
        continue
    if s[-2] in ids:
        ids.remove(s[-2])

print("Download videos and send them to walkman")
with YoutubeDL(params={
    "ignoreerrors": True,
    "cookiesfrombrowser": (browserForCookies, None, None, None),
    "extractaudio": True,
    "format": "bestaudio/best",
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "320",
    }],
    "remotecomponents": "ejs:github",
    "outtmpl": f"{walkmanMusicPath}/%(title)s.%(id)s",
}) as dler:
    try:
        dler.download([f"https://www.youtube.com/watch?v={i}" for i in ids])
    except Exception:
        pass

print("Complete.")