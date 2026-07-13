"""Write a program to read through the mbox-short.txt and figure out the
distribution by hour of the day for each of the messages. You can the hour out from
the "From " line by finding the time and then splitting the string a second time using a colon
From stephen.marquard@uct.ac.za Sat Jan 5 09:14:16 2008
Once you have accumulate the counts for each hour, print out the count sorted by hours as shown below
"""

name = input("Enter file name: ")
if len(name)<1:
    name = "mbox-short.txt"
handle = open(name)
counts = dict()

for line in handle:
    if not line.startswith("From "):
        continue
    words = line.split()
    time_str = words[5]

    time_part = time_str.split(":")
    hour = time_part[0]

    counts[hour] = counts.get(hour, 0) + 1

sorted_hour = sorted(counts.items())

for hour, count in sorted_hour:
    print(hour, count)
