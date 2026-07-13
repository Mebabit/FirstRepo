import io
import requests
import pandas as pd
from bs4 import BeautifulSoup
import urllib3

# Suppress the insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://mpsc.meghalaya.gov.in/advertisements.html"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

try:
    response = requests.get(url, headers=headers, verify=False)
    
    # FIX: Wrap response.text in io.StringIO so Pandas knows it is raw text data
    html_data = io.StringIO(response.text)
    
    tables = pd.read_html(html_data, flavor='bs4')
    
    if tables:
        job_table = tables[0]
        print("Successfully extracted the job table!\n")
        print("--- HERE IS A PREVIEW OF THE DATA ---")
        
        # This will show you a clean, readable text preview of the first 5 rows
        print(job_table.head().to_string()) 
        
        # Save it cleanly to Excel/CSV
        job_table.to_csv("meghalaya_jobs.csv", index=False)
        print("\n---")
        print("Saved everything perfectly to 'meghalaya_jobs.csv'")
    else:
        print("No tables found on this page.")

except Exception as e:
    print(f"An error occurred: {e}")
