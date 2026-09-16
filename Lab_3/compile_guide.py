import markdown

with open('LAB_3_STUDENT_GUIDE.md', 'r', encoding='utf-8') as f:
    md_text = f.read()

html_body = markdown.markdown(md_text, extensions=['tables', 'fenced_code'])

full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Lab 3: Secure Voice Model over IPSec Tunnel</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; line-height: 1.6; color: #24292e; max-width: 980px; margin: 0 auto; padding: 40px 20px; background-color: #fff; }}
    h1, h2, h3, h4 {{ color: #1a202c; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; margin-top: 28px; margin-bottom: 16px; font-weight: 600; }}
    h1 {{ font-size: 2em; }} h2 {{ font-size: 1.5em; }} h3 {{ font-size: 1.25em; }}
    pre {{ background-color: #f6f8fa; border-radius: 6px; padding: 16px; overflow: auto; font-size: 85%; line-height: 1.45; border: 1px solid #e1e4e8; }}
    code {{ background-color: rgba(27,31,35,0.05); border-radius: 3px; font-size: 85%; margin: 0; padding: 0.2em 0.4em; font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, Courier, monospace; }}
    pre code {{ background-color: transparent; padding: 0; }}
    img {{ max-width: 100%; height: auto; border-radius: 6px; border: 1px solid #d1d5db; margin: 16px 0; display: block; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }}
    table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
    th, td {{ border: 1px solid #dfe2e5; padding: 8px 12px; text-align: left; }}
    th {{ background-color: #f6f8fa; font-weight: 600; }}
    tr:nth-child(2n) {{ background-color: #fcfcfc; }}
    blockquote {{ padding: 0 1em; color: #6a737d; border-left: 0.25em solid #dfe2e5; margin: 0 0 16px 0; }}
    details {{ background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px; margin: 12px 0; }}
    summary {{ font-weight: 600; cursor: pointer; color: #2b6cb0; }}
  </style>
</head>
<body>
{html_body}
</body>
</html>"""

with open('LAB_3_STUDENT_GUIDE.html', 'w', encoding='utf-8') as f:
    f.write(full_html)

print('Compiled LAB_3_STUDENT_GUIDE.html successfully')
