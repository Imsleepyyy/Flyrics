# made by @bunnykek

import argparse
import requests
import bs4
import json
import re
from sanitize_filename import sanitize
from utility import saveLyrics

NAME = "Apple Music"
REGEX = re.compile("https://music.apple.com/(\w{2})/album/.+?/(\d+)(\?i=(\d+))?")

with open("config.json") as f:
    config = json.load(f)

    AUTH_BEARER = config['applemusic']['auth_bearer']
    TOKEN = config['applemusic']['media-user-token']

HEADERS = {
    "authorization": AUTH_BEARER,
    "media-user-token": TOKEN,
    "Origin": "https://music.apple.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://music.apple.com/",
    "content-type": "application/json",
    "x-apple-renewal": "true",
    "DNT": "1",
    "Connection": "keep-alive",
    'l': 'en-US'
}

def zpad(val, n):
    bits = val.split('.')
    return "%s.%s" % (bits[0].zfill(n), bits[1])

class Lyrics:
    def __init__(self, url, api = False) -> None:
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
   
        region, albumid, trackFlag, trackid = REGEX.search(url).groups()
        
        if trackFlag:
            self.jsonResponse = [self.getTrackLyric(trackid, region, api)]
        
        else:
            self.jsonResponse = self.getAlbumLyric(albumid, region, api)
        

    def getAlbumLyric(self, albumid: str, region: str, api: bool):
        print("Getting lyrics for the whole album...")
        metadata = self.session.get(f"https://api.music.apple.com/v1/catalog/{region}/albums/{albumid}").json()
        metadata = metadata['data'][0]

        lyricsJson = list()
        for track in metadata['relationships']['tracks']['data']:
            trackJson = self.getTrackLyric(track['id'], region, api)
            lyricsJson.append(trackJson)
        
        return lyricsJson

    def getTrackLyric(self, trackID: str, region: str, api: bool):
        response = self.session.get(f'https://amp-api.music.apple.com/v1/catalog/{region}/songs/{trackID}/lyrics')
        result = response.json()
        soup =  bs4.BeautifulSoup(result['data'][0]['attributes']['ttml'], 'lxml')
        metadata = self.session.get(f"https://api.music.apple.com/v1/catalog/{region}/songs/{trackID}").json()
        metadata = metadata['data'][0]

        title = sanitize(metadata['attributes']['name'])
        trackNo = metadata['attributes']['trackNumber']

        artist = sanitize(metadata['attributes']['artistName'])
        album = sanitize(metadata['attributes']['albumName'])
        year = metadata['attributes']['releaseDate'][0:4]

        plain_lyric = f"Title: {title}\nAlbum: {album}\nArtist: {artist}\n\n"
        synced_lyric = f"[ti:{title}]\n[ar:{artist}]\n[al:{album}]\n\n"
        paragraphs = soup.find_all("p")

        if 'itunes:timing="None"' in result['data'][0]['attributes']['ttml']:
            synced_lyric = None
            for line in paragraphs:
                plain_lyric += line.text+'\n'

        else:
            for paragraph in paragraphs:
                begin = paragraph.get('begin')
                splits = begin.split(':')
                millisec = zpad(splits[-1], 2)
                minutes = '00'
                try:
                    minutes = splits[-2].zfill(2)
                except:
                    pass
                timeStamp = minutes+":"+millisec
                text = paragraph.text
                plain_lyric += text+'\n'
                synced_lyric += f'[{timeStamp}]{text}\n'
        
        if not api:
            saveLyrics(synced_lyric, plain_lyric, title, artist, album, trackNo, year)
        
        return {
            'synced': synced_lyric,
            'plain': plain_lyric
        }
