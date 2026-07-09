(function(){
  var API='http://localhost:8000/api/admin/quiz/bookmarklet-import';
  var ADMIN_KEY='demo';

  var SEED_TITLES=[
    'BIOS Quiz','CPU Quiz','Cabling Quiz','Cloud Computing Concepts Quiz',
    'Common Networking Hardware Quiz','Connector Quiz','Core PC Hardware Troubleshooting Quiz',
    'Display Devices Quiz','Display Devices Troubleshooting Quiz','IP Addressing Quiz',
    'Internet Connection Types Quiz','Mobile Device Accessories Quiz',
    'Mobile Device Application Support Quiz','Mobile Device Connection Methods Quiz',
    'Mobile Device Hardware Servicing Quiz','Mobile Device Network Connectivity Quiz',
    'Mobile Devices Troubleshooting Quiz','Motherboard Quiz','Multifunction Devices Quiz',
    'Network Configuration Concepts Quiz','Network Protocols Quiz','Network Services Quiz',
    'Network Troubleshooting Quiz','Network Types Quiz','Networking Tools Quiz',
    'Power Supply Quiz','Printer Quiz','Printer Troubleshooting Quiz','RAM Quiz',
    'Storage Devices Quiz','Storage and RAID Troubleshooting Quiz','TCP & UDP Ports Quiz',
    'Virtualization Concepts Quiz','Wireless Networking Technologies Quiz'
  ];

  function normKey(s){
    return s.toLowerCase().replace(/\\band\\b/g,'').replace(/[^a-z0-9]/g,'');
  }
  var seedMap={};
  SEED_TITLES.forEach(function(t){seedMap[normKey(t)]=t;});

  function titleFromUrl(url){
    var slug=url.replace(/.*\\//,'').replace(/[?#].*/,'');
    var quizPart=slug.replace(/^.*?-exam-/,'');
    var ACRONYMS={pc:'PC',ip:'IP',bios:'BIOS',cpu:'CPU',ram:'RAM',tcp:'TCP',
                  udp:'UDP',dns:'DNS',dhcp:'DHCP',raid:'RAID',vpn:'VPN',vlan:'VLAN'};
    var words=quizPart.split('-').map(function(w){
      if(ACRONYMS[w]) return ACRONYMS[w];
      return w.charAt(0).toUpperCase()+w.slice(1);
    });
    var raw=words.join(' ');
    var fromSeed=seedMap[normKey(raw)];
    if(fromSeed) return fromSeed;
    var rawAmp=raw.replace(/ And /g,' & ');
    fromSeed=seedMap[normKey(rawAmp)];
    if(fromSeed) return fromSeed;
    var t=document.title.replace(/[|].*$/,'').replace(/-\\s*ExamCompass.*/i,'').replace(/^.*?\\bExam\\b\\s*[-:]?\\s*/i,'').trim();
    return(t&&t.length>4)?t:raw;
  }

  function showBanner(msg,state){
    var el=document.getElementById('nexus-banner');
    if(!el){
      el=document.createElement('div');
      el.id='nexus-banner';
      el.style.cssText='position:fixed;top:0;left:0;right:0;z-index:999999;padding:14px 20px;font-family:sans-serif;font-size:14px;font-weight:600;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,0.3);';
      document.body.appendChild(el);
    }
    el.style.background=state==='error'?'#dc2626':state==='done'?'#16a34a':'#1d4ed8';
    el.style.color='white';
    el.innerText=msg;
    if(state==='done'||state==='error') setTimeout(function(){if(el&&el.parentNode)el.parentNode.removeChild(el);},8000);
  }

  function sleep(ms){return new Promise(function(r){setTimeout(r,ms);});}

  function getPageInfo(){
    var m=document.body.innerText.match(/Page[:\\s]+(\\d+)\\s*of\\s*(\\d+)/i);
    return m?{current:parseInt(m[1]),total:parseInt(m[2]),found:true}:{current:1,total:1,found:false};
  }

  function isResultsPage(){
    var text=document.body.innerText;
    return !text.match(/Page[:\\s]+\\d+\\s*of\\s*\\d+/i)&&
           (text.includes('Missed')||text.match(/Your Score|Results|you (got|scored)|Quiz Complete/i));
  }

  function parseQuestionPage(){
    var inputs=document.querySelectorAll('input[type=checkbox],input[type=radio]');
    if(!inputs.length) return null;
    var questionText='';
    var node=inputs[0];
    for(var up=0;up<8;up++){
      node=node.parentElement;
      if(!node) break;
      var kids=Array.from(node.children);
      for(var k=0;k<kids.length;k++){
        var kid=kids[k];
        if(kid.querySelector('input,label')) continue;
        var t=(kid.innerText||'').trim();
        if(t.length>15&&t.length<800&&
           !t.match(/^(Page\\s*\\d|Continue|Next|Previous|Finish|ExamCompass|CompTIA|Discount|Copyright|Select your answer|Please)/i)){
          questionText=t.replace(/^[\\u25B6\\u25BA>\\-]\\s*/,'').trim();
          break;
        }
      }
      if(questionText) break;
    }
    if(!questionText){
      var allP=document.querySelectorAll('p,h3,h4,h5');
      for(var j=0;j<allP.length;j++){
        var pt=(allP[j].innerText||'').trim();
        if(pt.length>20&&pt.length<800&&!pt.match(/ExamCompass|Practice Test|Discount|Page:|Copyright|CompTIA A\\+/i)){
          questionText=pt.replace(/^[>\\u25B6]\\s*/,'').trim();
          break;
        }
      }
    }
    if(!questionText) return null;
    var options=[];
    inputs.forEach(function(inp){
      var lbl=document.querySelector('label[for="'+inp.id+'"]')||inp.closest('label')||inp.parentElement;
      var text='';
      if(lbl){
        var clone=lbl.cloneNode(true);
        clone.querySelectorAll('input,svg,img').forEach(function(x){x.remove();});
        text=(clone.innerText||clone.textContent||'').trim();
      }
      text=text.replace(/^[A-Ea-e][.)\\s]+/,'').replace(/^[\\u2713\\u2717\\u2610\\u2611\\u2714]\\s*/g,'').trim();
      if(text&&text.length>0&&options.indexOf(text)===-1) options.push(text);
    });
    if(options.length<2) return null;
    return{question_text:questionText,options:options};
  }

  function parseResultsPage(collectedQuestions) {
    var correctTexts = [];

    // Exact ExamCompass structure
    var correctChoiceRows = Array.from(
      document.querySelectorAll(
        'li.list-group-item.choice-answer:has(i.fa.fa-check[title*="Correct answer"])'
      )
    );

    // Fallback if :has is unsupported
    if (!correctChoiceRows.length) {
      correctChoiceRows = Array.from(document.querySelectorAll('li.list-group-item.choice-answer'))
        .filter(function (li) {
          return !!li.querySelector('i.fa.fa-check[title*="Correct answer"]');
        });
    }

    console.log('[Nexus] correct choice rows:', correctChoiceRows.length);

    correctChoiceRows.forEach(function (row) {
      var clone = row.cloneNode(true);
      clone.querySelectorAll('i,svg,img,input,button').forEach(function (x) { x.remove(); });

      var cleaned = (clone.innerText || clone.textContent || '')
        .replace(/Missed/gi, '')
        .replace(/Your answer/gi, '')
        .replace(/Correct answer/gi, '')
        .replace(/incorrect or incomplete/gi, '')
        .replace(/\([\s\S]*?\)/g, '')      // remove "( Missed )"
        .replace(/^[A-Ea-e][.)\s]+/, '')   // remove "A. "
        .replace(/\s+/g, ' ')
        .trim();

      if (cleaned.length > 1 && cleaned.length < 300) {
        correctTexts.push(cleaned);
      }
    });

    correctTexts = correctTexts.filter(function (t, i, a) { return a.indexOf(t) === i; });
    console.log('[Nexus] correct texts:', correctTexts.length, correctTexts);

    return collectedQuestions.map(function (q) {
      var opts = q.options;
      var correctIndices = [];

      opts.forEach(function (opt, idx) {
        var optN = opt.toLowerCase().replace(/\s+/g, ' ').trim();

        var matched = correctTexts.some(function (ct) {
          var ctN = ct.toLowerCase().replace(/\s+/g, ' ').trim();
          if (ctN === optN) return true;

          var shorter = optN.length <= ctN.length ? optN : ctN;
          var longer = optN.length <= ctN.length ? ctN : optN;
          if (shorter.length > 4 && longer.includes(shorter)) return true;

          var n = Math.min(30, shorter.length - 2);
          return n > 5 && ctN.substring(0, n) === optN.substring(0, n);
        });

        if (matched) correctIndices.push(idx);
      });

      var allCorrect = correctIndices.map(function (i) { return String.fromCharCode(65 + i); });

      return {
        question_text: q.question_text,
        option_a: opts[0] || '',
        option_b: opts[1] || '',
        option_c: opts[2] || '',
        option_d: opts[3] || '',
        option_e: opts[4] || '',
        correct_answer: allCorrect.length ? allCorrect[0] : 'A',
        all_correct_answers: allCorrect.length ? allCorrect : ['A'],
        explanation: '',
        is_multi: allCorrect.length > 1 || /select all|select 2|select 3/i.test(q.question_text)
      };
    });
  }

  function clickContinue(){
    var candidates=Array.from(document.querySelectorAll('button,input[type=submit],input[type=button],a.btn,a.button'))
      .filter(function(el){return el.offsetParent!==null&&!el.disabled;});
    var exact=candidates.find(function(el){
      var t=(el.innerText||el.value||el.textContent||'').trim().toLowerCase();
      return t==='continue'||t==='next'||t==='next question'||t==='finish';
    });
    if(exact){exact.click();return true;}
    var loose=candidates.find(function(el){
      var t=(el.innerText||el.value||el.textContent||'').trim().toLowerCase();
      return t.includes('continue')||t.includes('next');
    });
    if(loose){loose.click();return true;}
    return false;
  }

  function waitForPageChange(prevPage,timeout){
    return new Promise(function(resolve,reject){
      var start=Date.now();
      var iv=setInterval(function(){
        var info=getPageInfo();
        if(info.current>prevPage||isResultsPage()){clearInterval(iv);setTimeout(resolve,1200);}
        else if(Date.now()-start>(timeout||12000)){clearInterval(iv);reject(new Error('timeout p'+prevPage));}
      },300);
    });
  }

  async function run(){
    var weekNum=prompt('ExamCompass Import\\nWeek number?','1');
    if(weekNum===null) return;
    var pageInfo=getPageInfo();
    if(!pageInfo.found){showBanner('Not on a quiz page. Go to an ExamCompass quiz first.','error');return;}
    var title=titleFromUrl(window.location.href);
    var sourceUrl=window.location.href;
    var collectedQuestions=[];
    var totalPages=pageInfo.total;
    showBanner('Collecting '+totalPages+' questions for "'+title+'" — do not click anything...');
    await sleep(500);
    for(var page=pageInfo.current;page<=totalPages;page++){
      showBanner('Reading question '+page+' of '+totalPages+'...');
      var q=parseQuestionPage();
      if(q){
        var isDup=collectedQuestions.some(function(x){return x.question_text===q.question_text;});
        if(!isDup) collectedQuestions.push(q);
      } else {
        console.log('[Nexus] No question parsed on page',page,'— check DOM structure');
      }
      if(page<totalPages){
        var clicked=clickContinue();
        if(!clicked){showBanner('Could not find Continue button on page '+page+'. Check DevTools console.','error');return;}
        try{await waitForPageChange(page,12000);}catch(e){await sleep(2500);}
      } else {
        var clicked2=clickContinue();
        if(clicked2){
          showBanner('Submitted — waiting for results...');
          await new Promise(function(resolve){
            var start=Date.now();
            var iv=setInterval(function(){
              if(isResultsPage()){clearInterval(iv);setTimeout(resolve,2000);}
              else if(Date.now()-start>20000){clearInterval(iv);resolve();}
            },400);
          });
        }
      }
    }
    if(collectedQuestions.length===0){showBanner('No questions collected. Check DevTools console.','error');return;}
    showBanner('Parsing correct answers...');
    await sleep(800);
    var finalQuestions=[];
    try{
      finalQuestions=parseResultsPage(collectedQuestions);
    }catch(parseErr){
      console.error('[Nexus] parseResultsPage failed',parseErr);
      showBanner('Could not parse results page. Open DevTools console for details.','error');
      return;
    }
    var detected=finalQuestions.filter(function(q){return q.all_correct_answers.length>1||q.correct_answer!=='A';}).length;
    var allDefaultA=finalQuestions.every(function(q){return q.correct_answer==='A'&&q.all_correct_answers.join('')==='A';});
    if(allDefaultA){
      showBanner('Warning: answers defaulted to A. Check DevTools console. Saving anyway...','error');
      await sleep(3000);
    } else {
      showBanner('Detected '+detected+'/'+finalQuestions.length+' answers. Saving as "'+title+'"...');
      await sleep(500);
    }
    try{
      var res=await fetch(API,{
        method:'POST',
        headers:{'Content-Type':'application/json','X-Admin-Key':ADMIN_KEY},
        body:JSON.stringify({title:title,source_url:sourceUrl,week_number:parseInt(weekNum)||1,questions:finalQuestions})
      });
      var data=await res.json();
      if(data.success||(data.data&&data.data.quiz_id)){
        showBanner(
          allDefaultA?'Saved "'+title+'" — open Quiz Editor to fix answers':'✓ Done! "'+title+'" · '+finalQuestions.length+' Qs · '+detected+' answers detected',
          allDefaultA?'error':'done'
        );
      } else {
        showBanner('Server error: '+JSON.stringify(data).slice(0,150),'error');
      }
    }catch(e){
      showBanner('Cannot reach backend ('+API+'): '+e.message,'error');
    }
  }

  run().catch(function(e){showBanner('Fatal: '+e.message,'error');console.error('[Nexus]',e);});
})();