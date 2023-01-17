import os
import youtube_dl

from youtube_search import YoutubeSearch


def search_for_theme(query, convert_to_theme=True, duration_max=5):
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

    results = YoutubeSearch(query, max_results=10).to_dict()

    for videos in results:
        duration = videos['duration'].split(":")

        if len(duration) == 3:
            continue
        elif len(duration) == 2:
            if int(duration[0]) <= duration_max:
                return videos['id']

    return ""


def youtube2mp3(url=None, output_directory=""):
    """
    Download a YouTube video to mp3, to a specified directory.

    :param url: The url of the video to download
    :param output_directory: The path to the directory to store the file (by default, current directory)
    :return: None
    """

    if url is None:
        raise ValueError("Please enter an url")

    if not isinstance(url, str):
        raise ValueError("URL must be a string")

    if not url.startswith("www.youtube.com/watch?v="):
        url = "www.youtube.com/watch?v=" + url

    video_info = youtube_dl.YoutubeDL().extract_info(url=url, download=False)
    filename = f"{video_info['title'].replace('/', '')}.mp3"
    print(f"The filename will be : {filename} (called from youtube2mp3)")
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

    print()

    return filename