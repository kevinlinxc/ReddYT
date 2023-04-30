from simple_youtube_api.Channel import Channel
from simple_youtube_api.LocalVideo import LocalVideo
import os
from dotenv import load_dotenv

load_dotenv()


def upload_to_askreddit_channel(video_path, title, unlisted=True):
    title = f"AskReddit: {title} #askreddit #reddit #shorts"
    print("Proposed title: ", title)
    if len(title) > 100:
        print("Warning: title is probably too long!")
    if os.environ['dry_run'] == "True":
        print(f"DRY RUN: Would have uploaded video {video_path} to Askreddit Vibes channel with title:\n {title}")
        return
    channel = Channel()
    channel.login(os.environ['youtube_application_credentials'], "credentials.storage")
    print("Uploading to Askreddit Vibes channel")
    video = LocalVideo(file_path=video_path)
    print("B")
    video.set_title(title)
    video.set_category("entertainment")
    video.set_default_language("en-US")
    visibility = "unlisted" if unlisted else "public"
    video.set_privacy_status(visibility)
    video.set_embeddable(True)
    video = channel.upload_video(video)
    print("C")
    video_link = f"https://www.youtube.com/watch?v={video.id}"
    print(f"Video uploaded: {video.title}, view it at {video_link}")
    return video_link


if __name__ == '__main__':
    video_link = upload_to_askreddit_channel("videos/133em4v_with_music.mp4",
                                             "What wouldn't you buy even if you were rich?")
