#!/usr/bin/env python3
"""Download selected papers in order until N per category verify. arXiv: one request per 15 s (robots Crawl-delay).
PMC: NIH open-access dataset on AWS, MD5 checked. Every PDF: header, pypdf parse, first-page title match."""
import hashlib,json,os,re,subprocess,sys,threading,time
sys.path.insert(0,'/srv/ipm_build/pylib'); import pypdf
B='/srv/ipm_build'; N=45; UA='ipm-literature-builder/1.0'; LIB=B+'/lib'; TMP=B+'/tmp'; os.makedirs(TMP,exist_ok=True)
exec(open(B+'/tools/cats.py').read())
cand=json.load(open(B+'/state/candidates.json')); sel=json.load(open(B+'/state/selection.json'))
LOG=B+'/state/fetch.jsonl'; done={}
if os.path.exists(LOG):
    for l in open(LOG): o=json.loads(l); done[o['key']]=o
lock=threading.Lock()
def rec(o):
    with lock:
        open(LOG,'a').write(json.dumps(o,ensure_ascii=False)+'\n'); done[o['key']]=o
def fname(c):
    a0=(c['authors'][0] if c['authors'] else 'Anon') or 'Anon'; last=re.sub(r'[^A-Za-z]','',a0.split(',')[0].split()[0] if a0.split(',')[0].split() else 'Anon') or 'Anon'
    words=[w for w in re.findall(r'[A-Za-z0-9]+',c['title']) if w.lower() not in {'a','an','the','of','for','and','in','on','with','to','via','by','using','based','from','under','at','its'}][:5]
    return f"{(c['date'] or '0000')[:4]}_{last[:20]}_{''.join(w[:1].upper()+w[1:] for w in words)[:60]}_en.pdf"
def sha(p):
    h=hashlib.sha256(); f=open(p,'rb')
    for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()
def tokens(s): return set(w for w in re.findall(r'[a-z0-9]+',s.lower()) if len(w)>3)
def verify(p,title):
    if open(p,'rb').read(5)!=b'%PDF-': return 'not a PDF'
    try:
        r=pypdf.PdfReader(p); n=len(r.pages); txt=' '.join((r.pages[i].extract_text() or '') for i in range(min(2,n)))
    except Exception as e: return f'unreadable: {str(e)[:60]}'
    tt=tokens(title); hit=len(tt & tokens(txt))/max(1,len(tt))
    if hit<0.6: return f'title mismatch {hit:.2f}'
    return None
def curl(url,dest):
    r=subprocess.run(['curl','-sSL','-f','-A',UA,'--max-filesize',str(100*2**20),'-m','600','-o',dest,url],capture_output=True,text=True); return r.returncode,r.stderr[-150:]
def one(key,cat):
    c=cand[key]; name=f"papers/{CATS[cat]['key']}/{fname(c)}"; d=f'{LIB}/{name}'; os.makedirs(os.path.dirname(d),exist_ok=True)
    tmp=f'{TMP}/{hashlib.md5(key.encode()).hexdigest()}.pdf'
    if c['src']=='arxiv': url=c['pdf']; rc,err=curl(url,tmp)
    else:
        meta=subprocess.run(['curl','-sS','-m','60',f"https://pmc-oa-opendata.s3.amazonaws.com/{c['pmcid']}.1/{c['pmcid']}.1.json"],capture_output=True,text=True).stdout
        try: m=json.loads(meta)
        except Exception: rec(dict(key=key,cat=cat,status='failed',why='no PMC OA record')); return
        if not m.get('pdf_url'): rec(dict(key=key,cat=cat,status='failed',why='PMC OA has no PDF')); return
        p=m['pdf_url'].replace('s3://pmc-oa-opendata/','https://pmc-oa-opendata.s3.amazonaws.com/'); url=p.split('?')[0]; md5=re.search(r'md5=([0-9a-f]+)',p)
        rc,err=curl(url,tmp)
        if rc==0 and md5 and hashlib.md5(open(tmp,'rb').read()).hexdigest()!=md5.group(1): rc,err=99,'md5 mismatch'
        c['lic']=[m.get('license_code')] if m.get('license_code') else c['lic']
    if rc!=0: rec(dict(key=key,cat=cat,status='failed',why=f'download rc={rc} {err}',url=url)); os.path.exists(tmp) and os.remove(tmp); return
    why=verify(tmp,c['title'])
    if why: rec(dict(key=key,cat=cat,status='failed',why=why,url=url)); os.remove(tmp); return
    os.replace(tmp,d); rec(dict(key=key,cat=cat,status='ok',path=name,url=url,bytes=os.path.getsize(d),sha256=sha(d),lic=c['lic']))
def okcount(cat): return sum(1 for o in done.values() if o['cat']==cat and o['status']=='ok')
def worker(src,delay):
    while True:
        job=None
        for cat in sorted(sel):
            if okcount(cat)>=N: continue
            for x in sel[cat]:
                if x['key'] in done or cand[x['key']]['src']!=src: continue
                job=(x['key'],cat); break
            if job: break
        if not job: return
        with lock: done[job[0]]={'key':job[0],'cat':job[1],'status':'running'}
        one(*job); time.sleep(delay)
ts=[threading.Thread(target=worker,args=('arxiv',15)),threading.Thread(target=worker,args=('pmc',1))]
for t in ts: t.start()
for t in ts: t.join()
print('DONE',{cat:okcount(cat) for cat in sorted(sel)},flush=True)
