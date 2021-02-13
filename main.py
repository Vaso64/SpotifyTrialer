from selenium import webdriver
from selenium.webdriver.support.ui import Select
from getpass import getpass
import datetime
import requests
import random
import string
import copy
import time
import re

def InputSetup(oldCredentials, newCredentials, cc):
    print("= = = Spotify account gen/transfer by Vaso64 = = =\n")
    transfer = int(input("\nTransfer data from old account? (0/1): "))
    if transfer:
        oldCredentials["login"] = input("\tSource account login: ")
        oldCredentials["pass"] = getpass("\tSource account password: ")
    generate = int(input("\nGenerated new account? (0/1): "))
    if not generate:
        newCredentials["login"] = input("\tImport account login: ")
        newCredentials["pass"] = getpass("\tImport account password: ")
    activate  = int(input("\nActivate import account? (0/1): "))
    if activate:
        cc["number"] = input("\tCC number (without spaces): ")
        cc["exp"] = input("\tCC expiration date (DD/MM): ")
        cc["cvv"] = input("\tCCV code (3 digits): ")
    print("\nStarting...")

def GenerateAccount(session : webdriver.Chrome):
    # Generate credentials
    username = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    mail = "{0}@{1}.com".format(username, "".join(random.choices(string.ascii_lowercase + string.digits, k=6)))
    password = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    bdate = datetime.datetime(random.randint(1960, 2002), random.randint(1,12), random.randint(1,27))
    
    session.get("https://www.spotify.com/sk/signup/")
    time.sleep(2)
    session.find_element_by_id("onetrust-accept-btn-handler").click() #cookiePopUp
    session.find_element_by_id("email").send_keys(mail)
    session.find_element_by_id("confirm").send_keys(mail)
    session.find_element_by_id("password").send_keys(password)
    session.find_element_by_id("displayname").send_keys(username)
    session.find_element_by_id("day").send_keys(bdate.day)
    session.find_element_by_id("year").send_keys(bdate.year)
    Select(session.find_element_by_id("month")).select_by_visible_text("January")
    session.find_element_by_class_name("Indicator-sc-16vj7o8-0").click() #gender_radio
    session.find_element_by_class_name("Indicator-sc-11vkltc-0").click() #TOS_checkbox

    #Recaptcha wait
    while "signup" in session.current_url:
        time.sleep(1)
    time.sleep(3)

    print("\nYour newly generated account is follwing: {0}:{1}\n".format(mail, username))
    return { "login": mail, "pass": password }

def LoginSession(session : webdriver.Chrome, username, password):
    session.get("https://accounts.spotify.com/login")
    session.find_element_by_id("login-username").send_keys(username)
    session.find_element_by_id("login-password").send_keys(password)
    session.find_element_by_id("login-button").click()
    while("login" in session.current_url): time.sleep(0.25)
    print("Succesfully logged in with {0} account".format(username))

def Authorize(session : webdriver.Chrome):
    clientID = "bfaef1ecef0c45bb902c5983ce64793a"
    authScopes = ["user-follow-read", "user-follow-modify", 
                  "user-library-read", "user-library-modify",
                  "playlist-read-collaborative", "playlist-read-private", 
                  "playlist-modify-private", "playlist-modify-public"]
    authPage = "https://accounts.spotify.com/en/authorize?client_id={0}&response_type=code&redirect_uri=https://blank.org&scope=".format(clientID)
    for i, authScope in enumerate(authScopes):
        if (i != 0): authPage += "%20"
        authPage += authScope

    session.get(authPage)
    if ("/authorize" in session.current_url):
        session.find_element_by_id("auth-accept").click()
    print("API access granted")
    return re.match("^.*code=([\w\d\-_]*).*$", session.current_url).group(1)

def ActivateTrial(session : webdriver.Chrome, cc):
    session.get("https://www.spotify.com/sk/purchase/offer/1-month-trial/")
    time.sleep(1)
    session.find_element_by_id("cardnumber").send_keys(cc["number"])
    session.find_element_by_id("expiry-date").send_keys(cc["exp_date"])
    session.find_element_by_id("security-code").send_keys(cc["cvv"])
    #session.find_element_by_id("checkout_submit").click()
    print("Premium trial for import account has been succsefully activated")

    
def Transfer(fromAuth, toAuth):
    tokenPayload = {
        "grant_type": "authorization_code", 
        "code": None, 
        "redirect_uri": "https://blank.org",
        "client_id": "bfaef1ecef0c45bb902c5983ce64793a",
        "client_secret": "659da96ab94e41a8b25e7a1bd9542c1e" }
    fromHeader = {
        "Accept": "application/json",
        "Authorization": "Bearer {0}".format(requests.post("https://accounts.spotify.com/api/token", data={**tokenPayload, "code": fromAuth}).json()["access_token"]),
        "Content-Type": "application/json" }
    toHeader = {
        "Accept": "application/json",
        "Authorization": "Bearer {0}".format(requests.post("https://accounts.spotify.com/api/token", data={**tokenPayload, "code": toAuth}).json()["access_token"]),
        "Content-Type": "application/json" }
    fromID = requests.get("https://api.spotify.com/v1/me", headers = fromHeader).json()["id"]
    toID = requests.get("https://api.spotify.com/v1/me", headers = toHeader).json()["id"]


    TransferPlaylist(fromHeader, fromID, toHeader, toID)

    TransferAlbums(fromHeader, fromID, toHeader, toID)

    TransferTracks(fromHeader, fromID, toHeader, toID)

    TransferArtists(fromHeader, fromID, toHeader, toID)

    TransferShows(fromHeader, fromID, toHeader, toID)

    print("Data transfer completed")

def TransferPlaylist(fromHeader, fromID, toHeader, toID):
    print("Importing playlists...")

    #Get from old
    playlists = []
    data = {
        "limit": 50, 
        "offset": 0
    }
    while True:
        r = requests.get("https://api.spotify.com/v1/me/playlists", headers = fromHeader, params=data)
        for i in r.json()["items"]:
            playlists.append(copy.deepcopy(i))
        if len(playlists) == r.json()["total"]: break
        else: data["offset"] += data["limit"]
    print("Found {0} playlists".format(len(playlists)))

    #Import to new
    for playlist in playlists:
        print("Importing playlist \"{0}\" by {1}".format(playlist["name"], playlist["owner"]["display_name"]))

        #Follow collabs / not own
        if playlist["collaborative"] or playlist["owner"]["id"] != fromID:
            requests.put("https://api.spotify.com/v1/playlists/{0}/followers".format(playlist["id"]), headers=toHeader)
            print("Playlist {0} is now being followed".format(playlist["name"]))

        #Import privates
        else:
            #Create new playlist
            playlistData = {
                "name": playlist["name"], 
                "public": playlist["public"],
                "description": playlist["description"] }
            newPlaylist = requests.post("https://api.spotify.com/v1/users/{0}/playlists".format(toID), headers=toHeader, json=playlistData)
            print("Created new playlist with name {0}".format(playlist["name"]))

            #Get songs
            songs = []
            data = {
                "market": "from_token",
                "fields": "items(track(uri)),total",
                "limit": 100,
                "offset": 0
            }
            while True:
                r = requests.get(playlist["tracks"]["href"], headers=fromHeader, params=data)
                for song in r.json()["items"]:
                    songs.append(song["track"]["uri"]) 
                if len(songs) == r.json()["total"]: break
                else: data["offset"] += data["limit"]
            print("Found {0} songs".format(len(songs)))

            #Import songs
            for i in range(0, len(songs), 100):
                requests.post("https://api.spotify.com/v1/playlists/{0}/tracks".format(newPlaylist.json()["id"]), headers=toHeader, json={"uris": songs[i:min(i+100, len(songs))]})
            print("Imported {0} songs".format(len(songs)))

def TransferTracks(fromHeader, fromID, toHeader, toID):
    print("Importing tracks...")

    #Get from old
    tracks = []
    data = {
        "market": "from_token",
        "limit": 50,
        "offset": 0 }
    while True:
        r = requests.get("https://api.spotify.com/v1/me/tracks", headers=fromHeader, params=data)
        for i in r.json()["items"]:
            tracks.append(i["track"]["id"])
        if r.json()["total"] == len(tracks): break
        else: data["offset"] += data["limit"]
    print("Found {0} saved tracks".format(len(tracks)))

    #Import to new
    for i in range(0 , len(tracks), 50):
        requests.put("https://api.spotify.com/v1/me/tracks", headers=toHeader, json={"ids": tracks[i:min(i+50, len(tracks))]})
    print("Imported {0} tracks".format(len(tracks)))

def TransferAlbums(fromHeader, fromID, toHeader, toID):
    print("Importing albums...")

    #Get from old
    albums = []
    data = {
        "market": "from_token",
        "limit": 50,
        "offset": 0 }
    while True:
        r = requests.get("https://api.spotify.com/v1/me/albums", headers=fromHeader, params=data)
        for i in r.json()["items"]:
            albums.append(i["album"]["id"])
        if r.json()["total"] == len(albums): break
        else: data["offset"] += data["limit"]
    print("Found {0} saved albums".format(len(albums)))

    #Import to new
    for i in range(0 , len(albums), 50):
        requests.put("https://api.spotify.com/v1/me/albums", headers=toHeader, json={"ids": albums[i:min(i+50, len(albums))]})
    print("Imported {0} albums".format(len(albums)))

def TransferShows(fromHeader, fromID, toHeader, toID):
    print("Importing shows...")

    #Get from old
    shows = []
    data = {
        "market": "from_token",
        "limit": 50,
        "offset": 0 }
    while True:
        r = requests.get("https://api.spotify.com/v1/me/shows", headers=fromHeader, params=data)
        for i in r.json()["items"]:
            shows.append(i["show"]["id"])
        if r.json()["total"] == len(shows): break
        else: data["offset"] += data["limit"]
    print("Found {0} saved shows".format(len(shows)))

    #Import to new
    for i in range(0 , len(shows), 50):
        requests.put("https://api.spotify.com/v1/me/shows", headers=toHeader, json={"ids": shows[i:min(i+50, len(shows))]})
    print("Imported {0} shows".format(len(shows)))

def TransferArtists(fromHeader, fromID, toHeader, toID):
    print("Importing artists...")

    #Get from old
    artists = []
    data = {
        "type": "artist",
        "limit": 50
    }
    while True:
        r = requests.get("https://api.spotify.com/v1/me/following", headers=fromHeader, params=data)
        for i in r.json()["artists"]["items"]:
            artists.append(i["id"])
        if r.json()["artists"]["total"] == len(artists): break
        else: data["after"] = r.json()["artists"]["cursor"]["after"]
    print("Found {0} followed artists".format(len(artists)))

    #Import to new
    for i in range(0, len(artists), 50):
        requests.put("https://api.spotify.com/v1/me/following", headers=toHeader, params={"type": "artist"}, json={"ids": artists[i:min(i+50, len(artists))]})
    print("Imported {0} artists".format(len(artists)))

    
# Variables
##oldCredentials = { "login": "dabofiy746@dkt1.com", "pass": "M@t3J12e2Ee"}
##newCredentials = { "login": "komaxe5040@girtipo.com", "pass": "M@t3J12e2Ee" } 
cc = { "number": "", "exp_date": "", "cvv": ""}
oldCredentials = { "login": "", "pass": ""}
newCredentials = { "login": "", "pass": "" } 


# User input
InputSetup(oldCredentials, newCredentials, cc)

# Create / Login to new account
newSpotify_session = webdriver.Chrome("chromedriver.exe")
if newCredentials["login"]:
    LoginSession(newSpotify_session, newCredentials["login"], newCredentials["pass"])
else:
    newCredentials = GenerateAccount(newSpotify_session)

# Login to old, authorize and transfer to new
if oldCredentials["login"]:
    oldSpotify_session = webdriver.Chrome("chromedriver.exe")
    LoginSession(oldSpotify_session, oldCredentials["login"], oldCredentials["pass"])
    fromAuthCode = Authorize(oldSpotify_session)
    toAuthCode = Authorize(newSpotify_session)
    Transfer(fromAuthCode, toAuthCode)

# Activate subscription
if cc["number"]:
    ActivateTrial(newSpotify_session, cc)

print("Done!\n")
input("Press Enter to exit...")
