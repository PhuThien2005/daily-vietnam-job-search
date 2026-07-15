# 🔍 Vietnam Job Search Scraper & Automation

Hệ thống tự động hóa quét, tổng hợp và phân tích tin tuyển dụng vị trí **Java Backend Intern / Software Engineer Intern** tại khu vực TP. Hồ Chí Minh, phục vụ quá trình ứng tuyển của ứng viên **Đặng Phú Thiện**.

---

## 📊 Tổng Quan Dự Án

Dự án này là một pipeline tự động quét tin tuyển dụng từ nhiều nguồn uy tín tại Việt Nam (LinkedIn, ITviec, Ybox) theo tần suất hàng giờ, tự động chuẩn hóa dữ liệu, sắp xếp theo thời gian đăng mới nhất, cập nhật thời hạn nộp CV và gửi báo cáo trực tiếp đến Telegram cá nhân khi có thay đổi mới.

```
                  ┌──────────────┐
                  │ GitHub Cron  │ (Mỗi giờ)
                  └──────┬───────┘
                         ▼
        ┌──────────────────────────────────┐
        │  generate_daily_reports.py       │
        └────────────────┬─────────────────┘
                         │
        ┌────────────────┼─────────────────┐
        ▼                ▼                 ▼
 ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
 │   LinkedIn   │ │    ITviec    │ │     Ybox     │
 └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
        │                │                 │
        └────────────────┼─────────────────┘
                         ▼
        ┌──────────────────────────────────┐
        │   Lọc trùng & Sắp xếp theo       │
        │      thời gian đăng mới nhất     │
        └────────────────┬─────────────────┘
                         ▼
        ┌──────────────────────────────────┐
        │   Tính số ngày còn lại (PHS,     │
        │   Spartan X,...) & Đóng job hết hạn│
        └────────────────┬─────────────────┘
                         ▼
        ┌──────────────────────────────────┐
        │      Tạo 3 file báo cáo mới      │
        └────────────────┬─────────────────┘
                         ▼
        ┌──────────────────────────────────┐
        │   Kiểm tra Git Diff (Staged)     │
        └────────────────┬─────────────────┘
                         │ (Nếu có thay đổi)
                         ▼
        ┌──────────────────────────────────┐
        │  Commit, Push & Gửi Telegram Bot │
        └──────────────────────────────────┘
```

---

## 📁 Cấu Trúc Thư Mục

*   `tools/job-search/`: Chứa mã nguồn các công cụ cào dữ liệu và quản lý.
    *   [search_vietnam_jobs.py](file:///home/fhu_thjen/projects/java-intern/tools/job-search/search_vietnam_jobs.py): Scraper hợp nhất cào từ Ybox và ITviec, xử lý bộ lọc từ khóa và ghi file tổng hợp.
    *   [search_linkedin.py](file:///home/fhu_thjen/projects/java-intern/tools/job-search/search_linkedin.py): Scraper chuyên biệt cào LinkedIn Guest API theo từ khóa cấu hình.
    *   [generate_daily_reports.py](file:///home/fhu_thjen/projects/java-intern/tools/job-search/generate_daily_reports.py): Điều phối chạy các scraper, cập nhật đếm ngược deadline và tạo báo cáo tổng hợp chuyên sâu.
    *   [SKILL.md](file:///home/fhu_thjen/projects/java-intern/tools/job-search/SKILL.md): Cẩm nang hướng dẫn vận hành, các tiêu chuẩn lọc và cách mở rộng scraper.
*   `reports/`: Thư mục chứa báo cáo lịch sử chia theo ngày (`YYYY-MM-DD/`). Mỗi ngày bao gồm đúng 3 file:
    *   `job-search.md`: Báo cáo phân tích chuyên sâu (có đánh giá độ phù hợp ⭐, theo dõi dealine ứng tuyển và cập nhật danh sách tự động).
    *   `vietnam-jobs-scan.md`: Bảng quét thô hợp nhất từ các nguồn tại Việt Nam (sắp xếp mới nhất lên đầu).
    *   `linkedin-scan.md`: Danh sách quét thô từ LinkedIn.
*   `.github/workflows/`:
    *   [job-scraper.yml](file:///home/fhu_thjen/projects/java-intern/.github/workflows/job-scraper.yml): Workflow tự động hóa của GitHub Actions.

---

## ⚡ Các Tính Năng Nổi Bật

1.  **Cào Dữ Liệu Tự Động Không Cần Token/Tài Khoản**:
    *   **LinkedIn**: Sử dụng Guest API để tìm kiếm và trả về link direct ID sạch (dạng `https://www.linkedin.com/jobs/view/{job_id}/`), loại bỏ các tham số tracking phức tạp.
    *   **ITviec**: Tìm kiếm và bóc tách trực tiếp mã `job-slug` từ giao diện HTML tĩnh để sinh link trực tiếp.
    *   **Ybox**: Bóc tách trực tiếp trạng thái React SSR state (`window.__INITIAL_STATE__`) từ trang chủ tuyển dụng, cho phép lấy tin nhanh mà không cần API key.
2.  **Sắp Xếp Theo Thời Gian Thực**:
    *   Hệ thống phân tích các nhãn thời gian tương đối (`"6 minutes ago"`, `"20 hours ago"`, `"3 days ago"`) thành số giờ thực tế để sắp xếp danh sách từ **mới nhất đến cũ nhất**.
3.  **Tự Động Quản Lý Deadline**:
    *   Tự động tính toán số ngày còn lại đến hạn nộp (ví dụ: đếm ngược cho Phú Hưng Securities, Spartan X).
    *   Tự động phát hiện và gắn thẻ `(ĐÃ HẾT HẠN 🔴)` hoặc `(Đã đóng)` khi ngày hiện tại vượt quá deadline (như DigiEx Group).
4.  **Tối Ưu Hóa Tần Suất & Chống Spam Telegram**:
    *   GitHub Action được lên lịch chạy **mỗi giờ một lần** (`0 * * * *`).
    *   Workflow sử dụng `git diff` để kiểm tra sự thay đổi của nội dung báo cáo. Chỉ khi xuất hiện tin tuyển dụng mới hoặc có cập nhật về trạng thái/hạn nộp, hệ thống mới thực hiện Push lên GitHub và gửi thông báo kèm 3 file đính kèm qua Telegram Bot.

---

## 🚀 Hướng Dẫn Chạy Cục Bộ (Local)

Dự án được thiết kế hoàn toàn bằng các thư viện chuẩn của Python (standard libraries) như `urllib`, `re`, `json`, `os`, `sys`, `datetime` nên **không cần cài đặt thêm bất kỳ thư viện bên thứ ba nào** (no `pip install` required).

Để chạy quét và tạo báo cáo thủ công:
```bash
python3 tools/job-search/generate_daily_reports.py
```

Báo cáo sau khi quét sẽ được ghi trực tiếp vào thư mục `reports/YYYY-MM-DD/` tương ứng với ngày hiện tại (múi giờ ICT UTC+7).

---

## ⚙️ Cấu Hình GitHub Actions & Telegram Bot

Để kích hoạt tính năng tự động gửi tin nhắn về Telegram mỗi khi có thay đổi:

1.  **Tạo Bot Telegram**: Chat với `@BotFather` trên Telegram, gửi lệnh `/newbot` và nhận đoạn mã `HTTP API Token`.
2.  **Lấy Chat ID**: Chat với `@userinfobot` trên Telegram và nhấn **Start**, bot sẽ gửi lại dãy số `Id` cá nhân của bạn. Kích hoạt bot của bạn bằng cách nhấn **Start** trong cuộc trò chuyện riêng với bot.
3.  **Cài đặt Secrets trên GitHub**:
    Vào repository của bạn trên GitHub -> **Settings** -> **Secrets and variables** -> **Actions** -> Chọn **New repository secret** và thêm 2 biến sau:
    *   `TELEGRAM_TOKEN`: Mã Token của Bot nhận từ `@BotFather`.
    *   `TELEGRAM_TO`: Dãy số Chat ID nhận từ `@userinfobot`.

---

## 📝 Quy Trình Cập Nhật & Bảo Trì

Khi cần thêm từ khóa lọc hoặc sửa đổi hành vi cào dữ liệu, hãy tham khảo cẩm nang chi tiết tại [SKILL.md](file:///home/fhu_thjen/projects/java-intern/tools/job-search/SKILL.md) để đảm bảo không làm phá vỡ các quy tắc lọc và cấu trúc báo cáo của hệ thống.
