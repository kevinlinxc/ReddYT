import reddit_lib
import video_creator
import discord_lib
import asyncio
from dotenv import load_dotenv
load_dotenv()


# functions that each produce a video/videos for the YouTube channels
def make_askreddit_video():
    try:
        # 0. Notify Discord that we're starting
        loop = asyncio.get_event_loop()
        loop.run_until_complete(discord_lib.notify("##############################\nStarting AskReddit video!\n\n"))
        # 1. Get the popular recent posts
        posts_with_comments = reddit_lib.get_n_posts_with_m_comments("AskReddit", 1, 5)

        # 2. send to Discord for curation
        for index, post_with_comment in enumerate(posts_with_comments):
            print(f"2. Sending post {index + 1} to Discord for curation")
            loop = asyncio.get_event_loop()
            # 3. Callback function makes video and posts it. Chooses where to post it using the subreddit
            loop.run_until_complete(discord_lib.curate(post_with_comment, video_creator.make_and_post_video))
    except Exception as e:
        print(f"Failed to make AskReddit video with error: {e}")
        discord_lib.notify(f"Failed to make AskReddit video with error: {e}")
        raise e


if __name__ == '__main__':
    make_askreddit_video()
