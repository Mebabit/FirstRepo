#Using BeautifulSoup to scrape data from a website
import urllib.request, urllib.parse, urllib.error
from bs4 import BeautifulSoup

url = input("Enter url: ")
html = urllib.request.urlopen(url).read()
soup = BeautifulSoup(html, "html.parser")

# Retrieve all the anchor tag
tags = soup("a")
for tag in tags:
    print(tag.get("href", None))
