# Cybersecurity Intelligence Agent

An agentic AI system that processes real-time cybersecurity news and CVE data using LangChain.

## Features
- Natural language queries for CVEs and security news
- Multi-language scraping (Chinese, Russian, English)
- LLM-based content classification and ranking
- Email delivery support
- Real-time processing pipeline

## Usage
```bash
python main.py
```

Example queries:
- "Show me 5 critical CVEs from the last 3 days"
- "Find 10 cybersecurity news from this week"
- "Email me high severity vulnerabilities to user@company.com"

## Architecture
4-tool agentic pipeline:
1. **Scrape & Process** - Fresh article collection and translation
2. **Classify** - LLM-based CVE vs news classification  
3. **Filter & Rank** - Apply user criteria and intelligent ranking
4. **Present** - Format for display or email delivery

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Set OpenAI API key: `export OPENAI_API_KEY=your_key`
3. Run setup: `python utils/setup.py`
4. Start agent: `python main.py`