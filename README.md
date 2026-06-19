# AD Automation

SAP에서 반복 정비 데이터와 항공기 FH/FC 데이터를 내려받아 Google Sheets의 `REPETITIVE` 탭을 업데이트하는 자동화 도구입니다.

## 대상 파일

- Google Sheet: `(현재유효) 737-8 AD Status_20260420_자동화_작업중`
- Sheet ID: `1Atc94uuyCmG2I6bGkDSyQfTS7gLLuKgGhSKPqDr_OBY`
- Target tab: `REPETITIVE`

## 업데이트 범위

- `B4:C15`: 항공기별 최신 Total FH / Total FC
- `E4:E15`, `I4:I15`, `M4:M15`, `Q4:Q15`, `U4:U15`: Task Card별 Close Date

현재 IP24 export에서 실제 Close FH / Close FC 컬럼이 제공되지 않으므로 해당 값은 업데이트하지 않습니다. Close Date는 현재 IP24 export의 `Planned date` 컬럼을 임시로 사용합니다.

## 실행 전 조건

1. SAP가 실행 중이면 종료합니다.
2. Excel 파일은 모두 저장 후 닫습니다. 자동화 중 Excel 전체 종료가 수행됩니다.
3. `credentials.json`을 `AD_auto_main.exe` 또는 `AD_auto_main.py`와 같은 폴더에 둡니다.
4. 아래 SAP shortcut 파일이 존재해야 합니다.
   - `C:\Users\User\Desktop\IP24.SAP`
   - `C:\Users\User\Desktop\[PM]AC_FH_FC.SAP`

## SAP 화면 기준

- SAP GUI Scripting이 서버에서 비활성화된 환경을 기준으로 `pyautogui` 키보드/마우스 자동화를 사용합니다.
- Export 직전 SAP 창을 앞으로 가져오고 최대화한 뒤, 화면 절대좌표가 아니라 SAP 창 크기 기준 상대좌표에서 우클릭합니다.
- 사용자 PC의 해상도, Windows 배율, SAP 테마/레이아웃이 크게 다르면 상대좌표 보정이 필요할 수 있습니다.

## 실행 방법

### EXE

`AD_auto_main.exe`를 실행한 뒤 콘솔에 SAP 비밀번호를 입력합니다.

### Python

```powershell
python AD_auto_main.py
```

## Python 의존성

```powershell
python -m pip install -r requirements.txt
```

## EXE 빌드

```powershell
python -m PyInstaller --onefile --console --name AD_auto_main --clean --noconfirm AD_auto_main.py
```

빌드 후 `dist\AD_auto_main.exe`와 같은 폴더에 `credentials.json`을 둡니다.

## GitHub 제외 파일

아래 파일과 폴더는 GitHub에 올리지 않습니다.

- `credentials.json`
  - Google service account private key가 포함되어 있습니다.
  - 유출되면 Google Sheet 접근 권한이 외부로 노출될 수 있으므로 로컬 또는 배포 패키지에서만 관리합니다.
- `dist/AD_auto_main.exe`
  - 빌드 산출물입니다.
  - 소스 코드에서 다시 생성할 수 있고 파일 크기가 크므로 GitHub에는 올리지 않습니다.
- `EXPORT_*.xlsx`
  - SAP에서 내려받은 업무 데이터입니다.
  - 항공기 정비 데이터가 포함될 수 있고 실행할 때마다 새로 생성되므로 GitHub에는 올리지 않습니다.
- `build/`
  - PyInstaller 임시 빌드 폴더입니다.
  - 재빌드 시 자동 생성되므로 GitHub에는 올리지 않습니다.
- `Old/`
  - 이전 테스트/백업 파일 보관용 폴더입니다.
  - 현재 배포 대상 코드가 아니므로 GitHub에는 올리지 않습니다.

## 보안 주의

- `credentials.json`은 GitHub에 올리지 않습니다.
- SAP 비밀번호는 코드에 저장하지 않습니다.
- 자동화 실행 중 열려 있는 Excel 프로세스는 강제 종료됩니다.
