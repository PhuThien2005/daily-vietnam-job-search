#!/usr/bin/env python3
"""LinkedIn Guest API scraper. Queries, levels and roles come from search-config.json.

Writes reports/<date>/linkedin-scan.md and caches the raw results in .cache/linkedin.json
so search_vietnam_jobs.py can reuse them instead of hitting LinkedIn a second time.
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

from job_filters import (PROJECT_DIR, clean_text, filter_jobs, get_linkedin_queries,
                         load_config, load_profile, md_cell)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "*/*",
}
CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache", "linkedin.json")
REQUEST_DELAY_SECONDS = 1.5


def search_linkedin_jobs(keywords, entry_filter=False, location="Ho Chi Minh City", time_range="r604800"):
    # f_TPR=r604800: past week. f_E=1,2: Internship + Entry level.
    params = {"keywords": keywords, "location": location, "f_TPR": time_range, "start": 0}
    if entry_filter:
        params["f_E"] = "1,2"
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?{urllib.parse.urlencode(params)}"
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as response:
                return response.read().decode("utf-8")
        except Exception as e:
            if attempt == 0:
                print(f"  [Retry] '{keywords}': {e}")
                time.sleep(8)  # back off on 429 / connection resets
            else:
                print(f"  [Error] Failed to fetch LinkedIn jobs for '{keywords}': {e}")
    return None


def parse_jobs(html, entry_hint=False):
    if not html:
        return []
    jobs = []
    for item in html.split("<li")[1:]:
        title_match = re.search(r'class="base-search-card__title"[^>]*>\s*(.*?)\s*</h3>', item, re.DOTALL)
        company_match = (re.search(r'class="base-search-card__subtitle"[^>]*>\s*<a[^>]*>\s*(.*?)\s*</a>', item, re.DOTALL)
                         or re.search(r'class="base-search-card__subtitle"[^>]*>\s*(.*?)\s*</h4>', item, re.DOTALL))
        location_match = re.search(r'class="job-search-card__location"[^>]*>\s*(.*?)\s*</span>', item, re.DOTALL)
        time_match = re.search(r'class="job-search-card__listdate(?:--new)?"[^>]*>\s*(.*?)\s*</time>', item, re.DOTALL)
        link_match = re.search(r'href="(https://[^"]+/jobs/view/[^"?]+)', item)
        if not (title_match and link_match):
            continue
        job_id_match = re.search(r"(\d+)/?$", link_match.group(1))
        if not job_id_match:
            continue
        job_id = job_id_match.group(1)
        jobs.append({
            "source": "LinkedIn",
            "title": clean_text(title_match.group(1)),
            "company": clean_text(company_match.group(1)) if company_match else "N/A",
            "location": clean_text(location_match.group(1)) if location_match else "N/A",
            "time": clean_text(time_match.group(1)) if time_match else "N/A",
            "link": f"https://www.linkedin.com/jobs/view/{job_id}/",
            "id": job_id,
            "entry_hint": entry_hint,
        })
    return jobs


def fetch_all(config):
    """Run every configured query; merge duplicates (entry_hint is kept if any query had it)."""
    by_id = {}
    for i, (q, entry_filter) in enumerate(get_linkedin_queries(config)):
        if i:
            time.sleep(REQUEST_DELAY_SECONDS)
        label = f"{q} [Intern+Entry level]" if entry_filter else q
        print(f"📡 Querying: '{label}'...")
        jobs = parse_jobs(search_linkedin_jobs(q, entry_filter), entry_hint=entry_filter)
        print(f"  [Found] {len(jobs)} jobs")
        for job in jobs:
            if job["id"] in by_id:
                by_id[job["id"]]["entry_hint"] |= job["entry_hint"]
            else:
                by_id[job["id"]] = job
    return list(by_id.values())


def write_cache(jobs):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump({"fetched_at": time.time(), "jobs": jobs}, f, ensure_ascii=False)


def main():
    print("🚀 Running LinkedIn Guest API Job Searcher...")
    config = load_config()
    profile = load_profile(config)

    raw_jobs = fetch_all(config)
    write_cache(raw_jobs)
    filtered_jobs = filter_jobs(raw_jobs, profile)
    print(f"✨ {len(raw_jobs)} unique → {len(filtered_jobs)} relevant positions (newest first).\n")

    date_str = datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d")
    report_dir = os.path.join(PROJECT_DIR, "reports", date_str)
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, "linkedin-scan.md")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# 🔍 LinkedIn Auto-Scan Report - {date_str}\n\n")
        f.write("## 📊 Summary\n")
        f.write(f"- **Total unique relevant jobs found**: {len(filtered_jobs)}\n")
        f.write("- 🎯 *Phạm vi: Intern / Fresher / Junior / Entry level — Java, Backend, Fullstack, .NET, AI, QA Automation, Software Engineer*\n")
        f.write("- 📅 *Sắp xếp: job ghi rõ Intern/Fresher/Junior/Entry lên trước, sau đó là job chưa rõ level; trong mỗi nhóm mới nhất → cũ nhất*\n\n")
        f.write("## 📋 Job Listings\n")
        f.write("| # | Job Title | Company | Level | Nhóm role | Location | Posted Date | Direct LinkedIn Link |\n")
        f.write("|---|-----------|---------|-------|-----------|----------|-------------|----------------------|\n")
        for idx, job in enumerate(filtered_jobs, 1):
            f.write(f"| {idx} | **{md_cell(job['title'])}** | {md_cell(job['company'])} | {job['level']} | {job['role']} "
                    f"| {md_cell(job['location'])} | {job['time']} | [Link]({job['link']}) |\n")

    print(f"💾 Report saved successfully to: {report_path}\n")
    for idx, job in enumerate(filtered_jobs, 1):
        print(f"{idx}. [{job['level']} · {job['role']}] {job['title']} at {job['company']} — {job['time']}")


if __name__ == "__main__":
    main()
