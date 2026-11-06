#!/usr/bin/env python3
"""Discovery for categories 01-12 from arXiv (via DataCite) and PMC open access (via Europe PMC).
Window: first published 2023-10-29 .. 2026-11-06. Screening per the old screening_rules_cn.md. Cached per query."""
import hashlib,json,os,re,time,urllib.parse,urllib.request
B='/srv/ipm_build'; UA={'User-Agent':'ipm-literature-builder/1.0'}; C=B+'/state/qcache'; os.makedirs(C,exist_ok=True)
exec(open(B+'/tools/cats.py').read())
EXC=re.compile(r'intrusion|cyber|attack|business process|process mining|patient|clinical|hospital|covid|medical|traffic flow|financial|stock market|credit|social network|software log|microservice|epidem|cancer|tumou?r|disease',re.I)
REQ=re.compile(r'industr|plant|manufactur|chemical|fault|soft sensor|batch process|ferment|tennessee|reactor|refin|wastewater|steel|semiconductor|process monitoring|process control',re.I)
def get(u):
    k=C+'/'+hashlib.md5(u.encode()).hexdigest()+'.json'
    if os.path.exists(k): return json.load(open(k))
    for i in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=90) as r: d=json.load(r)
            json.dump(d,open(k,'w')); time.sleep(1.5); return d
        except Exception as e:
            err=e; time.sleep(10*(i+1))
    print('FAIL',u[:120],err,flush=True); return None
out={}
def add(key,rec,c,q,rank):
    t=rec['title']; ab=rec.get('abstract') or ''
    if EXC.search(t+' '+ab[:3000]) or not REQ.search(t+' '+ab): return
    e=out.setdefault(key,rec); e.setdefault('hits',{}).setdefault(c,[]).append([q,rank])
for c,v in CATS.items():
    for q in v['q']:
        # arXiv through DataCite
        qs=f'(titles.title:"{q}" OR descriptions.description:"{q}") AND publicationYear:[2023 TO 2026]'
        if ' ' in q and not q.startswith('"'):
            words=' AND '.join(w for w in q.split() if len(w)>2)
            qs=f'(titles.title:({words}) OR descriptions.description:({words})) AND publicationYear:[2023 TO 2026]'
        d=get('https://api.datacite.org/dois?'+urllib.parse.urlencode({'query':qs,'client-id':'arxiv.content','page[size]':'100'}))
        for rank,x in enumerate((d or {}).get('data',[])):
            a=x['attributes']; aid=a['doi'].split('arxiv.',1)[-1]
            sub=sorted(t['date'][:10] for t in a.get('dates',[]) if t.get('dateType')=='Submitted')
            if not sub or sub[0]<'2023-10-29': continue
            jdoi=[r['relatedIdentifier'] for r in a.get('relatedIdentifiers',[]) if r.get('relatedIdentifierType')=='DOI' and r.get('relationType')=='IsVersionOf']
            add('arxiv:'+aid.lower(),dict(src='arxiv',arxiv=aid,title=re.sub(r'\s+',' ',a['titles'][0]['title']),date=sub[0],
                authors=[p.get('name') for p in a.get('creators',[])][:12],lic=[r.get('rightsUri') for r in a.get('rightsList',[])],
                abstract=re.sub(r'\s+',' ',(a.get('descriptions') or [{}])[0].get('description','')),doi=(jdoi or [None])[0],
                pdf=f'https://arxiv.org/pdf/{aid}',page=f'https://arxiv.org/abs/{aid}'),c,q,rank)
        # PMC open access through Europe PMC
        eq=f'"{q}" AND OPEN_ACCESS:y AND IN_PMC:y AND FIRST_PDATE:[2023-10-29 TO 2026-11-06]' if len(q.split())<=3 else f'({q}) AND OPEN_ACCESS:y AND IN_PMC:y AND FIRST_PDATE:[2023-10-29 TO 2026-11-06]'
        d=get('https://www.ebi.ac.uk/europepmc/webservices/rest/search?'+urllib.parse.urlencode({'query':eq,'format':'json','pageSize':'100','resultType':'core'}))
        for rank,r in enumerate(((d or {}).get('resultList') or {}).get('result',[])):
            if not r.get('pmcid'): continue
            add('pmc:'+r['pmcid'],dict(src='pmc',pmcid=r['pmcid'],doi=r.get('doi'),title=re.sub(r'<[^>]+>','',r.get('title','')).strip(),date=r.get('firstPublicationDate'),
                authors=[a.get('fullName') for a in (r.get('authorList') or {}).get('author',[])][:12],lic=[r.get('license')],
                abstract=re.sub(r'<[^>]+>','',r.get('abstractText','') or ''),venue=(r.get('journalInfo') or {}).get('journal',{}).get('title'),
                page=f"https://pmc.ncbi.nlm.nih.gov/articles/{r['pmcid']}/"),c,q,rank)
    print(c,v['name'],'candidates',len(out),flush=True)
json.dump(out,open(B+'/state/candidates.json','w'),ensure_ascii=False)
print('DONE',len(out))
