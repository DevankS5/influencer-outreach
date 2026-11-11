"""Public Bluesky API and official YouTube Data API. No logged-in scraping."""
import os
import re
import time
from datetime import datetime, timezone
from .http import Client, APIError
from .db import now, event

BSKY = 'https://public.api.bsky.app/xrpc/'
TECH_QUERIES = ['developer', 'software', 'python', 'programmer', 'coding', 'cybersecurity', 'gadgets', 'open source', 'technology', 'AI', 'software engineer', 'devrel', 'javascript', 'simon willison', 'julia evans', 'wes bos', 'kent c dodds', 'sara vieira', 'josh comeau', 'addy osmani', 'sarah drasner', 'scott hanselman', 'troy hunt', 'scott helme', 'charlotte eleanor', 'sophie alpert']

def base_record(pid, platform, name, url, bio, followers):
    return {'id': pid, 'platform': platform, 'name': name, 'profile_url': url,
            'bio': bio, 'followers': followers, 'engagement_rate': None,
            'engagement_method': 'Not available', 'engagement_sample_size': 0,
            'recent_posts': [], 'email': 'Not Found', 'email_source': None,
            'website': None, 'audience_age': None, 'audience_gender': None,
            'audience_geography': None, 'observed_at': now(),
            'data_source': url, 'data_warnings': []}

def bluesky(limit=60, queries=None, feed_limit=12):
    client = Client(); actors = {}; queries = queries or TECH_QUERIES
    for query in queries:
        cursor = None
        for page in range(1 if limit <= 100 else 2):
            params = {'q': query, 'limit': 50}
            if cursor: params['cursor'] = cursor
            data = client.get(BSKY + 'app.bsky.actor.searchActors', params)
            for a in data.get('actors', []): actors[a['did']] = a
            cursor = data.get('cursor')
            if not cursor: break
    # Search results omit follower counts. Fetch the authoritative profile endpoint in batches.
    full = []
    ids = list(actors)
    for i in range(0, len(ids), 25):
        data = client.get(BSKY + 'app.bsky.actor.getProfiles', [('actors', did) for did in ids[i:i+25]])
        full.extend(data.get('profiles', []))
    # Retain a few failed examples for an auditable filter demonstration.
    full.sort(key=lambda a: (not (5000 <= a.get('followersCount', 0) <= 100000),
        not bool(re.search(r'[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}', a.get('description',''))),
        not bool(re.search(r'\b(developer|engineer|programmer|researcher|creator)\b', a.get('description',''), re.I)), a.get('handle', '')))
    for a in full[:limit]:
        p = base_record(a['did'], 'Bluesky', a.get('displayName') or a['handle'],
                        'https://bsky.app/profile/' + a['handle'], a.get('description', ''), a.get('followersCount'))
        p['handle'] = a['handle']; p['profile_api_url'] = BSKY + 'app.bsky.actor.getProfile?actor=' + a['did']
        try:
            feed = client.get(BSKY + 'app.bsky.feed.getAuthorFeed',
                              {'actor': a['did'], 'limit': min(100, feed_limit * 3), 'filter': 'posts_no_replies'})
            for item in feed.get('feed', []):
                post = item.get('post', {})
                if post.get('author', {}).get('did') != a['did']: continue
                record = post.get('record', {})
                # Filter reposts, replies, and pinned entries; duplicates cannot inflate the metric.
                if record.get('reply') or item.get('reason'): continue
                uri = post.get('uri', '')
                if any(x['uri'] == uri for x in p['recent_posts']): continue
                p['recent_posts'].append({'uri': uri, 'text': record.get('text', ''),
                    'url': p['profile_url'] + '/post/' + uri.rsplit('/', 1)[-1],
                    'published_at': record.get('createdAt'), 'likes': post.get('likeCount', 0),
                    'comments': post.get('replyCount', 0), 'reposts': post.get('repostCount', 0)})
                if len(p['recent_posts']) >= feed_limit: break
            n = len(p['recent_posts'])
            if n and p['followers']:
                p['engagement_rate'] = round(100 * sum(x['likes'] + x['comments'] + x['reposts'] for x in p['recent_posts']) / n / p['followers'], 4)
                p['engagement_sample_size'] = n
                p['engagement_method'] = 'Bluesky public interactions per original post / current followers × 100; observed sample, not audience reach'
                dates = [x['published_at'] for x in p['recent_posts'] if x['published_at']]
                p['engagement_window'] = {'oldest': min(dates) if dates else None, 'newest': max(dates) if dates else None}
        except APIError as e:
            p['data_warnings'].append(str(e)); event('feed_error', p['id'])
        yield p
        time.sleep(0.08)

def youtube(limit=60, queries=None, feed_limit=12):
    key = os.getenv('YOUTUBE_API_KEY')
    if not key: raise ValueError('Set YOUTUBE_API_KEY to use official YouTube discovery.')
    client = Client(); root = 'https://www.googleapis.com/youtube/v3/'; ids = []
    for q in queries or ['technology tutorials', 'software developer', 'tech reviews']:
        token = None
        for _ in range(3):
            params = {'key': key, 'part': 'snippet', 'type': 'channel', 'q': q, 'maxResults': 50}
            if token: params['pageToken'] = token
            d = client.get(root + 'search', params)
            for x in d.get('items', []):
                cid = x['id']['channelId']
                if cid not in ids: ids.append(cid)
            token = d.get('nextPageToken')
            if len(ids) >= limit or not token: break
        if len(ids) >= limit: break
    for start in range(0, min(len(ids), limit), 50):
        channels = client.get(root + 'channels', {'key': key, 'part': 'snippet,statistics,contentDetails', 'id': ','.join(ids[start:start+50])})
        for ch in channels.get('items', []):
            stats = ch['statistics']; snip = ch['snippet']; cid = ch['id']
            count = None if stats.get('hiddenSubscriberCount') else int(stats.get('subscriberCount', 0))
            p = base_record('youtube:' + cid, 'YouTube', snip['title'], 'https://www.youtube.com/channel/' + cid, snip.get('description', ''), count)
            p['creator_country'] = snip.get('country')  # NOT audience geography
            playlist = ch.get('contentDetails', {}).get('relatedPlaylists', {}).get('uploads')
            try:
                items = client.get(root + 'playlistItems', {'key': key, 'part': 'snippet', 'playlistId': playlist, 'maxResults': min(feed_limit,50)}) if playlist else {}
                vids = [x['snippet']['resourceId']['videoId'] for x in items.get('items', [])]
                videos = client.get(root + 'videos', {'key': key, 'part': 'snippet,statistics', 'id': ','.join(vids)}) if vids else {}
                for v in videos.get('items', []):
                    s = v.get('statistics', {}); sn = v['snippet']
                    p['recent_posts'].append({'uri': v['id'], 'url': 'https://www.youtube.com/watch?v=' + v['id'], 'text': sn['title'] + '\n' + sn.get('description', ''), 'published_at': sn.get('publishedAt'),
                        'likes': int(s['likeCount']) if 'likeCount' in s else None, 'comments': int(s['commentCount']) if 'commentCount' in s else None, 'views': int(s.get('viewCount', 0))})
                usable = [v for v in p['recent_posts'] if v['likes'] is not None and v['comments'] is not None]
                if usable and count:
                    p['engagement_rate'] = round(100 * sum(v['likes']+v['comments'] for v in usable)/len(usable)/count,4)
                    p['engagement_sample_size'] = len(usable)
                    p['engagement_method'] = 'YouTube average (public likes + comments) / current subscribers × 100; rounded subscriber counts; not view-based ER'
            except APIError as e: p['data_warnings'].append(str(e))
            yield p
