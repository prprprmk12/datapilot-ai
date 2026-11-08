"""Run held-out SQL cases against a real model; persist raw outcomes and a manifest."""
import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime,timezone
from fastapi.encoders import jsonable_encoder
from datapilot.config import Settings
from datapilot.tools import DatabaseTools
from datapilot.integrations.model_api import ModelAPIPolicy
from datapilot.evaluation import evaluate_case

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--cases',type=Path,default=Path('data/eval.jsonl'))
    p.add_argument('--split',choices=['train','dev','test'],default='test')
    p.add_argument('--one-per-family', action='store_true')
    p.add_argument('--limit',type=int,default=0)
    p.add_argument('--sql-retries',type=int,default=0,choices=range(0,4))
    p.add_argument('--variant',choices=['base','tuned'],default='base')
    p.add_argument('--output',type=Path,default=Path('runs/baseline.json'))
    args=p.parse_args()
    settings=Settings()
    if settings.model_provider!='model_api':
        p.error('This benchmark requires MODEL_PROVIDER=model_api; demo cannot be used as a model baseline')
    cases=[json.loads(line) for line in args.cases.read_text().splitlines() if line.strip()]
    cases=[x for x in cases if x['split']==args.split]
    if args.one_per_family:
        first_by_family = {}
        for case in cases:
            first_by_family.setdefault(case['family'], case)
        cases = list(first_by_family.values())
    if not cases:
        p.error('No cases selected')
    if args.limit: cases=cases[:args.limit]
    tools=DatabaseTools(settings);policy=ModelAPIPolicy(settings);outcomes=[]
    for case in cases:
        print('Running',case['id'],flush=True)
        row=evaluate_case(case,tools,policy,'model_api',args.sql_retries);outcomes.append(row)
        print('PASS' if row['success'] else 'FAIL',case['id'],row['elapsed_ms'],'ms',flush=True)
        report={'created_at':datetime.now(timezone.utc).isoformat(),'model':settings.model_id,
                'variant':args.variant,'sql_retries':args.sql_retries,'trained':args.variant=='tuned','split':args.split,'case_file_sha256':hashlib.sha256(args.cases.read_bytes()).hexdigest(),
                'completed':len(outcomes),'planned':len(cases),'successes':sum(x['success'] for x in outcomes),'outcomes':outcomes}
        args.output.parent.mkdir(parents=True,exist_ok=True)
        temp=args.output.with_suffix(args.output.suffix+'.tmp')
        temp.write_text(json.dumps(jsonable_encoder(report),ensure_ascii=False,indent=2))
        temp.replace(args.output)
    return 0 if outcomes and all(x['success'] for x in outcomes) else 1
if __name__=='__main__':raise SystemExit(main())
