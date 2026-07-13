#mboc.txt
import re
hand = open(r"C:\pracFolder\CourseraExcercise\PythonDataStructure\mboc.txt")
data = hand.read()
y = re.findall("[0-9]+", data)
x = [int(num) for num in y]
result = sum(x)
print(result)