import discord
import ml_data_writer
import asyncio
from reddit_lib import PostWithComments, MetaComment, MetaPost
import os

channel_id = 912261061233750109
bot_token = os.environ.get('DISCORD_TOKEN')


async def curate(post_with_comments: PostWithComments, callback):
    """
        Send post and comments in text form to Discord, and wait for emoji reactions
        Letter emojis are used to select comments, and check/x emojis are used to confirm/cancel.
        :param post_with_comments: The post and comments to send to Discord
        :param callback: A callback function that takes a curated PostWithComments object as an argument
    """

    client = discord.Client(intents=discord.Intents.all())

    future = asyncio.Future()
    future.add_done_callback(callback)

    async def _curate(channel):
        comments: list[MetaComment] = post_with_comments.comments
        n = len(comments)

        # create the message with the question and answers
        message = 'Post: ' + post_with_comments.post.text + '\n\nComments:\n'
        for i in range(n):
            message += f'{chr(65 + i)}: {comments[i].text}\n'
        message += '\nReact with the letters of your chosen answers and ✅ to confirm or ❌ to cancel.'

        sent_message = await channel.send(message)

        # add the reactions
        for i in range(n):
            await sent_message.add_reaction(chr(127462 + i))  # add the regional_indicator reactions
        await sent_message.add_reaction('✅')  # add the check reaction
        await sent_message.add_reaction('❌')  # add the X reaction

        letter_react_unicode = set([chr(127462 + i) for i in range(n)])

        def check(reaction, user):
            return user != client.user and str(reaction.emoji) in letter_react_unicode.union({'✅', '❌'})

        while True:
            try:
                reaction, user = await client.wait_for('reaction_add', timeout=None, check=check)
                if str(reaction.emoji) == '✅':
                    # update sent_message
                    sent_message = await channel.fetch_message(sent_message.id)
                    ml_data_writer.write_post_to_csv(post_with_comments.post, True)
                    #
                    chosen_answers = [comments[ord(reaction.emoji) - 127462] for reaction in sent_message.reactions if
                                      str(reaction.emoji) in letter_react_unicode and reaction.count > 1]
                    for comment in comments:
                        if comment in chosen_answers:
                            ml_data_writer.write_comment_to_csv(comment, True)
                        else:
                            ml_data_writer.write_comment_to_csv(comment, False)
                    post_with_comments.comments = chosen_answers

                    await channel.send(
                        f"Picked comments {', '.join([str(reaction.emoji) for reaction in sent_message.reactions if str(reaction.emoji) in letter_react_unicode and reaction.count > 1])}")
                    future.set_result(post_with_comments)
                    return
                elif str(reaction.emoji) == '❌':
                    ml_data_writer.write_post_to_csv(post_with_comments.post, False)
                    future.set_result(None)
                    return
            except asyncio.TimeoutError:
                future.set_result(None)
                return None

    @client.event
    async def on_ready():
        # using an on_ready callback was the only way for me to send a message for some reason (at least in a linear
        # script)
        channel = client.get_channel(channel_id)
        await _curate(channel)
        await client.close()

    await client.start(bot_token)
    return future


async def notify(message):
    """Function that just sends a message to the channel, to be used for exceptions etc."""
    client = discord.Client(intents=discord.Intents.all())

    async def _notify(channel):
        await channel.send(message)

    @client.event
    async def on_ready():
        channel = client.get_channel(channel_id)
        await _notify(channel)
        await client.close()

    await client.start(bot_token)


def dummy_callback(future: asyncio.Future):
    print(future.result())
    if isinstance(future.result(), PostWithComments):
        print(future.result().comments)


if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv()
    bot_loop = asyncio.get_event_loop()
    curated_post: asyncio.Future = bot_loop.run_until_complete(
        curate(PostWithComments(MetaPost("Test question", "128ukfw", "hi.png"),
                                [MetaComment("Test answer 1", "128ukfw",
                                             "128ukfw", "hi.png"),
                                 MetaComment("Test answer 2", "128ukfw",
                                             "128ukfw", "hi.png"),
                                 MetaComment("Test answer 3", "128ukfw",
                                             "128ukfw", "hi.png"),
                                 MetaComment("Test answer 4", "128ukfw",
                                             "128ukfw",
                                             "hi.png"), ], "AskReddit"), dummy_callback))
