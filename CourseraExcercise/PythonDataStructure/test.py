"""
Write a program to prompt for a file name, then open that file
and read through the file, looking for line of the form:
X-DSPAM-Confindence:     0.8475, count these line and extract the floating point
values from each of the lines and compute the average of those values
and produce an output as shown below. Do not used the sum() function or
a variable name sum in your situation.
"""

fname = input("Enter file name: ")
handle = open(fname)

counts = 0
total_value = 0.0

for line in handle:
    if not line.startswith("X-DSPAM-Confindence:"):
        continue

    colon_pos = line.find(":")
    number_str = line[colon_pos + 1:]

    value = float(number_str.strip())
    

    total_value = total_value + value
    counts = counts + 1
    
average = total_value / counts
print("Average Spam confidence: ", average)

