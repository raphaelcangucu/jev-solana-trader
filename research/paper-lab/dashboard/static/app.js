
const $ = s => document.querySelector(s);
let eqChart;
async function j(url, opts){
  const r = await fetch(url, Object.assign({headers:{'Accept':'application/json'}}, opts||{}));
  if(!r.ok) throw new Error(await r.text());
  return r.json();
}
function fmt(n, d=4){ return (n==null||Number.isNaN(n))?'—':Number(n).toFixed(d); }
async function refresh(){
  try{
    const [health, ov, eq, dec, tr, memes, params, chg, rev, rules] = await Promise.all([
      j('/api/health'), j('/api/overview'), j('/api/equity'), j('/api/decisions?limit=50'),
      j('/api/trades?limit=50'), j('/api/memes'), j('/api/params'), j('/api/param_changes?limit=80'), j('/api/reviews'), j('/api/rules')
    ]);
    $('#hdrMeta').textContent = `BRT ${health.ts_brt||''} · heartbeat ${fmt(health.heartbeat_age_s,1)}s · ciclos ${ov.cycles} · erros ${ov.errors} · wall ${fmt(ov.cycle_wall_ms,0)}ms`;
    $('#hdrPrice').textContent = `SOL $${fmt(ov.price_usd,3)} (${ov.price_source||'?'})`;
    $('#procs').innerHTML = (health.processes||[]).map(p =>
      `<div class="pill"><span class="mut">${p.name}</span><b class="${p.running?'ok':'bad'}">${p.running?'ON':'OFF'}</b><span class="mut">pid ${p.pid||'—'}</span></div>`
    ).join('');
    const jev = ov.jev || {};
    $('#jevStatus').textContent = `Jev hospedado: ${jev.status||'?'} · env ${jev.api_key_env||'JEV_API_KEY'} · live_trading=false`;

    $('#ports').innerHTML = Object.entries(ov.portfolios||{}).map(([name,p]) => `
      <div class="pill">
        <span class="mut">${name} · ${p.model||'?'}</span>
        <b>$${fmt(p.equity_usd)}</b>
        <div class="mut">PnL vs inicio ${fmt(p.pnl_vs_start)} · vs B&H ${fmt(p.pnl_vs_bh)}</div>
        <div class="mut">SOL exp ${fmt(p.sol_exposure_pct,1)}% · trades ${p.trades??0}</div>
        <div class="mut">ultimo: ${p.last_chosen}->${p.last_final} conf=${fmt(p.last_conf,3)} · ${(p.gate_reasons||[]).join(',')||'—'}</div>
      </div>`).join('');

    const colors = {baseline:'#60a5fa',relaxed:'#34d399',v2:'#f472b6',laya_baseline:'#a78bfa',laya_relaxed:'#c4b5fd',poorjev_baseline:'#fbbf24',poorjev_relaxed:'#fde68a'};
    const datasets = [];
    let bhDone=false, usdtDone=false;
    for(const [name, rows] of Object.entries(eq||{})){
      if(!rows.length) continue;
      datasets.push({label:name, data: rows.map(r=>({x:r.ts*1000, y:r.equity})), borderColor: colors[name]||'#94a3b8', tension:.2, pointRadius:0, borderWidth:1.5});
      if(!bhDone && rows[0].bh_equity!=null){
        datasets.push({label:'buy&hold', data: rows.map(r=>({x:r.ts*1000, y:r.bh_equity})), borderColor:'#64748b', borderDash:[4,4], pointRadius:0, borderWidth:1});
        bhDone=true;
      }
      if(!usdtDone && rows[0].all_usdt_equity!=null){
        datasets.push({label:'100% USDT', data: rows.map(r=>({x:r.ts*1000, y:r.all_usdt_equity})), borderColor:'#475569', borderDash:[2,3], pointRadius:0, borderWidth:1});
        usdtDone=true;
      }
    }
    if(eqChart) eqChart.destroy();
    eqChart = new Chart($('#eqChart'), {
      type:'line', data:{datasets},
      options:{responsive:true, maintainAspectRatio:false,
        scales:{x:{type:'linear', ticks:{callback:v=>new Date(v).toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'})}},
                y:{ticks:{callback:v=>'$'+Number(v).toFixed(2)}}},
        plugins:{legend:{labels:{color:'#cbd5e1', boxWidth:12, font:{size:10}}}}}
    });

    
    // Rules / hybrids panel
    if ($('#rulesMeta')) {
      const ind=((rules.indicators)||{}).sol||{};
      $('#rulesMeta').textContent = `inicio ${rules.started_brt||'—'} · ciclos ${rules.cycles||0} · erros ${rules.errors||0} · SOL 1h close=${fmt(ind.close_1h,3)} EMA12=${fmt(ind.ema12,3)} EMA26=${fmt(ind.ema26,3)} RSI=${fmt(ind.rsi,2)} bull=${ind.regime_bull}`;
      const rp=rules.portfolios||{};
      // also hybrid from overview
      const allRuleNames=['grid_sol_2pct','rsi_sol_1h','hybrid_von_relaxed_cap2'];
      $('#rulesPorts').innerHTML = allRuleNames.map(name=>{
        const p=rp[name]||(ov.portfolios||{})[name]||{};
        const ind2=p.indicators||{};
        return `<div class="pill"><span class="mut">${name} · ${p.strategy||p.model||'rule'}</span>
          <b>$${fmt(p.equity_usd)}</b>
          <div class="mut">vs B&H ${fmt(p.pnl_vs_bh)} · trades ${p.trades??0} · pos ${p.position||'—'}</div>
          <div class="mut">sinal=${p.last_signal||p.last_final||'—'} · ${(p.gate_reasons||[]).join(',')||'—'}</div>
          <div class="mut">${name.includes('grid')?('grid '+JSON.stringify(ind2.grid||ind2)):(name.includes('rsi')?('rsi='+fmt((ind2.rsi!=null?ind2.rsi:ind.rsi),2)):'regime bull='+((ov.portfolios||{}).hybrid_von_relaxed_cap2||{}).sol_regime_bull)}</div>
        </div>`;
      }).join('');
      const ms=rules.meme_portfolios||{};
      const syms=Object.keys(ms).length?Object.keys(ms):(memes.tokens||[]).map(t=>t.symbol);
      $('#rulesMemeBody').innerHTML = syms.map(sym=>{
        const e=ms[sym]||{};
        const tok=(memes.tokens||[]).find(t=>t.symbol===sym)||{};
        const hy=((tok.models||{}).hybrid_poorjev_regime)||e.hybrid||{};
        const reg=e.regime||((tok.models||{}).rule_regime)||{};
        const don=e.donch||((tok.models||{}).rule_donch)||{};
        const cell=x=>`${fmt(x.equity_usd||x.baseline_equity,2)}/${x.trades||x.baseline_trades||0} ${x.last_signal||x.position||''}`;
        return `<tr><td>${sym}</td><td>${cell(reg)}</td><td>${cell(don)}</td><td>${cell(hy)}</td></tr>`;
      }).join('') || '<tr><td colspan=4 class="mut">aguardando rules_bot</td></tr>';
      const bots=params.bots||{};
      if ($('#btnRulesPause')) {
        $('#btnRulesPause').textContent = bots.rules_paused ? 'Retomar Rules' : 'Pausar Rules';
        $('#btnRulesPause').onclick = async ()=>{ await j('/api/bots/rules/pause',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({paused:!bots.rules_paused})}); refresh(); };
      }
    }

$('#decBody').innerHTML = (dec||[]).map(r=>`<tr>
      <td>${(r.ts_brt||'').slice(11,19)}</td><td>${r.portfolio}</td><td>${r.model||''}</td>
      <td>${(r.state||'').split(' ').slice(0,6).join(' ')}</td>
      <td>${r.chosen_action}</td><td>${fmt(r.confidence,3)}</td><td>${fmt(r.skip_noul,3)}</td><td>${r.final_action}</td>
    </tr>`).join('');
    $('#trBody').innerHTML = (tr||[]).map(r=>`<tr>
      <td>${(r.ts_brt||'').slice(11,19)}</td><td>${r.portfolio}</td><td>${r.side}</td>
      <td>${fmt(r.price_mark,3)}</td><td>${r.fill_mode||'—'}</td></tr>`).join('');
    if ($('#memeMeta')) {
      $('#memeMeta').textContent = `modelos=${(memes.meme_models_enabled||[]).join(',')||'von'} wall=${fmt(memes.cycle_wall_ms,0)}ms lat=${JSON.stringify(memes.extra_latencies_ms||{})}`;
    }
    const cell = (m) => {
      if(!m) return '—';
      return `${fmt(m.baseline_equity,2)}/${m.baseline_trades||0} · ${fmt(m.relaxed_equity,2)}/${m.relaxed_trades||0}`;
    };
    $('#memeBody').innerHTML = (memes.tokens||[]).map(t=>{
      const ms = t.models || {};
      return `<tr>
      <td>${t.symbol}</td>
      <td>${t.price}</td><td>${t.price_source||''}</td>
      <td>${cell(ms.von)|| (fmt(t.baseline_equity,2)+'/'+(t.baseline_trades||0)+' · '+fmt(t.relaxed_equity,2)+'/'+(t.relaxed_trades||0))}</td>
      <td>${cell(ms.laya)}</td>
      <td>${cell(ms.poorjev)}</td></tr>`;
    }).join('');

    const bots = params.bots||{};
    $('#btnSolPause').textContent = bots.sol_paused ? 'Retomar SOL' : 'Pausar SOL';
    $('#btnMemePause').textContent = bots.meme_paused ? 'Retomar Meme' : 'Pausar Meme';
    $('#btnSolPause').onclick = async ()=>{ await j('/api/bots/sol/pause',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({paused:!bots.sol_paused})}); refresh(); };
    $('#btnMemePause').onclick = async ()=>{ await j('/api/bots/meme/pause',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({paused:!bots.meme_paused})}); refresh(); };

    const fields=['min_confidence','min_prob_margin','max_skip_noul','buy_fraction_usdt','cooldown_seconds','max_trades_per_hour'];
    $('#controls').innerHTML = Object.entries(params.portfolios||{}).map(([name,p]) => {
      const warn = p.is_baseline_control ? `<div class="warnbox">Baseline = controle fiel ao artigo. Editar com cuidado.</div>` : '';
      return `<div class="pill" data-port="${name}">
        <b>${name}</b> ${p.paused?'<span class="bad">pausado</span>':''}${warn}
        ${fields.map(f=>`<label>${f}<input type="number" step="any" data-f="${f}" value="${p[f]??''}"/></label>`).join('')}
        <div class="row" style="margin-top:8px">
          <button data-act="save">Salvar</button>
          <button class="secondary" data-act="pause">${p.paused?'Retomar':'Pausar'}</button>
          <button class="warn" data-act="restore">Restaurar padroes</button>
        </div></div>`;
    }).join('');
    $('#controls').querySelectorAll('.pill').forEach(el=>{
      const name = el.dataset.port;
      el.querySelector('[data-act=save]').onclick = async ()=>{
        const body={};
        el.querySelectorAll('input[data-f]').forEach(i=> body[i.dataset.f]=i.value);
        const res = await j('/api/params/'+name,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
        if(res.warning) alert(res.warning);
        refresh();
      };
      el.querySelector('[data-act=pause]').onclick = async ()=>{
        await j('/api/params/'+name,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({paused: !((params.portfolios[name]||{}).paused)})});
        refresh();
      };
      el.querySelector('[data-act=restore]').onclick = async ()=>{
        if(!confirm('Restaurar padroes de '+name+'?')) return;
        await j('/api/params/'+name+'/restore',{method:'POST'});
        refresh();
      };
    });

    $('#models').innerHTML = Object.entries(params.models||{}).map(([mid,m])=>`
      <div class="row" style="align-items:center;margin:6px 0">
        <div class="pill" style="flex:2"><b>${mid}</b><span class="mut">${m.label||''} · ${m.kind||''} · memes=${m.memes_enabled?'on':'off'}</span></div>
        <button class="${m.enabled?'danger':'secondary'}" data-m="${mid}" data-act="sol">${m.enabled?'Desabilitar SOL':'Habilitar SOL'}</button>
        <button class="secondary" data-m="${mid}" data-act="meme">${m.memes_enabled?'Memes OFF':'Memes ON'}</button>
      </div>`).join('');
    $('#models').querySelectorAll('button[data-m]').forEach(btn=>{
      btn.onclick = async ()=>{
        const mid=btn.dataset.m;
        const act=btn.dataset.act;
        const cur=params.models[mid]||{};
        const body = act==='meme' ? {memes_enabled: !cur.memes_enabled} : {enabled: !cur.enabled};
        const res = await j('/api/models/'+mid+'/enable',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
        if(res.note) alert(res.note);
        refresh();
      };
    });

    $('#reviews').innerHTML = `<div class="mut">review_done=${rev.review_done}</div>
      <ul>${(rev.files||[]).map(f=>`<li><a style="color:#93c5fd" href="/api/file?path=reviews/${encodeURIComponent(f)}" target="_blank">${f}</a></li>`).join('')}</ul>
      <ul>${(rev.criteria||[]).map(f=>`<li><a style="color:#93c5fd" href="/api/file?path=${encodeURIComponent(f)}" target="_blank">${f}</a></li>`).join('')}</ul>`;

    $('#chgBody').innerHTML = (chg||[]).map(r=>`<tr>
      <td>${(r.ts_brt||'').slice(0,19)}</td><td>${r.portfolio}</td><td>${r.field}</td><td>${r.old}</td><td>${r.new}</td>
    </tr>`).join('') || '<tr><td colspan=5 class="mut">nenhuma alteracao</td></tr>';
  }catch(e){
    console.error(e);
    $('#hdrMeta').textContent = 'erro: '+e.message;
  }
}
refresh();
setInterval(refresh, 12000);

// ---- Laboratório (hipóteses, forks, vereditos) ----
async function refreshLab(){
  try{
    const lab = await j('/api/lab');
    const st = lab.status||{}; const ng = lab.nightly||{};
    $('#labMeta').textContent = `lab: ciclos ${st.cycles??'—'} · erros ${st.errors??'—'} · decisões-fonte processadas ${st.processed_source_decisions??'—'} · vereditos atualizados ${lab.verdicts_ts_brt||'—'} · próxima revisão noturna ${ng.next_run_brt||'—'}`;
    const vcls = v => v==='vencedora'?'ok':(v==='perdedora'?'bad':'mut');
    $('#labBody').innerHTML = (lab.hypotheses||[]).sort((a,b)=>(a.name>b.name?1:-1)).map(h=>`<tr>
      <td>${h.hyp||(h.parent?'fork':'')}</td><td>${h.name}${h.parent?` <span class="mut">(fork de ${h.parent})</span>`:''}</td>
      <td class="mut">${h.label||''}${h.open_order?' · ordem limite aberta':''}</td>
      <td>$${fmt(h.equity_usd,3)}</td><td>${fmt(h.pnl,3)}</td><td>${fmt(h.vs_bh,3)}</td><td>${h.trades||0}</td><td>${fmt(h.exposure_pct,0)}%</td>
      <td><b class="${vcls(h.verdict)}">${h.verdict}</b> <span class="mut">${h.progress||''}</span></td>
      <td><button class="secondary" data-p="${h.name}" data-paused="${h.paused?1:0}">${h.paused?'Ligar':'Desligar'}</button></td></tr>`).join('') || '<tr><td colspan=10 class="mut">aguardando lab_bot</td></tr>';
    document.querySelectorAll('#labBody button[data-p]').forEach(b=>b.onclick=async()=>{
      await j('/api/params/'+b.dataset.p,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({paused:b.dataset.paused!=='1'})}); refreshLab(); });
    $('#linBody').innerHTML = (lab.lineages||[]).filter(l=>(l.members||[]).length>1).map(l=>`<tr><td>${l.lineage}</td><td>${
      l.members.map(m=>`<span class="pill"><b>${m.name}</b> $${fmt(m.equity_usd,2)} · PnL ${fmt(m.pnl,3)} · ${m.trades||0} tr · <span class="${vcls(m.verdict)}">${m.verdict}</span>${m.is_lead?' · <i>lead fork (base p/ tuning, não é veredito)</i>':''}</span>`).join(' → ')
      }</td></tr>`).join('') || '<tr><td colspan=2 class="mut">Nenhum fork ainda (tuning só com dados suficientes).</td></tr>';
    $('#verBody').innerHTML = (lab.original_verdicts||[]).sort((a,b)=>(a.name>b.name?1:-1)).map(v=>`<tr><td>${v.name}</td><td><b class="${vcls(v.verdict)}">${v.verdict}</b></td><td class="mut">${v.progress||''}</td><td class="mut">${v.reason||''}</td></tr>`).join('') || '<tr><td colspan=4 class="mut">aguardando job noturno (atualiza a cada 30 min)</td></tr>';
    if ($('#btnLabPause')) {
      $('#btnLabPause').textContent = lab.lab_paused ? 'Retomar Lab' : 'Pausar Lab';
      $('#btnLabPause').onclick = async ()=>{ await j('/api/bots/lab/pause',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({paused:!lab.lab_paused})}); refreshLab(); };
    }
  }catch(e){ if($('#labMeta')) $('#labMeta').textContent = 'erro lab: '+e; }
}
refreshLab(); setInterval(refreshLab, 20000);
