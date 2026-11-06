#!/usr/bin/env python3
"""Build the published tree (pub/), the Release tars (rel/) and the private copies of restricted files."""
import csv,hashlib,html,json,os,re,shutil,subprocess,collections
B='/srv/ipm_build'; LIB=B+'/lib'; PUB=B+'/pub'; REL=B+'/rel'
PRIV='/root/copyright_files/files/industrial-process-monitoring-literature/library'
REPO='https://github.com/yuriev315/industrial-process-monitoring-literature'; TAG='ipm-full-20261106'
exec(open(B+'/tools/cats.py').read())
cand=json.load(open(B+'/state/candidates.json')); sel=json.load(open(B+'/state/selection.json'))
fetch={}
for l in open(B+'/state/fetch.jsonl'):
    o=json.loads(l); fetch[o['key']]=o
OPEN=re.compile(r'creativecommons\.org/(licenses/(by|by-sa|by-nc|by-nc-sa|by-nd|by-nc-nd)/|publicdomain/)|^cc[ -]?(by|0)',re.I)
def licname(ls):
    for l in ls or []:
        if not l: continue
        m=re.search(r'creativecommons\.org/licenses/([a-z-]+)/([0-9.]+)',l)
        if m: return f'CC {m.group(1).upper()} {m.group(2)}'
        if 'publicdomain/zero' in l: return 'CC0 1.0'
        if 'arxiv.org/licenses/nonexclusive' in l: return 'arXiv 非独占分发许可'
        if 'arxiv.org/licenses/assumed' in l: return 'arXiv 默认许可（1991–2003）'
        if re.match(r'cc[ -]?',l,re.I): return l.upper().replace('CC ','CC ')
        return l
    return '未声明'
def is_open(ls): return any(l and OPEN.search(l.strip()) for l in ls or [])
def sha(p):
    h=hashlib.sha256(); f=open(p,'rb')
    for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()
def placeholder(path,title,url,note):
    d=f'{PUB}/{path}.url.txt'; os.makedirs(os.path.dirname(d),exist_ok=True)
    open(d,'w',encoding='utf-8').write(f'Title: {title}\nOfficial source: {url}\nOriginal file name: {os.path.basename(path)}\nNote: {note}\n')
R_NOTE='Not included because no redistribution licence was found. Download it from the official source.'
for d in (PUB,REL):
    if os.path.isdir(d):
        for n in os.listdir(d):
            if n=='.git': continue
            p=os.path.join(d,n); shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    os.makedirs(d,exist_ok=True)
rows=[]; public=[]; private=[]; fails=[]
COLS=['文献编号','资料类型','主分类','子方向或主题','标题','作者','首次公开日期','渠道','DOI','arXiv ID','PMCID','原始页面','全文URL','本地相对路径','许可证','全文位置','字节','SHA256','选入依据']
# ---- papers
for cat in sorted(sel):
    n=0
    for x in sel[cat]:
        k=x['key']; o=fetch.get(k)
        if not o or o['status']!='ok': 
            if o and o['status']=='failed': fails.append((cat,k,o.get('why'),o.get('url')))
            continue
        if n>=45: break
        n+=1; c=cand[k]; lic=o.get('lic') or c.get('lic'); path=o['path']
        q=sorted({h[0] for hs in c['hits'].values() for h in hs})[:3]
        r=dict(zip(COLS,[f'{cat}-{n:03d}','论文',f"{cat} {CATS[cat]['name']}",'',html.unescape(c['title']),'; '.join(a for a in c['authors'] if a),(c.get('date') or '')[:10],
            c.get('venue') or ('arXiv' if c['src']=='arxiv' else ''),c.get('doi') or '',c.get('arxiv') or '',c.get('pmcid') or '',c['page'],o['url'],path,licname(lic),'',o['bytes'],o['sha256'],'检索式：'+'；'.join(q)]))
        if is_open(lic): r['全文位置']='Release'; public.append(path)
        else:
            r['全文位置']='仅链接（未见再分发许可）'; private.append((path,r['标题'],c['page'])); placeholder(path,r['标题'],c['page'],R_NOTE)
        rows.append(r)
# 01-001..004 keep their numbers: the selection lists the three forced items first; add the IEEE paper as 01-001 and shift
ieee='papers/01_fundamentals_reviews/2017_Ge_DataMiningAnalyticsProcessIndustry_en.pdf'
p01=[r for r in rows if r['文献编号'].startswith('01-')]
for i,r in enumerate(p01): r['文献编号']=f'01-{i+2:03d}'
rows.insert(0,dict(zip(COLS,['01-001','论文','01 工业过程监控基础与综述','','Data Mining and Analytics in the Process Industry: The Role of Machine Learning','Zhiqiang Ge; Zhihuan Song; Steven X. Ding; Biao Huang','2017-09-26','IEEE Access','10.1109/ACCESS.2017.2756872','','','https://doi.org/10.1109/ACCESS.2017.2756872','https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber=8051033',ieee,'IEEE OAPA','仅链接（未见再分发许可）',os.path.getsize(f'{LIB}/{ieee}'),sha(f'{LIB}/{ieee}'),'经典综述（三年前文献）'])))
private.append((ieee,rows[0]['标题'],'https://doi.org/10.1109/ACCESS.2017.2756872')); placeholder(ieee,rows[0]['标题'],'https://doi.org/10.1109/ACCESS.2017.2756872',R_NOTE)
# ---- books and courses
BK=json.load(open(B+'/tools/books_courses.json'))
for b in BK:
    p=b['path']; f=f'{LIB}/{p}'
    r=dict(zip(COLS,[b['id'],b['type'],b['cat'],b['topic'],b['title'],b.get('authors',''),b.get('year',''),b.get('venue',''),b.get('doi',''),'','',b['page'],b.get('url',''),p,b['license'],'','','','']))
    if b['state']=='public' and os.path.exists(f):
        r['全文位置']='Release'; public.append(p)
        if os.path.isfile(f): r['字节']=os.path.getsize(f); r['SHA256']=sha(f)
    elif b['state']=='restricted':
        r['全文位置']='仅链接（未见再分发许可）'; placeholder(p,b['title'],b['page'],b.get('note') or R_NOTE)
        if os.path.exists(f): private.append((p,b['title'],b['page']))
    else:
        r['全文位置']='仅链接（'+b['why']+'）'; placeholder(p,b['title'],b['page'],b['note']); fails.append((b['id'][:2],b['id'],b['why'],b['page']))
    rows.append(r)
rows.sort(key=lambda r:r['文献编号'])
with open(f'{PUB}/catalog_cn.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,COLS); w.writeheader(); w.writerows(rows)
# ---- failures and link-only list
with open(f'{PUB}/download_failures_cn.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(['分类','条目','原因','地址'])
    for cat,k,why,url in fails: w.writerow([cat,cand[k]['title'] if k in cand else k,why,url or ''])
with open(f'{PUB}/release_excluded_cn.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(['文献编号','资料类型','标题','本地相对路径','许可证','原始页面','未收录原因'])
    for r in rows:
        if r['全文位置']!='Release': w.writerow([r['文献编号'],r['资料类型'],r['标题'],r['本地相对路径'],r['许可证'],r['原始页面'],r['全文位置']])
# ---- domain indexes
DK={**{c:(v['key'],v['name']) for c,v in CATS.items()},'13':('13_university_courses','著名大学课程教材与讲义'),'14':('14_books_references','书籍与参考资料')}
for c,(key,name) in DK.items():
    rs=[r for r in rows if r['文献编号'].startswith(c+'-')]
    L=[f'# {c} {name}','',f'共 {len(rs)} 条。全文在 Release `{TAG}` 中的标为“Release”，其余只有链接。','','| 编号 | 首次公开 | 标题 | 文件 | 全文 |','|---|---|---|---|---|']
    for r in rs:
        t=r['标题'].replace('|','/'); p=r['本地相对路径']; link=f"[{os.path.basename(p)}](../../{p}{'' if r['全文位置']=='Release' else '.url.txt'})"
        L.append(f"| {r['文献编号']} | {r['首次公开日期'][:10]} | {t} | {link} | {'Release' if r['全文位置']=='Release' else '链接'} |")
    os.makedirs(f'{PUB}/domains/{key}',exist_ok=True); open(f'{PUB}/domains/{key}/README_cn.md','w',encoding='utf-8').write('\n'.join(L)+'\n')
# ---- search log
qs=json.load(open(B+'/tools/queries_used.json'))
L=['# 检索日志','','- 检索日期：2026-11-06。','- 时间窗口：首次公开日期 2023-10-29 至 2026-11-06。','- 平台：arXiv（通过 DataCite 元数据检索，许可取自 DataCite rightsList）；Europe PMC（仅开放获取且收录于 PMC 的文章，全文取自 NIH 的 PMC 开放获取数据集）。','- 筛选：按 `scripts/screening_rules_cn.md` 的纳入与排除规则，用关键词自动筛选，每类最多 45 篇。未逐篇人工通读。','','| 分类 | 检索式 |','|---|---|']
for c,ql in qs.items():
    for q in ql: L.append(f'| {c} | {q} |')
open(f'{PUB}/search_log_cn.md','w',encoding='utf-8').write('\n'.join(L)+'\n')
# ---- tars
pub_files=[]
for p in sorted(set(public)):
    f=f'{LIB}/{p}'
    if os.path.isdir(f):
        for dp,dn,fn in os.walk(f):
            for x in fn: pub_files.append(os.path.relpath(os.path.join(dp,x),LIB))
    else: pub_files.append(p)
pub_files.sort(key=lambda p:(not p.startswith(('books/','university_materials/')),p))
batches=[[]]; size=0; LIM=1500*2**20
for p in pub_files:
    s=os.path.getsize(f'{LIB}/{p}')
    if size+s>LIM and batches[-1]: batches.append([]); size=0
    batches[-1].append(p); size+=s
with open(f'{PUB}/checksums_en.sha256','w') as ck:
    for p in pub_files: ck.write(f'{sha(LIB+"/"+p)}  {p}\n')
assets=[]
for i,bt in enumerate(batches,1):
    lst=f'{B}/tmp/batch{i}.txt'; open(lst,'w').write('\n'.join(bt)+'\n'); T=f'{REL}/industrial_process_monitoring_literature_20261106_batch{i:03d}_cn_en.tar'
    subprocess.check_call(['tar','-C',LIB,'--sort=name','--owner=0','--group=0','--numeric-owner','--mtime=2026-11-06 00:00Z','-cf',T,'-T',lst]); assets.append((os.path.basename(T),len(bt),os.path.getsize(T),sha(T)))
with open(f'{PUB}/archive_index_cn.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(['包文件名','相对路径','字节数'])
    for i,bt in enumerate(batches,1):
        for p in bt: w.writerow([assets[i-1][0],p,os.path.getsize(f'{LIB}/{p}')])
for n in ('catalog_cn.csv','checksums_en.sha256','archive_index_cn.csv'): shutil.copyfile(f'{PUB}/{n}',f'{REL}/{n}')
# ---- private copies
copied=[]
for p,t,u in private:
    s=f'{LIB}/{p}'; d=f'{PRIV}/{p}'
    if os.path.isdir(s):
        for dp,dn,fn in os.walk(s):
            for x in fn:
                ss=os.path.join(dp,x); dd=os.path.join(PRIV,os.path.relpath(ss,LIB)); os.makedirs(os.path.dirname(dd),exist_ok=True)
                if not os.path.exists(dd): shutil.copy2(ss,dd)
                copied.append((t,os.path.relpath(ss,LIB),dd,u))
    elif os.path.exists(s):
        os.makedirs(os.path.dirname(d),exist_ok=True)
        if not os.path.exists(d): shutil.copy2(s,d)
        copied.append((t,p,d,u))
json.dump(dict(assets=assets,copied=copied,n_rows=len(rows),n_public=len(pub_files),fails=len(fails)),open(B+'/state/build.json','w'),ensure_ascii=False,indent=1)
print('rows',len(rows),'papers',sum(r['资料类型']=='论文' for r in rows),'public files',len(pub_files),'private',len(copied),'fails',len(fails))
for a in assets: print(a)
