#ifndef AppVersion
  #define AppVersion "0.1.1"
#endif
#ifndef SourceDir
  #define SourceDir "..\dist\WhisperTranscriber"
#endif
#ifndef RootDir
  #define RootDir ".."
#endif

#define AppName "Whisper Transcriber Desktop"
#define AppExeName "WhisperTranscriber.exe"

[Setup]
AppId={{F0E7212D-4859-48F5-A26D-1F361FE0DF13}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=lucasitdias
AppPublisherURL=https://github.com/lucasitdias/whisper_desktop
AppSupportURL=https://github.com/lucasitdias/whisper_desktop/issues
DefaultDirName={localappdata}\Programs\Whisper Transcriber Desktop
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist\installer
OutputBaseFilename=WhisperTranscriber-Setup-Windows-x64
SetupIconFile={#RootDir}\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
VersionInfoVersion={#AppVersion}
VersionInfoDescription=Instalador do Whisper Transcriber Desktop
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar um atalho na área de trabalho"; GroupDescription: "Atalhos adicionais:"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#RootDir}\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Abrir o {#AppName}"; Flags: nowait postinstall skipifsilent
