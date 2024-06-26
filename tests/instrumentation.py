global coverage_dict
coverage_dict: dict[str, int] = {"branch-1001": False,
                                 "branch-1002": False,
                                 "branch-1003": False,
                                 "branch-1004": False,
                                 "branch-1005": False,
                                 "branch-1006": False,
                                 "branch-1007": False,
                                 "branch-1008": False,
                                 "branch-2001": False,
                                 "branch-2002": False,
                                 "branch-2003": False,
                                 "branch-2004": False,
                                 "branch-2005": False,
                                 "branch-2006": False,
                                 "branch-2007": False,
                                 "branch-2008": False
                                 }

def print_coverage_dict(branches: list[str] = None):
    print("\nCoverage dict:")
    branches_to_print = [branch for branch in coverage_dict if branch in branches] if branches else [branch for branch in coverage_dict]
    for branch in branches_to_print:
        print(f"\n\t{branch}: {coverage_dict[branch]}")
