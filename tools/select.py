#!/usr/bin/env python3
"""Screen candidates with the old screening rules and pick up to N per category.
A paper needs a process-monitoring core term in its title, or in its abstract together with an industrial-process context.
Single-equipment papers (bearing, gearbox, motor...) are dropped unless they mention a production process.
Category = best keyword score over the 12 category term lists (title x3, abstract x1); licence preference 1.2x."""
import json,re,collections,html
B='/srv/ipm_build'; N=45
exec(open(B+'/tools/cats.py').read())
cand=json.load(open(B+'/state/candidates.json'))
OPEN=re.compile(r'creativecommons\.org/(licenses/(by|by-sa|by-nc|by-nc-sa|by-nd|by-nc-nd)/|publicdomain/)|^cc[ -]?(by|0)',re.I)
CORE=re.compile(r'process monitoring|monitoring of (industrial|chemical|batch|manufacturing)|process fault|fault detection|fault diagnos|fault isolation|soft[- ]sensor|statistical process (control|monitoring)|control chart|condition monitoring|anomaly detection|root[- ]cause|virtual metrology|quality prediction|quality-related|batch process|industrial process|chemical process|process industr|process data|digital twin|state estimation|alarm (management|flood|analysis)|process supervision|incipient fault|tennessee eastman',re.I)
CTX=re.compile(r'industr|plant|chemical|process|manufactur|refiner|reactor|production',re.I)
EQUIP=re.compile(r'bearing|gearbox|gear |rotating machiner|induction motor|wind turbine|rolling element|spindle|battery|photovoltaic|power grid|transmission line|aircraft|vehicle|railway|bridge|building',re.I)
T={'01':r'review|survey|overview|tutorial|perspective|framework|control chart|statistical process control|\bSPC\b|alarm|profile monitoring',
'02':r'\bPCA\b|principal component|\bPLS\b|partial least squares|\bICA\b|independent component|canonical (variate|correlation)|slow feature|latent variable|kernel|probabilistic|bayesian|tensor|sparse|subspace|mahalanobis|hotelling',
'03':r'autoencoder|deep|neural network|\bLSTM\b|\bGRU\b|transformer|attention|graph neural|\bGNN\b|contrastive|self-supervised|convolutional|\bCNN\b|machine learning',
'04':r'anomal|incipient|early (fault|warning|detection)|drift|novelty|outlier|false alarm|detection delay|weak fault|unsupervised detection',
'05':r'root[- ]cause|diagnos|causal|propagation|isolation|contribution|explainab|interpretab|granger|transfer entropy',
'06':r'multi-?mode|operating (mode|condition)|non-?stationar|time-varying|transition|transfer learning|domain adaptation|continual|incremental|adaptive|dynamic',
'07':r'soft[- ]sensor|quality|virtual metrology|just-in-time|semi-supervised|inferential|key performance indicator',
'08':r'batch|fermentation|penicillin|bioprocess|pharmaceutical|phase partition|trajectory|biopharm|monoclonal',
'09':r'hybrid model|mechanistic|first-principles|physics-informed|physics-guided|digital twin|state estimation|observer|kalman|system identification|gr[ae]y-box',
'10':r'large language model|\bLLMs?\b|foundation model|multimodal|multi-modal|knowledge graph|few-shot|zero-shot|agent|\bGPT|vision-language',
'11':r'tennessee eastman|benchmark|dataset|data set|simulation platform|evaluation (protocol|metric)|reproducib|leakage|three-phase flow|\bSKAB\b',
'12':r'wastewater|steel|blast furnace|power plant|thermal power|semiconductor|cement|petrochemical|refiner|paper mill|mineral|flotation|coal|boiler|oil and gas|nuclear|wafer|sintering|aluminium|aluminum|hot rolling|cracking'}
T={k:re.compile(v,re.I) for k,v in T.items()}
def clean(s): return html.unescape(re.sub(r'<[^>]+>','',s or '')).strip()
def is_open(c): return any(l and OPEN.search(l.strip()) for l in c.get('lic') or [])
EXC=re.compile(r'intrusion|cyber|attack|business process|process mining|patient|clinical|hospital|surg|cardiac|pediatric|urodynam|covid|medical|health ?care|epidem|cancer|tumou?r|disease|traffic|financial|stock|credit|social network|software|microservice|cloud|5G|retract|rice|crop|forage|flavou?r|grape|wine|soil|crystal structure|photochemi|quantum dot|astronom|seismic|earthquake',re.I)
IND=re.compile(r'industr|chemical process|process industr|manufactur|refiner|reactor|production (line|process)|tennessee eastman|power plant|chemical plant|processing plant|wastewater treatment|steel|semiconductor|wafer|ferment|bioprocess|batch process|cement|blast furnace|flotation|petrochemical|distillation|polymeri|pharmaceutical (manufactur|process)|process monitoring|soft sensor|process control',re.I)
keep={}
for k,c in cand.items():
    t=clean(c['title']); ab=clean(c.get('abstract'))[:4000]; c['title']=t
    if EXC.search(t+' '+ab[:1500]) or not IND.search(t+' '+ab): continue
    if re.search(r'\b(image|images|visual|vision)\b',t,re.I) and not re.search(r'process|multimodal|multi-modal',t,re.I): continue
    if re.search(r'smart grid|power system|distribution network|localization|navigation|train|maglev|induction machine|\bmotor\b|engine|aero|satellite|robot',t,re.I) and not re.search(r'process|plant|production',t,re.I): continue
    core_t=CORE.search(t); core_a=len(CORE.findall(ab))
    if not (core_t or (core_a>=2 and any(r.search(t) for r in T.values()))): continue
    if re.search(r'predictive process monitoring|clinic|devulcani|wind power|wind speed|sign language|wellbore|household|plasmid|enzymatic synthesis|load forecasting|price',t,re.I): continue
    if EQUIP.search(t) and not re.search(r'process|plant|production|manufactur',t,re.I): continue
    sc={cat:3*len(r.findall(t))+min(4,len(r.findall(ab))) for cat,r in T.items()}
    for cat in c['hits']: sc[cat]+=1          # the category whose queries found it
    cat=max(sc,key=sc.get)
    if sc[cat]<3: continue
    keep[k]=(cat,(sc[cat]+(2 if core_t else 0))*(1.2 if is_open(c) else 1))
def norm(t): return re.sub(r'[^a-z0-9]','',t.lower())[:80]
uniq={}
for k in sorted(keep,key=lambda k:(cand[k]['src']!='pmc',-keep[k][1])): uniq.setdefault(norm(cand[k]['title']),k)
FORCE={'01':['arxiv:2503.01858','arxiv:2401.10266','pmc:PMC11723332']}
sel=collections.defaultdict(list)
for cat,ks in FORCE.items():
    for k in ks: sel[cat].append(dict(key=k,score=99,open=True,old=True))
forced={k for ks in FORCE.values() for k in ks}
for k in sorted(uniq.values(),key=lambda k:-keep[k][1]):
    cat=keep[k][0]
    if k in forced: continue
    if len(sel[cat])<N+20: sel[cat].append(dict(key=k,score=round(keep[k][1],2),open=is_open(cand[k])))
json.dump(sel,open(B+'/state/selection.json','w'),indent=0); json.dump(cand,open(B+'/state/candidates.json','w'),ensure_ascii=False)
print('passed screening',len(keep),'unique',len(uniq))
for cat in sorted(CATS): print(cat,CATS[cat]['name'],'pool',len(sel[cat]),'open in top',sum(x['open'] for x in sel[cat][:N]))
