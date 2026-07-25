' TenoHMS - Silent Background Launcher
' Used by Task Scheduler to start the server without showing a console window.
' The console window is hidden so the client sees nothing until the browser opens.

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Get the directory where this script lives
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Set working directory
WshShell.CurrentDirectory = scriptDir

' Start the Django server in a hidden command window
WshShell.Run "cmd /c """ & scriptDir & "start.bat""", 0, False

' Wait for server to start and port file to be written
WScript.Sleep 5000

' Read the port from file
port = 8000
portFile = scriptDir & ".current_port"
If fso.FileExists(portFile) Then
    Set ts = fso.OpenTextFile(portFile, 1)
    If Not ts.AtEndOfStream Then
        port = Trim(ts.ReadLine)
    End If
    ts.Close
End If

' Open browser
CreateObject("Shell.Application").ShellExecute "http://127.0.0.1:" & port
