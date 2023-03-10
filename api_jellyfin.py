"""
Original source code from :
https://github.com/mueslimak3r/jellyfin-playlist-maker-from-tmdb/blob/main/api_jellyfin.py
"""
import youtube_utils

'''
Big thanks to the jellyfin/jellyfin-mpv-shim devs for most of the code in this file!
Adapted from:
https://github.com/jellyfin/jellyfin-mpv-shim/blob/ed8a61d6984c79ac81ef9db1f84af940ca036e0f/jellyfin_mpv_shim/clients.py
Main project:
https://github.com/jellyfin/jellyfin-mpv-shim
'''

import sys
import os.path
import json
import uuid
import time
import logging
import re
import pathlib

from jellyfin_apiclient_python import JellyfinClient
from jellyfin_apiclient_python.connection_manager import CONNECTION_STATE
from getpass import getpass
from typing import Optional

APP_NAME = "Jellyfin musical theme finder"
USER_APP_NAME = "Jellyfin musical theme finder"
CLIENT_VERSION = "1.0"
USER_AGENT = "jellyfin-musical-theme-finder/%s" % CLIENT_VERSION
CAPABILITIES = {
	"PlayableMediaTypes": "",
	"SupportsMediaControl": False,
	"SupportedCommands": (),
}

connect_retry_mins = 0

ignore_ssl_cert = False

credentials_location = os.path.join(pathlib.Path(__file__).parent.resolve(), "cred.json")

log = logging.getLogger("clients")
path_regex = re.compile("^(https?://)?([^/:]+)(:[0-9]+)?(/.*)?$")


def expo(max_value: Optional[int] = None):
	n = 0
	while True:
		a = 2 ** n
		if max_value is None or a < max_value:
			yield a
			n += 1
		else:
			yield max_value


class ClientManager(object):
	def __init__(self):
		self.callback = lambda client, event_name, data: None
		self.credentials = []
		self.clients = {}
		self.usernames = {}
		self.is_stopping = False

	def cli_connect(self):
		is_logged_in = self.try_connect()
		add_another = False

		if "add" in sys.argv:
			add_another = True

		while not is_logged_in or add_another:
			server = input(("Server URL: "))
			username = input(("Username: "))
			password = getpass(("Password: "))

			is_logged_in = self.login(server, username, password)

			if is_logged_in:
				log.info(("Successfully added server."))
				add_another = input(("Add another server?") + " [y/N] ")
				add_another = add_another in ("y", "Y", "yes", "Yes")
			else:
				log.warning(("Adding server failed."))

	@staticmethod
	def client_factory():
		client = JellyfinClient(allow_multiple_clients=True)
		client.config.data["app.default"] = True
		client.config.app(
			USER_APP_NAME, CLIENT_VERSION, USER_APP_NAME, str(uuid.uuid4())
		)
		client.config.data["http.user_agent"] = USER_AGENT
		client.config.data["auth.ssl"] = not ignore_ssl_cert
		return client

	def _connect_all(self):
		is_logged_in = False
		for server in self.credentials:
			if self.connect_client(server):
				is_logged_in = True
		return is_logged_in

	def try_connect(self):
		if os.path.exists(credentials_location):
			with open(credentials_location) as cf:
				self.credentials = json.load(cf)

		if "Servers" in self.credentials:
			credentials_old = self.credentials
			self.credentials = []
			for server in credentials_old["Servers"]:
				server["uuid"] = str(uuid.uuid4())
				server["username"] = ""
				self.credentials.append(server)

		is_logged_in = self._connect_all()
		if connect_retry_mins and not is_logged_in:
			log.warning(
				"Connection failed. Will retry for {0} minutes.".format(
					connect_retry_mins
				)
			)
			for attempt in range(connect_retry_mins * 2):
				time.sleep(30)
				is_logged_in = self._connect_all()
				if is_logged_in:
					break

		return is_logged_in

	def save_credentials(self):
		with open(credentials_location, "w") as cf:
			json.dump(self.credentials, cf)

	def login(
			self, server: str, username: str, password: str, force_unique: bool = False
	):
		"""
		Start a connexion between you and a jellyfin server

		:param server: The server URL
		:param username: The username you need to connect to the server
		:param password: The password associated with username
		:param force_unique:
		:return: An instance of jellyfin connexion, or None if there is an error
		"""
		if server.endswith("/"):
			server = server[:-1]

		protocol, host, port, path = path_regex.match(server).groups()

		if not protocol:
			log.warning("Adding http:// because it was not provided.")
			protocol = "http://"

		if protocol == "http://" and not port:
			log.warning("Adding port 8096 for insecure local http connection.")
			log.warning(
				"If you want to connect to standard http port 80, use :80 in the url."
			)
			port = ":8096"

		server = "".join(filter(bool, (protocol, host, port, path)))

		client = self.client_factory()
		client.auth.connect_to_address(server)
		result = client.auth.login(server, username, password)
		if "AccessToken" in result:
			credentials = client.auth.credentials.get_credentials()
			server = credentials["Servers"][0]
			if force_unique:
				server["uuid"] = server["Id"]
			else:
				server["uuid"] = str(uuid.uuid4())
			server["username"] = username
			if force_unique and server["Id"] in self.clients:
				return client
			self.connect_client(server)
			self.credentials.append(server)
			self.save_credentials()
			return client
		return None

	def setup_client(self, client: "JellyfinClient", server):
		def event(event_name, data):
			if event_name == "WebSocketDisconnect":
				timeout_gen = expo(100)
				if server["uuid"] in self.clients:
					while not self.is_stopping:
						timeout = next(timeout_gen)
						log.info(
							"No connection to server. Next try in {0} second(s)".format(
								timeout
							)
						)
						self._disconnect_client(server=server)
						time.sleep(timeout)
						if self.connect_client(server):
							break
			else:
				self.callback(client, event_name, data)

		client.callback = event
		client.callback_ws = event
		client.start(websocket=True)

		client.jellyfin.post_capabilities(CAPABILITIES)

	def remove_client(self, uuid: str):
		self.credentials = [
			server for server in self.credentials if server["uuid"] != uuid
		]
		self.save_credentials()
		self._disconnect_client(uuid=uuid)

	def connect_client(self, server):
		if self.is_stopping:
			return False

		is_logged_in = False
		client = self.client_factory()
		state = client.authenticate({"Servers": [server]}, discover=False)
		server["connected"] = state["State"] == CONNECTION_STATE["SignedIn"]
		if server["connected"]:
			is_logged_in = True
			self.clients[server["uuid"]] = client
			self.setup_client(client, server)
			if server.get("username"):
				self.usernames[server["uuid"]] = server["username"]

		return is_logged_in

	def _disconnect_client(self, uuid: Optional[str] = None, server=None):
		if uuid is None and server is not None:
			uuid = server["uuid"]

		if uuid not in self.clients:
			return

		if server is not None:
			server["connected"] = False

		client = self.clients[uuid]
		del self.clients[uuid]
		client.stop()

	def remove_all_clients(self):
		self.stop_all_clients()
		self.credentials = []
		self.save_credentials()

	def stop_all_clients(self):
		for key, client in list(self.clients.items()):
			del self.clients[key]
			client.stop()

	def stop(self):
		self.is_stopping = True
		for client in self.clients.values():
			client.stop()

	def get_username_from_client(self, client):
		# This is kind of convoluted. It may fail if a server
		# was added before we started saving usernames.
		for uuid, client2 in self.clients.items():
			if client2 is client:
				if uuid in self.usernames:
					return self.usernames[uuid]
				for server in self.credentials:
					if server["uuid"] == uuid:
						return server.get("username", "Unknown")
				break

		return "Unknown"


clientManager = ClientManager()

'''
everything above is from jellyfin-mpv-shim
everything below is new
'''


def match_item_by_name(client=None, inputItem=None):
	if inputItem == None or client == None:
		return False

	result = client.jellyfin.user_items(params={
		'searchTerm': inputItem['title'],
		'IncludeMedia': True,
		'Recursive': True,
		'excludeItemTypes': (
			"Episode"
		),
		'enableImages': False,
		'enableUserData': False,
		'Limit': 20,
		'Fields': (
			"ProviderIds"
		)
	})

	if 'Items' in result and result['Items']:
		resultItem = result['Items'][0]

		# try to match against tmdb ID if jellyfin media has it. Otherwise just make sure the year matches
		if 'ProviderIds' in resultItem and 'Tmdb' in resultItem['ProviderIds'] \
				and inputItem['tmdb_id'] != 0 and resultItem['ProviderIds']['Tmdb'] != inputItem['tmdb_id']:
			return False
		elif 'ProviderIds' in resultItem and 'Tmdb' not in resultItem['ProviderIds']:
			if inputItem['year'] != 0 and resultItem['ProductionYear'] != inputItem['year']:
				return False
		inputItem['jellyfin_id'] = resultItem['Id']
		return True
	return False


def match_items_to_tmdb(client, inputList=None):
	if inputList == None:
		return []

	outputList = []
	for item in inputList:
		if match_item_by_name(client, item):
			print("matched: ", item['title'])
			outputList.append(item)
		else:
			print("removing: ", item['title'])
	return (outputList)


def sync_list_with_jellyfin_playlist(client=None, title=None, inputList=None):
	if title == None or client == None or not inputList:
		return
	user_id = client.auth.config.data['auth.user_id']

	payload = {
		"Name": title,
		"Ids": [],
		"UserId": user_id,
		"MediaType": None
	}

	for item in inputList:
		payload['Ids'].append(item['jellyfin_id'])
	print(str(json.dumps(payload)))
	response = client.jellyfin._post(handler="Playlists", params=payload)
	if 'Id' in response:
		print("Hopefully ;) created playlist: ", response['Id'])
	else:
		print(response)


def get_medias_without_theme(client: JellyfinClient = None):
	"""
	Recover all medias (movies, tv shows, etc.) from a jellyfin instance

	:param client: A jellyfin instance
	:return:
	"""

	if client is None:
		return

	output = []

	# print(client.jellyfin.items())
	movies = client.jellyfin.user_items(params={
		'Recursive': True,
		'hasThemeSong': False,
		'includeItemTypes': ("Movie")
	})

	"""for item in outuput['Items']:

		movie = client.jellyfin.get_item(item["Id"])

		print(os.path.dirname(movie["MediaSources"][0]["Path"]))
		# print(client.jellyfin.get_item(item["Id"]))"""

	series = client.jellyfin.user_items(params={
		'Recursive': True,
		'hasThemeSong': False,
		'includeItemTypes': ("Series")
	})

	output.extend(movies["Items"])
	output.extend(series["Items"])

	return output


def download_themes(client: JellyfinClient = None, medias=None, pause_between_downloads=0):

	if client is None or medias is None:
		return

	if not isinstance(pause_between_downloads, int):
		raise ValueError("pause_between_downloads must be an int")

	if pause_between_downloads < 0:
		raise ValueError("pause_between_downloads must be greater than 0")

	for item in medias:
		print()

		name = item["Name"]
		print(f"Downloading theme for : {name}")
		media = client.jellyfin.get_item(item["Id"])

		try:
			path = os.path.dirname(media["MediaSources"][0]["Path"])
			url = youtube_utils.search_for_theme(name)

			if url == "":
				continue

			print(f"The file will be stored here : {path}")

			if pause_between_downloads > 0:
				time.sleep(pause_between_downloads)

			filename = youtube_utils.youtube2mp3(url)
			os.rename(filename, f"{path}/theme.mp3")

		except KeyError:

			media = client.jellyfin.get_item(item["Id"])
			path = media["Path"]
			print(f"Error, downloading show theme for : {name}")
			print(f"The file will be stored here : {path}")
			url = youtube_utils.search_for_theme(name)

			if url == "":
				continue

			if pause_between_downloads > 0:
				time.sleep(pause_between_downloads)

			filename = youtube_utils.youtube2mp3(url, path)
			os.rename(filename, f"{path}/theme.mp3")

		except:
			continue

