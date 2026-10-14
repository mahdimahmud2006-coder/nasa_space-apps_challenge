"""Static HTML/CSS/local-asset checks. This does not execute or render a browser."""
from html.parser import HTMLParser
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
VOID={'meta','link','br','input','hr','img','source','wbr','area','base','embed','param','track','col'}


class Page(HTMLParser):
    def __init__(self):super().__init__();self.ids=[];self.stack=[];self.assets=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'id' in attrs:self.ids.append(attrs['id'])
        if tag not in VOID:self.stack.append(tag)
        if tag=='script' and attrs.get('src'):self.assets.append(attrs['src'])
        if tag=='link' and attrs.get('rel')=='stylesheet':self.assets.append(attrs['href'])
    def handle_endtag(self,tag):
        if not self.stack or self.stack[-1]!=tag:raise ValueError('HTML nesting mismatch: '+tag)
        self.stack.pop()


def check(root=ROOT):
    root=Path(root);report={}
    for name,script in [('index','studio.mjs'),('change-lab','change-lab.mjs'),('timeseries','timeseries.js'),('comparison','app.js')]:
        page=Page();page.feed((root/'web'/(name+'.html')).read_text())
        assert not page.stack and len(page.ids)==len(set(page.ids))
        for asset in page.assets:
            assert not asset.startswith(('http:','https:','//')),'Runtime external asset: '+asset
            assert (root/'web'/asset.lstrip('/')).is_file(),'Missing script/CSS: '+asset
        refs=set(re.findall(r"\$\('([^']+)'\)",(root/'web'/script).read_text()))
        assert refs.issubset(page.ids),'Unknown page IDs: '+str(refs-set(page.ids))
        report[name]={'unique_ids':len(page.ids),'javascript_literal_ids_resolve':len(refs),'balanced_html':True,'all_scripts_css_local':True}
    for path in (root/'web').glob('*.css'):
        css=path.read_text();assert css.count('{')==css.count('}'),'Unbalanced CSS: '+path.name
    return {'status':'STATIC_CHECKS_PASS','pages':report,'scope':'Source consistency only; browser visual, accessibility, GPU and responsive verification remain separate.'}


if __name__=='__main__':print(json.dumps(check(),indent=2))
