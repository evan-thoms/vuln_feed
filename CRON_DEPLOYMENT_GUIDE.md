# Sentinel Intelligence Cron Job Deployment Guide

## Overview
This guide covers deploying the automated intelligence gathering system using Render's cron jobs instead of Celery/Redis. This solution is optimized for Render's free tier and provides both testing (30-minute) and production (3-day) scheduling options.

## Architecture
- **Backend**: FastAPI on Render (Free Tier)
- **Database**: Supabase (Free Tier)
- **Scheduler**: Render Cron Jobs (Free Tier)
- **Notifications**: Email via SMTP (Gmail)
- **Frontend**: Next.js on Vercel (Free Tier)

## Key Features
- ✅ **Dual Scheduling**: 30-minute testing vs 3-day production
- ✅ **Email Notifications**: Success/error reports
- ✅ **Comprehensive Logging**: Separate logs for testing/production
- ✅ **Manual Triggers**: API endpoints for manual execution
- ✅ **Health Monitoring**: Status endpoints and health checks
- ✅ **Free Tier Optimized**: No Redis/Celery dependencies

## Pre-Deployment Setup

### 1. Environment Variables
Set these in your Render dashboard:

```bash
# Required for core functionality
OPENAI_API_KEY=your_openai_key
GROQ_API_KEY=your_groq_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Email notifications (optional but recommended)
SENTINEL_NOTIFICATION_EMAIL=your_email@example.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# Cron job configuration
CRON_SCHEDULE_TYPE=production  # or "testing"
SEND_TEST_NOTIFICATIONS=false  # set to "true" to get emails for testing runs
```

### 2. Gmail App Password Setup
1. Enable 2-factor authentication on your Gmail account
2. Generate an App Password:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate password for "Mail"
3. Use the generated password as `SMTP_PASSWORD`

## Deployment Steps

### Step 1: Local Testing
```bash
# Test the cron scheduler locally
cd backend
python test_scheduler.py

# Test individual components
python cron_scheduler.py  # This will run with CRON_SCHEDULE_TYPE env var
```

### Step 2: Deploy to Render
1. **Push your code** to your Git repository
2. **Connect to Render**:
   - Go to Render dashboard
   - Click "New +" → "Blueprint"
   - Connect your repository
   - Render will automatically detect `render.yaml`

3. **Verify Services Created**:
   - `sentinel-intelligence-api` (Web Service)
   - `sentinel-intelligence-cron` (Cron Job)

### Step 3: Configure Environment Variables
In Render dashboard, for both services:
1. Go to each service's "Environment" tab
2. Add all environment variables listed above
3. Set `CRON_SCHEDULE_TYPE=testing` initially for testing

### Step 4: Test the Deployment
```bash
# Test the web service
curl https://your-app.onrender.com/health

# Test manual cron trigger (testing mode)
curl -X POST https://your-app.onrender.com/test-cron

# Check cron status
curl https://your-app.onrender.com/cron-status
```

## Scheduling Configuration

### Testing Phase (30-minute intervals)
1. In Render dashboard, go to the cron job service
2. Set schedule to: `*/30 * * * *` (every 30 minutes)
3. Set environment variable: `CRON_SCHEDULE_TYPE=testing`
4. Set `SEND_TEST_NOTIFICATIONS=true` if you want email notifications

### Production Phase (3-day intervals)
1. In Render dashboard, go to the cron job service
2. Set schedule to: `0 0 */3 * *` (every 3 days at midnight UTC)
3. Set environment variable: `CRON_SCHEDULE_TYPE=production`
4. Set `SEND_TEST_NOTIFICATIONS=false`

## Monitoring & Maintenance

### Logs
- **Web Service**: Check Render logs for API endpoints
- **Cron Job**: Check Render logs for scheduled executions
- **Application Logs**: 
  - `scheduled_intelligence_testing.log` (30-minute runs)
  - `scheduled_intelligence_production.log` (3-day runs)
  - `cron_scheduler.log` (general scheduler logs)

### API Endpoints
```bash
# Health check
GET /health

# Manual triggers
POST /test-cron                    # Trigger testing run
POST /trigger-production-cron      # Trigger production run
POST /manual-trigger              # Legacy endpoint (still works)

# Status monitoring
GET /cron-status                  # Cron job status and recent executions
GET /scheduler-status             # Legacy status endpoint

# Data endpoints
POST /search                      # Full intelligence gathering
POST /search-minimal              # Existing data only
GET /cache                        # Cached data only
```

### Email Notifications
You'll receive emails for:
- ✅ **Successful runs**: Summary with CVEs found, processing time
- ❌ **Failed runs**: Error details and recommended actions
- 📊 **Performance metrics**: Processing speed, success rates

## Troubleshooting

### Common Issues

1. **Cron job not running**
   ```bash
   # Check Render cron job logs
   # Verify environment variables are set
   # Check if free tier limits are exceeded
   ```

2. **Email not sending**
   ```bash
   # Verify SMTP credentials
   # Check if Gmail App Password is correct
   # Ensure 2FA is enabled on Gmail
   ```

3. **Database connection issues**
   ```bash
   # Test Supabase connection
   curl https://your-app.onrender.com/test-supabase
   
   # Verify Supabase credentials
   # Check if database is accessible from Render
   ```

4. **API rate limits**
   ```bash
   # Monitor OpenAI/Groq usage
   # Check if free tier limits are exceeded
   # Consider reducing max_results for testing
   ```

### Debug Commands
```bash
# Test scheduler locally
cd backend
python test_scheduler.py

# Test email configuration
python -c "from utils.email_notifications import test_email_configuration; test_email_configuration()"

# Check logs
tail -f scheduled_intelligence_testing.log
tail -f scheduled_intelligence_production.log
```

## Performance Optimization

### Free Tier Limits
- **Render**: 750 hours/month for web services, 100 hours/month for cron jobs
- **Supabase**: 500MB database, 50,000 monthly active users
- **OpenAI**: Rate limits apply
- **Gmail**: 500 emails/day limit

### Optimization Tips
1. **Testing Mode**: Uses smaller batches (15 results vs 30)
2. **Focused Severity**: Testing only looks for Critical/High CVEs
3. **Shorter Time Range**: Testing looks at last 24 hours vs 3 days
4. **Conditional Emails**: Testing emails only sent if explicitly enabled

## Migration from Celery

### What Changed
- ❌ Removed: Celery, Redis, Beat scheduler
- ✅ Added: Render cron jobs, enhanced logging, email notifications
- ✅ Improved: Error handling, monitoring, configuration flexibility

### Migration Steps
1. **Deploy new system** alongside existing one
2. **Test thoroughly** with 30-minute schedule
3. **Switch to production** schedule when confident
4. **Remove old Celery services** from Render
5. **Update monitoring** to use new endpoints

## Security Considerations

1. **Environment Variables**: Never commit secrets to Git
2. **Email Security**: Use App Passwords, not regular passwords
3. **API Keys**: Rotate keys regularly
4. **Database**: Use connection pooling and prepared statements
5. **Logs**: Don't log sensitive information

## Scaling Considerations

When moving beyond free tier:
1. **Database**: Consider dedicated Supabase plan
2. **Monitoring**: Add proper monitoring and alerting
3. **Storage**: Consider dedicated storage for logs
4. **Performance**: Optimize scraping and processing

## Support

For issues:
1. Check Render documentation
2. Review application logs
3. Test components individually
4. Verify environment variables
5. Check free tier usage limits

---

## Quick Start Checklist

- [ ] Set up environment variables in Render
- [ ] Configure Gmail App Password
- [ ] Deploy using `render.yaml`
- [ ] Test with 30-minute schedule (`CRON_SCHEDULE_TYPE=testing`)
- [ ] Verify email notifications work
- [ ] Monitor first few runs
- [ ] Switch to production schedule (`CRON_SCHEDULE_TYPE=production`)
- [ ] Set up monitoring and alerting

**Next Steps**: After deployment, monitor the first few runs to ensure everything works correctly, then adjust the schedule or parameters as needed.
