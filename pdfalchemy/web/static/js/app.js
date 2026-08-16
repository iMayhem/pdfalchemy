class PDFAlchemyApp {
constructor() {
this.currentFileId=null;this.currentFilename='';this.totalPages=0;this.currentPage=0;
this.currentTool='convert';this.selectedFormat='docx';this.selectedRotation=90;this.zoom=100;this.apiBase='';
this.init();
}
init(){
this.bindEvents();
this.updateWatermarkPreview();
}
bindEvents(){
const uploadArea=document.getElementById('uploadArea'),fileInput=document.getElementById('fileInput');
uploadArea.addEventListener('click',()=>fileInput.click());
uploadArea.addEventListener('dragover',e=>{e.preventDefault();uploadArea.classList.add('dragover');});
uploadArea.addEventListener('dragleave',()=>uploadArea.classList.remove('dragover'));
uploadArea.addEventListener('drop',e=>{e.preventDefault();uploadArea.classList.remove('dragover');if(e.dataTransfer.files.length>0)this.handleUpload(e.dataTransfer.files[0]);});
fileInput.addEventListener('change',e=>{if(e.target.files.length>0)this.handleUpload(e.target.files[0]);});
document.querySelectorAll('.tool-btn').forEach(btn=>btn.addEventListener('click',()=>this.switchTool(btn.dataset.tool)));
document.querySelectorAll('.format-option').forEach(opt=>opt.addEventListener('click',()=>{document.querySelectorAll('.format-option').forEach(o=>o.classList.remove('active'));opt.classList.add('active');this.selectedFormat=opt.dataset.format;}));
document.getElementById('prevPage').addEventListener('click',()=>this.prevPage());
document.getElementById('nextPage').addEventListener('click',()=>this.nextPage());
document.getElementById('zoomIn').addEventListener('click',()=>this.zoomIn());
document.getElementById('zoomOut').addEventListener('click',()=>this.zoomOut());
document.getElementById('processBtn').addEventListener('click',()=>this.process());
document.getElementById('newFileBtn').addEventListener('click',()=>this.reset());
document.getElementById('watermarkText').addEventListener('input',()=>this.updateWatermarkPreview());
document.getElementById('watermarkOpacity').addEventListener('input',e=>{document.getElementById('opacityValue').textContent=e.target.value;this.updateWatermarkPreview();});
document.getElementById('watermarkSize').addEventListener('input',e=>{document.getElementById('fontsizeValue').textContent=e.target.value;this.updateWatermarkPreview();});
document.querySelectorAll('.rotate-btn').forEach(btn=>btn.addEventListener('click',()=>{document.querySelectorAll('.rotate-btn').forEach(b=>b.classList.remove('active'));btn.classList.add('active');this.selectedRotation=parseInt(btn.dataset.degrees);}));
document.getElementById('addRange').addEventListener('click',()=>this.addSplitRange());
document.getElementById('closeResultBtn').addEventListener('click',()=>{document.getElementById('resultModal').classList.remove('active');});
}
async handleUpload(file){
if(!file.name.endsWith('.pdf')){alert('Please upload a PDF file.');return;}
this.showProgress('Uploading...','Please wait while we upload your PDF');
const formData=new FormData();formData.append('file',file);
try{
const res=await fetch(`${this.apiBase}/api/upload`,{method:'POST',body:formData});
const data=await res.json();
this.currentFileId=data.file_id;this.currentFilename=data.filename;this.totalPages=data.page_count;this.currentPage=0;
document.getElementById('currentFilename').textContent=data.filename;
document.getElementById('pageCount').textContent=`${data.page_count} page${data.page_count!==1?'s':''}`;
document.getElementById('pageIndicator').textContent=`Page 1 of ${data.page_count}`;
document.querySelectorAll('.split-end').forEach(el=>{el.max=data.page_count;if(!el.value)el.value=data.page_count;});
document.querySelectorAll('.split-start').forEach(el=>{el.max=data.page_count;});
document.getElementById('redactPage').max=data.page_count;
this.hideProgress();this.showEditor();this.loadPreview();this.loadTextPreview();
}catch(err){this.hideProgress();alert('Upload failed: '+err.message);}
}
showEditor(){document.getElementById('uploadSection').style.display='none';document.getElementById('editorSection').style.display='flex';}
async loadPreview(){
if(!this.currentFileId)return;
const container=document.getElementById('pageView');
container.innerHTML='<div class="placeholder-text">Loading preview...</div>';
try{
const res=await fetch(`${this.apiBase}/api/thumbnail/${this.currentFileId}?page=${this.currentPage}&dpi=120`);
if(res.ok){const blob=await res.blob();const url=URL.createObjectURL(blob);container.innerHTML=`<img src="${url}" alt="Page ${this.currentPage+1}" style="max-width:100%;height:auto;">`;}
else container.innerHTML='<div class="placeholder-text">Preview not available</div>';
}catch(err){container.innerHTML='<div class="placeholder-text">Preview error</div>';}
}
async loadTextPreview(){
if(!this.currentFileId)return;
try{
const res=await fetch(`${this.apiBase}/api/preview/${this.currentFileId}?page=${this.currentPage}`);
const data=await res.json();
const content=document.getElementById('textPreviewContent');content.innerHTML='';
data.blocks.forEach(block=>{const div=document.createElement('div');div.className=`text-block ${block.type}`;div.textContent=block.text;div.title=`Type: ${block.type} | Font: ${block.font} | Size: ${block.size.toFixed(1)}pt | BBox: [${block.bbox.map(v=>v.toFixed(1)).join(', ')}]`;content.appendChild(div);});
if(data.tables.length>0){data.tables.forEach((table,idx)=>{const tableDiv=document.createElement('div');tableDiv.className='text-block';tableDiv.style.borderLeftColor='var(--warning)';tableDiv.innerHTML=`<strong>Table ${idx+1}</strong> (${table.rows}x${table.cols})`;content.appendChild(tableDiv);});}
}catch(err){document.getElementById('textPreviewContent').innerHTML='<div class="placeholder-text">Could not load text preview</div>';}
}
switchTool(tool){
this.currentTool=tool;
document.querySelectorAll('.tool-btn').forEach(btn=>btn.classList.remove('active'));
document.querySelector(`.tool-btn[data-tool="${tool}"]`).classList.add('active');
document.querySelectorAll('.tool-content').forEach(content=>content.classList.remove('active'));
document.querySelector(`.tool-content[data-tool="${tool}"]`).classList.add('active');
}
prevPage(){if(this.currentPage>0){this.currentPage--;this.updatePageIndicator();this.loadPreview();this.loadTextPreview();}}
nextPage(){if(this.currentPage<this.totalPages-1){this.currentPage++;this.updatePageIndicator();this.loadPreview();this.loadTextPreview();}}
updatePageIndicator(){document.getElementById('pageIndicator').textContent=`Page ${this.currentPage+1} of ${this.totalPages}`;}
zoomIn(){this.zoom=Math.min(this.zoom+25,200);this.applyZoom();}
zoomOut(){this.zoom=Math.max(this.zoom-25,50);this.applyZoom();}
applyZoom(){document.getElementById('zoomLevel').textContent=`${this.zoom}%`;document.getElementById('pageView').style.transform=`scale(${this.zoom/100})`;}
updateWatermarkPreview(){
const text=document.getElementById('watermarkText').value||'WATERMARK';
const opacity=document.getElementById('watermarkOpacity').value/100;
const size=document.getElementById('watermarkSize').value;
const sample=document.getElementById('wmSample');
if(sample){sample.textContent=text;sample.style.opacity=opacity;sample.style.fontSize=`${size}px`;}
}
addSplitRange(){
const container=document.getElementById('splitRanges');
const div=document.createElement('div');div.className='split-range';
div.innerHTML=`<input type="number" class="split-start" placeholder="From" min="1" value="1"><span>to</span><input type="number" class="split-end" placeholder="To" min="1" max="${this.totalPages}"><button class="remove-range">x</button>`;
div.querySelector('.remove-range').addEventListener('click',()=>div.remove());
container.appendChild(div);
}
async process(){
if(!this.currentFileId)return;
this.showProgress('Processing...','Working on your PDF');
try{
let res,data;
switch(this.currentTool){
case'convert':res=await this.postForm('/api/convert',{file_id:this.currentFileId,format:this.selectedFormat,page_breaks:document.getElementById('pageBreaks').checked});data=await res.json();this.showResult('Conversion Complete!','Your PDF has been converted.',data.download_url);break;
case'watermark':res=await this.postForm('/api/watermark',{file_id:this.currentFileId,text:document.getElementById('watermarkText').value,opacity:document.getElementById('watermarkOpacity').value/100,fontsize:document.getElementById('watermarkSize').value});data=await res.json();this.showResult('Watermark Added!','Your PDF now has a watermark.',data.download_url);break;
case'compress':res=await this.postForm('/api/compress',{file_id:this.currentFileId});data=await res.json();document.getElementById('originalSize').textContent=this.formatBytes(data.original_size);document.getElementById('compressedSize').textContent=this.formatBytes(data.compressed_size);document.getElementById('savedPercent').textContent=`${data.reduction_percent}%`;this.showResult('Compression Complete!',`Saved ${data.reduction_percent}% (${this.formatBytes(data.original_size-data.compressed_size)})`,data.download_url);break;
case'rotate':res=await this.postForm('/api/rotate',{file_id:this.currentFileId,degrees:this.selectedRotation});data=await res.json();this.showResult('Rotation Complete!',`All pages rotated ${this.selectedRotation}*.`,data.download_url);break;
case'split':const ranges=[];document.querySelectorAll('.split-range').forEach(range=>{const start=parseInt(range.querySelector('.split-start').value);const end=parseInt(range.querySelector('.split-end').value);if(start&&end)ranges.push([start,end]);});res=await this.postForm('/api/split',{file_id:this.currentFileId,ranges:JSON.stringify(ranges)});data=await res.json();this.showResultMulti('Split Complete!',`Created ${data.files.length} PDF files.`,data.files);break;
case'extract':res=await this.postForm('/api/extract-images',{file_id:this.currentFileId});data=await res.json();this.showExtractResult(data);break;
case'redact':res=await this.postForm('/api/redact',{file_id:this.currentFileId,page:document.getElementById('redactPage').value,x1:document.getElementById('redactX1').value,y1:document.getElementById('redactY1').value,x2:document.getElementById('redactX2').value,y2:document.getElementById('redactY2').value});data=await res.json();this.showResult('Redaction Complete!','Sensitive content has been blacked out.',data.download_url);break;
}
}catch(err){this.hideProgress();alert('Processing failed: '+err.message);}
}
async postForm(endpoint,data){
const formData=new FormData();
Object.keys(data).forEach(key=>formData.append(key,data[key]));
const res=await fetch(`${this.apiBase}${endpoint}`,{method:'POST',body:formData});
if(!res.ok){const err=await res.json();throw new Error(err.detail||'Request failed');}
return res;
}
showProgress(title,message){
document.getElementById('progressTitle').textContent=title;
document.getElementById('progressMessage').textContent=message;
document.getElementById('progressFill').style.width='0%';
document.getElementById('progressModal').classList.add('active');
setTimeout(()=>{document.getElementById('progressFill').style.width='40%';},200);
setTimeout(()=>{document.getElementById('progressFill').style.width='70%';},800);
}
hideProgress(){
document.getElementById('progressFill').style.width='100%';
setTimeout(()=>{document.getElementById('progressModal').classList.remove('active');},300);
}
showResult(title,message,downloadUrl){
this.hideProgress();
document.getElementById('resultTitle').textContent=title;
document.getElementById('resultMessage').textContent=message;
const actions=document.getElementById('resultActions');
actions.innerHTML=`<a href="${downloadUrl}" class="btn btn-primary" download>Download</a><button class="btn btn-secondary" id="closeResultBtn2">Close</button>`;
document.getElementById('closeResultBtn2').addEventListener('click',()=>{document.getElementById('resultModal').classList.remove('active');});
document.getElementById('resultModal').classList.add('active');
}
showResultMulti(title,message,files){
this.hideProgress();
document.getElementById('resultTitle').textContent=title;
document.getElementById('resultMessage').textContent=message;
const actions=document.getElementById('resultActions');
actions.innerHTML=files.map((f,i)=>`<a href="${f.download_url}" class="btn btn-primary" download>Download Part ${f.part}</a>`).join('')+`<button class="btn btn-secondary" id="closeResultBtn2">Close</button>`;
document.getElementById('closeResultBtn2').addEventListener('click',()=>{document.getElementById('resultModal').classList.remove('active');});
document.getElementById('resultModal').classList.add('active');
}
showExtractResult(data){
this.hideProgress();
const preview=document.getElementById('extractPreview');
if(data.image_count===0){preview.innerHTML='<div class="extract-placeholder"><p>No images found in this PDF.</p></div>';return;}
preview.innerHTML='<div class="extract-grid" id="extractGrid"></div>';
const grid=document.getElementById('extractGrid');
data.images.forEach(img=>{const link=document.createElement('a');link.href=img.download_url;link.download=img.filename;const imgEl=document.createElement('img');imgEl.src=img.download_url;imgEl.alt=img.filename;link.appendChild(imgEl);grid.appendChild(link);});
document.getElementById('resultTitle').textContent='Images Extracted!';
document.getElementById('resultMessage').textContent=`Found ${data.image_count} image(s). Click any image to download.`;
document.getElementById('resultActions').innerHTML='<button class="btn btn-secondary" id="closeResultBtn2">Close</button>';
document.getElementById('closeResultBtn2').addEventListener('click',()=>{document.getElementById('resultModal').classList.remove('active');});
document.getElementById('resultModal').classList.add('active');
}
reset(){
if(this.currentFileId){fetch(`${this.apiBase}/api/cleanup/${this.currentFileId}`,{method:'DELETE'});}
this.currentFileId=null;this.currentFilename='';this.totalPages=0;this.currentPage=0;this.zoom=100;
document.getElementById('uploadSection').style.display='flex';
document.getElementById('editorSection').style.display='none';
document.getElementById('fileInput').value='';
document.getElementById('pageView').innerHTML='<div class="placeholder-text">Upload a PDF to preview</div>';
document.getElementById('textPreviewContent').innerHTML='';
document.getElementById('zoomLevel').textContent='100%';
document.getElementById('pageView').style.transform='scale(1)';
document.getElementById('originalSize').textContent='--';
document.getElementById('compressedSize').textContent='--';
document.getElementById('savedPercent').textContent='--';
document.getElementById('extractPreview').innerHTML='<div class="extract-placeholder"><svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg><p>Images will appear here after extraction</p></div>';
}
formatBytes(bytes){
if(bytes===0)return'0 B';
const k=1024;
const sizes=['B','KB','MB','GB'];
const i=Math.floor(Math.log(bytes)/Math.log(k));
return parseFloat((bytes/Math.pow(k,i)).toFixed(2))+' '+sizes[i];
}
}
document.addEventListener('DOMContentLoaded',()=>{window.app=new PDFAlchemyApp();});
