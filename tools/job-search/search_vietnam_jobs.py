#!/usr/bin/env python3
import urllib.request
import urllib.parse
import json
import re
import os
import sys
from datetime import datetime, timezone, timedelta

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

def search_linkedin(queries):
    jobs = []
    print("📡 Scanning LinkedIn Guest API...")
    for q in queries:
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={urllib.parse.quote(q)}&location=Ho%20Chi%20Minh%20City&f_TPR=r864000"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as resp:
                html = resp.read().decode('utf-8')
                items = html.split('<li')
                for item in items[1:]:
                    title_match = re.search(r'class="base-search-card__title"[^>]*>\s*(.*?)\s*</', item, re.DOTALL)
                    title = title_match.group(1).strip() if title_match else "N/A"
                    title = re.sub(r'<[^>]*>', '', title)
                    title = re.sub(r'\s+', ' ', title)
                    
                    company_match = re.search(r'class="base-search-card__subtitle"[^>]*>\s*(.*?)\s*</', item, re.DOTALL)
                    if not company_match:
                        company_match = re.search(r'data-tracking-control-name="public_jobs_jserp-result_job-search-card-subtitle"[^>]*>\s*(.*?)\s*</', item, re.DOTALL)
                    company = company_match.group(1).strip() if company_match else "N/A"
                    company = re.sub(r'<[^>]*>', '', company)
                    company = re.sub(r'\s+', ' ', company)
                    
                    location_match = re.search(r'class="job-search-card__location"[^>]*>\s*(.*?)\s*</', item, re.DOTALL)
                    location = location_match.group(1).strip() if location_match else "N/A"
                    location = re.sub(r'<[^>]*>', '', location)
                    location = re.sub(r'\s+', ' ', location)
                    
                    time_match = re.search(r'class="job-search-card__listdate"[^>]*>\s*(.*?)\s*</', item, re.DOTALL)
                    if not time_match:
                        time_match = re.search(r'class="job-search-card__listdate--new"[^>]*>\s*(.*?)\s*</', item, re.DOTALL)
                    time_str = time_match.group(1).strip() if time_match else "N/A"
                    
                    link_match = re.search(r'href="(https://[^"]+/jobs/view/[^"?]+)', item)
                    link = link_match.group(1) if link_match else "N/A"
                    
                    job_id_match = re.search(r'(\d+)/?$', link)
                    job_id = job_id_match.group(1) if job_id_match else "N/A"
                    
                    if title != "N/A" and link != "N/A" and job_id != "N/A":
                        clean_link = f"https://www.linkedin.com/jobs/view/{job_id}/"
                        jobs.append({
                            "source": "LinkedIn",
                            "title": title,
                            "company": company,
                            "location": location,
                            "time": time_str,
                            "link": clean_link,
                            "id": job_id
                        })
        except Exception as e:
            continue
    return jobs

def search_ybox():
    jobs = []
    print("📡 Scanning Ybox newest posts template...")
    url = "https://ybox.vn/tuyen-dung"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp:
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

def search_itviec():
    jobs = []
    print("📡 Scanning ITviec...")
    queries = ["java-intern-ho-chi-minh", "software-engineer-intern-ho-chi-minh"]
    for q in queries:
        url = f"https://itviec.com/it-jobs/{q}"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as resp:
                html = resp.read().decode('utf-8')
                cards = html.split("class='job-card ")
                for card in cards[1:]:
                    slug_match = re.search(r"data-search--job-selection-job-slug-value='([^']+)'", card)
                    if not slug_match:
                        continue
                    slug = slug_match.group(1)
                    
                    title_match = re.search(r"<h3[^>]*>\s*(.*?)\s*</h3>", card, re.DOTALL)
                    title = title_match.group(1).strip() if title_match else "N/A"
                    title = re.sub(r'<[^>]*>', '', title)
                    title = re.sub(r'\s+', ' ', title)
                    
                    company_match = re.search(r'class="text-rich-grey"[^>]*>\s*(.*?)\s*</a>', card, re.DOTALL)
                    company = company_match.group(1).strip() if company_match else "N/A"
                    company = re.sub(r'<[^>]*>', '', company)
                    company = re.sub(r'\s+', ' ', company)
                    
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
            continue
    return jobs

def filter_jobs(jobs):
    filtered = []
    exclude_keywords = ["senior", "lead", "principal", "manager", "director", "head of", "expert", "test lead", "qa lead"]
    include_keywords = ["intern", "fresher", "junior", "trainee", "student", "thực tập", "học việc", "developer", "engineer", "backend", "java", "software", "angular"]
    
    seen_ids = set()
    
    for job in jobs:
        if job["id"] in seen_ids:
            continue
            
        title_lower = job["title"].lower()
        
        # Check exclusion
        is_excluded = any(ex in title_lower for ex in exclude_keywords)
        # Check inclusion
        is_included = any(inc in title_lower for inc in include_keywords)
        
        # Ybox title special check
        if job["source"] == "Ybox":
            has_it_word = any(re.search(rf'\b{w}\b', title_lower) for w in ["it", "cntt"])
            has_other_keywords = any(k in title_lower for k in ["lập trình", "java", "backend", "software", "công nghệ thông tin", "developer", "engineer"])
            if not (has_it_word or has_other_keywords):
                continue
                
        if is_included and not is_excluded:
            filtered.append(job)
            seen_ids.add(job["id"])
            
    return filtered

def main():
    print("🚀 Running Vietnam Job Search Aggregator...")
    
    # Target queries
    linkedin_queries = ["Java intern", "Backend intern", "Software engineer intern"]
    
    # Scrape all
    all_jobs = []
    
    linkedin_results = search_linkedin(linkedin_queries)
    print(f"  [Found] {len(linkedin_results)} LinkedIn jobs.")
    all_jobs.extend(linkedin_results)
    
    ybox_results = search_ybox()
    print(f"  [Found] {len(ybox_results)} Ybox posts.")
    all_jobs.extend(ybox_results)
    
    itviec_results = search_itviec()
    print(f"  [Found] {len(itviec_results)} ITviec jobs.")
    all_jobs.extend(itviec_results)
    
    # Deduplicate & Filter
    filtered = filter_jobs(all_jobs)
    print(f"✨ Deduplicated & filtered to {len(filtered)} positions.")
    
    # Save Report
    today_str = datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d")
    report_dir = os.path.join("reports", today_str)
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, "vietnam-jobs-scan.md")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Báo cáo tuyển dụng Java/Backend/Software Intern ({today_str})\n\n")
        f.write(f"Tìm thấy **{len(filtered)}** vị trí thực tập/fresher phù hợp.\n\n")
        f.write("| # | Nguồn | Công ty | Vị trí tuyển dụng | Ngày đăng | Link chi tiết |\n")
        f.write("|---|-------|---------|--------------------|-----------|---------------|\n")
        for idx, job in enumerate(filtered, 1):
            f.write(f"| {idx} | {job['source']} | **{job['company']}** | {job['title']} | {job['time']} | [{job['source']} Direct Link]({job['link']}) |\n")
            
    print(f"\n💾 Report successfully saved to: {report_path}\n")
    
    # Print console preview
    for idx, job in enumerate(filtered[:20], 1):
        print(f"{idx}. [{job['source']}] {job['title']} at {job['company']}")
        print(f"   Location: {job['location']} | Posted: {job['time']}")
        print(f"   Link: {job['link']}\n")

if __name__ == "__main__":
    main()
