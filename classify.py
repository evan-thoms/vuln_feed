from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
import json
import re

llm = ChatOllama(model="llama3")

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

Return nothing else besides this exact JSON format as this example below. Do not provide an explanation for your answers.
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
    chain = prompt | llm | (lambda x: x.content)
    result = chain.invoke({"article": article})
    print("result ", result)
    
    matches =extract_multiple_json_objects(result)
    if not matches:
        raise ValueError("No JSON found in response:\n" + result)
    return matches


if __name__ == "__main__":
    # example_text = "在Fortinet VPN产品中发现了一个新的远程代码执行漏洞，编号CVE-2024-12345，CVSS评分9.8..."
    example_text = "Microsoft Office 中的多个关键漏洞可能允许攻击者在受影响的系统上执行任意代码。这些漏洞被跟踪为CVE-2025-47162,CVE-2025-47953,CVE-2025-47164和CVE-2025-47167,所有漏洞的CVSS得分为8.4分(满分10分),并影响Windows,Mac和Android平台的众多Office版本。安全研究员0x140ce发现了这些缺陷,这些缺陷利用了基本的内存管理弱点,包括基于堆的缓冲区溢出,无使用条件和类型混淆错误。此漏洞(CWE-122)源于在 Office 文件解析例程中内存分配期间的不当边界检查。CVE-2025-47162:"
    print(classify_article(example_text))
