Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "c:\Users\yedek\Desktop\yapay zeka\AYEC Pro"
WshShell.Run """c:\Users\yedek\Desktop\yapay zeka\AYEC Pro\.venv_active\Scripts\pythonw.exe"" Main.py", 1, False
