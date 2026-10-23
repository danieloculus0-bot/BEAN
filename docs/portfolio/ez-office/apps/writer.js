/* EZ Writer: real formatting with restricted HTML import/export, text import and print. */
(function(){
"use strict";
const TAGS=new Set(["P","DIV","BR","B","STRONG","I","EM","U","S","H1","H2","H3","UL","OL","LI","BLOCKQUOTE","A","SPAN","FONT"]);
function cleanHTML(source){
  const parsed=new DOMParser().parseFromString(source,"text/html");
  function copy(node,out){
    if(node.nodeType===Node.TEXT_NODE){out.append(document.createTextNode(node.textContent));return;}
    if(node.nodeType!==Node.ELEMENT_NODE)return;
    if(["SCRIPT","STYLE","IFRAME","OBJECT","EMBED","SVG","FORM","INPUT","META","LINK","IMG","VIDEO","AUDIO"].includes(node.tagName))return;
    const el=TAGS.has(node.tagName)?document.createElement(node.tagName.toLowerCase()):document.createDocumentFragment();
    if(el.nodeType===Node.ELEMENT_NODE){
      if(node.tagName==="A"){
        try{const u=new URL(node.getAttribute("href")||"",location.href);if(["https:","http:","mailto:"].includes(u.protocol))el.setAttribute("href",u.href);}catch(e){}
      }
      if(node.tagName==="FONT" && /^[1-7]$/.test(node.getAttribute("size")||""))el.setAttribute("size",node.getAttribute("size"));
      // Permit only simple color, alignment and background-color formatting.
      const align=node.style.textAlign;
      if(["left","right","center","justify"].includes(align))el.style.textAlign=align;
      const color=node.style.color;
      if(/^(#[0-9a-f]{3,8}|rgb[a]?\([\d\s,.%]+\)|[a-z]{1,18})$/i.test(color))el.style.color=color;
      const background=node.style.backgroundColor;
      if(/^(#[0-9a-f]{3,8}|rgb[a]?\([\d\s,.%]+\)|[a-z]{1,18})$/i.test(background))el.style.backgroundColor=background;
    }
    for(const c of node.childNodes)copy(c,el);
    out.append(el);
  }
  const out=document.createElement("div");
  for(const n of parsed.body.childNodes)copy(n,out);
  return out.innerHTML;
}
EZOffice.register("writer",function(ctx){
  const {elem,button,root,toolbar,message,download,choose,info,markDirty,onDispose}=ctx;
  let dirty=false;
  const bar=toolbar();
  const name=elem("input",{type:"text",value:"Document.html","aria-label":"Document filename"},bar);
  const stats=elem("small",{},bar);
  const tools=toolbar();
  const editor=elem("div",{className:"rich-editor",contenteditable:"true",role:"textbox","aria-label":"Rich document editor","aria-multiline":"true",spellcheck:"true"},root);
  editor.innerHTML="<p>Start writing. Highlight text to format it, or choose a heading style.</p>";
  function mark(v){dirty=v;markDirty(v);}
  function tally(){const t=editor.innerText.trim();stats.textContent=(t?t.split(/\s+/u).length:0)+" words · "+t.length+" characters";}
  function command(cmd,arg){
    const formats={bold:"strong",italic:"em",underline:"u",strikeThrough:"s"};
    const selection=window.getSelection();
    const activeRange=selection&&selection.rangeCount?selection.getRangeAt(0).cloneRange():null;
    if(formats[cmd]&&activeRange&&!activeRange.collapsed&&
       editor.contains(activeRange.commonAncestorContainer)){
      // Explicitly wrap selected text instead of relying on inconsistent
      // document.execCommand HTML output across Chromium / WebKit versions.
      const wrap=document.createElement(formats[cmd]);
      try{activeRange.surroundContents(wrap);}
      catch(e){const selected=activeRange.extractContents();wrap.appendChild(selected);activeRange.insertNode(wrap);}
      selection.removeAllRanges();const range=document.createRange();
      range.selectNodeContents(wrap);selection.addRange(range);
      editor.focus();mark(true);tally();return;
    }
    editor.focus();
    document.execCommand(cmd,false,arg||null);
    mark(true);tally();
  }
  const formats=[
    ["Bold","bold"],["Italic","italic"],["Underline","underline"],["Strike","strikeThrough"],
    ["Bullets","insertUnorderedList"],["Numbers","insertOrderedList"],
    ["Left","justifyLeft"],["Center","justifyCenter"],["Right","justifyRight"],
    ["Undo","undo"],["Redo","redo"]
  ];
  for(const [label,cmd] of formats){
    const b=button(tools,label,()=>command(cmd));
    b.setAttribute("aria-label",label);
    // Mouse-down on a button should not drop the selected range in the editor.
    b.addEventListener("mousedown",e=>e.preventDefault());
  }
  // Find/replace operates on text nodes so bold, headings and links survive edits.
  const findBar=toolbar();
  const findTerm=elem("input",{type:"text",placeholder:"Find in document","aria-label":"Find text"},findBar);
  const replaceTerm=elem("input",{type:"text",placeholder:"Replace with","aria-label":"Replacement text"},findBar);
  let findPosition=0;
  function textNodes(){
    const walker=document.createTreeWalker(editor,NodeFilter.SHOW_TEXT);
    const nodes=[];while(walker.nextNode())nodes.push(walker.currentNode);
    return nodes;
  }
  function findNext(){
    const needle=findTerm.value;
    if(!needle){message("Enter text to find");return;}
    const nodes=textNodes(),lower=needle.toLocaleLowerCase();
    const total=nodes.reduce((n,v)=>n+v.textContent.length,0);
    function seek(start){
      let offset=0;
      for(const node of nodes){
        const source=node.textContent,at=source.toLocaleLowerCase().indexOf(lower,Math.max(0,start-offset));
        if(at>=0){return {node,at,absolute:offset+at};}
        offset+=source.length;
      }
      return null;
    }
    const result=seek(findPosition)||seek(0);
    if(!result){message("No match for: "+needle);return;}
    const range=document.createRange();
    range.setStart(result.node,result.at);range.setEnd(result.node,result.at+needle.length);
    const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);
    result.node.parentElement?.scrollIntoView({block:"nearest"});
    findPosition=result.absolute+needle.length;
    if(findPosition>=total)findPosition=0;
    message("Found: "+needle);
  }
  button(findBar,"Find next",findNext);
  button(findBar,"Replace all",()=>{
    const needle=findTerm.value;
    if(!needle){message("Enter text to replace");return;}
    let replacements=0;
    for(const node of textNodes()){
      const original=node.textContent;
      const lower=original.toLocaleLowerCase(),wanted=needle.toLocaleLowerCase();
      let cursor=0,next,updated="";
      while((next=lower.indexOf(wanted,cursor))>=0){
        updated+=original.slice(cursor,next)+replaceTerm.value;
        cursor=next+needle.length;replacements++;
      }
      if(cursor)node.textContent=updated+original.slice(cursor);
    }
    if(replacements){mark(true);tally();findPosition=0;}
    message(replacements+" text match"+(replacements===1?"":"es")+" replaced. Formatting preserved.");
  });
  findTerm.addEventListener("input",()=>{findPosition=0;});
  const headings=elem("select",{"aria-label":"Paragraph style"},tools);
  for(const [value,label] of [["P","Paragraph"],["H1","Heading 1"],["H2","Heading 2"],["H3","Heading 3"],["BLOCKQUOTE","Quote"]])elem("option",{value,text:label},headings);
  headings.addEventListener("change",()=>command("formatBlock",headings.value));
  const colors=elem("select",{"aria-label":"Text color"},tools);
  for(const [value,label] of [["#edf4f2","Default"],["#1e293b","Black"],["#c0392b","Red"],["#287fb8","Blue"],["#16875f","Green"]])elem("option",{value,text:label},colors);
  colors.addEventListener("change",()=>command("foreColor",colors.value));
  function exportHTML(){return "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><title>EZ Writer document</title><style>body{font:16px/1.6 Georgia,serif;max-width:800px;margin:40px auto;padding:20px}h1,h2,h3{line-height:1.25}a{color:#2563eb}</style></head><body>"+cleanHTML(editor.innerHTML)+"</body></html>";}
  function save(asText){
    const text=editor.innerText;
    const basename=(name.value.replace(/[\\/]/g,"_").replace(/\.(html?|txt|md)$/i,"")||"Document");
    download(basename+(asText?".txt":".html"),asText?text:exportHTML(),asText?"text/plain;charset=utf-8":"text/html;charset=utf-8");
    mark(false);
  }
  button(bar,"Open",()=>choose(".html,.htm,.txt,.md,text/html,text/plain",async file=>{
    if(file.size>5*1024*1024)throw Error("File exceeds the 5 MB editor limit");
    if(dirty&&!confirm("Discard unsaved document changes?"))return;
    const t=await file.text();if(!ctx.isActive())return;
    if(/\.html?$/i.test(file.name))editor.innerHTML=cleanHTML(t);
    else{editor.replaceChildren();const p=document.createElement("p");p.textContent=t;editor.append(p);editor.style.whiteSpace="pre-wrap";}
    name.value=file.name;mark(false);tally();message("Opened "+file.name);
  }));
  button(bar,"Open DOCX",()=>choose(".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document",async file=>{
    if(file.size>10*1024*1024)throw Error("DOCX exceeds the 10 MB import limit");
    if(dirty&&!confirm("Discard unsaved document changes?"))return;
    const parsed=EZOfficeImport.readDOCX(await file.arrayBuffer());
    if(!ctx.isActive())return;
    editor.innerHTML=cleanHTML(parsed.html);
    editor.style.whiteSpace="";
    name.value=file.name;
    mark(false);tally();
    message("Imported "+parsed.blocks+" Word paragraph(s). Images, page layout and advanced objects are not imported.");
  }));
  button(bar,"Save DOCX",()=>{
    const basename=(name.value.replace(/[\/]/g,"_").replace(/.(html?|txt|md|docx)$/i,"")||"Document");
    download(basename+".docx",EZOfficeExport.docx(editor),"application/vnd.openxmlformats-officedocument.wordprocessingml.document");
    mark(false);
  },true);
  button(bar,"Save HTML",()=>save(false));
  button(bar,"Export text",()=>save(true));
  button(bar,"Print / PDF",()=>window.print());
  button(bar,"New",()=>{
    if(dirty&&!confirm("Discard unsaved document changes?"))return;
    editor.innerHTML="<p></p>";name.value="Document.html";mark(false);tally();
  });
  editor.addEventListener("input",()=>{mark(true);tally();});
  editor.addEventListener("paste",e=>{
    // Plain-text paste by default, so pasted websites cannot execute code.
    if(e.clipboardData){e.preventDefault();document.execCommand("insertText",false,e.clipboardData.getData("text/plain"));}
  });
  function key(e){if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="s"){e.preventDefault();save(false);}}
  document.addEventListener("keydown",key);
  onDispose(()=>document.removeEventListener("keydown",key));
  tally();
  info("Export real DOCX for Word and LibreOffice, HTML, plain text, and Print / Save as PDF from your browser. Real editable formatted HTML with find/replace, headings, bold, italic, underline, lists, alignment, colors and printing. Opens HTML safely with restricted tags. Imports DOCX paragraphs, basic headings and text emphasis; images, tables, complex page layout and other advanced Word features are not reproduced.");
  return ()=>{editor.replaceChildren();};
});
})();