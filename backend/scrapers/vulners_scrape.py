#!/usr/bin/env python3
"""
Vulners API scraper for high CVE density data.
Integrates with the existing scraping pipeline to provide recent and important CVEs.
"""

import vulners
import sys
import os
from datetime import datetime, timedelta
import json

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Article

class VulnersScraper:
    def __init__(self, max_results=10, api_key=None):
        self.max_results = max_results
        self.api_key = api_key or "9DZAW2NZ8L5502PAVQURU0VRCL7WLXNO61JEX3A4MCF1T0SNRS4THDSVMITCHUHM"
        self.vulners_api = vulners.VulnersApi(api_key=self.api_key)
    
    def get_recent_cves(self, days_back=7, min_cvss=5.0):
        """Get recent CVEs with minimum CVSS score"""
        print(f"🔍 Fetching recent CVEs from Vulners (last {days_back} days, CVSS >= {min_cvss})...")
        
        articles = []
        
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Build search query for recent, high-severity CVEs
            query = f"type:cve AND published:[{start_date.strftime('%Y-%m-%d')} TO {end_date.strftime('%Y-%m-%d')}]"
            
            # Search for CVEs with specified fields
            search_result = self.vulners_api.find(
                query,
                limit=self.max_results,
                fields=[
                    "id", "title", "description", "short_description",
                    "type", "bulletinFamily", "cvss", "published", 
                    "modified", "href", "cvelist", "references"
                ]
            )
            
            if search_result:
                documents = search_result
                
                for doc in documents:
                    # Filter by minimum CVSS score
                    cvss_score = doc.get('cvss', {}).get('score', 0)
                    if cvss_score < min_cvss:
                        continue
                    
                    # Extract CVE ID
                    cve_id = doc.get('id', 'Unknown')
                    if not cve_id.startswith('CVE-'):
                        continue
                    
                    # Get title and description
                    title = doc.get('title', f"Vulnerability: {cve_id}")
                    description = doc.get('description', '') or doc.get('short_description', '')
                    
                    if not description:
                        description = f"Vulnerability details for {cve_id}"
                    
                    # Parse publication date
                    published_str = doc.get('published', '')
                    published_date = datetime.now()
                    if published_str:
                        try:
                            published_date = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                            published_date = published_date.replace(tzinfo=None)
                        except:
                            pass
                    
                    # Determine severity
                    severity = "MEDIUM"
                    if cvss_score >= 9.0:
                        severity = "CRITICAL"
                    elif cvss_score >= 7.0:
                        severity = "HIGH"
                    elif cvss_score >= 4.0:
                        severity = "MEDIUM"
                    else:
                        severity = "LOW"
                    
                    # Create article
                    article = Article(
                        id=None,
                        source="Vulners",
                        title=title,
                        title_translated=title,  # Already in English
                        url=doc.get('href', f"https://vulners.com/cve/{cve_id}"),
                        content=description,
                        content_translated=description,
                        language="en",
                        scraped_at=datetime.now(),
                        published_date=published_date
                    )
                    
                    articles.append(article)
            
            print(f"✅ Vulners: Found {len(articles)} recent CVEs (CVSS >= {min_cvss})")
            
        except Exception as e:
            print(f"❌ Error fetching from Vulners API: {e}")
        
        return articles
    
    def get_high_severity_cves(self, max_results=10):
        """Get high-severity CVEs (CVSS >= 7.0)"""
        print("🔍 Fetching high-severity CVEs from Vulners...")
        
        articles = []
        
        try:
            # Search for high-severity CVEs
            query = "type:cve AND cvss.score:[7.0 TO 10.0]"
            
            search_result = self.vulners_api.find(
                query,
                limit=max_results,
                fields=[
                    "id", "title", "description", "short_description",
                    "type", "bulletinFamily", "cvss", "published", 
                    "modified", "href", "cvelist", "references"
                ]
            )
            
            if 'data' in search_result and 'documents' in search_result['data']:
                documents = search_result['data']['documents']
                
                for doc in documents:
                    cve_id = doc.get('id', 'Unknown')
                    if not cve_id.startswith('CVE-'):
                        continue
                    
                    title = doc.get('title', f"High-Severity Vulnerability: {cve_id}")
                    description = doc.get('description', '') or doc.get('short_description', '')
                    
                    if not description:
                        description = f"High-severity vulnerability details for {cve_id}"
                    
                    # Parse publication date
                    published_str = doc.get('published', '')
                    published_date = datetime.now()
                    if published_str:
                        try:
                            published_date = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                            published_date = published_date.replace(tzinfo=None)
                        except:
                            pass
                    
                    article = Article(
                        id=None,
                        source="Vulners",
                        title=title,
                        title_translated=title,
                        url=doc.get('href', f"https://vulners.com/cve/{cve_id}"),
                        content=description,
                        content_translated=description,
                        language="en",
                        scraped_at=datetime.now(),
                        published_date=published_date
                    )
                    
                    articles.append(article)
            
            print(f"✅ Vulners: Found {len(articles)} high-severity CVEs")
            
        except Exception as e:
            print(f"❌ Error fetching high-severity CVEs: {e}")
        
        return articles
    
    def get_exploitable_cves(self, max_results=10):
        """Get CVEs with available exploits"""
        print("🔍 Fetching exploitable CVEs from Vulners...")
        
        articles = []
        
        try:
            # Search for CVEs with exploits
            query = "type:cve AND exploit"
            
            search_result = self.vulners_api.find(
                query,
                limit=max_results,
                fields=[
                    "id", "title", "description", "short_description",
                    "type", "bulletinFamily", "cvss", "published", 
                    "modified", "href", "cvelist", "references"
                ]
            )
            
            if 'data' in search_result and 'documents' in search_result['data']:
                documents = search_result['data']['documents']
                
                for doc in documents:
                    cve_id = doc.get('id', 'Unknown')
                    if not cve_id.startswith('CVE-'):
                        continue
                    
                    title = doc.get('title', f"Exploitable Vulnerability: {cve_id}")
                    description = doc.get('description', '') or doc.get('short_description', '')
                    
                    if not description:
                        description = f"Exploitable vulnerability details for {cve_id}"
                    
                    # Parse publication date
                    published_str = doc.get('published', '')
                    published_date = datetime.now()
                    if published_str:
                        try:
                            published_date = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                            published_date = published_date.replace(tzinfo=None)
                        except:
                            pass
                    
                    article = Article(
                        id=None,
                        source="Vulners",
                        title=title,
                        title_translated=title,
                        url=doc.get('href', f"https://vulners.com/cve/{cve_id}"),
                        content=description,
                        content_translated=description,
                        language="en",
                        scraped_at=datetime.now(),
                        published_date=published_date
                    )
                    
                    articles.append(article)
            
            print(f"✅ Vulners: Found {len(articles)} exploitable CVEs")
            
        except Exception as e:
            print(f"❌ Error fetching exploitable CVEs: {e}")
        
        return articles
    
    def scrape_all(self):
        """Scrape from all Vulners sources"""
        print("🚀 Starting Vulners CVE scraping...")
        
        all_articles = []
        
        # Get recent CVEs
        recent_cves = self.get_recent_cves(days_back=7, min_cvss=5.0)
        all_articles.extend(recent_cves)
        
        # Get high-severity CVEs
        high_sev_cves = self.get_high_severity_cves(max_results=5)
        all_articles.extend(high_sev_cves)
        
        # Get exploitable CVEs
        exploitable_cves = self.get_exploitable_cves(max_results=5)
        all_articles.extend(exploitable_cves)
        
        # Remove duplicates based on URL
        unique_articles = []
        seen_urls = set()
        for article in all_articles:
            if article.url not in seen_urls:
                unique_articles.append(article)
                seen_urls.add(article.url)
        
        print(f"\n📊 Total unique Vulners CVEs: {len(unique_articles)}")
        return unique_articles[:self.max_results]

def main():
    """Test the Vulners scraper"""
    scraper = VulnersScraper(max_results=10)
    articles = scraper.scrape_all()
    
    # Save sample results
    if articles:
        sample_data = []
        for article in articles[:5]:
            sample_data.append({
                'source': article.source,
                'title': article.title,
                'url': article.url,
                'language': article.language,
                'published_date': article.published_date.isoformat()
            })
        
        with open('vulners_scraper_sample.json', 'w') as f:
            json.dump(sample_data, f, indent=2, default=str)
        
        print(f"\n💾 Sample saved to vulners_scraper_sample.json")
        print(f"📋 Sample CVEs:")
        for i, article in enumerate(articles[:3]):
            print(f"{i+1}. {article.title[:60]}...")

if __name__ == "__main__":
    main()
