import test from "node:test"
import assert from "node:assert/strict"
import { COACH_FEATURES, coachTime, parseCoachReport } from "../src/lib/coachReport.ts"

function report() {
  const features=Object.fromEntries(COACH_FEATURES.map(k=>[k,0]));Object.assign(features,{distance_m:20,angle_rad:.3,lateral_m:3})
  const shots=Array.from({length:5},(_,i)=>{
    const xg=i<3?.04:.25,margin=Math.log(xg/(1-xg)),base=-2
    const shap=Object.fromEntries(COACH_FEATURES.map(k=>[k,0]));shap.distance_m=margin-base
    return {event_id:`s${i+1}`,event_index:i+1,team_id:1,player_id:7,player:"Player One",short_name:"One",period:1,minute:i+1,second:5,
      features:structuredClone(features),xg,margin,base_log_odds:base,shap_log_odds:shap}
  })
  const selected=shots.slice(0,3),sum=shots.reduce((n,s)=>n+s.xg,0)
  return {kind:"shot_advisor_v1",source:"statsbomb",timing:"post_match",match_id:10,
    model_audit:{method:"TreeExplainer/tree_path_dependent",units:"log_odds",trees_explained:2,best_iteration:1,model_sha256:"a".repeat(64)},
    protocol:{minimum_team_shots:5,minimum_subset_shots:3,low_xg_threshold:.08,high_xg_threshold:.2,low_xg_fraction:.5,high_xg_fraction:.25,pressure_fraction:.4},
    provenance:{model_dataset_split:"val"},limitations:["Chưa nghiệm thu hiệu quả chiến thuật"],shots,
    teams:[{team_id:1,team:"Team A",eligible_shots:5,xg_total:sum,mean_xg:sum/5,status:"review_suggestions",recommendations:[{
      id:"1:review_low_quality_shots",rule:"review_low_quality_shots",title:"Rà soát lựa chọn vị trí",action:"Xem lại cú sút",interpretation:"Không phải kết luận nhân quả",supporting_features:["distance_m"],
      evidence:{event_ids:selected.map(s=>s.event_id),subset_shots:3,team_shots:5,fraction:.6,mean_xg:.04,mean_features:structuredClone(features),mean_shap_log_odds:structuredClone(shots[0].shap_log_odds)}}]}]}
}

test("accepts consistent advisor JSON, preserves full export and traces exact shots",()=>{
  const raw=report(),parsed=parseCoachReport(JSON.stringify(raw))
  assert.equal(parsed.matchId,10);assert.equal(parsed.teams[0].shots.length,5)
  assert.deepEqual(parsed.teams[0].cards[0].shots.map(s=>s.id),["s1","s2","s3"])
  assert.equal(parsed.teams[0].cards[0].fraction,.6)
  assert.equal(parsed.trees,2);assert.equal(parsed.split,"val")
  assert.equal(coachTime(parsed.shots[0]),"1:05")
  assert.deepEqual(parseCoachReport(JSON.stringify(parsed.original)).original,raw)
  // Other two existing rules must also accept valid, reconstructable evidence.
  const other=report(),margin=Math.log(.25/.75)
  for(const shot of other.shots){shot.xg=.25;shot.margin=margin;shot.features.under_pressure=1;shot.shap_log_odds.under_pressure=-.1;shot.shap_log_odds.distance_m=margin-shot.base_log_odds+.1}
  const card=other.teams[0].recommendations[0]
  Object.assign(card.evidence,{event_ids:other.shots.map(s=>s.event_id),subset_shots:5,fraction:1,mean_xg:.25,mean_features:structuredClone(other.shots[0].features),mean_shap_log_odds:structuredClone(other.shots[0].shap_log_odds)})
  Object.assign(card,{id:"1:review_pressure_support",rule:"review_pressure_support",title:"Rà soát áp lực",supporting_features:["under_pressure"]})
  const high=structuredClone(card);Object.assign(high,{id:"1:review_good_entries",rule:"review_good_entries",title:"Rà soát cơ hội tốt",supporting_features:["distance_m"]})
  other.teams[0].recommendations.push(high);Object.assign(other.teams[0],{xg_total:1.25,mean_xg:.25})
  assert.deepEqual(parseCoachReport(JSON.stringify(other)).teams[0].cards.map(c=>c.rule),["review_pressure_support","review_good_entries"])
})

test("rejects false totals and broken probability/SHAP reconstruction",()=>{
  for(const modify of [r=>r.teams[0].xg_total=1,r=>r.teams[0].mean_xg=.8,r=>r.teams[0].eligible_shots=6,
    r=>r.shots[0].xg=.9,r=>r.shots[0].margin=0,r=>r.shots[0].shap_log_odds.distance_m=1,r=>r.model_audit.units="probability",r=>r.model_audit.trees_explained=3]){
    const raw=report();modify(raw);assert.throws(()=>parseCoachReport(JSON.stringify(raw)))
  }
})

test("rejects fabricated evidence averages, duplicate/missing IDs and wrong support",()=>{
  for(const modify of [c=>c.evidence.event_ids[0]="missing",c=>c.evidence.event_ids[0]="s2",c=>c.evidence.mean_xg=.2,
    c=>c.evidence.fraction=.99,c=>c.evidence.mean_features.distance_m=5,c=>c.evidence.mean_shap_log_odds.distance_m=0,
    c=>c.supporting_features=["angle_rad"],c=>c.rule="unknown"]){
    const raw=report();modify(raw.teams[0].recommendations[0]);assert.throws(()=>parseCoachReport(JSON.stringify(raw)))
  }
  const raw=report(),other=structuredClone(raw.shots[0]);other.event_id="other";other.event_index=10;other.team_id=2
  raw.shots.push(other);raw.teams.push({team_id:2,team:"Other",eligible_shots:1,xg_total:other.xg,mean_xg:other.xg,status:"insufficient_data",recommendations:[]})
  raw.teams[0].recommendations[0].evidence.event_ids[0]="other"
  assert.throws(()=>parseCoachReport(JSON.stringify(raw)),/khác đội/)
})

test("keeps empty report/insufficient-data states and rejects duplicate events",()=>{
  const empty=report();empty.shots=[];empty.teams=[]
  assert.equal(parseCoachReport(JSON.stringify(empty)).teams.length,0)
  const small=report();small.shots=small.shots.slice(0,1);Object.assign(small.teams[0],{eligible_shots:1,xg_total:.04,mean_xg:.04,status:"insufficient_data",recommendations:[]})
  assert.equal(parseCoachReport(JSON.stringify(small)).teams[0].cards.length,0)
  const malformed=report();malformed.shots[1].event_id="s1"
  assert.throws(()=>parseCoachReport(JSON.stringify(malformed)),/Trùng/)
  malformed.shots[1].event_id="s2";malformed.shots[1].period=5
  assert.throws(()=>parseCoachReport(JSON.stringify(malformed)))
  assert.throws(()=>parseCoachReport("not JSON"))
})
