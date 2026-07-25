import json
import urllib.parse
import urllib.request
import ssl

# Service endpoint as specified in the assignment
serviceurl = 'http://py4e-data.dr-chuck.net/opengeo?'

# Ignore SSL certificate errors
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

while True:
    address = input('Enter location: ')
    if len(address) < 1:
        break

    # Build the parameters dictionary including 'q' and 'key=42'
    parms = dict()
    parms['q'] = address
    parms['key'] = 42

    url = serviceurl + urllib.parse.urlencode(parms)

    print('Retrieving', url)
    uh = urllib.request.urlopen(url, context=ctx)
    data = uh.read().decode()
    print('Retrieved', len(data), 'characters')

    try:
        js = json.loads(data)
    except Exception:
        js = None

    if not js or 'features' not in js:
        print('=== Failure To Retrieve ===')
        print(data)
        continue

    # Extract the plus_code from properties
    plus_code = js['features'][0]['properties']['plus_code']
    print('Plus code', plus_code)