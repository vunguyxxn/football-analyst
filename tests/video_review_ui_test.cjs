// Offline handler tests with a small DOM double; no browser/network/download.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const template = fs.readFileSync(process.argv[2], 'utf8');
const source = template.split('<script>')[1].split('</script>')[0];
const input = {version:1,packet_id:'qa_packet',reviewer:'',plan:{image_size:[1280,720],fps:60,
  landmarks:[{id:'mid_far',label:'midpoint',pitch_xy:[52.5,68]}]},clips:[],
  frames:[1105,1145].map(frame=>({clip:'return',label:'test',clean_frame:frame,raw_frame:frame+600,
    time_s:frame/60,raw_time_s:(frame+600)/60,image:'not-loaded.png',reviewed:false,annotations:[]}))};
const elements = new Map(), downloads = [], blobs = [];
function element(){return {value:'',textContent:'',children:[],checked:false,style:{},
  append(child){this.children.push(child);},replaceChildren(){this.children=[];},
  click(){downloads.push({name:this.download,url:this.href});},
  getBoundingClientRect(){return {left:100,top:50,width:640,height:360};},
  getContext(){return new Proxy({}, {get:()=>()=>{},set:()=>true});}};}
const get=id=>{if(!elements.has(id))elements.set(id,element());return elements.get(id);};
get('packet').textContent=JSON.stringify(input);
Object.entries({kind:'player',team:'A',visibility:'visible',landmark:'mid_far'}).forEach(([key,value])=>get(key).value=value);
const stored=new Map();
const context=vm.createContext({document:{getElementById:get,createElement:element},structuredClone,Blob,
  Image:class{constructor(){this.naturalWidth=1280;this.naturalHeight=720;}set src(value){this.onload();}},
  localStorage:{getItem:key=>stored.get(key),setItem:(key,value)=>stored.set(key,value)},
  URL:{createObjectURL:blob=>{blobs.push(blob);return 'mock:blob';},revokeObjectURL(){}},
  setTimeout:fn=>fn()});
vm.runInContext(source,context);
const state=()=>JSON.parse(vm.runInContext('JSON.stringify(packet)',context));
(async()=>{
  assert.equal(state().frames[0].annotations.length,0);
  get('add').onclick();assert.match(get('status').textContent,/Bấm lên ảnh/);
  get('reviewer').value='QA';get('entity').value='A01';get('note').value='=HYPERLINK("test")';
  get('canvas').onclick({clientX:420,clientY:230});get('add').onclick();
  let point=state().frames[0].annotations[0];
  assert.equal(point.image_x_px,640);assert.equal(point.image_y_px,360);
  assert.equal(point.pitch_x_m,null);assert.equal(point.entity_id,'A01');
  get('canvas').onclick({clientX:425,clientY:235});get('add').onclick();
  assert.equal(state().frames[0].annotations.length,1); // duplicate is refused
  get('reviewed').checked=true;get('reviewed').onchange();get('exportJson').onclick();
  const exported=JSON.parse(await blobs[0].text());
  assert.equal(exported.reviewer,'QA');assert.equal(exported.frames[0].reviewed,true);
  assert.equal(exported.frames[1].reviewed,false);assert.equal(downloads[0].name,'annotations_review.json');
  get('exportCsv').onclick();assert.match(await blobs[1].text(),/'=HYPERLINK/);
  get('kind').value='landmark';get('kind').onchange();
  assert.equal(get('markLabel').hidden,false);assert.equal(get('personLabel').hidden,true);
  get('canvas').onclick({clientX:200,clientY:150});get('add').onclick();
  point=state().frames[0].annotations[1];assert.equal(point.pitch_x_m,52.5);assert.equal(point.pitch_y_m,68);
  assert.equal(state().frames[0].reviewed,false); // edits require review again
  get('next').onclick();assert.equal(state().frames[1].annotations.length,0);
  get('prev').onclick();assert.equal(state().frames[0].annotations.length,2);
  const invalid=structuredClone(exported);invalid.packet_id='different';
  const file={files:[{text:async()=>JSON.stringify(invalid)}],value:'mock'};
  await get('importFile').onchange({target:file});assert.match(get('status').textContent,/bộ ảnh khác/);
  invalid.packet_id='qa_packet';invalid.frames[0].annotations[0].image_x_px=99999;
  await get('importFile').onchange({target:file});assert.match(get('status').textContent,/Pixel ngoài ảnh/);
  file.files=[{text:async()=>JSON.stringify(exported)}];
  await get('importFile').onchange({target:file});assert.equal(state().frames[0].annotations.length,1);
  assert.equal(state().frames[0].reviewed,true);
  assert.equal(JSON.parse([...stored.values()][0]).reviewer,'QA');
  console.log('offline UI: scaling, add/duplicate, landmarks, review state, export/import, persistence OK');
})().catch(error=>{console.error(error);process.exitCode=1;});
