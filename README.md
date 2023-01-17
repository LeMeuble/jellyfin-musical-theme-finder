# jellyfin-musical-theme-finder

---

This program will download for you the musical themes for the movies/shows you have on your jellyfin server.

## Requirements:

---

- Access to the machine where your jellyfin server is installed
- All your movies should be on their dedicated folders, as described on the [official documentation](https://jellyfin.org/docs/general/server/media/movies)
- Python 3
- The following python libraries :
  - jellyfin_apiclient_python
  - youtube_dl
  - youtube_search
- Make sure the user you start the program with has write permissions on the folders where your medias are located !

## Usage:

---

- Put the files on the machine you have jellyfin installed on (you can put them in a dedicated folder)
- Start main.py
- Enter server IP (should be 127.0.0.1)
- Enter your credentials
- Wait for the program to finish 
- Refresh your jellyfin libraries 

---

## Todo:

---

- [ ] Put all the code in one file
- [ ] Beautify logs
- [ ] Comment the code
- [ ] Make the connection to the server automatic, and add a function to make it run every set time
- [ ] Make installation easier (requirements.txt...)