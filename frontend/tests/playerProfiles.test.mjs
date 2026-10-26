import test from "node:test"
import assert from "node:assert/strict"
import { parsePlayerReport, filterPlayers, formatProfileMetric } from "../src/lib/playerProfiles.ts"

function eventReport() {
  return { kind:"statsbomb_player_profiles_v1", source:"statsbomb", match_id:10, players:[{match_id:10,player_id:1,player:"Nguyễn Văn A",short_name:"Văn A",team:"A",starter:true,jersey_number:7,
    passes_attempted:2,passes_completed:1,pass_completion_pct:50,carries:0,shots:0,shot_goals:0,recorded_player_events:2,
    event_indices:{Pass:[1,2],Carry:[],Shot:[]},role_contexts:[{status:"unknown",first_event_index:1,last_event_index:2,event_count:2}]}] }
}
function trackingReport() {
  return {kind:"offline_metrica_tactics_v1",game:1,period:1,start_s:60,stop_s:120,coordinate_system:"105x68_bottom_left",heatmap:{columns:21,rows:14,origin:"bottom_left",unit:"observed_frames"},motion_policy:{max_speed_kmh:40},teams:[{team:"A",players:[{
    track_id:1,team:"A",is_goalkeeper:false,samples:0,sample_coverage:0,represented_motion_duration_s:0,represented_window_fraction:0,observed_distance_m:0,mean_speed_kmh:null,max_speed_kmh:null,rejected_motion_intervals:0,median_position_m:null,heatmap_observed_frames:Array.from({length:14},()=>Array(21).fill(0))}]}]}
}

test("StatsBomb keeps source, short names, ID identity and nullable outcomes",()=>{
  const raw=eventReport(),other=structuredClone(raw.players[0]); other.player_id=2;other.team="B";other.event_indices.Pass=[3,4];other.role_contexts[0].first_event_index=3;other.role_contexts[0].last_event_index=4;raw.players.push(other)
  const report=parsePlayerReport(JSON.stringify(raw))
  assert.equal(report.players.length,2);assert.notEqual(report.players[0].key,report.players[1].key)
  assert.equal(report.players[0].shortName,"Văn A")
  assert.equal(filterPlayers(report,"A","nguyen").length,1)
  assert.equal(filterPlayers(report,"","missing").length,0)
  assert.equal(formatProfileMetric(null),"—");assert.equal(formatProfileMetric(0),"0")
  raw.players[0].passes_completed=null;raw.players[0].pass_completion_pct=null;raw.players[0].shot_goals=null
  const parsed=parsePlayerReport(JSON.stringify(raw));assert.equal(parsed.players[0].events.goals,null)
})

test("rejects mixed matches, duplicate identity/events and fabricated completion",()=>{
  for(const change of [r=>r.players.push(structuredClone(r.players[0])),r=>r.players[0].match_id=11,r=>r.players[0].pass_completion_pct=100,r=>r.players[0].passes_completed=3,r=>r.players[0].event_indices.Pass=[1,1],r=>r.players[0].shot_goals=1]){
    const raw=eventReport();change(raw);assert.throws(()=>parsePlayerReport(JSON.stringify(raw)))
  }
  assert.throws(()=>parsePlayerReport("not JSON"));assert.throws(()=>parsePlayerReport(JSON.stringify({kind:"video"})))
  const empty=eventReport();empty.players=[];assert.deepEqual(parsePlayerReport(JSON.stringify(empty)).players,[])
})

test("Metrica window and zero versus absent motion remain distinct",()=>{
  const raw=trackingReport(),report=parsePlayerReport(JSON.stringify(raw))
  assert.equal(report.source,"metrica");assert.match(report.scope,/60–120/)
  assert.equal(report.players[0].tracking.meanSpeed,null)
  assert.equal(report.players[0].events,null)
  const p=raw.teams[0].players[0];p.samples=1;p.sample_coverage=.1;p.heatmap_observed_frames[0][0]=1;p.median_position_m=[0,0];p.represented_motion_duration_s=1;p.represented_window_fraction=1/60;p.mean_speed_kmh=0;p.max_speed_kmh=0
  assert.equal(parsePlayerReport(JSON.stringify(raw)).players[0].tracking.meanSpeed,0)
  assert.notEqual(parsePlayerReport(JSON.stringify(raw)).players[0].key,parsePlayerReport(JSON.stringify(eventReport())).players[0].key)
})

test("rejects reversed coordinate systems, broken heatmaps and wrong motion coverage",()=>{
  for(const change of [r=>r.coordinate_system="120x80",r=>r.teams[0].players[0].heatmap_observed_frames[0][0]=1,r=>r.teams[0].players[0].represented_window_fraction=.8,r=>r.teams[0].players[0].max_speed_kmh=41,r=>r.teams[0].players[0].median_position_m=[106,0]]){
    const raw=trackingReport();change(raw);assert.throws(()=>parsePlayerReport(JSON.stringify(raw)))
  }
})
