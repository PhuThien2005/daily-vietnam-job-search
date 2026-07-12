# 🔍 Hướng Dẫn Prompt Tạo Báo Cáo Tìm Kiếm Việc Làm (Job Search Tool)

Tài liệu này hướng dẫn cách tương tác và viết prompt với AI Agent (Gemini/Claude) để kích hoạt công cụ tìm kiếm và tự động tạo báo cáo việc làm chất lượng cao, tuân thủ đúng quy trình xác minh nghiêm ngặt.

---

## 🚀 Các Prompt Mẫu Kích Hoạt

Bạn có thể sử dụng các mẫu prompt dưới đây để yêu cầu AI Agent chạy công cụ tìm kiếm việc làm:

### 1. Tìm kiếm và cập nhật định kỳ (Khuyên dùng)
> "Tìm kiếm và cập nhật cho mình danh sách các vị trí thực tập Java/Backend/Software Engineering mới nhất tại TP.HCM ngày hôm nay. Hãy chạy quy trình xác minh trạng thái và xuất báo cáo mới vào thư mục reports."

### 2. Tìm kiếm mở rộng (Đa quốc gia & LinkedIn)
> "Mở rộng tìm kiếm các vị trí thực tập Backend/Java tại các công ty công nghệ đa quốc gia (MNCs) ở TP.HCM. Hãy quét qua LinkedIn, các cổng careers của công ty (Greenhouse, Lever, SmartRecruiters) và verify xem job nào thực sự còn mở nhé."

### 3. Tìm theo công nghệ cụ thể
> "Tìm kiếm các vị trí thực tập sinh yêu cầu kỹ năng Spring Boot và cơ sở dữ liệu PostgreSQL ở khu vực TP.HCM. Xuất báo cáo và chỉ giữ lại các job đang tuyển (🟢)."

### 4. Tìm kiếm từ nguồn Đại học/Cộng đồng
> "Quét các diễn đàn trường đại học như UIT Forum, FIT HCMUS, HCMUTE Career Hub để tìm các chương trình thực tập IT hoặc Fresher mới đăng trong 2 tuần qua."

---

## 🛠️ Quy Trình Tự Động Của AI Agent (Workflow)

Khi nhận được prompt, AI Agent sẽ tự động chạy các bước sau:

```
[ Đọc search-config.json ]  --> Lấy profile ứng viên & danh sách 25+ công ty
          ↓
[ Phân chia Subagents ]      --> Quét Job Platforms (LinkedIn, ITviec, TopCV...)
                            --> Quét University pages (FIT HCMUS, UIT Forum...)
                            --> Quét Career portals trực tiếp (Greenhouse, Lever...)
          ↓
[ XÁC MINH BẮT BUỘC ]       --> Đọc HTML trang gốc (read_url_content)
                            --> Check thông báo ẩn: "job expired", "không tồn tại"
                            --> Lấy ngày đăng gốc (Original posted date) & Link chi tiết
          ↓
[ Chấm Điểm & Phân Loại ]   --> Chấm Match Score (1-5⭐) dựa trên CV ứng viên
                            --> Phân loại: 🟢 ĐANG MỞ | 🟡 KHÔNG RÕ | 🔴 ĐÃ ĐÓNG
          ↓
[ Xuất Báo Cáo ]            --> Tạo file reports/job-search-YYYY-MM-DD.md
                            --> Cập nhật hệ thống Artifact hiển thị trực quan
```

---

## 📌 Các Nguyên Tắc Chất Lượng Dữ Liệu (Phải Tuân Thủ)

Báo cáo được tạo ra luôn đảm bảo:
1.  **Link gốc chi tiết (Direct Link)**: Luôn là link dẫn thẳng tới trang tuyển dụng cụ thể của job đó (Ví dụ: `https://www.geocomply.com/careers/all-jobs/ho-chi-minh-software-engineer-intern-backend/`), tuyệt đối không dùng link trang chủ chung chung.
2.  **Ngày đăng gốc (Original Posted Date)**: Hiển thị ngày sớm nhất job xuất hiện thay vì hạn nộp hồ sơ, giúp bạn nộp sớm nhất có thể (tuyển dụng dạng *rolling*).
3.  **Xác minh trạng thái thực tế**: Tự động loại bỏ các job đã đóng hoặc hết hạn (như Zalo Tech Fresher, SRT Group) vào mục `🔴 ĐÃ ĐÓNG / THEO DÕI ĐỢT SAU` để tránh mất thời gian ứng tuyển.

---

## 📂 Quản Lý File Cấu Hình

Bạn có thể cập nhật thông tin CV hoặc danh sách công ty cần quét bằng cách chỉnh sửa trực tiếp file cấu hình:
*   [search-config.json](file:///home/fhu_thjen/projects/java-intern/tools/job-search/search-config.json) (Chứa profile CV của bạn, các từ khóa, các nguồn trang web, và danh sách 25+ công ty mục tiêu).
