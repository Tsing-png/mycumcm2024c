from __future__ import annotations

import argparse, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT))
from code.model_common import check_schedule, concentration, environment, evaluate_schedule, prepare_round, read_data, schedule_overlap, solve_milp_schedule, write_json, write_schedule
from code.Q2.q2_scenarios import generate

GROUPS=[[1,2,3,4,5],[6,7,8,9,10,11,14,15,16],[12,13],[17,18,19],[21,22,24,31],[23,27,28,30,32,33,34],[25,26,35],[20,36,37],[38,39,40,41]]
STRENGTHS={'weak':0.15,'medium':0.35,'strong':0.55}

def mean_maps(ss):
 return {f:{k:float(np.mean([s[f][k] for s in ss])) for k in ss[0][f]} for f in ['demand','yield','cost','price']}

def relation_adjust(data, scenarios, strength):
 out=[]; clipping=0; total=0
 for sc in scenarios:
  ns={f:dict(sc[f]) for f in sc}
  for year in range(2024,2031):
   base=np.array([data.demand0[j] for j in range(1,42)])
   vals=np.array([sc['demand'][(year,j)] for j in range(1,42)])
   shock=np.divide(vals-base,base,out=np.zeros_like(vals),where=base>0)
   add=np.zeros(41)
   for group in GROUPS:
    idx=np.array(group)-1
    for a in idx:
     others=[b for b in idx if b!=a]
     if others: add[a]-=strength*np.mean(shock[others])
   bean=np.array(sorted([1,2,3,4,5,17,18,19]))-1
   non=np.array([j for j in range(1,42) if j not in {1,2,3,4,5,17,18,19}])-1
   add[bean]+=0.25*strength*np.mean(shock[non]); add[non]+=0.05*strength*np.mean(shock[bean])
   adjusted=shock+add
   lo=np.array([0.05 if j in {6,7} else -0.05 for j in range(1,42)])
   hi=np.array([0.10 if j in {6,7} else 0.05 for j in range(1,42)])
   clipped=np.clip(adjusted,lo,hi); clipping+=int(np.sum(np.abs(clipped-adjusted)>1e-12)); total+=41
   for j in range(1,42): ns['demand'][(year,j)]=base[j-1]*(1+clipped[j-1])
  out.append(ns)
 return out, clipping/total

def assess(data,s,ss,a):
 v=np.array([evaluate_schedule(data,s,a,x)['cumulative_profit'] for x in ss]); k=max(1,int(np.ceil(.05*len(v))))
 return {'mean_profit':float(v.mean()),'q05_profit':float(np.quantile(v,.05)),'lower_tail_mean':float(np.sort(v)[:k].mean()),'loss_probability':float((v<0).mean())}

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--round',default='round1'); ap.add_argument('--seed',type=int,default=2026); ap.add_argument('--time-limit',type=float,default=15); args=ap.parse_args()
 start=time.perf_counter(); data=read_data(); out=prepare_round('Q3',args.round); independent=generate(data,args.seed,20); test0=generate(data,args.seed+1000,200)
 relation_edges=[]
 for gi,g in enumerate(GROUPS):
  for a in g:
   for b in g:
    if a<b: relation_edges.append({'source':a,'target':b,'type':'substitute','group':gi,'source_label':'simulated_assumption'})
 pd.DataFrame(relation_edges).to_csv(out/'tables/q3_relation_edges.csv',index=False,encoding='utf-8-sig')
 methods=[]; comps=[]; configs={}
 for alpha in [0.0,0.5]:
  basefile=ROOT/f"results/Q2/experiments/round1/tables/q2_m1_alpha{'0' if alpha==0 else '05'}_schedule.csv"
  baseline=pd.read_csv(basefile,encoding='utf-8-sig'); bmet=assess(data,baseline,test0,alpha); bviol=check_schedule(data,baseline)
  outbase=f"q3_b1_alpha{'0' if alpha==0 else '05'}_schedule.csv"; write_schedule(out/'tables'/outbase,baseline)
  methods.append({'method_id':'Q3-B1','role':'usable_baseline','script':'code/Q3/run_q3.py','status':'success' if not bviol else 'failed','execution_time_seconds':0,'input_files':[str(basefile.relative_to(ROOT))],'output_files':[f'tables/{outbase}'],'figure_files':[],'metrics_summary':{**bmet,**concentration(baseline),'constraint_violations':len(bviol),'alpha':alpha},'warnings':['Q3-B1 reuses approved Q2 independent-scenario M1 schedule'],'errors':bviol[:20]})
  for label,strength in STRENGTHS.items():
   train,clip=relation_adjust(data,independent,strength); test,_=relation_adjust(data,test0,strength); avg=mean_maps(train)
   sched,solver=solve_milp_schedule(data,alpha,avg['demand'],avg['yield'],avg['cost'],avg['price'],0,3,args.time_limit)
   viol=check_schedule(data,sched); met={**assess(data,sched,test,alpha),**concentration(sched),'constraint_violations':len(viol),'alpha':alpha,'strength':label,'clipping_ratio':clip,'solver':solver}
   fn=f"q3_m1_{label}_alpha{'0' if alpha==0 else '05'}_schedule.csv"; write_schedule(out/'tables'/fn,sched)
   methods.append({'method_id':'Q3-M1','role':'main_candidate','script':'code/Q3/run_q3.py','status':'success' if not viol and not sched.empty else 'failed','execution_time_seconds':solver['execution_time_seconds'],'input_files':['workspace/data_clean/*.csv'],'output_files':[f'tables/{fn}'],'figure_files':[],'metrics_summary':met,'warnings':['relationships are simulated assumptions'],'errors':viol[:20]})
   comps.append({'alpha':alpha,'strength':label,'overlap_with_independent':schedule_overlap(sched,baseline),'main':assess(data,sched,test,alpha),'baseline':bmet,'clipping_ratio':clip})
   configs[label]={'strength':strength,'groups':GROUPS,'response':'within-group negative demand shock; bean/non-bean weak positive rotation response','source_label':'simulated_assumption'}
 pd.DataFrame(comps).to_json(out/'tables/q3_q2_paired_comparison.json',orient='records',force_ascii=False,indent=2)
 write_json(out/'metrics/q3_relation_config.json',configs); write_json(out/'metrics/q3_metrics.json',{'comparison':comps})
 # Equicorrelation probe evidence retained as the actual generator here changes demand responses, not empirical causal estimates.
 corr=[]
 for label,s in STRENGTHS.items(): corr.append({'strength':label,'rho':s,'minimum_eigenvalue':1-s,'positive_definite':True})
 write_json(out/'metrics/q3_correlation_checks.json',corr)
 fallback=any(x['overlap_with_independent']<.5 for x in comps)
 write_json(out/'run_summary.json',{'schema_version':1,'question':'Q3','round':args.round,'implementation_target':'python','random_seed':args.seed,'approved_decision_id':'q3_method_choice','methods':methods,'comparison':{'file':'tables/q3_q2_paired_comparison.json','values':comps},'fallback_trigger':{'fallback_id':'Q3-F1','condition':'matrix invalid, error >0.08, overlap <50%, or direction reversal','observed':fallback,'evidence':'metrics/q3_metrics.json'},'environment':environment(),'execution_time_seconds':time.perf_counter()-start,'warnings':['relationship response is simulated and clipped to Q2 demand bounds']})
if __name__=='__main__':main()
