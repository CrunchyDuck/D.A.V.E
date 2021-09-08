import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import math
import pandas


class MatAnimation:
    def __init__(self, ax, bars_to_display, users, titles):
        self.ax = ax
        self.bars_to_display = bars_to_display
        self.users = users
        self.titles = titles

    def animate_frame(self, frame_num):
        self.ax.clear()
        style_graph(self.ax)
        #frame = self.frames[frame_num]
        positions = []
        bar_sizes = []
        cols = []
        labels = []
        self.ax.text(0.95, 0.15, self.titles[frame_num], transform=self.ax.transAxes, horizontalalignment="right", size=22)
        for user in self.users:
            y_pos = user.y_pos[frame_num]
            count = user.count[frame_num]
            if count == 0:
                continue

            cols.append(user.color)
            labels.append(user.name)
            bar_sizes.append(count)
            positions.append(y_pos)
            #if self.bars_to_display > y_pos > 0:  # Python 3.9 added this, and PyCharm wants me to use it.
            self.ax.text(count + 3, y_pos, round(count), verticalalignment="center")

        self.ax.barh(y=positions, width=bar_sizes, color=cols, tick_label=labels)
        #print(self.ax.get_ylim())
        #print(len(self.users))
        top = len(self.users)+0.5
        bottom = top - self.bars_to_display
        self.ax.set_ylim(bottom, top)  # Range of bars to show. This is offset by -0.5 so we don't cut the bars in half.
        #self.ax.set_title(self.titles[frame_num])
        return [self.ax]


class User:
    """Each user tracks their own animation data."""
    interp_per_update = 1/10  # How many frames it takes for the animation to complete.

    def __init__(self, name=None, color=None, default_pos=11):
        self.name = name  # Username
        self.color = color  # Colour of their bar. This is assigned by ColorTracker.get_color()

        self.count = []  # Number of messages
        self.y_pos = []  # Used by AnimationFrame

        # Used to interpolate towards new y positions.
        self.interp_pos = 0  # How far
        self.last_pos = None
        self.target_pos = default_pos

    def update_y_pos(self, position):
        if not self.y_pos:  # Initialization
            self.y_pos.append(position)
            self.last_pos = position
            self.target_pos = position

        if position == self.target_pos:  # Target hasn't changed.
            if self.interp_pos >= 1:  # Target reached
                self.y_pos.append(self.target_pos)
            else:
                self.interp_pos += self.interp_per_update
                self.y_pos.append(slerp(self.last_pos, self.target_pos, self.interp_pos))
        else:  # New target acquired.
            self.last_pos = self.y_pos[-1]
            self.target_pos = position
            #self.interp_pos = abs((self.y_pos[-1] - self.last_pos) / (self.target_pos - self.last_pos))
            self.interp_pos = 0
            self.update_y_pos(position)


def lerp(a, b, t):
    return a + (b-a) * t


def slerp(a, b, t):
    deg = t * 90
    new_t = math.sin(math.radians(deg))
    return lerp(a, b, new_t)


def style_graph(ax):
    """Formats the graph to look a little prettier."""
    ax.set_facecolor('.8')
    ax.tick_params(labelsize=8, length=5)
    ax.grid(True, axis='x', color='white')
    ax.set_axisbelow(True)
    [spine.set_visible(False) for spine in ax.spines.values()]


def prepare_dataframe(dataframe, expand_factor):
    # Expand out the dataframe
    dataframe = dataframe.reset_index()  # Not certain what this does but it's vital.
    dataframe.index = dataframe.index * expand_factor  # Change indexes from 0,1,2... to 0,30,60...
    last_index = dataframe.index[-1] + 1
    dataframe = dataframe.reindex(range(last_index))  # Inset empty rows between new indexes.
    dataframe["date"] = dataframe["date"].fillna(method="ffill")  # Fill in column

    # Interpolate values
    dataframe = dataframe.interpolate()
    #dataframe = dataframe.round()  # We can't have a fraction of a message.

    return dataframe


def get_colors(color_map, count):
    """Gets a list of colours to be used in matplotlib
    # See for colour mappings https://matplotlib.org/stable/gallery/color/colormap_reference.html
    """
    cols = plt.get_cmap(color_map, count + 1)  # +1 to prevent wrapping, where col 0 is same as col -1
    cols = cols(range(count + 1)).tolist()  # Create a list of colours
    return cols[:-1]  # Remove overlapping colour and return


def main(path, frames_per_keyed_frame, users_to_display):
    """
    data_file_path - Path to the .csv file containing
    """
    dataframe = pandas.read_csv(path, index_col="date")
    dataframe = prepare_dataframe(dataframe, frames_per_keyed_frame)
    user_cols = dataframe.columns.values.tolist()[1:]  # Removes date column
    users = [User(name=x, default_pos=-users_to_display) for x in user_cols]  # A list of all Users being tracked.
    # Give users colours
    cols = get_colors("twilight_shifted", len(users))
    for user, col in zip(users, cols):
        user.color = col

    dates = []
    for index, row in dataframe.iterrows():
        dates.append(row[0])
        row = row[1:]  # Removes date column
        rankings = pandas.Series(row, dtype="int64").rank(method="first")
        for user, count, ranking in zip(users, row, rankings):
            user.count.append(count)
            user.update_y_pos(ranking)

    fig = plt.Figure(figsize=(7, 6), dpi=144)
    ax = fig.add_subplot()
    animator = MatAnimation(ax, users_to_display, users, dates)
    #a = animator.animate_frame(60)[0]
    #fig.savefig("test.png")
    #return

    frame_num = dataframe.shape[0]
    frame_duration = (1 / 30) * 1000  # How long each frame lasts.
    anim = FuncAnimation(fig=fig, func=animator.animate_frame, frames=frame_num, interval=frame_duration, repeat=False)
    anim.save("test.mp4")


if __name__ == "__main__":
    # The path to the data recorded from the Discord bot.
    data_file_path = "top_members.csv"
    # How many frames each keyframes takes up. Note this is NOT framerate, which is always at 30 fps.
    # This is just how long each line is displayed for. E.G 5 lines at 60 will be a 10 second animation.
    frames_per_keyed_frame = 15

    users_to_display = 10
    main(data_file_path, frames_per_keyed_frame, users_to_display)
