import "./style.css";

type Mode = "topic" | "video";
const root = document.querySelector<HTMLDivElement>("#root")!;
let mode: Mode = "topic";
let approved = false;
const workflowUrl = "https://github.com/lk0024709-ux/2d-trend/actions/workflows/render.yml";
const sampleScript = "A tiny idea can become a big story.\nStart with one bold thought.\nTurn it into a visual moment people remember.";
root.innerHTML = `
<header class="topbar"><a class="brand" href="#"><span class="mark">2D</span><span> TREND <small>STUDIO</small></span></a><span class="cloud"><i></i> CLOUD WORKER</span></header>
<main>
<section class="hero"><p class="eyebrow">CREATOR WORKSPACE / ANDROID FIRST</p><h1>Make your story<br><em>move.</em></h1><p class="sub">Turn a video into illustrated motion, or build an animated reel from a topic. Rendering runs in GitHub Actions—not on your phone.</p></section>
<nav class="tabs" aria-label="Workflows"><button class="tab active" data-mode="topic">✦ Topic to Animated Reel</button><button class="tab" data-mode="video">▧ Video to 2D Animation</button></nav>
<section class="panel" id="topic-panel">
<div class="panel-head"><div><span class="step">01 / CREATE</span><h2>Start with a topic</h2></div><span class="pill">NO API KEY · DEMO READY</span></div>
<label>What is your reel about?<textarea id="topic" rows="2" maxlength="500" placeholder="e.g. 3 surprising facts about the moon">3 surprising facts about the moon</textarea></label>
<div class="grid"><label>Language<select id="language"><option>English</option><option>Hindi</option><option>Hinglish</option></select></label><label>Duration<select id="duration"><option value="15">15 seconds</option><option value="30">30 seconds</option><option value="45">45 seconds</option><option value="60">60 seconds</option></select></label><label>Visual style<select id="style"><option value="indian-comic">Indian comic / cel shade</option><option value="bold-motion">Bold motion graphics</option><option value="minimal">Minimal typography</option></select></label><label>Voice<select id="voice"><option value="none">No voice (demo)</option><option value="own-recording">I'll add my recording</option><option value="tts">Configured TTS provider</option></select></label></div>
<div class="script-head"><div><span class="step">02 / REVIEW</span><h3>Script draft</h3></div><button class="text-btn" id="reset-script">Reset draft</button></div>
<textarea id="script" class="script" rows="5">${sampleScript}</textarea>
<label class="check"><input type="checkbox" id="approve"/> I have reviewed and approve this script for rendering.</label>
</section>
<section class="panel hidden" id="video-panel">
<div class="panel-head"><div><span class="step">01 / SOURCE</span><h2>Bring your video</h2></div><span class="pill">HTTPS SOURCE</span></div>
<label>Direct video URL<input id="media-url" type="url" placeholder="https://example.com/video.mp4"/></label>
<p class="hint">Use a direct HTTPS media URL reachable by GitHub Actions. Private videos need authenticated object storage; do not paste access tokens here.</p>
<label>Illustration treatment<select id="video-style"><option value="indian-comic">Indian comic / cel shade</option><option value="ink">Ink and posterized colour</option><option value="soft">Soft illustrated colour</option></select></label>
<label class="check"><input type="checkbox" id="preserve-audio" checked/> Preserve original audio</label>
<p class="hint">The MVP applies a non-generative stylized video filter and preserves source timing/cuts. It does not reproduce actors' exact faces.</p>
</section>
<section class="action-panel"><div><span class="step">03 / CLOUD RENDER</span><h3>Ready when you are</h3><p id="status">Your phone prepares the job. GitHub Actions renders the MP4 in the cloud.</p></div><button id="prepare" class="primary">Prepare render ↗</button></section>
<section id="result" class="result hidden" aria-live="polite"></section>
<section class="notice"><strong>What this MVP can do</strong><p>Topic mode creates an animated typography reel with phrase-timed captions. Video mode applies a deterministic illustration-style filter to a source clip. Generative frame artwork and TTS need configured provider credentials.</p></section>
</main><footer>2D TREND STUDIO <span>BUILT FOR MOBILE · RENDERED IN THE CLOUD</span></footer>`;

const $ = <T extends HTMLElement>(id:string) => document.getElementById(id) as T;
function setMode(next:Mode){mode=next;approved=false;$<HTMLInputElement>("approve").checked=false;document.querySelectorAll<HTMLButtonElement>(".tab").forEach(b=>b.classList.toggle("active",b.dataset.mode===next));$("topic-panel").classList.toggle("hidden",next!=="topic");$("video-panel").classList.toggle("hidden",next!=="video");$("result").classList.add("hidden");}
document.querySelectorAll<HTMLButtonElement>(".tab").forEach(b=>b.addEventListener("click",()=>setMode(b.dataset.mode as Mode)));
$("reset-script").addEventListener("click",()=>{$<HTMLTextAreaElement>("script").value=sampleScript;$<HTMLInputElement>("approve").checked=false;});
$("approve").addEventListener("change",e=>{approved=(e.target as HTMLInputElement).checked;});
$("prepare").addEventListener("click",()=>{
 const err=(message:string)=>{const box=$("result");box.classList.remove("hidden");box.innerHTML=`<p class="error">${message}</p>`;};
 let manifest:Record<string,unknown>;
 if(mode==="topic"){
  const topic=$<HTMLTextAreaElement>("topic").value.trim(), script=$<HTMLTextAreaElement>("script").value.trim();
  if(topic.length<4)return err("Please enter a topic with at least 4 characters.");
  if(!script)return err("Add a script before preparing the render.");
  if(!approved)return err("Review the script and tick the approval checkbox first.");
  manifest={version:1,mode:"topic",topic,language:$<HTMLSelectElement>("language").value,duration_seconds:Number($<HTMLSelectElement>("duration").value),style:$<HTMLSelectElement>("style").value,voice:$<HTMLSelectElement>("voice").value,script,output:{width:1080,height:1920,fps:24}};
 }else{
  const url=$<HTMLInputElement>("media-url").value.trim();
  try{const parsed=new URL(url);if(parsed.protocol!=="https:")throw new Error();}catch{return err("Enter a valid direct HTTPS video URL.");}
  manifest={version:1,mode:"video",media_url:url,style:$<HTMLSelectElement>("video-style").value,preserve_audio:$<HTMLInputElement>("preserve-audio").checked,output:{width:1080,height:1920,fps:24}};
 }
 const json=JSON.stringify(manifest,null,2);
 const box=$("result");box.classList.remove("hidden");
 box.innerHTML=`<span class="step">JOB MANIFEST READY</span><h3>Next: start the cloud render</h3><p>Copy this manifest, open the repository's Render workflow, choose <b>Run workflow</b>, paste it into the manifest field, and start the job. Your MP4 and QA report will appear under the run's Artifacts when it finishes.</p><textarea id="manifest" rows="9" readonly></textarea><div class="result-actions"><button class="secondary" id="copy">Copy manifest</button><a class="primary link-button" href="${workflowUrl}" target="_blank" rel="noreferrer">Open Render workflow ↗</a></div><p class="hint">No render has started yet. This page does not store GitHub credentials or pretend a job completed.</p>`;
 $<HTMLTextAreaElement>("manifest").value=json;
 $("copy").addEventListener("click",async()=>{await navigator.clipboard.writeText(json);$("copy").textContent="Copied ✓";});
 $("status").textContent="Manifest validated locally. Waiting for you to start the GitHub Actions workflow.";
});
