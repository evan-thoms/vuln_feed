"""
Email Notification System for Sentinel Intelligence Gathering
Sends notifications for successful runs and errors
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, Any, Optional



def send_intelligence_report(
    email_address: str,
    session_id: str,
    results: Dict[str, Any],
    success: bool = True
) -> bool:
    """
    Send intelligence gathering report via email
    
    Args:
        email_address: Recipient email address
        session_id: Session identifier
        results: Results dictionary with statistics
        success: Whether the operation was successful
        include_recent_items: Whether to include recent items in email
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Get email configuration
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        username = os.getenv('SMTP_USERNAME')
        password = os.getenv('SMTP_PASSWORD')
        
        if not all([username, password]):
            print("❌ Email configuration missing")
            return False
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = username
        msg['To'] = email_address
        msg['Subject'] = f"Sentinel Intelligence Report - {'✅ Success' if success else '❌ Failed'}"
        
        # Build email body
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: {'#22D3EE' if success else '#EF4444'};">
                🛡️ Sentinel Intelligence Report
            </h2>
            
            <div style="background-color: {'#D1FAE5' if success else '#FEE2E2'}; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h3>📊 Summary</h3>
                <p><strong>Session ID:</strong> {session_id}</p>
                <p><strong>Status:</strong> {'✅ Successful' if success else '❌ Failed'}</p>
                <p><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                <p><strong>CVEs Found:</strong> {results.get('cves_found', 0)}</p>
                <p><strong>News Articles:</strong> {results.get('news_found', 0)}</p>
                <p><strong>Processing Time:</strong> {results.get('processing_time', 0):.2f} seconds</p>
            </div>
        """
        

        
        # Add recent items if successful
        if success:
            try:
                from db import get_items_by_session
                recent_items = get_items_by_session(session_id, limit=5)
                
                if recent_items['cves']:
                    body += """
                    <div style="margin: 20px 0;">
                        <h3>🔍 Recent CVEs Found</h3>
                        <ul style="list-style: none; padding: 0;">
                    """
                    for cve in recent_items['cves'][:3]:  # Show top 3
                        cve_id, title, severity, summary, created_at = cve
                        severity_color = {
                            'Critical': '#EF4444',
                            'High': '#F97316', 
                            'Medium': '#EAB308',
                            'Low': '#22C55E'
                        }.get(severity, '#6B7280')
                        
                        body += f"""
                        <li style="margin: 10px 0; padding: 10px; border-left: 4px solid {severity_color}; background-color: #F8FAFC;">
                            <strong>{cve_id}</strong> - {title}<br>
                            <span style="color: {severity_color}; font-weight: bold;">{severity}</span><br>
                            <small style="color: #6B7280;">{summary[:150]}{'...' if len(summary) > 150 else ''}</small>
                        </li>
                        """
                    body += "</ul></div>"
                
                if recent_items['news']:
                    body += """
                    <div style="margin: 20px 0;">
                        <h3>📰 Recent News Articles</h3>
                        <ul style="list-style: none; padding: 0;">
                    """
                    for news in recent_items['news'][:3]:  # Show top 3
                        title, source, summary, created_at = news
                        body += f"""
                        <li style="margin: 10px 0; padding: 10px; border-left: 4px solid #22D3EE; background-color: #F8FAFC;">
                            <strong>{title}</strong><br>
                            <small style="color: #6B7280;">Source: {source}</small><br>
                            <small style="color: #6B7280;">{summary[:150]}{'...' if len(summary) > 150 else ''}</small>
                        </li>
                        """
                    body += "</ul></div>"
            except Exception as e:
                print(f"⚠️ Error getting recent items for email: {e}")
        
        # Add error details if failed
        if not success:
            body += f"""
            <div style="background-color: #FEE2E2; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h3>❌ Error Details</h3>
                <p><strong>Error:</strong> {results.get('error', 'Unknown error')}</p>
            </div>
            """
        
        body += """
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #E5E7EB; color: #6B7280; font-size: 12px;">
                <p>This is an automated notification from Sentinel Intelligence Platform.</p>
                <p>Generated at: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC') + """</p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
        
        print(f"✅ Intelligence report email sent to {email_address}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send email: {str(e)}")
        return False

def send_error_notification(
    email_address: str,
    session_id: str,
    error: str
) -> bool:
    """
    Send error notification via email
    
    Args:
        email_address: Recipient email address
        session_id: Session identifier
        error: Error message
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Get email configuration from environment
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_username = os.getenv('SMTP_USERNAME')
        smtp_password = os.getenv('SMTP_PASSWORD')
        
        if not all([smtp_username, smtp_password]):
            print("⚠️ SMTP credentials not configured")
            return False
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🚨 Sentinel Intelligence Error - {session_id}"
        msg['From'] = smtp_username
        msg['To'] = email_address
        
        # Create HTML content
        html_content = _create_error_notification_html(session_id, error)
        msg.attach(MIMEText(html_content, 'html'))
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        
        print(f"✅ Error notification email sent to {email_address}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send error notification email: {e}")
        return False

def _create_intelligence_report_html(session_id: str, results: Dict[str, Any], success: bool) -> str:
    """Create HTML content for intelligence report"""
    
    cves_found = results.get('cves_found', 0)
    news_found = results.get('news_found', 0)
    total_results = results.get('total_results', 0)
    execution_time = results.get('execution_time_seconds', 0)
    
    status_icon = "✅" if success else "⚠️"
    status_text = "Completed Successfully" if success else "Completed with Issues"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
            .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .shield-icon {{ font-size: 48px; margin-bottom: 10px; }}
            .status {{ text-align: center; margin: 20px 0; padding: 15px; border-radius: 5px; }}
            .success {{ background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
            .warning {{ background-color: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }}
            .stats {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0; }}
            .stat-card {{ background-color: #f8f9fa; padding: 20px; border-radius: 5px; text-align: center; }}
            .stat-number {{ font-size: 24px; font-weight: bold; color: #007bff; }}
            .stat-label {{ color: #6c757d; margin-top: 5px; }}
            .footer {{ margin-top: 30px; text-align: center; color: #6c757d; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="shield-icon">🛡️</div>
                <h1>Sentinel Intelligence Report</h1>
                <p>Session ID: {session_id}</p>
            </div>
            
            <div class="status {'success' if success else 'warning'}">
                <h2>{status_icon} {status_text}</h2>
                <p>Report generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p UTC')}</p>
            </div>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number">{cves_found}</div>
                    <div class="stat-label">CVEs Found</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{news_found}</div>
                    <div class="stat-label">News Items</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{total_results}</div>
                    <div class="stat-label">Total Results</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{execution_time:.1f}s</div>
                    <div class="stat-label">Execution Time</div>
                </div>
            </div>
            
            <div style="margin-top: 30px; padding: 20px; background-color: #e9ecef; border-radius: 5px;">
                <h3>📊 Summary</h3>
                <p>Your Sentinel intelligence gathering system has automatically collected {total_results} new items from the past 3 days:</p>
                <ul>
                    <li><strong>{cves_found} CVEs</strong> - New vulnerability reports</li>
                    <li><strong>{news_found} News Items</strong> - Cybersecurity news and updates</li>
                </ul>
                <p>All data has been stored in your Supabase database and is ready for analysis.</p>
            </div>
            
            <div class="footer">
                <p>This is an automated report from your Sentinel Intelligence System.</p>
                <p>To view your data, visit your Sentinel dashboard.</p>
            </div>
        </div>
    </body>
    </html>
    """

def _create_error_notification_html(session_id: str, error: str) -> str:
    """Create HTML content for error notification"""
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
            .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .shield-icon {{ font-size: 48px; margin-bottom: 10px; }}
            .error {{ background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .footer {{ margin-top: 30px; text-align: center; color: #6c757d; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="shield-icon">🚨</div>
                <h1>Sentinel Intelligence Error</h1>
                <p>Session ID: {session_id}</p>
            </div>
            
            <div class="error">
                <h2>⚠️ Intelligence Gathering Failed</h2>
                <p><strong>Error:</strong> {error}</p>
                <p><strong>Time:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p UTC')}</p>
            </div>
            
            <div style="margin-top: 30px; padding: 20px; background-color: #fff3cd; border-radius: 5px;">
                <h3>🔧 Recommended Actions</h3>
                <ul>
                    <li>Check your Render logs for detailed error information</li>
                    <li>Verify your API keys and environment variables</li>
                    <li>Ensure your Supabase database is accessible</li>
                    <li>Check if your scraping sources are available</li>
                </ul>
            </div>
            
            <div class="footer">
                <p>This is an automated error notification from your Sentinel Intelligence System.</p>
                <p>Please investigate the issue to ensure continuous intelligence gathering.</p>
            </div>
        </div>
    </body>
    </html>
    """
