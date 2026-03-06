(function(){
  var API='http://localhost:8000/api/admin/quiz/bookmarklet-import';
  var ADMIN_KEY=(window.NEXUS_ADMIN_KEY||'5e884c93f8e7be2527aaee270169748f035fde89fa09890d1d9b54d12934bc33').trim();

  function banner(msg,state){
    var el=document.getElementById('nexus-banner');
    if(!el){
      el=document.createElement('div');
      el.id='nexus-banner';
      el.style.cssText='position:fixed;top:0;left:0;right:0;z-index:999999;padding:12px 16px;font:600 14px/1.2 sans-serif;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,.3)';
      document.body.appendChild(el);
    }
    el.style.background=state==='error'?'#dc2626':state==='done'?'#16a34a':'#1d4ed8';
    el.style.color='#fff';
    el.innerText=msg;
    if(state==='done'||state==='error') setTimeout(function(){if(el&&el.parentNode)el.parentNode.removeChild(el);},7000);
  }

  function sleep(ms){return new Promise(function(r){setTimeout(r,ms);});}

  function pageInfo(){
    var text=document.body.innerText||'';
    var m=text.match(/(?:Page|Question)[:\s#]*(\d+)\s*(?:of|\/)\s*(\d+)/i);
    if(m) return {current:parseInt(m[1],10),total:parseInt(m[2],10),found:true};
    var hasChoices=document.querySelectorAll('input[type=checkbox],input[type=radio]').length>0;
    return {current:1,total:1,found:hasChoices};
  }

  function isResults(){
    var t=document.body.innerText||'';
    return !/(?:Page|Question)[:\s#]*\d+\s*(?:of|\/)\s*\d+/i.test(t) && (t.includes('Missed')||/Your Score|Results|Quiz Complete/i.test(t));
  }

  function titleFromUrl(){
    var slug=(location.pathname.split('/').filter(Boolean).pop()||'').replace(/[?#].*/,'');
    var q=slug.replace(/^.*?-exam-/,'');
    if(!q) q=(document.title||'').replace(/[|].*$/,'').replace(/-\s*ExamCompass.*/i,'').trim();
    var ac={pc:'PC',ip:'IP',bios:'BIOS',cpu:'CPU',ram:'RAM',tcp:'TCP',udp:'UDP',dns:'DNS',dhcp:'DHCP',raid:'RAID',vpn:'VPN',vlan:'VLAN'};
    var w=q.split('-').filter(Boolean).map(function(x){x=x.toLowerCase();return ac[x]||x.charAt(0).toUpperCase()+x.slice(1);});
    var t=w.join(' ').trim();
    return t&&t.length>4?t:'ExamCompass Import';
  }

  function parseQuestion(){
    var inputs=document.querySelectorAll('input[type=checkbox],input[type=radio]');
    if(!inputs.length) return null;

    var text='';
    var node=inputs[0];
    for(var up=0;up<8;up++){
      node=node&&node.parentElement;
      if(!node) break;
      var kids=Array.from(node.children||[]);
      for(var i=0;i<kids.length;i++){
        var k=kids[i];
        if(k.querySelector&&k.querySelector('input,label')) continue;
        var t=(k.innerText||'').trim();
        if(t.length>15&&t.length<800&&!/^(Page\s*\d|Continue|Next|Previous|Finish|ExamCompass|CompTIA|Discount|Copyright|Select your answer|Please)/i.test(t)){
          text=t.replace(/^[\u25B6\u25BA>\-]\s*/,'').trim();
          break;
        }
      }
      if(text) break;
    }

    if(!text){
      var ps=document.querySelectorAll('p,h3,h4,h5');
      for(var j=0;j<ps.length;j++){
        var pt=(ps[j].innerText||'').trim();
        if(pt.length>20&&pt.length<800&&!/ExamCompass|Practice Test|Discount|Page:|Copyright|CompTIA A\+/i.test(pt)){
          text=pt.replace(/^[>\u25B6]\s*/,'').trim();
          break;
        }
      }
    }
    if(!text) return null;

    var options=[];
    inputs.forEach(function(inp){
      var lbl=document.querySelector('label[for="'+inp.id+'"]')||inp.closest('label')||inp.parentElement;
      var ot='';
      if(lbl){
        var c=lbl.cloneNode(true);
        c.querySelectorAll('input,svg,img').forEach(function(x){x.remove();});
        ot=(c.innerText||c.textContent||'').trim();
      }
      ot=ot.replace(/^[A-Ea-e][.)\s]+/,'').replace(/^[\u2713\u2717\u2610\u2611\u2714]\s*/g,'').trim();
      if(ot&&options.indexOf(ot)===-1) options.push(ot);
    });

    return options.length>=2?{question_text:text,options:options}:null;
  }

  function parseResults(collected){
    function cleanChoiceText(li){
      var c=li.cloneNode(true);
      c.querySelectorAll('i,svg,img,input,button').forEach(function(x){x.remove();});
      return (c.innerText||c.textContent||'')
        .replace(/Missed/gi,'').replace(/Your answer/gi,'').replace(/Correct answer/gi,'')
        .replace(/incorrect or incomplete/gi,'').replace(/\([\s\S]*?\)/g,'')
        .replace(/^[A-Ea-e][.)\s]+/,'').replace(/\s+/g,' ').trim();
    }

    function extractQuestionText(group){
      function cleanQ(t){return (t||'').replace(/^\s*[▶►>\-]\s*/,'').replace(/\s+/g,' ').trim();}
      function validQ(t){
        return t.length>15 && !/CompTIA|ExamCompass|Your answer|incorrect or incomplete|Correct answer|Missed|Discount/i.test(t) && !/^(A|B|C|D|E)[.)\s]/i.test(t);
      }

      var prev=group.previousElementSibling;
      while(prev){
        var pt=cleanQ(prev.innerText||prev.textContent||'');
        if(validQ(pt)) return pt;
        prev=prev.previousElementSibling;
      }

      var container=group.closest('.question-item,.panel,.well,.box,.quiz-result,.gk-article')||group.parentElement||group;
      var headingEl=container.querySelector('h1,h2,h3,h4,.panel-heading,.question-title,.question-text,strong');
      var ht=cleanQ(headingEl&&(headingEl.innerText||headingEl.textContent||'')||'');
      if(validQ(ht)) return ht;

      var clone=container.cloneNode(true);
      clone.querySelectorAll('ul.list-group.quiz-result-question,li.list-group-item.choice-answer,i,svg,img,input,button,.text-error').forEach(function(x){x.remove();});
      var lines=(clone.innerText||clone.textContent||'').split('\n').map(cleanQ).filter(Boolean);
      for(var i=0;i<lines.length;i++){ if(validQ(lines[i])) return lines[i]; }
      return '';
    }

    var groups=Array.from(document.querySelectorAll('ul.list-group.quiz-result-question,.quiz-result-question')).filter(function(g){
      return g.querySelectorAll('li.list-group-item.choice-answer').length>0;
    });

    var parsed=groups.map(function(group,idx){
      var qText=extractQuestionText(group);
      var rows=Array.from(group.querySelectorAll('li.list-group-item.choice-answer'));
      var options=rows.map(cleanChoiceText).filter(function(t){return t.length>0;});

      if((!qText||qText.length<8)&&collected[idx]&&collected[idx].question_text) qText=collected[idx].question_text;
      if(options.length<2&&collected[idx]&&Array.isArray(collected[idx].options)) options=collected[idx].options.slice();

      options=options.filter(function(t,i,a){return a.indexOf(t)===i;});

      var correctTexts=rows.filter(function(li){return !!li.querySelector('i.fa.fa-check[title*="Correct answer"]');})
        .map(cleanChoiceText)
        .filter(function(t){return t.length>0;})
        .filter(function(t,i,a){return a.indexOf(t)===i;});

      var idxs=[];
      options.forEach(function(opt,i){
        var on=opt.toLowerCase().replace(/\s+/g,' ').trim();
        var hit=correctTexts.some(function(ct){return ct.toLowerCase().replace(/\s+/g,' ').trim()===on;});
        if(hit) idxs.push(i);
      });

      var all=idxs.map(function(i){return String.fromCharCode(65+i);});
      if(all.length>1&&!/select all|select 2|select 3/i.test(qText)) all=[all[0]];

      return {
        question_text:qText,
        option_a:options[0]||'', option_b:options[1]||'', option_c:options[2]||'', option_d:options[3]||'', option_e:options[4]||'',
        correct_answer:all.length?all[0]:'A',
        all_correct_answers:all.length?all:['A'],
        explanation:'',
        is_multi:all.length>1||/select all|select 2|select 3/i.test(qText),
      };
    }).filter(function(q){return (q.question_text&&q.question_text.length>0)||q.option_a;});

    if(parsed.length){
      if(collected.length>parsed.length){
        for(var i=parsed.length;i<collected.length;i++){
          var opts=collected[i].options||[];
          parsed.push({
            question_text:collected[i].question_text||('Question '+(i+1)),
            option_a:opts[0]||'', option_b:opts[1]||'', option_c:opts[2]||'', option_d:opts[3]||'', option_e:opts[4]||'',
            correct_answer:'A', all_correct_answers:['A'], explanation:'',
            is_multi:/select all|select 2|select 3/i.test(collected[i].question_text||''),
          });
        }
      }
      return parsed;
    }

    return collected.map(function(q){
      var opts=q.options||[];
      return {question_text:q.question_text,option_a:opts[0]||'',option_b:opts[1]||'',option_c:opts[2]||'',option_d:opts[3]||'',option_e:opts[4]||'',correct_answer:'A',all_correct_answers:['A'],explanation:'',is_multi:/select all|select 2|select 3/i.test(q.question_text)};
    });
  }

  function clickNext(){
    var els=Array.from(document.querySelectorAll('button,input[type=submit],input[type=button],a.btn,a.button')).filter(function(e){return e.offsetParent!==null&&!e.disabled;});
    var e=els.find(function(x){var t=(x.innerText||x.value||x.textContent||'').trim().toLowerCase();return t==='continue'||t==='next'||t==='next question'||t==='finish';});
    if(!e) e=els.find(function(x){var t=(x.innerText||x.value||x.textContent||'').trim().toLowerCase();return t.includes('continue')||t.includes('next');});
    if(e){e.click();return true;}
    return false;
  }

  function waitPage(prev,to){
    return new Promise(function(resolve,reject){
      var st=Date.now();
      var iv=setInterval(function(){
        var p=pageInfo();
        if(p.current>prev||isResults()){clearInterval(iv);setTimeout(resolve,1200);}
        else if(Date.now()-st>(to||12000)){clearInterval(iv);reject(new Error('timeout '+prev));}
      },300);
    });
  }

  async function run(){
    if(!ADMIN_KEY){banner('Missing admin key (VITE_ADMIN_KEY).','error');return;}

    var weekNum=prompt('ExamCompass Import\nWeek number?','1');
    if(weekNum===null) return;

    var pi=pageInfo();
    if(!pi.found){banner('Not on an ExamCompass quiz page.','error');return;}

    var title=titleFromUrl(),sourceUrl=location.href,collected=[],total=pi.total;
    banner('Collecting '+total+' questions for "'+title+'"...');
    await sleep(400);

    for(var page=pi.current;page<=total;page++){
      banner('Reading question '+page+' of '+total+'...');
      var q=parseQuestion();
      if(q&&!collected.some(function(x){return x.question_text===q.question_text;})) collected.push(q);

      if(page<total){
        if(!clickNext()){banner('Could not find Continue/Next on page '+page,'error');return;}
        try{await waitPage(page,12000);}catch(_e){await sleep(2500);}
      }else if(clickNext()){
        banner('Submitted - waiting for results...');
        await new Promise(function(resolve){
          var st=Date.now();
          var iv=setInterval(function(){
            if(isResults()){clearInterval(iv);setTimeout(resolve,1800);} else if(Date.now()-st>20000){clearInterval(iv);resolve();}
          },400);
        });
      }
    }

    if(!collected.length){banner('No questions collected.','error');return;}

    banner('Parsing correct answers...');
    await sleep(600);

    var finalQuestions;
    try{finalQuestions=parseResults(collected);}catch(e){console.error('[Nexus] parse failed',e);banner('Could not parse results page.','error');return;}

    var detected=finalQuestions.filter(function(q){return q.all_correct_answers.length>1||q.correct_answer!=='A';}).length;
    var allA=finalQuestions.every(function(q){return q.correct_answer==='A'&&q.all_correct_answers.join('')==='A';});

    try{
      var res=await fetch(API,{method:'POST',headers:{'Content-Type':'application/json','X-Admin-Key':ADMIN_KEY},body:JSON.stringify({title:title,source_url:sourceUrl,week_number:parseInt(weekNum,10)||1,questions:finalQuestions})});
      var data=await res.json();
      if(data.success||(data.data&&data.data.quiz_id)){
        banner(allA?'Saved "'+title+'" (answers need review)':'Done! "'+title+'" - '+finalQuestions.length+' questions, '+detected+' answers detected',allA?'error':'done');
      } else {
        banner('Server error: '+JSON.stringify(data).slice(0,140),'error');
      }
    }catch(e){
      banner('Cannot reach backend: '+e.message,'error');
    }
  }

  run().catch(function(e){banner('Fatal: '+e.message,'error');console.error('[Nexus]',e);});
})();
