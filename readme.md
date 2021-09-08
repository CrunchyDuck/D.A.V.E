# D.A.V.E - Discord Activity Visual Envisioner
#### No life data visualization

Creates a bar chart race of user activity on a Discord server.
It's split into two parts: The Discord bot, and the graph script.

### Bot:
The bot's script is a Discord cog which is called with "bar_fetch" in the desired channel.
It will tally up all messages in that channel and create a top_members.csv file, containing data used to chart the top 10 active members in that channel each day.

### Graph:
The graphing script reads top_members.csv and generates a bar chart animation to show the position of users through time.