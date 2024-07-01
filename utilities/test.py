from html.parser import HTMLParser
import re


def html_to_plain_text(html):
    parser = HTMLTextExtractor()
    parser.feed(html)
    text = ''.join(parser.result)
    # Clean up extra whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text).strip()
    return text

# Example usage
html = """
<h1>Hello World</h1>
<p>This is a paragraph.</p>
<ul>
    <li>Item 1</li>
    <li>Item 2</li>
</ul>
"""

plain_text = html_to_plain_text(html)
print(plain_text)