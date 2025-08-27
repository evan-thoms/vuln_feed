#!/usr/bin/env python3
"""
Local Email Test Script for Sentinel Scheduler
Test email notifications before deploying to production
"""

import os
import sys
from datetime import datetime

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_email_configuration():
    """Test email configuration with user input"""
    print("📧 Sentinel Email Configuration Test")
    print("=" * 50)
    
    # Get email configuration from user
    print("\nPlease provide your Gmail configuration:")
    
    email_address = input("Gmail address (nadodude329@gmail.com): ").strip()
    if not email_address:
        email_address = "nadodude329@gmail.com"
    
    app_password = input("App Password (16 characters): ").strip()
    if not app_password:
        print("❌ App Password is required!")
        return False
    
    # Test email configuration
    try:
        from utils.email_notifications import send_intelligence_report
        
        print(f"\n🧪 Testing email configuration...")
        print(f"From: {email_address}")
        print(f"To: {email_address}")
        
        # Send test email
        result = send_intelligence_report(
            email_address=email_address,
            session_id="test_local_" + datetime.now().strftime("%Y%m%d_%H%M%S"),
            results={
                'cves_found': 15,
                'news_found': 8,
                'processing_time': 45.2,
                'status': 'Test run completed successfully'
            },
            success=True
        )
        
        if result:
            print("✅ Email test successful! Check your inbox.")
            return True
        else:
            print("❌ Email test failed!")
            return False
            
    except Exception as e:
        print(f"❌ Email test error: {str(e)}")
        return False

def save_configuration():
    """Save email configuration to .env file"""
    print("\n💾 Save configuration to .env file?")
    save = input("Save configuration (y/n): ").strip().lower()
    
    if save == 'y':
        email_address = input("Gmail address: ").strip()
        app_password = input("App Password: ").strip()
        
        env_content = f"""# Email Configuration for Sentinel Scheduler
SENTINEL_NOTIFICATION_EMAIL={email_address}
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME={email_address}
SMTP_PASSWORD={app_password}
"""
        
        with open('.env', 'a') as f:
            f.write(env_content)
        
        print("✅ Configuration saved to .env file")
        print("⚠️  Remember to add these variables to Render environment variables for production!")

def main():
    """Main test function"""
    print("🚀 Sentinel Email Configuration Test")
    print("This will test email notifications before production deployment\n")
    
    # Test email configuration
    success = test_email_configuration()
    
    if success:
        print("\n🎉 Email test successful!")
        save_configuration()
        print("\n📋 Next steps:")
        print("1. Add environment variables to Render dashboard")
        print("2. Deploy the updated code")
        print("3. Test the manual trigger endpoint")
    else:
        print("\n❌ Email test failed!")
        print("Please check your configuration and try again.")

if __name__ == "__main__":
    main()
