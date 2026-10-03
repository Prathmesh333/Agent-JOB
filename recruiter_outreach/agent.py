"""Offline recruiter outreach: no scraping, auto-DMs or credentials."""
import argparse, csv, hashlib, json, re, sqlite3
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

DDL = '''CREATE TABLE IF NOT EXISTS leads (
 id INTEGER PRIMARY KEY, fingerprint TEXT UNIQUE, name TEXT, company TEXT, title TEXT,
 url TEXT, role TEXT, evidence TEXT, score INTEGER, draft TEXT DEFAULT '',
 state TEXT DEFAULT 'new', last_contact TEXT, followups INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS events (lead_id INTEGER, day TEXT, action TEXT);'''

def connect(path):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path);db.row_factory=sqlite3.Row;db.executescript(DDL)
    return db

def canonical(url):
    p=urlparse(url.strip())
    if p.scheme!='https' or p.hostname not in ('linkedin.com','www.linkedin.com') or not re.fullmatch(r'/in/[\w%-]+/?',p.path):
        raise ValueError('Expected an HTTPS public linkedin.com/in/profile URL')
    return 'https://www.linkedin.com'+p.path.rstrip('/')

def import_leads(db,path):
    counts={'added':0,'duplicate':0,'invalid':0}
    with open(path,newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f)
        if not {'name','company','title','profile_url','role','evidence'}<=set(reader.fieldnames or []):
            raise ValueError('CSV needs name,company,title,profile_url,role,evidence')
        for r in reader:
            try:
                if any(not r[k].strip() for k in ('name','company','title','role','evidence')): raise ValueError('empty field')
                url=canonical(r['profile_url'])
                fingerprint=hashlib.sha256(url.lower().encode()).hexdigest()
                title=r['title'].lower(); evidence=r['evidence'].lower()
                score=25*any(s in title for s in ('recruit','talent','hiring')) + 30*any(s in evidence for s in ('ai','machine learning','genai','backend','software'))+20*bool(r['role'].strip())
                cur=db.execute('INSERT OR IGNORE INTO leads(fingerprint,name,company,title,url,role,evidence,score) VALUES(?,?,?,?,?,?,?,?)',
                    (fingerprint,r['name'].strip(),r['company'].strip(),r['title'].strip(),url,r['role'].strip(),r['evidence'].strip(),score))
                counts['added' if cur.rowcount else 'duplicate']+=1
            except (ValueError,KeyError):counts['invalid']+=1
    db.commit();return counts

def row(db,id):
    r=db.execute('SELECT * FROM leads WHERE id=?',(id,)).fetchone()
    if not r:raise ValueError('Unknown lead')
    return r

def log(db,id,action): db.execute('INSERT INTO events VALUES(?,?,?)',(id,date.today().isoformat(),action))

def draft(db,id,profile):
    r=row(db,id)
    if r['state'] not in ('new','drafted'):raise ValueError('Cannot overwrite a sent/approved outreach')
    for key in ('name','intro','proof'):
        if not profile.get(key) or not isinstance(profile[key],str):raise ValueError('Profile missing '+key)
    msg=(f"Hi {r['name'].split()[0]}, I noticed your work in recruiting at {r['company']}. "
         f"I'm interested in {r['role']} roles. {profile['intro']} {profile['proof']} "
         f"Would you be open to connecting if your team has a relevant opening? Thanks, {profile['name']}")
    if len(msg)>1100:raise ValueError('Draft too long')
    db.execute("UPDATE leads SET draft=?,state='drafted' WHERE id=?",(msg,id));log(db,id,'drafted');db.commit()
    return msg

def transition(db,id,action):
    r=row(db,id);current=r['state']
    required={'approve':'drafted','sent':'approved','replied':'sent','closed':'sent'}
    if action in required:
        if current!=required[action]:raise ValueError(f'{action} requires {required[action]} state')
        updates={'approve':("state='approved'",()),'sent':("state='sent',last_contact=?",(date.today().isoformat(),)),
                 'replied':("state='replied'",()),'closed':("state='closed'",())}
        clause,params=updates[action];db.execute(f'UPDATE leads SET {clause} WHERE id=?',(*params,id))
    elif action=='followup':
        if current!='sent' or r['followups']>=2 or not r['last_contact'] or (date.today()-date.fromisoformat(r['last_contact'])).days<7:
            raise ValueError('Requires sent state, >=7 days quiet and fewer than 2 follow-ups')
        db.execute('UPDATE leads SET followups=followups+1,last_contact=? WHERE id=?',(date.today().isoformat(),id))
    else:raise ValueError('Unknown action')
    log(db,id,action);db.commit()

def due(db,days=10):
    return [dict(r) for r in db.execute("SELECT * FROM leads WHERE state='sent' AND followups<2 AND last_contact IS NOT NULL")
            if (date.today()-date.fromisoformat(r['last_contact'])).days>=days]

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',default='.local/outreach.db')
    sub=p.add_subparsers(dest='cmd',required=True)
    a=sub.add_parser('import');a.add_argument('csv')
    sub.add_parser('list');a=sub.add_parser('draft');a.add_argument('id',type=int);a.add_argument('--profile',required=True)
    for action in ('approve','sent','replied','closed','followup','show'):
        a=sub.add_parser(action);a.add_argument('id',type=int)
    a=sub.add_parser('due');a.add_argument('--days',type=int,default=10)
    args=p.parse_args(argv)
    with connect(args.db) as db:
        try:
            if args.cmd=='import':print(import_leads(db,args.csv))
            elif args.cmd=='list':
                for r in db.execute('SELECT id,name,company,role,score,state FROM leads ORDER BY score DESC,id'):print(dict(r))
            elif args.cmd=='draft':print(draft(db,args.id,json.loads(Path(args.profile).read_text(encoding='utf-8'))))
            elif args.cmd=='due':print(json.dumps(due(db,args.days),indent=2))
            elif args.cmd=='show':print(json.dumps(dict(row(db,args.id)),indent=2))
            else:transition(db,args.id,args.cmd);print('Local state recorded. No LinkedIn action was performed.')
        except (ValueError,OSError) as e:p.exit(2,'Error: '+str(e)+'\n')
if __name__=='__main__':main()
