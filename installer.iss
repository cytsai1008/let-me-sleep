; Inno Setup Script for Let Me Sleep
; Download Inno Setup from: https://jrsoftware.org/isinfo.php

#define MyAppName "Let Me Sleep"
#define MyAppVersion "0.1.4"
#define MyAppPublisher "CYTsai"
#define MyAppURL "https://github.com/cytsai1008/let-me-sleep"
#define MyAppExeName "LetMeSleep.exe"

[Setup]
AppId={{2E61D334-9DF9-4CAB-A041-9C22A083035A}
AppName={cm:AppDisplayName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={cm:AppDisplayName}
AllowNoIcons=yes
LicenseFile=LICENSE
OutputDir=installer_output
OutputBaseFilename=LetMeSleep_Setup_{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "chinesetraditional"; MessagesFile: "compiler:Languages\ChineseTraditional.isl"

[CustomMessages]
english.AppDisplayName=Let Me Sleep
english.OptionsGroup=Options:
english.ScheduledTaskOption=Install as scheduled task (enables admin privileges and logon autostart option)
english.AutostartOption=Start at user logon (requires scheduled task)
chinesesimplified.AppDisplayName=我要睡觉
chinesesimplified.OptionsGroup=选项:
chinesesimplified.ScheduledTaskOption=安装为计划任务（启用管理员权限和登录自启动选项）
chinesesimplified.AutostartOption=登录时自启动（需要计划任务）
chinesetraditional.AppDisplayName=我想睡覺
chinesetraditional.OptionsGroup=選項:
chinesetraditional.ScheduledTaskOption=安裝為排程工作（啟用管理員權限與登入自動啟動選項）
chinesetraditional.AutostartOption=登入時自動啟動（需要排程工作）

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "scheduledtask"; Description: "{cm:ScheduledTaskOption}"; GroupDescription: "{cm:OptionsGroup}"; Flags: checkablealone
Name: "autostart"; Description: "{cm:AutostartOption}"; GroupDescription: "{cm:OptionsGroup}"; Flags: unchecked

[Files]
Source: "dist\main.dist\*"; DestDir: "{app}\app"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "dist\{#MyAppExeName}"; DestDir: "{app}\app"; Flags: ignoreversion skipifsourcedoesntexist
Source: "dist\LetMeSleep-Updater.exe"; DestDir: "{app}"; DestName: "LetMeSleep-Updater.exe"; Flags: ignoreversion skipifsourcedoesntexist
Source: "dist\VERSION"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{cm:AppDisplayName}"; Filename: "{app}\LetMeSleep-Updater.exe"; Parameters: """{app}"" --no-update"
Name: "{group}\{cm:UninstallProgram,{cm:AppDisplayName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{cm:AppDisplayName}"; Filename: "{app}\LetMeSleep-Updater.exe"; Parameters: """{app}"" --no-update"; Tasks: desktopicon

[Run]
; Install scheduled task with autostart if both selected
Filename: "{app}\app\{#MyAppExeName}"; Parameters: "--install-task-with-autostart"; Flags: runhidden; Check: IsAutostartSelected and FileExists(ExpandConstant('{app}\app\{#MyAppExeName}'))
Filename: "{app}\main.dist\{#MyAppExeName}"; Parameters: "--install-task-with-autostart"; Flags: runhidden; Check: IsAutostartSelected and FileExists(ExpandConstant('{app}\main.dist\{#MyAppExeName}'))
Filename: "{app}\main\{#MyAppExeName}"; Parameters: "--install-task-with-autostart"; Flags: runhidden; Check: IsAutostartSelected and FileExists(ExpandConstant('{app}\main\{#MyAppExeName}'))
; Install scheduled task without autostart if only task selected
Filename: "{app}\app\{#MyAppExeName}"; Parameters: "--install-task"; Flags: runhidden; Check: IsTaskOnlySelected and FileExists(ExpandConstant('{app}\app\{#MyAppExeName}'))
Filename: "{app}\main.dist\{#MyAppExeName}"; Parameters: "--install-task"; Flags: runhidden; Check: IsTaskOnlySelected and FileExists(ExpandConstant('{app}\main.dist\{#MyAppExeName}'))
Filename: "{app}\main\{#MyAppExeName}"; Parameters: "--install-task"; Flags: runhidden; Check: IsTaskOnlySelected and FileExists(ExpandConstant('{app}\main\{#MyAppExeName}'))
; Launch updater after install (it launches app)
Filename: "{app}\LetMeSleep-Updater.exe"; Parameters: """{app}"""; Description: "{cm:LaunchProgram,{cm:AppDisplayName}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Remove scheduled task on uninstall (if it exists)
Filename: "schtasks"; Parameters: "/Delete /TN ""LetMeSleep"" /F"; Flags: runhidden; RunOnceId: "RemoveTask"

[UninstallDelete]
Type: files; Name: "{app}\LetMeSleep-Updater.log"
Type: dirifempty; Name: "{app}"

[Code]
var
  ScheduledTaskItemIndex: Integer;
  AutostartItemIndex: Integer;

function FindTaskItemIndex(const TaskDescription: String): Integer;
var
  I: Integer;
begin
  Result := -1;
  for I := 0 to WizardForm.TasksList.Items.Count - 1 do
  begin
    if WizardForm.TasksList.ItemCaption[I] = TaskDescription then
    begin
      Result := I;
      Exit;
    end;
  end;
end;

procedure UpdateAutostartAvailability();
var
  ScheduledSelected: Boolean;
begin
  if (ScheduledTaskItemIndex < 0) or (AutostartItemIndex < 0) then
    Exit;

  ScheduledSelected := WizardForm.TasksList.Checked[ScheduledTaskItemIndex];
  WizardForm.TasksList.ItemEnabled[AutostartItemIndex] := ScheduledSelected;

  if not ScheduledSelected then
    WizardForm.TasksList.Checked[AutostartItemIndex] := False;
end;

procedure TasksListClickCheck(Sender: TObject);
begin
  UpdateAutostartAvailability();
end;

procedure InitializeWizard();
begin
  ScheduledTaskItemIndex := -1;
  AutostartItemIndex := -1;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpSelectTasks then
  begin
    if (ScheduledTaskItemIndex < 0) or (AutostartItemIndex < 0) then
    begin
      ScheduledTaskItemIndex := FindTaskItemIndex(ExpandConstant('{cm:ScheduledTaskOption}'));
      AutostartItemIndex := FindTaskItemIndex(ExpandConstant('{cm:AutostartOption}'));
      WizardForm.TasksList.OnClickCheck := @TasksListClickCheck;
    end;

    UpdateAutostartAvailability();
  end;
end;

function IsScheduledTaskSelected(): Boolean;
begin
  Result := WizardIsTaskSelected('scheduledtask');
end;

function IsTaskOnlySelected(): Boolean;
begin
  Result := WizardIsTaskSelected('scheduledtask') and not WizardIsTaskSelected('autostart');
end;

function IsAutostartSelected(): Boolean;
begin
  Result := WizardIsTaskSelected('scheduledtask') and WizardIsTaskSelected('autostart');
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
begin
  if CurUninstallStep = usUninstall then
  begin
    // Kill running instance before uninstall
    Exec('taskkill', '/F /IM LetMeSleep.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;
