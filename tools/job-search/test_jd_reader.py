#!/usr/bin/env python3
"""Regression tests for the JD experience filter. Run: python3 tools/job-search/test_jd_reader.py"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jd_reader import experience_label, extract_experience, extract_flags  # noqa: E402
from job_filters import apply_experience_filter, load_profile  # noqa: E402

# (description text, expected label, expected to be removed with max_years_experience = 2)
CASES = [
    ("Requirements\n- Over 5 years of experience in backend development, preferably with large-scale systems.", "> 5 năm", True),
    ("Minimum of 3 years of professional experience in backend software development.", "≥ 3 năm", True),
    ("At least three (3) years of experience with Java", "≥ 3 năm", True),
    ("5 years Java development", "≥ 5 năm", True),
    ("Two years of experience with Spring Boot", "≥ 2 năm", False),
    ("0-1 year experience, fresh graduates are welcome", "0 năm (nhận fresher)", False),
    ("1 - 2 years of working experience with Java", "≥ 1 năm", False),
    ("6 months of experience with Spring", "≥ 6 tháng", False),
    ("Có ít nhất 3 năm kinh nghiệm lập trình Java", "≥ 3 năm", True),
    ("Tối thiểu ba năm kinh nghiệm làm việc với Spring Boot", "≥ 3 năm", True),
    ("Có trên 2 năm kinh nghiệm phát triển backend", "> 2 năm", True),
    ("Có hơn hai năm kinh nghiệm Java", "> 2 năm", True),
    ("Từ 1-2 năm kinh nghiệm với .NET", "≥ 1 năm", False),
    ("Có năm năm kinh nghiệm ở vị trí tương đương", "≥ 5 năm", True),
    ("Kinh nghiệm: 3 năm trở lên", "≥ 3 năm", True),
    ("Có 6 tháng kinh nghiệm thực tập là lợi thế", "≥ 6 tháng (ưu tiên)", False),
    ("Ưu tiên ứng viên có 3 năm kinh nghiệm", "≥ 3 năm (ưu tiên)", False),
    ("3+ years with AWS is a plus", "≥ 3 năm (ưu tiên)", False),
    ("5 years of experience with Kafka (preferred)", "≥ 5 năm (ưu tiên)", False),
    ("Preferred experience:\n3+ years with Kafka", "≥ 3 năm (ưu tiên)", False),
    ("Bachelor degree preferred.\nExperience Requirements\n5+ years of development experience", "≥ 5 năm", True),
    ("Experts with over 15 years of experience\nRequired Qualifications\n1–3 years of software development experience.", "≥ 1 năm", False),
    ("Our company has over 20 years of experience delivering software", "Không ghi số năm", False),
    ("14 day-off per year along with experienced managers", "Không ghi số năm", False),
    ("Độ tuổi 22-30 năm, có kinh nghiệm là lợi thế", "Không ghi số năm", False),
    ("Sinh viên năm cuối, năm 2026", "Không ghi số năm", False),
    ("Không yêu cầu kinh nghiệm, chấp nhận sinh viên năm cuối", "Không ghi số năm", False),
]


FLAG_CASES = [
    ("Sau thực tập có cơ hội trở thành nhân viên chính thức", ["convert"]),
    ("Cơ hội được ký hợp đồng chính thức sau kỳ thực tập", ["convert"]),
    ("Xét chuyển chính thức sau 3 tháng", ["convert"]),
    ("Được giữ lại làm việc sau khi tốt nghiệp", ["convert"]),
    ("Opportunity to become a full-time employee after the internship", ["convert"]),
    ("Outstanding interns will receive a return offer.", ["convert"]),
    ("Monthly allowance and opportunity to be converted to a full-time position", ["convert", "paid"]),
    ("Thực tập sinh có lương 5 triệu/tháng", ["paid"]),
    ("Trợ cấp thực tập 4.000.000 VNĐ", ["paid"]),
    ("We are a full-time remote team", []),
    ("Lương tháng 13, chế độ bảo hiểm đầy đủ", []),
    ("Hợp đồng chính thức ngay từ ngày đầu, lương 15-20 triệu", []),
]


class FlagTest(unittest.TestCase):
    def test_flags(self):
        for text, flags in FLAG_CASES:
            with self.subTest(text=text):
                self.assertEqual(sorted(extract_flags(text)), sorted(flags))


class ExperienceFilterTest(unittest.TestCase):
    def test_cases(self):
        profile = {**load_profile(), "max_years_experience": 2}
        for text, label, removed in CASES:
            with self.subTest(text=text):
                jd = {"read": True, **(extract_experience(text) or {})}
                self.assertEqual(experience_label(jd), label)
                self.assertEqual(bool(apply_experience_filter([{"jd": jd}], profile)[1]), removed)

    def test_unread_jd_is_kept(self):
        kept, removed = apply_experience_filter([{"jd": {"read": False}}], load_profile())
        self.assertEqual((len(kept), len(removed)), (1, 0))


if __name__ == "__main__":
    unittest.main()
