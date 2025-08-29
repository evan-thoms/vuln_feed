# Render Cron Job Deployment Guide

This guide will help you set up automated intelligence gathering on Render using cron jobs.

## Step 1: Create the Cron Service

1. **Go to your Render Dashboard**
2. **Click "New" → "Cron Job"**
3. **Configure the service:**

```
Name: sentinel-intelligence-cron
Environment: Python 3
Region: Choose closest to you
Branch: main (or your deployment branch)
```

## Step 2: Configure Build Settings

```
Build Command: pip install -r requirements.txt
Start Command: python backend/cron_scheduler.py
```

## Step 3: Set Environment Variables

Add these environment variables to your Render cron service:

### Required Variables:
```
CRON_SCHEDULE_TYPE=production
OPENAI_API_KEY=your-openai-api-key
```

### Optional Variables:
```
SENTINEL_NOTIFICATION_EMAIL=your-email@example.com
SEND_TEST_NOTIFICATIONS=false
```

### Database Variables (if using Supabase):
```
DATABASE_URL=your-supabase-connection-string
```

## Step 4: Set Cron Schedule

In Render, set the cron schedule to:
```
*/30 * * * *  # Every 30 minutes for testing
```

Or for production:
```
0 */6 * * *  # Every 6 hours (00:00, 06:00, 12:00, 18:00)
```

## Step 5: Deploy and Test

1. **Deploy the cron service**
2. **Check the logs** to ensure it's working
3. **Monitor the first few runs** to verify everything is working

## Step 6: Optional - Create Multiple Cron Jobs

You can create separate cron jobs for different schedules:

### Testing Cron Job (Frequent):
- **Name**: `sentinel-intelligence-testing`
- **Schedule**: `*/30 * * * *` (every 30 minutes)
- **Environment Variable**: `CRON_SCHEDULE_TYPE=testing`

### Production Cron Job (Less Frequent):
- **Name**: `sentinel-intelligence-production`
- **Schedule**: `0 */6 * * *` (every 6 hours)
- **Environment Variable**: `CRON_SCHEDULE_TYPE=production`

## Monitoring and Troubleshooting

### Check Logs
- Go to your cron service in Render
- Click on "Logs" tab
- Look for execution logs

### Common Issues

1. **Import Errors**: Make sure all dependencies are in `requirements.txt`
2. **Database Connection**: Verify `DATABASE_URL` is set correctly
3. **API Keys**: Ensure `OPENAI_API_KEY` is valid
4. **File Paths**: Cron jobs run from the project root, so use `backend/cron_scheduler.py`

### Log Format
The cron job will log:
- Start time and session ID
- Working directory and Python executable
- Execution parameters
- Results (CVEs found, news found, execution time)
- Success/failure status

## Expected Output

Successful execution should show:
```
🔄 Starting 6-hour production intelligence gathering - Session: render_cron_20250829_120000
📁 Working directory: /opt/render/project/src
🐍 Python executable: /opt/render/project/src/.venv/bin/python
📊 Cron job parameters: {'content_type': 'both', 'severity': ['Critical', 'High', 'Medium', 'Low'], 'days_back': 3, 'max_results': 30, 'output_format': 'json'}
✅ 6-hour production intelligence gathering completed: 15 CVEs, 12 news items
⏱️ Execution time: 45.23 seconds
✅ Cron job completed successfully
```

## Cost Considerations

- **Free Tier**: 750 hours/month (sufficient for 30-minute cron jobs)
- **Paid Tier**: $7/month for unlimited usage
- **Monitor Usage**: Check Render dashboard for usage statistics

## Security Notes

- Environment variables are encrypted in Render
- Never commit API keys to your repository
- Use Render's secrets management for sensitive data
- Consider using service-specific API keys for the cron job

## Troubleshooting Commands

If you need to debug locally:

```bash
# Test the cron scheduler locally
cd backend
python cron_scheduler.py

# Check environment variables
echo $CRON_SCHEDULE_TYPE
echo $OPENAI_API_KEY

# Test database connection
python -c "from db import init_db; init_db(); print('Database connection successful')"
```
