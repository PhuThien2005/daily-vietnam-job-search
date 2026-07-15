# 🔍 Vietnam Job Search Scraper & Automation

Hệ thống tự động hóa quét, tổng hợp và phân tích tin tuyển dụng vị trí **Java Backend Intern / Software Engineer Intern** tại khu vực TP. Hồ Chí Minh.

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

## 🧠 Tích Hợp AI Agent Skills & Subagents (Dành cho Antigravity IDE/CLI)

Nếu bạn đang phát triển dự án này bằng **Antigravity IDE** hoặc CLI `agy`, dự án đã được trang bị sẵn custom **Skill** và các cấu hình tích hợp **Subagents** để AI có thể tự động tìm kiếm thông minh:

### 1. Custom Skill: `job-search`
*   **Vị trí file cấu hình**: [tools/job-search/SKILL.md](file:///home/fhu_thjen/projects/java-intern/tools/job-search/SKILL.md)
*   **Cách hoạt động**: Khi bạn chat với Agent Antigravity và yêu cầu tìm job hoặc cập nhật báo cáo, Agent sẽ tự động đọc `SKILL.md` để nắm được các bài học kinh nghiệm tránh bịa đặt thông tin (anti-hallucination rules), cách bypass lỗi 403 Forbidden bằng Jina Reader, và quy chuẩn chấm điểm độ phù hợp (Match Score ⭐).

### 2. Sử Dụng Research Subagent (`research`)
Hệ thống tận dụng subagent `research` tích hợp sẵn của Antigravity để xử lý tìm kiếm song song:
*   **Nhiệm vụ**: Agent chính (Orchestrator) sẽ tự động chia nhỏ công việc và kích hoạt các subagent `research` chạy ngầm để đọc code, tra cứu dữ liệu web đồng thời từ nhiều nguồn khác nhau mà không làm nghẽn luồng xử lý chính.
*   **Cách kích hoạt nhanh**: Bạn có thể dùng slash command `/plan` hoặc `/goal` trực tiếp trong chat box để yêu cầu Agent phân rã task tìm kiếm và phân bổ cho các `research` subagents xử lý.

### 3. Prompt Mẫu Yêu Cầu Agent Quét Rộng (Nguồn Ngoài 3 Sàn Lớn)
Vì hệ thống chạy tự động (cron) hàng giờ chỉ quét 3 sàn lớn (LinkedIn, ITviec, Ybox) để tối ưu hiệu năng và tránh bị chặn, bạn có thể chủ động prompt cho AI Agent (Gemini/Claude) thực hiện quét sâu các diễn đàn trường đại học và trang tuyển dụng công ty bằng các câu lệnh mẫu sau:

*   **Prompt quét sâu diễn đàn trường & career page**:
    > "Hãy quét sâu diện rộng toàn bộ các diễn đàn trường đại học (UIT Forum, FIT HCMUS, HCMUTE Career) và trang career của các công ty công nghệ mục tiêu để cập nhật báo cáo job-search ngày hôm nay giúp mình."
*   **Prompt quét theo công nghệ & xác minh link ứng tuyển**:
    > "Tìm kiếm thêm các vị trí Java/Backend Intern yêu cầu Spring Boot mới nhất trên các trang web tuyển dụng công ty tại TP.HCM. Hãy dùng trình duyệt để xác minh link apply hoạt động và cập nhật trực tiếp vào file báo cáo."

---

## 📝 Quy Trình Cập Nhật & Bảo Trì

Khi cần thêm từ khóa lọc hoặc sửa đổi hành vi cào dữ liệu, hãy tham khảo cẩm nang chi tiết tại [SKILL.md](file:///home/fhu_thjen/projects/java-intern/tools/job-search/SKILL.md) để đảm bảo không làm phá vỡ các quy tắc lọc và cấu trúc báo cáo của hệ thống.
