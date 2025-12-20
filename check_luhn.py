
def calculate_luhn(imei14):
    digits = [int(d) for d in imei14]
    sum_val = 0
    # Procesar de derecha a izquierda (índice 13 hacia 0)
    # Posición 1 (derecha, índice 13): x2
    # Posición 2 (derecha, índice 12): x1
    # ...
    for i in range(13, -1, -1):
        digit = digits[i]
        # Posición desde la derecha (1-based): 14 - i
        pos_from_right = 14 - i
        
        if pos_from_right % 2 != 0: # Impares desde la derecha (1, 3, 5...) -> x2
            digit *= 2
            if digit > 9:
                digit -= 9
        
        sum_val += digit
        
    check_digit = (10 - (sum_val % 10)) % 10
    return check_digit

test_cases = [
    ("35209900176148", 2),
    ("86250906645473", 0),
    ("35892984056686", 5)
]

for imei14, expected in test_cases:
    calculated = calculate_luhn(imei14)
    print(f"IMEI14: {imei14}, Expected: {expected}, Calculated: {calculated}, Match: {expected == calculated}")

