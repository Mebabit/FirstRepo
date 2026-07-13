"""
Write a Python script that asks the user for a URL, fetches the page,
and loops through the anchor (<a>) tags. However, instead of printing all links,
your script must only print links that lead to other Wikipedia articles
(meaning the href starts with the text "/wiki/").
"""
#https://en.wikipedia.org/wiki/Main_Page

import urllib.request, urllib.parse, urllib.error
from bs4 import BeautifulSoup

url = input("Enter url: ")
html = urllib.request.urlopen(url).read()

# FIX: Changed "html.parse" to "html.parser"
soup = BeautifulSoup(html, "html.parser")

tags = soup("a")
for tag in tags:
    href = tag.get("href", None)

    if href is not None and href.startswith("/wiki/"):
        print(href)

#The above code is not working because the owner website detect the python code and
#didn't want to allow it, so the code below is to bypass that
"""import urllib.request, urllib.parse, urllib.error
from bs4 import BeautifulSoup

url = input("Enter url: ")

try:
    # 1. Create a Request object and add a 'User-Agent' header to look like a browser
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    )
    
    # 2. Open the request instead of the raw URL string
    html = urllib.request.urlopen(req).read()
    
    soup = BeautifulSoup(html, "html.parser")

    tags = soup("a")
    for tag in tags:
        href = tag.get("href", None)

        if href is not None and href.startswith("/wiki/"):
            print(href)

except urllib.error.HTTPError as e:
    print(f"HTTP Error occurred: {e.code}")
except Exception as e:
    print(f"An error occurred: {e}")"""
