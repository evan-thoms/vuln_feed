import requests
from bs4 import BeautifulSoup
import json

headers = {
    "authority": "www.exploit-db.com",
    "accept": "application/json, text/javascript, */*; q=0.01",
    "x-requested-with": "XMLHttpRequest",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36",
    "referer": "https://www.exploit-db.com/",
    "accept-language": "en-US,en;q=0.9",
}

url = "https://www.exploit-db.com/"

params = {
    "start": 0,
    "length": 10,  
    "columns[0][data]": "id",
    "columns[0][name]": "id",
    "order[0][column]": "0",
    "order[0][dir]": "desc", 
}


response = requests.get(url, headers=headers, params=params)


try:
    retrieved_json = response.json()
except json.decoder.JSONDecodeError as exc:
    print(f"Can't decode json {exc}")

print("GOT IT", retrieved_json)

exploits = retrieved_json["data"]

for exploit in exploits:
    date = exploit["date_published"]
    # `description` contains an <a> tag with link
    id = exploit["id"]
    link = "https://www.exploit-db.com/exploits/"+id
    title = exploit["description"][1]

    print(f"Date: {date}")
    print(f"Title: {title}")
    print(f"Link: {link}\n")

with open("cves.json", "w") as f:
    json.dump(exploits, f, indent=2)