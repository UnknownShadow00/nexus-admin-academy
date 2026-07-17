import logging

import httpx

logger = logging.getLogger(__name__)


async def fetch_recent_cves(keyword: str = "windows", count: int = 5) -> list[dict]:
    url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    params = {"keywordSearch": keyword, "resultsPerPage": max(1, min(count, 20))}

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    cves = []
    for item in data.get("vulnerabilities", []):
        cve = item.get("cve", {})
        descriptions = cve.get("descriptions", [])
        description = ""
        for desc in descriptions:
            if desc.get("lang") == "en":
                description = desc.get("value", "")
                break
        if not description and descriptions:
            description = descriptions[0].get("value", "")

        severity = "UNKNOWN"
        metrics = cve.get("metrics", {})
        if metrics.get("cvssMetricV31"):
            severity = metrics["cvssMetricV31"][0].get("cvssData", {}).get("baseSeverity", "UNKNOWN")
        elif metrics.get("cvssMetricV30"):
            severity = metrics["cvssMetricV30"][0].get("cvssData", {}).get("baseSeverity", "UNKNOWN")

        cves.append(
            {
                "cve_id": cve.get("id"),
                "description": description,
                "severity": severity,
                "published": cve.get("published"),
            }
        )

    return cves


async def generate_security_ticket_from_cve(cve_id: str) -> dict | None:
    cves = await fetch_recent_cves(count=20)
    cve = next((item for item in cves if item.get("cve_id") == cve_id), None)
    if not cve:
        return None

    severity = (cve.get("severity") or "UNKNOWN").upper()
    difficulty = 4 if severity in {"HIGH", "CRITICAL"} else 3

    description = (
        f"Security team flagged vulnerability {cve_id}. "
        f"{cve.get('description', '')[:600]}\n\n"
        "Your tasks:\n"
        "1. Research this vulnerability\n"
        "2. Determine if lab systems are affected\n"
        "3. Document remediation steps\n"
        "4. Create a brief risk assessment"
    )

    return {
        "title": f"Security Alert: {cve_id}",
        "description": description,
        "difficulty": difficulty,
        "week_number": 8,
        "category": "security",
    }
