from reddit_lib import MetaComment, MetaPost

posts_file = "ML/posts.csv"
comments_file = "ML/comments.csv"



def remove_non_ascii(text):
    return ''.join([i if ord(i) < 128 else ' ' for i in text])

def write_post_to_csv(post: MetaPost, accepted: bool):
    with open(posts_file, 'a') as f:
        f.write(f"{post.post_id},{remove_non_ascii(post.text)},{accepted}\n")


def write_comment_to_csv(comment: MetaComment, accepted: bool):
    with open(comments_file, 'a') as f:
        f.write(f"{comment.post_id},{comment.comment_id},{remove_non_ascii(comment.text)},{accepted}\n")
