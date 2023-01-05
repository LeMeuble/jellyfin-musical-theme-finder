import os
import youtube_dl

from youtube_search import YoutubeSearch
from pytube import YouTube
from pathlib import Path


def search_for_theme(query, convert_to_theme=True):
    """
    Search for the theme of a specified input (movie, tv show...)

    :param query: The name of the media (must be a string)
    :param convert_to_theme: If the program automatically add "theme" at the end of a query missing it
    :return: A dict containing infos about the theme
    """

    if not isinstance(query, str):
        raise TypeError("String expected as a query !")

    if isinstance(query, str):

        if not query.endswith(" theme") and convert_to_theme:

            query += " theme"

    results = YoutubeSearch(query, max_results=1).to_dict()

    return results[0]


def youtube2mp3(url=None, output_directory=""):
    """
    Download a YouTube video to mp3, to a specified directory.

    :param url: The url of the video to download
    :param output_directory: The path to the directory to store the file (by default, current directory)
    :return: None
    """

    video_info = youtube_dl.YoutubeDL().extract_info(url=url, download=False)
    filename = f"{video_info['title']}mp3"
    options = {
        'format': 'bestaudio/best',
        'keepvideo': False,
        'outtmpl': filename,
    }
    with youtube_dl.YoutubeDL(options) as ydl:
        ydl.download([video_info['webpage_url']])

    # Check success of download
    if os.path.exists(filename):
        print(f'{video_info["title"]} has been successfully downloaded.')
    else:
        print(f'ERROR: {video_info["title"]} could not be downloaded!')

