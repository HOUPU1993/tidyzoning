import math

def calculate_circle(radius):
    if radius <= 0:
        return "Radius must be greater than 0"
    
    area = math.pi * (radius ** 2)
    circumference = 2 * math.pi * radius
    
    return {
        "Area": round(area, 2),
        "Circumference": round(circumference, 2)
    }