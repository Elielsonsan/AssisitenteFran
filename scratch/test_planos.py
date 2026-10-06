import os
import re

path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'professor_planos_aula.html')
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

div_open = len(re.findall(r'<div', html))
div_close = len(re.findall(r'</div', html))

print(f"<div> count: {div_open}, </div> count: {div_close}")
if div_open == div_close:
    print("Tags div balanceadas.")
else:
    print("ERRO: Tags div desbalanceadas.")

assert 'planos-hero-outer hero-card-outer' in html
assert 'planos-box-outer card-moldura-outer' in html
print("Todas as classes presentes.")
