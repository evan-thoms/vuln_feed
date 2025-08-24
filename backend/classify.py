from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import List, Dict, Optional
import json
import os
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

llm = ChatOpenAI(
    model="gpt-4o-mini",  # Much cheaper than GPT-4, great for classification
    openai_api_key=os.environ.get("OPENAI_API_KEY"),
    temperature=0,  # Consistent output
    max_tokens=500,  # Limit tokens to save cost
    max_retries=2
)
# REQUIRED FORMAT:
# {
#   "type": "CVE" | "News",
#   "cve_id": ["..."],
#   "severity": "Low" | "Medium" | "High" | "Critical",
#   "cvss_score": "0.0 - 10.0",
#   "summary": "Concise, human-readable explanation",
#   "intrigue": "0-10",
#   "affected_products": ["product1", "product2"]
# }
prompt = ChatPromptTemplate.from_template("""
You are a security threat intelligence assistant, returning a json report in my specified format
Given this text:
---
{article}
---
Return a SINGLE JSON object with ALL of the following fields, and nothing else, no other notes.

Type: If this contains a unique and identifieable CVE, then set this to CVE. Otherwise, always set it to News
cve_id: If identifiable CVE numbers are found, return a list of all of them here. If no unique CVE ID is present, set cve_id to Unknown if no identifiable CVE nubmer is present and type to News
severity: Give your best estimate from these 4 choices as to how severe this incident is: (Low/Medium/High/Critical)
CVSS_score: If CVSS score is present in text, extract it as a float. Otherwise, provide your own reasoned estimate based on described impact and exploitability, choosing a value between 0.0 and 10.0 and avoiding overestimation.
summary: Provide a 2-3 sentence consise and compact summary of the details the vulnerability, exploitation process, and affected machines
intrigue: Rate how intriguing and exciting this information is by providing a number from 1 to 10, with ten being the most intriguing, must-read information for someone getting updates about cybersecurity.
affected_products: Create simple list of affected products as a list of strings

Return nothing else besides this exact JSON format as this example below. Do not provide an explanation for your answers or comments.
{{
  "type": "CVE",
  "cve_id": ["CVE-2023-12345"],
  "severity": "High",
  "cvss_score": 7.2,
  "summary": "Concise explanation of the vulnerability and exploitation details.",
  "intrigue": 7,
  "affected_products": ["Product A", "Product B"]
}}
""")
def extract_multiple_json_objects(llm_output: str):
    """
    Extract multiple JSON objects from LLM output.
    Ignores noise between or around them.
    Returns a list of valid JSON objects.
    """
    json_objects = []
    
    # Match all JSON blocks
    matches = re.finditer(r'\{.*?\}', llm_output, re.DOTALL)
    
    for match in matches:
        try:
            obj = json.loads(match.group())
            json_objects.append(obj)
        except json.JSONDecodeError:
            continue  
    
    return json_objects

def classify_article(article: str) -> dict:
    if not article or not article.strip():
        print("⚠️  Empty article content, skipping classification")
        return []
    
    try:
        print(f"🔍 Classifying article (length: {len(article)} chars)...")
            
        chain = prompt | llm | (lambda x: x.content)
        result = chain.invoke({"article": article[:2500]})
        print("result ", result)
        
        matches =extract_multiple_json_objects(result)

        if not matches:
            print("❌ No valid JSON found, creating fallback classification")
            # Return fallback classification instead of crashing
            return [{
                "type": "News",
                "cve_id": ["Unknown"],
                "severity": "Medium",
                "cvss_score": 5.0,
                "summary": "Classification failed - manual review needed",
                "intrigue": 3,
                "affected_products": ["Unknown"]
            }]
        print(f"✅ Successfully extracted {len(matches)} classifications")
        return matches
    
    except Exception as e:
        print(f"❌ Classification error: {e}")
        # Return empty list instead of crashing
        return []

def classify_single_article_safe(article_data):
    """
    Thread-safe wrapper for single article classification.
    Input: (index, article_content, article_url)
    Output: (index, success, results, error_msg)
    """
    index, content, url = article_data
    
    try:
        print(f"🔍 [{index}] Processing: {url}...")
        results = classify_article(content)
        return (index, True, results, None)
    except Exception as e:
        print(f"❌ [{index}] Error: {e}")
        return (index, False, [], str(e))

def classify_articles_parallel(articles_data, max_workers=5, target_results=None):
    """
    Classify multiple articles in parallel.
    
    Args:
        articles_data: List of (index, content, url) tuples
        max_workers: Number of concurrent threads (don't exceed OpenAI rate limits)
    
    Returns:
        List of (index, success, results, error_msg) tuples
    """
    print(f"🚀 Starting parallel classification with {max_workers} workers...")
    print(f"📊 Processing {len(articles_data)} articles...")
    
    results = []
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_index = {
            executor.submit(classify_single_article_safe, data): data[0] 
            for data in articles_data
        }
        
        # Collect results as they complete
        completed = 0
        for future in as_completed(future_to_index):
            result = future.result()
            results.append(result)
            completed += 1
            print(f"📈 Progress: {completed}/{len(articles_data)} completed")
    
    elapsed = time.time() - start_time
    successful = sum(1 for _, success, _, _ in results if success)
    failed = len(results) - successful
    
    print(f"🎯 Parallel classification complete!")
    print(f"⏱️  Time: {elapsed:.2f} seconds")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"🚀 Speed: {len(articles_data)/elapsed:.1f} articles/second")
    
    # Sort results by original index to maintain order
    return sorted(results, key=lambda x: x[0])

if __name__ == "__main__":
    # example_text = "在Fortinet VPN产品中发现了一个新的远程代码执行漏洞，编号CVE-2024-12345，CVSS评分9.8..."
    example_text = "Microsoft Office 中的多个关键漏洞可能允许攻击者在受影响的系统上执行任意代码。这些漏洞被跟踪为CVE-2025-47162,CVE-2025-47953,CVE-2025-47164和CVE-2025-47167,所有漏洞的CVSS得分为8.4分(满分10分),并影响Windows,Mac和Android平台的众多Office版本。安全研究员0x140ce发现了这些缺陷,这些缺陷利用了基本的内存管理弱点,包括基于堆的缓冲区溢出,无使用条件和类型混淆错误。此漏洞(CWE-122)源于在 Office 文件解析例程中内存分配期间的不当边界检查。CVE-2025-47162:"
    print(classify_article(example_text))
