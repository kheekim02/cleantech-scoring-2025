import re

# 1. Update index.html
with open('site/index.html', 'r') as f:
    html = f.read()

# Find and remove the AI Verified Section block
pattern_html = r'<!-- AI Verified Section -->.*?</div>\s*</div>'
html_cleaned = re.sub(pattern_html, '', html, flags=re.DOTALL)

with open('site/index.html', 'w') as f:
    f.write(html_cleaned)

# 2. Update render.js
with open('site/js/render.js', 'r') as f:
    render_js = f.read()

# We need to carefully remove the block that updates the AI pills container
# to prevent "null is not an object" errors when it tries to find those elements
pattern_js = r'const aiCat = aiCats\[stepCat\];.*?aiPillsContainer\.innerHTML = \'\;\n    \}'
render_js_cleaned = re.sub(pattern_js, '', render_js, flags=re.DOTALL)

with open('site/js/render.js', 'w') as f:
    f.write(render_js_cleaned)

print("Removed AI Verified Tab from HTML and JS")
