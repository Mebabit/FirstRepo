
import xml.etree.ElementTree as et

inp = '''
<stuff>
    <user x = "2" >
        <id> 001 </id> 
        <name> Chuck </name>
    </user>
    <user x = "7" >
        <id> 009 </id>
        <name> Brent </name>
    </user>
</stuff>'''

stuff = et.fromstring(inp)
lst = stuff.findall("user")
print("User count:", len(lst))
for item in lst:
    print("\nName:", item.find("name").text)
    print("ID:", item.find("id").text)
    print("Attribute:", item.get("x"))

                
