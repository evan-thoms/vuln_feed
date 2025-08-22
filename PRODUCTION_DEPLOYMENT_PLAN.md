# 🚀 CyberIntel Production Deployment Plan

## 📋 Overview
This plan outlines how to deploy your cybersecurity intelligence platform to production using free services.

## 🎯 Production Requirements

### **Current Architecture:**
- **Backend:** FastAPI + Celery + Redis + SQLite
- **Frontend:** Next.js React app
- **Database:** SQLite (needs upgrade for production)
- **Scheduling:** Celery Beat (weekly intelligence gathering)
- **Real-time:** WebSocket communication

## 🏗️ **Recommended Production Stack (100% Free)**

### **Option 1: Render + Supabase (Recommended)**
**Cost:** $0/month (completely free)

#### **Backend (Render)**
- **Service:** Render.com
- **Cost:** Free tier (750 hours/month, sleeps after inactivity)
- **Features:** Auto-deploy, environment variables, custom domains
- **Limitations:** Sleeps after inactivity (wake on request)

#### **Database (Supabase)**
- **Service:** Supabase.com
- **Cost:** Free tier (500MB database, 50,000 monthly active users)
- **Features:** PostgreSQL, real-time subscriptions, built-in auth
- **Migration:** SQLite → PostgreSQL

#### **Frontend (Vercel)**
- **Service:** Vercel.com
- **Cost:** Free tier (unlimited deployments)
- **Features:** Auto-deploy, CDN, custom domains

#### **Redis (Upstash)**
- **Service:** Upstash.com
- **Cost:** Free tier (10,000 requests/day)
- **Features:** Serverless Redis, pay-per-use

### **Option 2: Fly.io + Supabase (Alternative)**
**Cost:** $0/month (completely free)

#### **Backend (Fly.io)**
- **Service:** Fly.io
- **Cost:** Free tier (3 shared-cpu VMs, 3GB persistent volume)
- **Features:** Global deployment, auto-scaling
- **Great for:** Always-on services

#### **Database (Supabase)**
- **Service:** Supabase.com
- **Cost:** Free tier (500MB database, 50,000 monthly active users)
- **Features:** PostgreSQL, real-time subscriptions, auth

### **Option 3: Google Cloud Run + Supabase**
**Cost:** $0/month (completely free)

#### **Backend (Google Cloud Run)**
- **Service:** Google Cloud Run
- **Cost:** Free tier (2 million requests/month)
- **Features:** Serverless, auto-scaling, global deployment
- **Limits:** 360,000 vCPU-seconds, 180,000 GiB-seconds memory

#### **Database (Supabase)**
- **Service:** Supabase.com
- **Cost:** Free tier (500MB database, 50,000 monthly active users)
- **Features:** PostgreSQL, real-time subscriptions, auth

## 🔧 **Migration Steps**

### **Phase 1: Database Migration (SQLite → PostgreSQL)**

#### **1.1 Update Database Configuration**
```python
# backend/db.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Production database URL (Supabase PostgreSQL)
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///articles.db')

# Create engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

#### **1.2 Create Migration Script**
```python
# backend/migrate_db.py
import sqlite3
import psycopg2
from sqlalchemy import create_engine, text
import os

def migrate_sqlite_to_postgresql():
    """Migrate data from SQLite to PostgreSQL (Supabase)"""
    # Connect to SQLite
    sqlite_conn = sqlite3.connect('articles.db')
    
    # Connect to PostgreSQL (Supabase)
    postgres_engine = create_engine(os.getenv('DATABASE_URL'))
    
    # Migrate tables
    tables = ['raw_articles', 'cves', 'newsitems']
    
    for table in tables:
        # Get data from SQLite
        data = sqlite_conn.execute(f'SELECT * FROM {table}').fetchall()
        
        # Insert into PostgreSQL
        with postgres_engine.connect() as conn:
            for row in data:
                # Convert to proper format and insert
                pass
```

### **Phase 2: Environment Configuration**

#### **2.1 Environment Variables**
```bash
# .env.production
DATABASE_URL=postgresql://postgres:[password]@[host]:5432/postgres
REDIS_URL=redis://user:pass@host:port
OPENAI_API_KEY=your_openai_key
CELERY_BROKER_URL=redis://user:pass@host:port
CELERY_RESULT_BACKEND=redis://user:pass@host:port
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key
```

#### **2.2 Update Celery Configuration**
```python
# backend/celery/celery_config.py
import os

broker_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
result_backend = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
```

### **Phase 3: Production Optimizations**

#### **3.1 Add Health Checks**
```python
# backend/main.py
@app.get("/health")
async def health_check():
    """Production health check"""
    try:
        # Check database
        db_status = check_database_connection()
        
        # Check Redis
        redis_status = check_redis_connection()
        
        # Check Celery
        celery_status = check_celery_status()
        
        return {
            "status": "healthy" if all([db_status, redis_status, celery_status]) else "unhealthy",
            "database": db_status,
            "redis": redis_status,
            "celery": celery_status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

#### **3.2 Add Logging**
```python
# backend/logging_config.py
import logging
import sys

def setup_logging():
    """Configure production logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('app.log')
        ]
    )
```

#### **3.3 Add Rate Limiting**
```python
# backend/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/search")
@limiter.limit("10/minute")
async def search_intelligence(request: SearchRequest):
    # ... existing code
```

### **Phase 4: Deployment Scripts**

#### **4.1 Railway Deployment**
```yaml
# railway.toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "cd backend && python -m uvicorn main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "on_failure"
```

#### **4.2 Vercel Deployment**
```json
// vercel.json
{
  "buildCommand": "cd frontend && npm run build",
  "outputDirectory": "frontend/.next",
  "framework": "nextjs",
  "env": {
    "NEXT_PUBLIC_API_URL": "https://your-backend.railway.app"
  }
}
```

## 🚀 **Deployment Steps**

### **Step 1: Database Setup (Supabase)**
1. Create Supabase account at supabase.com
2. Create new project
3. Get connection string from Settings > Database
4. Run migration script
5. Update environment variables

### **Step 2: Backend Deployment (Render)**
1. Push code to GitHub
2. Connect Render to GitHub repo
3. Set environment variables in Render
4. Deploy

### **Step 3: Frontend Deployment (Vercel)**
1. Push frontend code to GitHub
2. Connect Vercel to GitHub repo
3. Set environment variables
4. Deploy

### **Step 4: Celery Setup**
1. Deploy Celery worker to Render
2. Configure Redis connection
3. Test weekly scheduling

## 📊 **Monitoring & Maintenance**

### **Free Monitoring Tools**
- **Uptime:** UptimeRobot (free tier)
- **Logs:** Render/Vercel built-in logging
- **Metrics:** Custom health check endpoints

### **Weekly Tasks**
- Review Celery logs
- Check database performance
- Monitor API usage
- Update dependencies

## 💰 **Cost Breakdown**

### **Monthly Costs (100% Free)**
- **Render Backend:** Free (750 hours/month)
- **Supabase Database:** Free (500MB, 50K users)
- **Vercel Frontend:** Free (unlimited deployments)
- **Upstash Redis:** Free (10K requests/day)
- **Total:** $0/month 🎉

### **Free Tier Limits**
- **Render:** 750 hours/month (sleeps when inactive)
- **Supabase:** 500MB database, 50K monthly active users
- **Vercel:** Unlimited deployments, 100GB bandwidth
- **Upstash:** 10,000 requests/day

## 🔒 **Security Considerations**

### **Environment Variables**
- Store all secrets in platform environment variables
- Never commit API keys to code
- Use different keys for dev/prod

### **API Security**
- Add rate limiting
- Implement CORS properly
- Add request validation

### **Database Security**
- Use connection pooling
- Implement proper indexing
- Regular backups (Supabase handles this)

## 🎯 **Next Steps**

1. **Set up Supabase database** and run migration
2. **Deploy backend** to Render with environment variables
3. **Deploy frontend** to Vercel with API URL configuration
4. **Test Celery scheduling** in production
5. **Set up monitoring** and alerts
6. **Configure custom domain** (optional)

## 📞 **Support**

- **Render:** Good documentation and community
- **Supabase:** Great support, documentation, and Discord
- **Vercel:** Extensive docs and community
- **Upstash:** Good documentation and support

## 🆓 **Why This Stack is Perfect**

1. **Completely Free:** $0/month cost
2. **Scalable:** Can upgrade when needed
3. **Simple:** Easy to deploy and maintain
4. **Reliable:** Production-ready services
5. **Modern:** Latest technologies and features

## 🚀 **Quick Setup Guide for Render**

### **Render Deployment Steps:**
1. **Sign up** at render.com
2. **Connect GitHub** repository
3. **Create Web Service** from your backend code
4. **Set environment variables:**
   - `DATABASE_URL` (from Supabase)
   - `REDIS_URL` (from Upstash)
   - `OPENAI_API_KEY`
   - `CELERY_BROKER_URL`
   - `CELERY_RESULT_BACKEND`
5. **Deploy** and get your backend URL
6. **Update frontend** with new backend URL

### **Render Free Tier Benefits:**
- **750 hours/month** (more than Railway had)
- **Auto-deploy** from GitHub
- **Custom domains** support
- **Environment variables** management
- **Built-in logging** and monitoring

This plan provides a production-ready deployment with **zero cost** and maximum reliability!
