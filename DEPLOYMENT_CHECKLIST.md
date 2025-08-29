# Deployment Checklist - Sentinel Intelligence Cron Job

## Pre-Deployment Checklist

### ✅ Code Changes Completed
- [x] Enhanced `cron_scheduler.py` with dual scheduling modes
- [x] Created `email_notifications.py` with HTML templates
- [x] Updated `main.py` with new cron endpoints
- [x] Created `render.yaml` for Render deployment
- [x] Updated `requirements.txt` (removed Celery/Redis)
- [x] Created comprehensive test suite
- [x] Removed old Celery files
- [x] All tests passing locally

### ✅ Files Ready for Deployment
- [x] `backend/cron_scheduler.py` - Enhanced scheduler
- [x] `backend/utils/email_notifications.py` - Email system
- [x] `backend/main.py` - Updated API endpoints
- [x] `backend/test_scheduler.py` - Test suite
- [x] `render.yaml` - Render configuration
- [x] `requirements.txt` - Updated dependencies
- [x] `CRON_DEPLOYMENT_GUIDE.md` - Deployment guide
- [x] `IMPLEMENTATION_SUMMARY.md` - Implementation summary

## Deployment Steps

### Step 1: Git Repository
- [ ] Commit all changes to Git
- [ ] Push to your repository
- [ ] Verify all files are in the repository

### Step 2: Render Setup
- [ ] Go to Render dashboard
- [ ] Click "New +" → "Blueprint"
- [ ] Connect your repository
- [ ] Verify `render.yaml` is detected
- [ ] Deploy both services:
  - `sentinel-intelligence-api` (Web Service)
  - `sentinel-intelligence-cron` (Cron Job)

### Step 3: Environment Variables
Set these in Render dashboard for both services:

#### Required Variables
- [ ] `OPENAI_API_KEY` - Your OpenAI API key
- [ ] `GROQ_API_KEY` - Your Groq API key
- [ ] `SUPABASE_URL` - Your Supabase URL
- [ ] `SUPABASE_KEY` - Your Supabase key

#### Email Variables (Optional but Recommended)
- [ ] `SENTINEL_NOTIFICATION_EMAIL` - Your email address
- [ ] `SMTP_SERVER` - `smtp.gmail.com`
- [ ] `SMTP_PORT` - `587`
- [ ] `SMTP_USERNAME` - Your Gmail address
- [ ] `SMTP_PASSWORD` - Your Gmail App Password

#### Cron Configuration
- [ ] `CRON_SCHEDULE_TYPE` - Set to `testing` initially
- [ ] `SEND_TEST_NOTIFICATIONS` - Set to `true` for testing

### Step 4: Gmail App Password Setup
- [ ] Enable 2-factor authentication on Gmail
- [ ] Generate App Password for "Mail"
- [ ] Use App Password as `SMTP_PASSWORD`

### Step 5: Testing Phase (30-minute intervals)
- [ ] Set cron job schedule to: `*/30 * * * *`
- [ ] Set `CRON_SCHEDULE_TYPE=testing`
- [ ] Set `SEND_TEST_NOTIFICATIONS=true`
- [ ] Wait for first execution (up to 30 minutes)
- [ ] Check logs for successful execution
- [ ] Verify email notifications are received

### Step 6: Production Phase (3-day intervals)
- [ ] Set cron job schedule to: `0 0 */3 * *`
- [ ] Set `CRON_SCHEDULE_TYPE=production`
- [ ] Set `SEND_TEST_NOTIFICATIONS=false`
- [ ] Monitor first few executions

## Verification Commands

### Health Check
```bash
curl https://your-app.onrender.com/health
```

### Manual Testing
```bash
# Test cron job (testing mode)
curl -X POST https://your-app.onrender.com/test-cron

# Production cron job
curl -X POST https://your-app.onrender.com/trigger-production-cron

# Check status
curl https://your-app.onrender.com/cron-status
```

### Database Test
```bash
curl https://your-app.onrender.com/test-supabase
```

## Monitoring Checklist

### After Deployment
- [ ] Web service is running and accessible
- [ ] Cron job service is created and scheduled
- [ ] Environment variables are set correctly
- [ ] First cron execution completes successfully
- [ ] Log files are created
- [ ] Email notifications are received (if configured)

### Ongoing Monitoring
- [ ] Check Render logs regularly
- [ ] Monitor email notifications
- [ ] Verify database connectivity
- [ ] Check API rate limits
- [ ] Monitor free tier usage

## Troubleshooting

### Common Issues
- [ ] **Cron not running**: Check Render cron job logs
- [ ] **Email not sending**: Verify SMTP credentials
- [ ] **Database errors**: Check Supabase connectivity
- [ ] **API errors**: Verify API keys and rate limits

### Debug Commands
```bash
# Test locally
cd backend
python test_scheduler.py

# Check logs
tail -f scheduled_intelligence_testing.log
tail -f scheduled_intelligence_production.log
```

## Success Criteria

### Testing Phase
- [ ] Cron job runs every 30 minutes
- [ ] Collects 15 results (CVEs + news)
- [ ] Focuses on Critical/High severity
- [ ] Sends email notifications
- [ ] Logs execution details

### Production Phase
- [ ] Cron job runs every 3 days
- [ ] Collects 30 results (CVEs + news)
- [ ] Includes all severity levels
- [ ] Sends email notifications
- [ ] Maintains stable performance

## Rollback Plan

If issues occur:
1. **Immediate**: Disable cron job in Render dashboard
2. **Investigate**: Check logs and error messages
3. **Fix**: Update code and redeploy
4. **Test**: Re-enable with testing schedule
5. **Monitor**: Verify stability before production

## Support Resources

- [ ] `CRON_DEPLOYMENT_GUIDE.md` - Detailed deployment guide
- [ ] `IMPLEMENTATION_SUMMARY.md` - Implementation details
- [ ] Render documentation
- [ ] Application logs
- [ ] Test suite (`test_scheduler.py`)

---

**Status**: ✅ **Ready for Deployment**

All components have been implemented, tested, and validated. The system is ready for deployment to Render's free tier with comprehensive monitoring and error handling.
