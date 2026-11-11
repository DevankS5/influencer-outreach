import csv
import json
from pathlib import Path
from .db import profiles, messages, connect, now


def csv_file(path, fields, rows):
    with open(path,'w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); writer.writeheader()
        for row in rows:
            safe={}
            for k in fields:
                value=row.get(k)
                if isinstance(value,(dict,list)): value=json.dumps(value,ensure_ascii=False)
                if value is None: value='Not Available'
                if isinstance(value,str) and value.lstrip().startswith(('=','+','-','@')): value="'"+value
                safe[k]=value
            writer.writerow(safe)

def export(campaign, directory):
    root=Path(directory); root.mkdir(parents=True,exist_ok=True)
    ps=profiles(); ms=messages(campaign); mmap={m['profile_id']:m for m in ms}
    fields=['id','name','platform','profile_url','followers','engagement_rate','engagement_method','engagement_sample_size',
        'engagement_window','category','content_themes','email','email_source','website','audience_age','audience_gender','audience_geography',
        'filter_status','filter_reasons','brand_fit','observed_at','data_source','data_warnings']
    csv_file(root/'influencers.csv',fields,ps)
    csv_file(root/'messages.csv',['name','profile_id','campaign_id','subject','email_body','dm','generator','approved','created_at'],
             [dict(m,name=next((p['name'] for p in ps if p['id']==m['profile_id']),'')) for m in ms])
    with connect() as c:
        deliveries=[dict(r) for r in c.execute('SELECT * FROM deliveries WHERE campaign_id=?',(campaign,))]
        events=[dict(r) for r in c.execute('SELECT * FROM events ORDER BY id')]
    tracker=[]
    for p in ps:
        ds=[d for d in deliveries if d['profile_id']==p['id']]
        for d in ds or [{}]:
            tracker.append({'influencer':p['name'],'profile_id':p['id'],'email':p['email'],'message_generated':p['id'] in mmap,
                'approved':bool(mmap.get(p['id'],{}).get('approved')),'sent':d.get('status')=='sent',
                'date':d.get('created_at',''),'mode':d.get('mode',''),'status':d.get('status','not_contactable' if p['email']=='Not Found' else 'pending_review'),
                'detail':d.get('detail',''),'message_id':d.get('message_id','')})
    csv_file(root/'outreach_tracker.csv',['influencer','profile_id','email','message_generated','approved','sent','date','mode','status','detail','message_id'],tracker)
    (root/'profiles.json').write_text(json.dumps(ps,ensure_ascii=False,indent=2),encoding='utf-8')
    (root/'events.json').write_text(json.dumps(events,indent=2),encoding='utf-8')
    summary={'exported_at':now(),'campaign_id':campaign,'discovered':len(ps),'passed':sum(p.get('filter_status')=='passed' for p in ps),
             'with_public_email':sum(p['email']!='Not Found' for p in ps),'messages':len(ms),'deliveries':len(deliveries),
             'generators':sorted(set(m['generator'] for m in ms)), 'warning':'Public metrics are observations, not verified reach. Missing demographics are unknown. Offline generators are not LLM output.'}
    (root/'run_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    return summary
