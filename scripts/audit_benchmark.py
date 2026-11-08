"""Score recorded benchmark episodes with AuditKIT; no model calls or DB access."""
import argparse
import hashlib
import json
from pathlib import Path
from datapilot.integrations.auditkit import evaluate_episode

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('report',type=Path)
    p.add_argument('--cases', type=Path, default=Path('data/eval.jsonl'))
    args=p.parse_args()
    report=json.loads(args.report.read_text())
    if report.get('case_file_sha256') and report['case_file_sha256'] != hashlib.sha256(args.cases.read_bytes()).hexdigest():
        p.error('Report was produced with a different case file. Pass the original file with --cases.')
    cases=[json.loads(line) for line in args.cases.read_text().splitlines() if line.strip()]
    questions={case['id']:case['question'] for case in cases}
    for row in report['outcomes']:
        if not row.get('response'):
            print(json.dumps({'id':row['id'],'status':'not_scored','reason':row.get('error_type','missing episode')},ensure_ascii=False))
            continue
        result=evaluate_episode(questions[row['id']],row['response'],row['expected'],[])
        scored=result.rows[0]
        print(json.dumps({'id':row['id'],'outcome':scored.outcome['verdict'],
            'tool_calls':len(row['response']['trace']),'ineligible':scored.ineligible},ensure_ascii=False))
