from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
import json
import re

llm = ChatOllama(model="llama3")

prompt = ChatPromptTemplate.from_template("""
You are a security threat intelligence assistant, returning a json report in my specified format
Given this text:
---
{article}
---
1. Does this contain a unique and identifiable CVE (yes/no)?
2. If yes, extract:
    - 
   - If you find no CVE number, ALWAYS set `cve_id` to `["Unknown"]` AND `type` to `"News"`.
    - If you find one or more valid CVE IDs, ALWAYS set `type` to `"CVE"` and `cve_id` to the found CVE list.
    - NEVER output `"CVE"` type if the ID is missing or unknown.
    - If no unique CVE ID is present, do NOT make up a fake CVE format like `CVE-XXXX-XXXX` — just set it to `["Unknown"]`.

   - Severity (Low/Medium/High/Critical). Give your best estimate from these 4 choices
   - CVSS score, If CVSS score is present in text, extract it as a float. Otherwise, provide your own reasoned estimate based on described impact and exploitability, choosing a value between 0.0 and 10.0 and avoiding overestimation.
   - Rate how intriguing and exciting this information is by providing a number from 1 to 10, with ten being the most intriguing, must-read information for someone getting updates about cybersecurity.
   - Create simple list of affected products as a list of strings
3. For the summary field, provide a 2-3 sentence consise and compact summary of the details the vulnerability, exploitation process, and affected machines

Here is your format, return ONLY IN THIS FORMAT and provide no other information. Return this information as only one object, not a list of objects.
{{"type":"CVE"|"News","cve_id":"[]", "severity":"Low"|"Medium"|"High"|"Critical", "cvss_score":"", "summary":"", "intrigue":"", "affected_products":"[]"}}
""")

def classify_article(article: str) -> dict:
    chain = prompt | llm | (lambda x: x.content)
    result = chain.invoke({"article": article})
    print("result ", result)
    
    match = re.search(r"\{[\s\S]*\}", result)
    if not match:
        raise ValueError("No JSON found in response:\n" + result)

    return json.loads(match.group(0))


if __name__ == "__main__":
    # example_text = "在Fortinet VPN产品中发现了一个新的远程代码执行漏洞，编号CVE-2024-12345，CVSS评分9.8..."
    example_text = "Microsoft Office 中的多个关键漏洞可能允许攻击者在受影响的系统上执行任意代码。这些漏洞被跟踪为CVE-2025-47162,CVE-2025-47953,CVE-2025-47164和CVE-2025-47167,所有漏洞的CVSS得分为8.4分(满分10分),并影响Windows,Mac和Android平台的众多Office版本。安全研究员0x140ce发现了这些缺陷,这些缺陷利用了基本的内存管理弱点,包括基于堆的缓冲区溢出,无使用条件和类型混淆错误。此漏洞(CWE-122)源于在 Office 文件解析例程中内存分配期间的不当边界检查。CVE-2025-47162:"
    print(classify_article(example_text))
