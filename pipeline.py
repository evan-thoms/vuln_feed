from scrapers.chinese_scrape import ChineseScraper
from deep_translator import GoogleTranslator
from models import NewsItem, Vulnerability
from agent import classify_article
import json
import argostranslate.package
import argostranslate.translate
from models import Article
import datetime
from db import (
    init_db,
    insert_raw_article,
    is_article_scraped,
    mark_as_processed,
    get_unprocessed_articles,
    insert_cve,
    insert_newsitem,
)

def truncate_text(text, max_length=3000):
    return text[:max_length]

def setup_argos():
    argostranslate.package.update_package_index()
    available_packages = argostranslate.package.get_available_packages()
    
    zh_en_package = next(
        filter(lambda x: x.from_code == "zh" and x.to_code == "en", available_packages)
    )
    argostranslate.package.install_from_path(zh_en_package.download())
    
    ru_en_package = next(
        filter(lambda x: x.from_code == "ru" and x.to_code == "en", available_packages)
    )
    argostranslate.package.install_from_path(ru_en_package.download())

def translate_articles(articles):
    for i, art in enumerate(articles):
        print(f"Translating article {i+1}/{len(articles)} title")
        art.title_translated = translate(art.title, art.language)
        print(f"Translating article {i+1}/{len(articles)} content")
        art.content_translated = translate(art.content, art.language)
    return articles

def chunk_text(text, max_length=5000):
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_length, len(text))
        chunk = text[start:end]
        last_newline = chunk.rfind('\n')
        last_space = chunk.rfind(' ')
        break_pos = max(last_newline, last_space)
        if break_pos > 0 and end < len(text):
            end = start + break_pos
        chunks.append(text[start:end])
        start = end
    return chunks


def translate_argos(text: str, source_lang: str, target_lang: str = "en") -> str:
    return argostranslate.translate.translate(text, source_lang, target_lang)

def translate(text: str, source_lang, target_lang="en") -> str:
    if source_lang == "en":
        print("Source language is English, skipping translation.")
        return text
    chunks = chunk_text(text, max_length=5000)
    translated_chunks = []
    for i, chunk in enumerate(chunks):
        print(f"Translating chunk {i+1}/{len(chunks)} (length {len(chunk)})")
        translated = translate_argos(chunk, source_lang)
        translated_chunks.append(translated)
    return "\n".join(translated_chunks)
    

def classify_articles(articles):
    cves = []
    news = []

    for art in articles:
        result = classify_article(art.content_translated)
        print(f"Agent result: {result}")

        if result["type"] == "CVE":
            vul = Vulnerability(
                cve_id=result["cve_id"][0] if result["cve_id"] else "Unknown",
                title=art.title,
                title_translated=art.title_translated,
                summary=result["summary"],
                severity=result["severity"],
                cvss_score=float(result["cvss_score"]) if result["cvss_score"] else 0.0,
                published_date=art.scraped_at,
                original_language=art.language,
                source=art.source,
                url=art.url,
                affected_products=[], 
            )
            cves.append(vul)
        else:
            news_item = NewsItem(
                title=art.title,
                title_translated=art.title_translated,
                summary=result["summary"],
                published_date=art.scraped_at,
                original_language=art.language,
                source=art.source,
                url=art.url,
            )
            news.append(news_item)

    return cves, news

def save_to_json(items, path):
    with open(path, "w") as f:
        json.dump([vars(item) for item in items], f, ensure_ascii=False, indent=2)

def main():
    init_db()
    setup_argos()

    articles = []
    c_scraper = ChineseScraper()
    articles += c_scraper.scrape_all()

    # r_scraper = RussianScraper()
    # articles+= r_scraper.scrape_all()

    # e_scraper = EnglishScraper()
    # articles+= c_scraper.scrape_all()


    unprocessed_rows = get_unprocessed_articles()
    if unprocessed_rows:
        print("processing " ,len(unprocessed_rows), " unprocessed rows")
    leftover_articles = [row_to_article(row) for row in unprocessed_rows]

    articles+= leftover_articles
    for art in articles:
        art.content = truncate_text(art.content, max_length=3000)
    print(f"Scraped {len(articles)} articles")

    translated_articles = translate_articles(articles)
    
    print(f"Translated {len(translated_articles)} articles")

    for art in translated_articles:
        print("Inserted ", art.title_translated)
        insert_raw_article(art)

    cves, newsitems = classify_articles(translated_articles)
 
    for cve in cves:
        print("Inserted CVE ", cve.title_translated)
        insert_cve(cve)

    for newsitem in newsitems:
        print("Inserted News ", newsitem.title_translated)
        insert_newsitem(newsitem)
    
    save_to_json(cves, "cves.json")
    save_to_json(newsitems, "newsitems.json")
        
def row_to_article(row):
    return Article(
        id=row[0],
        source=row[1],
        title=row[2],
        title_translated=row[3],
        url=row[4],
        content=row[5],
        content_translated=row[6],
        language=row[7],
        scraped_at=row[8]
    )

def test_classify_example():
    example_text = """Researchers use OpenAI o3 model to discover remote zero-day vulnerability in Linux kernel
Yixin Security
2025-05-27 15:42:39
11000

Source of this article
Official account
Yixin Security
If you have any questions, please contact FreeBuf customer service (WeChat ID: freebee1024)
Researchers use OpenAI o3 model to discover remote zero-day vulnerability in Linux kernel
Image
Article background
The protagonist of the article is Sean Heelan, a senior security researcher. When he audited the SMB implementation ksmbd of the Linux kernel, he used OpenAI's latest o3 model to successfully discover a remote zero-day vulnerability CVE-2025-37899. ksmbd is a module in the Linux kernel used to implement the SMB (Server Message Block) protocol, mainly used for file sharing services. Since the SMB protocol is widely used in enterprise environments, the discovery of this vulnerability is of great significance.

Vulnerability Overview: CVE-2025-37899
Vulnerability Type
CVE-2025-37899 is a use-after-free (UAF) vulnerability located in the logoff command handler of ksmbd. UAF vulnerability definition: When a memory object is released and the program still attempts to access or operate the memory address, a UAF vulnerability is triggered. This situation may lead to undefined behavior, including program crashes or even remote code execution.

Vulnerability Location
The vulnerability occurs when ksmbd processes the logoff command of the SMB protocol. The logoff command is usually sent by the client to notify the server to disconnect the current session.

Vulnerability Details Analysis
Cause Analysis
The core problem of the vulnerability is improper reference count management, combined with the concurrent connection characteristics of the SMB server, which leads to the occurrence of UAF. The following are the specific causes:

1. Object release
When processing the logoff command, ksmbd will release a key object (such as a session or connection-related structure). After this object is released, its memory address should be marked as unavailable.

2. Concurrent access
The SMB server supports multi-threaded processing of concurrent connections. When one thread releases the object, another thread may still be processing operations related to the object and try to access the released memory.

3. Missing reference count
The object does not correctly implement the reference counting mechanism. Normally, the reference count is used to track the number of active references to the object, and the object will be safely released only when the count is zero. However, in ksmbd, a design flaw causes the object to be released early when there are still threads referencing it.

Speculated code problem
The article does not directly provide the code snippet of the vulnerability, but based on the description, I speculate that the problem may appear in the following logic (pseudo-code representation):

struct session {
int ref_count; // reference count
void *data; // data pointer
};
void process_logoff(struct session *s) {
free(s->data); // release data
free(s); // release session object
}
void handle_connection(struct session *s) {
// assume that another thread is still using s->data
process_data(s->data);
}
In the above pseudo-code: The process_logoff function releases s->data and s, but does not check whether ref_count is zero. If handle_connection is still accessing s->data in a concurrent thread, the UAF will be triggered.

Vulnerability Exploitation Method
The article does not disclose the specific exploitation method in detail, but based on the characteristics of the UAF vulnerability, I can speculate a possible exploitation path:

1. Triggering object release
The attacker triggers the release of the target object by sending a carefully constructed logoff command.

2. Concurrent access
After the object is released, the attacker immediately accesses the same object through another SMB connection. At this time, the memory may still not be overwritten and points to the released address.

3. Memory reuse and control
The released memory may be reallocated to other uses by the operating system.
The attacker controls the reallocated memory content (such as heap spray technology) by sending specific SMB requests, thereby overwriting critical data (such as function pointers).
If the memory layout is successfully controlled, arbitrary code execution may be achieved.
Difficulty of Exploitation
Challenge: Exploiting UAF requires precise control of memory allocation and thread timing, which is a high-difficulty exploit. Possibility: Since ksmbd runs in kernel mode, successful exploitation may lead to remote privilege escalation or system crash.

Vulnerability Discovery Method
Using OpenAI o3 Model
Sean Heelan used OpenAI's o3 model, a powerful large language model (LLM) that has the ability to understand and analyze code. The discovery process is as follows:

1. Code input
The author inputs the relevant code of ksmbd (about 12,000 lines) into the o3 model. This includes the logoff command handler and related concurrent logic.

2. Model Analysis
The o3 model identifies potential vulnerability points through static analysis and semantic understanding. In particular, it can:"""
    result = classify_article(example_text)
    print(f"Agent result: {result}")

if __name__ == "__main__":
    # result = classify_article(cool)
    # print(f"Agent result: {result}")
    main()