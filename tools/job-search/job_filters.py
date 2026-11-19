#!/usr/bin/env python3
"""Shared config loading, level/role classification and filtering for the job scrapers.

All keyword lists live in search-config.json under "search_profile", so widening or
narrowing the search only needs a config edit.
"""
import html
import json
import os
import re

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "search-config.json")
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Fallbacks used only when the config has no "search_profile" block.
DEFAULT_PROFILE = {
    "max_days_old": 7,
    "levels": {
        "Intern": ["intern", "thực tập", "trainee", "student"],
        "Fresher": ["fresher", "graduate", "entry level", "entry-level"],
        "Junior": ["junior", "jr."],
    },
    "exclude_levels": ["senior", "sr.", "lead", "principal", "manager", "director", "head of", "expert", "architect"],
    "soft_exclude_levels": ["middle", "mid-level", "intermediate"],
    "role_groups": {
        "Java/Spring": ["java", "spring"],
        "Backend": ["backend", "back-end", "back end"],
        "Software Engineer": ["software", "developer", "engineer", "lập trình"],
    },
    "exclude_roles": [],
}


def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_profile(config=None):
    config = config if config is not None else load_config()
    profile = dict(DEFAULT_PROFILE)
    profile.update(config.get("search_profile", {}))
    return profile


def get_platform(config, name):
    for platform in config.get("search_sources", {}).get("job_platforms", []):
        if platform.get("name") == name:
            return platform
    return {}


def get_linkedin_queries(config):
    """Return [(keywords, entry_filter_bool)] from config. Plain strings mean no entry filter."""
    queries = []
    for q in get_platform(config, "LinkedIn").get("search_queries", []):
        if isinstance(q, str):
            queries.append((q, False))
        elif isinstance(q, dict) and q.get("keywords"):
            queries.append((q["keywords"], bool(q.get("entry_filter"))))
    return queries or [("Java intern", False), ("Backend intern", False), ("Software engineer intern", False)]


def clean_text(s):
    s = re.sub(r"<[^>]*>", "", s or "")
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


LEVEL_ORDER = {"Intern": 0, "Fresher": 1, "Junior": 2, "Entry (LinkedIn)": 3}
_PATTERN_CACHE = {}


def _kw_pattern(kw):
    """Whole-word match at word-character edges: 'intern' won't hit 'International',
    'java' won't hit 'JavaScript', but '.net' still hits 'ASP.NET'."""
    if kw not in _PATTERN_CACHE:
        k = kw.lower().strip()
        start = r"(?<!\w)" if re.match(r"\w", k) else ""
        end = r"(?!\w)" if re.search(r"\w$", k) else ""
        _PATTERN_CACHE[kw] = re.compile(start + re.escape(k) + end)
    return _PATTERN_CACHE[kw]


def _has(text, keywords):
    return any(_kw_pattern(kw).search(text) for kw in keywords)


def detect_level(title, profile):
    t = title.lower()
    for level, keywords in profile["levels"].items():
        if _has(t, keywords):
            return level
    return None


def detect_role(title, profile):
    t = title.lower()
    for group, keywords in profile["role_groups"].items():
        if _has(t, keywords):
            return group
    return None


def classify(job, profile):
    """Return (keep, level_label, role_label) for a job dict with 'title' and optional 'entry_hint'."""
    t = job["title"].lower()
    level = detect_level(job["title"], profile)
    hint = job.get("level_hint")  # level stated by the site itself (VietnamWorks, TopDev)
    if hint == "__senior__" and not level:
        return False, None, None
    if not level and hint in LEVEL_ORDER:
        level = hint

    if _has(t, profile["exclude_levels"]):
        # "Junior/Senior" style titles stay; pure senior/lead roles go.
        if not level:
            return False, None, None
        if _has(t, ["lead", "principal", "manager", "director", "head of", "architect"]):
            return False, None, None
    if not level and _has(t, profile["soft_exclude_levels"]):
        return False, None, None
    years = re.search(r"(\d+)\s*\+?\s*(?:yoe|years?|yrs|năm)", t)
    if years and int(years.group(1)) > profile.get("max_years_experience", 2):
        return False, None, None
    if _has(t, profile.get("exclude_roles", [])):
        return False, None, None

    role = detect_role(job["title"], profile)
    if not role and job.get("source") == "Ybox":
        # Ybox titles are Vietnamese posts; treat generic IT posts as relevant.
        if re.search(r"\b(it|cntt)\b", t) or _has(t, ["công nghệ thông tin", "lập trình"]):
            role = "IT (chung)"
    if not role:
        return False, None, None

    if not level:
        level = "Entry (LinkedIn)" if job.get("entry_hint") else "Chưa rõ — xem JD"
    return True, level, role


def parse_time_to_hours(time_str):
    """Parse relative time strings ('20 hours ago', '3 days ago', 'Just now') into hours. Lower = newer."""
    time_str = (time_str or "").strip().lower()
    if time_str in ("just now", "recent", "n/a", ""):
        return 0
    match = re.match(r"(\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago", time_str)
    if match:
        value = int(match.group(1))
        multipliers = {"second": 1 / 3600, "minute": 1 / 60, "hour": 1, "day": 24,
                       "week": 24 * 7, "month": 24 * 30, "year": 24 * 365}
        return value * multipliers[match.group(2)]
    return 99999




def filter_jobs(jobs, profile):
    """Dedupe by id, drop jobs older than max_days_old, classify and sort."""
    max_hours = profile.get("max_days_old", 7) * 24
    seen, kept = set(), []
    for job in jobs:
        if job["id"] in seen:
            continue
        if parse_time_to_hours(job["time"]) > max_hours:
            continue
        keep, level, role = classify(job, profile)
        if not keep:
            continue
        seen.add(job["id"])
        kept.append({**job, "level": level, "role": role})
    # Jobs with an explicit entry-level marker first, then "level unknown"; each block newest first.
    kept.sort(key=lambda j: (j["level"] not in LEVEL_ORDER, parse_time_to_hours(j["time"])))
    return kept


def apply_experience_filter(jobs, profile):
    """Split jobs by the experience their description *requires* (job["jd"] set by jd_reader).
    Nice-to-have mentions and unread JDs never remove a job. Returns (kept, removed)."""
    limit = profile.get("max_years_experience", 2)
    kept, removed = [], []
    for job in jobs:
        jd = job.get("jd") or {}
        y = jd.get("min_years")
        if y is not None and not jd.get("optional") and (y > limit or (jd.get("strict") and y >= limit)):
            removed.append(job)
        else:
            kept.append(job)
    return kept, removed


def md_cell(s):
    return str(s).replace("|", "/")
