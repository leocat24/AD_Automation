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

## 보안 주의

- `credentials.json`은 GitHub에 올리지 않습니다.
- SAP 비밀번호는 코드에 저장하지 않습니다.
- 자동화 실행 중 열려 있는 Excel 프로세스는 강제 종료됩니다.
