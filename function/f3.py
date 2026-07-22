#Write a function base program to find the greatest of three number and
#also reverse of a number using two function

def find_greatest(a, b, c):
    if a > b and a > c:
        max = a
    elif b > a and b > c:
        max = b
    else:
        max = c
    print(f"Greatest number is: {max}")

def find_reverse(n):
    rev = 0
    while n!=0:
        d = n%10
        rev = rev*10 + d
        n =n//10
    print(f"Reverse is {rev}\n")

while True:
    try:
        x = int(input("Enter 1st number: "))
        y = int(input("Enter 2nd number: "))
        z = int(input("Enter 3rd number: "))
        find_greatest(x, y, z)

        q = int(input("Enter multidigit number: "))
        find_reverse(q)
    except ValueError:
        print("\nPlease enter number only")
        ad = input("\nPress any key to continue...")
