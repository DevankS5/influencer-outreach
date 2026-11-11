"""At-most-one attempt per campaign/contact/mode. SMTP ambiguity is never retried automatically."""
import json
import os
import smtplib
import ssl
import uuid
from email.message import EmailMessage
from .db import connect, now, profiles, messages, event
from .config import brand
from .enrichment import valid_email


def approve(profile_id, campaign, approved=True):
    with connect() as c:
        row=c.execute('SELECT data FROM profiles WHERE id=?',(profile_id,)).fetchone()
        if not row: raise ValueError('Unknown profile')
        if approved and json.loads(row['data']).get('filter_status')!='passed': raise ValueError('Only qualified profiles may be approved')
        n=c.execute('UPDATE messages SET approved=? WHERE profile_id=? AND campaign_id=?',(int(approved),profile_id,campaign)).rowcount
        if not n: raise ValueError('Generate a message before reviewing it')
    event('review',f'{profile_id} campaign={campaign} approved={approved}')


def smtp_settings():
    if os.getenv('LIVE_SEND_ENABLED')!='yes': raise ValueError('Set LIVE_SEND_ENABLED=yes after compliance review')
    config={k:os.getenv('SMTP_'+k,'') for k in ('HOST','USERNAME','PASSWORD','FROM')}
    if not all(config.values()) or not valid_email(config['FROM']): raise ValueError('Configure all SMTP fields and a valid sender')
    if brand()['name']=='Your Brand': raise ValueError('Configure real campaign brand before live sending')
    port=int(os.getenv('SMTP_PORT','587'))
    if port not in (465,587): raise ValueError('Only TLS SMTP ports 465 and 587 are supported')
    config['PORT']=port
    return config


def send(campaign, live=False, profile_id=None):
    settings=smtp_settings() if live else None
    mode='live' if live else 'simulation'; by_id={m['profile_id']:m for m in messages(campaign)}
    results=[]
    for p in profiles():
        if profile_id and p['id']!=profile_id: continue
        m=by_id.get(p['id']); address=p.get('email','')
        if p.get('filter_status')!='passed' or not m or not m['approved'] or not valid_email(address): continue
        address=address.lower()
        message_id='<'+str(uuid.uuid4())+'@outreach.local>'
        # One atomic INSERT is the reservation. Unique constraints protect parallel workers.
        with connect() as c:
            if c.execute('SELECT 1 FROM suppressions WHERE email=?',(address,)).fetchone():
                results.append({'profile_id':p['id'],'status':'suppressed'}); continue
            cur=c.execute('''INSERT OR IGNORE INTO deliveries(profile_id,campaign_id,email,mode,status,message_id,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?)''',(p['id'],campaign,address,mode,'sending' if live else 'simulated',message_id,now(),now()))
            if not cur.rowcount:
                results.append({'profile_id':p['id'],'status':'duplicate_skipped'}); continue
            delivery_id=cur.lastrowid
        status='simulated'; detail='No network delivery. Manual Instagram DM only.'
        if live:
            email=EmailMessage(); email['From']=settings['FROM']; email['To']=address
            email['Subject']=m['subject']; email['Message-ID']=message_id
            email.set_content(m['email_body']+'\n\nIf you prefer not to receive collaboration enquiries, reply to opt out. We will not follow up.\n')
            try:
                if settings['PORT']==465:
                    server=smtplib.SMTP_SSL(settings['HOST'],465,timeout=30,context=ssl.create_default_context())
                else:
                    server=smtplib.SMTP(settings['HOST'],587,timeout=30)
                with server:
                    if settings['PORT']==587: server.ehlo(); server.starttls(context=ssl.create_default_context()); server.ehlo()
                    server.login(settings['USERNAME'],settings['PASSWORD'])
                    refused=server.send_message(email)
                    if refused: raise smtplib.SMTPException('Recipient refused')
                status='sent'; detail='SMTP server accepted message; not proof of inbox delivery.'
            except Exception as e:
                status='unknown'; detail=f'{type(e).__name__}; inspect provider logs before any manual retry. No automatic retry.'
        with connect() as c:
            c.execute('UPDATE deliveries SET status=?,detail=?,updated_at=? WHERE id=?',(status,detail,now(),delivery_id))
        results.append({'profile_id':p['id'],'status':status})
    return results


def suppress(address, reason='Opt-out'):
    if not valid_email(address): raise ValueError('Invalid suppression email')
    with connect() as c:
        c.execute('INSERT OR REPLACE INTO suppressions VALUES(?,?,?)',(address.lower(),reason,now()))
    event('suppressed',address.lower())
