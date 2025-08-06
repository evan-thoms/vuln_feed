import requests
import json
import time
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Optional
import pandas as pd
from bs4 import BeautifulSoup
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

@dataclass
class Vulnerability:
    cve_id: str
    title: str
    description: str
    severity: str
    cvss_score: float
    published_date: datetime
    source: str
    url: str
    affected_products: List[str]
    
    def get_priority_score(self) -> float:
        """Calculate priority based on CVSS score and recency"""
        days_old = (datetime.now() - self.published_date).days
        recency_factor = max(0, 30 - days_old) / 30  # Higher score for newer vulns
        severity_factor = self.cvss_score / 10  # Normalize CVSS to 0-1
        return (severity_factor * 0.7) + (recency_factor * 0.3)

class VulnerabilityFeedScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'VulnIntel-Research-Bot/1.0 (Security Research Purpose)'
        })
        self.vulnerabilities = []
        
    def scrape_nist_nvd(self, days_back: int = 7) -> List[Vulnerability]:
        """Scrape NIST National Vulnerability Database"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # NIST NVD API 2.0
        base_url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
        params = {
            'pubStartDate': start_date.strftime('%Y-%m-%dT%H:%M:%S.000'),
            'pubEndDate': end_date.strftime('%Y-%m-%dT%H:%M:%S.000'),
            'resultsPerPage': 100
        }
        
        vulnerabilities = []
        
        try:
            response = self.session.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            for cve in data.get('vulnerabilities', []):
                cve_data = cve['cve']
                
                # Extract CVSS score
                cvss_score = 0.0
                if 'metrics' in cve_data:
                    if 'cvssMetricV31' in cve_data['metrics']:
                        cvss_score = cve_data['metrics']['cvssMetricV31'][0]['cvssData']['baseScore']
                    elif 'cvssMetricV30' in cve_data['metrics']:
                        cvss_score = cve_data['metrics']['cvssMetricV30'][0]['cvssData']['baseScore']
                    elif 'cvssMetricV2' in cve_data['metrics']:
                        cvss_score = cve_data['metrics']['cvssMetricV2'][0]['cvssData']['baseScore']
                
                # Determine severity
                severity = self._get_severity_from_cvss(cvss_score)
                
                # Extract description
                description = ""
                if 'descriptions' in cve_data:
                    for desc in cve_data['descriptions']:
                        if desc['lang'] == 'en':
                            description = desc['value']
                            break
                
                # Extract affected products
                affected_products = []
                if 'configurations' in cve_data:
                    for config in cve_data['configurations']:
                        for node in config.get('nodes', []):
                            for cpe_match in node.get('cpeMatch', []):
                                if cpe_match.get('vulnerable', False):
                                    affected_products.append(cpe_match['criteria'])
                
                vuln = Vulnerability(
                    cve_id=cve_data['id'],
                    title=cve_data['id'],
                    description=description,
                    severity=severity,
                    cvss_score=cvss_score,
                    published_date=datetime.fromisoformat(cve_data['published'].replace('Z', '+00:00')),
                    source='NIST NVD',
                    url=f"https://nvd.nist.gov/vuln/detail/{cve_data['id']}",
                    affected_products=affected_products[:5]  # Limit to first 5
                )
                vulnerabilities.append(vuln)
                
            # Rate limiting - NIST allows 50 requests per 30 seconds
            time.sleep(0.6)
            
        except requests.exceptions.RequestException as e:
            print(f"Error scraping NIST NVD: {e}")
            
        return vulnerabilities
    
    def scrape_cisa_kev(self) -> List[Vulnerability]:
        """Scrape CISA Known Exploited Vulnerabilities"""
        url = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
        
        vulnerabilities = []
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            
            # Filter for recent additions (last 30 days)
            recent_date = datetime.now() - timedelta(days=30)
            
            for vuln in data.get('vulnerabilities', []):
                date_added = datetime.strptime(vuln['dateAdded'], '%Y-%m-%d')
                
                if date_added >= recent_date:
                    vuln_obj = Vulnerability(
                        cve_id=vuln['cveID'],
                        title=vuln['vulnerabilityName'],
                        description=vuln['shortDescription'],
                        severity='CRITICAL',  # CISA KEV are high priority
                        cvss_score=9.0,  # Assume high since actively exploited
                        published_date=date_added,
                        source='CISA KEV',
                        url=f"https://cve.mitre.org/cgi-bin/cvename.cgi?name={vuln['cveID']}",
                        affected_products=[vuln['product']]
                    )
                    vulnerabilities.append(vuln_obj)
                    
        except requests.exceptions.RequestException as e:
            print(f"Error scraping CISA KEV: {e}")
            
        return vulnerabilities
    
    def scrape_exploit_db(self, days_back: int = 7) -> List[Vulnerability]:
        """Scrape Exploit-DB via direct page scraping"""
        base_url = "https://www.exploit-db.com"
        vulnerabilities = []
        
        try:
            # Get the main page first
            response = self.session.get(base_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for recent exploits table
            table = soup.find('table', {'id': 'exploits-table'})
            if not table:
                # Try alternative scraping approach
                response = self.session.get(f"{base_url}/search")
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
            
            # Since Exploit-DB's AJAX endpoint is protected, let's use RSS feed instead
            rss_url = "https://www.exploit-db.com/rss.xml"
            response = self.session.get(rss_url)
            response.raise_for_status()
            
            # Parse RSS feed
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)
            
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            for item in root.findall('.//item')[:20]:  # Limit to first 20
                title = item.find('title').text if item.find('title') is not None else ""
                link = item.find('link').text if item.find('link') is not None else ""
                pub_date_str = item.find('pubDate').text if item.find('pubDate') is not None else ""
                
                try:
                    # Parse RSS date format
                    pub_date = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z')
                    pub_date = pub_date.replace(tzinfo=None)  # Remove timezone for comparison
                    
                    if pub_date >= cutoff_date:
                        # Extract EDB ID from URL
                        edb_id = link.split('/')[-1] if link else "unknown"
                        
                        vuln = Vulnerability(
                            cve_id=f"EDB-{edb_id}",
                            title=title,
                            description=title,
                            severity='HIGH',
                            cvss_score=7.5,
                            published_date=pub_date,
                            source='Exploit-DB',
                            url=link,
                            affected_products=[]
                        )
                        vulnerabilities.append(vuln)
                        
                except ValueError as e:
                    print(f"Date parsing error: {e}")
                    continue
                    
        except requests.exceptions.RequestException as e:
            print(f"Error scraping Exploit-DB: {e}")
        except Exception as e:
            print(f"Error parsing Exploit-DB data: {e}")
            
        return vulnerabilities
    
    def scrape_vulndb(self, days_back: int = 7) -> List[Vulnerability]:
        """Scrape VulnDB style sources or security blogs"""
        sources = [
            "https://thehackernews.com",
            "https://www.bleepingcomputer.com",
            "https://krebsonsecurity.com"
        ]
        
        vulnerabilities = []
        
        for source in sources:
            try:
                response = self.session.get(source)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Generic article extraction
                articles = soup.find_all(['article', 'div'], class_=re.compile(r'(post|article|story|entry)'))
                
                cutoff_date = datetime.now() - timedelta(days=days_back)
                
                for article in articles[:5]:  # Limit per source
                    try:
                        title_elem = article.find(['h1', 'h2', 'h3', 'a'])
                        if not title_elem:
                            continue
                            
                        title = title_elem.get_text(strip=True)
                        
                        # Skip if not vulnerability related
                        vuln_keywords = ['vulnerability', 'exploit', 'cve', 'security', 'patch', 'flaw', 'bug']
                        if not any(keyword in title.lower() for keyword in vuln_keywords):
                            continue
                        
                        # Try to find date
                        date_elem = article.find('time') or article.find(class_=re.compile(r'date'))
                        pub_date = datetime.now()  # Default to now
                        
                        if date_elem:
                            date_str = date_elem.get('datetime') or date_elem.get_text(strip=True)
                            try:
                                # Try various date formats
                                for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%B %d, %Y']:
                                    try:
                                        pub_date = datetime.strptime(date_str[:19], fmt)
                                        break
                                    except ValueError:
                                        continue
                            except:
                                pass
                        
                        if pub_date >= cutoff_date:
                            link_elem = title_elem if title_elem.name == 'a' else title_elem.find('a')
                            url = link_elem.get('href', '') if link_elem else ""
                            if url and not url.startswith('http'):
                                url = f"{source}{url}"
                            
                            vuln = Vulnerability(
                                cve_id=f"NEWS-{hash(title) % 10000}",
                                title=title,
                                description=title,
                                severity='MEDIUM',
                                cvss_score=5.0,
                                published_date=pub_date,
                                source=source.split('//')[1].split('/')[0],
                                url=url,
                                affected_products=[]
                            )
                            vulnerabilities.append(vuln)
                            
                    except Exception as e:
                        continue
                        
            except requests.exceptions.RequestException as e:
                print(f"Error scraping {source}: {e}")
                continue
                
        return vulnerabilities
    
    def _get_severity_from_cvss(self, score: float) -> str:
        """Convert CVSS score to severity level"""
        if score >= 9.0:
            return 'CRITICAL'
        elif score >= 7.0:
            return 'HIGH'
        elif score >= 4.0:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def aggregate_and_prioritize(self, days_back: int = 7) -> List[Vulnerability]:
        """Aggregate vulnerabilities from all sources and prioritize"""
        all_vulns = []
        
        print("Scraping NIST NVD...")
        all_vulns.extend(self.scrape_nist_nvd(days_back))
        
        print("Scraping CISA KEV...")
        all_vulns.extend(self.scrape_cisa_kev())
        
        print("Scraping Exploit-DB...")
        all_vulns.extend(self.scrape_exploit_db(days_back))
        
        print("Scraping security news sources...")
        all_vulns.extend(self.scrape_vulndb(days_back))
        
        # Remove duplicates based on CVE ID
        unique_vulns = {}
        for vuln in all_vulns:
            if vuln.cve_id not in unique_vulns:
                unique_vulns[vuln.cve_id] = vuln
            else:
                # Keep the one with higher priority score
                if vuln.get_priority_score() > unique_vulns[vuln.cve_id].get_priority_score():
                    unique_vulns[vuln.cve_id] = vuln
        
        # Sort by priority score (highest first)
        sorted_vulns = sorted(unique_vulns.values(), 
                            key=lambda x: x.get_priority_score(), 
                            reverse=True)
        
        return sorted_vulns
    
    def generate_report(self, vulnerabilities: List[Vulnerability], top_n: int = 20) -> str:
        """Generate HTML report of top vulnerabilities"""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Weekly Vulnerability Intelligence Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #2c3e50; color: white; padding: 20px; text-align: center; }}
                .vuln {{ border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }}
                .critical {{ border-left: 5px solid #e74c3c; }}
                .high {{ border-left: 5px solid #f39c12; }}
                .medium {{ border-left: 5px solid #f1c40f; }}
                .low {{ border-left: 5px solid #27ae60; }}
                .meta {{ color: #7f8c8d; font-size: 0.9em; }}
                .score {{ font-weight: bold; color: #2c3e50; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Weekly Vulnerability Intelligence Report</h1>
                <p>Generated on {date}</p>
            </div>
            
            <h2>Top {count} Critical & Recent Vulnerabilities</h2>
            {vulnerabilities}
            
            <div class="meta">
                <p>Report generated by Vulnerability Intelligence Pipeline</p>
                <p>Sources: NIST NVD, CISA KEV, Exploit-DB, Security News</p>
            </div>
        </body>
        </html>
        """
        
        vuln_html = ""
        for vuln in vulnerabilities[:top_n]:
            products_str = ", ".join(vuln.affected_products[:3])
            if len(vuln.affected_products) > 3:
                products_str += f" (+{len(vuln.affected_products) - 3} more)"
            
            vuln_html += f"""
            <div class="vuln {vuln.severity.lower()}">
                <h3>{vuln.title}</h3>
                <p><strong>CVE ID:</strong> {vuln.cve_id}</p>
                <p><strong>Description:</strong> {vuln.description[:200]}...</p>
                <p><strong>Severity:</strong> <span class="score">{vuln.severity} (CVSS: {vuln.cvss_score})</span></p>
                <p><strong>Published:</strong> {vuln.published_date.strftime('%Y-%m-%d')}</p>
                <p><strong>Source:</strong> {vuln.source}</p>
                <p><strong>Affected Products:</strong> {products_str}</p>
                <p><a href="{vuln.url}" target="_blank">View Details</a></p>
                <div class="meta">Priority Score: {vuln.get_priority_score():.2f}</div>
            </div>
            """
        
        return html_template.format(
            date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            count=min(top_n, len(vulnerabilities)),
            vulnerabilities=vuln_html
        )
    
    def send_email_report(self, html_report: str, recipient_email: str, 
                         smtp_server: str, smtp_port: int, sender_email: str, 
                         sender_password: str):
        """Send email report"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Weekly Vulnerability Intelligence Report - {datetime.now().strftime('%Y-%m-%d')}"
            msg['From'] = sender_email
            msg['To'] = recipient_email
            
            html_part = MIMEText(html_report, 'html')
            msg.attach(html_part)
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
            
            print(f"Report sent successfully to {recipient_email}")
            
        except Exception as e:
            print(f"Error sending email: {e}")

# Example usage
def main():
    scraper = VulnerabilityFeedScraper()
    
    # Scrape vulnerabilities from the last 7 days
    print("Starting vulnerability intelligence gathering...")
    vulnerabilities = scraper.aggregate_and_prioritize(days_back=7)
    
    print(f"Found {len(vulnerabilities)} vulnerabilities")
    
    # Generate report
    html_report = scraper.generate_report(vulnerabilities, top_n=15)
    
    # Save report to file
    with open(f"vuln_report_{datetime.now().strftime('%Y%m%d')}.html", 'w') as f:
        f.write(html_report)
    
    # Optionally send email (configure your SMTP settings)
    # scraper.send_email_report(
    #     html_report,
    #     "recipient@example.com",
    #     "smtp.gmail.com",
    #     587,
    #     "your-email@gmail.com",
    #     "your-app-password"
    # )
    
    # Print top 5 for quick review
    print("\nTop 5 Critical Vulnerabilities:")
    for i, vuln in enumerate(vulnerabilities[:5], 1):
        print(f"{i}. {vuln.cve_id} - {vuln.title} (Score: {vuln.get_priority_score():.2f})")

if __name__ == "__main__":
    main()
