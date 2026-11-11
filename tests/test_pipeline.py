"""All tests use explicit synthetic fixtures, never exported as discovered profiles."""
import copy
import json
from concurrent.futures import ThreadPoolExecutor
import pytest
from outreach import db
from outreach.discovery import base_record
from outreach.filtering import classify
from outreach.enrichment import enrich, extract_emails, valid_email, safe_url
from outreach.personalization import generate, offline_message, validate, word_count
from outreach.sending import approve, send, suppress
from outreach.exporting import export

@pytest.fixture(autouse=True)
def isolated(tmp_path,monkeypatch):
    monkeypatch.setenv('DATABASE_PATH',str(tmp_path/'test.sqlite3'))
    for k in ('LLM_API_KEY','SMTP_HOST','SMTP_PASSWORD','LIVE_SEND_ENABLED','BRAND_NAME','BRAND_DESCRIPTION','CAMPAIGN_OFFER'):
        monkeypatch.delenv(k,raising=False)
    db.init()

@pytest.fixture
def creator():
    p=base_record('fixture:synthetic','Bluesky','Test Creator','https://bsky.app/profile/fixture.invalid',
        'Synthetic software developer fixture. Contact: partnerships@fixture.invalid',12000)
    p.update(engagement_rate=1.5,engagement_sample_size=3,
        recent_posts=[{'uri':str(i),'text':'A Python tutorial for software developers','url':f'https://fixture.invalid/{i}',
            'likes':100,'comments':3,'reposts':1,'published_at':'2026-01-01T00:00:00Z'} for i in range(3)])
    return classify(enrich(p))

def prepared(creator):
    db.save_profile(creator); generate(creator,'test'); approve(creator['id'],'test')

def test_complete_flow(creator,tmp_path):
    prepared(creator)
    assert send('test')[0]['status']=='simulated'
    assert send('test')[0]['status']=='duplicate_skipped'
    s=export('test',tmp_path/'exports'); assert s['discovered']==1 and s['messages']==1
    assert 'simulated' in (tmp_path/'exports/outreach_tracker.csv').read_text()
    assert 'False' in (tmp_path/'exports/outreach_tracker.csv').read_text()

def test_passes_with_evidence(creator):
    assert creator['filter_status']=='passed'
    assert creator['email_source']==creator['profile_url']
    assert creator['audience_geography'] is None

@pytest.mark.parametrize('followers',[4999,100001,None])
def test_follower_failures(creator,followers):
    creator['followers']=followers
    assert classify(creator)['filter_status']=='failed'

@pytest.mark.parametrize('rate',[None,0,0.09])
def test_engagement_failure(creator,rate):
    creator['engagement_rate']=rate
    assert classify(creator)['filter_status']=='failed'

def test_missing_email_not_fabricated(creator):
    creator['bio']='Software developer'; creator['recent_posts']=[]
    assert enrich(creator)['email']=='Not Found'

def test_word_boundaries(creator):
    creator['bio']='Chair enthusiast'; creator['recent_posts']=[]
    assert classify(creator)['category']=='Unclassified'

def test_organization_exclusion(creator):
    creator['name']='Example University'
    assert classify(creator)['filter_status']=='failed'

def test_adult_brand_exclusion(creator):
    creator['bio']='software developer in sex tech'
    assert classify(creator)['filter_status']=='failed'

def test_missing_geography_is_not_inferred(creator):
    assert classify(creator,geography='IN')['filter_status']=='failed'

def test_message_lengths_and_variation(creator):
    m=offline_message(creator); assert 60<=word_count(m['email_body'])<=90 and 15<=word_count(m['dm'])<=30
    variants=[]
    for i in range(20):
        p=copy.deepcopy(creator);p['id']=str(i);variants.append(offline_message(p)['email_body'])
    assert len(set(variants))>=3

def test_validation_rejects_short_output():
    with pytest.raises(ValueError): validate({'subject':'Hi','email_body':'too short','dm':'also short'})

def test_no_approval_no_send(creator):
    db.save_profile(creator);generate(creator,'test');assert send('test')==[]

def test_missing_email_no_send(creator):
    creator['email']='Not Found';prepared(creator);assert send('test')==[]

def test_live_gated(creator):
    prepared(creator)
    with pytest.raises(ValueError): send('test',live=True)

def test_concurrent_idempotency(creator):
    prepared(creator)
    with ThreadPoolExecutor(max_workers=4) as pool: results=list(pool.map(lambda _:send('test'),range(4)))
    assert sum(r[0]['status']=='simulated' for r in results)==1

def test_email_dedup_across_profiles(creator):
    prepared(creator); other=copy.deepcopy(creator);other['id']='other';prepared(other)
    statuses=[r['status'] for r in send('test')]
    assert sorted(statuses)==['duplicate_skipped','simulated']

def test_suppression_blocks_send(creator):
    prepared(creator);suppress(creator['email']);assert send('test')[0]['status']=='suppressed'

def test_approval_reset_on_profile_change(creator):
    prepared(creator);creator['followers']=12001;db.save_profile(creator)
    assert db.messages('test')[0]['approved']==0

def test_regeneration_clears_approval(creator):
    prepared(creator);generate(creator,'test',overwrite=True)
    assert db.messages('test')[0]['approved']==0

def test_default_generate_keeps_existing(creator):
    prepared(creator);assert generate(creator,'test') is False
    assert db.messages('test')[0]['approved']==1

@pytest.mark.parametrize('address',['Not Found','foo@example.com','bad\n@real.org','missing-at.test','a@b'])
def test_invalid_emails(address): assert not valid_email(address)

def test_extract_literal_email_only():
    assert extract_emails('me [at] place [dot] com')==[]
    assert extract_emails('Contact hello@fixture.invalid today')==['hello@fixture.invalid']

@pytest.mark.parametrize('url',['http://127.0.0.1','http://169.254.169.254','file:///etc/passwd','https://a:b@google.com','http://localhost:22'])
def test_unsafe_urls_blocked(url):
    with pytest.raises((ValueError,OSError)): safe_url(url)

def test_csv_formula_escaped(tmp_path):
    from outreach.exporting import csv_file
    out=tmp_path/'file.csv';csv_file(out,['name'],[{'name':'=HYPERLINK("bad")'}])
    assert "'=HYPERLINK" in out.read_text(encoding='utf-8-sig')

def test_mocked_llm(creator,monkeypatch):
    from outreach.personalization import llm_message
    monkeypatch.setenv('LLM_API_KEY','test-key-not-real')
    m=offline_message(creator)
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'choices':[{'message':{'content':json.dumps(m)}}]}
    monkeypatch.setattr('outreach.personalization.requests.post',lambda *a,**kw:Response())
    assert llm_message(creator)==m

def test_failed_profile_no_message(creator):
    creator['filter_status']='failed';db.save_profile(creator)
    assert generate(creator,'test') is False
