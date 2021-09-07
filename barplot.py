import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import sys
import json
import math
from collections import Counter

# About how we store data:
# It would use an unreasonable amount of space to track all message counts from all members for all dates.
# Over 1 year with 100,000 members, that'd be 36,500,000 entries! And we'd need to run lots of calculations on each entry!
# Instead, if we want the top 10 members, we'll keep only keep track of the top 15 at any point.
# That doesn't mean members that aren't in the top 15 are ignored - If they break into top 15 they'll start getting saved.
# This just saves a lot of storage space on data we wouldn't be using otherwise.
#
# The reason we save the top 15 instead of only the top 10 is to allow people to cleanly animate dropping in/out of the top rankings.
# Otherwise if someone leaves top 10, they'd just suddenly disappear and be replaced, rather than animate out.
#
# The data file itself is quite simple, based off of CSV files.
# The first line gives information about how the data was stored, e.g how many users were tracked at once.
# After that, each line represents 1 frame.
# Each line will have a date as the first value.
# After this, there will be 2 values for each member that was stored, their name and their message count.
# E.G if CrunchyDuck has 5 messages, and Dave has 10, the line would be:
# 2021-09-06,Dave,10,CrunchyDuck,5
# You can see that each value is separated by a comma. Each row should have the same number of entries.


class Keyframe:
    def __init__(self, name, count):
        self.name = name  # Username
        self.count = count  # Number of messages
        self.color = None  # Colour of their bar. This is assigned by ColorTracker.get_color()
        self.y_position = None  # Used by AnimationFrame

    # These functions allow comparisons to work between Keyframes, E.G dp1 < dp2.
    def __repr__(self):
        return f"[{self.name}, {self.count}, {self.color}, {self.y_position}]"

    def __lt__(self, other):
        return self.count < other.count

    def __gt__(self, other):
        return self.count > other.count

    def __eq__(self, other):
        return self.count == other.count

    def __le__(self, other):
        return self.count <= other.count

    def __ge__(self, other):
        return self.count >= other.count

    def __ne__(self, other):
        return self.count != other.count


class ColorTracker:
    """This object handles the assignment of colours to Keyframe objects.
    This is necessary to keep the colour of Keyframes constant while they're being tracked.
    When a Keyframe leaves the tracked list of members, its colour is taken from it and given to something else.
    """
    def __init__(self, colors):
        # These are all of the colours that haven't been claimed yet.
        self.unreserved_colors = colors

        # These are all of the colours reserved by Keyframes.
        # If any of these are unclaimed in last_frame at the end of the parsing, they're marked as unreserved - aka the Keyframe dropped out.
        # Stored as {Keyframe.name: color}
        self.reserved_colors_last_frame = {}
        self.reserved_colors_this_frame = {}

        # A list of Keyframes that have requested a colour, and are waiting.
        # When a colour is available, which will always inevitably happen, it's given to someone on this list.
        self.data_points_awaiting_color = []

    def get_color(self, dp: Keyframe):
        """Gets the colour this data point had last frame. If not found, puts it in the waiting line for colours."""
        if dp.name in self.reserved_colors_last_frame:
            col = self.reserved_colors_last_frame.pop(dp.name)
            dp.color = col
            self.reserved_colors_this_frame[dp.name] = col
        else:
            self.data_points_awaiting_color.append(dp)

    def finish_frame(self):
        """Should be called at the end of each frame.
        This fills reserved_colors_last_frame and assigns all data_points_awaiting_color
        """
        # Put any remaining colours into the unclaimed colours bag.
        self.unreserved_colors += self.reserved_colors_last_frame.values()

        for dp in self.data_points_awaiting_color:  # New arrivals to the ranked peeps
            col = self.unreserved_colors.pop(0)  # Get colour
            self.reserved_colors_this_frame[dp.name] = col  # Reserve colour
            dp.color = col  # Apply colour

        self.data_points_awaiting_color = []
        self.reserved_colors_last_frame = self.reserved_colors_this_frame
        self.reserved_colors_this_frame = {}


class AnimationFrame:
    """A frame contains all keyframes in a frame."""

    def __init__(self, title=None):
        self.title = title  # Date to display on the timelapse.
        self.keyframes = {}


class MatAnimation:
    def __init__(self, ax, bars_to_display, frames):
        self.ax = ax
        self.bars_to_display = bars_to_display
        self.frames = frames

    def animate_frame(self, frame_num):
        self.ax.clear()
        style_graph(self.ax)
        frame = self.frames[frame_num]
        positions = []
        bar_sizes = []
        cols = []
        labels = []
        for k, keyframe in frame.keyframes.items():
            positions.append(keyframe.y_position)
            bar_sizes.append(keyframe.count)
            cols.append(keyframe.color)
            labels.append(keyframe.name)
            if self.bars_to_display > keyframe.y_position > 0:  # Python 3.9 added this, and PyCharm wants me to use it.
                self.ax.text(keyframe.count + 3, keyframe.y_position, round(keyframe.count), verticalalignment="center")

        self.ax.barh(y=positions, width=bar_sizes, color=cols, tick_label=labels)
        self.ax.set_ylim([self.bars_to_display - 0.5, -0.5])  # Range of bars to show. This is offset by -0.5 so we don't cut the bars in half.
        self.ax.set_title("test")
        return [self.ax]


def lerp(a, b, t):
    return a + (b-a) * t


def slerp(a, b, t):
    deg = t * 90
    new_t = math.sin(math.radians(deg))
    return lerp(a, b, new_t)


def parse_row_data(data: str):
    """Makes the values to use in the bar chart

    Returns:
        [date, list:Keyframes]
    """
    data = json.loads(data)

    date = data[0]
    users = data[1]
    data_points = []
    for user in users:
        name = user["ident"]
        count = user["count"]
        dp = Keyframe(name, count)
        data_points.append(dp)

    return date, data_points


def style_graph(ax):
    """Formats the graph to look a little prettier."""
    ax.set_facecolor('.8')
    ax.tick_params(labelsize=8, length=5)
    ax.grid(True, axis='x', color='white')
    ax.set_axisbelow(True)
    [spine.set_visible(False) for spine in ax.spines.values()]


def main():
    data_file_path = "keyframes.txt"
    data_file = open(data_file_path, "r")

    # == Constants == #
    file_metadata = data_file.readline().split(",")
    dp_display_number = int(file_metadata[0])  # How many Keyframes should be shown at once.
    dp_tracked_number = int(file_metadata[1])  # How many Keyframes in total are tracked. The extra values are used for animations.
    frames_per_keyed_frame = 60  # Distance between each keyed frame. Always at least 1.

    # == Loop initialization == #
    # Colours we'll be using.
    col_count = dp_tracked_number + 1  # We add one to prevent wrapping, where colour 0 is the same as colour -1
    cols = plt.get_cmap("twilight_shifted", col_count)  # See https://matplotlib.org/stable/gallery/color/colormap_reference.html
    cols = cols(range(col_count)).tolist()  # Convert the colours into scalar RGBA values.
    color_tracker = ColorTracker(cols)  # Object that handles bar colour assignment.
    keyed_frames = []

    data_line = data_file.readline()  # First line of data
    # ==== Create frame data ==== #
    while data_line:
        # Creates keyframes with a name and message count.
        date, keyframes = parse_row_data(data_line)

        # Get the colours for each bar.
        for keyframe in keyframes:
            color_tracker.get_color(keyframe)
        color_tracker.finish_frame()

        # Calculate ranking of data
        keyframes = sorted(keyframes, reverse=True)
        for i in range(len(keyframes)):
            keyframes[i].y_position = i

        # Save all keyframes to a frame.
        frame = AnimationFrame(date)  # Contains all keyframes, indexed by a unique identifier.
        for keyframe in keyframes:
            frame.keyframes[keyframe.name] = keyframe  # Each keyframe needs a unique identifier; In this case, the username.

        keyed_frames.append(frame)  # Add this frame to the list of frames
        data_line = data_file.readline()

    # ==== Fill in frame data ==== #
    frames = [AnimationFrame() for i in range(len(keyed_frames) * frames_per_keyed_frame)]
    for i in range(len(frames)):
        previous_keyed_frame_i = i//frames_per_keyed_frame
        next_keyed_frame_i = (i//frames_per_keyed_frame) + 1
        fraction_between_keyframes = (i % frames_per_keyed_frame) / frames_per_keyed_frame  # Used for interpolation

        # Get frames
        previous_keyed_frame = keyed_frames[previous_keyed_frame_i]
        next_keyed_frame = keyed_frames[next_keyed_frame_i] if next_keyed_frame_i < len(keyed_frames) else previous_keyed_frame
        this_frame = frames[i]

        # Interpolate between keyed frames.
        for k, keyframe in previous_keyed_frame.keyframes.items():
            if k not in next_keyed_frame.keyframes:  # User stopped being tracked. This should happen off-screen
                continue
            next_keyframe = next_keyed_frame.keyframes[k]

            name = keyframe.name
            count = lerp(keyframe.count, next_keyframe.count, fraction_between_keyframes)

            this_keyframe = Keyframe(name, count)
            this_keyframe.y_position = keyframe.y_position #slerp(keyframe.y_position, next_keyframe.y_position, fraction_between_keyframes)
            this_keyframe.color = keyframe.color
            this_frame.keyframes[name] = this_keyframe



    # ==== Create the animation ==== #
    fig = plt.Figure(figsize=(7, 6), dpi=144)
    ax = fig.add_subplot()
    animator = MatAnimation(ax, dp_display_number, frames)
    #a = animator.animate_frame(270)[0]
    #fig.savefig("test.png")
    #return

    anim = FuncAnimation(fig=fig, func=animator.animate_frame, frames=60*5, interval=(1/60)*1000, repeat=False)
    anim.save("test_animation.mp4")


if __name__ == "__main__":
    main()
