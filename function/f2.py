#Declaring a function
while True:
    def findTotal(a, b, c):
        s = a + b + c
        return s

    x = int(input("Enter first number: "))
    y = int(input("Enter second number: "))
    z = int(input("Enter third number: "))

    tot = findTotal(x, y, z)
    print(f"Total is {tot}")
    ans = input("\nEnter any key to continue...")
