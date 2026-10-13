
(function(){
  var root=document.documentElement,key='jp-theme';
  try{var s=localStorage.getItem(key);if(s==='dark'||s==='light')root.setAttribute('data-theme',s);}catch(e){}
  function cur(){var t=root.getAttribute('data-theme');if(t)return t;return matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}
  function init(){
    var b=document.getElementById('themebtn');if(!b)return;
    function label(){b.textContent=cur()==='dark'?'Light':'Dark';}
    label();
    b.addEventListener('click',function(){
      var n=cur()==='dark'?'light':'dark';
      root.setAttribute('data-theme',n);
      try{localStorage.setItem(key,n);}catch(e){}
      label();
    });
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();

document.addEventListener('DOMContentLoaded',function(){
(function(){
  var btns=[].slice.call(document.querySelectorAll('.step'));
  var tag=document.getElementById('d-tag'),nm=document.getElementById('d-name'),
      why=document.getElementById('d-why'),fail=document.getElementById('d-fail');
  btns.forEach(function(b){
    b.addEventListener('click',function(){
      btns.forEach(function(x){x.setAttribute('aria-pressed',x===b?'true':'false');});
      tag.className='tag '+(b.dataset.cat==='det'?'':b.dataset.cat);
      tag.textContent=b.dataset.kind;
      nm.textContent=b.dataset.name;why.textContent=b.dataset.why;fail.textContent=b.dataset.fail;
      try{b.scrollIntoView({block:'nearest',inline:'center',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});}catch(e){}
    });
  });
})();

(function(){
  var chips=[].slice.call(document.querySelectorAll('.chip'));
  var rows=[].slice.call(document.querySelectorAll('#entries .entry'));
  var empty=document.getElementById('empty');
  chips.forEach(function(c){
    c.addEventListener('click',function(){
      var f=c.dataset.filter,shown=0;
      chips.forEach(function(x){x.setAttribute('aria-pressed',x===c?'true':'false');});
      rows.forEach(function(r){var ok=f==='All'||r.dataset.stage===f;r.hidden=!ok;if(ok)shown++;});
      empty.hidden=shown>0;
    });
  });
})();

(function(){
  var d=document.querySelector('details[data-collapse-mobile]');
  if(d&&matchMedia('(max-width:640px)').matches)d.removeAttribute('open');
})();
});
