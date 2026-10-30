#!/usr/bin/env python3
"""Build the GitHub Actions matrix JSON for N users: {"include":[{"index":1},...]}"""
import json, sys
n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
n = max(1, min(n, 100))
print(json.dumps({"include": [{"index": i} for i in range(1, n + 1)]}))
