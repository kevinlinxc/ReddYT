import discord
from discord.ext import commands
import ml_data_writer
import asyncio
import os
from dotenv import load_dotenv
import trends_lib
import reddit_lib
import video_creator
import youtube_lib


async def main():
    load_dotenv()
    channel_id = 1092145376846434405
    bot_token = os.environ.get('DISCORD_TOKEN')
    current_posts = None
    current_subreddit = None
    client = commands.Bot(intents=discord.Intents.all(), command_prefix="!")
    reddit = reddit_lib.create_reddit()

    @client.event
    async def on_ready():
        # gets called when the bot is first online, which is after client.start() is called at the bottom of the file
        channel = client.get_channel(channel_id)
        await channel.send("Reddyt bot is ready!")

    @client.command(aliases=['trends', 'trend', 't'], brief='trends',
                    description='options: add a number after to get that many trends')
    async def get_trends(ctx, arg1="dog1"):
        """
        Fetches trends from pytrends to inform user of what to search on Reddit
        :param ctx: discord context, passed in automatically from client.command
        :param arg1: number of trends to fetch
        :return: None, sends to channel
        """
        if arg1.isdigit():
            trends = trends_lib.get_top_n_trends(int(arg1))
        else:
            trends = trends_lib.get_top_n_trends()
        await ctx.send('Top trends: ' + '\n '.join(trends))

    @client.command(aliases=['ask'],
                    description="Get top posts from AskReddit. Can pass time filter e.g. day, hour, month and a number "
                                "of posts. Default: !askreddit day 5")
    async def askreddit(ctx, arg1="day", arg2=5):
        """
        Fetches top posts from AskReddit and sets them as the current posts
        :param ctx: Discord context
        :param arg1: time filter
        :param arg2: number of posts
        :return: None, sets current_posts
        """
        print("!askreddit called")
        if arg1 not in ["all", "day", "hour", "month", "week", "year"]:
            await ctx.send('Invalid time filter, please try again')
            return
        posts = await reddit_lib.get_top_n_posts(reddit, "askreddit", arg2, time_filter=arg1)
        global current_posts
        current_posts = posts
        global current_subreddit
        current_subreddit = "askreddit"
        await ctx.send(f"Here are the top {arg2} posts in the last {arg1}:")
        await print_current_posts(ctx)
        await ctx.send("Use !pick <number> to pick a post to fetch comments for.")

    @client.command(aliases=['current', 'posts', 'print'],
                    description="View the current posts again")
    async def print_current_posts(ctx):
        """
        Prints the current posts on discord to remind the user of what the current posts are.
        """
        global current_posts
        if current_posts is None:
            await ctx.send("No posts currently")
            return
        message = ""
        for index, post in enumerate(current_posts):
            message += f"{index + 1}: {post.text}, score: {post.score}\n"
        await ctx.send(message)

    @client.command(aliases=['p', "comments"],
                    description="Pick a post from the current stored posts to get comments for")
    async def pick(ctx, arg1="1"):
        print("!pick called")
        if not arg1.isdigit():
            await ctx.send("Please enter a number as the first argument")
            return
        global current_posts
        if current_posts is None:
            await ctx.send("No posts currently")
            return
        if int(arg1) > len(current_posts):
            await ctx.send("Please enter a valid number")
            return
        post = current_posts[int(arg1) - 1]
        await ctx.send(f"Fetching comments for post: \"{post.text}\"")

        comments = await reddit_lib.async_get_top_n_comments_from_post(reddit, post.post_id, 10)
        global current_subreddit
        post_with_comments = reddit_lib.PostWithComments(post, comments, current_subreddit)
        curated_post = await curate_post_comments(ctx, post_with_comments)
        if curated_post is None:
            await ctx.send("Post cancelled.")
            return
        status = await ctx.send("Comments chosen, fetching images...")
        with_images = reddit_lib.get_images_for_post_with_comments(curated_post)
        await status.edit(content="Images fetched, creating video")
        video_path = video_creator.make_video_from_post_with_comments(with_images)
        print("Posting video to Discord for approval/upload.")
        await confirm_video(ctx, video_path, curated_post)

    async def curate_post_comments(ctx, post_with_comments: reddit_lib.PostWithComments):
        """
            Send post and comments in text form to Discord, and wait for emoji reactions to choose the comments
            Letter emojis are used to select comments, and check/x emojis are used to confirm/cancel.
            :param post_with_comments: The post and comments to send to Discord
            :param callback: A callback function that takes a curated PostWithComments object as an argument
        """
        # future = asyncio.Future()
        # future.add_done_callback(callback)
        comments: list[reddit_lib.MetaComment] = post_with_comments.comments
        n = len(comments)

        # create the message with the question and answers
        message = ""
        for i in range(n):
            tentative_message = message  # tentative message logic is just for if we go over the 2000 character limit
            tentative_message += f'{chr(65 + i)}: {comments[i].text}\n'
            if len(tentative_message) > 2000:
                await ctx.send(message)
                message = ""
            else:
                message = tentative_message
        message += '\nReact with the letters of your chosen answers and ✅ to confirm or ❌ to cancel. ' \
                   '\nYou can also react with 👍 to select all the comments.'

        sent_message = await ctx.send(message)

        # add the reactions
        for i in range(n):
            await sent_message.add_reaction(chr(127462 + i))  # add the regional_indicator reactions
        await sent_message.add_reaction('✅')  # for confirming comment selection
        await sent_message.add_reaction('❌')  # for declining the post
        await sent_message.add_reaction('👍')  # for okaying all the comments

        letter_react_unicode = set([chr(127462 + i) for i in range(n)])

        def check(reaction, user):
            return user != client.user and str(reaction.emoji) in letter_react_unicode.union({'✅', '❌', '👍'})

        while True:
            try:
                reaction, user = await client.wait_for('reaction_add', timeout=None, check=check)
                if str(reaction.emoji) == '👍':
                    # update sent_message
                    ml_data_writer.write_post_to_csv(post_with_comments.post, True)
                    for comment in comments:
                        ml_data_writer.write_comment_to_csv(comment, True)
                    confirmation_message = f"Okayed all comments"
                    await ctx.send(confirmation_message)
                    print(confirmation_message)
                    return post_with_comments
                elif str(reaction.emoji) == '✅':
                    # update sent_message
                    sent_message = await ctx.fetch_message(sent_message.id)
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

                    confirmation_message = f"Picked comments {', '.join([str(reaction.emoji) for reaction in sent_message.reactions if str(reaction.emoji) in letter_react_unicode and reaction.count > 1])}"
                    await ctx.send(confirmation_message)
                    print(confirmation_message)
                    return post_with_comments
                elif str(reaction.emoji) == '❌':
                    await ctx.send("Declined post.")
                    ml_data_writer.write_post_to_csv(post_with_comments.post, False)
                    return
            except asyncio.TimeoutError:
                return

    async def confirm_video(ctx, video_path, post_with_comments: reddit_lib.PostWithComments):
        with open(video_path, 'rb') as f:
            video = discord.File(f)

        # Create the buttons and their corresponding functions
        async def upload_button_callback(interaction: discord.Interaction):
            await interaction.response.send_message('Uploading to YouTube...')
            video.close() # maybe necessary to be able to open the file while uploading it
            f.close()
            if post_with_comments.subreddit == 'askreddit':
                yt_link = youtube_lib.upload_to_askreddit_channel(video_path, post_with_comments.post.text)
                await interaction.response.edit_message(content=f'Uploaded to YouTube: {yt_link}')

        async def get_path_button_callback(interaction: discord.Interaction):
            await interaction.response.send_message(video_path)
            # remove the buttons
            view.stop()

        async def done_button_callback(interaction: discord.Interaction):
            view.stop()

        upload_button = discord.ui.Button(style=discord.ButtonStyle.green, label='Upload')
        upload_button.callback = upload_button_callback

        get_path_button = discord.ui.Button(style=discord.ButtonStyle.gray, label='Print Path')
        get_path_button.callback = get_path_button_callback

        done_button = discord.ui.Button(style=discord.ButtonStyle.red, label='Done')
        done_button.callback = done_button_callback

        # Create the view and add the buttons to it
        view = discord.ui.View()
        view.add_item(upload_button)
        view.add_item(get_path_button)
        view.add_item(done_button)

        # Send the file and buttons to the channel
        await ctx.send(file=video, view=view)

    await client.start(bot_token)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
