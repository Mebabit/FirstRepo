#

import xml.etree.ElementTree as et

data = '''<person>
              <name>Chuck</name>
              <phone>
                  +91 5678543289
              </phone>
              <email hide = "yes" />
          </person>'''

tree = et.fromstring(data)
print("Name:", tree.find("name").text)
print("Attribute:", tree.find("email").get("hide"))
