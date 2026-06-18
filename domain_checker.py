"""
Domain Age & Reputation Checker for Spam Detection
Extracts domains from text, checks age and blacklist status.
"""

import re
import whois
import dns.resolver
from datetime import datetime
from typing import Optional, Dict, List, Tuple

# Common DNSBL (blacklist) providers
DNSBL_PROVIDERS = [
    "zen.spamhaus.org",      # Spamhaus Zen - most comprehensive
    "bl.spamcop.net",        # SpamCop
    "b.barracudacentral.org", # Barracuda
    "dbl.spamhaus.org",      # Domain blocklist
]

def extract_domains(text: str) -> List[str]:
    """
    Extract domains from text using regex.
    Returns unique domains found in the message.
    """
    # Regex to extract domains from URLs and plain text
    pattern = r'https?://(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)'
    urls = re.findall(pattern, text, re.IGNORECASE)
    
    # Also find domains not in URL format
    domain_pattern = r'\b([a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)\b'
    domains = re.findall(domain_pattern, text, re.IGNORECASE)
    
    # Combine and remove duplicates
    all_domains = list(set(urls + domains))
    return all_domains

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
        
        age_days = (datetime.now() - creation_date).days
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
    risk_score, recommendation = calculate_risk_score(age_days, blacklist_results)
    
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
        "blacklisted": any(blacklist_results.values()),
        "blacklist_details": blacklist_results,
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


# Quick test function
if __name__ == "__main__":
    # Test with sample spam message
    test_message = "Click here: http://suspicious-site.com and http://new-phishing-domain.xyz"
    
    result = analyze_text(test_message)
    print("Domain Analysis Result:")
    import json
    print(json.dumps(result, indent=2))