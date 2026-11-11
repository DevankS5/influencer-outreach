import argparse
import json
import sys
from . import db
from .config import campaign_id, ROOT
from .discovery import bluesky, youtube
from .enrichment import enrich
from .filtering import classify
from .personalization import generate
from .sending import approve, send, suppress
from .exporting import export


def main():
    parser=argparse.ArgumentParser(description='Evidence-first influencer outreach pipeline')
    parser.add_argument('--campaign',default=campaign_id())
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('init')
    for name in ('discover','run'):
        p=sub.add_parser(name)
        p.add_argument('--provider',choices=['bluesky','youtube'],default='bluesky')
        p.add_argument('--limit',type=int,default=60)
        p.add_argument('--query',action='append',help='Repeat for multiple search terms')
        p.add_argument('--crawl-web',action='store_true',help='Opt-in public website email extraction, robots-aware')
        p.add_argument('--min-engagement',type=float,default=.1)
        p.add_argument('--geography',help='Require known audience geography; unknowns will fail')
        if name=='run': p.add_argument('--generator',choices=['offline','llm'],default='offline')
    p=sub.add_parser('generate'); p.add_argument('--generator',choices=['offline','llm'],default='offline'); p.add_argument('--overwrite',action='store_true')
    p=sub.add_parser('approve'); p.add_argument('--id',required=True); p.add_argument('--revoke',action='store_true')
    p=sub.add_parser('send'); p.add_argument('--live',action='store_true'); p.add_argument('--id')
    p=sub.add_parser('export'); p.add_argument('--output',default=str(ROOT/'data'/'export'))
    p=sub.add_parser('suppress'); p.add_argument('--email',required=True); p.add_argument('--reason',default='Opt-out')
    sub.add_parser('stats')
    sub.add_parser('serve')
    args=parser.parse_args(); db.init(); campaign=args.campaign
    if args.command in ('discover','run'):
        if not 1<=args.limit<=1000: parser.error('--limit must be 1–1000')
        provider=bluesky if args.provider=='bluesky' else youtube
        count=0
        for p in provider(args.limit,queries=args.query):
            p=classify(enrich(p,args.crawl_web),min_engagement=args.min_engagement,geography=args.geography)
            db.save_profile(p); count+=1
            print(f'{count}: {p["name"]} | {p["followers"]} | {p["filter_status"]}',flush=True)
        db.event('discovery_complete',f'provider={args.provider} requested={args.limit} fetched={count}')
        if count<args.limit: print(f'WARNING: source returned only {count}; broaden queries.',file=sys.stderr)
    if args.command in ('run','generate'):
        count=0
        for p in db.profiles():
            try: count+=int(generate(p,campaign,args.generator,getattr(args,'overwrite',False)))
            except ValueError as e: db.event('generation_error',f'{p["id"]}: {e}'); print(f'Generation skipped {p["name"]}: {e}',file=sys.stderr)
        print(f'Generated {count} new messages')
    if args.command=='suppress': suppress(args.email,args.reason)
    if args.command=='approve': approve(args.id,campaign,not args.revoke)
    if args.command=='send': print(json.dumps(send(campaign,args.live,args.id),indent=2))
    if args.command in ('export','stats','run'):
        result=export(campaign,getattr(args,'output',str(ROOT/'data'/'export')))
        print(json.dumps(result,indent=2))
    if args.command=='serve':
        from .server import serve
        serve(campaign)

if __name__=='__main__':
    try: main()
    except (ValueError, RuntimeError) as e: print(f'Error: {e}',file=sys.stderr); sys.exit(1)
