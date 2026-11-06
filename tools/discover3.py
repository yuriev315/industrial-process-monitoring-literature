#!/usr/bin/env python3
"""Second discovery pass: phrase pairs, matched in title or abstract only. Merges into candidates.json."""
import hashlib,json,os,re,time,urllib.parse,urllib.request
B='/srv/ipm_build'; UA={'User-Agent':'ipm-literature-builder/1.0'}; C=B+'/state/qcache'
P={'01':[("process monitoring","review"),("fault detection","review"),("statistical process control",None),("control chart",None),("alarm management",None),("alarm flood",None),("profile monitoring",None),("multivariate statistical process monitoring",None)],
'02':[("process monitoring","principal component"),("fault detection","principal component"),("process monitoring","partial least squares"),("process monitoring","slow feature"),("fault detection","canonical variate"),("process monitoring","canonical correlation"),("process monitoring","independent component"),("process monitoring","latent variable"),("fault detection","kernel principal"),("process monitoring","Bayesian")],
'03':[("process monitoring","autoencoder"),("fault detection","autoencoder"),("fault diagnosis","Tennessee Eastman"),("process monitoring","transformer"),("process monitoring","graph neural"),("fault detection","LSTM"),("process monitoring","deep learning"),("fault diagnosis","chemical process"),("process monitoring","contrastive")],
'04':[("incipient fault",None),("anomaly detection","industrial process"),("anomaly detection","chemical process"),("early fault detection",None),("fault detection","false alarm"),("process monitoring","anomaly"),("process monitoring","drift")],
'05':[("root cause analysis",None),("root cause","fault"),("fault diagnosis","causal"),("fault propagation",None),("fault isolation",None),("contribution plot",None),("fault diagnosis","interpretable"),("alarm","root cause"),("transfer entropy","fault")],
'06':[("multimode process",None),("multimode","monitoring"),("nonstationary process",None),("non-stationary","process monitoring"),("transfer learning","fault diagnosis"),("domain adaptation","fault diagnosis"),("dynamic process monitoring",None),("operating condition","process monitoring"),("continual learning","fault")],
'07':[("soft sensor",None),("soft sensing",None),("quality-related",None),("quality prediction","industrial process"),("virtual metrology",None),("just-in-time learning",None),("inferential sensor",None),("key performance indicator","process monitoring")],
'08':[("batch process",None),("fermentation","monitoring"),("bioprocess monitoring",None),("bioprocess","soft sensor"),("penicillin","fermentation"),("process analytical technology",None),("pharmaceutical manufacturing","monitoring"),("batch","fault detection"),("cell culture","process monitoring")],
'09':[("hybrid model","chemical process"),("hybrid modeling","bioprocess"),("digital twin","process monitoring"),("digital twin","fault"),("physics-informed","chemical process"),("state estimation","chemical process"),("observer","fault detection"),("system identification","industrial process"),("grey-box model",None),("mechanistic","machine learning")],
'10':[("large language model","fault"),("large language model","industrial"),("large language model","chemical process"),("foundation model","time series"),("foundation model","industrial"),("multimodal","fault diagnosis"),("knowledge graph","fault"),("few-shot","fault diagnosis"),("agent","chemical process")],
'11':[("Tennessee Eastman",None),("benchmark","fault detection"),("benchmark","process monitoring"),("dataset","fault detection"),("dataset","industrial anomaly detection"),("three-phase flow",None),("data leakage","time series"),("evaluation","time series anomaly detection")],
'12':[("wastewater treatment","monitoring"),("wastewater","fault"),("blast furnace",None),("steel","process monitoring"),("power plant","fault detection"),("thermal power","monitoring"),("semiconductor","process monitoring"),("semiconductor","fault detection"),("cement","monitoring"),("refinery","fault"),("flotation","monitoring"),("hot rolling",None),("boiler","fault"),("oil and gas","fault detection"),("nuclear power plant","fault")]}
def get(u):
    k=C+'/'+hashlib.md5(u.encode()).hexdigest()+'.json'
    if os.path.exists(k): return json.load(open(k))
    for i in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=120) as r: d=json.load(r)
            json.dump(d,open(k,'w')); time.sleep(1.5); return d
        except Exception as e: err=e; time.sleep(10*(i+1))
    print('FAIL',u[:100],err,flush=True); return None
cand=json.load(open(B+'/state/candidates.json')); n0=len(cand)
def add(key,rec,c,q,rank):
    e=cand.setdefault(key,rec); e.setdefault('hits',{}).setdefault(c,[]).append([q,rank])
for c,pairs in P.items():
    for a,b in pairs:
        q=a if not b else f'{a} + {b}'
        dc=f'(titles.title:"{a}" OR descriptions.description:"{a}")'+(f' AND (titles.title:"{b}" OR descriptions.description:"{b}")' if b else '')+' AND publicationYear:[2023 TO 2026]'
        d=get('https://api.datacite.org/dois?'+urllib.parse.urlencode({'query':dc,'client-id':'arxiv.content','page[size]':'300'}))
        for rank,x in enumerate((d or {}).get('data',[])):
            at=x['attributes']; aid=at['doi'].split('arxiv.',1)[-1]
            sub=sorted(t['date'][:10] for t in at.get('dates',[]) if t.get('dateType')=='Submitted')
            if not sub or sub[0]<'2023-10-29': continue
            jdoi=[r['relatedIdentifier'] for r in at.get('relatedIdentifiers',[]) if r.get('relatedIdentifierType')=='DOI' and r.get('relationType')=='IsVersionOf']
            add('arxiv:'+aid.lower(),dict(src='arxiv',arxiv=aid,title=re.sub(r'\s+',' ',at['titles'][0]['title']),date=sub[0],authors=[p.get('name') for p in at.get('creators',[])][:12],
                lic=[r.get('rightsUri') for r in at.get('rightsList',[])],abstract=re.sub(r'\s+',' ',(at.get('descriptions') or [{}])[0].get('description','')),doi=(jdoi or [None])[0],
                pdf=f'https://arxiv.org/pdf/{aid}',page=f'https://arxiv.org/abs/{aid}'),c,q,rank)
        eq=f'(TITLE:"{a}" OR ABSTRACT:"{a}")'+(f' AND (TITLE:"{b}" OR ABSTRACT:"{b}")' if b else '')+' AND OPEN_ACCESS:y AND IN_PMC:y AND FIRST_PDATE:[2023-10-29 TO 2026-11-06]'
        d=get('https://www.ebi.ac.uk/europepmc/webservices/rest/search?'+urllib.parse.urlencode({'query':eq,'format':'json','pageSize':'300','resultType':'core'}))
        for rank,r in enumerate(((d or {}).get('resultList') or {}).get('result',[])):
            if not r.get('pmcid'): continue
            add('pmc:'+r['pmcid'],dict(src='pmc',pmcid=r['pmcid'],doi=r.get('doi'),title=re.sub(r'<[^>]+>','',r.get('title','')).strip(),date=r.get('firstPublicationDate'),
                authors=[x.get('fullName') for x in (r.get('authorList') or {}).get('author',[])][:12],lic=[r.get('license')],abstract=re.sub(r'<[^>]+>','',r.get('abstractText','') or ''),
                venue=(r.get('journalInfo') or {}).get('journal',{}).get('title'),page=f"https://pmc.ncbi.nlm.nih.gov/articles/{r['pmcid']}/"),c,q,rank)
    print(c,'candidates',len(cand),flush=True)
json.dump(cand,open(B+'/state/candidates.json','w'),ensure_ascii=False)
print('DONE added',len(cand)-n0)
