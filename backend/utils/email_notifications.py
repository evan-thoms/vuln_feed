"""
Email notification utilities for Sentinel Intelligence Gathering
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Any, Optional

def send_intelligence_report(
    email_address: str,
    session_id: str,
    results: Dict[str, Any],
    success: bool = True,
    schedule_type: str = "production"
) -> bool:
    """
    Send intelligence gathering report via email
    
    Args:
        email_address: Recipient email address
        session_id: Session identifier
        results: Results dictionary from intelligence gathering
        success: Whether the operation was successful
        schedule_type: "testing" or "production"
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Get SMTP configuration from environment
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_username = os.getenv('SMTP_USERNAME')
        smtp_password = os.getenv('SMTP_PASSWORD')
        
        if not all([smtp_username, smtp_password]):
            print("⚠️ SMTP credentials not configured")
            return False
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = smtp_username
        msg['To'] = email_address
        msg['Subject'] = f"🔒 Sentinel Intelligence Report - {schedule_type.title()} Run"
        
        # Create email body
        body = _create_report_body(session_id, results, success, schedule_type)
        msg.attach(MIMEText(body, 'html'))
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        
        print(f"✅ Intelligence report email sent to {email_address}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send intelligence report email: {e}")
        return False

def send_error_notification(
    email_address: str,
    session_id: str,
    error: str,
    schedule_type: str = "production"
) -> bool:
    """
    Send error notification via email
    
    Args:
        email_address: Recipient email address
        session_id: Session identifier
        error: Error message
        schedule_type: "testing" or "production"
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Get SMTP configuration from environment
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_username = os.getenv('SMTP_USERNAME')
        smtp_password = os.getenv('SMTP_PASSWORD')
        
        if not all([smtp_username, smtp_password]):
            print("⚠️ SMTP credentials not configured")
            return False
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = smtp_username
        msg['To'] = email_address
        msg['Subject'] = f"❌ Sentinel Intelligence Error - {schedule_type.title()} Run"
        
        # Create error email body
        body = _create_error_body(session_id, error, schedule_type)
        msg.attach(MIMEText(body, 'html'))
        
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

def _create_report_body(
    session_id: str,
    results: Dict[str, Any],
    success: bool,
    schedule_type: str
) -> str:
    """Create HTML email body for intelligence report"""
    
    cves_found = results.get('cves_found', 0)
    news_found = results.get('news_found', 0)
    total_results = results.get('total_results', 0)
    execution_time = results.get('execution_time_seconds', 0)
    
    status_emoji = "✅" if success else "⚠️"
    status_text = "SUCCESS" if success else "PARTIAL SUCCESS"
    
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background-color: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
            .content {{ margin: 20px 0; }}
            .stats {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }}
            .footer {{ color: #7f8c8d; font-size: 12px; margin-top: 20px; }}
            .success {{ color: #27ae60; }}
            .warning {{ color: #f39c12; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔒 Sentinel Intelligence Gathering Report</h1>
            <p><strong>Schedule:</strong> {schedule_type.title()} | <strong>Session:</strong> {session_id}</p>
        </div>
        
        <div class="content">
            <h2>{status_emoji} {status_text}</h2>
            <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            
            <div class="stats">
                <h3>📊 Intelligence Summary</h3>
                <ul>
                    <li><strong>CVEs Found:</strong> {cves_found}</li>
                    <li><strong>News Items:</strong> {news_found}</li>
                    <li><strong>Total Results:</strong> {total_results}</li>
                    <li><strong>Execution Time:</strong> {execution_time:.1f} seconds</li>
                </ul>
            </div>
            
            <div class="stats">
                <h3>🎯 Performance Metrics</h3>
                <ul>
                    <li><strong>Processing Speed:</strong> {total_results/execution_time:.1f} items/second</li>
                    <li><strong>Success Rate:</strong> {"100%" if success else "Partial"}</li>
                </ul>
            </div>
        </div>
        
        <div class="footer">
            <p>This is an automated report from your Sentinel Intelligence Gathering system.</p>
            <p>Next scheduled run: {"30 minutes" if schedule_type == "testing" else "3 days"}</p>
        </div>
    </body>
    </html>
    """
    
    return html_body

def _create_error_body(
    session_id: str,
    error: str,
    schedule_type: str
) -> str:
    """Create HTML email body for error notification"""
    
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background-color: #e74c3c; color: white; padding: 20px; border-radius: 5px; }}
            .content {{ margin: 20px 0; }}
            .error {{ background-color: #fdf2f2; border: 1px solid #f5c6cb; padding: 15px; border-radius: 5px; margin: 10px 0; }}
            .footer {{ color: #7f8c8d; font-size: 12px; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>❌ Sentinel Intelligence Gathering Error</h1>
            <p><strong>Schedule:</strong> {schedule_type.title()} | <strong>Session:</strong> {session_id}</p>
        </div>
        
        <div class="content">
            <h2>🚨 Error Occurred</h2>
            <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            
            <div class="error">
                <h3>Error Details</h3>
                <pre>{error}</pre>
            </div>
            
            <h3>🔧 Recommended Actions</h3>
            <ul>
                <li>Check the application logs for more details</li>
                <li>Verify all environment variables are set correctly</li>
                <li>Check database connectivity</li>
                <li>Verify API keys are valid and have sufficient credits</li>
                <li>Monitor the next scheduled run</li>
            </ul>
        </div>
        
        <div class="footer">
            <p>This is an automated error notification from your Sentinel Intelligence Gathering system.</p>
            <p>Next scheduled run: {"30 minutes" if schedule_type == "testing" else "3 days"}</p>
        </div>
    </body>
    </html>
    """
    
    return html_body

def test_email_configuration() -> bool:
    """
    Test email configuration by sending a test email
    
    Returns:
        bool: True if test email sent successfully, False otherwise
    """
    try:
        email_address = os.getenv('SENTINEL_NOTIFICATION_EMAIL')
        if not email_address:
            print("❌ SENTINEL_NOTIFICATION_EMAIL not configured")
            return False
        
        # Create test results
        test_results = {
            'cves_found': 5,
            'news_found': 3,
            'total_results': 8,
            'execution_time_seconds': 45.2
        }
        
        success = send_intelligence_report(
            email_address=email_address,
            session_id="test_session",
            results=test_results,
            success=True,
            schedule_type="testing"
        )
        
        if success:
            print("✅ Email configuration test successful")
        else:
            print("❌ Email configuration test failed")
        
        return success
        
    except Exception as e:
        print(f"❌ Email configuration test error: {e}")
        return False
