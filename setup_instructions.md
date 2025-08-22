# CyberIntel - Cybersecurity Intelligence Platform

A modern, agentic cybersecurity vulnerability and news collector with a sleek React frontend and FastAPI backend.

## Architecture

```
React/Next.js Frontend ↔ FastAPI Backend ↔ LangChain Tools ↔ Scrapers (EN/CN/RU)
```

## Features

- 🔍 **Multi-language Intelligence**: Scrapes English, Chinese, and Russian sources
- 🚨 **CVE Tracking**: Real-time vulnerability discovery and classification
- 📰 **News Aggregation**: Cybersecurity news with intelligent filtering
- 🎯 **Smart Filtering**: Filter by severity, content type, and date range
- 📊 **Real-time Processing**: Live status updates during search execution
- 🌐 **Modern UI**: Sleek, responsive interface with dark theme

## Quick Start

### Backend Setup

1. **Install Python dependencies:**
```bash
cd backend/
pip install -r requirements.txt
```

2. **Set up your existing modules:**
   - Ensure your `models.py`, `tools.py`, `scrapers/`, `classify.py`, and `db.py` are in the backend directory
   - Update import paths in `main.py` if needed

3. **Run FastAPI server:**
```bash
uvicorn main:app --reload --port 8000
```

### Frontend Setup

1. **Install Node.js dependencies:**
```bash
cd frontend/
npm install
```

2. **Configure Tailwind CSS:**
Create `tailwind.config.js`:
```javascript
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

3. **Create `postcss.config.js`:**
```javascript
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

4. **Add to `app/globals.css`:**
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

5. **Replace `app/page.tsx` with the React component provided**

6. **Run development server:**
```bash
npm run dev
```

## Project Structure

```
cyberintel/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── requirements.txt     # Python dependencies
│   ├── models.py           # Your existing data models
│   ├── tools.py            # Your existing LangChain tools
│   ├── scrapers/           # Your scraper modules
│   ├── classify.py         # Your classification logic
│   └── db.py              # Database operations
├── frontend/
│   ├── package.json        # Node.js dependencies
│   ├── next.config.js      # Next.js configuration
│   ├── tailwind.config.js  # Tailwind CSS config
│   └── app/
│       ├── page.tsx        # Main React component
│       └── globals.css     # Global styles
└── README.md
```

## API Endpoints

### POST `/search`
Main intelligence search endpoint.

**Request Body:**
```json
{
  "content_type": "both",     // "cve", "news", "both"
  "severity": ["high", "critical"], // Optional severity filter
  "max_results": 10,          // Maximum results to return
  "days_back": 7,            // Days to look back
  "output_format": "json",    // Response format
  "email_address": null       // Optional email for reports
}
```

**Response:**
```json
{
  "search_id": "search_1234567890",
  "cves": [...],              // Vulnerability objects
  "news": [...],              // News item objects
  "total_results": 15,
  "processing_time": 45.2,
  "query_params": {...}
}
```

### GET `/search/{search_id}/status`
Get the status of a running search operation.

### GET `/health`
Health check endpoint.

### GET `/stats`
API usage statistics.

## Development Features

### Backend Features
- **Async Processing**: Non-blocking intelligence gathering
- **Status Tracking**: Real-time search progress monitoring
- **Error Handling**: Comprehensive error responses
- **CORS Support**: Configured for React development
- **Data Validation**: Pydantic models for request/response validation

### Frontend Features
- **Modern Design**: Dark theme with glassmorphism effects
- **Responsive Layout**: Works on desktop, tablet, and mobile
- **Real-time Updates**: Live search status and results
- **Interactive Filtering**: Multi-select severity filters
- **Smart Results Display**: Separate CVE and news sections
- **External Links**: Direct links to original sources

## Deployment

### Backend Deployment
- **Railway**: