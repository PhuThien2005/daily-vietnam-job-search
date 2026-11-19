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
PARSER_VERSION = 4  # bump when extract_experience changes so cached results are recomputed
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


# ---- "Apply first" flags -------------------------------------------------------------
CONVERT_PATTERN = re.compile(
    r"chuyển (?:lên |sang |thành )?(?:nhân viên |làm |hợp đồng )?chính thức|trở thành (?:nhân viên )?chính thức|"
    r"(?:cơ hội|xem xét|xét|được) (?:được |để )?(?:ký |làm |tuyển |giữ lại |nhận )?(?:hợp đồng |làm việc |vào )?(?:chính thức|lâu dài)|"
    r"ký hợp đồng (?:lao động )?chính thức|giữ lại làm việc|nhân viên chính thức sau|"
    r"return offer|full[- ]time offer|offer (?:of |for )?(?:a )?full[- ]time|"
    r"convert(?:ed|ing)? (?:to|into) (?:a )?(?:full[- ]time|permanent|official)|conversion to (?:a )?(?:full[- ]time|permanent)|"
    r"(?:opportunit(?:y|ies)|chance|possibility) (?:to|for) (?:become|be|join|transition|move)\w* (?:\w+ ){0,3}?"
    r"(?:full[- ]time|permanent|official) (?:employee|position|role|staff|member)|"
    r"(?:full[- ]time|permanent|official) (?:position|role|employment) (?:after|upon)", re.I)
PAID_PATTERN = re.compile(r"có lương|có trợ cấp|trợ cấp|phụ cấp thực tập|hỗ trợ (?:chi phí|tài chính|lương)|lương thực tập|"
                          r"\ballowance|paid internship|stipend|\bpaid\b", re.I)


def extract_flags(text):
    """['convert'] if the post promises an intern→official path, ['paid'] if the internship is paid."""
    flags = []
    if CONVERT_PATTERN.search(text or ""):
        flags.append("convert")
    if PAID_PATTERN.search(text or ""):
        flags.append("paid")
    return flags


def flags_label(job):
    flags = set((job.get("jd") or {}).get("flags", [])) | set(extract_flags(job.get("title", "")))
    parts = []
    if "convert" in flags:
        parts.append("🎯 chuyển chính thức")
    if "paid" in flags and job.get("level") in ("Intern", None):
        parts.append("💰 có lương")
    return ", ".join(parts)


def html_to_text(fragment):
    """HTML → plain text that keeps one line per paragraph/list item (needed for line-based parsing)."""
    text = re.sub(r"<(?:script|style)[^>]*>.*?</(?:script|style)>", " ", fragment or "", flags=re.S)
    text = re.sub(r"<(?:br|/p|/li|li|p|/h\d|h\d|/ul|/div|div|tr)[^>]*>", "\n", text)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return "\n".join(re.sub(r"[ \t\xa0]+", " ", line).strip() for line in text.splitlines() if line.strip())


def _parse_linkedin_posting(page):
    desc = re.search(r'class="show-more-less-html__markup[^"]*"[^>]*>(.*?)</div>', page, re.S)
    if not desc:
        return None
    text = html_to_text(desc.group(1))
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


def _slice(text, starts, ends, max_len=12000):
    """Keep only the job-description part of a full page (drops 'similar jobs' sidebars)."""
    low = text.lower()
    start = min([i for i in (low.find(k.lower()) for k in starts) if i >= 0] or [0])
    end_candidates = [i for i in (low.find(k.lower(), start + 1) for k in ends) if i > start]
    end = min(end_candidates) if end_candidates else start + max_len
    return text[start:min(end, start + max_len)]


def _fetch_itviec(job):
    """ITviec job page: direct first, Jina Reader when ITviec blocks us (403 on GitHub Actions)."""
    from http_util import http_get, jina_get
    status, page = http_get(job["link"])
    text = html_to_text(page) if status == 200 else jina_get(job["link"])
    if not text or not re.search(r"Job description|Mô tả công việc|skills and experience", text, re.I):
        return None  # blocked / empty page: don't cache, retry next run
    return {"text": _slice(text, ["Job description", "Mô tả công việc"],
                           ["Why you'll love working here", "Tại sao bạn sẽ yêu thích", "More jobs for you",
                            "Việc làm khác"]), "seniority": ""}


def _fetch_careerlink(job):
    """CareerLink job page. Prefers its structured data: JSON-LD monthsOfExperience and the
    '2 - 5 năm kinh nghiệm' summary; falls back to the description text."""
    from http_util import http_get
    status, page = http_get(job["link"])
    if status != 200:
        return None
    months = re.search(r'monthsOfExperience\\?"\s*:\s*(\d+)', page)
    summary = re.search(r">\s*((?:Không yêu cầu kinh nghiệm|Chưa có kinh nghiệm|Dưới 1 năm[^<]*|"
                        r"[^<>]{0,25}\d+[^<>]{0,25}năm kinh nghiệm))\s*<", page)
    text = html_to_text(page)
    if not months and not summary and "Mô tả công việc" not in text:
        return None  # CareerLink throttles bursts with an empty shell page: don't cache, retry next run
    body = _slice(text, ["Mô tả công việc"], ["Thông tin liên hệ", "Việc làm tương tự", "Việc làm liên quan"])
    exp = None
    if summary:
        line = summary.group(1).strip()
        if re.search(r"không yêu cầu|chưa có|dưới 1", line, re.I):
            exp = {"min_years": 0.0, "strict": False, "optional": False, "snippet": f"CareerLink: {line}"}
        else:
            exp = extract_experience("Kinh nghiệm: " + line)
            if exp:
                exp["snippet"] = f"CareerLink: {line}"
    if exp is None and months:
        m = int(months.group(1))
        exp = {"min_years": round(m / 12, 2), "strict": False, "optional": False,
               "snippet": f"CareerLink: {m} tháng kinh nghiệm"}
    return {"exp": exp, "text": body, "seniority": ""}


def _fetch_uit_forum(job):
    from http_util import http_get
    topic_id = job["id"].split("-", 1)[1]
    status, text = http_get(f"https://forum.uit.edu.vn/t/{topic_id}.json")
    if status != 200:
        return None
    posts = json.loads(text).get("post_stream", {}).get("posts", [])
    return {"text": html_to_text(posts[0].get("cooked", "")) if posts else "", "seniority": ""}


def _fetch_fit_hcmus(job):
    from http_util import http_get
    status, page = http_get(job["link"])
    if status != 200:
        return None
    text = html_to_text(page)
    if job["title"][:20].lower() not in text.lower():
        return None  # not the article page: don't cache
    return {"text": _slice(text, [job["title"][:20]], ["©2006", "Các tin khác", "Tin liên quan"]), "seniority": ""}


FETCHERS = {
    "UIT Forum": _fetch_uit_forum,
    "FIT HCMUS": _fetch_fit_hcmus,
    "LinkedIn": lambda job: _fetch_linkedin(job["id"]),
    "ITviec": _fetch_itviec,
    "CareerLink": _fetch_careerlink,
}


MAX_NEW_FETCHES = {"LinkedIn": 60, "ITviec": 25, "CareerLink": 20, "UIT Forum": 30, "FIT HCMUS": 30}  # per run; the rest wait for the next run
DELAY_SECONDS = {"LinkedIn": 1.2, "ITviec": 1.0, "CareerLink": 3.0, "UIT Forum": 2.0, "FIT HCMUS": 1.5}  # Jina calls are spaced in http_util


def enrich_jobs(jobs):
    """Attach job["jd"] = {read, min_years, strict, optional, snippet, seniority} by reading each job's description.
    Jobs whose site already states the experience (VietnamWorks, TopDev) keep their structured value.
    Results are cached per source+id, so each description is read once."""
    cache = _load_cache()
    fetched = {}
    for job in jobs:
        source = job.get("source")
        fetcher = FETCHERS.get(source)
        if job.get("jd") or not fetcher:
            continue
        key = job["id"] if source == "LinkedIn" else f"{source}:{job['id']}"
        entry = cache.get(key)
        if entry is None and fetched.get(source, 0) < MAX_NEW_FETCHES.get(source, 20):
            if fetched.get(source):
                time.sleep(DELAY_SECONDS.get(source, 1.5))
            fetched[source] = fetched.get(source, 0) + 1
            posting = fetcher(job)
            if posting:
                exp = posting.get("exp") or extract_experience(posting.get("text", "")) or {}
                entry = {"read": True, "seniority": posting.get("seniority", ""), "fetched_at": time.time(),
                         "v": PARSER_VERSION, "flags": extract_flags(posting.get("text", "")), **exp}
                cache[key] = entry
        job["jd"] = entry or {"read": False}
    _save_cache(cache)
    print(f"  [JD] read new descriptions {fetched or '{}'}, {len(cache)} cached")
    return jobs


enrich_linkedin = enrich_jobs  # backwards-compatible name


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
