# Standardized Tuberculosis Test Detection Patterns

## Skin Test Patterns and Keywords

```python
skin_test_keywords = {
    # Test names and abbreviations
    "Test": [
        "tuberculin skin test <95%>",
        "mantoux tuberculin test <95%>",
        "purified protein derivative <90%>",
        "ppd skin test <95%>",
        "tst <90%>",
        "ppd <90%>",
        "mt <70%>",
        "mantoux test <95%>",
        "tuberculosis skin test <95%>",
        "tb skin test <90%>",
        "mantoux <95%>",
        "mantoux tuberculin skin test <95%>",
        "tuberculin test <90%>",
        "two-step tst <95%>",
        "two-step tuberculin <95%>",
        "ppd test <85%>"
    ],
    
    # Process descriptions
    "Process": [
        "intradermal injection <85%>",
        "intradermal tuberculin <90%>",
        "mantoux technique <95%>",
        "intradermal tst <95%>",
        "skin tuberculin <90%>",
        "tuberculin skin reaction <90%>",
        "tb skin testing <90%>",
        "tb skin reactivity <90%>",
        "intradermal ppd <95%>",
        "skin reactivity <80%>",
        "tuberculin reaction <85%>"
    ],
    
    # Administration terms
    "Administration": [
        "tuberculin administered <90%>",
        "tst administered <95%>",
        "tst performed <95%>",
        "ppd administered <95%>",
        "ppd placed <95%>",
        "skin test done <85%>",
        "skin test performed <85%>",
        "mantoux administered <95%>",
        "skin test given <85%>",
        "tb skin test administered <95%>",
        "mantoux placed <90%>",
        "placed ppd <90%>",
        "administered ppd <90%>",
        "tst placed <90%>",
        "tb skin test completed <90%>"
    ],
    
    # Documentation and results
    "Documentation": [
        "tuberculin test result <95%>",
        "tst result <95%>",
        "induration <95%>",
        "skin test reading <90%>",
        "induration <95%>",
        "skin reaction measurement <90%>",
        "millimeters induration <95%>",
        "mm induration <90%>",
        "mm of induration <95%>",
        "induration size <90%>",
        "tst reading <90%>",
        "skin test diameter <90%>",
        "ppd reaction <85%>",
        "ppd skin test result <95%>",
        "tuberculin reading <85%>",
        "tested with tuberculin <85%>"
    ]
}

skin_test_patterns = {
    # Test name patterns
    "Test": [
        r"\btuberculin\s+skin\s+test\b <95%>",
        r"\btst\b(?!.*\bdid\s+not\b) <90%>",
        r"\bppd\b(?!\s+test\s+not\s+performed) <90%>",
        r"\bmantoux\b(?:\s+test)? <95%>",
        r"\btb\s+skin\s+test\b <95%>",
        r"\btuberculin\s+test\b <90%>",
        r"\bmantoux\s+tuberculin\s+test\b <95%>",
        r"\bmt\b(?:\s+test)? <70%>",
        r"\btwo[\s-]step\s+(?:tst|tuberculin|skin\s+test)\b <95%>"
    ],
    
    # Process patterns
    "Process": [
        r"(?:intradermal|skin)\s+(?:injection|test)\s+(?:of|with)\s+(?:tuberculin|ppd) <95%>",
        r"(?:skin|tuberculin)\s+testing\s+(?:performed|done|administered|completed) <90%>"
    ],
    
    # Administration patterns
    "Administration": [
        r"(?:received|administered|placed)[\s:]+(?:a\s+)?(?:tuberculin|ppd|mantoux|skin\s+test) <95%>",
        r"(?:tst|tuberculin|ppd)\s+(?:given|performed|administered|done|placed)\s+on <95%>"
    ],
    
    # Documentation patterns
    "Documentation": [
        r"induration(?:\s+of)?\s+(\d+)(?:\s*|-*)mm <95%>",
        r"(\d+)(?:\s*|-*)mm(?:\s+of)?\s+induration <95%>",
        r"skin\s+test\s+(?:result|reading)[\s:]+(\d+)(?:\s*|-*)mm <95%>",
        r"(?:tst|ppd|mantoux)\s+(?:result|reading)[\s:]+(\d+)(?:\s*|-*)mm <95%>",
        r"(?:tst|ppd|mantoux)[\s:]+(\d+)(?:\s*|-*)mm <90%>",
        r"induration[\s:]+(\d+)(?:\s*|-*)mm <95%>",
        r"tuberculin\s+reaction[\s:]+(\d+)(?:\s*|-*)mm <90%>",
        r"(?:tst|skin\s+test|tuberculin|ppd)\s+(?:result|interpretation|reading)[\s:]+(?:positive|negative|indeterminate) <95%>",
        r"(?:positive|negative)\s+(?:tst|skin\s+test|ppd|mantoux)\s+(?:result|reading) <95%>",
        r"(?:tst|ppd|mantoux|tuberculin)\s+(?:reading|result)\s+(?:is|was)\s+(?:positive|negative) <95%>",
        r"(?:read|interpreted)\s+(?:the|a)\s+(?:tst|ppd|mantoux|tuberculin|skin\s+test) <85%>"
    ]
}
```

## Blood Test Patterns and Keywords

```python
blood_test_keywords = {
    # Test names and abbreviations
    "Test": [
        "interferon gamma release assay <95%>",
        "quantiferon tb gold <95%>",
        "quantiferon tb gold plus <95%>",
        "quantiferon gold in-tube <95%>",
        "t-spot tb test <95%>",
        "tb blood test <90%>",
        "interferon-gamma release assay <95%>",
        "interferon gamma test <90%>",
        "tb blood assay <90%>",
        "tb antigen test <85%>",
        "igra test <95%>",
        "qft-git <95%>",
        "qft-plus <95%>",
        "qft-g <95%>",
        "t-spot.tb <95%>",
        "igra <90%>",
        "qft <90%>",
        "t-spot <90%>",
        "ifn-gamma <85%>",
        "qft-gp <95%>",
        "quantiferon gold test <95%>",
        "tb gamma test <90%>"
    ],
    
    # Process descriptions
    "Process": [
        "interferon gamma <80%>",
        "tb antigen response <90%>",
        "mitogen response <90%>",
        "tb antigen minus nil <95%>",
        "nil value <85%>",
        "tb response <80%>",
        "mitogen value <90%>",
        "tb1 antigen <95%>",
        "tb2 antigen <95%>",
        "antigen tube <85%>",
        "spot forming cells <95%>",
        "ifn-γ response <90%>",
        "tb tube result <90%>",
        "interferon assay <85%>"
    ],
    
    # Administration terms
    "Administration": [
        "blood drawn for tb <90%>",
        "blood collected for igra <95%>",
        "quantiferon performed <95%>",
        "igra testing completed <95%>",
        "ordered igra <90%>",
        "ordered quantiferon <90%>",
        "ordered t-spot <90%>",
        "drawn for quantiferon <95%>",
        "igra sent <85%>",
        "igra ordered <90%>",
        "performed igra <95%>",
        "blood sample for tb <90%>",
        "qft collection <95%>",
        "qft tubes <95%>"
    ],
    
    # Documentation and results
    "Documentation": [
        "tb blood test resulted <95%>",
        "igra result <95%>",
        "elispot result <90%>",
        "quantiferon result <95%>",
        "blood test for tb <90%>",
        "tb blood work <85%>",
        "tb blood screening <90%>"
    ]
}

blood_test_patterns = {
    # Test name patterns
    "Test": [
        r"\b(?:interferon[\s-]*gamma[\s-]*release[\s-]*assay|igra)\b(?!\s+not\s+performed) <95%>",
        r"\bquantiferon[\s-]*(?:tb)?[\s-]*gold(?:[\s-]*plus)?\b <95%>",
        r"\bt[\s-]*spot\.?tb\b <95%>",
        r"\bqft[\s-]*(?:g|git|plus|p|gp)?\b <90%>",
        r"\btb\s+blood\s+test\b <90%>",
        r"\binterferon[\s-]*gamma\s+test\b <90%>",
        r"\btb\s+blood\s+assay\b <90%>",
        r"\bigra\b(?!\s+not\s+performed) <90%>",
        r"\bt[\s-]*spot\b(?!\s+not\s+performed) <85%>"
    ],
    
    # Process patterns
    "Process": [
        r"(?:tb\d|tb[\s-]antigen[\s-]\d)[\s:]+(?:\d+\.?\d*) <95%>",
        r"(?:spot[\s-]forming[\s-]cells|sfc)[\s:]+(?:\d+) <95%>",
        r"interferon[\s-]*gamma[\s:]+(?:level|value)[\s:]+(?:\d+\.?\d*) <90%>",
        r"(?:tb\s+antigen|mitogen)[\s-]*minus[\s-]*nil[\s:]+(?:\d+\.?\d*) <95%>",
        r"elispot[\s:]+(?:result|count) <95%>",
        r"spot[\s-]*forming[\s-]*(?:cells|units) <95%>",
        r"ifn[\s-]*(?:gamma|γ)[\s:]+(?:release|production|response) <90%>"
    ],
    
    # Administration patterns
    "Administration": [
        r"(?:blood|specimen)\s+(?:collected|drawn)\s+for\s+(?:igra|quantiferon|t-spot|tb\s+blood\s+test) <95%>",
        r"(?:performed|completed|conducted|ordered)\s+(?:a\s+)?(?:igra|quantiferon|t-spot|tb\s+blood\s+test) <95%>",
        r"(?:sent|collected)\s+(?:specimen|sample|blood)\s+for\s+(?:igra|quantiferon|t-spot) <95%>",
        r"(?:blood|specimen)[\s:]+(?:igra|quantiferon|t-spot|tb\s+blood\s+test) <90%>",
        r"(?:igra|quantiferon|t-spot)\s+collection <95%>",
        r"(?:igra|quantiferon|t-spot)\s+(?:drawn|sent|ordered) <95%>"
    ],
    
    # Documentation patterns
    "Documentation": [
        r"(?:igra|quantiferon|t-spot)[\s:]+(?:result|interpretation)[\s:]+(?:positive|negative|indeterminate) <95%>",
        r"(?:tb\s+antigen|mitogen)[\s:]+(?:response|result)[\s:]+(?:\d+\.?\d*) <95%>",
        r"(?:nil|tb\s+ag|mitogen)[\s:]*(?:\d+\.?\d*) <90%>",
        r"quantiferon[\s:]+(?:positive|negative|indeterminate) <95%>",
        r"t[\s-]spot[\s:]+(?:positive|negative|indeterminate) <95%>",
        r"igra[\s:]+(?:positive|negative|indeterminate) <95%>",
        r"interferon[\s-]*gamma[\s-]*analysis <90%>",
        r"qft[\s-]*(?:g|git|plus|p)[\s:]+result <95%>"
    ]
}
```

## X-ray Patterns and Keywords

```python
xray_keywords = {
    # Test names and abbreviations
    "Test": [
        "x-ray <95%>",
        "chest x-ray <95%>",
        "chest radiograph <95%>",
        "chest radiography <95%>",
        "chest imaging <90%>",
        "thoracic radiograph <90%>",
        "chest film <90%>",
        "chest roentgenogram <95%>",
        "thoracic x-ray <90%>",
        "chest xray <95%>",
        "pulmonary x-ray <90%>",
        "lung x-ray <85%>",
        "tb chest x-ray <95%>",
        "cxr <90%>",
        "pa chest <95%>",
        "ap chest <95%>",
        "lateral chest <90%>",
        "chest pa <95%>",
        "pa and lateral <90%>",
        "pa/lat <90%>",
        "pa & lat <90%>",
        "ap/lat <90%>",
        "chest pa/lat <95%>",
        "cxr pa <95%>",
        "chest ct <80%>",
        "lung ct <80%>",
        "thoracic ct <80%>",
        "chest tomography <85%>"
    ],
    
    # Process descriptions
    "Process": [
        "pulmonary radiograph <90%>",
        "thoracic imaging <85%>",
        "lung field imaging <90%>",
        "radiological examination chest <95%>",
        "pulmonary imaging <85%>",
        "pleural imaging <85%>",
        "chest scan <80%>",
        "mediastinal imaging <85%>",
        "x-ray of chest <95%>",
        "radiograph of thorax <90%>",
        "portable chest <90%>",
        "imaging of chest <90%>",
        "radiology chest <90%>"
    ],
    
    # Administration terms
    "Administration": [
        "chest x-ray completed <95%>",
        "chest radiography performed <95%>",
        "chest radiology examination <95%>",
        "chest imaging performed <90%>",
        "cxr obtained <95%>",
        "chest films taken <90%>",
        "chest x-ray ordered <90%>",
        "cxr ordered <90%>",
        "chest x-ray done <95%>",
        "chest radiograph obtained <95%>"
    ],
    
    # Documentation and results
    "Documentation": [
        "x-ray chest <95%>",
        "tb x-ray <90%>",
        "chest x-ray findings <95%>",
        "chest x-ray reviewed <90%>"
    ]
}

