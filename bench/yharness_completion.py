from pathlib import Path
from decimal import Decimal
import os,sys,json,subprocess,shutil,time,signal,tarfile,hashlib
BASE=Path(__file__).resolve().parent
PLAN=json.loads((BASE/'plan.json').read_text())
assert hashlib.sha256((BASE/'plan.json').read_bytes()).hexdigest()==(BASE/'plan.sha256').read_text().strip()

def rows(path):return [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []
def records():
    root = BASE / 'runs'
    if not root.exists():
        return []
    result = []
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        record_path = folder / 'record.json'
        if not record_path.is_file():
            raise RuntimeError(f'Incomplete attempt folder: {folder.name}')
        record = json.loads(record_path.read_text())
        requests = request_rows(folder)
        if record.get('requests') != len(requests):
            raise RuntimeError(f'Invalid prior attempt {folder.name}: request count mismatch')
        if record.get('valid_usage') is not True or not valid_usage_rows(requests):
            raise RuntimeError(f'Invalid prior attempt {folder.name}: incomplete or invalid usage')
        if record.get('known_costs') != known_costs(requests):
            raise RuntimeError(f'Invalid prior attempt {folder.name}: recorded costs disagree with meter')
        if not isinstance(record.get('grade', {}).get('success'), bool):
            raise RuntimeError(f'Incomplete attempt folder: {folder.name} has no final grade')
        result.append(record)
    return result

def totals(items):
 return {'requests':sum(r['requests'] for r in items),'allowance':sum((Decimal(r['known_costs']['allowance']) for r in items),Decimal(0))}

def grade(project,stage):
 args=['docker','run','--rm','--read-only','--network','none','--cap-drop','ALL','--security-opt','no-new-privileges','--cpus','2','--memory','512m','--pids-limit','128','--tmpfs','/tmp:rw,nosuid,size=128m']
 for src,dst in [(project,'/input/project'),(BASE/'fixtures/shopkit','/input/original'),(BASE/'grader','/grader')]:args+=['--mount',f'type=bind,source={src},target={dst},readonly']
 args+=['--entrypoint','/usr/bin/python3',PLAN['docker_image_id'],'-B','/grader/grade.py',str(stage)]
 result=subprocess.run(args,text=True,capture_output=True,timeout=90)
 if result.returncode:raise RuntimeError('Independent grader failed: '+result.stderr[-3000:])
 return json.loads(result.stdout)

def _numbered(events,event,description):
 selected=[r for r in events if r.get('event')==event]
 numbers=[r.get('number') for r in selected]
 if any(type(n) is not int or n<1 for n in numbers):raise RuntimeError(f'Invalid {description} number')
 if len(numbers)!=len(set(numbers)):raise RuntimeError(f'Duplicate {description}')
 return {r['number']:r for r in selected}

def request_rows(folder):
 events=rows(folder/'requests.jsonl')
 started=_numbered(events,'request_started','request start number')
 completed=_numbered(events,'request','request completion number')
 if set(started)!=set(range(1,len(started)+1)):raise RuntimeError('Noncontiguous request starts')
 if completed.keys()-started.keys():raise RuntimeError('Completion without request start')
 return [completed.get(n,{**started[n],'complete':False,'error':'request started without final meter record'}) for n in range(1,len(started)+1)]

COST_FIELDS = ('allowance', 'list_cost', 'cost')


def usage_amount(request, field):
    usage = request.get('usage')
    if request.get('complete') is not True or not isinstance(usage, dict):
        return None
    value = usage.get(field)
    if type(value) not in (int, float):
        return None
    amount = Decimal(str(value))
    return amount if amount.is_finite() and amount >= 0 else None


def valid_usage_rows(requests):
    return bool(requests) and all(
        request.get('status') == 200
        and request.get('model') == PLAN['model']
        and all(usage_amount(request, field) is not None for field in COST_FIELDS)
        for request in requests
    )


def known_costs(requests):
    result = {}
    for field in COST_FIELDS:
        amounts = (usage_amount(request, field) for request in requests)
        result[field] = str(sum((amount for amount in amounts if amount is not None), Decimal(0)))
    return result


def invoke(index,stage,arm,attempt,prompt,session,attempt_kind=None):
 task=PLAN['sequences'][0]['tasks'][stage]['name'];out=BASE/'runs'/f'{index:02d}-{task}-{arm}-{attempt}'
 prior=records();all_used=totals(prior);arm_used=totals([r for r in prior if r['arm']==arm])
 remaining=min(PLAN['total_max_requests']-all_used['requests'],PLAN['per_arm_max_requests']-arm_used['requests'])
 money=min(Decimal(PLAN['total_max_allowance_usd'])-all_used['allowance'],Decimal(PLAN['per_arm_max_allowance_usd'])-arm_used['allowance'])
 if remaining<=0 or money<=0:raise RuntimeError('Budget reached before next attempt')
 cap=min(PLAN['max_requests_per_run'] if attempt==0 else PLAN['max_requests_per_repair'],remaining)
 env={**os.environ,'COMPOUND_EXPECT_ROUTING':'1' if arm=='with' else '0','DSH_HOME':PLAN['dsh_home'],'DSH_PERMISSION_MODE':'workspace-write','PATH':str(BASE/'runtime/bin')+':'+os.environ['PATH'],'COMPOUND_PILOT_METER':str(out/'requests.jsonl'),'COMPOUND_PILOT_MAX_CALLS':str(cap),'COMPOUND_PILOT_MAX_USD':str(min(money,Decimal(PLAN['max_allowance_per_run_usd'])))}
 command=['node','--import',str(BASE/'meter.mjs'),PLAN['cli'],'--profile',PLAN['profile'],'--patch',str(BASE/(arm+'.yml')),'--json']
 if session:command+=['--session-id',session]
 out.mkdir()
 command.append(prompt);(out/'prompt.txt').write_text(prompt)
 print('START',index+1,task,arm,'attempt',attempt,'max_requests',cap,flush=True)
 started=time.monotonic();timed_out=False
 with (out/'events.jsonl').open('w') as stdout,(out/'stderr.log').open('w') as stderr:
  child=subprocess.Popen(command,cwd=BASE/'workspace',env=env,stdout=stdout,stderr=stderr,start_new_session=True)
  try:code=child.wait(timeout=PLAN['max_wall_seconds_per_run'])
  except subprocess.TimeoutExpired:
   timed_out=True;os.killpg(child.pid,signal.SIGINT)
   try:code=child.wait(timeout=15)
   except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);code=child.wait()
 req=request_rows(out);events=rows(out/'events.jsonl');meter=rows(out/'requests.jsonl')
 valid=valid_usage_rows(req)
 known=known_costs(req)
 sessions=[e for e in events if e.get('type')=='session'];finals=[e for e in events if e.get('type')=='final']
 record={'schema':'compound-live-attempt-1','index':index,'stage':stage,'task':task,'arm':arm,'attempt':attempt,'attempt_kind':attempt_kind or ('initial' if not attempt else 'semantic_repair'),'requests':len(req),'tool_calls':sum(e.get('type')=='tool_call' for e in events),'known_costs':known,'costs':known if valid else {k:None for k in known},'valid_usage':valid,'exit_code':code,'timed_out':timed_out,'budget_stopped':any(r.get('event')=='budget_stop' for r in meter),'session_id':sessions[0]['sessionId'] if sessions else session,'resumed':bool(session),'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'plan_sha256':(BASE/'plan.sha256').read_text().strip(),'wall_seconds':time.monotonic()-started}
 (out/'record.json').write_text(json.dumps(record,indent=2)+'\n')
 result=grade(BASE/'active'/arm,stage)
 record.update(grade=result,accepted=result['success'] and valid,native_exit_success=code==0,final_message_present=bool(finals),final=finals[-1] if finals else None)
 (out/'record.json').write_text(json.dumps(record,indent=2)+'\n')
 with tarfile.open(out/'final.tgz','w:gz') as a:a.add(BASE/'active'/arm,arcname='project')
 print(json.dumps({k:record[k] for k in ['task','arm','attempt','requests','tool_calls','costs','accepted','valid_usage','exit_code']}),flush=True)
 if code:print('DIAGNOSTIC', (out/'stderr.log').read_text()[-1200:],flush=True)
 if not valid:raise RuntimeError('Stop comparison: missing usage, routing/model/tool activation error or provider failure; all attempts retained')
 return record

def available(arm):
 prior=records();used=totals(prior);local=totals([r for r in prior if r['arm']==arm])
 return used['requests']<PLAN['total_max_requests'] and local['requests']<PLAN['per_arm_max_requests'] and used['allowance']<Decimal(PLAN['total_max_allowance_usd']) and local['allowance']<Decimal(PLAN['per_arm_max_allowance_usd'])

def skip(index,stage,arm,reason):
 with (BASE/'skips.jsonl').open('a') as f:f.write(json.dumps(dict(index=index,stage=stage,arm=arm,reason=reason))+'\n')
 print('SKIP',index,arm,reason,flush=True)

def run(index):
 _,stage,arm=PLAN['schedule'][index];prior=[r for r in records() if r['arm']==arm]
 if any(r['index']==index for r in prior):raise RuntimeError('Attempt already exists; refusing to rerun')
 if stage and not any(r['stage']==stage-1 and r.get('accepted') for r in prior):
  skip(index,stage,arm,'previous task artifact not accepted');return
 if not available(arm):
  skip(index,stage,arm,'request or allowance guard reached');return
 session=max(prior,key=lambda r:(r['stage'],r['attempt']))['session_id'] if prior else None
 record=invoke(index,stage,arm,0,PLAN['sequences'][0]['tasks'][stage]['prompt'],session)
 if not record['accepted']:
  if not available(arm):
   skip(index,stage,arm,'no budget for the single follow-up');return
  kind='interruption_recovery' if record['exit_code']!=0 or record['timed_out'] or record['budget_stopped'] else 'semantic_repair'
  feedback='The independent check of this task did not pass. Continue from the current files and finish this task. Preserve previously accepted changes and do not remove or weaken existing tests.\n'+json.dumps({k:v for k,v in record['grade'].items() if k!='success'},indent=2)
  record=invoke(index,stage,arm,1,feedback,record['session_id'],attempt_kind=kind)
 print('STAGE_DONE',index,arm,record['accepted'],flush=True)

if __name__=='__main__':
 for index in map(int,sys.argv[1:]):run(index)
