import discord
from discord.ext import commands
import datetime  # Used for timestamps
from collections import Counter  # Used to count the users.
import json  # Used to create the file the animation software uses.


class Admin(commands.Cog, name="admin"):
    """Admin commands. Mostly just fun things for me to toy with, sometimes test, rarely useful."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name=f"bar_fetch")
    async def bar_fetch(self, ctx):
        if not await self.bot.has_perm(ctx, admin=True, message_on_fail=False): return
        # ==== Customization variables ==== #
        top_users = 10  # How many users will be displayed in the animation.
        capture_interval = 86400  # How regularly, in seconds, to capture the state of the counter.
        keyframes_path = "top_members.csv"  # Where to save the data to.
        date_format = "%Y-%m-%d"  # Currently set to year-month-day. See datetime.strftime for formatting options.

        # This system of copying the counters is a bit memory inefficient.
        # There might be more efficient ways to do this, but until it's an issue it's fine.
        keyed_frames = []  # Stores the counter at each recorded moment.
        top_users_buffer = top_users + 5  # How many users we'll record each capture. Used for animation reasons.
        with open(keyframes_path, "w") as f:
            f.writelines(f"{top_users},{top_users_buffer}\n")  # Metadata

        message_count = 0  # Total messages done. Used to give updates on progress.
        c = Counter()  # This counts how many messages each user has sent so far.

        # Get the first message to use as a starting point for the animation.
        first_message = await ctx.channel.history(limit=1, oldest_first=True).flatten()
        first_message = first_message[0]
        c[first_message.author.name] += 1  # Add this message to the counter.
        start_snowflake = first_message.id
        while True:  # For me, this takes around 7 seconds each loop to search 1000 messages
            end_snowflake = add_to_snowflake(start_snowflake, capture_interval)  # One day later...

            # We've caught up to the current day!
            if discord.utils.snowflake_time(end_snowflake) >= datetime.datetime.now():
                break

            # Count each message for each person on this day...
            async for message in ctx.channel.history(limit=None, after=discord.Object(start_snowflake), before=discord.Object(end_snowflake), oldest_first=True):
                c[message.author.name] += 1

            # Create a row for our data sheet...
            current_tops = c.most_common(top_users_buffer)
            current_date = discord.utils.snowflake_time(start_snowflake).strftime(date_format)
            users = []
            for user in current_tops:
                user_dict = {
                    "ident": user[0],
                    "count": user[1],
                    "label": "",
                    "col": ""
                }
                users.append(user_dict)

            # Add the keyframe to the file...
            keyframe = [current_date, users]
            with open(keyframes_path, "a") as f:
                f.write(f"{json.dumps(keyframe)}\n")

            start_snowflake = end_snowflake
            message_count += 1
            if message_count >= 60:
                break
        print(c)


        #await ctx.send("Got")

def add_to_snowflake(snowflake, seconds):
    return snowflake + (seconds * 1000 << 22)


def setup(bot):
    bot.add_cog(Admin(bot))


def teardown(bot):
    bot.remove_cog(Admin(bot))
