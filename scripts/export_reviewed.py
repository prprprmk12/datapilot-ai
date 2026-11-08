"""Export human-accepted real-model runs as project-specific message traces, not EventLog."""
import argparse,json
from pathlib import Path
from datapilot.config import Settings
from datapilot.runs import RunStore
from datapilot.integrations.protocol import messages_for

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    store=RunStore(Settings().runs_path);rows=[]
    for item in store.list(limit=10000):
        if item['review']!='accepted' or item['mode']=='demo':continue
        record=store.get(item['id']);response=record['response']
        if not response.get('result') or response.get('error'):continue
        messages=messages_for(item['question'],response['trace'])
        messages.append({'role':'assistant','content':json.dumps({'name':'finish','arguments':{'answer':response['answer']}},ensure_ascii=False)})
        rows.append({'messages':messages,'metadata':{'run_id':item['id'],'model':item['model'],'review':'accepted','format':'datapilot-messages-v1'}})
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows))
    print('Exported',len(rows),'reviewed real-model traces. This is not an AgentTune EventLog.')
