def show_error(message):
    print(f"Error: {message}")

def format_data(data):
    # Format data for display or storage
    return [round(d, 2) for d in data]

def validate_input(value, min_value, max_value):
    if not (min_value <= value <= max_value):
        show_error(f"Value {value} is out of range ({min_value}, {max_value})")
        return False
    return True