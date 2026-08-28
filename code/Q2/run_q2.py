from __future__ import annotations

import argparse, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from code.model_common import check_schedule, concentration, environment, evaluate_schedule, prepare_round, read_data, schedule_overlap, solve_milp_schedule, write_json, write_schedule
from code.Q2.q2_scenarios import center, generate


def mean_maps(scenarios):
    out = {}
    for field in ["demand", "yield", "cost", "price"]:
        keys = scenarios[0][field]
        out[field] = {k: float(np.mean([s[field][k] for s in scenarios])) for k in keys}
    return out


def assess(data, schedule, scenarios, alpha):
    values = np.array([evaluate_schedule(data, schedule, alpha, s)["cumulative_profit"] for s in scenarios])
    k = max(1, int(np.ceil(0.05 * len(values))))
    return {"mean_profit": float(values.mean()), "q05_profit": float(np.quantile(values, .05)),
            "lower_tail_mean": float(np.sort(values)[:k].mean()), "loss_probability": float((values < 0).mean())}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--round',default='round1'); ap.add_argument('--seed',type=int,default=2026); ap.add_argument('--time-limit',type=float,default=60); args=ap.parse_args()
    started=time.perf_counter(); data=read_data(); out=prepare_round('Q2',args.round)
    train=generate(data,args.seed,20); test=generate(data,args.seed+1000,200); tri=generate(data,args.seed+2000,200,'triangular')
    avg=mean_maps(train); ctr=center(data); methods=[]; comparison=[]
    for alpha in [0.0,0.5]:
        main_s, main_solver=solve_milp_schedule(data,alpha,avg['demand'],avg['yield'],avg['cost'],avg['price'],0.0,3,args.time_limit)
        base_s, base_solver=solve_milp_schedule(data,alpha,ctr['demand'],ctr['yield'],ctr['cost'],ctr['price'],0.0,3,args.time_limit)
        for mid,role,sched,solver in [('Q2-M1','main_candidate',main_s,main_solver),('Q2-B1','usable_baseline',base_s,base_solver)]:
            tag='m1' if mid.endswith('M1') else 'b1'; an='0' if alpha==0 else '05'; fn=f'q2_{tag}_alpha{an}_schedule.csv'; write_schedule(out/'tables'/fn,sched)
            viol=check_schedule(data,sched); met={**assess(data,sched,test,alpha),**concentration(sched),'constraint_violations':len(viol),'solver':solver,'alpha':alpha,'triangular':assess(data,sched,tri,alpha)}
            methods.append({'method_id':mid,'role':role,'script':'code/Q2/run_q2.py','status':'success' if len(viol)==0 and not sched.empty else 'failed','execution_time_seconds':solver['execution_time_seconds'],'input_files':['workspace/data_clean/*.csv'],'output_files':[f'tables/{fn}'],'figure_files':[],'metrics_summary':met,'warnings':['optimization_uses_20_scenario_mean_parameter_SAA_due_scale; 200 scenarios reserved for out-of-sample evaluation'],'errors':viol[:20]})
        comparison.append({'alpha':alpha,'schedule_overlap':schedule_overlap(main_s,base_s),'main':assess(data,main_s,test,alpha),'baseline':assess(data,base_s,test,alpha)})
    pd.DataFrame(comparison).to_json(out/'tables/q2_paired_comparison.json',orient='records',force_ascii=False,indent=2)
    write_json(out/'metrics/q2_metrics.json',{'comparison':comparison,'train_scenarios':20,'test_scenarios':200,'seed':args.seed})
    fallback=any(abs(x['main']['lower_tail_mean']-x['main'].get('lower_tail_mean',0))>0.1*abs(x['main']['lower_tail_mean']) or x['schedule_overlap']<0.7 for x in comparison)
    write_json(out/'run_summary.json',{'schema_version':1,'question':'Q2','round':args.round,'implementation_target':'python','random_seed':args.seed,'approved_decision_id':'q2_method_choice','methods':methods,'comparison':{'file':'tables/q2_paired_comparison.json','values':comparison},'fallback_trigger':{'fallback_id':'Q2-F1','condition':'tail changes >10% or overlap <70%','observed':fallback,'evidence':'metrics/q2_metrics.json'},'environment':environment(),'execution_time_seconds':time.perf_counter()-started,'warnings':['20-scenario optimization approximation; full 200-scenario extensive form deferred to scale review']})
if __name__=='__main__': main()
