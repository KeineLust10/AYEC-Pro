; AYEC Pro installer definition.
; The executable embeds the application icon; the source icon is bundled for
; installer validation and resource tooling.
[Setup]
AppName=AYEC Pro
AppVersion=1.0.0
DefaultDirName={autopf}\AYEC Pro
OutputBaseFilename=AYECPro_Setup
SetupIconFile=assets\app_icon.ico

[Files]
Source: "assets\app_icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autodesktop}\AYEC Pro"; Filename: "{app}\AYECPro.exe"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\AYEC Pro"; Filename: "{app}\AYECPro.exe"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{userappdata}\Microsoft\Windows\Start Menu\Programs\AYEC Pro"; Filename: "{app}\AYECPro.exe"; IconFilename: "{app}\{#MyAppExeName}"
