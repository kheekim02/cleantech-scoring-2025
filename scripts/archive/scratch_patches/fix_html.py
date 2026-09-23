with open('site/index.html', 'r') as f:
    html = f.read()

html = html.replace('''      <div class="right-scroll-area">
        
        
        </div>''', '''      <div class="right-scroll-area">''')

with open('site/index.html', 'w') as f:
    f.write(html)
