import json

with open('coverage.json') as f:
    data = json.load(f)

print(f"Total Coverage: {data['totals']['percent_covered']:.2f}%")
print(f"Covered Lines: {data['totals']['covered_lines']}")
print(f"Missing Lines: {data['totals']['missing_lines']}")
