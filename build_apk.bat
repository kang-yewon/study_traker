@echo off
chcp 65001 > nul
echo ========================================================
echo       StudyTimer (Capacitor Android Gradle 빌드)
echo ========================================================
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

if "%JAVA_HOME%"=="" (
    if exist "C:\Program Files\Android\Android Studio\jbr" (
        set "JAVA_HOME=C:\Program Files\Android\Android Studio\jbr"
    )
)

echo [1/3] 웹 에셋 동기화 중... (Capacitor Sync)
call npx cap sync android
if %ERRORLEVEL% neq 0 (
    echo [오류] Capacitor 동기화에 실패했습니다.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/3] 네이티브 Android Gradle APK 빌드 중...
call ".\android\gradlew.bat" -p android assembleDebug
if %ERRORLEVEL% neq 0 (
    echo [오류] Gradle 빌드에 실패했습니다.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [3/3] 생성된 APK 파일 복사 중...
if exist "android\app\build\outputs\apk\debug\app-debug.apk" (
    copy /y "android\app\build\outputs\apk\debug\app-debug.apk" "StudyTimer.apk" > nul
    echo.
    echo ========================================================
    echo  [성공] 빌드가 완료되었습니다!
    echo  생성 위치: StudyTimer.apk
    echo ========================================================
) else (
    echo [경고] APK 파일을 찾을 수 없습니다.
)

pause
