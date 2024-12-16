import pyaudio  # type: ignore
import numpy as np  # type: ignore
import matplotlib.pyplot as plt  
from matplotlib.animation import FuncAnimation

FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
CHUNK = 512
LATENCY_INTERVAL = 30
theta = np.pi / 4
rotation_matrix = np.array([[np.cos(theta), -np.sin(theta)],
                            [np.sin(theta), np.cos(theta)]])
audio = pyaudio.PyAudio()
stream = audio.open(format=FORMAT, 
                    channels=CHANNELS, 
                    rate=RATE, 
                    input=True, 
                    frames_per_buffer=CHUNK)
print("Close the plot window to stop.")
fig, ax = plt.subplots()
sc = ax.scatter([], [], c='blue', alpha=0.5, s=1)
ax.set_xlim(-100, 100)
ax.set_ylim(-100, 100)
ax.set_title("Stereo Channel Visualization (Rotated 45°)")
ax.set_xlabel("Right Channel (X)")
ax.set_ylabel("Left Channel (Y)")
ax.axhline(0, color='black', linewidth=0.5)
ax.axvline(0, color='black', linewidth=0.5)

def update(frame):
    data = stream.read(CHUNK, exception_on_overflow=False)
    audio_data = np.frombuffer(data, dtype=np.int16)
    left_channel = audio_data[0::2]
    right_channel = audio_data[1::2]
    left_channel_scaled = left_channel / 1000
    right_channel_scaled = right_channel / 1000
    points = np.vstack((right_channel_scaled, left_channel_scaled))
    rotated_points = rotation_matrix @ points
    sc.set_offsets(rotated_points.T)
    return sc,

ani = FuncAnimation(fig, update, blit=True, interval=LATENCY_INTERVAL, frames=60)

try:
    plt.show()
except KeyboardInterrupt:
    print("Stopped Recording.")

stream.stop_stream()
stream.close()
audio.terminate()
