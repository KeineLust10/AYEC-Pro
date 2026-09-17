try:
    import pyaudio
    print("SUCCESS: pyaudio (shim) imported successfully.")
    p = pyaudio.PyAudio()
    print(f"SUCCESS: PyAudio host API count: {p.get_host_api_count()}")
    p.terminate()
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
