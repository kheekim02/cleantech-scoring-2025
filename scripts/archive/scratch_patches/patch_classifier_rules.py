with open('10_ai_document_classifier_hybrid.py', 'r') as f:
    code = f.read()

# Replace m4 in TP with m4 in M
code = code.replace(
    "if 'ebd4' in f or 'm4questions' in f:\n        return 'TP', True",
    "if 'ebd4' in f:\n        return 'TP', True"
)
code = code.replace(
    "if 'ebd3' in f:\n        return 'M', True",
    "if 'ebd3' in f or 'm4questions' in f or 'm4_questions' in f or 'module_4' in f:\n        return 'M', True"
)

with open('10_ai_document_classifier_hybrid.py', 'w') as f:
    f.write(code)

print("Updated 10_ai_document_classifier_hybrid.py locally.")
