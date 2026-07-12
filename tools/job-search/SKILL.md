---
name: job-search
description: >
  Tìm kiếm việc làm Java/Backend/Software Intern ở HCM City từ nhiều nguồn
  (LinkedIn, TopCV, ITviec, Indeed, career pages đại học, trang tuyển dụng công ty).
  Tạo báo cáo .md chi tiết với link trực tiếp tới job posting.
  Sử dụng: Prompt "tìm job intern java hcm" hoặc "cập nhật danh sách job intern"
---

# Job Search Skill - Tìm Job Intern Java/Backend HCM

## ⚠️ Bài học từ lỗi hallucination (cập nhật 11/07/2026)

Trong lần chạy đầu tiên, subagent đã tạo ra báo cáo chứa **nhiều thông tin bịa đặt**:
- Liệt kê job không tồn tại (FPT Software Fresher Java → YBOX tìm ra 0 kết quả)
- Ghi sai ngày (DEKON internship thực tế đăng 19/05/2026 cho đợt 06/2026, không phải 10/07/2026)
- Điền link TopCV/Glints giả (URL dạng `/1278892.html` tự bịa ra không tồn tại)
- Tổng hợp từ AI search synthesis (Google search summary) rồi trình bày như sự thật đã xác minh

**Nguyên nhân gốc**: `search_web` trả về tóm tắt AI-generated, KHÔNG phải nội dung trang thật. Dùng kết quả này để điền thông tin job là hallucination.

---

## Mục đích
Skill này giúp tìm kiếm, lọc và tổng hợp các vị trí thực tập (intern)
Java/Backend/Software Engineering ở HCM City từ nhiều nguồn khác nhau.

## Workflow bắt buộc

### Bước 1: Đọc cấu hình
Đọc file cấu hình tại: `tools/job-search/search-config.json`
- Lấy thông tin profile ứng viên
- Lấy danh sách nguồn tìm kiếm
- Lấy search settings (max_days_old, locations, etc.)

### Bước 2: Tìm kiếm — LẤY URL THẬT

Dùng `search_web` CHỈ để **tìm ra URL** của bài đăng, KHÔNG dùng nội dung tóm tắt của search để điền thông tin job.

Query mẫu để tìm URL:
```
site:itviec.com "Java Intern" "Ho Chi Minh" 2026
site:topcv.vn "thực tập" "java" "hồ chí minh" 2026
site:ybox.vn "Java" "intern" "thực tập" HCM 2026
site:forum.uit.edu.vn "[KTTT]" java OR backend intern 2026
```

Nguồn ưu tiên theo thứ tự:
1. **ATS trực tiếp**: Greenhouse, Lever, SmartRecruiters, Workday của từng công ty
2. **Job boards lớn**: ITviec, TopCV, YBOX, Glints, VietnamWorks, CareerViet, CareerLink
3. **Diễn đàn trường**: UIT Forum (`forum.uit.edu.vn/c/ho-tro-doi-song/viec-lam-thuc-tap/32`), FIT HCMUS, HCMUTE
4. **Career page công ty**: Bosch, GeoComply, VNG, OPSWAT, ShopBack, v.v.

**Tối ưu search quality (tìm job mới nhất):**
- Dùng `after:YYYY-MM-DD` trong query Google để lọc kết quả mới
- Ưu tiên query site-specific: `site:itviec.com "java intern" "ho chi minh" 2026`
- Kết hợp nhiều query nhỏ thay vì 1 query lớn
- Thêm query tiếng Việt: `"thực tập" "java" OR "backend" "hồ chí minh"`

**Xử lý trang bị chặn (403 Forbidden):**
- Khi `read_url_content(url)` trả về 403, thử qua **Jina Reader**: `read_url_content("https://r.jina.ai/" + url)`
- Các trang thường bị chặn: Glints, TopCV, Greenhouse, Workable (CAPTCHA)
- Nếu Jina Reader cũng thất bại → ghi rõ 🟡 Chưa xác minh, yêu cầu user check bằng browser

### Bước 3: Xác minh — ĐỌC TRANG THẬT (BẮT BUỘC)

**MỖI JOB** phải được xác minh bằng `read_url_content(url)` trước khi đưa vào báo cáo.

Kiểm tra sau khi đọc:
- Tên công ty và vị trí có khớp không?
- Ngày đăng thực tế là bao nhiêu?
- Trang có thông báo "đã đóng / expired / không tồn tại" không?
- Yêu cầu kỹ năng thực tế là gì?

**NẾU `read_url_content` thất bại (404, 403, timeout)**: Ghi rõ trong báo cáo, đánh `🟡 Chưa xác minh` — KHÔNG được suy đoán hay điền thông tin từ search summary.

### Bước 4: Tổng hợp — CHỈ GHI THÔNG TIN ĐÃ ĐỌC TRỰC TIẾP

Với mỗi job đã xác minh, thu thập từ nội dung trang thật:
1. **Tên công ty** — từ trang gốc
2. **Vị trí** — từ trang gốc
3. **Địa điểm** — từ trang gốc
4. **Ngày đăng gốc** — từ trang gốc (ghi rõ nguồn)
5. **Trạng thái**: 🟢 Đang mở / 🟡 Chưa xác minh / 🔴 Đã đóng
6. **Link gốc** — URL đã dùng để `read_url_content`, KHÔNG phải URL tự bịa
7. **Yêu cầu chính** — trích từ nội dung trang thật
8. **Match score** (1-5 ⭐)

### Bước 5: Tạo báo cáo

Tạo file: `reports/job-search-YYYY-MM-DD.md`

Format mỗi entry:
```markdown
### [Tên Công Ty] — [Vị Trí]
- 📍 Địa điểm: ... (nguồn: [url đã đọc])
- 📅 Ngày đăng: DD/MM/YYYY (xác minh từ trang gốc)
- 🔗 [Link apply](url_đã_đọc_thật)
- 📋 Yêu cầu: ... (trích từ JD)
- ⭐ Phù hợp: X/5
- 📎 Xác minh: read_url_content ✅ / ❌ thất bại (lý do)
```

---

## Quy tắc tuyệt đối (KHÔNG ĐƯỢC VI PHẠM)

1. **Không dùng search summary làm nguồn thông tin**
   `search_web` chỉ dùng để tìm URL. Nội dung AI-generated trong search summary là không đáng tin và KHÔNG được dùng để điền thông tin job.

2. **Không điền URL nếu chưa `read_url_content` thành công**
   URL phải là URL đã thực sự fetch được nội dung. Tuyệt đối không điền URL tự suy đoán theo pattern (ví dụ: tự ghép `/viec-lam/java-intern-company/12345.html`).

3. **Không suy diễn thông tin từ tên công ty**
   Nếu biết công ty thường tuyển Java intern nhưng không tìm thấy post cụ thể → KHÔNG liệt kê. Ghi vào mục "Theo dõi thêm" với note rõ ràng.

4. **Ngày đăng phải đọc từ trang thật**
   Không ước tính ngày. Nếu trang không hiển thị ngày → ghi "Không rõ ngày".

5. **Trạng thái mặc định là 🟡 nếu chưa `read_url_content`**
   Chỉ được đánh 🟢 khi đã đọc trang thật và xác nhận form/nút apply còn hoạt động.

6. **Mỗi entry phải ghi rõ: `📎 Xác minh: read_url_content ✅` hoặc `❌ thất bại`**
   Đây là bằng chứng bắt buộc để người đọc biết thông tin nào đáng tin.

---

## Danh sách nguồn tìm kiếm
Xem file `tools/job-search/search-config.json` để biết danh sách đầy đủ các nguồn.

### Unified Aggregated Scraper Integration (`search_vietnam_jobs.py`)
Để cào danh sách job mới nhất từ nhiều trang web mà không bị chặn bởi tường đăng nhập (login walls) hay CAPTCHA, chúng tôi tích hợp công cụ quét hợp nhất tại [search_vietnam_jobs.py](file:///home/fhu_thjen/projects/java-intern/tools/job-search/search_vietnam_jobs.py).

Các kỹ thuật bypass và thu thập dữ liệu cụ thể cho từng nguồn:
1. **LinkedIn Guest API**:
   - Gửi request trực tiếp tới Guest API Search endpoint của LinkedIn: `https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search`.
   - Parse các thẻ `<li>` trả về để lấy tiêu đề, công ty, địa điểm và thời gian.
   - **Tối ưu link**: Tự động chuyển đổi toàn bộ URL sang định dạng ID trực tiếp `https://www.linkedin.com/jobs/view/{job_id}/` (tránh lỗi redirect/login-wall của link SEO-slug).
2. **Ybox (React State Parser)**:
   - Thay vì cào HTML động (React client-side rendering), script tải trực tiếp trang tĩnh `https://ybox.vn/tuyen-dung` và trích xuất React state được nhúng trong thẻ script qua biến `window.__INITIAL_STATE__ = { ... }`.
   - Sử dụng thuật toán brace-matching để parse chính xác JSON state và lấy danh sách `NewestPosts` cùng `HighlightPosts` thời gian thực.
   - **Tối ưu link**: Định dạng link trực tiếp theo cấu trúc rút gọn của Ybox: `https://ybox.vn/tuyen-dung/job-{_id}`.
3. **ITviec (Job Card Scraper)**:
   - Tải trang tìm kiếm của ITviec (ví dụ: `/it-jobs/java-intern-ho-chi-minh`) và phân tách HTML theo thẻ `class='job-card '`.
   - Trích xuất tiêu đề, công ty, thời gian đăng từ thuộc tính của card.
   - **Tối ưu link**: Định dạng link trực tiếp: `https://itviec.com/it-jobs/{slug}`.

Công cụ này tự động hóa toàn bộ việc quét, lọc trùng, lọc bỏ các job Senior/Manager và ghi nhận kết quả sạch vào thư mục `reports/vietnam-jobs-scan-YYYY-MM-DD.md`.

## Yêu cầu công cụ
- `search_web`: Chỉ dùng để tìm URL, KHÔNG dùng nội dung tóm tắt
- `read_url_content`: **Bắt buộc** cho mỗi job trước khi đưa vào báo cáo
- `write_to_file`: Tạo báo cáo

### Bước 5: Tạo báo cáo
Tạo file báo cáo MD tại: `reports/job-search-YYYY-MM-DD.md`

Format báo cáo:
```markdown
# 🔍 Báo Cáo Tìm Kiếm Việc Làm Intern
**Ngày tìm kiếm**: YYYY-MM-DD
**Ứng viên**: Đặng Phú Thiện
**Vị trí mục tiêu**: Java Backend Intern | Software Engineer Intern
**Khu vực**: HCM City

## 📊 Tổng quan
- Tổng số job tìm được: X
- Số job đang mở (🟢): X
- Số job phù hợp cao (4-5⭐): X
- Số nguồn đã tìm: X

## 🔴 KHẨN CẤP (Đăng gần đây hoặc Sắp đóng)
### 1. [Tên công ty] - [Vị trí]
- 📍 Địa điểm: ...
- 📅 Ngày đăng gốc: DD/MM/YYYY (nguồn: ...)
- 🔗 [Link gốc ứng tuyển](url_gốc_chi_tiết)
- 📋 Yêu cầu: ...
- ⭐ Phù hợp: 5/5
- 💡 Ghi chú: ...

## 🟢 ĐANG TUYỂN (Đã xác minh còn hạn)
### 1. [Tên công ty] - [Vị trí]
- 📍 Địa điểm: ...
- 📅 Ngày đăng gốc: DD/MM/YYYY
- 🔗 [Link gốc ứng tuyển](url_gốc_chi_tiết)
- 📋 Yêu cầu: ...
- ⭐ Phù hợp: ...

## 🔴 ĐÃ ĐÓNG / THEO DÕI ĐỢT SAU
### 1. Zalo - Tech Fresher 2026
- 🔗 [Link gốc](https://zalo.careers/techfresher)
- 💡 Ghi chú: Đã đóng nhận CV từ ngày 22/05/2026. Onboard 13/07/2026.

## 📋 Bảng tổng hợp
| # | Công ty | Vị trí | Ngày đăng gốc | Trạng thái | Match | Link chi tiết |
|---|---------|--------|---------------|------------|-------|---------------|

## 📌 Ghi chú & Khuyến nghị
- Chiến lược apply: ...
- Thứ tự ưu tiên: ...
```

### Quy tắc quan trọng
1. **Link chi tiết gốc**: BẮT BUỘC dẫn tới trang mô tả chi tiết của job đó (ví dụ: `https://www.geocomply.com/careers/all-jobs/ho-chi-minh-software-engineer-intern-backend/`), tuyệt đối không dùng link trang chủ chung chung `https://www.geocomply.com/careers/`.
2. **Ngày đăng gốc**: Xác minh ngày đăng sớm nhất thay vì hạn nộp. DN tuyển theo kiểu rolling cần apply càng sớm càng tốt.
3. **Đọc và xác minh**: Dùng `read_url_content` kiểm tra hạn nộp/thông báo tuyển dụng trên trang gốc để phân loại đúng trạng thái (🟢/🔴). Loại bỏ các chương trình đã đóng khỏi mục "Đang tuyển".
4. **Lọc trùng**: Giữ lại tin đăng gốc của doanh nghiệp, bỏ qua tin đăng gián tiếp.
5. **Minh bạch nguồn & Cảnh báo link không xác minh**:
   - Với mỗi job listing, BẮT BUỘC ghi rõ trường `📎 Nguồn xác minh:` nêu rõ nguồn tìm thấy (ví dụ: ITviec, TopCV, UIT Forum, website công ty, YBOX, email HR...) và URL cụ thể của bài đăng nếu có.
   - Nếu **không tìm thấy URL bài đăng cụ thể** (chỉ tìm được trang công ty chung chung hoặc thông tin tổng hợp từ web search), phải ghi rõ cảnh báo `⚠️ Lưu ý: Cần xác minh thêm — không tìm thấy post public cụ thể` trong trường nguồn xác minh.
   - Không được tự ý điền email/link nộp hồ sơ nếu chưa được xác minh trực tiếp từ trang tuyển dụng gốc của công ty. Phải ghi chú rõ `(chưa xác minh)` hoặc `(tham khảo từ các đợt trước)` nếu chỉ là ước tính.
   - Các vị trí chỉ xác minh qua AI search synthesis (không có URL gốc dẫn đến trang job cụ thể) phải được đánh dấu `🟡 Chưa xác minh` thay vì `🟢 Đang tuyển`.

## Danh sách nguồn tìm kiếm (cập nhật)
Xem file `tools/job-search/search-config.json` để biết danh sách đầy đủ các nguồn.
Có thể thêm/bớt nguồn bằng cách chỉnh sửa file config.

## Yêu cầu công cụ
- `search_web`: Tìm kiếm web
- `read_url_content`: Đọc nội dung trang web  
- `write_to_file`: Tạo báo cáo
- Subagents: Chạy song song các tìm kiếm

