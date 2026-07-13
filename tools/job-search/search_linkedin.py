#!/usr/bin/env python3
import urllib.request
import urllib.parse
import re
import json
import os
from datetime import datetime, timezone, timedelta

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "search-config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def search_linkedin_jobs(keywords, location="Ho Chi Minh City", time_range="r604800"):
    # f_TPR=r86400 is past 24h, f_TPR=r604800 is past week
    params = {
        "keywords": keywords,
        "location": location,
        "f_TPR": time_range,
        "start": 0
    }
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?{urllib.parse.urlencode(params)}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "*/*"
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"  [Error] Failed to fetch LinkedIn jobs for '{keywords}': {e}")
        return None

def parse_jobs(html):
    if not html:
        return []
    
    items = html.split('<li')
    jobs = []
    
    for item in items[1:]:
        try:
            # Title
            title_match = re.search(r'class="base-search-card__title"[^>]*>\s*(.*?)\s*</h3>', item, re.DOTALL)
            title = title_match.group(1).strip() if title_match else "N/A"
            
            # Company
            company_match = re.search(r'class="base-search-card__subtitle"[^>]*>\s*<a[^>]*>\s*(.*?)\s*</a>', item, re.DOTALL)
            if not company_match:
                company_match = re.search(r'class="base-search-card__subtitle"[^>]*>\s*(.*?)\s*</h4>', item, re.DOTALL)
            company = company_match.group(1).strip() if company_match else "N/A"
            
            # Location
            location_match = re.search(r'class="job-search-card__location"[^>]*>\s*(.*?)\s*</span>', item, re.DOTALL)
            location = location_match.group(1).strip() if location_match else "N/A"
            
            # Time
            time_match = re.search(r'class="job-search-card__listdate(?:--new)?"[^>]*>\s*(.*?)\s*</time>', item, re.DOTALL)
            time_str = time_match.group(1).strip() if time_match else "N/A"
            
            # Link
            link_match = re.search(r'href="(https://[^"]+/jobs/view/[^"?]+)', item)
            link = link_match.group(1) if link_match else "N/A"
            
            # Extract job ID (the digits at the end of the URL path)
            job_id_match = re.search(r'(\d+)/?$', link)
            job_id = job_id_match.group(1) if job_id_match else "N/A"
            
            if title != "N/A" and link != "N/A":
                clean_link = f"https://www.linkedin.com/jobs/view/{job_id}/" if job_id != "N/A" else link
                jobs.append({
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

def filter_jobs(jobs):
    filtered = []
    # Filter only relevant roles (Intern, Fresher, Junior, Trainee, Software, Developer, Java, Backend)
    # Exclude Senior, Lead, Principal, Manager, HR, Director
    exclude_keywords = ["senior", "lead", "principal", "manager", "director", "head of", "expert", "test lead", "qa lead"]
    include_keywords = ["intern", "fresher", "junior", "trainee", "student", "thực tập", "học việc", "developer", "engineer", "backend", "java", "software"]
    
    for job in jobs:
        title_lower = job["title"].lower()
        
        # Check exclusion
        is_excluded = any(ex in title_lower for ex in exclude_keywords)
        if is_excluded:
            continue
            
        # Check inclusion
        is_included = any(inc in title_lower for inc in include_keywords)
        if is_included:
            filtered.append(job)
            
    return filtered

def main():
    print("🚀 Running LinkedIn Guest API Job Searcher...")
    config = load_config()
    
    # Get keywords from config
    queries = []
    if config and "search_sources" in config:
        for platform in config["search_sources"].get("job_platforms", []):
            if platform.get("name") == "LinkedIn":
                queries = platform.get("search_queries", [])
                
    if not queries:
        queries = ["Java Intern", "Backend Intern", "Software Intern", "React Intern"]
        
    print(f"🔎 Target Queries: {queries}")
    
    all_raw_jobs = []
    for q in queries:
        print(f"📡 Querying: '{q}'...")
        html = search_linkedin_jobs(q, time_range="r604800")
        jobs = parse_jobs(html)
        print(f"  [Found] {len(jobs)} jobs")
        all_raw_jobs.extend(jobs)
        
    # Deduplicate by Job ID
    unique_jobs = {}
    for job in all_raw_jobs:
        if job["id"] != "N/A":
            unique_jobs[job["id"]] = job
            
    filtered_jobs = filter_jobs(list(unique_jobs.values()))
    print(f"✨ Deduplicated & filtered to {len(filtered_jobs)} relevant positions.\n")
    
    # Save Report
    ict_tz = timezone(timedelta(hours=7))
    date_str = datetime.now(ict_tz).strftime('%Y-%m-%d')
    report_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "reports", date_str)
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, "linkedin-scan.md")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# 🔍 LinkedIn Auto-Scan Report - {date_str}\n")
        f.write(f"Generated on: {datetime.now(ict_tz).strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## 📊 Summary\n")
        f.write(f"- **Total unique relevant jobs found**: {len(filtered_jobs)}\n\n")
        
        f.write("## 📋 Job Listings\n")
        f.write("| # | Job Title | Company | Location | Posted Date | Direct LinkedIn Link |\n")
        f.write("|---|-----------|---------|----------|-------------|----------------------|\n")
        
        for idx, job in enumerate(filtered_jobs, 1):
            clean_title = job['title'].replace('|', '/')
            clean_company = job['company'].replace('|', '/')
            clean_loc = job['location'].replace('|', '/')
            f.write(f"| {idx} | **{clean_title}** | {clean_company} | {clean_loc} | {job['time']} | [Link]({job['link']}) |\n")
            
    print(f"💾 Report saved successfully to: {report_path}\n")
    
    # Output to stdout for quick review
    for idx, job in enumerate(filtered_jobs, 1):
        print(f"{idx}. {job['title']} at {job['company']}")
        print(f"   Location: {job['location']}")
        print(f"   Posted: {job['time']}")
        print(f"   Link: {job['link']}\n")

if __name__ == "__main__":
    main()
