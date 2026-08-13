/* ══════════════════════════════════════════════════════════
   app-ui.js — state, hash router, views.
   Every view renders into #view. No CSS display toggling of
   stacked sections, so no specificity collisions.
   ══════════════════════════════════════════════════════════ */
window.addEventListener('error',ev=>{
  let b=document.getElementById('errbar');
  if(!b){b=document.createElement('pre');b.id='errbar';
    b.style.cssText='position:fixed;left:0;right:0;bottom:0;z-index:99999;margin:0;padding:12px 16px;background:#B3271C;color:#fff;font:12px/1.6 monospace;white-space:pre-wrap;max-height:40vh;overflow:auto';
    document.body.appendChild(b);}
  b.textContent+='JS ERROR: '+(ev.message||ev.error)+'  @'+(ev.lineno||'?')+':'+(ev.colno||'?')+'\n';
});

const APP_NAME="[ชื่อระบบ]";
const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const KEY='siit.v5';

/* ══ STATE ══ */
const BLANK={answers:[],qi:0,target:null,raw:'',spans:[],confirmed:{},selfRep:{},
  profile:{field:'',year:null,gpa:null,obligation:'none',hours:8,budget:1500}};
let S=load();
function load(){
  try{const j=JSON.parse(localStorage.getItem(KEY));if(j&&j.profile)return {...structuredClone(BLANK),...j};}catch(e){}
  return structuredClone(BLANK);
}
function save(){ try{localStorage.setItem(KEY,JSON.stringify(S));}catch(e){} }
function reset(){ S=structuredClone(BLANK); try{localStorage.removeItem(KEY);}catch(e){} }

const career=id=>CAREERS.find(c=>c.id===id);
function targetCareer(){ return S.target?career(S.target):null; }

/* ══ ROUTER ══ */
const ROUTES={quiz:vQuiz,result:vResult,careers:vCareers,career:vCareerDetail,
  roadmap:vRoadmap,upload:vUpload,evidence:vEvidence,profile:vProfile,data:vData};

function parse(){
  const h=(location.hash||'').replace(/^#\/?/,'');
  if(!h)return {name:'',arg:''};
  const [name,arg]=h.split('/');
  return {name,arg:arg||''};
}
function render(){
  const {name,arg}=parse();
  const app=$('#app'), land=$('#landing');
  if(!name||!ROUTES[name]){
    app.classList.remove('on'); land.style.display='';
    document.body.style.background='#fff';
    return;
  }
  land.style.display='none'; app.classList.add('on');
  $('#view').innerHTML=ROUTES[name](arg);
  if(!RM)$('#view').classList.add('fade');
  setTimeout(()=>$('#view').classList.remove('fade'),300);
  paintChrome(name);
  window.scrollTo(0,0);
}
function goTo(r){ location.hash='#/'+r; }
addEventListener('hashchange',render);

function paintChrome(name){
  $$('.nav[data-r],.botnav button[data-r]').forEach(b=>b.classList.toggle('on',b.dataset.r===name));
  $('#dQuiz').style.display=S.answers.length>=6?'':'none';
  $('#dTarget').style.display=S.target?'':'none';
  $('#dCv').style.display=Object.keys(S.confirmed).length?'':'none';
  $('#dProf').style.display=S.profile.field?'':'none';
  const t=targetCareer();
  $('#topTarget').textContent=t?t.th:'';
  $('#rail').innerHTML=railHtml();
}

/* ══ RAIL ══ */
function railHtml(){
  const t=targetCareer();
  if(!t){
    return `<div class="railcard">
      <p class="mono up" style="color:var(--g-dark)">ยังไม่ได้เลือกเป้าหมาย</p>
      <p class="small" style="margin-top:8px;color:var(--ink)">ทำแบบทดสอบ หรือเลือกอาชีพเอง แล้วเส้นทางจะขึ้นตรงนี้</p>
      <button class="btn btn-g btn-sm btn-block" style="margin-top:14px" onclick="goTo('quiz')">ทำแบบทดสอบ</button>
    </div>
    <p class="mono up" style="margin-bottom:8px">ความคืบหน้า</p>
    <p class="small">ตอบแบบทดสอบ ${S.answers.length}/${QUESTIONS.length} ข้อ</p>
    <p class="small">ยืนยันทักษะจาก CV ${Object.keys(S.confirmed).length} รายการ</p>`;
  }
  const cov=coverage(t,S.confirmed,S.selfRep);
  const rm=roadmapFor(t,S.confirmed,S.selfRep);
  return `<div class="railcard">
    <p class="mono up" style="color:var(--g-dark)">เป้าหมาย</p>
    <p style="font-size:18px;font-weight:600;margin-top:4px">${esc(t.th)}</p>
    <p style="font-family:var(--mono);font-size:44px;line-height:1.1;margin-top:12px">${cov.pct}<span style="font-size:.42em">%</span></p>
    <p class="mono" style="color:var(--g-dark)">${cov.done} / ${cov.total} ทักษะครบแล้ว</p>
    <div style="margin-top:12px;display:flex;gap:12px;flex-wrap:wrap">
      <span class="tag tag-g">${cov.fromCv} จาก CV</span><span class="tag tag-d">${cov.fromSelf} กรอกเอง</span>
    </div>
  </div>
  ${rm.next?`<div class="railcard" style="background:#fff;border:1.5px solid var(--line)">
    <p class="mono up">ก้าวถัดไป</p>
    <p style="font-size:15.5px;font-weight:500;margin-top:6px;line-height:1.55">${esc(rm.next.th)}</p>
    <button class="btn btn-g btn-sm btn-block" style="margin-top:12px" onclick="goTo('roadmap')">ดูวิธีไปถึง</button>
  </div>`:''}
  <button class="btn btn-line btn-sm btn-block" onclick="goTo('careers')">เปลี่ยนเป้าหมาย</button>`;
}

/* ══ helpers ══ */
function lvBar(cur,tgt,kind){
  let h='<span class="lv">';
  for(let i=1;i<=3;i++)h+=`<i class="${i<=cur?(kind==='self'?'claim':'on'):''}"></i>`;
  return h+'</span>';
}
function head(title,sub){
  return `<p class="mono up">${esc(sub||'')}</p><h2 style="margin-top:8px">${esc(title)}</h2>`;
}

/* ══════════ QUIZ ══════════ */
function vQuiz(){
  if(S.qi>=QUESTIONS.length) { location.hash='#/result'; return ''; }
  const q=QUESTIONS[S.qi];
  const showInterim = S.qi>0 && S.qi%6===0 && !S.seenInterim;
  if(showInterim){
    const m=matchTargets(S.answers,S.profile);
    S.seenInterim=true;save();
    return `${head('ระหว่างทาง','ตอบไปแล้ว '+S.answers.length+' ข้อ')}
      <div class="card" style="margin-top:22px">
        ${m.separated
          ? `<h3>ตอนนี้ชัดแล้ว</h3><p class="body" style="margin-top:8px">${esc((m.ranked[0]||{}).c ? m.ranked[0].c.th : '')} กำลังนำอยู่ชัดเจน — ตอบต่ออีกหน่อยเพื่อความมั่นใจ</p>`
          : `<h3>ยังแยกไม่ออกระหว่างสองอาชีพนี้</h3>
             <p class="body" style="margin-top:8px">${m.pair?esc(m.pair[0])+' กับ '+esc(m.pair[1]):'อันดับ 1 กับ 2'} ยังห่างกันไม่พอ ขอถามอีกหน่อย</p>`}
        <p class="note g" style="margin-top:18px">เราบอกตรง ๆ ว่ายังไม่ชัด ดีกว่ายัดอันดับให้ดูมั่นใจ</p>
        <div class="row" style="margin-top:20px">
          <button class="btn btn-g" onclick="S.seenInterim=false;save();render()">ถามต่อ</button>
          <button class="btn btn-line" onclick="goTo('result')">ดูผลเลย</button>
        </div>
      </div>`;
  }
  S.seenInterim=false;
  const dots=QUESTIONS.map((_,k)=>`<i class="${k<S.qi?'on':''}"></i>`).join('');
  return `${head('แบบทดสอบกิจกรรม','ข้อ '+(S.qi+1)+' จาก '+QUESTIONS.length)}
    <div class="dots" style="margin-top:20px">${dots}</div>
    <div class="card">
      <p class="mono">คุณอยากทำสิ่งนี้ไหม</p>
      <h3 style="margin-top:10px;font-size:clamp(21px,3.4vw,28px);line-height:1.45">${esc(q.p)}</h3>
      <p class="body" style="margin-top:12px">${esc(q.c)}</p>
      <p class="small" style="margin-top:6px">${esc(q.e)}</p>
      <div class="ans">
        <button onclick="answer(1)">อยากทำ</button>
        <button onclick="answer(0)">เฉย ๆ</button>
        <button onclick="answer(-1)">ไม่อยากทำ</button>
      </div>
    </div>
    <p class="mono" style="margin-top:16px">ข้อคำถามไม่มีชื่ออาชีพโดยตั้งใจ — คุณตอบต่อกิจกรรม ไม่ใช่ต่อชื่องาน</p>
    ${S.answers.length?`<button class="btn btn-line btn-sm" style="margin-top:18px" onclick="goTo('result')">ดูผลตอนนี้</button>`:''}`;
}
function answer(v){
  const q=QUESTIONS[S.qi]; if(!q)return;
  S.answers=S.answers.filter(a=>a.id!==q.id);
  S.answers.push({id:q.id,answer:v});
  S.qi++;save();
  if(S.qi>=QUESTIONS.length)goTo('result'); else render();
}

/* ══════════ RESULT ══════════ */
function vResult(){
  const m=matchTargets(S.answers,S.profile);
  if(!m.ranked.length){
    return `${head('ยังไม่มีผล','ผลลัพธ์')}
      <p class="body" style="margin-top:14px">ตอบแบบทดสอบอย่างน้อย 3–4 ข้อก่อน ระบบถึงจะมีเหตุผลย้อนกลับไปหาคำตอบของคุณได้</p>
      <button class="btn btn-g" style="margin-top:20px" onclick="goTo('quiz')">ไปทำแบบทดสอบ</button>`;
  }
  const cards=m.ranked.map(x=>`
    <div class="card" style="margin-bottom:14px${x.rank===1?';border-color:var(--g)':''}">
      <div class="row" style="justify-content:space-between;align-items:flex-start">
        <div><p class="mono up" style="color:var(--g-dark)">อันดับ ${x.rank}</p>
          <h3 style="margin-top:4px">${esc(x.c.th)}</h3></div>
        <span style="font-family:var(--mono);font-size:26px;color:var(--g-dark)">${x.score}</span>
      </div>
      ${x.el.temporal.length?`<p class="pill pill-w" style="margin-top:10px">${esc(x.el.temporal[0].msg)}</p>`:''}
      <p class="mono up" style="margin-top:16px">ทำไมถึงเสนออาชีพนี้</p>
      ${x.why.map(w=>`<p class="body" style="margin-top:5px">— ${esc(w)}</p>`).join('')}
      ${x.heads.length?`<div class="note s" style="margin-top:14px">
        <p class="mono up" style="color:var(--stop)">สิ่งที่ควรรู้ก่อนเลือก</p>
        ${x.heads.map(h=>`<p style="margin-top:5px;font-size:15px">— ${esc(h)}</p>`).join('')}</div>`:''}
      <button class="btn btn-g btn-block" style="margin-top:16px" onclick="pick('${x.c.id}')">เลือกอาชีพนี้</button>
    </div>`).join('');

  const unc=m.unconsidered?`
    <div class="hr"></div>
    <p class="mono up">ปลายทางที่คุณอาจไม่ได้คิดถึง</p>
    <div class="card" style="margin-top:12px;background:var(--g-soft);border:0">
      <h3>${esc(m.unconsidered.c.th)}</h3>
      <p class="body" style="margin-top:8px">คะแนนดี แต่อยู่นอกสาขาที่คุณเรียน — เราแสดงไว้เพราะทักษะที่คุณมีถ่ายโอนไปได้</p>
      ${m.unconsidered.why.map(w=>`<p class="body" style="margin-top:5px">— ${esc(w)}</p>`).join('')}
      <button class="btn btn-line btn-block" style="margin-top:14px" onclick="pick('${m.unconsidered.c.id}')">ดูเส้นทางของอาชีพนี้</button>
    </div>`:'';

  return `${head('ผลลัพธ์','ตอบไปแล้ว '+S.answers.length+' ข้อ')}
    ${m.separated?'':`<p class="note g" style="margin-top:16px"><strong>อันดับ 1 กับ 2 ยังห่างกันไม่มาก</strong> — ลองดูทั้งสองอาชีพก่อนตัดสินใจ</p>`}
    <div style="margin-top:20px">${cards}</div>
    ${unc}
    <p class="mono" style="margin-top:20px">คะแนนคือตำแหน่งเทียบกันในกลุ่ม 0–100 ไม่ใช่เปอร์เซ็นต์ความเหมาะสม · อันดับ 1 ได้ 100 เสมอ</p>
    <button class="btn btn-line btn-sm" style="margin-top:18px" onclick="goTo('quiz')">ตอบเพิ่มให้ชัดขึ้น</button>`;
}
function pick(id){ S.target=id;save();goTo('roadmap'); }

/* ══════════ CAREERS ══════════ */
function vCareers(){
  const rows=CAREERS.map(c=>({c,el:eligibility(c,S.profile)}));
  const okList=rows.filter(x=>x.el.ok), cut=rows.filter(x=>!x.el.ok);
  const tile=x=>{
    const cov=coverage(x.c,S.confirmed,S.selfRep);
    return `<button class="card click" onclick="location.hash='#/career/${x.c.id}'">
      <div class="thumb"><img src="${CAREER_IMG[x.c.id]||''}" alt="${esc(IMG_ALT[x.c.id]||'')}" loading="lazy"></div>
      <p class="mono up">${x.c.id} · ${esc(x.c.sec)}</p>
      <h3 style="margin-top:7px">${esc(x.c.th)}</h3>
      <p class="body" style="font-size:16px;margin-top:6px">${esc(x.c.sum)}</p>
      <div class="row" style="margin-top:13px">
        <span class="pill">${x.c.reqs.length} ทักษะ</span>
        ${Object.keys(S.confirmed).length?`<span class="pill">ตรงแล้ว ${cov.pct}%</span>`:''}
        ${x.el.temporal.map(t=>`<span class="pill pill-w">${esc(t.msg)}</span>`).join('')}
        ${S.target===x.c.id?`<span class="pill" style="background:var(--ink);color:#fff">เป้าหมายปัจจุบัน</span>`:''}
      </div></button>`;
  };
  return `${head('อาชีพ','ปลายทาง '+CAREERS.length+' อาชีพ')}
    ${S.profile.field?'':`<p class="note g" style="margin-top:16px">กรอกโปรไฟล์ก่อน ระบบจะกรองอาชีพที่ผิดเงื่อนไขสาขาและทุนออกให้ พร้อมบอกเหตุผล
      <button class="btn btn-g btn-sm" style="margin-top:10px" onclick="goTo('profile')">กรอกโปรไฟล์</button></p>`}
    <div class="grid2" style="margin-top:20px">${okList.map(tile).join('')}</div>
    ${cut.length?`<div class="hr"></div>
      <h3>ไม่ตรงเงื่อนไขของคุณ</h3>
      <p class="small" style="margin-top:4px">แสดงพร้อมเหตุผลเสมอ — อาชีพหายเงียบ ๆ คือบั๊ก ไม่ใช่ฟีเจอร์</p>
      <div class="grid2" style="margin-top:14px">
        ${cut.map(x=>`<div class="card off">
          <div class="thumb"><img src="${CAREER_IMG[x.c.id]||''}" alt="${esc(IMG_ALT[x.c.id]||'')}" loading="lazy"></div>
          <p class="mono up">${x.c.id}</p>
          <h3 style="margin-top:7px;color:var(--grey)">${esc(x.c.th)}</h3>
          ${x.el.perm.map(p=>`<p class="pill pill-s" style="margin-top:10px">${esc(p.msg)}</p>`).join('')}
        </div>`).join('')}</div>`:''}`;
}

/* ══════════ CAREER DETAIL ══════════ */
function vCareerDetail(id){
  const c=career(id); if(!c)return vCareers();
  const el=eligibility(c,S.profile);
  const cov=coverage(c,S.confirmed,S.selfRep);
  return `<button class="btn btn-line btn-sm" onclick="goTo('careers')">← กลับ</button>
    <div class="banner"><img src="${CAREER_IMG[c.id]||''}" alt="${esc(IMG_ALT[c.id]||'')}"></div>
    <p class="mono up" style="margin-top:18px">${c.id} · ${esc(c.sec)} · ${esc(c.en)}</p>
    <h2 style="margin-top:6px">${esc(c.th)}</h2>
    <p class="lead" style="margin-top:12px">${esc(c.sum)}</p>
    ${el.perm.map(p=>`<p class="note s" style="margin-top:16px">${esc(p.msg)}</p>`).join('')}
    ${el.temporal.map(t=>`<p class="pill pill-w" style="margin-top:12px">${esc(t.msg)}</p>`).join('')}
    <div class="hr"></div>
    <p class="mono up">วันหนึ่งของอาชีพนี้</p>
    <p class="body" style="margin-top:8px">${esc(c.day)}</p>
    <div class="hr"></div>
    <div class="row" style="justify-content:space-between">
      <p class="mono up">ต้องเคยทำอะไรมาแล้ว · ${c.reqs.length} ทักษะ</p>
      <p class="mono tag-g">ตอนนี้คุณมี ${cov.pct}%</p>
    </div>
    <div style="margin-top:14px">
      ${c.reqs.map(([sid,lv])=>{
        const cur=S.confirmed[sid]||0;
        return `<div class="st" style="grid-template-columns:1fr auto;gap:14px">
          <div><p class="t">${esc((SKILL[sid]||{}).th||sid)}</p>
            <p class="mono" style="margin-top:4px">${sid} · ต้องถึง ${LVL[lv]}</p></div>
          <div style="text-align:right">${lvBar(cur,lv,'cv')}</div></div>`;
      }).join('')}
    </div>
    ${el.perm.length?'':`<button class="btn btn-g btn-block" style="margin-top:24px" onclick="pick('${c.id}')">
      ${S.target===c.id?'ดูเส้นทาง':'ตั้งเป็นเป้าหมาย แล้วดูเส้นทาง'}</button>`}`;
}

/* ══════════ ROADMAP ══════════ */
function vRoadmap(){
  const t=targetCareer();
  if(!t){
    return `${head('ยังไม่ได้เลือกเป้าหมาย','เส้นทาง')}
      <div class="banner ph duo" style="margin-top:18px"><img src="img/d-crane.jpg" alt="เครนที่ไซต์ก่อสร้าง"></div>
      <p class="body" style="margin-top:18px">เลือกอาชีพก่อน แล้วเราจะคำนวณเส้นทางจากทักษะที่คุณมีจริงตอนนี้</p>
      <div class="row" style="margin-top:20px">
        <button class="btn btn-g" onclick="goTo('quiz')">ทำแบบทดสอบ</button>
        <button class="btn btn-line" onclick="goTo('careers')">เลือกอาชีพเอง</button>
      </div>`;
  }
  const cov=coverage(t,S.confirmed,S.selfRep);
  const rm=roadmapFor(t,S.confirmed,S.selfRep);
  const noEv=!Object.keys(S.confirmed).length;

  const rows=rm.steps.map((s,i)=>{
    let cls='st';
    if(s.st==='locked')cls+=' locked';
    if(s.actionable)cls+=' act';
    const nx=rm.steps[i+1];
    if(nx&&nx.st==='locked'&&s.st!=='locked')cls+=' pre';
    const nd=s.actionable?'nd half':(s.st==='locked'?'nd open':(s.st==='flexible'?'nd dash':'nd'));
    let meta;
    if(s.actionable)meta='<span class="tag tag-g">ก้าวถัดไปของคุณ</span>';
    else if(s.st==='done')meta=`<span class="tag tag-g">ครบแล้ว</span>${s.unlocks?`<span class="tag"> · ปลดล็อก ${s.unlocks} ก้าว</span>`:''}`;
    else if(s.st==='locked')meta=`<span class="tag">ต้องผ่าน ${s.blockedBy.map(b=>b).join(' · ')} ก่อน</span>`;
    else if(s.st==='flexible')meta='<span class="tag tag-d">ทำคู่ขนานได้ ไม่บล็อกก้าวอื่น</span>';
    else meta='<span class="tag">ยังไม่เริ่ม</span>';

    const opts=s.actionable?`<div style="margin-top:14px">
      <p class="mono up" style="margin-bottom:8px">ทางไปถึง — เลือกเองได้</p>
      ${resourcesFor(s.id,S.profile).map(r=>`
        <div style="padding:10px 0;border-top:1px solid var(--line)">
          <div class="row" style="justify-content:space-between;gap:10px">
            <div style="min-width:0">
              <p style="font-size:15.5px;font-weight:500">${esc(r.title)}</p>
              <p class="mono" style="margin-top:3px">${esc(r.kind)}${r.hours?' · '+r.hours+' ชม.':''}${r.cost?' · '+r.cost.toLocaleString()+' บาท':' · ฟรี'}</p>
            </div>
            ${r.gen?'<span class="pill">ระบบสร้างให้</span>':''}
          </div>
          ${r.blocked?`<p class="pill pill-w" style="margin-top:7px">${esc(r.blocked)}</p>`:''}
        </div>`).join('')}
    </div>`:'';

    return `<div class="${cls}"><span class="${nd}"></span><div style="min-width:0">
      <p class="t">${esc(s.th)}</p>
      <div class="row" style="margin-top:7px">${lvBar(s.cur,s.tgt,s.ev==='self'?'self':'cv')}<span class="mono">${s.id}</span>${meta}</div>
      ${opts}
    </div></div>`;
  }).join('');

  return `<p class="mono up">เส้นทางสู่</p>
    <h2 style="margin-top:6px">${esc(t.th)}</h2>
    <div class="card" style="margin-top:20px;background:var(--g-soft);border:0">
      <div class="row" style="justify-content:space-between;align-items:flex-end">
        <div><p class="mono up" style="color:var(--g-dark)">ความคืบหน้า</p>
          <p style="font-family:var(--mono);font-size:clamp(42px,9vw,64px);line-height:1.05">${cov.pct}<span style="font-size:.4em">%</span></p></div>
        <div style="text-align:right">
          <p class="mono">${cov.done} / ${cov.total} ทักษะ</p>
          <p class="tag tag-g" style="margin-top:5px">${cov.fromCv} จาก CV</p>
          <p class="tag tag-d" style="margin-top:5px;display:inline-block">${cov.fromSelf} กรอกเอง</p>
        </div>
      </div>
    </div>
    ${noEv?`<p class="note g" style="margin-top:18px"><strong>ยังไม่มีหลักฐานเลย</strong> — ส่งผลงานที่เคยทำ แล้ว % จะขยับตามของจริง
      <button class="btn btn-g btn-sm" style="margin-top:10px" onclick="goTo('upload')">ส่งผลงาน</button></p>`:''}
    <div class="steps" style="margin-top:22px">${rows}</div>
    <p class="note" style="margin-top:24px">ข้อกำหนดของอาชีพนี้ทีมเรียบเรียงเอง ยังไม่ได้ยืนยันกับประกาศงานจริง (0 ประกาศ)</p>`;
}

/* ══════════ UPLOAD ══════════ */
function vUpload(){
  return `${head('ส่งผลงาน','อ่านจากสิ่งที่คุณเคยทำ')}
    <p class="lead" style="margin-top:12px">ระบบอ่านว่าผลงานของคุณ<strong style="color:var(--ink)">แสดง</strong>ความสามารถอะไร ไม่ให้คะแนน ไม่ตัดสินคุณภาพ</p>
    <div class="field" style="margin-top:24px">
      <label>วางข้อความจาก CV หรือพอร์ตของคุณ</label>
      <textarea id="cv" rows="7" style="resize:vertical" placeholder="เช่น ปี 3 ทำโปรเจกต์เก็บข้อมูลราคาสินค้าจากเว็บ เขียนด้วย Python แล้วเก็บลง PostgreSQL ตั้ง cron ให้ดึงทุกคืน ใช้ Git ทำงานกับเพื่อน 3 คน">${esc(S.raw)}</textarea>
    </div>
    <div class="row" style="margin-top:12px;justify-content:space-between">
      <button class="btn btn-line btn-sm" onclick="fillSample()">ใส่ตัวอย่าง</button>
      <span class="mono" id="cvn">${S.raw.length} ตัวอักษร</span>
    </div>
    <label style="display:flex;gap:12px;align-items:flex-start;margin-top:22px;cursor:pointer">
      <input type="checkbox" id="ok" style="width:20px;height:20px;flex:none;margin-top:5px;accent-color:var(--g)">
      <span class="small">ยินยอมให้ระบบอ่านข้อความนี้เพื่อหาทักษะ เก็บไว้ในเครื่องคุณเท่านั้น ลบได้ทุกเมื่อ</span>
    </label>
    <p class="note s" id="err" style="display:none;margin-top:16px"></p>
    <button class="btn btn-g btn-block" style="margin-top:20px" onclick="doExtract()">อ่านผลงาน</button>
    <p class="mono" style="margin-top:14px">ตอนนี้ใช้วิธีจับคำสำคัญ ${window.EXTRACT_DICT_SIZE||''} ชุด ยังไม่ใช่ AI — บางคำอาจจับผิด คุณต้องกดยืนยันเองทุกข้อ</p>`;
}
function fillSample(){
  $('#cv').value="ปี 3 ทำโปรเจกต์เก็บข้อมูลราคาสินค้าจากเว็บ เขียนด้วย Python แล้วเก็บลง PostgreSQL ตั้ง cron ให้ดึงทุกคืน ทำ dashboard ให้ทีมดูยอดย้อนหลังได้ ใช้ Git ทำงานร่วมกับเพื่อนอีก 3 คน และเขียน unit test คุมไว้";
  $('#cvn').textContent=$('#cv').value.length+' ตัวอักษร';
}
function doExtract(){
  const err=$('#err');err.style.display='none';
  const text=$('#cv').value.trim();
  const probs=[];
  if(!text)probs.push('ยังไม่ได้ใส่ข้อความ');
  if(!$('#ok').checked)probs.push('ยังไม่ได้ติ๊กยินยอม');
  if(probs.length){err.innerHTML=probs.join('<br>');err.style.display='block';return;}
  const spans=extractSkills(text);
  if(!spans.length){
    err.innerHTML='ไม่พบทักษะในข้อความนี้ — ลองเขียนชื่อเครื่องมือที่ใช้จริง เช่น Python · SolidWorks · MATLAB · Excel · AutoCAD';
    err.style.display='block';return;
  }
  S.raw=text;S.spans=spans;S.ei=0;save();
  goTo('evidence');
}

/* ══════════ EVIDENCE — one skill per screen ══════════ */
function vEvidence(){
  const pend=S.spans.filter(s=>s.status==='pending');
  if(!S.spans.length)return vUpload();
  if(!pend.length){
    const n=S.spans.filter(s=>s.status==='confirmed').length;
    return `${head('ยืนยันครบแล้ว','หลักฐาน')}
      <p class="body" style="margin-top:14px">นับเป็นหลักฐานจากผลงานจริง <strong style="color:var(--ink)">${n} ทักษะ</strong> — เส้นทางคำนวณใหม่ตามนี้แล้ว</p>
      <div class="row" style="margin-top:20px">
        <button class="btn btn-g" onclick="goTo('roadmap')">ดูเส้นทาง</button>
        <button class="btn btn-line" onclick="goTo('upload')">ส่งผลงานเพิ่ม</button>
      </div>`;
  }
  const s=pend[0];
  const done=S.spans.length-pend.length;
  const a=Math.max(0,s.span_start-48),b=Math.min(S.raw.length,s.span_end+48);
  const ctx=(a>0?'… ':'')+esc(S.raw.slice(a,s.span_start))+`<mark>${esc(s.span_text)}</mark>`+esc(S.raw.slice(s.span_end,b))+(b<S.raw.length?' …':'');
  const dots=S.spans.map((_,k)=>`<i class="${k<done?'on':''}"></i>`).join('');
  return `${head('คุณทำสิ่งนี้ได้จริงไหม','ยืนยัน '+(done+1)+' จาก '+S.spans.length)}
    <div class="dots" style="margin-top:18px">${dots}</div>
    <div class="card">
      <p class="mono up">เราเจอคำนี้ในผลงานของคุณ</p>
      <h3 style="margin-top:10px;font-size:clamp(20px,3.2vw,26px);line-height:1.45">${esc(s.th)}</h3>
      <div class="raw" style="margin-top:18px">${ctx}</div>
      <p class="mono" style="margin-top:12px">${s.id} · ตำแหน่ง ${s.span_start}–${s.span_end} · ระดับที่ระบบเดา ${LVL[s.lv]}</p>
      <div class="ans">
        <button onclick="confirmSpan(true)">ใช่ ทำได้</button>
        <button onclick="confirmSpan(false)">ไม่ใช่ ระบบจับผิด</button>
      </div>
    </div>
    <p class="mono" style="margin-top:16px">ยังไม่ยืนยัน = ยังไม่นับ — ระบบจะไม่เอาไปคำนวณเส้นทางจนกว่าคุณจะกด</p>`;
}
function confirmSpan(ok){
  const s=S.spans.find(x=>x.status==='pending'); if(!s)return;
  s.status=ok?'confirmed':'rejected';
  if(ok)S.confirmed[s.id]=Math.max(S.confirmed[s.id]||0,s.lv);
  save();render();
}

/* ══════════ PROFILE ══════════ */
function vProfile(){
  const p=S.profile;
  return `${head('โปรไฟล์','ถามเฉพาะสิ่งที่ผลงานไม่บอก')}
    <div class="stk" style="margin-top:22px;max-width:520px">
      <div class="field"><label>สาขาที่เรียน</label>
        <select id="pf">
          <option value="">ยังไม่ระบุ</option>
          ${FIELDS.map(f=>`<option value="${f.id}" ${p.field===f.id?'selected':''}>${f.th} (${f.id})</option>`).join('')}
        </select></div>
      <div class="row" style="gap:13px;flex-wrap:nowrap">
        <div class="field" style="flex:1"><label>ชั้นปี</label><input id="py" type="number" min="1" max="4" value="${p.year||''}"></div>
        <div class="field" style="flex:1"><label>เกรดเฉลี่ย</label><input id="pg" type="number" step="0.01" value="${p.gpa||''}"></div>
      </div>
      <div class="field"><label>ทุน / เงื่อนไขชดใช้ทุน</label>
        <select id="po">${OBLIGATIONS.map(o=>`<option value="${o.id}" ${p.obligation===o.id?'selected':''}>${o.th}</option>`).join('')}</select>
        <span class="small">เงื่อนไขนี้จะตัดอาชีพที่ผิดเงื่อนไขออกจริง พร้อมบอกเหตุผล</span></div>
      <div class="row" style="gap:13px;flex-wrap:nowrap">
        <div class="field" style="flex:1"><label>เวลา ชม./สัปดาห์</label><input id="ph" type="number" value="${p.hours||''}"></div>
        <div class="field" style="flex:1"><label>งบ บาท</label><input id="pb" type="number" value="${p.budget!=null?p.budget:''}"></div>
      </div>
    </div>
    <p class="note g" style="margin-top:22px"><strong>ทักษะที่กรอกเอง</strong>จะเก็บแยกจากทักษะที่อ่านได้จากผลงานจริง และแสดงด้วยเส้นประเสมอ เพราะยังไม่มีหลักฐานรองรับ</p>
    <p id="pmsg" class="note g" style="display:none;margin-top:16px"></p>
    <button class="btn btn-g btn-block" style="margin-top:20px;max-width:520px" onclick="saveProfile()">บันทึก</button>`;
}
function saveProfile(){
  const v=id=>{const e=$('#'+id);return e?e.value:''};
  S.profile={field:v('pf'),year:+v('py')||null,gpa:+v('pg')||null,
    obligation:v('po')||'none',hours:+v('ph')||null,budget:v('pb')===''?null:+v('pb')};
  save();
  const cut=CAREERS.filter(c=>!eligibility(c,S.profile).ok).length;
  const m=$('#pmsg');m.style.display='block';
  m.innerHTML=`บันทึกแล้ว · ${cut?`ตัดอาชีพที่ผิดเงื่อนไขออก ${cut} อาชีพ พร้อมเหตุผล`:'ยังไม่มีอาชีพไหนถูกตัดออก'}
    <button class="btn btn-g btn-sm" style="margin-top:10px" onclick="goTo('careers')">ดูอาชีพ</button>`;
  paintChrome('profile');
}

/* ══════════ DATA ══════════ */
function vData(){
  const conf=Object.keys(S.confirmed);
  return `${head('ข้อมูลของฉัน','เก็บในเครื่องคุณเท่านั้น')}
    <p class="body" style="margin-top:14px">ทุกอย่างอยู่ใน localStorage ของเบราว์เซอร์นี้ ไม่มีการส่งออกไปไหน</p>
    <div class="card" style="margin-top:20px">
      <p class="mono up">สิ่งที่เก็บไว้</p>
      <div style="margin-top:12px">
        <p class="body">คำตอบแบบทดสอบ · ${S.answers.length} ข้อ</p>
        <p class="body">ข้อความผลงาน · ${S.raw.length} ตัวอักษร</p>
        <p class="body">ทักษะที่ยืนยันแล้ว · ${conf.length} รายการ</p>
        <p class="body">เป้าหมาย · ${S.target?esc(career(S.target).th):'ยังไม่เลือก'}</p>
        <p class="body">โปรไฟล์ · ${S.profile.field||'ยังไม่ระบุสาขา'}</p>
      </div>
    </div>
    ${conf.length?`<div class="card" style="margin-top:14px">
      <p class="mono up">ทักษะที่ยืนยันแล้ว</p>
      ${conf.map(id=>`<div class="row" style="justify-content:space-between;padding:9px 0;border-top:1px solid var(--line)">
        <span style="font-size:15.5px">${esc((SKILL[id]||{}).th||id)}</span>${lvBar(S.confirmed[id],3,'cv')}</div>`).join('')}
    </div>`:''}
    <button class="btn btn-block" style="margin-top:22px;background:var(--stop)" onclick="wipe()">ลบข้อมูลทั้งหมด</button>
    <p class="mono" style="margin-top:12px">ลบแล้วกู้คืนไม่ได้</p>`;
}
function wipe(){
  if(!confirm('ลบข้อมูลทั้งหมดในเครื่องนี้? กู้คืนไม่ได้'))return;
  reset();goTo('quiz');
}

/* ══ boot ══ */
document.getElementById('brandL').textContent=APP_NAME;
document.getElementById('brandA').textContent=APP_NAME;
document.getElementById('brandM').textContent=APP_NAME;
document.title=APP_NAME;

$$('[data-start]').forEach(b=>b.addEventListener('click',()=>{
  goTo(b.dataset.start||(S.target?'roadmap':'quiz'));
}));
$$('.nav[data-r],.botnav button[data-r]').forEach(b=>b.addEventListener('click',()=>goTo(b.dataset.r)));
$('#brandA').addEventListener('click',()=>{location.hash='';});
$('#brandM').addEventListener('click',()=>{location.hash='';});

/* marquee — build once, then duplicate the set so the loop is seamless */
(function(){
  const track=document.getElementById('track'); if(!track)return;
  const SET=[
    ["img/students-lab.jpg","นักศึกษานั่งทำงานร่วมกัน","ม.ต้น → มหาวิทยาลัย"],
    ["img/d-survey.jpg","กล้องสำรวจที่หน้างาน","7 สาขาวิศวะ"],
    ["img/c-mfg.jpg","ช่างทำงานกับเครื่องจักร","8 อาชีพปลายทาง"],
    ["img/d-crane.jpg","เครนที่ไซต์ก่อสร้าง","73 ทักษะ"],
    ["img/c-robot.jpg","เครื่องมือวัดอิเล็กทรอนิกส์","105 เส้นเชื่อม"],
    ["img/writing-book.jpg","กำลังเขียนโน้ตในสมุด","O*NET 29.1"],
    ["img/c-struct.jpg","วิศวกรที่หน้างานก่อสร้าง","เงื่อนไขทุนกรองจริง"],
    ["img/team-laptop.jpg","ทีมทำงานหน้าแล็ปท็อป","ยืนยันเองทุกทักษะ"]
  ];
  const cell=(src,alt,cap,dup)=>
    `<div class="ph duo"${dup?' aria-hidden="true"':''}>`+
    `<img src="${src}" alt="${dup?'':alt}" loading="lazy" draggable="false">`+
    `<span class="ph-cap">${cap}</span></div>`;
  track.innerHTML = SET.map(s=>cell(s[0],s[1],s[2],false)).join('')
                  + SET.map(s=>cell(s[0],s[1],s[2],true)).join('');
})();

const io=new IntersectionObserver(es=>{es.forEach(en=>{
  if(!en.isIntersecting)return;
  en.target.classList.add('seen');
  en.target.querySelectorAll('.bar i').forEach(b=>b.style.width=b.dataset.w+'%');
  io.unobserve(en.target);
});},{threshold:.18});
$$('.rv').forEach(el=>io.observe(el));
addEventListener('scroll',()=>{const n=$('#lnav');if(n)n.classList.toggle('stuck',scrollY>10)},{passive:true});

render();
