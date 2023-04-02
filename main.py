import reddit_lib
import video_creator
import discord_lib


# functions that each produce a video/videos for the YouTube channels
def make_askreddit_video():
    # 1. Get the popular recent posts
    posts_with_comments = reddit_lib.get_n_posts_with_m_comments("AskReddit", 5, 10)

    # 2. send to Discord for curation
    curated_posts = discord_lib.curate(posts_with_comments, discord_lib.dummy_callback)

    # 3.



    pass


def make_showerthoughts_video():
    pass