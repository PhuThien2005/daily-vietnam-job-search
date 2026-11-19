#!/usr/bin/env python3
"""Read job descriptions (LinkedIn Guest API) and extract the minimum years of experience required.

Handles English and Vietnamese, digits and number words:
  "3+ years", "at least three (3) years", "minimum of 3 years", "3-5 yrs", "5 YOE",
  "tối thiểu 3 năm kinh nghiệm", "ít nhất ba năm", "trên 2 năm", "từ 3 năm trở lên", "1-2 năm".
Lines marked as nice-to-have ("preferred", "is a plus", "ưu tiên", "lợi thế") don't count as requirements.

Results are cached per job id in .cache/jd-cache.json so each JD is fetched once (the GitHub
workflow persists this folder with actions/cache).
"""
import html
import json
import os
import re
import time
import urllib.request

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
JD_CACHE_PATH = os.path.join(CACHE_DIR, "jd-cache.json")
CACHE_TTL_DAYS = 21
PARSER_VERSION = 2  # bump when extract_experience changes so cached results are recomputed
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
}

EN_NUMBERS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
              "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "a": 1, "an": 1}
VI_NUMBERS = {"một": 1, "hai": 2, "ba": 3, "bốn": 4, "tư": 4, "năm": 5, "sáu": 6, "bảy": 7,
              "tám": 8, "chín": 9, "mười": 10}

EXPERIENCE_WORDS = re.compile(r"experience|exp\b|yoe|kinh nghiệm|\bkn\b|làm việc|background|track record", re.I)
OPTIONAL_WORDS = re.compile(r"prefer|nice[- ]to[- ]have|\bplus\b|bonus|advantage|desirable|ideally|"
                            r"ưu tiên|lợi thế|điểm cộng|là một lợi thế", re.I)
STRONG_OPTIONAL = re.compile(r"\ba (?:big |huge |strong )?plus\b|nice[- ]to[- ]have|\bbonus\b|advantage|desirable|"
                             r"lợi thế|điểm cộng|\bpreferred\W*$|\(preferred\)|\(ưu tiên\)", re.I)
REQUIRED_HEADER = re.compile(r"require|qualification|must|you have|what we need|who you are|yêu cầu|tiêu chuẩn|"
                             r"responsibilit|mô tả|benefit|quyền lợi|about", re.I)
NOT_REQUIREMENT = re.compile(r"years? old|tuổi|day-?off|ngày phép|per year|mỗi năm|hàng năm|/năm|annual|"
                             r"founded|established|thành lập|over the (?:last|past)|for (?:over|more than) \d+ years,? (?:we|our)|"
                             r"company with|công ty (?:có|với) (?:hơn|trên)", re.I)

NUM = r"(\d+(?:[.,]5)?)"
# English: "3+ years", "3 - 5 years", "3 to 5 yrs", "5 YOE", "three (3) years"
EN_PATTERN = re.compile(NUM + r"\s*(?:\+|plus)?\s*(?:(?:-|–|to|~)\s*" + NUM + r"\s*\+?\s*)?(?:years?|yrs?|yoe)\b", re.I)
EN_CONTEXT_PATTERN = re.compile(EN_PATTERN.pattern + r"\s+(?:of|in|with|working|developing|building|hands-on|professional|"
                                r"programming|development|as|using|on|java|spring|backend)\b", re.I)
# Vietnamese: "3 năm", "1-2 năm", "từ 3 năm trở lên", "3+ năm"
VI_PATTERN = re.compile(NUM + r"\s*\+?\s*(?:(?:-|–|đến|tới|~)\s*" + NUM + r"\s*)?năm\b", re.I)
# Months: "6 months", "6 tháng" → < 1 year
MONTH_PATTERN = re.compile(NUM + r"\s*\+?\s*(?:months?|tháng)\b", re.I)


def _normalize(line):
    s = line.lower()
    # "three (3) years" → "3 years"; "3 (three) years" → "3 years"
    s = re.sub(r"\b([a-z]+)\s*\((\d+)\)", lambda m: m.group(2) if m.group(1) in EN_NUMBERS else m.group(0), s)
    s = re.sub(r"(\d+)\s*\(([a-z]+)\)", r"\1", s)
    # English number words directly before years/yrs: "three years", "two+ years"
    s = re.sub(r"\b(" + "|".join(k for k in EN_NUMBERS if len(k) > 2) + r")\b(?=\s*\+?\s*(?:or more\s+)?(?:years?|yrs?)\b)",
               lambda m: str(EN_NUMBERS[m.group(1)]), s)
    # Vietnamese number words directly before "năm" ("ba năm", "năm năm" = 5 years)
    s = re.sub(r"(?<!\w)(" + "|".join(VI_NUMBERS) + r")(?=\s+năm(?!\w))",
               lambda m: str(VI_NUMBERS[m.group(1)]), s)
    return s


def extract_experience(text):
    """Return dict(min_years, optional, snippet) for the strictest *required* experience mention, or None."""
    best = None
    optional_best = None
    optional_section = False
    for raw in re.split(r"[\n•;]|(?<=[.!?])\s+", text):
        line = raw.strip()
        if not line or len(line) > 400:
            continue
        # Section headers like "Preferred experience:" / "Nice to have" / "Ưu tiên:" vs "Requirements:" / "Yêu cầu:"
        # (a sentence ending in "." such as "Degree preferred but not required." is not a header)
        if len(line) <= 60 and not re.search(r"\d", line) and not line.endswith((".", "!", "?", ";")):
            if OPTIONAL_WORDS.search(line):
                optional_section = True
            elif REQUIRED_HEADER.search(line):
                optional_section = False
        if NOT_REQUIREMENT.search(line):
            continue
        has_exp_word = bool(EXPERIENCE_WORDS.search(line))
        norm = _normalize(line)
        values, first_pos = [], len(norm)
        if has_exp_word:
            patterns = (EN_PATTERN, VI_PATTERN)
        else:
            # Without "experience"/"kinh nghiệm", only trust English "3+ years of/in/with ..." phrasing
            patterns = (EN_CONTEXT_PATTERN,)
        for pattern in patterns:
            for m in pattern.finditer(norm):
                v = float(m.group(1).replace(",", "."))
                if v <= 10:  # bigger numbers are company/team history, not requirements
                    values.append(v)
                    first_pos = min(first_pos, m.start())
        if not values and has_exp_word:
            for m in MONTH_PATTERN.finditer(norm):
                values.append(round(float(m.group(1).replace(",", ".")) / 12, 2))
                first_pos = min(first_pos, m.start())
        if not values:
            continue
        years = min(values)  # a range "3-5 years" → minimum 3
        num = str(int(years)) if years.is_integer() else str(years)
        # "trên 2 năm" / "more than 2 years" / "over 2 years" means strictly greater than 2
        strict = bool(re.search(r"(?:more than|over|above|trên|hơn)\s*" + re.escape(num) + r"\b", norm))
        hit = {"min_years": years, "strict": strict, "snippet": re.sub(r"\s+", " ", line).strip(" -•*")[:160]}
        # Optional only if the hedge comes before the number ("Ưu tiên ứng viên có 2 năm", "Preferred: 3 years")
        # or the sentence is clearly a nice-to-have ("... is a plus", "... là lợi thế", "..., preferred.").
        # "5 years of experience, preferably with distributed systems" stays required.
        optional = (optional_section or OPTIONAL_WORDS.search(norm[:first_pos])
                    or STRONG_OPTIONAL.search(norm))
        rank = years + (0.5 if strict else 0)
        if optional:
            if optional_best is None or rank > optional_best["_rank"]:
                optional_best = {**hit, "optional": True, "_rank": rank}
        elif best is None or rank > best["_rank"]:
            best = {**hit, "optional": False, "_rank": rank}
    result = best or optional_best
    if result:
        result.pop("_rank")
    return result


def _parse_linkedin_posting(page):
    desc = re.search(r'class="show-more-less-html__markup[^"]*"[^>]*>(.*?)</div>', page, re.S)
    if not desc:
        return None
    text = re.sub(r"<(?:br|/p|/li|li|p|/h\d|/ul|/div)[^>]*>", "\n", desc.group(1))
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    criteria = dict((k.strip(), html.unescape(re.sub(r"\s+", " ", v)).strip()) for k, v in re.findall(
        r'description__job-criteria-subheader">\s*(.*?)\s*</h3>\s*<span[^>]*>\s*(.*?)\s*</span>', page, re.S))
    return {"text": text, "seniority": criteria.get("Seniority level", "")}


def _fetch_linkedin(job_id):
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return _parse_linkedin_posting(resp.read().decode("utf-8", "replace"))
        except Exception as e:
            if attempt == 0:
                time.sleep(8)
            else:
                print(f"  [JD] {job_id} failed: {e}")
    return None


def _load_cache():
    try:
        with open(JD_CACHE_PATH, "r", encoding="utf-8") as f:
            cache = json.load(f)
    except (OSError, ValueError):
        return {}
    cutoff = time.time() - CACHE_TTL_DAYS * 86400
    return {k: v for k, v in cache.items()
            if v.get("fetched_at", 0) >= cutoff and v.get("v") == PARSER_VERSION}


def _save_cache(cache):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(JD_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)


def enrich_linkedin(jobs, max_new_fetches=60, delay_seconds=1.2):
    """Attach job["jd"] = {read, min_years, optional, snippet, seniority} to LinkedIn jobs (cached)."""
    cache = _load_cache()
    fetched = 0
    for job in jobs:
        if job.get("source") != "LinkedIn":
            continue
        entry = cache.get(job["id"])
        if entry is None and fetched < max_new_fetches:
            if fetched:
                time.sleep(delay_seconds)
            fetched += 1
            posting = _fetch_linkedin(job["id"])
            if posting:
                exp = extract_experience(posting["text"]) or {}
                entry = {"read": True, "seniority": posting["seniority"], "fetched_at": time.time(),
                         "v": PARSER_VERSION, **exp}
                cache[job["id"]] = entry
        job["jd"] = entry or {"read": False}
    _save_cache(cache)
    print(f"  [JD] fetched {fetched} new descriptions, {len(cache)} cached")
    return jobs


def experience_label(jd):
    if not jd or not jd.get("read"):
        return "Chưa đọc được JD"
    if "min_years" not in jd:
        return "Không ghi số năm"
    y = jd["min_years"]
    if y == 0:
        return "0 năm (nhận fresher)"
    sign = ">" if jd.get("strict") else "≥"
    label = f"{sign} {y:g} năm" if y >= 1 else f"{sign} {round(y * 12):g} tháng"
    return label + (" (ưu tiên)" if jd.get("optional") else "")
