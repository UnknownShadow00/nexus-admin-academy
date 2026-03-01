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
      el.style.cssText='position:fixed;top:0;left:0;right:0;z-index:999999;padding:14px 20px;font-family:sans-serif;font-size:14px;font-weight:600;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,0.3);transition:background 0.3s;';
      document.body.appendChild(el);
    }
    el.style.background=state==='error'?'#dc2626':state==='done'?'#16a34a':'#1d4ed8';
    el.style.color='white';
    el.innerText=msg;
    if(state==='done'||state==='error') setTimeout(function(){if(el.parentNode)el.parentNode.removeChild(el);},8000);
  }

  function sleep(ms){return new Promise(function(r){setTimeout(r,ms);});}

  function getPageInfo(){
    var m=document.body.innerText.match(/Page[:\\s]+(\\d+)\\s*of\\s*(\\d+)/i);
    return m?{current:parseInt(m[1]),total:parseInt(m[2]),found:true}:{current:1,total:1,found:false};
  }

  function isResultsPage(){
    var text=document.body.innerText;
    return !text.match(/Page:\\s*\\d+\\s*of\\s*\\d+/i)&&
           (text.includes('Missed')||text.match(/Your Score|Results|you (got|scored)|Quiz Complete/i));
  }

  function parseQuestionPage(){
    var inputs=document.querySelectorAll('input[type=checkbox],input[type=radio]');
    if(!inputs.length) return null;

    // Find question text
    var questionText='';
    var container=inputs[0].closest('form,table,fieldset,[class*=quiz],[class*=question],.panel,.card')||document.body;
    var candidates=container.querySelectorAll('p,h3,h4,h5,strong,b,td,div,span');
    for(var i=0;i<candidates.length;i++){
      if(candidates[i].querySelector('input,label')) continue;
      var t=(candidates[i].innerText||'').trim();
      if(t.length>15&&t.length<800&&!t.match(/^(Page\\s*\\d|Continue|Next|ExamCompass|CompTIA|Discount|Copyright|Select your answer)/i)){
        questionText=t.replace(/^[\\u25B6\\u25BA\\u25B8\\u25CF>\\-]\\s*/,'').trim();
        break;
      }
    }
    if(!questionText){
      var allP=document.querySelectorAll('p,h3,h4');
      for(var j=0;j<allP.length;j++){
        var pt=(allP[j].innerText||'').trim();
        if(pt.length>20&&!pt.match(/ExamCompass|Practice Test|Discount|Page:|Copyright/i)){
          questionText=pt.replace(/^[>\\u25B6]\\s*/,'').trim();
          break;
        }
      }
    }
    if(!questionText) return null;

    // Collect options
    var options=[];
    inputs.forEach(function(inp){
      var lbl=document.querySelector('label[for="'+inp.id+'"]')||inp.closest('label')||inp.parentElement;
      var text='';
      if(lbl){
        var clone=lbl.cloneNode(true);
        clone.querySelectorAll('input').forEach(function(el){el.remove();});
        text=(clone.innerText||clone.textContent||'').trim();
      }
      text=text.replace(/^[A-Ea-e][.)\\s]+/,'').replace(/^[\\u2713\\u2717\\u2610\\u2611\\u2714]\\s*/g,'').trim();
      if(text&&text.length>0&&options.indexOf(text)===-1) options.push(text);
    });
    if(options.length<2) return null;
    return {question_text:questionText,options:options};
  }

  // NEW STRATEGY: Parse correct answers from the results page
  // by reading the full page text and finding option text that appears
  // near "Missed" markers. Works regardless of HTML structure.
  function parseResultsPage(collectedQuestions){

    // APPROACH 1: Walk the DOM tree looking for text nodes
    // The results page lists each question with answers. Correct answers
    // the user missed are marked. We find them by their surrounding context.
    var correctTexts=[];

    // Try getting all leaf-level text from the page
    var fullText=document.body.innerText;

    // APPROACH 2: Find every element that literally contains "Missed"
    // and grab its sibling/parent text as the correct answer text
    var allElements=Array.from(document.querySelectorAll('*'));
    var missedEls=allElements.filter(function(el){
      return el.children.length===0&&(el.innerText||el.textContent||'').trim()==='Missed';
    });

    console.log('[Nexus] Found',missedEls.length,'"Missed" leaf elements');

    missedEls.forEach(function(el){
      // Walk up to find a container that has the option text
      var node=el;
      for(var depth=0;depth<5;depth++){
        node=node.parentElement;
        if(!node) break;
        var clone=node.cloneNode(true);
        // Remove the Missed element and any icons
        clone.querySelectorAll('input,svg,img,button').forEach(function(x){x.remove();});
        var cleaned=(clone.innerText||clone.textContent||'')
          .replace(/Missed/gi,'')
          .replace(/Your answer/gi,'')
          .replace(/Correct answer/gi,'')
          .replace(/[\\u2713\\u2714\\u2717\\u2718]/g,'') // ✓✔✗✘
          .replace(/\\(.*?\\)/g,'')  // remove parenthetical markers
          .replace(/^[A-Ea-e][.)\\s]+/,'')
          .replace(/\\s+/g,' ')
          .trim();
        if(cleaned.length>5&&cleaned.length<300&&
           !cleaned.match(/^(Page|ExamCompass|CompTIA|Copyright|Quiz|Score|Result)/i)){
          correctTexts.push(cleaned);
          console.log('[Nexus] Correct text found at depth',depth,':',cleaned.substring(0,80));
          break;
        }
      }
    });

    // APPROACH 3: If approach 2 found nothing, fall back to scanning all text
    // for option text that appears near the word "Missed" in the raw text
    if(correctTexts.length===0){
      console.log('[Nexus] Approach 2 found nothing, trying text proximity approach');
      // Split page text into lines and find lines near "Missed" lines
      var lines=fullText.split('\\n').map(function(l){return l.trim();}).filter(function(l){return l.length>0;});
      lines.forEach(function(line,idx){
        if(line.match(/^Missed$/i)||line.match(/\\(.*Missed.*\\)/i)){
          // The option text is usually 1-3 lines before the "Missed" marker
          for(var back=1;back<=4;back++){
            var candidate=(lines[idx-back]||'').trim()
              .replace(/^[A-Ea-e][.)\\s]+/,'')
              .replace(/[\\u2713\\u2714\\u2717]/g,'')
              .trim();
            if(candidate.length>5&&!candidate.match(/^(Your answer|Correct|Missed|Page|ExamCompass)/i)){
              correctTexts.push(candidate);
              console.log('[Nexus] Text proximity match:',candidate.substring(0,80));
              break;
            }
          }
        }
      });
    }

    // APPROACH 4: Look at the full page text for the ✓ character directly
    if(correctTexts.length===0){
      console.log('[Nexus] Trying checkmark character scan');
      allElements.forEach(function(el){
        if(el.children.length>3) return;
        var t=(el.innerText||el.textContent||'').trim();
        if((t.includes('\\u2713')||t.includes('\\u2714')||t.startsWith('✓')||t.startsWith('✔'))&&t.length<300){
          var cleaned=t.replace(/[\\u2713\\u2714]/g,'').replace(/Missed/gi,'').replace(/^[A-Ea-e][.)\\s]+/,'').trim();
          if(cleaned.length>5) correctTexts.push(cleaned);
        }
      });
    }

    console.log('[Nexus] All correct texts collected:',correctTexts);

    // Deduplicate
    correctTexts=correctTexts.filter(function(t,i,a){return a.indexOf(t)===i;});

    // Match correct texts back to each question's options
    return collectedQuestions.map(function(q){
      var opts=q.options;
      var correctIndices=[];

      opts.forEach(function(opt,idx){
        var optClean=opt.toLowerCase().replace(/\\s+/g,' ').trim();
        var matched=correctTexts.some(function(ct){
          var ctClean=ct.toLowerCase().replace(/\\s+/g,' ').trim();
          // Exact match
          if(ctClean===optClean) return true;
          // One contains the other (handles minor differences)
          var shorter=optClean.length<=ctClean.length?optClean:ctClean;
          var longer=optClean.length<=ctClean.length?ctClean:optClean;
          if(shorter.length>8&&longer.includes(shorter)) return true;
          // First N chars match (handles truncation)
          var n=Math.min(35,shorter.length-2);
          if(n>6&&ctClean.substring(0,n)===optClean.substring(0,n)) return true;
          return false;
        });
        if(matched) correctIndices.push(idx);
      });

      var allCorrect=correctIndices.map(function(i){return String.fromCharCode(65+i);});
      console.log('[Nexus] Q:',q.question_text.substring(0,50),'-> correct:',allCorrect);

      return {
        question_text:q.question_text,
        option_a:opts[0]||'',
        option_b:opts[1]||'',
        option_c:opts[2]||'',
        option_d:opts[3]||'',
        option_e:opts[4]||'',
        correct_answer:allCorrect.length>0?allCorrect[0]:'A',
        all_correct_answers:allCorrect.length>0?allCorrect:['A'],
        explanation:'',
        is_multi:correctIndices.length>1||
                 q.question_text.toLowerCase().includes('select all')||
                 q.question_text.toLowerCase().includes('select 2')||
                 q.question_text.toLowerCase().includes('select 3')
      };
    });
  }

  function clickContinue(){
    var all=document.querySelectorAll('button,input[type=button],input[type=submit],a.btn,a.button');
    for(var i=0;i<all.length;i++){
      var t=(all[i].innerText||all[i].value||all[i].textContent||'').trim().toLowerCase();
      if(t==='continue'||t==='next'||t==='next question'||t.includes('continue')){
        all[i].click();return true;
      }
    }
    // Last resort: only big button on page
    var btns=Array.from(document.querySelectorAll('button')).filter(function(b){
      return (b.innerText||'').trim().length>0;
    });
    if(btns.length===1){btns[0].click();return true;}
    return false;
  }

  function waitForPageChange(prevPage,timeout){
    return new Promise(function(resolve,reject){
      var start=Date.now();
      var iv=setInterval(function(){
        var info=getPageInfo();
        if(info.current>prevPage||isResultsPage()){clearInterval(iv);setTimeout(resolve,1000);}
        else if(Date.now()-start>(timeout||12000)){clearInterval(iv);reject(new Error('timeout on page '+prevPage));}
      },300);
    });
  }

  async function run(){
    var weekNum=prompt('ExamCompass Quiz Import\\nWeek number?','1');
    if(weekNum===null) return;

    var pageInfo=getPageInfo();
    if(!pageInfo.found){
      showBanner('Not on a quiz page. Go to an ExamCompass quiz first.','error');
      return;
    }

    var title=document.title.replace(/[|\\-].*$/,'').trim();
    var sourceUrl=window.location.href;
    var collectedQuestions=[];
    var totalPages=pageInfo.total;

    showBanner('Collecting '+totalPages+' questions — do not click anything...');
    await sleep(500);

    // Phase 1: click through all pages collecting question text and options
    for(var page=pageInfo.current;page<=totalPages;page++){
      showBanner('Reading question '+page+' of '+totalPages+'...');
      var q=parseQuestionPage();
      if(q){
        var isDup=collectedQuestions.some(function(x){return x.question_text===q.question_text;});
        if(!isDup) collectedQuestions.push(q);
      }
      if(page<totalPages){
        var clicked=clickContinue();
        if(!clicked){showBanner('Could not find Continue button on page '+page,'error');return;}
        try{await waitForPageChange(page,12000);}catch(e){await sleep(2500);}
      } else {
        // Last page: submit without answering to get results
        var clicked2=clickContinue();
        if(clicked2){
          showBanner('Submitted — waiting for results page...');
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

    if(collectedQuestions.length===0){
      showBanner('No questions collected. Are you on an ExamCompass quiz page?','error');
      return;
    }

    showBanner('Reading correct answers from results...');
    await sleep(800);

    var finalQuestions=parseResultsPage(collectedQuestions);

    var detected=finalQuestions.filter(function(q){
      return q.all_correct_answers.length>1||q.correct_answer!=='A';
    }).length;

    var allDefaultA=finalQuestions.every(function(q){
      return q.correct_answer==='A'&&q.all_correct_answers.join('')==='A';
    });

    if(allDefaultA){
      showBanner('Warning: could not detect correct answers (all defaulted to A). Open DevTools Console for diagnostic info. Importing anyway...');
      await sleep(3000);
    } else {
      showBanner('Detected '+detected+'/'+finalQuestions.length+' correct answers. Saving...');
      await sleep(500);
    }

    try{
      var res=await fetch(API,{
        method:'POST',
        headers:{'Content-Type':'application/json','X-Admin-Key':ADMIN_KEY},
        body:JSON.stringify({
          title:title,
          source_url:sourceUrl,
          week_number:parseInt(weekNum)||1,
          questions:finalQuestions
        })
      });
      var data=await res.json();
      if(data.success||(data.data&&data.data.quiz_id)){
        showBanner(allDefaultA
          ?'Saved (answers need manual correction in quiz editor — check console for diagnostic)'
          :'Done! '+finalQuestions.length+' questions, '+detected+' answers auto-detected.',
          allDefaultA?'error':'done'
        );
      } else {
        showBanner('Server error: '+JSON.stringify(data).slice(0,120),'error');
      }
    }catch(e){
      showBanner('Cannot reach backend at ${API_URL}. '+e.message,'error');
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
