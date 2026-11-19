#!/usr/bin/env python3
import urllib.request
import urllib.parse
import json
import re
import os
import time
from datetime import datetime, timezone, timedelta

from jd_reader import enrich_linkedin, experience_label
from job_filters import (PROJECT_DIR, apply_experience_filter, clean_text, filter_jobs, get_platform, load_config,
                         load_profile, md_cell)
from search_linkedin import CACHE_PATH, fetch_all

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5"
}

def extract_json_by_braces(s):
    start = s.find('{')
    if start == -1:
        return None
    
    count = 0
    in_string = False
    escape = False
    
    for i in range(start, len(s)):
        char = s[i]
        if escape:
            escape = False
            continue
        if char == '\\':
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if not in_string:
            if char == '{':
                count += 1
            elif char == '}':
                count -= 1
                if count == 0:
                    return s[start:i+1]
    return None

def search_linkedin(config, max_cache_age_seconds=1800):
    """Reuse search_linkedin.py's fresh cache when available; otherwise query LinkedIn directly."""
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            cache = json.load(f)
        if time.time() - cache.get("fetched_at", 0) <= max_cache_age_seconds:
            print("📡 LinkedIn: reusing cached results from search_linkedin.py")
            return cache["jobs"]
    except (OSError, ValueError, KeyError):
        pass
    print("📡 Scanning LinkedIn Guest API...")
    return fetch_all(config)

def search_ybox():
    jobs = []
    print("📡 Scanning Ybox newest posts template...")
    url = "https://ybox.vn/tuyen-dung"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resp:
            html = resp.read().decode('utf-8')
            state_start = html.find('window.__INITIAL_STATE__')
            if state_start != -1:
                json_str = extract_json_by_braces(html[state_start:])
                if json_str:
                    state = json.loads(json_str)
                    
                    # Extract newest posts and highlight posts
                    newest = state.get("app", {}).get("initialPosts", {}).get("NewestPosts", {}).get("edges", [])
                    highlights = state.get("app", {}).get("initialPosts", {}).get("HighlightPosts", {}).get("edges", [])
                    selective = state.get("app", {}).get("initialPosts", {}).get("SelectivePosts", {}).get("edges", [])
                    
                    all_edges = newest + highlights + selective
                    seen_ids = set()
                    
                    for post in all_edges:
                        post_id = post.get("_id")
                        if not post_id or post_id in seen_ids:
                            continue
                        seen_ids.add(post_id)
                        
                        title = post.get("title", "N/A")
                        published_at = post.get("publishedAt", "N/A")
                        
                        # Calculate human readable time diff
                        time_str = "Recent"
                        if published_at != "N/A":
                            try:
                                dt = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
                                diff = datetime.now(timezone.utc) - dt
                                if diff.days > 0:
                                    time_str = f"{diff.days} days ago"
                                else:
                                    hours = diff.seconds // 3600
                                    time_str = f"{hours} hours ago" if hours > 0 else "Just now"
                            except Exception:
                                time_str = published_at[:10]
                                
                        # Extract company name from title e.g. [HCM] Công Ty ABC Tuyển Dụng...
                        company = "N/A"
                        comp_match = re.search(r'\]\s*([^T]+?)\s*Tuyển Dụng', title)
                        if comp_match:
                            company = comp_match.group(1).strip()
                        else:
                            comp_match_2 = re.search(r'Công Ty\s+([^ ]+)', title)
                            if comp_match_2:
                                company = f"Công Ty {comp_match_2.group(1)}"
                        
                        # Clean link format
                        clean_link = f"https://ybox.vn/tuyen-dung/job-{post_id}"
                        
                        jobs.append({
                            "source": "Ybox",
                            "title": title,
                            "company": company,
                            "location": "Ho Chi Minh City / Hanoi",
                            "time": time_str,
                            "link": clean_link,
                            "id": post_id
                        })
    except Exception as e:
        print(f"  [Error] Ybox search failed: {e}")
    return jobs

def search_itviec(config):
    jobs = []
    print("📡 Scanning ITviec...")
    platform = get_platform(config, "ITviec")
    suffix = platform.get("scraper_slug_suffix", "-ho-chi-minh")
    queries = platform.get("search_queries") or ["java-intern", "software-engineer-intern"]
    for i, q in enumerate(queries):
        if i:
            time.sleep(1)
        url = f"https://itviec.com/it-jobs/{q}{suffix}"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                html = resp.read().decode('utf-8')
                cards = html.split("class='job-card ")
                for card in cards[1:]:
                    slug_match = re.search(r"data-search--job-selection-job-slug-value='([^']+)'", card)
                    if not slug_match:
                        continue
                    slug = slug_match.group(1)
                    
                    title_match = re.search(r"<h3[^>]*>\s*(.*?)\s*</h3>", card, re.DOTALL)
                    title = title_match.group(1).strip() if title_match else "N/A"
                    title = clean_text(title)
                    
                    company_match = re.search(r'class="text-rich-grey"[^>]*>\s*(.*?)\s*</a>', card, re.DOTALL)
                    company = company_match.group(1).strip() if company_match else "N/A"
                    company = clean_text(company)
                    
                    time_match = re.search(r"Posted\s*(.*?)\s*</span>", card, re.DOTALL)
                    time_str = time_match.group(1).strip() if time_match else "Recent"
                    time_str = re.sub(r'<[^>]*>', '', time_str)
                    time_str = re.sub(r'\s+', ' ', time_str)
                    
                    clean_link = f"https://itviec.com/it-jobs/{slug}"
                    
                    jobs.append({
                        "source": "ITviec",
                        "title": title,
                        "company": company,
                        "location": "Ho Chi Minh City",
                        "time": time_str,
                        "link": clean_link,
                        "id": slug
                    })
        except Exception as e:
            print(f"  [Error] ITviec '{q}' failed: {e}")
            continue
    return jobs

def main():
    print("🚀 Running Vietnam Job Search Aggregator...")
    config = load_config()
    profile = load_profile(config)

    all_jobs = []
    for name, results in (("LinkedIn", search_linkedin(config)), ("Ybox", search_ybox()), ("ITviec", search_itviec(config))):
        print(f"  [Found] {len(results)} {name} jobs.")
        all_jobs.extend(results)

    filtered = filter_jobs(all_jobs, profile)
    enrich_linkedin(filtered)  # served from jd-cache.json written by search_linkedin.py
    filtered, removed = apply_experience_filter(filtered, profile)
    limit = profile.get("max_years_experience", 2)
    print(f"✨ Deduplicated & filtered to {len(filtered)} positions ({len(removed)} removed: JD > {limit:g} years).")

    today_str = datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d")
    report_dir = os.path.join(PROJECT_DIR, "reports", today_str)
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, "vietnam-jobs-scan.md")

    by_level = {}
    for job in filtered:
        by_level[job["level"]] = by_level.get(job["level"], 0) + 1
    level_summary = ", ".join(f"{k}: {v}" for k, v in sorted(by_level.items(), key=lambda kv: -kv[1]))

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Báo cáo tuyển dụng IT — Intern / Fresher / Junior ({today_str})\n\n")
        f.write(f"Tìm thấy **{len(filtered)}** vị trí phù hợp ({level_summary or 'không có'}).\n\n")
        f.write(f"🧹 *Đã đọc description LinkedIn và loại {len(removed)} job yêu cầu trên {limit:g} năm kinh nghiệm "
                "(chi tiết ở `linkedin-scan.md`).*\n\n")
        f.write("🎯 *Role: Java/Spring, Backend, Fullstack, .NET/C#, AI/LLM Application, QA/Test Automation, Software Engineer — "
                "cấu hình tại `tools/job-search/search-config.json` → `search_profile`*\n\n")
        f.write("📅 *Sắp xếp: job ghi rõ Intern/Fresher/Junior/Entry lên trước, sau đó là job chưa rõ level; trong mỗi nhóm mới nhất → cũ nhất*\n\n")
        f.write("| # | Nguồn | Công ty | Vị trí tuyển dụng | Level | Nhóm role | Kinh nghiệm (JD) | Ngày đăng | Link chi tiết |\n")
        f.write("|---|-------|---------|--------------------|-------|-----------|------------------|-----------|---------------|\n")
        for idx, job in enumerate(filtered, 1):
            f.write(f"| {idx} | {job['source']} | **{md_cell(job['company'])}** | {md_cell(job['title'])} | {job['level']} "
                    f"| {job['role']} | {experience_label(job.get('jd')) if job['source'] == 'LinkedIn' else '—'} "
                    f"| {job['time']} | [{job['source']} Direct Link]({job['link']}) |\n")

    print(f"\n💾 Report successfully saved to: {report_path}\n")
    for idx, job in enumerate(filtered[:30], 1):
        print(f"{idx}. [{job['source']} · {job['level']} · {job['role']}] {job['title']} at {job['company']} — {job['time']}")


if __name__ == "__main__":
    main()
