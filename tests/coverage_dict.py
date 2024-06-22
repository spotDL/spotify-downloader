coverage_dict: dict[str, int] = {"1001": False, "1002": False, "1003": False, "1004": False, "1005": False, "1006": False, "1007": False, "1008": False, "1009": False}

def print_coverage_dict():
    print("\nCoverage dict:")

    for branch, hit in coverage_dict.items():
        print(f"\n\t{branch}: {hit}")
