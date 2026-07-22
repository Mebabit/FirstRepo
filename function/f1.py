#Write a program using function to check whether two numbwe are equal or not
while True:
    def check_relation(a, b):
        if a == b:
            print(a, "is equal to", b)
        elif a > b:
            print(a, "is greater than", b)
        else:
            print(a, "is less than", b)

    x = int(input("Enter first number: "))
    y = int(input("Enter second number: "))
    check_relation(x, y)
    
    ans = input("\nPress any key to continue..")
