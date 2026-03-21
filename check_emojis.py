import os
import re

target_dir = r'd:\Project\Immortal-Custom-Rules'
# Regex for:
# ASCII: \x00-\x7f
# Chinese: \u4e00-\u9fff, \u3400-\u4dbf, \u20000-\u2a6df
# CJK symbols/punctuation: \u3000-\u303f, \uff00-\uffef
# These are the characters we DO allow (standard Chinese text + English/ASCII).
# We search for anything OUTSIDE of these.
pattern = re.compile(r'[^\x00-\x7f\u4e00-\u9fff\u3400-\u4dbf\u20000-\u2a6df\u3000-\u303f\uff00-\uffef]')

findings = []
for root, dirs, files in os.walk(target_dir):
    # Only check template directory and test_emoji.py
    if 'template' not in root and 'test_emoji.py' not in files:
        continue
    for file in files:
        if file.endswith(('.yaml', '.py')):
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f, 1):
                        if pattern.search(line):
                            findings.append(f"{path}:{i}: {line.strip()}")
            except Exception as e:
                findings.append(f"Error reading {path}: {e}")

if findings:
    print("\n".join(findings))
else:
    print("None found")
