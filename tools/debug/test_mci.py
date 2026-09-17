import ctypes
import time
import os
import urllib.request

def play_mp3(filepath):
    print(f"Playing {filepath}...")
    mci = ctypes.windll.winmm.mciSendStringW
    # close any existing alias
    mci('close tts_audio', None, 0, None)
    
    # open 
    res = mci(f'open "{filepath}" alias tts_audio', None, 0, None)
    if res != 0:
        print(f"Error opening: {res}")
        return False
    
    # play wait
    print("Executing play wait...")
    res = mci('play tts_audio wait', None, 0, None)
    if res != 0:
        print(f"Error playing: {res}")
    
    mci('close tts_audio', None, 0, None)
    print("Finished playing.")
    return True

if __name__ == "__main__":
    test_mp3 = "test_audio.mp3"
    if not os.path.exists(test_mp3):
        print("Downloading sample mp3...")
        urllib.request.urlretrieve("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3", test_mp3)
    
    play_mp3(test_mp3)
