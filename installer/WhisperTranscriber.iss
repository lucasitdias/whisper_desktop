#ifndef AppVersion
  #define AppVersion "0.1.1"
#endif
#ifndef SourceDir
  #define SourceDir "..\dist\WhisperTranscriber"
#endif
#ifndef RootDir
  #define RootDir ".."
#endif
#ifndef OutputBaseFilename
  #define OutputBaseFilename "WhisperTranscriber-Setup-Windows-x64"
#endif

#define AppName "Whisper Transcriber Desktop"
#define AppExeName "WhisperTranscriber.exe"

[Setup]
AppId={{F0E7212D-4859-48F5-A26D-1F361FE0DF13}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Lucas Dias
AppCopyright=Copyright (c) 2026 Lucas Dias
AppPublisherURL=https://github.com/lucasitdias/whisper_desktop
AppSupportURL=https://github.com/lucasitdias/whisper_desktop/issues
DefaultDirName={localappdata}\Programs\Whisper Transcriber Desktop
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist\installer
OutputBaseFilename={#OutputBaseFilename}
SetupIconFile={#RootDir}\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2/max
SolidCompression=yes
; A variante CUDA pode ultrapassar o limite de 4,2 GB de um Setup.exe único.
; O launcher e as fatias .bin devem permanecer juntos na mesma pasta.
DiskSpanning=yes
DiskSliceSize=2000000000
SlicesPerDisk=1
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
Source: "{#SourceDir}\*"; DestDir: "{app}"; Excludes: "\_internal\assets\models\*"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceDir}\_internal\assets\models\*"; DestDir: "{app}\_internal\assets\models"; Flags: ignoreversion nocompression recursesubdirs createallsubdirs
Source: "{#RootDir}\docs\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#RootDir}\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Code]
const
  LargeV3CheckpointSize = 3087371615;

procedure MigrateLegacyLargeV3;
var
  LegacyPath: String;
  CacheDir: String;
  CachePath: String;
  LegacySize: Int64;
  CacheSize: Int64;
begin
  LegacyPath := ExpandConstant('{app}\_internal\assets\models\large-v3.pt');
  if (not FileExists(LegacyPath)) or
     (not FileSize64(LegacyPath, LegacySize)) or
     (LegacySize <> LargeV3CheckpointSize) then
    exit;

  CacheDir := ExpandConstant('{localappdata}\WhisperTranscriber\models');
  CachePath := CacheDir + '\large-v3.pt';
  if FileExists(CachePath) then
  begin
    if FileSize64(CachePath, CacheSize) and
       (CacheSize = LargeV3CheckpointSize) then
      DeleteFile(LegacyPath);
    exit;
  end;

  if ForceDirectories(CacheDir) then
    RenameFile(LegacyPath, CachePath);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  MigrateLegacyLargeV3;
  Result := '';
end;

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Abrir o {#AppName}"; Flags: nowait postinstall skipifsilent
