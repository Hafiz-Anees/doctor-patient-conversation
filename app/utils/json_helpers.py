"""
json_helpers.py — small reusable helpers for cleaning up dicts before
they're sent back to the frontend.
"""


def remove_empty_fields(data):
    """
    Recursively removes keys/items whose value is empty:
    None, "", [], or {}. Works on nested dicts and lists.
    Leaves the original object untouched — returns a new cleaned copy.
    """
    #if data is dictionary, iterate over its items and remove empty fields recursively
    if isinstance(data, dict):
        cleaned = {}
        #if the value is a dict or list, call remove_empty_fields recursively
        for key, value in data.items():
            cleaned_value = remove_empty_fields(value)
            if cleaned_value not in (None, "", [], {}):
                cleaned[key] = cleaned_value
        return cleaned
#else if data is list, iterate over its items and remove empty fields recursively
    elif isinstance(data, list):
        cleaned_list = [remove_empty_fields(item) for item in data]
        return [item for item in cleaned_list if item not in (None, "", [], {})]

    else:
        return data


def remove_keys(data, keys_to_remove):
    """
    Recursively removes specific keys (by name, case-insensitive) from a
    dict, no matter how deeply nested. keys_to_remove is a list of key
    names, e.g. ["Vitals"]. Leaves the original object untouched.
    """
    keys_to_remove_lower = {k.lower() for k in keys_to_remove}

    if isinstance(data, dict):
        return {
            key: remove_keys(value, keys_to_remove)
            for key, value in data.items()
            if key.lower() not in keys_to_remove_lower
        }
    elif isinstance(data, list):
        return [remove_keys(item, keys_to_remove) for item in data]
    else:
        return data


def keep_keys(data: dict, keys_to_keep: list) -> dict:
    """
    Returns a new dict containing ONLY the given keys (any others are
    dropped). The opposite of remove_keys — use this when you know exactly
    what you want to show, rather than trying to name everything to hide.
    """
    return {k: v for k, v in data.items() if k in keys_to_keep}