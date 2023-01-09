from typing import List

from spotdl.utils.formatter import slugify


def fill_string(strings: List[str], main_string: str, string_to_check: str) -> str:
    """
    Create a string with strings from `strings` list
    if they are not yet present in main_string
    but are present in string_to_check

    ### Arguments
    - strings: strings to check
    - main_string: string to add strings to
    - string_to_check: string to check if strings are present in

    ### Returns
    - final_str: string with strings from `strings` list
    """

    final_str = main_string.replace("-", "")
    simple_test_str = string_to_check.replace("-", "")
    for string in strings:
        slug_str = slugify(string).replace("-", "")

        if slug_str in simple_test_str and slug_str not in final_str:
            final_str += f"-{slug_str}"

    return final_str


def sort_string(strings: List[str], join_str: str) -> str:
    """
    Sort strings in list and join them with `join` string

    ### Arguments
    - strings: strings to sort
    - join: string to join strings with

    ### Returns
    - final_str: string with sorted strings
    """

    final_str = strings
    final_str.sort()

    return f"{join_str}".join(final_str)
