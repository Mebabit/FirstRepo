from urllib.request import urlopen
from bs4 import BeautifulSoup
import ssl

# Ignore SSL certificate errors
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = input('Enter URL: ')
count = int(input('Enter count: '))
position = int(input('Enter position: '))

for i in range(count):
    print('Retrieving:', url)
    html = urlopen(url, context=ctx).read()
    soup = BeautifulSoup(html, "html.parser")

    # Find all anchor tags
    tags = soup('a')

    # Position is 1-based, so subtract 1 for list indexing
    tag = tags[position - 1]

    # The href gives us the next URL to follow
    url = tag.get('href', None)

print('Retrieving:', url)