def default_name(obj, prefix: str) -> str:
    last_order = obj.search([], order='id desc', limit=1)
    if last_order.name and last_order.name.startswith(prefix) and last_order.name[len(prefix):].isdigit():
        last_number = int(last_order.name[len(prefix):])
        new_number = last_number + 1
    else:
        new_number = 1
    return f'{prefix}{new_number:05d}'
