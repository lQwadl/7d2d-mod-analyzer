Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\gingt\Desktop\Work\Final product"
WshShell.Run chr(34) & "C:\Users\gingt\AppData\Local\Programs\Python\Python312\python.exe" & chr(34) & " gui\app.py", 0
Set WshShell = Nothing
