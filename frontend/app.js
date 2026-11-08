'use strict';
const $ = (s, root=document) => root.querySelector(s);
const $$ = (s, root=document) => [...root.querySelectorAll(s)];
const node = (tag, cls='', text='') => { const e=document.createElement(tag); e.className=cls; e.textContent=text; return e; };
let health=null, tables=[], busy=false, history=[], toastTimer;
try { const stored=JSON.parse(localStorage.getItem('datapilot.history.v1') || '[]'); if(Array.isArray(stored)) history=stored.filter(x=>typeof x.question==='string' && x.response && Array.isArray(x.response.trace)).slice(0,20); } catch {}
const dateLabel = value => new Date(value).toLocaleString('ru-RU',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'});
function toast(message){ $('#toast').textContent=message; $('#toast').classList.remove('hidden'); clearTimeout(toastTimer); toastTimer=setTimeout(()=>$('#toast').classList.add('hidden'),3000); }
async function api(path, options={}){
 const response=await fetch('/api'+path,{...options,headers:{'Content-Type':'application/json',...options.headers},signal:AbortSignal.timeout(400000)});
 let data; try {data=await response.json();} catch {throw new Error('Сервер вернул неожиданный ответ. Проверьте запуск backend.');}
 if(!response.ok){const detail=typeof data.detail==='string'?data.detail:'Проверьте запрос и подключение к серверу.'; throw new Error(detail);}
 return data;
}
function showView(view){
 for(const name of ['workspace','schema','history']) $('#'+name+'-view').classList.toggle('hidden',name!==view);
 $$('.nav-item').forEach(x=>x.classList.toggle('active',x.dataset.view===view));
 $('#page-title').textContent={workspace:'AI-аналитик',schema:'Схема данных',history:'История запросов'}[view];
 $('#sidebar').classList.remove('open');
 if(view==='schema') loadSchema();
 if(view==='history') renderHistory();
}
$$('.nav-item').forEach(b=>b.addEventListener('click',()=>showView(b.dataset.view)));
$('#all-schema').addEventListener('click',()=>showView('schema'));
$('#mobile-menu').addEventListener('click',()=>$('#sidebar').classList.toggle('open'));
$('#settings-open').addEventListener('click',()=>{
 $('#settings-current').textContent=health?.mode==='demo'?'Сейчас используется Demo: фиксированные сценарии, без LLM.':'Настроен режим '+(health?.mode || 'неизвестен')+'. Модель: '+(health?.model || 'не указана')+'. Доступность inference проверяется при отправке вопроса.';
 $('#settings-dialog').showModal();
});
$('#settings-close').addEventListener('click',()=>$('#settings-dialog').close());
$('#settings-dialog').addEventListener('click',e=>{if(e.target===$('#settings-dialog'))$('#settings-dialog').close();});
async function refresh(){
 try {
  [health,tables]=await Promise.all([api('/health'),api('/tools/list_tables')]);
  $('#connection-label').textContent='Подключено к'; $('#connection-side').textContent='Подключено';
  ['#connection-dot','#connection-main'].forEach(x=>$(x).classList.remove('offline'));
  $('#table-count').textContent=tables.length; $('#tables-label').textContent=tables.length+' таблиц';
  const demo=health.mode==='demo';
  $('#mode-label').textContent=demo?'Demo-режим':'Tiny Aya · AI-режим'; $('#composer-mode').textContent=demo?'Demo':'Tiny Aya';
  $('#demo-note').textContent=demo?'ⓘ Demo: три готовых сценария с реальными данными PostgreSQL. Свободные вопросы доступны после подключения модели.':'✧ AI-режим настроен. Модель сама выбирает инструменты; каждый SQL-запрос проходит проверку. Inference может занять несколько минут.';
  const list=$('#schema-list'); list.replaceChildren();
  tables.forEach(t=>{const b=node('button','schema-table');b.append(node('span','table-icon','▦'),node('span','',t.table_name),node('span','table-arrow','↗'));b.addEventListener('click',()=>{showView('schema');});list.append(b);});
 } catch(error){
  $('#connection-label').textContent='Нет соединения';$('#connection-side').textContent='Недоступно';
  ['#connection-dot','#connection-main'].forEach(x=>$(x).classList.add('offline'));
  $('#mode-label').textContent='Backend недоступен'; $('#schema-list').replaceChildren(node('p','muted','Не удалось загрузить схему. Нажмите ↻ после запуска PostgreSQL.'));
  toast('Не удалось подключиться к базе');
 }
}
$('#refresh').addEventListener('click',refresh);
function saveHistory(){try {localStorage.setItem('datapilot.history.v1',JSON.stringify(history));}catch {toast('История не сохранена: хранилище браузера заполнено.');}renderRecent();}
function renderRecent(){const list=$('#recent-list');list.replaceChildren();if(!history.length)list.append(node('p','muted','Здесь появятся ваши вопросы'));history.slice(0,5).forEach(item=>{const b=node('button','recent-item',item.question);b.title=item.question;b.addEventListener('click',()=>openSaved(item));list.append(b);});}
function renderHistory(){const list=$('#history-list');list.replaceChildren();if(!history.length)list.append(node('p','muted','Пока нет запросов. Начните с вопроса в рабочей области.'));history.forEach(item=>{const b=node('button','history-item');b.append(node('strong','',item.question),node('span','',dateLabel(item.date)));b.addEventListener('click',()=>openSaved(item));list.append(b);});$('#clear-history').disabled=!history.length;}
function openSaved(item){if(busy){toast('Дождитесь завершения текущего запроса.');return;}showView('workspace');$('#conversation').replaceChildren();renderTurn(item.question,item.response);$('#suggestions').classList.add('hidden');}
$('#clear-history').addEventListener('click',()=>{history=[];saveHistory();renderHistory();toast('История очищена');});
$('#new-chat').addEventListener('click',()=>{if(busy){toast('Дождитесь завершения запроса.');return;}showView('workspace');$('#conversation').replaceChildren();$('#suggestions').classList.remove('hidden');$('#question').value='';$('#question').focus();});
$$('.suggestion').forEach(b=>b.addEventListener('click',()=>ask(b.dataset.question)));
$('#question-form').addEventListener('submit',e=>{e.preventDefault();ask($('#question').value.trim());});
$('#question').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();$('#question-form').requestSubmit();}});
async function streamChat(question, signal, showProgress) {
 const response = await fetch('/api/chat/stream', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({question}),
  signal: AbortSignal.any([signal, AbortSignal.timeout(400000)])
 });
 if (!response.ok || !response.body) throw new Error('Не удалось начать запрос.');
 const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
 let pending = '';
 try {
  while (true) {
   const {value, done} = await reader.read();
   if (done) throw new Error('Соединение закрыто до получения результата.');
   pending += value;
   let newline;
   while ((newline = pending.indexOf('\n')) !== -1) {
    const event = JSON.parse(pending.slice(0, newline));
    pending = pending.slice(newline + 1);
    if (event.type === 'progress') showProgress(event.step);
    if (event.type === 'error') throw new Error(event.detail);
    if (event.type === 'result') return event.data;
   }
  }
 } finally {
  await reader.cancel().catch(() => {});
 }
}
const stepLabels = {
 choose: 'Агент выбирает следующий шаг…',
 summarize: 'Формирую ответ по результатам SQL…',
 list_tables: 'Читаю список таблиц…',
 describe_table: 'Проверяю столбцы таблицы…',
 get_relationships: 'Изучаю связи таблиц…',
 execute_sql: 'Выполняю SQL…',
 finish: 'Сохраняю результат…'
};
async function ask(question){
 if(!question||busy)return;
 busy=true;$('#send').disabled=true;$('#question').disabled=true;$$('.suggestion').forEach(b=>b.disabled=true);
 $('#suggestions').classList.add('hidden');$('#question').value='';
 const turn=node('article','turn');const q=node('div','question-message');q.append(node('span','avatar','ВЫ'),node('span','',question));turn.append(q);
 const controller = new AbortController();
 const status = node('span', '', 'Запускаю запрос…');
 status.setAttribute('role', 'status');
 const cancel = node('button', 'small-button', 'Отменить');
 cancel.addEventListener('click', () => controller.abort());
 const loading = node('div', 'loading-line');
 loading.append(node('span', 'spinner'), status, cancel);
 turn.append(loading);
 $('#conversation').append(turn);
 try{
  const response=await streamChat(question, controller.signal, step => { status.textContent = stepLabels[step] || 'Обрабатываю запрос…'; });
  turn.remove();renderTurn(question,response);
  history.unshift({question,response,date:Date.now()});history=history.slice(0,20);saveHistory();
 }catch(error){loading.remove();turn.append(node('div','error-card',controller.signal.aborted?'Запрос отменён.':error.name==='TimeoutError'?'Время ожидания истекло. Проверьте модель и backend.':error.message));}
 finally{busy=false;$('#send').disabled=false;$('#question').disabled=false;$$('.suggestion').forEach(b=>b.disabled=false);$('#question').focus();}
}
function format(value){if(value===null||value===undefined)return 'NULL';if(typeof value==='object')return JSON.stringify(value);if(typeof value==='number')return new Intl.NumberFormat('ru-RU',{maximumFractionDigits:4}).format(value);return String(value);}
function renderTurn(question,data){
 const turn=node('article','turn');const q=node('div','question-message');q.append(node('span','avatar','ВЫ'),node('span','',question));turn.append(q);
 const header=node('div','answer-header');header.append(node('span','mini-brand','✳'),node('strong','','DataPilot'),node('span','',data.mode==='demo'?'· Demo':'· Tiny Aya'));turn.append(header,node('div','answer-text',data.answer));
 if(data.result){
  const card=node('div','result-card'),toolbar=node('div','result-toolbar'),tabs=node('div','tabs');toolbar.append(tabs);
  const download=node('button','small-button','↓ CSV');download.addEventListener('click',()=>exportCSV(data.result));toolbar.append(download);card.append(toolbar);
  const panels={data:node('div','result-panel'),sql:node('div','result-panel hidden'),trace:node('div','result-panel hidden')};
  for(const [key,label]of [['data','Данные'],['sql','SQL'],['trace','Шаги агента']]){const b=node('button','tab'+(key==='data'?' active':''),label);b.setAttribute('aria-pressed',String(key==='data'));b.addEventListener('click',()=>{Object.entries(panels).forEach(([k,p])=>p.classList.toggle('hidden',k!==key));$$('.tab',tabs).forEach(t=>{t.classList.toggle('active',t===b);t.setAttribute('aria-pressed',String(t===b));});});tabs.append(b);}
  const result=data.result;
  if(result.rows.length>1 && result.rows.length<=10){const cols=result.columns || Object.keys(result.rows[0]);const label=cols.find(c=>typeof result.rows[0][c]==='string'),value=cols.find(c=>typeof result.rows[0][c]==='number');if(label&&value){const values=result.rows.map(r=>Number(r[value]));const max=Math.max(...values);if(max>0 && values.every(x=>x>=0)){const chart=node('div','query-chart');result.rows.forEach(r=>{const row=node('div','chart-row'),track=node('div','chart-track'),bar=node('div','chart-bar');bar.style.width=(Number(r[value])/max*100)+'%';track.append(bar);row.append(node('span','chart-label',format(r[label])),track,node('span','chart-value',format(r[value])));chart.append(row);});panels.data.append(chart);}}}
  const scroll=node('div','table-scroll'),table=node('table'),thead=node('thead'),tr=node('tr');const cols=result.columns || Object.keys(result.rows[0]||{});cols.forEach(c=>tr.append(node('th','',c)));thead.append(tr);table.append(thead);const tbody=node('tbody');result.rows.forEach(row=>{const tr=node('tr');cols.forEach(c=>tr.append(node('td','',format(row[c]))));tbody.append(tr);});table.append(tbody);scroll.append(table);panels.data.append(scroll);if(!result.rows.length)panels.data.append(node('p','muted','Запрос выполнен. Строк не найдено.'));
  panels.sql.append(node('pre','',result.sql));const copy=node('button','small-button','Копировать SQL');copy.style.margin='12px';copy.addEventListener('click',async()=>{try{await navigator.clipboard.writeText(result.sql);toast('SQL скопирован');}catch{toast('Копирование недоступно. Выделите SQL вручную.');}});panels.sql.append(copy);
  const trace=node('div','trace-list');data.trace.forEach((step,index)=>{const details=node('details','trace-item'),summary=node('summary');summary.append(node('span','trace-step',index+1),node('span','',step.name),node('span','trace-ok','✓ Выполнено'));details.append(summary,node('pre','',JSON.stringify(step,null,2)));trace.append(details);});panels.trace.append(trace);
  Object.values(panels).forEach(p=>card.append(p));const meta=node('div','result-meta');meta.append(node('span','',result.rows.length+' строк'+(result.truncated?' · лимит достигнут':'')),node('span','',data.trace.length+' вызова инструментов'),node('span','',((data.elapsed_ms||0)/1000).toFixed(2)+' с'),node('span','','✓ Read-only'));card.append(meta);turn.append(card);
 }
 $('#conversation').append(turn);
}
function exportCSV(result){
 const columns=result.columns||Object.keys(result.rows[0]||{});
 // Prevent spreadsheet formula injection in exported strings.
 const cell=v=>{let s=v==null?'':String(v);if(typeof v==='string'&&/^[=+\-@\t\r]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"';};
 const csv='\ufeff'+[columns.map(cell).join(','),...result.rows.map(r=>columns.map(c=>cell(r[c])).join(','))].join('\r\n');
 const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));const a=node('a');a.href=url;a.download='datapilot-result.csv';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('CSV сохранён');
}
async function loadSchema(){
 const root=$('#schema-detail');root.replaceChildren(node('p','muted','Загрузка схемы…'));
 try{
  const list=await api('/tools/list_tables');const [columns,relationships]=await Promise.all([Promise.all(list.map(t=>api('/tools/describe_table/'+encodeURIComponent(t.table_name)))),api('/tools/get_relationships')]);root.replaceChildren();
  list.forEach((t,i)=>{const card=node('article','table-detail');card.append(node('h2','','▦ '+t.table_name));const table=node('table'),head=node('thead'),tr=node('tr');['Столбец','Тип','NULL'].forEach(c=>tr.append(node('th','',c)));head.append(tr);table.append(head);const body=node('tbody');columns[i].forEach(c=>{const tr=node('tr');[c.column_name,c.data_type,c.is_nullable].forEach(x=>tr.append(node('td','',x)));body.append(tr);});table.append(body);card.append(table);root.append(card);});
  const rel=node('article','relationships');rel.append(node('h2','','Связи таблиц'));relationships.forEach(x=>rel.append(node('div','relationship',x.table_name+'.'+x.column_name+' → '+x.foreign_table_name+'.'+x.foreign_column_name)));root.append(rel);
 }catch(error){root.replaceChildren(node('div','error-card',error.message));}
}
renderRecent();refresh();
