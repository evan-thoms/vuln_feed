# **Session Tracking Implementation - Production Deployment Guide**

## **Overview**

This guide covers the deployment of session tracking functionality that adds `session_id` and `created_at` columns to track when and how data was added to your Sentinel intelligence platform.

## **What's New**

### **Database Changes**
- **`session_id`**: Identifies which scrape run added each item
- **`created_at`**: Timestamp when item was added
- **Indexes**: For efficient querying by session and time

### **Session ID Format**
```
Format: YYYYMMDD_HHMMSS_[type]
Examples:
- 20250115_143022_scheduled  (automated run)
- 20250115_143022_manual     (user query)
- 20250115_143022_test       (testing)
- legacy                     (existing data)
```

### **Enhanced Features**
- **Email notifications** now include recent items found
- **Session tracking** for debugging and monitoring
- **Backward compatibility** with existing data

## **Pre-Deployment Checklist**

### **1. Backup Your Database**
```bash
# For Supabase (PostgreSQL)
pg_dump $DATABASE_URL > backup_before_session_tracking.sql

# For SQLite
cp articles.db articles_backup.db
```

### **2. Environment Variables**
Ensure these are set in Render:
```bash
# Existing variables (keep these)
OPENAI_API_KEY=your_openai_key
GROQ_API_KEY=your_groq_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Email variables (if not already set)
SENTINEL_NOTIFICATION_EMAIL=nadodude329@gmail.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=nadodude329@gmail.com
SMTP_PASSWORD=your_app_password
```

## **Deployment Steps**

### **Step 1: Local Testing**

1. **Run migration locally first**:
   ```bash
   cd backend
   python migrate_database.py
   ```

2. **Run comprehensive tests**:
   ```bash
   python test_session_tracking.py
   ```

3. **Test email functionality**:
   ```bash
   python quick_email_test.py
   ```

### **Step 2: Deploy to Production**

1. **Push code to Git repository**:
   ```bash
   git add .
   git commit -m "Add session tracking functionality"
   git push origin main
   ```

2. **Deploy to Render**:
   - Render will automatically deploy the updated code
   - Monitor the deployment logs for any errors

### **Step 3: Run Database Migration in Production**

1. **SSH into Render** (if needed) or use Render's shell:
   ```bash
   cd /opt/render/project/src
   python migrate_database.py
   ```

2. **Verify migration**:
   ```bash
   python test_session_tracking.py
   ```

### **Step 4: Test Production Deployment**

1. **Test manual trigger**:
   ```bash
   curl -X POST https://your-render-app.onrender.com/manual-trigger
   ```

2. **Check scheduler status**:
   ```bash
   curl https://your-render-app.onrender.com/scheduler-status
   ```

3. **Monitor logs** for any errors

## **What to Expect**

### **Email Notifications Now Include**:
```
🛡️ Sentinel Intelligence Report
📊 Summary
- Session ID: 20250115_143022_scheduled
- Status: ✅ Successful
- CVEs Found: 15
- News Articles: 8
- Processing Time: 45.2 seconds

🔍 Recent CVEs Found
• CVE-2024-1234 - Critical vulnerability in Apache
• CVE-2024-5678 - High severity issue in OpenSSL

📰 Recent News Articles
• Major cybersecurity breach reported
• New threat intelligence platform launched
```

### **Database Queries You Can Now Run**:
```sql
-- Get items from specific session
SELECT * FROM cves WHERE session_id = '20250115_143022_scheduled';

-- Get recent items (last 24 hours)
SELECT * FROM cves WHERE created_at >= NOW() - INTERVAL '24 hours';

-- Get session statistics
SELECT session_id, COUNT(*) FROM cves GROUP BY session_id ORDER BY COUNT(*) DESC;
```

## **Monitoring & Troubleshooting**

### **Check Migration Status**
```bash
# In production
python migrate_database.py
```

### **Monitor Logs**
- **Render logs**: Check for any deployment errors
- **Application logs**: Look for session tracking errors
- **Email logs**: Verify notifications are being sent

### **Common Issues & Solutions**

1. **Migration fails**:
   - Check database connection
   - Verify environment variables
   - Check if columns already exist

2. **Email not sending**:
   - Verify SMTP credentials
   - Check if Gmail App Password is correct
   - Ensure 2FA is enabled

3. **Session tracking not working**:
   - Check if database migration completed
   - Verify session_id is being generated
   - Check database indexes

### **Rollback Plan**

If something goes wrong:

1. **Restore database backup**:
   ```bash
   # For PostgreSQL
   psql $DATABASE_URL < backup_before_session_tracking.sql
   
   # For SQLite
   cp articles_backup.db articles.db
   ```

2. **Revert code**:
   ```bash
   git revert HEAD
   git push origin main
   ```

## **Performance Impact**

### **Database Performance**
- **Minimal impact**: New indexes improve query performance
- **Storage**: ~50 bytes per record for session tracking
- **Query performance**: Faster filtering by session and time

### **Application Performance**
- **No impact**: Session ID generation is negligible
- **Email**: Slightly larger emails with recent items
- **Memory**: Minimal additional memory usage

## **Security Considerations**

1. **Session IDs**: Don't contain sensitive information
2. **Database**: No additional security risks
3. **Email**: Same security as existing notifications

## **Future Enhancements**

With session tracking in place, you can now:

1. **Analytics dashboard**: Track scraping performance over time
2. **Duplicate detection**: Identify and handle duplicate runs
3. **Performance monitoring**: Track processing times by session
4. **Debugging tools**: Easily identify issues with specific runs

## **Support**

If you encounter issues:

1. **Check the logs** for specific error messages
2. **Run the test suite** to identify problems
3. **Verify environment variables** are correctly set
4. **Check database connectivity** and permissions

---

**Next Steps**: After successful deployment, monitor the first few scheduled runs to ensure everything works correctly, then adjust the schedule as needed.
