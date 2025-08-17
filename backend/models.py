from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Literal

@dataclass
class QueryParams:
    content_type: Literal["cve", "news", "both"] = "both"
    severity: Optional[str] = None  # low, medium, high, critical
    days_back: int = 7
    max_results: int = 10
    output_format: Literal["display", "email"] = "display"
    email_address: Optional[str] = None
    language: Literal["en", "zh", "ru", "all"] = "all"


@dataclass
class NewsItem:
    title: str
    title_translated: str
    summary: str
    published_date: datetime
    original_language: str
    source: str
    url: str        
    intrigue: float

@dataclass
class Vulnerability:
    cve_id: str
    title: str
    title_translated: str
    summary: str
    severity: str
    cvss_score: float
    published_date: datetime
    original_language: str
    source: str
    url: str
    intrigue: float
    affected_products: List[str]

    def get_priority_score(self) -> float:
        days_old = (datetime.now() - self.published_date).days
        recency = max(0, 30-days_old)/30
        severity = self.cvss_score /10 
        return (severity * .7) + (recency*.3)
    
@dataclass
class Article:
    id: Optional[int]
    source: str
    title: str
    title_translated: str
    url: str
    content: str
    content_translated: str
    language: str
    scraped_at: datetime
    published_date: datetime
