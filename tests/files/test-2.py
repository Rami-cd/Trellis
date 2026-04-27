import math

def calculate_circle_area(radius):
    """Calculate the area of a circle."""
    return math.pi * radius ** 2

def fibonacci(n):
    """Generate fibonacci sequence up to n terms."""
    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a + b

numbers = list(fibonacci(10))
