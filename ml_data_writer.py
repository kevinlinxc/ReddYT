from reddit_lib import MetaComment, MetaPost

posts_file = "posts.csv"
comments_file = "comments.csv"


def write_post_to_csv(post: MetaPost, accepted: bool):
    with open(posts_file, 'a') as f:
        f.write(f"{post.post_id},{post.text},{accepted}\n")


def write_comment_to_csv(comment: MetaComment, accepted: bool):
    with open(comments_file, 'a') as f:
        f.write(f"{comment.post_id},{comment.comment_id},{comment.text},{accepted}\n")
