import glob
import ctypes
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import gspread
import pandas as pd
import pyautogui
from google.oauth2.service_account import Credentials
from gspread import Cell


SPREADSHEET_ID = "1Atc94uuyCmG2I6bGkDSyQfTS7gLLuKgGhSKPqDr_OBY"
WORKSHEET_NAME = "REPETITIVE"

IP24_SAP_FILE = Path(r"C:\Users\User\Desktop\IP24.SAP")
FHFC_SAP_FILE = Path(r"C:\Users\User\Desktop\[PM]AC_FH_FC.SAP")
FHFC_DOWNLOAD_DIR = Path.home() / "Desktop" / "Google Drive for Henry Desktop"
IP24_DOWNLOAD_DIR = FHFC_DOWNLOAD_DIR / "AD Repeat"
DESKTOP_DIR = Path.home() / "Desktop"
EXPORT_SEARCH_DIRS = [
    DESKTOP_DIR,
    FHFC_DOWNLOAD_DIR,
    IP24_DOWNLOAD_DIR,
]
SAP_EXPORT_RIGHT_CLICK_X_RATIO = 0.48
SAP_EXPORT_RIGHT_CLICK_Y_RATIO = 0.50

GTL_RANGE = "A25:A29"
AIRCRAFT_RANGE = "A4:A15"
FHFC_UPDATE_RANGE = "B4:C15"

AD_BLOCKS = [
    {"plan_col": 4, "date_col": 5, "fh_col": 6, "fc_col": 7},     # D:G
    {"plan_col": 8, "date_col": 9, "fh_col": 10, "fc_col": 11},   # H:K
    {"plan_col": 12, "date_col": 13, "fh_col": 14, "fc_col": 15}, # L:O
    {"plan_col": 16, "date_col": 17, "fh_col": 18, "fc_col": 19}, # P:S
    {"plan_col": 20, "date_col": 21, "fh_col": 22, "fc_col": 23}, # T:W
]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def credentials_path() -> Path:
    candidates = [
        app_dir() / "credentials.json",
        Path.cwd() / "credentials.json",
        Path(r"C:\Users\User\Desktop\AD_Automation\credentials.json"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "credentials.json을 찾을 수 없습니다. EXE 또는 py 파일과 같은 폴더에 credentials.json을 두세요."
    )


def get_worksheet():
    credentials = Credentials.from_service_account_file(str(credentials_path()), scopes=SCOPES)
    gc = gspread.authorize(credentials)
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)
    return spreadsheet.worksheet(WORKSHEET_NAME)


def is_sap_running() -> bool:
    try:
        result = subprocess.run(
            ["tasklist"],
            capture_output=True,
            text=True,
            check=False,
            encoding="mbcs",
            errors="ignore",
        )
        return "saplogon.exe" in result.stdout.lower()
    except Exception:
        return False


def run_sap_file(sap_file_path: Path) -> None:
    if not sap_file_path.exists():
        raise FileNotFoundError(f"SAP 파일을 찾을 수 없습니다: {sap_file_path}")
    os.startfile(str(sap_file_path))
    print(f"SAP 파일 실행: {sap_file_path}")


def get_sap_password() -> str:
    password = os.environ.get("SAP_PASSWORD", "").strip()
    if password:
        return password
    return input("SAP 비밀번호 입력: ").strip()


def minimize_console_window() -> None:
    try:
        console_window = ctypes.windll.kernel32.GetConsoleWindow()
        if console_window:
            ctypes.windll.user32.ShowWindow(console_window, 6)
            print("실행창 최소화 완료")
            time.sleep(1.0)
    except Exception as exc:
        print(f"실행창 최소화 실패: {exc}")


def activate_sap_window() -> None:
    script = r"""
$signature = @'
using System;
using System.Runtime.InteropServices;
public class WinApi {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
'@
Add-Type $signature -ErrorAction SilentlyContinue | Out-Null
$processes = Get-Process | Where-Object {
    $_.MainWindowHandle -ne 0 -and (
        $_.ProcessName -like '*sap*' -or
        $_.MainWindowTitle -like '*SAP*' -or
        $_.MainWindowTitle -like '*Logon*'
    )
} | Sort-Object StartTime -Descending
foreach ($process in $processes) {
    [void][WinApi]::ShowWindow($process.MainWindowHandle, 9)
    [void][WinApi]::SetForegroundWindow($process.MainWindowHandle)
    exit 0
}
exit 1
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    if result.returncode == 0:
        print("SAP 창 활성화 완료")
        time.sleep(1.0)
        return

    app_activate_script = r"""
$shell = New-Object -ComObject WScript.Shell
$titles = @('SAP Logon', 'SAP', 'Logon')
foreach ($title in $titles) {
    try {
        if ($shell.AppActivate($title)) {
            exit 0
        }
    } catch {}
}
exit 1
"""
    app_result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", app_activate_script],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    if app_result.returncode == 0:
        print("SAP 창 AppActivate 완료")
        time.sleep(1.0)
        return

    print("SAP 창 자동 활성화 실패: Alt+Tab 시도")
    pyautogui.hotkey("alt", "tab")
    time.sleep(1.0)


def get_maximized_sap_window_rect() -> tuple[int, int, int, int] | None:
    script = r"""
$signature = @'
using System;
using System.Runtime.InteropServices;
public class WinApi {
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
}
'@
Add-Type $signature -ErrorAction SilentlyContinue | Out-Null
$processes = Get-Process | Where-Object {
    $_.MainWindowHandle -ne 0 -and (
        $_.ProcessName -like '*sap*' -or
        $_.MainWindowTitle -like '*SAP*'
    )
} | Sort-Object StartTime -Descending
foreach ($process in $processes) {
    [void][WinApi]::ShowWindow($process.MainWindowHandle, 3)
    Start-Sleep -Milliseconds 500
    [void][WinApi]::SetForegroundWindow($process.MainWindowHandle)
    $rect = New-Object WinApi+RECT
    if ([WinApi]::GetWindowRect($process.MainWindowHandle, [ref]$rect)) {
        "$($rect.Left),$($rect.Top),$($rect.Right),$($rect.Bottom)"
        exit 0
    }
}
exit 1
"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except Exception as exc:
        print(f"SAP window rect check failed: {exc}")
        return None

    if result.returncode != 0:
        return None

    match = re.search(r"(-?\d+),(-?\d+),(-?\d+),(-?\d+)", result.stdout)
    if not match:
        return None

    left, top, right, bottom = (int(value) for value in match.groups())
    width = right - left
    height = bottom - top
    if width <= 0 or height <= 0:
        return None
    return left, top, width, height


def right_click_sap_export_area(label: str) -> None:
    rect = get_maximized_sap_window_rect()
    if rect is None:
        print(f"{label} SAP window rect failed: fallback to screen center")
        screen_width, screen_height = pyautogui.size()
        x = screen_width // 2
        y = screen_height // 2
    else:
        left, top, width, height = rect
        x = left + int(width * SAP_EXPORT_RIGHT_CLICK_X_RATIO)
        y = top + int(height * SAP_EXPORT_RIGHT_CLICK_Y_RATIO)
        print(f"{label} SAP right click position: x={x}, y={y}")

    pyautogui.click(x=x, y=y, button="right")


def login_to_sap(password: str) -> None:
    print("SAP 로그인 창 대기: 5초")
    time.sleep(5)
    minimize_console_window()
    activate_sap_window()
    pyautogui.write(password, interval=0.05)
    time.sleep(0.2)
    pyautogui.press("enter")
    print("SAP 로그인 입력 완료")
    time.sleep(5)


def read_gtl_values(worksheet) -> list[str]:
    cells = worksheet.range(GTL_RANGE)
    values = []
    for cell in cells:
        value = (cell.value or "").strip()
        if "#" in value:
            value = value.split("#", 1)[0].strip()
        if value:
            values.append(value)
    if not values:
        raise RuntimeError(f"{WORKSHEET_NAME}!{GTL_RANGE}에서 GTL 값을 찾지 못했습니다.")
    print(f"GTL 값 {len(values)}개 수집: {values}")
    return values


def sap_ip24_fill_and_export(gtl_values: list[str]) -> None:
    print("IP24 화면 대기: 5초")
    time.sleep(5)

    print("IP24 시작일 입력 위치로 이동: Tab 47회")
    for _ in range(47):
        pyautogui.press("tab")
        time.sleep(0.03)

    start_date = "2025.01.01"
    end_date = datetime.now().strftime("%Y.%m.%d")

    pyautogui.write(start_date, interval=0.05)
    time.sleep(0.2)
    pyautogui.press("tab")
    time.sleep(0.2)
    pyautogui.write(end_date, interval=0.05)
    time.sleep(0.2)

    print("GTL 입력 위치로 이동: Tab 33회")
    for _ in range(33):
        pyautogui.press("tab")
        time.sleep(0.03)

    pyautogui.press("enter")
    time.sleep(1.5)

    for index, value in enumerate(gtl_values, start=1):
        print(f"IP24 GTL 입력 [{index}/{len(gtl_values)}]: {value}")
        pyautogui.write(value, interval=0.05)
        time.sleep(0.1)
        pyautogui.press("tab")
        time.sleep(0.05)
        pyautogui.press("tab")
        time.sleep(0.1)

    pyautogui.press("f8")
    time.sleep(0.5)
    pyautogui.press("f8")

    export_current_sap_list("IP24")


def sap_fhfc_fill_and_export() -> None:
    print("FH/FC 화면 대기: 5초")
    time.sleep(5)

    pyautogui.write("HL8523", interval=0.05)
    time.sleep(0.2)
    pyautogui.press("tab")
    time.sleep(0.2)
    pyautogui.write("HL9999", interval=0.05)
    time.sleep(0.2)
    pyautogui.press("tab")
    time.sleep(0.1)
    pyautogui.press("tab")
    time.sleep(0.2)

    for _ in range(15):
        pyautogui.press("backspace")
    time.sleep(0.2)

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y.%m.%d")
    pyautogui.write(yesterday, interval=0.05)
    time.sleep(0.2)
    pyautogui.press("tab")
    time.sleep(0.2)
    pyautogui.write(yesterday, interval=0.05)
    time.sleep(0.5)

    pyautogui.press("f8")

    export_current_sap_list("FH/FC")


def export_current_sap_list(label: str) -> None:
    print(f"{label} 리스트 로드 대기: 5초")
    time.sleep(5)
    right_click_sap_export_area(label)
    time.sleep(0.5)
    pyautogui.press("s")
    time.sleep(0.3)
    pyautogui.press("s")
    time.sleep(0.5)
    pyautogui.press("enter")
    time.sleep(1.5)
    pyautogui.hotkey("shift", "f8")
    time.sleep(1.0)
    pyautogui.hotkey("alt", "s")
    time.sleep(1.0)
    pyautogui.press("enter")
    print(f"{label} 내보내기 명령 완료")


def current_export_files(folders: list[Path]) -> set[Path]:
    files = set()
    for folder in folders:
        if not folder.exists():
            continue
        files.update(Path(path) for path in glob.glob(str(folder / "EXPORT_*.xlsx")))
    return files


def wait_for_new_export(
    folders: list[Path],
    before: set[Path],
    started_at: datetime,
    label: str,
    timeout: int = 120,
) -> Path:
    print(f"{label} EXPORT_*.xlsx 생성 대기")
    deadline = time.time() + timeout
    started_ts = started_at.timestamp() - 2

    while time.time() < deadline:
        candidates = []
        for path in current_export_files(folders):
            if path in before:
                continue
            try:
                if path.stat().st_mtime >= started_ts:
                    candidates.append(path)
            except FileNotFoundError:
                continue

        if candidates:
            newest = max(candidates, key=lambda p: p.stat().st_mtime)
            wait_until_file_stable(newest)
            print(f"{label} 다운로드 파일 확인: {newest.name}")
            return newest

        time.sleep(2)

    raise TimeoutError(f"{label} 다운로드 파일을 {timeout}초 안에 찾지 못했습니다.")


def wait_until_file_stable(path: Path, checks: int = 3, interval: float = 1.0) -> None:
    last_size = -1
    stable_count = 0
    while stable_count < checks:
        size = path.stat().st_size
        if size == last_size and size > 0:
            stable_count += 1
        else:
            stable_count = 0
            last_size = size
        time.sleep(interval)


def close_excel_workbook(path: Path, label: str = "Excel") -> None:
    print(f"{label} Excel 자동 닫기 대기: 5초")
    time.sleep(5)

    try:
        import win32com.client
    except ImportError:
        close_excel_workbook_with_powershell(path, label)
        force_close_excel_all(label)
        return

    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            excel = win32com.client.GetActiveObject("Excel.Application")
        except Exception:
            return

        target_name = path.name.lower()
        target_fullname = str(path.resolve()).lower()
        closed = False

        try:
            for workbook in list(excel.Workbooks):
                try:
                    workbook_name = str(workbook.Name).lower()
                    workbook_fullname = str(Path(workbook.FullName).resolve()).lower()
                except Exception:
                    continue

                if workbook_fullname == target_fullname or workbook_name == target_name:
                    workbook.Close(SaveChanges=False)
                    closed = True
                    print(f"{label} Excel 파일 닫기 완료: {path.name}")
                    break

            if hasattr(excel, "ProtectedViewWindows"):
                for protected_window in list(excel.ProtectedViewWindows):
                    try:
                        caption = str(protected_window.Caption).lower()
                        source_path = str(protected_window.SourcePath).lower()
                    except Exception:
                        caption = ""
                        source_path = ""

                    if target_name in caption or target_name in source_path or target_fullname in source_path:
                        protected_window.Close()
                        closed = True
                        print(f"{label} Excel Protected View 닫기 완료: {path.name}")
                        break

            if closed:
                if excel.Workbooks.Count == 0:
                    try:
                        if not hasattr(excel, "ProtectedViewWindows") or excel.ProtectedViewWindows.Count == 0:
                            excel.Quit()
                    except Exception:
                        pass
                force_close_excel_all(label)
                return
        except Exception:
            pass

        time.sleep(2)

    print(f"{label} Excel 파일을 자동으로 닫지 못했습니다: {path.name}")
    force_close_excel_all(label)


def close_excel_workbook_with_powershell(path: Path, label: str) -> None:
    target_fullname = str(path.resolve())
    target_name = path.name
    script = f"""
$targetFullName = @'
{target_fullname}
'@
$targetName = @'
{target_name}
'@
$deadline = (Get-Date).AddSeconds(30)
while ((Get-Date) -lt $deadline) {{
    try {{
        $excel = [Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application')
    }} catch {{
        Start-Sleep -Seconds 2
        continue
    }}
    $closed = $false
    foreach ($workbook in @($excel.Workbooks)) {{
        try {{
            if (($workbook.FullName -ieq $targetFullName) -or ($workbook.Name -ieq $targetName)) {{
                $workbook.Close($false)
                $closed = $true
                break
            }}
        }} catch {{}}
    }}
    try {{
        foreach ($protectedWindow in @($excel.ProtectedViewWindows)) {{
            try {{
                $caption = [string]$protectedWindow.Caption
                $sourcePath = [string]$protectedWindow.SourcePath
                if (($caption -like "*$targetName*") -or ($sourcePath -like "*$targetName*") -or ($sourcePath -ieq $targetFullName)) {{
                    $protectedWindow.Close()
                    $closed = $true
                    break
                }}
            }} catch {{}}
        }}
    }} catch {{}}
    if ($closed) {{
        try {{
            if (($excel.Workbooks.Count -eq 0) -and ($excel.ProtectedViewWindows.Count -eq 0)) {{
                $excel.Quit()
            }}
        }} catch {{}}
        exit 0
    }}
    Start-Sleep -Seconds 2
}}
exit 1
"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            check=False,
            timeout=40,
        )
        if result.returncode == 0:
            print(f"{label} Excel 파일 닫기 완료 또는 Excel 없음: {path.name}")
        else:
            print(f"{label} Excel 파일을 자동으로 닫지 못했습니다: {path.name}")
    except Exception as exc:
        print(f"{label} Excel 파일 자동 닫기 실패: {exc}")


def force_close_excel_all(label: str) -> None:
    try:
        result = subprocess.run(
            ["taskkill", "/IM", "EXCEL.EXE", "/F"],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
            encoding="mbcs",
            errors="ignore",
        )
        if result.returncode == 0:
            print(f"{label} Excel 전체 종료 완료")
        else:
            message = (result.stderr or result.stdout or "").strip()
            if "not found" in message.lower() or "찾을 수 없습니다" in message:
                print(f"{label} 종료할 Excel 프로세스 없음")
            else:
                print(f"{label} Excel 전체 종료 결과: {message}")
    except Exception as exc:
        print(f"{label} Excel 전체 종료 실패: {exc}")


def normalize_key(value) -> str:
    text = str(value or "").strip()
    if text.endswith(".0"):
        text = text[:-2]
    return re.sub(r"\s+", "", text).upper()


def normalize_column(name) -> str:
    return re.sub(r"[^A-Z0-9가-힣]", "", str(name).strip().upper())


def normalize_task(value) -> str:
    text = str(value or "").upper()
    task_card = re.findall(r"\d{2}-\d{3}-\d{2}-\d{2}[A-Z]?", text)
    if task_card:
        return re.sub(r"[^A-Z0-9]", "", task_card[-1])
    return re.sub(r"[^A-Z0-9가-힣]", "", text)


def pick_column(df: pd.DataFrame, candidates: list[str], required: bool = True) -> str | None:
    normalized = {normalize_column(col): col for col in df.columns}
    for candidate in candidates:
        key = normalize_column(candidate)
        if key in normalized:
            return normalized[key]
    for candidate in candidates:
        key = normalize_column(candidate)
        for normalized_name, original in normalized.items():
            if key and key in normalized_name:
                return original
    if required:
        raise ValueError(f"필수 컬럼을 찾지 못했습니다. 후보={candidates}, 실제={list(df.columns)}")
    return None


def read_excel(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path)
    df.columns = df.columns.astype(str).str.strip()
    return df


def parse_fhfc_export(path: Path) -> dict[str, dict[str, object]]:
    df = read_excel(path)
    ac_col = pick_column(df, ["A/C No.", "AC No", "Aircraft", "기번"])
    fh_col = pick_column(df, ["Total F/H", "Total FH", "TOTAL F/H"])
    fc_col = pick_column(df, ["Total F/C", "Total FC", "TOTAL F/C"])

    df[ac_col] = df[ac_col].astype(str).str.strip()
    df = df[(pd.to_numeric(df[fh_col], errors="coerce") > 0) & (pd.to_numeric(df[fc_col], errors="coerce") > 0)]

    result = {}
    for _, row in df.iterrows():
        ac_no = normalize_key(row[ac_col])
        result[ac_no] = {"FH": row[fh_col], "FC": row[fc_col]}

    print(f"FH/FC 데이터 {len(result)}건 분석 완료")
    return result


def parse_ip24_export(path: Path) -> dict[tuple[str, str], dict[str, object]]:
    df = read_excel(path)

    ac_col = pick_column(df, ["Functional Location", "A/C No.", "AC No", "Aircraft", "Equipment", "기번"])
    task_col = pick_column(df, ["Maintenance item description", "Task Card", "Taskcard", "Description", "작업내용"])
    date_col = pick_column(
        df,
        ["Planned date", "Close Date", "Completion Date", "Actual Date", "Date", "확인일", "수행일"],
    )

    records = {}
    for _, row in df.iterrows():
        task = normalize_task(row[task_col])
        ac_no = normalize_key(row[ac_col])
        if not task or not ac_no:
            continue

        record = {
            "DATE": row[date_col],
            "_sort_date": pd.to_datetime(row[date_col], errors="coerce"),
        }
        key = (task, ac_no)
        old = records.get(key)
        if old is None or record["_sort_date"] > old["_sort_date"]:
            records[key] = record

    print(f"IP24 Close Date 데이터 {len(records)}건 분석 완료")
    return records


def format_sheet_date(value) -> object:
    dt = pd.to_datetime(value, errors="coerce")
    if pd.isna(dt):
        return value
    return dt.strftime("%Y-%m-%d")


def read_aircraft_rows(worksheet) -> dict[int, str]:
    values = worksheet.get(AIRCRAFT_RANGE)
    rows = {}
    for index, row_values in enumerate(values, start=4):
        if row_values and row_values[0]:
            rows[index] = normalize_key(row_values[0])
    return rows


def read_task_headers(worksheet) -> dict[int, str]:
    values = worksheet.get("A2:W2")
    header_row = values[0] if values else []
    result = {}
    for block in AD_BLOCKS:
        zero_based_col = block["plan_col"] - 1
        if zero_based_col < len(header_row):
            task = normalize_task(header_row[zero_based_col])
            if task:
                result[block["plan_col"]] = task
    return result


def build_update_cells(worksheet, fhfc_data, ip24_data) -> list[Cell]:
    aircraft_rows = read_aircraft_rows(worksheet)
    task_headers = read_task_headers(worksheet)
    cells = []

    for row, ac_no in aircraft_rows.items():
        fhfc = fhfc_data.get(ac_no)
        if fhfc:
            cells.append(Cell(row=row, col=2, value=fhfc["FH"]))
            cells.append(Cell(row=row, col=3, value=fhfc["FC"]))

        for block in AD_BLOCKS:
            task = task_headers.get(block["plan_col"])
            if not task:
                continue

            record = ip24_data.get((task, ac_no))
            if not record:
                continue

            cells.append(Cell(row=row, col=block["date_col"], value=format_sheet_date(record["DATE"])))

    return cells


def update_repetitive_sheet(worksheet, fhfc_data, ip24_data) -> None:
    cells = build_update_cells(worksheet, fhfc_data, ip24_data)
    if not cells:
        raise RuntimeError("업데이트할 셀을 찾지 못했습니다. 엑셀 컬럼과 시트 PLAN/기번 값을 확인하세요.")

    worksheet.update_cells(cells, value_input_option="USER_ENTERED")
    print(f"구글시트 업데이트 완료: {len(cells)}개 셀")


def run_workflow() -> None:
    if is_sap_running():
        raise RuntimeError("SAP가 이미 실행 중입니다. 자동 입력 안정성을 위해 SAP를 종료한 뒤 다시 실행하세요.")

    if not FHFC_DOWNLOAD_DIR.exists():
        raise FileNotFoundError(f"FH/FC 다운로드 폴더를 찾을 수 없습니다: {FHFC_DOWNLOAD_DIR}")
    if not IP24_DOWNLOAD_DIR.exists():
        raise FileNotFoundError(f"IP24 다운로드 폴더를 찾을 수 없습니다: {IP24_DOWNLOAD_DIR}")

    worksheet = get_worksheet()
    gtl_values = read_gtl_values(worksheet)
    sap_password = get_sap_password()

    known_exports = current_export_files(EXPORT_SEARCH_DIRS)

    ip24_started = datetime.now()
    run_sap_file(IP24_SAP_FILE)
    login_to_sap(sap_password)
    sap_ip24_fill_and_export(gtl_values)
    ip24_export = wait_for_new_export(EXPORT_SEARCH_DIRS, known_exports, ip24_started, "IP24")
    close_excel_workbook(ip24_export)
    known_exports.add(ip24_export)

    fhfc_started = datetime.now()
    run_sap_file(FHFC_SAP_FILE)
    sap_fhfc_fill_and_export()
    fhfc_export = wait_for_new_export(EXPORT_SEARCH_DIRS, known_exports, fhfc_started, "FH/FC")
    close_excel_workbook(fhfc_export)

    ip24_data = parse_ip24_export(ip24_export)
    fhfc_data = parse_fhfc_export(fhfc_export)
    update_repetitive_sheet(worksheet, fhfc_data, ip24_data)


if __name__ == "__main__":
    try:
        run_workflow()
        print("전체 자동화 완료")
    except Exception as exc:
        print(f"오류: {exc}")
        input("종료하려면 Enter를 누르세요...")
        raise
