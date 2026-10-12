#define AppName "BEAN"
#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{78A7B85B-A19A-439A-B63A-E037148EFDA7}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=BEAN Research Project
AppPublisherURL=https://github.com/danieloculus0-bot/BEAN
DefaultGroupName=BEAN
OutputDir=..\\..\\out
OutputBaseFilename=BEAN-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
DefaultDirName={localappdata}\\Programs\\BEAN
UninstallDisplayIcon={app}\\BEAN.exe
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=no

[Files]
Source: "..\\..\\dist\\BEAN\\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\\BEAN"; Filename: "{app}\\BEAN.exe"
Name: "{autodesktop}\\BEAN"; Filename: "{app}\\BEAN.exe"; Tasks: desktopicon

[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
Filename: "{app}\\BEAN.exe"; Description: "Launch BEAN"; Flags: nowait postinstall skipifsilent
