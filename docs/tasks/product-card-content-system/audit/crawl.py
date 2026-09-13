# Обход витрины biz-soft.pro: скачать страницы из sitemap в ./pages (см. products.txt), затем запустить. Выход: products.csv и crawl-stats.json.
import os,re,csv,json,collections
from bs4 import BeautifulSoup
rows=[]; stats=collections.defaultdict(collections.Counter)
for fn in sorted(os.listdir('pages')):
    s=BeautifulSoup(open('pages/'+fn,encoding='utf-8'),'lxml')
    for t in s(['script','style','svg']): t.decompose()
    main=s.find('main') or s.body; txt=main.get_text('\n',strip=True)
    g=lambda p: (re.search(p,txt) or [None,''])[1]
    h1=s.find('h1').get_text(' ',strip=True)
    r={'slug':fn[:-5],'h1':h1,'marker':(re.search(r'(Командный план|Универсальный план|Индивидуальный план|Универсальный продукт|Дополнение к продукту)',txt[:300]) or [None,''])[1],
       'vendor':g(r'Производитель:\n([^\n]+)'),'term':g(r'Срок:\n([^\n]+)'),'unit':g(r'Расчётная единица:\n([^\n]+)'),'min_qty':g(r'Минимальное количество:\n([^\n]+)'),
       'sku':g(r'Артикул BIZSoft:\n([^\n]+)'),'category':g(r'Категория:\n([^\n]+)'),
       'hero_starts_vhodit':int('Что входит:' in txt[:2500] or 'Что входит на каждое место' in txt[:2500]),
       'has_faq':int('Частые вопросы' in txt),'has_related':int('Похожие товары' in txt),'has_seo_text':int('prose-bizsoft block' in open('pages/'+fn,encoding='utf-8',errors='ignore').read()),
       'has_use_cases':int('Какие задачи закрывает' in txt),'h2s':' | '.join(h.get_text(' ',strip=True).strip('/ ') for h in main.find_all('h2'))}
    rows.append(r)
    for k in ['marker','unit','min_qty','term']: stats[k][r[k]]+=1
    for ph in ['Кому подходит:','Оформим','Типичный сценарий','Чем отличается']: stats['phrases'][ph]+=int(ph in txt)
    for h in main.find_all('h2'): stats['h2'][h.get_text(' ',strip=True).strip('/ ')]+=1
    stats['flags']['hero_starts_vhodit']+=r['hero_starts_vhodit']; stats['flags']['has_faq']+=r['has_faq']; stats['flags']['has_related']+=r['has_related']; stats['flags']['has_seo_text']+=r['has_seo_text']
with open('/mnt/user-data/outputs/audit/products.csv','w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
json.dump({'crawled_at':'2026-09-13','pages':len(rows),**{k:dict(v.most_common()) for k,v in stats.items()}},open('/mnt/user-data/outputs/audit/crawl-stats.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
print(len(rows))
