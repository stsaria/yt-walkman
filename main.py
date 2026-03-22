import json
import os
import sys
import getpass
import requests
from yt_dlp import YoutubeDL
from mutagen.easyid3 import EasyID3

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

WALKMAN_MUSIC_PATHS = [f"/media/{getpass.getuser()}/WALKMAN/MUSIC", "/mnt/WALKMAN/MUSIC"]
walkmanMusicPath = None

for p in WALKMAN_MUSIC_PATHS:
    if os.path.isdir(p):
        walkmanMusicPath = p

if not walkmanMusicPath:
    print("You must connect to your walkman.")
    sys.exit()

for playlistId in PLAYLIST_IDS:
    playlistTitle = getPlaylistTitle(playlistId)
    print(f"\033cStarting downloading a playlist {playlistTitle}")
    ids = getVideoIdsByPlaylist(playlistId)
    oIds = ids.copy()

    for fN in os.listdir(walkmanMusicPath):
        s = fN.split(".")
        if len(s) < 4:
            continue
        if s[-3] in ids and s[-2] == playlistId:
            ids.remove(s[-3])

    print("Downloading videos and send them to walkman")
    with YoutubeDL(params={
        "ignoreerrors": True,
        "cookiesfrombrowser": (BROWSER, None, None, None),
        "extractaudio": True,
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "320",
        }],
        "remotecomponents": "ejs:github",
        "outtmpl": f"{walkmanMusicPath}/%(title)s.%(id)s.{playlistId}",
    }) as dler:
        try:
            dler.download([f"https://www.youtube.com/watch?v={i}" for i in ids])
        except Exception:
            pass
    print("Setting album")
    for fN in os.listdir(walkmanMusicPath):
        s = fN.split(".")
        if len(s) < 4:
            continue
        if s[-2] == playlistId:
            mp3 = EasyID3(f"{walkmanMusicPath}/{fN}")
            mp3["album"] = playlistTitle
            mp3["title"] = fN.split(".")[:-3]
            mp3.save(v1=0, v2_version=3)
print("\033cCompleted.")