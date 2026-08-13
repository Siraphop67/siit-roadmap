/* ══════════════════════════════════════════════════════════
   app-engine.js — deterministic. no randomness, no LLM.
   eligibility · coverage · roadmap (topological) · target match
   Same contracts as backend/app/engine/*.py
   ══════════════════════════════════════════════════════════ */

/* ── eligibility ────────────────────────────────────────────
   permanent  : field, obligation      → career is cut, with a reason
   temporal   : year                   → career stays, marked "not yet"   (D6)
*/
function eligibility(career, p){
  const perm=[], temporal=[];
  if(p.field && career.field.length && !career.field.includes(p.field)){
    const f=FIELDS.find(x=>x.id===p.field);
    const need=career.field.map(id=>(FIELDS.find(x=>x.id===id)||{}).th).filter(Boolean).join(' หรือ ');
    perm.push({kind:'field',msg:`ต้องเรียน${need} — สาขาของคุณคือ${f?f.th:p.field}`});
  }
  const ob=OBLIGATIONS.find(o=>o.id===p.obligation);
  if(ob && ob.sectors && !ob.sectors.includes(career.sec)){
    perm.push({kind:'obligation',msg:`${ob.th} — อาชีพนี้อยู่ภาค${career.sec} ซึ่งผิดเงื่อนไขทุน`});
  }
  if(p.year && career.minYear && p.year < career.minYear){
    temporal.push({kind:'year',msg:`สมัครได้เมื่อขึ้นปี ${career.minYear}`});
  }
  return {ok:perm.length===0, perm, temporal};
}

/* ── coverage ───────────────────────────────────────────────
   only CV-confirmed levels count toward the number.
   self-reported is tracked separately and never merged. (rule 1)
*/
function coverage(career, confirmed, selfRep){
  let got=0, need=0, fromCv=0, fromSelf=0;
  career.reqs.forEach(([sid,lvNeed])=>{
    need+=lvNeed;
    const cv=confirmed[sid]||0;
    got+=Math.min(cv,lvNeed);
    if(cv>0)fromCv++;
    if((selfRep||{})[sid]>0 && !cv)fromSelf++;
  });
  return {pct: need? Math.round(got/need*100):0, fromCv, fromSelf,
          done: career.reqs.filter(([s,l])=>(confirmed[s]||0)>=l).length,
          total: career.reqs.length};
}

/* ── roadmap ────────────────────────────────────────────────
   topological order over the prerequisite DAG, restricted to
   what this career actually needs (plus prereqs pulled in).
   status: current · in_progress · flexible · locked
*/
function roadmapFor(career, confirmed, selfRep){
  const need=new Set();
  const pull=id=>{
    if(need.has(id))return;
    need.add(id);
    ((SKILL[id]||{}).pre||[]).forEach(pull);
  };
  career.reqs.forEach(([sid])=>pull(sid));

  const target={};
  career.reqs.forEach(([sid,lv])=>target[sid]=lv);
  need.forEach(id=>{ if(!target[id])target[id]=2; });   // pulled-in prereqs default to level 2

  /* Kahn topological sort — stable, so the order never jumps around */
  const ids=[...need];
  const indeg={}, adj={};
  ids.forEach(i=>{indeg[i]=0;adj[i]=[]});
  ids.forEach(i=>((SKILL[i]||{}).pre||[]).forEach(p=>{
    if(need.has(p)){adj[p].push(i);indeg[i]++;}
  }));
  const q=ids.filter(i=>indeg[i]===0).sort();
  const order=[];
  while(q.length){
    const n=q.shift();order.push(n);
    adj[n].forEach(m=>{ if(--indeg[m]===0)q.push(m); });
  }
  ids.forEach(i=>{ if(!order.includes(i))order.push(i); });   // cycle guard

  const met=id=>(confirmed[id]||0)>=(target[id]||1);
  const steps=order.map(id=>{
    const sk=SKILL[id]||{th:id,pre:[]};
    const cur=confirmed[id]||0;
    const self=(selfRep||{})[id]||0;
    const tgt=target[id];
    const unlocked=sk.pre.every(p=>!need.has(p)||met(p));
    let st;
    if(cur>=tgt) st='done';
    else if(sk.flex) st='flexible';
    else if(!unlocked) st='locked';
    else if(cur>0) st='in_progress';
    else st='current';
    return {
      id, th:sk.th, cur, self, tgt, st,
      ev: cur>0 ? 'cv' : (self>0 ? 'self' : null),
      blockedBy: sk.pre.filter(p=>need.has(p)&&!met(p)),
      unlocks: (adj[id]||[]).length
    };
  });

  /* the one actionable step — first unlocked, unfinished, non-flexible */
  const next=steps.find(s=>s.st==='current'||s.st==='in_progress')||null;
  if(next)next.actionable=true;
  return {steps,next};
}

/* ── resources for a step, filtered by the student's real limits ── */
function resourcesFor(id,p){
  const list=(RES[id]||RES_DEFAULT).map(r=>({...r}));
  return list.map(r=>{
    let blocked=null;
    if(r.year && p.year && p.year<r.year) blocked=`เปิดให้ลงเมื่อขึ้นปี ${r.year}`;
    else if(r.cost && p.budget!=null && r.cost>p.budget) blocked=`เกินงบที่ตั้งไว้ (${r.cost.toLocaleString()} บาท)`;
    else if(r.hours && p.hours && r.hours>p.hours*14) blocked=`ใช้เวลา ${r.hours} ชม. มากกว่าที่คุณมีใน 14 สัปดาห์`;
    return {...r,blocked};                    /* blocked options stay visible, with the reason */
  });
}

/* ── target match ───────────────────────────────────────────
   score = Σ(answer × how much this career does that activity)
   every suggestion must trace back to an answer the user gave. (D3)
*/
function matchTargets(answers, profile){
  if(!answers.length)return {ranked:[],separated:false};
  const score={}, why={}, heads={};
  CAREERS.forEach(c=>{score[c.id]=0;why[c.id]=[];heads[c.id]=[];});

  answers.forEach(a=>{
    const q=QUESTIONS.find(x=>x.id===a.id); if(!q)return;
    CAREERS.forEach(c=>{
      const w=q.w[c.id]||0;
      score[c.id]+=a.answer*w;
      if(a.answer>0 && w>=2) why[c.id].push(`คุณอยาก${q.p} และงานนี้ได้ทำเยอะ`);
      if(a.answer<0 && w>=3) heads[c.id].push(`งานนี้ต้อง${q.p} ค่อนข้างเยอะ ซึ่งคุณบอกว่าไม่อยากทำ`);
    });
  });

  let list=CAREERS.map(c=>{
    const el=eligibility(c,profile);
    return {c,raw:score[c.id],why:why[c.id].slice(0,3),heads:heads[c.id].slice(0,2),el,
            unconsidered: profile.field ? !c.field.includes(profile.field) : false};
  })
  .filter(x=>x.why.length>0)                       /* no traceable reason → not shown at all */
  .sort((a,b)=>b.raw-a.raw);

  const eligible=list.filter(x=>x.el.ok);
  const top=eligible.length?eligible:list;
  const hi=top.length?top[0].raw:0, lo=top.length?top[top.length-1].raw:0;
  const span=Math.max(hi-lo,1);
  top.forEach((x,i)=>{ x.rank=i+1; x.score=i===0?100:Math.round(((x.raw-lo)/span)*99); });

  const separated = top.length<2 ? true : (top[0].raw-top[1].raw) >= 3;
  const unconsidered = list.find(x=>x.unconsidered && x.el.perm.length===0 && !top.includes(x))||null;
  if(unconsidered){ unconsidered.score=Math.round(((unconsidered.raw-lo)/span)*99); }

  return {ranked:top.slice(0,4), separated, unconsidered,
          pair: top.length>1?[top[0].c.th,top[1].c.th]:null};
}
