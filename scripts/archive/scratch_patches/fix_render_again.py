with open('site/js/render.js', 'r') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if "const aiCat = aiCats[stepCat];" in line:
        skip = True
        continue
    
    if skip and "aiPillsContainer.innerHTML = '';" in line:
        skip = False
        continue
    
    if skip and "}" in line.strip() and len(line.strip()) == 1:
        # this might match the closing brace of the else block. Let's just use string parsing
        pass

with open('site/js/render.js', 'r') as f:
    code = f.read()

# safely remove the block
start_str = "    const aiCat = aiCats[stepCat];"
end_str = "aiPillsContainer.innerHTML = '';\n    }"

if start_str in code and end_str in code:
    start_idx = code.find(start_str)
    end_idx = code.find(end_str) + len(end_str)
    code = code[:start_idx] + code[end_idx:]
    with open('site/js/render.js', 'w') as f:
        f.write(code)
    print("Successfully removed the AI pills logic!")
else:
    print("Could not find the exact strings.")

