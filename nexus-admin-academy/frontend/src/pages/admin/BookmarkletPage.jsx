import { useState } from "react";
import { CheckCircle, Copy } from "lucide-react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const ADMIN_KEY = import.meta.env.VITE_ADMIN_KEY || "";

export default function BookmarkletPage() {
  const [copied, setCopied] = useState(false);

  const bookmarkletCode = `javascript:(function(){
  var API='${API_URL}/api/admin/quiz/bookmarklet-import';
  var ADMIN_KEY='${ADMIN_KEY}';

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
    if(state==='done'||state==='error') setTimeout(function(){if(el.parentNode)el.parentNode.removeChild(el);},6000);
  }

  function sleep(ms){return new Promise(function(r){setTimeout(r,ms);});}

  function getPageInfo(){
    var m=document.body.innerText.match(/Page[:\\s]+(\\d+)\\s*of\\s*(\\d+)/i);
    return m?{current:parseInt(m[1]),total:parseInt(m[2]),found:true}:{current:1,total:1,found:false};
  }

  function isResultsPage(){
    return !document.body.innerText.match(/Page:\\s*\\d+\\s*of\\s*\\d+/i)&&
           (document.body.innerText.includes('Missed')||!!document.body.innerText.match(/score|correct|incorrect|complete/i));
  }

  function parseQuestionPage(){
    var inputs=document.querySelectorAll('input[type=checkbox],input[type=radio]');
    if(!inputs.length) return null;
    var questionText='';
    var container=inputs[0].closest('table,form,[class*=question],fieldset,.panel,.card')||inputs[0].closest('div');
    if(container){
      var candidates=container.querySelectorAll('p,h3,h4,h5,strong,span,td,div');
      for(var i=0;i<candidates.length;i++){
        if(candidates[i].querySelector('input')) continue;
        var t=(candidates[i].innerText||'').trim();
        if(t.length>15&&t.length<800&&!t.match(/^(Page|Continue|Next|ExamCompass|CompTIA Exam|Discount|Support|Copyright)/i)){
          questionText=t.replace(/^[>\\u25B6\\u25BA\\u25B8]\\s*/,'').trim();
          break;
        }
      }
    }
    if(!questionText){
      var paras=document.querySelectorAll('p');
      for(var j=0;j<paras.length;j++){
        var pt=(paras[j].innerText||'').trim();
        if(pt.length>15&&!pt.match(/Page:|ExamCompass|Practice Test|Discount/i)){
          questionText=pt.replace(/^[>]\\s*/,'').trim();
          break;
        }
      }
    }
    if(!questionText) return null;

    var options=[];
    inputs.forEach(function(inp){
      var lbl=(inp.id&&document.querySelector('label[for="'+inp.id+'"]'))||inp.closest('label')||inp.parentElement;
      var text=((lbl?lbl.innerText||lbl.textContent:'')||'').trim()
        .replace(/^[A-Ea-e][.)\\s]+/,'')
        .replace(/^[\\u2713\\u2717\\u2610\\u2611\\u2714]\\s*/g,'')
        .trim();
      if(text&&text.length>0&&options.indexOf(text)===-1) options.push(text);
    });
    if(options.length<2) return null;
    return {question_text:questionText,options:options};
  }

  function parseResultsPage(collectedQuestions){
    var correctOptionTexts=[];

    var rows=Array.from(document.querySelectorAll('tr,li,[class*="row"],[class*="item"],[class*="option"],[class*="answer"],[class*="choice"]'));
    document.querySelectorAll('table,ul,ol,[class*="question"],[class*="answers"]').forEach(function(c){
      c.childNodes.forEach(function(child){if(child.nodeType===1) rows.push(child);});
    });

    rows.forEach(function(row){
      var rowHTML=row.innerHTML||'';
      var rowText=row.innerText||'';
      var hasMissed=rowText.includes('Missed');
      var hasThumbsDown=rowHTML.includes('thumb')||!!row.querySelector('[class*="thumb"],[class*="dislike"],[alt*="thumb"]');
      var hasCheckmark=!!row.querySelector('[class*="correct"],[class*="check"]:not(input),svg[class*="check"]')||
                       rowHTML.includes('✓')||rowHTML.includes('✔')||
                       rowHTML.includes('\u2713')||rowHTML.includes('\u2714');
      if(!hasMissed&&!hasThumbsDown&&!hasCheckmark) return;

      var clone=row.cloneNode(true);
      clone.querySelectorAll('input,svg,img,[class*="icon"],[class*="thumb"],[class*="check"]:not(label)').forEach(function(el){el.remove();});
      clone.querySelectorAll('*').forEach(function(el){
        var t=(el.innerText||el.textContent||'').trim();
        if(t.match(/^\\(?\\s*Missed\\s*\\)?$/i)||t.match(/^\\(.*Missed.*\\)$/i)) el.remove();
      });
      var cleaned=(clone.innerText||clone.textContent||'')
        .replace(/\\(.*?Missed.*?\\)/gi,'').replace(/Missed/gi,'')
        .replace(/[\\u2713\\u2714\\u2717]/g,'').replace(/^[A-Ea-e][.)\\s]+/,'')
        .replace(/\\s+/g,' ').trim();
      if(cleaned&&cleaned.length>3&&!cleaned.match(/^(Your answer|incorrect|complete|Page|CompTIA|ExamCompass)/i))
        correctOptionTexts.push(cleaned);
    });

    correctOptionTexts=correctOptionTexts.filter(function(t,i,a){return a.indexOf(t)===i;});

    var finalQuestions = collectedQuestions.map(function(q){
      var opts=q.options;
      var correctIndices=[];
      opts.forEach(function(opt,idx){
        var optClean=opt.toLowerCase().replace(/\\s+/g,' ').trim();
        var matched=correctOptionTexts.some(function(c){
          var cClean=c.toLowerCase().replace(/\\s+/g,' ').trim();
          if(cClean===optClean) return true;
          var shorter=optClean.length<cClean.length?optClean:cClean;
          var longer=optClean.length<cClean.length?cClean:optClean;
          if(shorter.length>10&&longer.includes(shorter)) return true;
          var prefix=Math.min(40,shorter.length-3);
          if(prefix>8&&cClean.substring(0,prefix)===optClean.substring(0,prefix)) return true;
          return false;
        });
        if(matched) correctIndices.push(idx);
      });
      var allCorrect=correctIndices.map(function(i){return String.fromCharCode(65+i);});
      return {
        question_text:q.question_text,
        option_a:opts[0]||'',option_b:opts[1]||'',option_c:opts[2]||'',option_d:opts[3]||'',option_e:opts[4]||'',
        correct_answer:allCorrect.length>0?allCorrect[0]:'A',
        all_correct_answers:allCorrect.length>0?allCorrect:['A'],
        explanation:'',
        is_multi:q.question_text.toLowerCase().includes('select all')||
                 q.question_text.toLowerCase().includes('select 2')||
                 q.question_text.toLowerCase().includes('select 3')||
                 correctIndices.length>1
      };
    });

    console.log('[Nexus] correctOptionTexts:', correctOptionTexts);
    console.log('[Nexus] answers detected:', finalQuestions.map(function(q){
      return {q: q.question_text.substring(0,50), correct: q.correct_answer, all: q.all_correct_answers};
    }));

    return finalQuestions;
  }

  function clickContinue(){
    var all=document.querySelectorAll('button,input[type=button],input[type=submit],a');
    for(var i=0;i<all.length;i++){
      var t=(all[i].innerText||all[i].value||all[i].textContent||'').trim().toLowerCase();
      if(t==='continue'||t==='next question'||t==='next'||t.includes('continue')){
        all[i].click();return true;
      }
    }
    // Fallback: if only one prominent button exists, click it
    var btns=document.querySelectorAll('button:not([class*="nav"]):not([class*="menu"])');
    if(btns.length===1){btns[0].click();return true;}
    return false;
  }

  function waitForPageChange(prevPage,timeout){
    return new Promise(function(resolve,reject){
      var start=Date.now();
      var iv=setInterval(function(){
        var info=getPageInfo();
        if(info.current>prevPage||isResultsPage()){clearInterval(iv);setTimeout(resolve,800);} 
        else if(Date.now()-start>(timeout||10000)){clearInterval(iv);reject(new Error('timeout'));}
      },300);
    });
  }

  async function run(){
    var weekNum=prompt('Auto-importing with correct answers.\\nWeek number?','1');
    if(weekNum===null) return;
    var title=document.title.replace(/[|\\-].*examcompass.*/i,'').trim();
    var sourceUrl=window.location.href;
    var collectedQuestions=[];
    var pageInfo=getPageInfo();
    if(!pageInfo.found){showBanner('Not on a quiz page.','error');return;}
    var totalPages=pageInfo.total;
    showBanner('Nexus - Collecting '+totalPages+' questions...');
    await sleep(400);

    for(var page=pageInfo.current;page<=totalPages;page++){
      showBanner('Collecting Q'+page+'/'+totalPages+'...');
      var q=parseQuestionPage();
      if(q&&!collectedQuestions.some(function(x){return x.question_text===q.question_text;})) collectedQuestions.push(q);
      var clicked=clickContinue();
      if(!clicked&&page<totalPages){showBanner('Could not find Continue on page '+page,'error');return;}
      if(page<totalPages){
        try{await waitForPageChange(page,10000);}catch(e){await sleep(2000);}
      } else {
        showBanner('Waiting for results page...');
        await new Promise(function(resolve){
          var start=Date.now();
          var iv=setInterval(function(){
            if(isResultsPage()){clearInterval(iv);setTimeout(resolve,1500);} 
            else if(Date.now()-start>15000){clearInterval(iv);resolve();}
          },400);
        });
      }
    }

    showBanner('Reading correct answers...');
    await sleep(600);
    var finalQuestions=parseResultsPage(collectedQuestions);
    var allA=finalQuestions.every(function(q){return q.correct_answer==='A'&&q.all_correct_answers.join('')==='A';});
    if(allA){showBanner('Warning: correct answers defaulting to A - importing anyway...');await sleep(2000);}
    showBanner('Sending '+finalQuestions.length+' questions...');

    try{
      var res=await fetch(API,{method:'POST',headers:{'Content-Type':'application/json','X-Admin-Key':ADMIN_KEY},body:JSON.stringify({title:title,source_url:sourceUrl,week_number:parseInt(weekNum)||1,questions:finalQuestions})});
      var data=await res.json();
      if(data.success||(data.data&&data.data.quiz_id)){
        var detected=finalQuestions.filter(function(q){return q.correct_answer!=='A'||q.all_correct_answers.length>1;}).length;
        showBanner('Done! '+finalQuestions.length+' questions, '+detected+' answers detected.','done');
      } else {
        showBanner('Server error: '+JSON.stringify(data).slice(0,120),'error');
      }
    }catch(e){
      showBanner('Cannot reach backend. Is it running? '+e.message,'error');
    }
  }

  run().catch(function(e){showBanner('Error: '+e.message,'error');});
})();`;

  const handleCopy = () => {
    navigator.clipboard.writeText(bookmarkletCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <main className="mx-auto max-w-3xl space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">ExamCompass Bookmarklet</h1>
        <p className="mt-1 text-slate-500 dark:text-slate-400">One-click import from ExamCompass while you browse.</p>
      </div>

      <div className="panel space-y-5 dark:border-slate-700 dark:bg-slate-900">
        <h2 className="text-lg font-bold">Setup (one time)</h2>

        <div className="flex items-start gap-4">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-600 text-sm font-bold text-white">1</span>
          <div>
            <p className="font-medium text-slate-900 dark:text-slate-100">Show bookmarks bar</p>
            <p className="text-sm text-slate-500">Press <kbd className="rounded border px-1.5 py-0.5 font-mono text-xs dark:border-slate-600">Ctrl+Shift+B</kbd> (Windows) or <kbd className="rounded border px-1.5 py-0.5 font-mono text-xs dark:border-slate-600">Cmd+Shift+B</kbd> (Mac)</p>
          </div>
        </div>

        <div className="flex items-start gap-4">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-600 text-sm font-bold text-white">2</span>
          <div className="flex-1">
            <p className="font-medium text-slate-900 dark:text-slate-100">Copy bookmarklet code</p>
            <p className="mb-2 text-sm text-slate-500">Click below to copy</p>
            <button onClick={handleCopy} className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">
              {copied ? <CheckCircle size={16} /> : <Copy size={16} />}
              {copied ? "Copied!" : "Copy Bookmarklet Code"}
            </button>
          </div>
        </div>

        <div className="flex items-start gap-4">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-600 text-sm font-bold text-white">3</span>
          <div>
            <p className="font-medium text-slate-900 dark:text-slate-100">Create bookmark</p>
            <p className="text-sm text-slate-500">Right-click bookmarks bar and add a new bookmark</p>
            <ul className="mt-2 space-y-1 text-sm text-slate-500">
              <li>- Name: <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">Import to Nexus</code></li>
              <li>- URL: paste copied code</li>
            </ul>
          </div>
        </div>
      </div>

      <div className="panel dark:border-slate-700 dark:bg-slate-900">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-lg font-bold">Bookmarklet Code</h2>
          <button onClick={handleCopy} className="btn-secondary text-xs">{copied ? "Copied!" : "Copy"}</button>
        </div>
        <pre className="max-h-40 overflow-auto whitespace-pre-wrap break-all rounded-lg bg-slate-100 p-3 text-xs text-slate-700 dark:bg-slate-800 dark:text-slate-300">{bookmarkletCode}</pre>
        <p className="mt-2 text-xs text-slate-400">This code runs in your browser and posts to {API_URL}</p>
      </div>
    </main>
  );
}
