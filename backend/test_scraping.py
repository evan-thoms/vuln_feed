import vulners

vulners_api = vulners.VulnersApi(api_key="9DZAW2NZ8L5502PAVQURU0VRCL7WLXNO61JEX3A4MCF1T0SNRS4THDSVMITCHUHM")
search_result = vulners_api.search.search_bulletins("type:cve")
print(search_result)

import vulners
import json
from pprint import pprint

def main():
    # Initialize the API
    vulners_api = vulners.VulnersApi(api_key="9DZAW2NZ8L5502PAVQURU0VRCL7WLXNO61JEX3A4MCF1T0SNRS4THDSVMITCHUHM")

# Search for CVE bulletins with specific fields
# According to the docs, you can specify which fields to return
search_result = vulners_api.search.search_bulletins(
    "type:cve"
    # , 
    # skip=0, 
    # size=5,  # Limit to 5 results for easier viewing
    # fields=[
    #     "id", 
    #     "title", 
    #     "description", 
    #     "short_description",
    #     "type", 
    #     "bulletinFamily",
    #     "cvss", 
    #     "published", 
    #     "modified", 
    #     "lastseen", 
    #     "href", 
    #     "sourceHref", 
    #     "cvelist"
    # ]
)

print("=== VULNERS API SEARCH RESULTS ===")
print(f"Response type: {type(search_result)}")
print(f"Response keys: {list(search_result.keys()) if isinstance(search_result, dict) else 'Not a dict'}")

# Check if we have data
if 'data' in search_result:
    documents = search_result['data']['documents']
    print(f"\nFound {len(documents)} CVE documents")
    
    # Display each CVE in a readable format
    for i, cve in enumerate(documents, 1):
        print(f"\n--- CVE #{i} ---")
        print(f"ID: {cve.get('id', 'N/A')}")
        print(f"Title: {cve.get('title', 'N/A')}")
        print(f"Type: {cve.get('type', 'N/A')}")
        print(f"Bulletin Family: {cve.get('bulletinFamily', 'N/A')}")
        print(f"Published: {cve.get('published', 'N/A')}")
        print(f"Modified: {cve.get('modified', 'N/A')}")
        
        # Display CVSS information if available
        if 'cvss' in cve and cve['cvss']:
            print(f"CVSS Score: {cve['cvss'].get('score', 'N/A')}")
            print(f"CVSS Vector: {cve['cvss'].get('vector', 'N/A')}")
        
        # Display short description (truncated for readability)
        short_desc = cve.get('short_description', '')
        if short_desc:
            print(f"Short Description: {short_desc[:200]}{'...' if len(short_desc) > 200 else ''}")
        
        # Display related CVEs if available
        if 'cvelist' in cve and cve['cvelist']:
            print(f"Related CVEs: {', '.join(cve['cvelist'][:5])}")  # Show first 5
            
        print(f"Source URL: {cve.get('href', 'N/A')}")
        print("-" * 50)

else:
    print("No 'data' key found in response")
    print("Full response structure:")
    pprint(search_result)

print("\n=== RAW RESPONSE STRUCTURE (for debugging) ===")
print("Keys in response:", list(search_result.keys()) if isinstance(search_result, dict) else "Not a dict")

# Show a sample of the raw data structure
if isinstance(search_result, dict) and 'data' in search_result:
    print("\nSample raw document structure:")
    if search_result['data']['documents']:
        first_doc = search_result['data']['documents'][0]
        print("Available fields in first document:")
        for key, value in first_doc.items():
            value_type = type(value).__name__
            value_preview = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
            print(f"  {key} ({value_type}): {value_preview}")

if __name__ == "__main__":
    main()