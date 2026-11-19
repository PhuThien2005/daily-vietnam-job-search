#!/usr/bin/env python3
"""Vietnamese job sources that are friendlier to students/freshers than LinkedIn.

- VietnamWorks: public search API (IT jobs in Ho Chi Minh City), structured years of experience + level.
- TopDev: public API, structured experience ("Không yêu cầu", "2 năm", "Trên 10 năm") + level.
- CareerLink: server-rendered search pages (HCM + keyword).

Every job dict uses the shared shape: source, title, company, location, time ("N days ago"), link, id,
optional level_hint ("Intern"/"Fresher"/"Junior"/"__senior__") and optional jd (experience already known).
"""
import json
import re
import time
import urllib.parse
from datetime import datetime, timezone, timedelta

from http_util import http_get
from jd_reader import extract_experience, html_to_text
from job_filters import clean_text, get_platform

ICT = timezone(timedelta(hours=7))


def ago_text(dt):
    """datetime → 'N hours ago' / 'N days ago' (format understood by parse_time_to_hours)."""
    hours = max(0, (datetime.now(timezone.utc) - dt).total_seconds() / 3600)
    if hours < 1:
        return "Just now"
    if hours < 24:
        return f"{int(hours)} hours ago"
    return f"{int(hours // 24)} days ago"


def level_hint_from_vi(level_text):
    t = (level_text or "").lower()
    if any(k in t for k in ("thực tập", "sinh viên", "intern")):
        return "Intern"
    if any(k in t for k in ("mới tốt nghiệp", "fresher", "fresh")):
        return "Fresher"
    if any(k in t for k in ("trưởng", "giám đốc", "quản lý", "cấp cao", "manager", "director", "senior")):
        return "__senior__"
    return None


def jd_from_years(years, strict=False, snippet=""):
    """Experience given by the site itself (structured field)."""
    if years is None:
        return {"read": True, "site": True}
    return {"read": True, "site": True, "min_years": float(years), "strict": strict, "optional": False,
            "snippet": snippet}


# ---------------------------------------------------------------- VietnamWorks
def search_vietnamworks(config, max_days=7):
    platform = get_platform(config, "Vietnamworks")
    city_id = str(platform.get("api_city_id", 29))           # 29 = Ho Chi Minh
    it_group = str(platform.get("api_it_group_id", 5))       # 5 = Công Nghệ Thông Tin/Viễn Thông
    print("📡 Scanning VietnamWorks API (IT, Ho Chi Minh)...")
    jobs, cutoff = [], datetime.now(timezone.utc) - timedelta(days=max_days)
    for page in range(int(platform.get("max_pages", 6))):
        payload = {"userId": 0, "query": "", "ranges": [], "hitsPerPage": 50, "page": page,
                   "filter": [{"field": "workingLocations.cityId", "value": city_id},
                              {"field": "groupJobFunctionsV3.groupJobFunctionV3Id", "value": it_group}],
                   "order": [{"field": "approvedOn", "value": "desc"}]}
        status, text = http_get("https://ms.vietnamworks.com/job-search/v1.0/search", data=payload)
        if status != 200:
            print(f"  [Error] VietnamWorks page {page}: HTTP {status}")
            break
        hits = json.loads(text).get("data", [])
        too_old = False
        for h in hits:
            try:
                approved = datetime.fromisoformat(h["approvedOn"])
            except (KeyError, ValueError):
                continue
            if approved < cutoff:
                too_old = True
                continue
            years = h.get("yearsOfExperience")
            if isinstance(years, int) and years >= 0:
                jd = jd_from_years(years, snippet=f"VietnamWorks: kinh nghiệm {years} năm")
            else:
                exp = extract_experience(html_to_text(h.get("jobRequirement", "")))
                jd = {"read": True, "site": True, **(exp or {})}
            jobs.append({
                "source": "VietnamWorks",
                "title": clean_text(h.get("jobTitle", "")),
                "company": clean_text(h.get("companyName", "")) or "N/A",
                "location": "Ho Chi Minh City",
                "time": ago_text(approved),
                "link": h.get("jobUrl") or f"https://www.vietnamworks.com/{h.get('alias', '')}-{h.get('jobId')}-jv",
                "id": f"vnw-{h.get('jobId')}",
                "level_hint": level_hint_from_vi(h.get("jobLevelVI")),
                "jd": jd,
            })
        if too_old or len(hits) < 50:
            break
        time.sleep(1)
    return jobs


# ---------------------------------------------------------------- TopDev
def _topdev_years(exp_str):
    s = (exp_str or "").lower()
    if not s or "không yêu cầu" in s or "dưới 1" in s:
        return 0, False
    nums = [int(n) for n in re.findall(r"\d+", s)]
    if not nums:
        return None, False
    return min(nums), ("trên" in s or "hơn" in s)


def search_topdev(config, max_days=7):
    platform = get_platform(config, "TopDev")
    keywords = platform.get("search_queries") or ["java", "backend", "developer"]
    region = str(platform.get("api_region_id", 79))           # 79 = Thành phố Hồ Chí Minh
    print("📡 Scanning TopDev API...")
    jobs, cutoff = [], datetime.now(ICT) - timedelta(days=max_days)
    for i, kw in enumerate(keywords):
        if i:
            time.sleep(1)
        params = {"fields[job]": "id,title,company,job_levels_str,experiences_str,detail_url,published",
                  "fields[company]": "display_name", "keyword": kw, "region_ids": region,
                  "page": 1, "page_size": 50, "locale": "vi_VN", "ordering": "newest_job"}
        status, text = http_get("https://api.topdev.vn/td/v2/jobs?" + urllib.parse.urlencode(params))
        if status != 200:
            print(f"  [Error] TopDev '{kw}': HTTP {status}")
            continue
        for j in json.loads(text).get("data", []):
            try:
                published = datetime.strptime(j["published"]["date"], "%d-%m-%Y").replace(tzinfo=ICT)
            except (KeyError, TypeError, ValueError):
                continue
            if published < cutoff:
                continue
            years, strict = _topdev_years(j.get("experiences_str"))
            jobs.append({
                "source": "TopDev",
                "title": clean_text(j.get("title", "")),
                "company": clean_text((j.get("company") or {}).get("display_name", "")) or "N/A",
                "location": "Ho Chi Minh City",
                "time": ago_text(published),
                "link": j.get("detail_url", ""),
                "id": f"topdev-{j.get('id')}",
                "level_hint": level_hint_from_vi(j.get("job_levels_str")),
                "jd": jd_from_years(years, strict, f"TopDev: kinh nghiệm {j.get('experiences_str', '')}"),
            })
    return jobs


# ---------------------------------------------------------------- CareerLink
def search_careerlink(config, max_days=7):
    platform = get_platform(config, "CareerLink")
    keywords = platform.get("search_queries") or ["java", "lập trình viên"]
    print("📡 Scanning CareerLink (Ho Chi Minh)...")
    jobs, cutoff = [], datetime.now(timezone.utc) - timedelta(days=max_days)
    for i, kw in enumerate(keywords):
        if i:
            time.sleep(3)
        url = "https://www.careerlink.vn/tim-viec-lam-tai/ho-chi-minh/HCM?" + urllib.parse.urlencode({"keyword": kw})
        status, page = http_get(url)
        if status != 200:
            print(f"  [Error] CareerLink '{kw}': HTTP {status}")
            continue
        rows = page.split('data-testid="job-result-row"')[1:]
        if not rows and 'data-testid="job-results"' not in page:
            print("  [CareerLink] empty page (throttled?) → stop for this run")
            break
        for row in rows:
            link = re.search(r'title="([^"]*)" href="(/tim-viec-lam/[^"]+/(\d+))"', row)
            when = re.search(r'<time dateTime="([^"]+)"', row)
            if not (link and when):
                continue
            posted = datetime.fromisoformat(when.group(1).replace("Z", "+00:00"))
            if posted < cutoff:
                continue
            company = re.search(r'__company"[^>]*title="([^"]*)"', row)
            jobs.append({
                "source": "CareerLink",
                "title": clean_text(link.group(1)),
                "company": clean_text(company.group(1)) if company else "N/A",
                "location": "Ho Chi Minh City",
                "time": ago_text(posted),
                "link": "https://www.careerlink.vn" + link.group(2),
                "id": f"careerlink-{link.group(3)}",
            })
    return jobs
