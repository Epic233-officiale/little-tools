import pyaudio # type: ignore
import numpy as np # type: ignore
import matplotlib.pyplot as plt # type: ignore
import threading
import queue
import os

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

p = pyaudio.PyAudio()

stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=512)

print("Press Ctrl+C to stop")

fig, ax = plt.subplots()
num_bins = 512  
log_freqs = np.logspace(np.log2(20), np.log2(RATE // 2), num=num_bins, base=2)

line, = ax.plot(log_freqs, np.zeros_like(log_freqs))
ax.set_xlim(20, RATE // 2)
ax.set_ylim(0, 1)  

ax.set_xscale('log')

plt.ion()

freq_data_queue = queue.Queue()

def process_audio(CHUNK=2048):
    epsilon = 1e-10
    MAX_DB = 160
    overlap_buffer = np.zeros(2048, dtype=np.int16)
    while True:
        try:
            audio_data = np.frombuffer(stream.read(1024), dtype=np.int16)
            overlap_buffer = np.concatenate([overlap_buffer[CHUNK//2:], audio_data])
            fft_data = np.fft.fft(overlap_buffer)
            fft_magnitude = np.abs(fft_data)[:CHUNK // 2]
            fft_magnitude_db = 20 * np.log10(fft_magnitude + epsilon)
            chunk_size = CHUNK
            fft_data = np.fft.fft(overlap_buffer[:chunk_size])
            fft_magnitude = np.abs(fft_data)[:chunk_size // 2]
            fft_magnitude_db = 20 * np.log10(fft_magnitude + epsilon)
            max_db = MAX_DB
            scale_factor = MAX_DB / max_db if max_db != 0 else 1
            fft_magnitude_db_scaled = fft_magnitude_db * scale_factor
            fft_magnitude_db_scaled = np.clip(fft_magnitude_db_scaled, 0, MAX_DB)
            scaled_magnitude = np.clip((fft_magnitude_db_scaled - MAX_DB) / 100 + 1, 0, 1)
            log_index = np.interp(log_freqs, np.linspace(20, RATE // 2, chunk_size // 2), np.arange(chunk_size // 2))
            log_magnitude = np.interp(log_index, np.arange(chunk_size // 2), scaled_magnitude)
            freq_data_queue.put(log_magnitude)
        except KeyboardInterrupt:
            stream.stop_stream()
            stream.close()
            p.terminate()
            plt.ioff()
            plt.show()
        except Exception as e:
            print("Error:", e)
audio_thread = threading.Thread(target=process_audio, daemon=True)
audio_thread.start()
try:
    while True:
        try:
            log_magnitude = freq_data_queue.get(timeout=1)
            line.set_ydata(log_magnitude)
            plt.pause(0.01) 
        except queue.Empty:
            pass
except KeyboardInterrupt:
    stream.stop_stream()
    stream.close()
    p.terminate()
    plt.ioff()
    plt.show()
