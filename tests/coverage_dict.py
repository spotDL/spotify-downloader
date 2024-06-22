coverage_dict: dict[str, int] = {"branch-1001": False,
                                 "branch-1002": False,
                                 "branch-1003": False,
                                 "branch-1004": False,
                                 "branch-1005": False,
                                 "branch-1006": False,
                                 "branch-1007": False,
                                 "branch-1008": False,
                                 "branch-1009": False}

def print_coverage_dict():
    print("\nCoverage dict:")
    for branch, hit in coverage_dict.items():
        print(f"\n\t{branch}: {hit}")
