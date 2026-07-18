#!/usr/bin/env python3
import os
import sys
import re
import subprocess
from datetime import datetime, date, timezone, timedelta

def run_script(script_name):
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    print(f"Running {script_name}...")
    try:
        result = subprocess.run([sys.executable, script_path], check=True, capture_output=True, text=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_name}: {e}")
        print(e.stderr)

def get_latest_report_date(reports_dir, today_str):
    dates = []
    if not os.path.exists(reports_dir):
        return None
    for name in os.listdir(reports_dir):
        if os.path.isdir(os.path.join(reports_dir, name)) and re.match(r'^\d{4}-\d{2}-\d{2}$', name):
            if name != today_str:
                dates.append(name)
    if not dates:
        return None
    dates.sort()
    return dates[-1]

def calculate_remaining_days(deadline_str, target_date):
    try:
        # Expected format: DD/MM/YYYY
        day, month, year = map(int, deadline_str.split('/'))
        deadline_date = date(year, month, day)
        diff = (deadline_date - target_date).days
        return diff
    except Exception:
        return None

def update_deadlines(content, today_date):
    # Update DigiEx (12/07/2026)
    digiex_deadline = date(2026, 7, 12)
    if today_date == digiex_deadline:
        content = re.sub(
            r'⚠️ \*\*Hạn nộp\*\*: \*\*12/07/2026\*\*.*',
            '⚠️ **Hạn nộp**: **12/07/2026** (HẾT HẠN HÔM NAY! Nộp gấp trước 23h59!)',
            content
        )
    elif today_date > digiex_deadline:
        content = re.sub(
            r'⚠️ \*\*Hạn nộp\*\*: \*\*12/07/2026\*\*.*',
            '⚠️ **Hạn nộp**: **12/07/2026** (ĐÃ HẾT HẠN 🔴)',
            content
        )
        # Move DigiEx to closed or mark it clearly
        if '### 1. 🆕 DigiEx Group — Backend Intern (Đã đóng)' not in content:
            content = content.replace('### 1. 🆕 DigiEx Group — Backend Intern', '### 1. 🆕 DigiEx Group — Backend Intern (Đã đóng)')
        
    # Update PHS (15/07/2026)
    phs_days = calculate_remaining_days("15/07/2026", today_date)
    if phs_days is not None:
        if phs_days > 0:
            content = re.sub(
                r'⚠️ \*\*Hạn nộp\*\*: \*\*15/07/2026\*\* \(Còn \d+ ngày!\)',
                f'⚠️ **Hạn nộp**: **15/07/2026** (Còn {phs_days} ngày!)',
                content
            )
        elif phs_days == 0:
            content = re.sub(
                r'⚠️ \*\*Hạn nộp\*\*: \*\*15/07/2026\*\*.*',
                '⚠️ **Hạn nộp**: **15/07/2026** (HẾT HẠN HÔM NAY!)',
                content
            )
        else:
            content = re.sub(
                r'⚠️ \*\*Hạn nộp\*\*: \*\*15/07/2026\*\*.*',
                '⚠️ **Hạn nộp**: **15/07/2026** (ĐÃ HẾT HẠN 🔴)',
                content
            )

    # Update Spartan X (~14/07/2026)
    spartan_days = calculate_remaining_days("14/07/2026", today_date)
    if spartan_days is not None:
        if spartan_days > 0:
            content = re.sub(
                r'⚠️ \*\*Hạn nộp\*\*: \*\*~14/07/2026\*\* \((?:Có thể chỉ còn|Còn) \d+ ngày[^)]*\)',
                f'⚠️ **Hạn nộp**: **~14/07/2026** (Còn {spartan_days} ngày — CẦN CHECK GẤP!)',
                content
            )
        elif spartan_days == 0:
            content = re.sub(
                r'⚠️ \*\*Hạn nộp\*\*: \*\*~14/07/2026\*\*.*',
                '⚠️ **Hạn nộp**: **~14/07/2026** (HẾT HẠN HÔM NAY!)',
                content
            )
        else:
            content = re.sub(
                r'⚠️ \*\*Hạn nộp\*\*: \*\*~14/07/2026\*\*.*',
                '⚠️ **Hạn nộp**: **~14/07/2026** (ĐÃ HẾT HẠN 🔴)',
                content
            )
            
    return content

def generate_job_search_report():
    ict_tz = timezone(timedelta(hours=7))
    today = datetime.now(ict_tz)
    today_str = today.strftime("%Y-%m-%d")
    today_date = today.date()
    
    project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    reports_dir = os.path.join(project_dir, "reports")
    today_dir = os.path.join(reports_dir, today_str)
    
    # 1. Get latest report to use as template
    today_report_path = os.path.join(today_dir, "job-search.md")
    template_path = None
    
    if os.path.exists(today_report_path):
        template_path = today_report_path
        print(f"Found existing today's report, using it as template: {template_path}")
    else:
        latest_date = get_latest_report_date(reports_dir, today_str)
        if latest_date:
            template_path = os.path.join(reports_dir, latest_date, "job-search.md")
            print(f"Found template from {latest_date}: {template_path}")
            
    if template_path and os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Update title and search date
        content = re.sub(r'# 🔍 Báo Cáo Tìm Kiếm Việc Làm Intern — Cập nhật \d{2}/\d{2}/\d{4}', f'# 🔍 Báo Cáo Tìm Kiếm Việc Làm Intern — Cập nhật {today.strftime("%d/%m/%Y")}', content)
        content = re.sub(r'\*\*Ngày tìm kiếm\*\*: \d{2}/\d{2}/\d{4}', f'**Ngày tìm kiếm**: {today.strftime("%d/%m/%Y")}', content)
        
        # Update deadlines countdowns
        content = update_deadlines(content, today_date)
        
        # Append new scan results if we have them
        scan_report_path = os.path.join(today_dir, "vietnam-jobs-scan.md")
        if os.path.exists(scan_report_path):
            with open(scan_report_path, "r", encoding="utf-8") as sf:
                scan_lines = sf.readlines()
                
            # Find the job listing table from scan report
            table_lines = []
            start_table = False
            for line in scan_lines:
                if line.startswith("| # |") or line.startswith("|---|"):
                    start_table = True
                    table_lines.append(line)
                elif start_table and line.startswith("|"):
                    table_lines.append(line)
                elif start_table and not line.strip():
                    break
            
            if table_lines:
                # Remove existing "CÁC TIN TUYỂN DỤNG QUÉT ĐƯỢC" section if present
                content = re.split(r'## 📋 Bảng tổng hợp', content)[0]
                content += "\n## 📋 Bảng tổng hợp vị trí đang mở & cần chú ý (Quét tự động)\n\n"
                content += "".join(table_lines)
                content += "\n\n*Lưu ý: Bảng trên được cập nhật tự động bằng script quét. Để xem phân tích chuyên sâu cho từng vị trí, vui lòng đối chiếu với phần mô tả ở trên.*\n"
    else:
        # Basic Fallback Template
        print("No template found. Creating basic fallback template...")
        content = f"""# 🔍 Báo Cáo Tìm Kiếm Việc Làm Intern — Cập nhật {today.strftime("%d/%m/%Y")}

**Ngày tìm kiếm**: {today.strftime("%d/%m/%Y")}
**Ứng viên**: Đặng Phú Thiện
**Vị trí mục tiêu**: Java Backend Intern | Software Engineer Intern

---

## 📊 Tổng quan
Vui lòng xem báo cáo quét thô `vietnam-jobs-scan.md` và `linkedin-scan.md` trong thư mục này để có danh sách đầy đủ.
"""

    # 2. Write to today's folder
    os.makedirs(today_dir, exist_ok=True)
    today_report_path = os.path.join(today_dir, "job-search.md")
    with open(today_report_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    print(f"Generated job-search.md for today at: {today_report_path}")

def main():
    print("🌅 Starting daily report generation workflow...")
    # Run scrapers
    run_script("search_vietnam_jobs.py")
    run_script("search_linkedin.py")
    # Generate unified job-search report
    generate_job_search_report()
    print("✨ All reports generated successfully!")

if __name__ == "__main__":
    main()
