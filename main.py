import os
import api_jellyfin
import youtube_utils
import jellyfin_apiclient_python

from getpass import getpass

# url = "https://youtube.com" + youtube_utils.search_for_theme("Jurassic Park").get('url_suffix')

# youtube_utils.youtube2mp3(url)

server_url = input("Enter your jellyfin server url/ip address : ")
server_username = input("Enter your login : ")
server_password = input("Enter your password : ")

clientManager = api_jellyfin.clientManager
client = clientManager.login(server_url, server_username, server_password)

medias = api_jellyfin.get_medias_without_theme(client)

api_jellyfin.download_themes(client, medias, 5)

print("Program finished")
