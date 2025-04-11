# Tuberculosis Test Detection Patterns

## Skin Test Detection

```python
skin_test_keywords = [
    # Official test names
    "tuberculin skin test",
    "mantoux tuberculin test",
    "purified protein derivative",
    "ppd skin test",
    "tst result",
    
    # Testing process terms
    "intradermal injection",
    "intradermal tuberculin",
    "mantoux technique",
    "tuberculin administered",
    
    # Result measurement terms
    "induration measured",
    "skin test reading",
    "induration diameter",
    "skin reaction measurement",
    "millimeters induration",
    
    # Documentation phrases
    "tst administered",
    "tst performed",
    "ppd administered",
    "ppd placed",
    "tuberculin test result"
]

skin_test_patterns = [
    # Precise test name matches
    r"\btuberculin\s+skin\s+test\b",
    r"\btst\b(?!.*\bdid\s+not\b)",  # TST but not "did not TST"
    r"\bppd\b(?!\s+test\s+not\s+performed)",  # PPD but not when not performed
    r"\bmantoux\b(?:\s+test)?",
    
    # Measurement patterns
    r"induration(?:\s+of)?\s+(\d+)(?:\s*|-*)mm",
    r"(\d+)(?:\s*|-*)mm(?:\s+of)?\s+induration",
    r"skin\s+test\s+(?:result|reading)[\s:]+(\d+)(?:\s*|-*)mm",
    
    # Administration documentation
    r"(?:received|administered|placed)[\s:]+(?:a\s+)?(?:tuberculin|ppd|mantoux|skin\s+test)",
    r"(?:tst|tuberculin|ppd)\s+(?:given|performed|administered)\s+on",
    
    # Result reporting
    r"(?:tst|skin\s+test|tuberculin|ppd)\s+(?:result|interpretation)[\s:]+(?:positive|negative|indeterminate)",
    r"(?:positive|negative)\s+(?:tst|skin\s+test|ppd|mantoux)\s+(?:result|reading)"
]
```

## Blood Test Detection

```python
blood_test_keywords = [
    # Full test names
    "interferon gamma release assay",
    "quantiferon tb gold",
    "quantiferon tb gold plus",
    "quantiferon gold in-tube",
    "t-spot tb test",
    
    # Common abbreviations
    "igra test",
    "qft-git",
    "qft-plus",
    "qft-g",
    "t-spot.tb",
    
    # Test result terms
    "interferon gamma",
    "tb antigen response",
    "mitogen response",
    "tb antigen minus nil",
    "igra result",
    
    # Documentation phrases
    "blood drawn for tb",
    "blood collected for igra",
    "quantiferon performed",
    "igra testing completed",
    "tb blood test resulted"
]

blood_test_patterns = [
    # Precise test name matches
    r"\b(?:interferon[\s-]*gamma[\s-]*release[\s-]*assay|igra)\b(?!\s+not\s+performed)",
    r"\bquantiferon[\s-]*(?:tb)?[\s-]*gold(?:[\s-]*plus)?\b",
    r"\bt[\s-]*spot\.?tb\b",
    r"\bqft[\s-]*(?:g|git|plus|p)\b",
    
    # Result documentation
    r"(?:igra|quantiferon|t-spot)[\s:]+(?:result|interpretation)[\s:]+(?:positive|negative|indeterminate)",
    r"(?:tb\s+antigen|mitogen)[\s:]+(?:response|result)[\s:]+(?:\d+\.?\d*)",
    r"(?:nil|tb\s+ag|mitogen)[\s:]*(?:\d+\.?\d*)",
    
    # Administration documentation
    r"(?:blood|specimen)\s+(?:collected|drawn)\s+for\s+(?:igra|quantiferon|t-spot|tb\s+blood\s+test)",
    r"(?:performed|completed|conducted)\s+(?:a\s+)?(?:igra|quantiferon|t-spot)",
    
    # Technical result reporting
    r"(?:interferon[\s-]*gamma|ifn[\s-]*gamma)\s+(?:level|concentration|production)",
    r"(?:tb\s+antigen|mitogen)[\s-]*minus[\s-]*nil[\s:]+(?:\d+\.?\d*)",
    r"interferon[\s-]*gamma[\s-]*analysis"
]
```

## X-ray Detection

```python
xray_keywords = [
    # Standard terminology
    "chest x-ray",
    "chest radiograph",
    "chest radiography",
    "chest imaging",
    "thoracic radiograph",
    
    # Common abbreviations
    "cxr performed",
    "pa chest",
    "ap chest",
    "lateral chest",
    "chest pa",
    
    # Technical terms
    "pulmonary radiograph",
    "thoracic imaging",
    "chest film",
    "lung field imaging",
    "radiological examination chest",
    
    # Documentation phrases
    "x-ray of chest",
    "chest x-ray completed",
    "radiograph of thorax",
    "chest radiography performed",
    "chest radiology examination"
]

xray_patterns = [
    # Precise test name matches
    r"\bchest[\s-]*(?:x[\s-]*ray|radiograph|radiography|imaging)\b",
    r"\bcxr\b(?!\s+not\s+performed)",
    r"\b(?:pa|ap)[\s-]*(?:and)?[\s-]*(?:lateral)?[\s-]*chest\b",
    r"\bchest[\s-]*(?:pa|ap)[\s-]*(?:and)?[\s-]*(?:lateral)?\b",
    
    # Administration documentation
    r"(?:performed|obtained|completed|conducted)[\s:]+(?:a\s+)?(?:chest[\s-]*x[\s-]*ray|cxr|chest[\s-]*radiograph)",
    r"(?:chest|thoracic)[\s-]*(?:x[\s-]*ray|radiograph|imaging)\s+(?:done|performed|obtained)\s+on",
    
    # Result reporting
    r"(?:chest[\s-]*x[\s-]*ray|cxr|chest[\s-]*radiograph)[\s:]+(?:result|interpretation|finding)s?",
    r"radiolog(?:ical|y)\s+(?:examination|evaluation|assessment)\s+of\s+(?:chest|thorax|lung)",
    
    # Technical descriptions
    r"(?:infiltrate|opacity|consolidation|lesion)s?\s+(?:on|in|seen\s+in)\s+(?:chest[\s-]*x[\s-]*ray|cxr|radiograph)",
    r"(?:chest|lung|thoracic)[\s-]*(?:imaging|radiograph|x[\s-]*ray)\s+(?:shows|demonstrates|reveals)",
    r"chest[\s-]*film[\s-]*(?:review|interpretation|finding)"
]
```

## Implementation Recommendations

To further minimize false positives and negatives:

```python
def check_negative_context(text, test_type):
    negative_patterns = {
        "skin_test": [
            r"(?:skin\s+test|tst|ppd|mantoux)\s+(?:not|wasn't|wasn't|wasn't|never)\s+(?:performed|administered|done|given)",
            r"(?:declined|refused|rejected)\s+(?:the\s+)?(?:skin\s+test|tst|ppd|mantoux)",
            r"no\s+(?:skin\s+test|tst|ppd|mantoux)\s+(?:performed|administered|done|given)"
        ],
        "blood_test": [
            r"(?:igra|quantiferon|t-spot)\s+(?:not|wasn't|wasn't|wasn't|never)\s+(?:performed|drawn|done|collected)",
            r"(?:declined|refused|rejected)\s+(?:the\s+)?(?:igra|quantiferon|t-spot|blood\s+test)",
            r"no\s+(?:igra|quantiferon|t-spot|blood\s+test)\s+(?:performed|drawn|done|collected)"
        ],
        "xray": [
            r"(?:chest\s+x-ray|cxr|chest\s+radiograph)\s+(?:not|wasn't|wasn't|wasn't|never)\s+(?:performed|done|obtained)",
            r"(?:declined|refused|rejected)\s+(?:the\s+)?(?:chest\s+x-ray|cxr|chest\s+radiograph)",
            r"no\s+(?:chest\s+x-ray|cxr|chest\s+radiograph)\s+(?:performed|done|obtained)"
        ]
    }
    
    for pattern in negative_patterns[test_type]:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def check_contextual_proximity(text, match, test_type):
    # Examine text within ±100 characters of the match
    start = max(0, text.find(match) - 100)
    end = min(len(text), text.find(match) + len(match) + 100)
    context = text[start:end].lower()
    
    # Positive confirmatory phrases
    positive_context = [
        "performed", "administered", "given", "completed", 
        "conducted", "done", "resulted", "interpreted",
        "received", "results show", "reading shows"
    ]
    
    # Check for negative phrases in proximity
    if check_negative_context(context, test_type):
        return False
        
    # Check for positive confirmation
    for phrase in positive_context:
        if phrase in context:
            return True
            
    # Default to true if no negative indicators found
    return True

def detect_test(text, test_type):
    keywords = eval(f"{test_type}_keywords")
    patterns = eval(f"{test_type}_patterns")
    
    # Track matches for weighting
    keyword_matches = []
    pattern_matches = []
    
    # Check keywords
    for keyword in keywords:
        if keyword.lower() in text.lower():
            keyword_matches.append(keyword)
    
    # Check patterns
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            pattern_matches.extend(matches)
    
    # Decision logic
    if pattern_matches:  # Pattern matches are strongest evidence
        for match in pattern_matches:
            if check_contextual_proximity(text, match, test_type):
                return True
    
    if len(keyword_matches) >= 2:  # Multiple keyword matches increase confidence
        return True
    
    if keyword_matches and not check_negative_context(text, test_type):
        return True
        
    return False
```

## Complete Example Implementation

```python
import re

class TBTestDetector:
    def __init__(self):
        # Initialize keyword and pattern lists (from above)
        # [skin_test_keywords, skin_test_patterns, etc.]
        
    def detect_tests(self, ocr_text):
        text = ocr_text.lower()
        
        # Initialize results
        results = {
            "skin_test": False,
            "blood_test": False, 
            "xray": False
        }
        
        # Check each test type
        for test_type in results.keys():
            results[test_type] = self.detect_test(text, test_type)
        
        return results
        
    def detect_test(self, text, test_type):
        # Implementation of detect_test function from above
        pass
        
    def check_negative_context(self, text, test_type):
        # Implementation of check_negative_context function from above
        pass
        
    def check_contextual_proximity(self, text, match, test_type):
        # Implementation of check_contextual_proximity function from above
        pass

# Example usage
detector = TBTestDetector()
results = detector.detect_tests("Patient received Quantiferon-TB Gold test on 3/15/2025. Chest X-ray performed.")
print(results)  # Expected: {'skin_test': False, 'blood_test': True, 'xray': True}
```
