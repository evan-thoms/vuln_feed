# Sentinel Intelligence Scheduler - Deployment Guide

## Overview
This guide covers deploying the automated intelligence gathering scheduler that runs every 3 days to collect CVEs and news articles.

## Architecture
- **Backend**: FastAPI on Render (Free Tier)
- **Database**: Supabase (Free Tier)
- **Scheduler**: Render Cron Jobs (Free Tier)
- **Notifications**: Email via SMTP
- **Frontend**: Next.js on Vercel (Free Tier)

## Pre-Deployment Checklist

### 1. Environment Variables Setup
Add these to your Render environment variables:

```bash
# Existing variables (keep these)
OPENAI_API_KEY=your_openai_key
GROQ_API_KEY=your_groq_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# New variables for scheduling
SENTINEL_NOTIFICATION_EMAIL=your_email@example.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

### 2. Email Setup (Gmail Example)
1. Enable 2-factor authentication on your Gmail account
2. Generate an App Password:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate password for "Mail"
3. Use the generated password as `SMTP_PASSWORD`

## Deployment Steps

### Step 1: Update Backend Code
1. Ensure all new files are committed:
   - `backend/cron_scheduler.py`
   - `backend/utils/email_notifications.py`
   - `backend/test_scheduler.py`
   - `render.yaml`

2. Update existing files:
   - `backend/main.py` (new endpoints)
   - `requirements.txt` (email dependencies)

### Step 2: Deploy to Render
1. Push code to your Git repository
2. In Render dashboard:
   - Connect your repository
   - Deploy the web service
   - Add the cron job service

### Step 3: Configure Cron Job
1. In Render dashboard, go to the cron job service
2. Set schedule: `0 0 */3 * *` (every 3 days at midnight UTC)
3. Ensure environment variables are synced

### Step 4: Test the Setup
Run the test script locally first:
```bash
cd backend
python test_scheduler.py
```

## Monitoring & Maintenance

### Logs
- **Web Service**: Check Render logs for API endpoints
- **Cron Job**: Check Render logs for scheduled executions
- **Application**: Check `scheduled_intelligence.log` for detailed execution logs

### Manual Operations
- **Trigger manually**: `POST /manual-trigger`
- **Check status**: `GET /scheduler-status`
- **View logs**: Check Render dashboard or log files

### Email Notifications
You'll receive emails for:
- ✅ Successful intelligence gathering runs
- ❌ Failed runs with error details
- 📊 Summary statistics (CVEs found, processing time)

## Troubleshooting

### Common Issues

1. **Cron job not running**
   - Check Render cron job logs
   - Verify environment variables are set
   - Check if free tier limits are exceeded

2. **Email not sending**
   - Verify SMTP credentials
   - Check if Gmail App Password is correct
   - Ensure 2FA is enabled on Gmail

3. **Database connection issues**
   - Verify Supabase credentials
   - Check if database is accessible from Render

4. **API rate limits**
   - Monitor OpenAI/Groq usage
   - Check if free tier limits are exceeded

### Debug Commands
```bash
# Test scheduler locally
cd backend
python cron_scheduler.py

# Test email notifications
python -c "from utils.email_notifications import send_intelligence_report; print('Email test')"

# Check logs
tail -f scheduled_intelligence.log
```

## Performance Considerations

### Free Tier Limits
- **Render**: 750 hours/month for web services, 100 hours/month for cron jobs
- **Supabase**: 500MB database, 50,000 monthly active users
- **OpenAI**: Rate limits apply
- **Gmail**: 500 emails/day limit

### Optimization Tips
1. **Batch processing**: Process multiple sources in parallel
2. **Caching**: Cache API responses when possible
3. **Error handling**: Implement retry logic for failed requests
4. **Logging**: Keep logs concise to avoid storage issues

## Security Considerations

1. **Environment Variables**: Never commit secrets to Git
2. **Email Security**: Use App Passwords, not regular passwords
3. **API Keys**: Rotate keys regularly
4. **Database**: Use connection pooling and prepared statements

## Scaling Considerations

When moving beyond free tier:
1. **Redis**: Add for better task queuing
2. **Celery**: Implement for distributed task processing
3. **Monitoring**: Add proper monitoring and alerting
4. **Database**: Consider dedicated database instance

## Support

For issues:
1. Check Render documentation
2. Review application logs
3. Test components individually
4. Verify environment variables

---

**Next Steps**: After deployment, monitor the first few runs to ensure everything works correctly, then adjust the schedule or parameters as needed.
