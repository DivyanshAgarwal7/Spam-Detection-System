"""
Domain Age & Reputation Checker for Spam Detection
Extracts domains from text, checks age and blacklist status.
"""

import re
import os
import requests
import whois
import dns.resolver
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime
from typing import Optional, Dict, List, Tuple

# Per-provider HTTP request timeout (seconds); THREAT_INTEL_OVERALL_TIMEOUT
# caps the wait while aggregating the concurrent provider results.
THREAT_INTEL_REQUEST_TIMEOUT = 3
THREAT_INTEL_OVERALL_TIMEOUT = 5

# Common DNSBL (blacklist) providers
DNSBL_PROVIDERS = [
    "zen.spamhaus.org",      # Spamhaus Zen - most comprehensive
    "bl.spamcop.net",        # SpamCop
    "b.barracudacentral.org", # Barracuda
    "dbl.spamhaus.org",      # Domain blocklist
]

# Cap the text scanned for domains so a pathologically large, attacker-supplied
# body cannot turn extraction into a performance sink (issue #940).
MAX_TEXT_LENGTH = 100_000

# Maximum length of a fully-qualified domain name (RFC 1035).
_MAX_HOSTNAME_LENGTH = 253

# Known public TLDs used to validate extraction candidates (issue #974).
#
# extract_domains used to match any "<label>.<2+ letters>" token, so ordinary
# prose -- "file.txt", "e.g", "the end.Then" -- produced fake domains that then
# incurred real WHOIS / DNSBL / threat-intel lookups on non-domains. Requiring
# the final label to be a real TLD is what turns the loose token match into a
# hostname test.
#
# The set is curated and self-contained rather than sourced from a public-suffix
# dependency: the repo ships no such library, and pulling one in (plus keeping
# its suffix data refreshed) is disproportionate for a spam heuristic. It covers
# the ISO-3166 ccTLDs and the widely used gTLDs. Filename-extension look-alikes
# that also happen to be registry TLDs (e.g. .zip, .mov) are intentionally
# omitted: in email/message text a "name.zip" token is far more likely a file
# than a domain, and under-extracting there is the safe direction for a
# precision fix. An exotic gTLD that is absent is simply not treated as a
# domain -- again the safe direction.
_CC_TLDS = frozenset(
    """
ac ad ae af ag ai al am ao aq ar as at au aw ax az
ba bb bd be bf bg bh bi bj bm bn bo br bs bt bw by bz
ca cc cd cf cg ch ci ck cl cm cn co cr cu cv cw cx cy cz
de dj dk dm do dz
ec ee eg er es et eu
fi fj fk fm fo fr
ga gb gd ge gf gg gh gi gl gm gn gp gq gr gs gt gu gw gy
hk hm hn hr ht hu
id ie il im in io iq ir is it
je jm jo jp
ke kg kh ki km kn kp kr kw ky kz
la lb lc li lk lr ls lt lu lv ly
ma mc md me mg mh mk ml mm mn mo mp mq mr ms mt mu mv mw mx my mz
na nc ne nf ng ni nl no np nr nu nz
om
pa pe pf pg ph pk pl pm pn pr ps pt pw py
qa
re ro rs ru rw
sa sb sc sd se sg sh si sj sk sl sm sn so sr ss st su sv sx sy sz
tc td tf tg th tj tk tl tm tn to tr tt tv tw tz
ua ug uk us uy uz
va vc ve vg vi vn vu
wf ws
ye yt
za zm zw
""".split()
)

_G_TLDS = frozenset(
    """
com net org edu gov mil int info biz name pro mobi asia tel travel jobs
coop aero museum cat post arpa
app dev page xyz online site tech store shop blog cloud email live news
media agency solutions digital finance systems network global world today
ventures capital studio design software cyou icu top vip club fun space
""".split()
)

KNOWN_TLDS = _CC_TLDS | _G_TLDS

# A single DNS label: 1-63 chars, alphanumeric plus hyphen, no leading/trailing
# hyphen. Anchored so it validates one already-split label at a time.
_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")

# Host candidate: one or more dot-separated labels followed by an alphabetic
# TLD. Quantifiers are bounded (labels <= 63 chars, <= 10 levels deep) so the
# scan stays linear on adversarial label runs (issue #940). The lookbehind stops
# a match from starting mid-token (so a longer host isn't split); the lookahead
# stops the alphabetic TLD from being truncated before a trailing label char.
# The preceding "@" or "/" is deliberately allowed so hosts inside email
# addresses and scheme-prefixed URLs are still captured.
_HOST_CANDIDATE_RE = re.compile(
    r"(?<![\w.-])" r"((?:[a-z0-9-]{1,63}\.){1,10}[a-z]{2,63})" r"(?![a-z0-9-])",
    re.IGNORECASE,
)


def _normalize_host(host: str) -> str:
    """Lower-case, drop a trailing root dot, and strip a leading ``www.``.

    ``www`` is stripped so ``https://www.example.com`` and a bare
    ``example.com`` collapse to the same registrable host for downstream
    lookups and de-duplication.
    """
    host = host.rstrip(".").lower()
    if host.startswith("www."):
        host = host[len("www.") :]
    return host


def _is_valid_domain(host: str) -> bool:
    """True when ``host`` is a syntactically valid hostname with a known TLD."""
    if not host or len(host) > _MAX_HOSTNAME_LENGTH:
        return False
    labels = host.split(".")
    if len(labels) < 2:
        return False
    if not all(_LABEL_RE.match(label) for label in labels):
        return False
    return labels[-1] in KNOWN_TLDS

def extract_domains(text: str) -> List[str]:
    """
    Extract domains from text.

    Returns the unique, normalized domains found in the message, sorted for
    determinism. Only tokens that are shaped like a real hostname *and* end in a
    known public TLD are returned, so non-domain text (``file.txt``, ``e.g``,
    ``example.``, bare filenames, sentence fragments with dots) is rejected
    before it can reach the WHOIS / DNSBL / threat-intel lookups (issue #974).
    """
    if not text:
        return []
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH]

    found = set()
    for match in _HOST_CANDIDATE_RE.finditer(text):
        host = _normalize_host(match.group(1))
        if _is_valid_domain(host):
            found.add(host)
    return sorted(found)

def check_domain_age(domain: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Check domain age using WHOIS.
    Returns (age_days, creation_date) or (None, error_message)
    """
    try:
        w = whois.whois(domain)
        creation_date = w.creation_date
        
        if not creation_date:
            return None, "No creation date found"
        
        # Handle if creation_date is a list (sometimes multiple dates)
        if isinstance(creation_date, list):
            creation_date = creation_date[0]
        
        # Handle string parsing if creation_date is returned as a string
        if isinstance(creation_date, str):
            from dateutil import parser as date_parser
            try:
                creation_date = date_parser.parse(creation_date)
            except Exception:
                for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%d-%b-%Y", "%Y.%m.%d"):
                    try:
                        creation_date = datetime.strptime(creation_date, fmt)
                        break
                    except ValueError:
                        continue
        
        if isinstance(creation_date, str):
            return None, f"Could not parse creation date string: {creation_date}"
            
        # Handle timezone-aware datetime
        now = datetime.now()
        if creation_date.tzinfo is not None:
            # If creation_date has timezone, make now timezone-aware
            from datetime import timezone
            now = datetime.now(timezone.utc)
        
        age_days = (now - creation_date).days
        return age_days, creation_date.strftime("%Y-%m-%d")
        
    except Exception as e:
        return None, f"WHOIS lookup failed: {str(e)}"

def check_blacklist(domain: str) -> Dict[str, bool]:
    """
    Check if domain is blacklisted on DNSBL providers.
    Returns dict with provider names and boolean status.
    """
    results = {}
    
    for provider in DNSBL_PROVIDERS:
        query = f"{domain}.{provider}"
        try:
            resolver = dns.resolver.Resolver()
            resolver.timeout = 5
            resolver.lifetime = 5
            
            answers = resolver.resolve(query, 'A')
            results[provider] = len(answers) > 0
            
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.Timeout):
            results[provider] = False
        except Exception:
            results[provider] = False
    
    return results

def _check_urlhaus(domain: str) -> Tuple[str, bool]:
    """URLHaus lookup (keyless, free public check)."""
    try:
        urlhaus_url = "https://urlhaus-api.abuse.ch/v1/host/"
        response = requests.post(urlhaus_url, json={"host": domain}, timeout=THREAT_INTEL_REQUEST_TIMEOUT)
        if response.status_code == 200 and response.json().get("query_status") == "ok":
            return "urlhaus", True
    except Exception:
        pass
    return "urlhaus", False


def _check_google_safe_browsing(domain: str) -> Tuple[str, bool]:
    """Google Safe Browsing lookup. Returns False (no-op) without an API key."""
    gsb_api_key = os.getenv("SAFE_BROWSING_API_KEY")
    if not gsb_api_key:
        return "google_safe_browsing", False
    try:
        gsb_url = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={gsb_api_key}"
        payload = {
            "client": {
                "clientId": "spam-detection-system",
                "clientVersion": "1.0.0"
            },
            "threatInfo": {
                "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": [
                    {"url": domain}
                ]
            }
        }
        response = requests.post(gsb_url, json=payload, timeout=THREAT_INTEL_REQUEST_TIMEOUT)
        if response.status_code == 200 and "matches" in response.json():
            return "google_safe_browsing", True
    except Exception:
        pass
    return "google_safe_browsing", False


def _check_virustotal(domain: str) -> Tuple[str, bool]:
    """VirusTotal domain lookup. Returns False (no-op) without an API key."""
    vt_api_key = os.getenv("VIRUSTOTAL_API_KEY")
    if not vt_api_key:
        return "virustotal", False
    try:
        vt_url = f"https://www.virustotal.com/api/v3/domains/{domain}"
        headers = {"x-apikey": vt_api_key}
        response = requests.get(vt_url, headers=headers, timeout=THREAT_INTEL_REQUEST_TIMEOUT)
        if response.status_code == 200:
            stats = response.json().get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
            if stats.get("malicious", 0) > 0 or stats.get("suspicious", 0) > 1:
                return "virustotal", True
    except Exception:
        pass
    return "virustotal", False


# Independent threat-intel providers. Each returns (result_key, flagged) and
# swallows its own errors, so they can be dispatched concurrently and aggregated
# without one provider affecting another.
_THREAT_INTEL_PROVIDERS = (
    _check_urlhaus,
    _check_google_safe_browsing,
    _check_virustotal,
)


def check_threat_intelligence(domain: str) -> Dict[str, bool]:
    """
    Query threat intelligence APIs to check if the domain is flagged/blacklisted.

    The providers are independent external services, so they are queried
    concurrently: total latency is bounded by the slowest single provider rather
    than the sum of all of them. Each provider applies its own request timeout and
    handles its own failures, so a slow or failing provider degrades to a False
    result without blocking the others.
    """
    results = {
        "google_safe_browsing": False,
        "virustotal": False,
        "urlhaus": False
    }

    with ThreadPoolExecutor(max_workers=len(_THREAT_INTEL_PROVIDERS)) as executor:
        futures = [executor.submit(provider, domain) for provider in _THREAT_INTEL_PROVIDERS]
        for future in futures:
            try:
                key, flagged = future.result(timeout=THREAT_INTEL_OVERALL_TIMEOUT)
                results[key] = flagged
            except (FuturesTimeoutError, Exception):
                # Individual provider timeout/failure: keep its default False and
                # keep aggregating the rest.
                continue

    return results

def calculate_risk_score(age_days: Optional[int], blacklist_results: Dict[str, bool]) -> Tuple[int, str]:
    """
    Calculate risk score based on domain age and blacklist status.
    Returns (score, recommendation)
    """
    score = 0
    
    # Age-based scoring (newer domains are more suspicious)
    if age_days is not None:
        if age_days < 7:
            score += 60  # Very new - high risk
        elif age_days < 30:
            score += 40  # New - medium risk
        elif age_days < 90:
            score += 20  # Moderately new - low risk
        else:
            score += 5   # Old - minimal risk
    else:
        score += 10  # Unknown - assume slightly suspicious
    
    # Blacklist-based scoring
    blacklisted_count = sum(blacklist_results.values())
    if blacklisted_count > 0:
        score += 30 + (blacklisted_count * 5)  # Base 30 + extra per blacklist
        
    # If domain is flagged on any blacklisting/threat service, set risk score to 100 immediately
    if any(blacklist_results.values()):
        score = 100
    
    # Cap at 100
    score = min(score, 100)
    
    # Determine recommendation
    if score >= 70:
        recommendation = "BLOCK"
    elif score >= 40:
        recommendation = "WARNING"
    else:
        recommendation = "SAFE"
    
    return score, recommendation

def analyze_domain(domain: str) -> Dict:
    """
    Complete analysis for a single domain.
    Returns dict with all domain risk information.
    """
    age_days, creation_date = check_domain_age(domain)
    blacklist_results = check_blacklist(domain)
    threat_intel = check_threat_intelligence(domain)
    
    # Merge blacklist results and threat intel results for calculate_risk_score
    all_blacklists = {**blacklist_results, **threat_intel}
    
    risk_score, recommendation = calculate_risk_score(age_days, all_blacklists)
    
    # Determine risk level
    if risk_score >= 70:
        risk_level = "HIGH"
    elif risk_score >= 40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"
    
    return {
        "url": domain,
        "age_days": age_days if age_days is not None else "unknown",
        "creation_date": creation_date if creation_date else "unknown",
        "blacklisted": any(all_blacklists.values()),
        "blacklist_details": blacklist_results,
        "threat_intel_details": threat_intel,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "recommendation": recommendation,
    }

def analyze_text(text: str) -> Dict:
    """
    Analyze all domains in text and return consolidated results.
    """
    domains = extract_domains(text)
    
    if not domains:
        return {
            "domains_found": [],
            "max_risk_score": 0,
            "overall_risk": "SAFE",
            "details": []
        }
    
    domain_analyses = []
    max_score = 0
    
    for domain in domains[:5]:  # Limit to first 5 domains for performance
        analysis = analyze_domain(domain)
        domain_analyses.append(analysis)
        max_score = max(max_score, analysis["risk_score"])
    
    # Determine overall recommendation
    if max_score >= 70:
        overall = "BLOCK"
    elif max_score >= 40:
        overall = "WARNING"
    else:
        overall = "SAFE"
    
    return {
        "domains_found": domains,
        "max_risk_score": max_score,
        "overall_risk": overall,
        "details": domain_analyses,
    }