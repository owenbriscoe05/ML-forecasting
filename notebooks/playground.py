import pytest
import re

""" name = input("What's your name? ")

split = name.split(' ')

# dunder grab
__,last = split
first,__ = split

print(f"hello, {last.strip().title()}")

# standard error catch
if last == "briscoe" and first == "owen":
    print("success!")
else:
    print(f"first name is {first} and last name is {last}")

# assert error catch
assert(last == "briscoe" and first == "owen")

# pytest error catch
assert(last == "briscoe")
assert(first == "owen")


# regex functionality testing
name = input("What's your name? ").strip()
matches = re.search(r"^(.+), ?(.+)$", name)
if matches:
    last = matches.group(1)
    first = matches.group(2)
    unknown = matches.group(0)
else:
    print("No name provided")

print(f"hello, {first} {last} \n and the unknown item is {type(unknown)}") """

def main():
    student = get_student()
    print(f"{student.name} is {student.age} years old")

class Student:
    ...

def get_student():
    student = Student()
    student.name = "Owen"
    student.age = 20
    return student

if __name__ == "__main__":
    main()