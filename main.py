import os
import api_jellyfin
import jellyfin_apiclient_python

from getpass import getpass

server_url = input("Enter your jellyfin server url/ip address : ")
server_username = input("Enter your login : ")
server_password = getpass("Enter your password : ")

clientManager = api_jellyfin.clientManager
client = clientManager.login(server_url, server_username, server_password)
