import re

THEMES = {
 'AI and machine learning': ['artificial intelligence','machine learning','llm','generative ai','neural','ai'],
 'Software development': ['software','developer','programming','python','javascript','coding','programmer','open source','github','rust','typescript'],
 'Technology education': ['technology','tech','computer','computing','tutorial','linux','engineering'],
 'Cybersecurity': ['cybersecurity','infosec','security research','privacy','hacking'],
 'Gadgets and reviews': ['gadgets','smartphone','hardware','tech reviews','electronics'],
}

def classify(p, min_followers=5000, max_followers=100000, min_engagement=0.1, min_posts=3, geography=None):
    # Use exact word boundaries; "ai" must not match "chair".
    bio=p.get('bio','')
    posts=p.get('recent_posts',[])
    evidence_bio=re.sub(r'(?:no|anti|🚫)\s*(?:generative\s+)?ai(?:\s*/\s*nft)?', '', bio, flags=re.I)
    text=evidence_bio+' '+ ' '.join(x.get('text','') for x in posts)
    hits={theme: [w for w in words if re.search(r'(?<!\w)'+re.escape(w)+r'(?!\w)', text,re.I)] for theme,words in THEMES.items()}
    themes=[k for k,v in hits.items() if v]
    # Require evidence in the bio OR at least two original content items.
    pattern=r'(?<!\w)(?:'+ '|'.join(re.escape(w) for words in THEMES.values() for w in words)+r')(?!\w)'
    relevant=sum(bool(re.search(pattern,x.get('text',''),re.I)) for x in posts)
    bio_relevant=bool(re.search(pattern,evidence_bio,re.I))
    technical_role=bool(re.search(r'\b(developer|programmer|software|engineer|cybersecurity|infosec|machine learning|ai researcher|tech reviewer|technology educator|gadgets)\b', evidence_bio,re.I))
    content_ratio=relevant / len(posts) if posts else 0
    reasons=[]
    organization = re.search(r'\b(university|institute|foundation|society|museum|school|journal|center for|centre for|technology review|google for developers|developerbot)\b', p.get('name',''), re.I)
    if organization: reasons.append('Institutional or organizational account, not an individual creator')
    if re.search(r'\b(nsfw|pornography|sex tech)\b', bio+' '+p.get('name',''), re.I): reasons.append('Excluded brand-fit topic: adult content')
    f=p.get('followers'); er=p.get('engagement_rate')
    if f is None: reasons.append('Follower count unavailable')
    elif not min_followers <= f <= max_followers: reasons.append(f'Follower count {f} outside {min_followers}–{max_followers}')
    if not themes or not ((bio_relevant and technical_role) or (relevant>=3 and content_ratio>=0.25)): reasons.append('Insufficient technology niche evidence (technical bio or ≥3 posts and ≥25% relevant content)')
    if '[bridged from' in bio.lower(): reasons.append('Mirrored/bridged account excluded to reduce duplicate creator identities')
    if er is None: reasons.append('Engagement rate unavailable')
    elif er < min_engagement: reasons.append(f'Observed engagement {er}% below {min_engagement}%')
    if p.get('engagement_sample_size',0)<min_posts: reasons.append(f'Fewer than {min_posts} usable original posts')
    if geography and p.get('audience_geography') != geography: reasons.append('Requested audience geography unknown or not matched')
    p.update({'category':'Technology' if themes else 'Unclassified','content_themes':themes,
        'classification_evidence':hits,'relevant_post_count':relevant,'content_relevance_ratio':round(content_ratio,3),
        'brand_fit': 'Technology educational content; human brand-safety review required',
        'filter_status':'failed' if reasons else 'passed',
        'filter_reasons': reasons or ['Technology niche, micro audience, usable engagement sample and minimum engagement matched'],
        'filter_policy':{'min_followers':min_followers,'max_followers':max_followers,'min_engagement_percent':min_engagement,'min_posts':min_posts,'audience_geography':geography},
        'audience_demographics_status':'Not available from public API; no inferred age, gender or geography'})
    return p
