
from bs4 import BeautifulSoup


h = """<h1>Product1</h1>"""

# Name
soup = BeautifulSoup(h, 'html.parser')
name_selector = ("h1")
name_tag = soup.find(
    name_selector
)
if name_tag:
    name = name_tag.get_text(strip=True)
    print(name)
else:
    print('no name tag found')