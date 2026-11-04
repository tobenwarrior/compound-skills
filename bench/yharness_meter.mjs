import { createHash } from 'node:crypto';
import { appendFileSync } from 'node:fs';
const original = globalThis.fetch;
let pending;
let unverifiable = false;
let calls = 0, used = 0;
const path = process.env.COMPOUND_PILOT_METER;
const maxCalls = Number(process.env.COMPOUND_PILOT_MAX_CALLS ?? 20);
const maxCost = Number(process.env.COMPOUND_PILOT_MAX_USD ?? 0.25);
const expectedModel = process.env.COMPOUND_PILOT_EXPECT_MODEL;
const expectedOutputCap = process.env.COMPOUND_PILOT_EXPECT_OUTPUT_CAP;
const expectedPromptHash = process.env.COMPOUND_PILOT_EXPECT_PROMPT_SHA256;
const readOnly = process.env.COMPOUND_PILOT_READ_ONLY === '1';
if (!Number.isSafeInteger(maxCalls) || maxCalls < 0 || !Number.isFinite(maxCost) || maxCost < 0) {
  throw new Error('Benchmark has an invalid request or allowance guard');
}

function amountReported(amount) {
  return typeof amount === 'number' && Number.isFinite(amount) && amount >= 0;
}
function save(record) { if (path) appendFileSync(path, JSON.stringify(record) + '\n', {mode:0o600}); }
function normalized(usage) {
  if (!usage || typeof usage !== 'object') return undefined;
  const o = usage.opencode ?? {};
  return {prompt_tokens:usage.prompt_tokens, completion_tokens:usage.completion_tokens, total_tokens:usage.total_tokens,
    cost:usage.cost, billing_source:o.billing_source, list_cost:o.list_cost, allowance:o.allowance,
    tokens:o.tokens, prompt_tokens_details:usage.prompt_tokens_details, completion_tokens_details:usage.completion_tokens_details};
}
export async function observe(response, record) {
  let usage, lastModel, id, text='';
  const accept = line => {
    if (!line.startsWith('data:')) return;
    const payload=line.slice(5).trim(); if (payload==='[DONE]') return;
    try { const value=JSON.parse(payload); if(value.usage) usage=normalized(value.usage); if(value.model) lastModel=value.model; if(value.id) id=value.id; } catch {}
  };
  try {
    if ((response.headers.get('content-type') ?? '').includes('text/event-stream')) {
      const reader=response.body.getReader(); const decoder=new TextDecoder();
      while(true) { const {done,value}=await reader.read(); if(done) break; text+=decoder.decode(value,{stream:true}); let i; while((i=text.indexOf('\n'))>=0){accept(text.slice(0,i).replace(/\r$/,''));text=text.slice(i+1);} }
      text+=decoder.decode(); if(text) accept(text);
    } else { const value=await response.json(); usage=normalized(value.usage);lastModel=value.model;id=value.id; }
    if (amountReported(usage?.allowance)) used += usage.allowance;
    if (record.status !== 200 || (expectedModel && lastModel !== expectedModel) ||
        ![usage?.allowance, usage?.list_cost, usage?.cost].every(amountReported)) {
      unverifiable = true;
    }
    save({...record,model:lastModel,response_id:id,usage,complete:!!usage,ended_at:new Date().toISOString()});
  } catch(error) {
    unverifiable = true;
    save({...record,complete:false,error:String(error),ended_at:new Date().toISOString()});
  }
}
globalThis.fetch = async function(input, init) {
  const url = new URL(typeof input==='string'||input instanceof URL ? input : input.url);
  if(url.hostname!=='opencode.ai' || !/\/(chat\/completions|responses|messages)$/.test(url.pathname)) return original(input,init);
  // Wait for final usage before permitting another model request.
  while (pending) await pending;
  if (unverifiable) {
    save({event:'meter_stop',calls,used});
    throw new Error('Benchmark stopped after an unverified provider response');
  }
  if(calls>=maxCalls || used>=maxCost) { save({event:'budget_stop',calls,used}); throw new Error('Local benchmark request/allowance limit reached'); }
  const body = typeof init?.body === 'string' ? JSON.parse(init.body) : null;
  if ((expectedModel && body?.model !== expectedModel) ||
      (expectedOutputCap && (body?.max_tokens ?? body?.max_completion_tokens) !== Number(expectedOutputCap))) {
    throw new Error('Benchmark refuses request outside the frozen model or output cap');
  }
  if (calls === 0 && body) {
    const prompt=JSON.stringify(body);
    const managedRouting=['global','project'].some(scope =>
      prompt.includes(`<!-- compound-skills:${scope}-setup:start -->`) &&
      prompt.includes(`<!-- compound-skills:${scope}-setup:end -->`));
    const routingPresent=managedRouting || prompt.includes('Review-only: inspect diff/callers/tests;');
    const expected=process.env.COMPOUND_EXPECT_ROUTING;
    if(expected!==undefined && routingPresent!==(expected==='1')) throw new Error('Benchmark refuses request: treatment routing missing or control contaminated');
    const names=(body.tools??[]).map(tool=>tool.function?.name??tool.name);
    const required = readOnly ? ['bash', 'read', 'grep', 'glob'] : ['bash', 'read', 'edit', 'write'];
    if (!required.every(name => names.includes(name)) || (readOnly && (names.includes('edit') || names.includes('write')))) {
      throw new Error('Benchmark refuses model request: tool set does not match the run mode');
    }
    if (expectedPromptHash) {
      const content = body.messages?.findLast(message => message.role === 'user')?.content;
      const delivered = typeof content === 'string' ? content :
        Array.isArray(content) && content.every(part => part?.type === 'text' && typeof part.text === 'string') ? content.map(part => part.text).join('') : null;
      if (delivered === null || createHash('sha256').update(delivered).digest('hex') !== expectedPromptHash) {
        throw new Error('Benchmark refuses model request: delivered prompt differs from the frozen prompt');
      }
    }
    save({event:'request_preflight',tools:names,routing_present:routingPresent,model:body.model,max_tokens:body.max_tokens??body.max_completion_tokens,
      ...(expectedPromptHash ? {prompt_sha256:expectedPromptHash} : {})});
  }
  const record={event:'request',number:++calls,started_at:new Date().toISOString()};
  save({...record,event:'request_started'});
  let settle;
  pending = new Promise(resolve => { settle = resolve; });
  const finish = () => {
    pending = undefined;
    settle();
  };
  try {
    const response=await original(input,init);
    void observe(response.clone(), {...record,status:response.status}).then(finish, () => {
      unverifiable = true;
      finish();
    });
    return response;
  } catch(error) {
    unverifiable = true;
    try {
      save({...record,complete:false,error:String(error),ended_at:new Date().toISOString()});
    } finally {
      finish();
    }
    throw error;
  }
};
process.once('beforeExit', async () => { await pending; });
