!include LogicLib.nsh
!include MUI2.nsh

!define VERSION "0.1"
!define APPNAME "Biostata"
!define EXENAME ${APPNAME}.exe
OutFile "biostata-v${VERSION}-win32.exe"
InstallDir $PROGRAMFILES32\${APPNAME}

!macro VerifyUserIsAdmin
	UserInfo::GetAccountType
	pop $0
	${If} $0 != "admin" ;Require admin rights on NT4+
		messageBox mb_iconstop "Administrator rights required!"
		setErrorLevel 740 ;ERROR_ELEVATION_REQUIRED
		quit
	${EndIf}
!macroend

Function .onInit
	setShellVarContext all
	!insertmacro VerifyUserIsAdmin
FunctionEnd

Function un.RMDirUP
	!define RMDirUP '!insertmacro RMDirUPCall'
	
	!macro RMDirUPCall _PATH
		push '${_PATH}'
		Call un.RMDirUP
	!macroend
	
	; $0 - current folder
	ClearErrors
	
	Exch $0
	;DetailPrint "ASDF - $0\.."
	RMDir "$0\.."
	
	IfErrors Skip
	${RMDirUP} "$0\.."
	Skip:
	
	Pop $0
FunctionEnd

Function un.onInit
	SetShellVarContext all
 
	#Verify the uninstaller - last chance to back out
	MessageBox MB_OKCANCEL "Remove ${APPNAME}?" IDOK next
		Abort
	next:
	!insertmacro VerifyUserIsAdmin
FunctionEnd

RequestExecutionLevel admin
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Section "install"
	SetOutPath $INSTDIR
	# copy program files
	File /a /r "dist\biostata\"
	
	# Create program data directory
	SetShellVarContext all
	ReadEnvStr $1 PROGRAMDATA
	!define DTDIR "$1\Biostata"
	${IfNot} ${FileExists} "${DTDIR}\*.*"
		CreateDirectory "${DTDIR}"
	${EndIf}
	AccessControl::GrantOnFile "${DTDIR}" "(S-1-5-32-545)" "FullAccess"

	# Create initial rc file with paths to excel and notepad
	# Only if this file does not exist
	${IfNot} ${FileExists} "${DTDIR}\.biostatarc"
		DetailPrint "Creating initial rc file at ${DTDIR}\.biostatarc"
		# detect excel
		!define EXCEL_PATH ""
		ClearErrors
		ReadRegStr $2 HKLM "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\excel.exe" ""
		IfErrors SkipExcel
		!define /redef EXCEL_PATH $2
		DetailPrint "Excel was found at ${EXCEL_PATH}"
		SkipExcel:
		
		FileOpen $3 "${DTDIR}\.biostatarc" w
		FileWrite $3 "<BiostataOptions version=$\"${VERSION}$\">$\r$\n"
		FileWrite $3 "    <EXTERNAL>$\r$\n"
		FileWrite $3 "        <XLSX>${EXCEL_PATH}</XLSX>$\r$\n"
		FileWrite $3 "        <TXT>notepad.exe</TXT>$\r$\n"
		FileWrite $3 "    </EXTERNAL>$\r$\n"
		FileWrite $3 "</BiostataOptions>"
		FileClose $3
	${EndIf}
	
	# create a file which links to a program data folder
	FileOpen $4 "$INSTDIR\config.txt" w
	FileWrite $4 "datadir: ${DTDIR}"
	FileClose $4

	# Shortcuts for bin files. Places ico file to bin directory
	File /oname=biostata.ico resources\biostata256.ico
	!define /redef ShortcutIcon $INSTDIR\biostata.ico 
	CreateDirectory "$SMPROGRAMS\${APPNAME}"
	CreateShortCut "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk" \
		"$INSTDIR\${EXENAME}" "" "${ShortcutIcon}" ""
		
	# uninstaller
	WriteUninstaller $INSTDIR\Uninstall.exe
	CreateShortCut "$SMPROGRAMS\${APPNAME}\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Uninstall"
	# Remove Start Menu launcher
	delete "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk"
	delete "$SMPROGRAMS\${APPNAME}\Uninstall.lnk"
	rmDir "$SMPROGRAMS\${APPNAME}"
 
	# Remove files
	RMDir /r "$INSTDIR"
	${RMDirUP} "$INSTDIR"   ;remove parents (if each is empty ONLY)
	delete "$INSTDIR\${APPNAME}.lnk"
 
	# Always delete uninstaller as the last action
	delete "$INSTDIR\Uninstall.exe"
 
	# Try to remove the install directory - this will only happen if it is empty
	rmDir $INSTDIR
SectionEnd
