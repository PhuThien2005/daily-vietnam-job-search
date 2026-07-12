#!/usr/bin/env bash
# ============================================================
# Job Search Quick Reference
# ============================================================
# Sử dụng với AI Agent (Claude/Gemini) bằng cách prompt:
#
# 1. Tìm job mới:
#    "Tìm job intern java/backend HCM mới nhất"
#    "Cập nhật danh sách job intern cho tui"
#
# 2. Tìm theo công ty cụ thể:
#    "Tìm intern ở VNG, Shopee, Bosch"
#
# 3. Tìm chương trình thực tập:
#    "Tìm các chương trình Star Camp, Fresher Academy 2026"
#
# 4. Lọc theo skill:
#    "Tìm job intern yêu cầu Spring Boot"
#
# Kết quả sẽ được lưu tại:
#   reports/job-search-YYYY-MM-DD.md
#
# Cấu hình nguồn tìm kiếm:
#   tools/job-search/search-config.json
#
# Skill instructions:
#   tools/job-search/SKILL.md
# ============================================================

echo "📋 Job Search Tool - Quick Reference"
echo "====================================="
echo ""
echo "Cấu hình: tools/job-search/search-config.json"
echo "Skill:     tools/job-search/SKILL.md"
echo ""
echo "Báo cáo gần nhất:"
ls -la reports/job-search-*.md 2>/dev/null || echo "  (Chưa có báo cáo nào)"
echo ""
echo "Sử dụng:"
echo "  1. Prompt AI Agent với yêu cầu tìm job"
echo "  2. Quét trực tiếp LinkedIn/Ybox/ITviec: python3 tools/job-search/search_vietnam_jobs.py"
