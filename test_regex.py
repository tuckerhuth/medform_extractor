import re

# Our patterns
pattern1 = r'\btst\s+administered(?:\s*,?\s*awaiting\s+results)?\b'
pattern2 = r'(?:tuberculin|ppd|skin\s+test)\s+(?:administered|performed|placed|done)(?:\s*,?\s*awaiting\s+results)?\b'

# Test phrases
test_phrases = [
    'TST administered, awaiting results',
    'tst administered',
    'TST ADMINISTERED',
    'tuberculin skin test administered, awaiting results',
    'PPD administered',
    'skin test performed, awaiting results',
    'TST placed',
    'tuberculin administered on patient',
    'TST results received',
    'administered medication'
]

print("Regex Pattern Testing Results:\n")

for phrase in test_phrases:
    print(f"Testing phrase: \"{phrase}\"")
    match1 = re.search(pattern1, phrase, re.IGNORECASE)
    match2 = re.search(pattern2, phrase, re.IGNORECASE)
    print(f"Pattern 1 (TST): {'✓ MATCH' if match1 else '✗ NO MATCH'}")
    print(f"Pattern 2 (General): {'✓ MATCH' if match2 else '✗ NO MATCH'}")
    print() 