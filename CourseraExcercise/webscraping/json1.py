import json
import urllib.request
import urllib.parse
import ssl

# Ignore SSL certificate errors (for HTTPS connections)
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Prompt for the URL
url = input('Enter location: ')
if len(url) < 1:
    url = 'http://py4e-data.dr-chuck.net/comments_2420981.json'

print('Retrieving', url)
uh = urllib.request.urlopen(url, context=ctx)
data = uh.read().decode()

print('Retrieved', len(data), 'characters')

# Parse the JSON string into a Python dictionary
info = json.loads(data)

# Extract the list of comments and sum the counts
comments = info.get('comments', [])
total_sum = 0
count = 0

for item in comments:
    total_sum += item['count']
    count += 1

print('Count:', count)
print('Sum:', total_sum)