from urllib.request import urlopen
from bs4 import BeautifulSoup
import ssl

# Ignore SSL certificate errors
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = input('Enter - ')
html = urlopen(url, context=ctx).read()
soup = BeautifulSoup(html, "html.parser")

# Retrieve all of the span tags
tags = soup('span')
count = 0
total = 0
for tag in tags:
    # Contents[0] gives the text inside the span
    num = int(tag.contents[0])
    count = count + 1
    total = total + num

print('Count', count)
print('Sum', total)