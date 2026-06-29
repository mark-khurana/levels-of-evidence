#!/usr/bin/env python3
"""Regenerate Table 1, eTable 4, eTable 1 from current evidence_atlas + comprehensive_analysis.
Consistent with pipeline/analysis.py definitions (primary = in_primary_analysis guidelines, >=5 GL/specialty)."""
import csv, json, collections
from pathlib import Path
D=Path('data'); A=D/'analysis'
rows=list(csv.DictReader(open(D/'evidence_atlas.csv')))
atlas=json.load(open(D/'evidence_atlas.json'))
comp=json.load(open(A/'comprehensive_analysis.json'))
# primary guideline ids
prim_gl={g['id'] for g in atlas['guidelines'] if g.get('in_primary_analysis')}
# authoritative primary specialty set (the 20)
prim_specs=[s['specialty'] for s in comp['primary_analysis']['specialty_gaps']]
def tier(v):
    v=float(v); return 'A' if v>=1 else 'B' if v>=.75 else 'C' if v>=.5 else 'D' if v>=.25 else 'E'
def stats(recs):
    norm=[float(r['loe_normalized']) for r in recs if r['loe_normalized'] not in('','None')]
    if not norm: return None
    c=collections.Counter(tier(r['loe_normalized']) for r in recs if r['loe_normalized'] not in('','None'))
    n=len(norm); socs=len(set(r['society'] for r in recs)); gls=len(set(r['guideline_id'] for r in recs))
    pct={t:100*c[t]/n for t in 'ABCDE'}
    gap=1-sum(norm)/n
    return dict(n=n,socs=socs,gls=gls,pct=pct,de=pct['D']+pct['E'],gap=gap,cA=c['A'],cD=c['D'],cE=c['E'])
# ---- group recs by specialty (primary subset: only in_primary_analysis GLs, with loe) ----
by_spec_prim=collections.defaultdict(list); by_spec_all=collections.defaultdict(list)
for r in rows:
    if r['loe_normalized'] in('','None'): continue
    by_spec_all[r['specialty']].append(r)
    if r['guideline_id'] in prim_gl: by_spec_prim[r['specialty']].append(r)
# Table 1: primary specialties with >=5 GL
t1=[]
for sp,recs in by_spec_prim.items():
    st=stats(recs)
    if st and st['gls']>=5: t1.append((sp,st))
t1.sort(key=lambda x:-x[1]['gap'])
def fmt(n): return f"{n:,}"
lines=["# Table 1: Evidence Distribution by Specialty (Primary Analysis)","",
 "| Specialty | Soc | GL | Recs | %A | %B | %C | %D | %E | %D+E | Gap |","|-|-|-|-|-|-|-|-|-|-|-|"]
tA=tot=tDE=0
for sp,s in t1:
    lines.append(f"| {sp} | {s['socs']} | {s['gls']} | {fmt(s['n'])} | {s['pct']['A']:.1f}% | {s['pct']['B']:.1f}% | {s['pct']['C']:.1f}% | {s['pct']['D']:.1f}% | {s['pct']['E']:.1f}% | {s['de']:.1f}% | {s['gap']:.2f} |")
    tA+=s['cA']; tot+=s['n']; tDE+=s['cD']+s['cE']
lines+=["",f"**{fmt(tot)} recs, {len(t1)} specs. A: {fmt(tA)} ({100*tA/tot:.1f}%). D+E: {fmt(tDE)} ({100*tDE/tot:.1f}%).**",""]
open(A/'table1_primary_analysis.md','w').write("\n".join(lines))
print(f"Table1: {len(t1)} specialties, {tot} recs, A {100*tA/tot:.1f}%, D+E {100*tDE/tot:.1f}%")
# ---- eTable4: ALL specialties ----
e5=[]
for sp,recs in by_spec_all.items():
    st=stats(recs); 
    if st: e5.append((sp,st))
e5.sort(key=lambda x:-x[1]['gap'])
el=["# eTable 4","","| Specialty | Soc | GL | Recs | %A | %D+E | Gap | Primary |","|-|-|-|-|-|-|-|-|"]
prim_t1_specs={sp for sp,_ in t1}
for sp,s in e5:
    el.append(f"| {sp} | {s['socs']} | {s['gls']} | {fmt(s['n'])} | {s['pct']['A']:.1f}% | {s['de']:.1f}% | {s['gap']:.2f} | {'Yes' if sp in prim_t1_specs else 'No'} |")
open(A/'eTable4_all_specialties.md','w').write("\n".join(el)+"\n")
print(f"eTable4: {len(e5)} specialties")
# ---- eTable1: included guidelines ----
gls=sorted(atlas['guidelines'], key=lambda g:(g.get('society',''),g.get('specialty',''),str(g.get('year',''))))
gl_lines=["# eTable 1","","| Society | Specialty | Title | Year | System | Recs | DOI |","|-|-|-|-|-|-|-|"]
for g in gls:
    doi=g.get('doi') or ''
    doi=f"https://doi.org/{doi}" if doi and not str(doi).startswith('http') else doi
    title=(g.get('title') or '').replace('|','/')
    gl_lines.append(f"| {g.get('society','')} | {g.get('specialty','')} | {title} | {g.get('year','')} | {g.get('grading_system','')} | {g.get('rec_count','')} | {doi} |")
open(A/'eTable1_included_guidelines.md','w').write("\n".join(gl_lines)+"\n")
print(f"eTable1: {len(gls)} guidelines")
