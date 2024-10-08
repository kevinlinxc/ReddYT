import time
from selenium import webdriver
from selenium.common.exceptions import ElementNotVisibleException, ElementClickInterceptedException, \
    ElementNotInteractableException
from pyshadow.main import Shadow
import asyncpraw as praw
import logging
import shutil

handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
for logger_name in ("asyncpraw", "asyncprawcore"):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
from dataclasses import dataclass
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass
class MetaPost:
    """A class to hold the metadata of a Reddit post."""
    text: str  # title
    post_id: str
    nsfw: bool
    score: int
    path_to_image: Optional[str] = None


@dataclass
class MetaComment:
    """A class to hold the metadata of a Reddit comment."""
    text: str
    post_id: str
    comment_id: str
    path_to_image: Optional[str] = None


class PostWithComments:
    """
    A class to hold a Reddit post and its comments together. Used as the main data structure being passed around
    for this project.
    """

    def __init__(self, post: MetaPost, comments: list, subreddit: str):
        self.post = post
        self.comments = comments
        self.subreddit = subreddit


class PostFailedToCapture(Exception):
    pass


class CommentFailedToCapture(Exception):
    pass


async def get_top_n_posts(praw_inst, subreddit, n, time_filter="day"):
    """Get the IDs of the top n posts from a subreddit.

    Args:
        subreddit (str): The name of the subreddit to get posts from.
        n (int): The number of posts to get.
        :param time_filter:
    Returns:
        list: A list of post IDs.

    """
    # ignore nsfw posts, they have an annoying modal, and we don't want them on YouTube anyway
    return_list = []
    posts_found = 0
    sub = await praw_inst.subreddit(subreddit)
    async for post in sub.top(time_filter=time_filter):
        if not post.over_18:
            return_list.append(MetaPost(text=post.title, post_id=post.id, nsfw=post.over_18, score=post.score))
            posts_found += 1
            if posts_found == n:
                break
    print(f"Found {posts_found} posts")
    return return_list


async def search_subreddit(praw_inst, subreddit, query, n=5):
    """Search a subreddit for a query.

    Args:
        subreddit (str): The name of the subreddit to search.
        query (str): The query to search for.
        n (int): The number of posts to get.

    Returns:
        list: A list of post IDs.

    """
    return_list = []
    posts_found = 0
    sub = await praw_inst.subreddit(subreddit)
    async for post in sub.search(query, limit=n, sort="top"):
        if not post.over_18:
            return_list.append(MetaPost(text=post.title, post_id=post.id, nsfw=post.over_18, score=post.score))
            posts_found += 1
            if posts_found == n:
                break
    print(f"Found {posts_found} posts")
    return return_list

def get_posts(praw_inst, ids):
    return_list = []
    for id in ids:
        post = praw_inst.submission(id=id)
        return_list.append(MetaPost(text=post.title, post_id=post.id, nsfw=post.over_18))
    return return_list


def get_top_n_comments_from_post(praw_inst, post_id, n):
    """Get the top n comments from a post.

    Args:
        post_id (str): The ID of the post to get comments from.
        n (int): The number of comments to get.

    Returns:
        list: A list of comments.
    """
    post = praw_inst.submission(id=post_id)
    post.comments.replace_more(limit=0)
    return [MetaComment(text=comment.body, post_id=comment.link_id, comment_id=comment.id) for comment in
            post.comments[:n]]


async def async_get_top_n_comments_from_post(praw_inst, post_id, n):
    """Get the top n comments from a post.

    Args:
        post_id (str): The ID of the post to get comments from.
        n (int): The number of comments to get.

    Returns:
        list: A list of comments.
    """
    print("Getting top n comments from post with id: " + post_id)
    post = await praw_inst.submission(post_id)
    await post.comments.replace_more(limit=0)
    comments = post.comments._comments[:n]
    return [MetaComment(text=comment.body, post_id=comment.link_id, comment_id=comment.id) for comment in
            comments]


def capture_reddit_mobile_post_card(post_id, image_path, nsfw=False):
    """Capture a screenshot of the mobile preview card for a Reddit post.

    Args:
        post_id (str): The ID of the Reddit post to capture.
        image_path (str): The path to save the image to.
    Returns none
    """
    # Set up the Chrome driver with mobile device emulation
    if nsfw:
        driver = webdriver.Chrome()
    else:
        mobile_emulation = {
            "deviceMetrics": {"width": 400, "height": 700, "pixelRatio": 3.0},
            "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 10_3 like Mac OS X) AppleWebKit/602.1.50 (KHTML, like Gecko) CriOS/56.0.2924.75 Mobile Safari/535.19"
        }
        options = webdriver.ChromeOptions()
        options.add_experimental_option("mobileEmulation", mobile_emulation)
        driver = webdriver.Chrome(options=options)
    driver.execute_script("document.body.style.zoom='120%'")

    # Navigate to the post and wait for the preview card to load
    driver.get(f"https://www.reddit.com/{post_id}")
    shadow = Shadow(driver)
    shadow.set_explicit_wait(10, 2)
    continue_button = shadow.find_element_by_xpath('//*[@id="secondary-button"]/span/span')
    continue_button.click()

    preview_card_element = shadow.find_element_by_xpath(f'//*[@id="t3_{post_id}"]')
    with open(image_path, "wb") as f:
        f.write(preview_card_element.screenshot_as_png)
    driver.quit()


def capture_reddit_comment_mobile(post_id, comment_id, image_path, subreddit, retry=False):
    """Capture a screenshot of the mobile preview card for a Reddit post's comment.

    Args:
        post_id (str): The ID of the Reddit post to capture.
        comment_id (str): The ID of the comment to capture.
        image_path (str): The path to save the image to.
        subreddit (str): The subreddit the post is in (to form the URL)
    """
    # Set up the Chrome driver with mobile device emulation
    mobile_emulation = {
        "deviceMetrics": {"width": 400, "height": 700, "pixelRatio": 3.0},
        "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 10_3 like Mac OS X) AppleWebKit/602.1.50 (KHTML, like Gecko) CriOS/56.0.2924.75 Mobile Safari/535.19"
    }
    options = webdriver.ChromeOptions()
    options.add_experimental_option("mobileEmulation", mobile_emulation)
    driver = webdriver.Chrome(options=options)
    driver.execute_script("document.body.style.zoom='120%'")

    # Navigate to the post and wait for the preview card to load
    driver.get(f"https://www.reddit.com/r/{subreddit}/comments/{post_id}/comment/{comment_id}")
    shadow = Shadow(driver)
    shadow.set_explicit_wait(10, 2)
    continue_button = shadow.find_element_by_xpath('//*[@id="secondary-button"]/span/span')
    continue_button.click()

    # close the comments thread so the screenshot only captures the first comment
    try:
        shadow.find_element('[id="comment-fold-button"]').click()
    except ElementNotVisibleException:  # some comments might not have replies, ignore
        pass
    except (ElementClickInterceptedException, ElementNotInteractableException):
        print("Warning, comment is probably longer than the screen")
        pass
    try:
        comment_element = shadow.find_element(f'[thingid="t1_{comment_id}"]')

        with open(image_path, "wb") as f:
            f.write(comment_element.screenshot_as_png)
        driver.quit()
    except ElementNotVisibleException as e:
        if retry:
            raise e
        capture_reddit_comment_mobile(post_id, comment_id, image_path, subreddit, retry=True)


# Sign in to Reddit using API Key
def create_reddit():
    return praw.Reddit(user_agent="Fetching top posts to compile into an informative video",
                       client_id=os.environ['reddit_client_id'],
                       client_secret=os.environ['reddit_client_secret'],
                       username=os.environ['reddit_username'],
                       password=os.environ['reddit_password'],
                       timeout=30)


reddit = create_reddit()


def get_n_posts_with_m_comments(subreddit, n, m, prime=None):
    """
    Get the top n posts from a subreddit, and the top m comments from each post.
    If prime is given (a list of string ids), ignore n and use the ids in prime instead.
    This is the main function that ties everything together.
    It returns a list of PostWithComments objects
    """
    if m > 17:
        raise RuntimeError("M cant be greater than 17, or else discord won't have enough reactions.")
    if prime is None:

        print(f"1. Getting top {n} posts from r/{subreddit} with {m} comments each")
        posts = get_top_n_posts(reddit, subreddit, n)
    else:
        print(f"Ignoring n, using ids from prime")
        posts = get_posts(reddit, prime)

    successful_meta_posts_with_comments = []
    for index, meta_post in enumerate(posts):
        print(f"Post {index + 1}: {meta_post.text}")
        images_dir = os.path.join(os.getcwd(), "images")
        image_path = os.path.join(images_dir, f"{meta_post.post_id}", f"{meta_post.post_id}.png")
        meta_post.path_to_image = image_path
        try:
            capture_reddit_mobile_post_card(meta_post.post_id, image_path, nsfw=meta_post.nsfw)
        except Exception as e:
            print(f"Failed to capture post {meta_post.post_id} with error: {e}")
            raise PostFailedToCapture(e)

        comments = get_top_n_comments_from_post(reddit, meta_post.post_id, m)
        meta_comment: MetaComment
        print("\t Comments:")

        successful_meta_comments = []
        for com_index, meta_comment in enumerate(comments):
            print(f"\t {com_index + 1}: {meta_comment.text}")
            image_path = os.path.join(images_dir, f"{meta_post.post_id}", f"{meta_post.post_id}_{meta_comment.comment_id}.png")
            try:
                capture_reddit_comment_mobile(meta_post.post_id, meta_comment.comment_id, image_path, subreddit)
                meta_comment.path_to_image = image_path
                successful_meta_comments.append(meta_comment)
            except Exception as e:
                print(f"Failed to capture comment {meta_comment.comment_id} with error: {e}")
                raise CommentFailedToCapture(e)
        if len(successful_meta_comments) == 0:
            print("Failed to capture any comments for this post. Skipping...")
        else:
            # posts AND their comments succeeded, so make a PostWithComments object
            successful_meta_posts_with_comments.append(PostWithComments(meta_post, successful_meta_comments, subreddit))
    if len(successful_meta_posts_with_comments) == 0:
        raise Exception(f"Failed to capture any posts or comments.")
    print(f"Successfully captured {len(successful_meta_posts_with_comments)} posts with comments.")
    return successful_meta_posts_with_comments


def get_images_for_post_with_comments(post_with_comments: PostWithComments):
    """
    Given a PostWithComments object, download the images for the post and its comments
    """
    meta_post = post_with_comments.post
    images_dir = os.path.join(os.getcwd(), "images")
    post_dir = os.path.join(images_dir, f"{meta_post.post_id}")
    if os.path.exists(post_dir):
        shutil.rmtree(post_dir)
    os.mkdir(os.path.join(images_dir, f"{meta_post.post_id}"))
    image_path = os.path.join(images_dir, f"{meta_post.post_id}", f"{meta_post.post_id}.png")
    print(f"Fetching image for post")
    try:
        capture_reddit_mobile_post_card(meta_post.post_id, image_path, nsfw=meta_post.nsfw)
        meta_post.path_to_image = image_path
    except Exception as e:
        print(f"Failed to capture post {meta_post.post_id} with error: {e}")
        raise PostFailedToCapture(e)

    comments = post_with_comments.comments
    meta_comment: MetaComment
    print("\t Fetching images for comments:")

    successful_meta_comments = []
    for com_index, meta_comment in enumerate(comments):
        print(f"\t {com_index + 1}: {meta_comment.text}")
        image_path = os.path.join(images_dir, f"{meta_post.post_id}", f"{meta_post.post_id}_{meta_comment.comment_id}.png")
        try:
            capture_reddit_comment_mobile(meta_post.post_id, meta_comment.comment_id, image_path, post_with_comments.subreddit)
            meta_comment.path_to_image = image_path
            successful_meta_comments.append(meta_comment)
        except Exception as e:
            print(f"Failed to capture comment {meta_comment.comment_id} with error: {e}")
            raise CommentFailedToCapture(e)
    if len(successful_meta_comments) == 0:
        print("Failed to capture any comments for this post. Skipping...")
    else:
        # posts AND their comments succeeded, so make a PostWithComments object
        return PostWithComments(meta_post, successful_meta_comments, post_with_comments.subreddit)


if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv()
    get_n_posts_with_m_comments("AskReddit", 1, 5)
