import sys, csv, json, re, ast
from pathlib import Path

_rx_ph = re.compile(r'(?<!\d)(?:\+?91[\-\s]?)?([6-9]\d{9})(?!\d)')
_rx_aa = re.compile(r'(?<!\d)(\d{12})(?!\d)')
_rx_pp = re.compile(r'\b([A-PR-WYZa-pr-wyz]\d{7})\b')
_rx_em = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
_rx_up = re.compile(r'([A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,64})')
_rx_ip = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
_rx_pi = re.compile(r'\b(\d{6})\b')

def _pjson(x):
    if x is None: return {}
    if isinstance(x, dict): return x
    x = str(x).strip()
    for fn in (lambda y: json.loads(y),
               lambda y: ast.literal_eval(y),
               lambda y: json.loads(y.replace("'", '"'))):
        try: return fn(x)
        except: pass
    return {}

def _mph(v):
    s = re.sub(r'\D','',str(v))
    if len(s)==10: return s[:2]+'X'*6+s[-2:]
    if len(s)>10: s=s[-10:]; return s[:2]+'X'*6+s[-2:]
    return 'X'*len(s)

def _maa(v):
    s = re.sub(r'\D','',str(v))
    return s[:4]+'X'*4+s[-4:] if len(s)==12 else 'X'*len(s)

def _mpp(v):
    v=str(v); 
    return v[0]+'X'*(len(v)-2)+v[-1] if len(v)>=3 else 'X'*len(v)

def _mem(v):
    v=str(v); m=_rx_em.search(v)
    if not m: return 'X@'+v.split('@')[-1] if '@' in v else 'X'
    loc,dom=v.split('@',1); 
    locm='X'*len(loc) if len(loc)<=2 else loc[0]+'X'*(max(1,len(loc)-2))+loc[-1]
    return locm+'@'+dom

def _mup(v):
    v=str(v)
    if '@' in v:
        l,d=v.split('@',1)
        lm='X'*len(l) if len(l)<=2 else l[0]+'X'*(len(l)-2)+l[-1]
        return lm+'@'+d
    d=re.sub(r'\D','',v)
    return _mph(d[-10:]) if len(d)>=10 else 'X'*len(v)

def _mip(v):
    p=str(v).split('.')
    return '.'.join(p[:3]+['X']) if len(p)==4 else 'X'*len(str(v))

def _isnm(v):
    if not v: return False
    return len([t for t in re.split(r'\s+',v.strip()) if t])>=2

def _mtxt(t):
    if not isinstance(t,str): return t
    t=_rx_ph.sub(lambda m:_mph(m.group(1)),t)
    t=_rx_aa.sub(lambda m:_maa(m.group(1)),t)
    t=_rx_pp.sub(lambda m:_mpp(m.group(1)),t)
    t=_rx_em.sub(lambda m:_mem(m.group(0)),t)
    t=_rx_up.sub(lambda m:_mup(m.group(1)),t)
    return t

def main(fin,fout):
    R,tot,cnt=[],0,{'s':0,'c':0,'t':0}
    with open(fin,newline='',encoding='utf-8') as f:
        rd=csv.DictReader(f)
        for r in rd:
            tot+=1; rid=r.get('record_id') or r.get('recordId') or str(tot)
            d=_pjson(r.get('Data_json') or r.get('data_json') or '')
            x=dict(d); sf=False; pii=False; cmb=0

            # phones
            ph=None
            for k in ('phone','contact','mobile','customer_phone'):
                if k in d and d[k]: ph=str(d[k]); break
            if not ph:
                m=_rx_ph.search(json.dumps(d))
                if m: ph=m.group(1)
            if ph and _rx_ph.search(ph):
                for k in ('phone','contact','mobile','customer_phone'):
                    if k in x and x[k]: x[k]=_mph(x[k])
                sf=True; cnt['s']+=1

            # aadhar
            aa=d.get('aadhar') or None
            if not aa:
                m=_rx_aa.search(json.dumps(d))
                if m: aa=m.group(1)
            if aa and _rx_aa.search(str(aa)):
                if 'aadhar' in x and x['aadhar']: x['aadhar']=_maa(x['aadhar'])
                sf=True; cnt['s']+=1

            # passport
            pp=d.get('passport') or None
            if not pp:
                m=_rx_pp.search(json.dumps(d))
                if m: pp=m.group(1)
            if pp and _rx_pp.search(str(pp)):
                if 'passport' in x and x['passport']: x['passport']=_mpp(x['passport'])
                sf=True; cnt['s']+=1

            # upi
            up=d.get('upi_id') or d.get('upi') or None
            if not up:
                m=_rx_up.search(json.dumps(d))
                if m: up=m.group(1)
            if up and _rx_up.search(str(up)):
                for k in ('upi_id','upi'):
                    if k in x and x[k]: x[k]=_mup(x[k])
                sf=True; cnt['s']+=1

            if sf: pii=True

            # names
            nm=None
            if 'name' in d and d['name']: nm=d['name']
            elif d.get('first_name') and d.get('last_name'): nm=str(d['first_name'])+' '+str(d['last_name'])
            if nm and _isnm(nm):
                cmb+=1
                prt=nm.split()
                prr=[p[0]+'X'*(len(p)-1) if len(p)>2 else p[0]+'X'*(max(0,len(p)-1)) for p in prt]
                if 'name' in x and x['name']: x['name']=' '.join(prr)
                if d.get('first_name') and d.get('last_name'):
                    x['first_name']=prr[0] if prr else x['first_name']
                    if len(prr)>1: x['last_name']=prr[-1]

            # email
            em=d.get('email')
            if not em:
                m=_rx_em.search(json.dumps(d))
                if m: em=m.group(0)
            if em and _rx_em.search(str(em)):
                cmb+=1
                if 'email' in x and x['email']: x['email']=_mem(x['email'])

            # addr
            ad,ct,pn=d.get('address') or '',d.get('city') or '',d.get('pin_code') or d.get('pin') or d.get('pincode') or ''
            ap=False
            if ad and isinstance(ad,str) and (',' in ad or any(t in ad.lower() for t in ['street','st','road','rd','lane','apt','flat','house'])): ap=True
            if pn and _rx_pi.search(str(pn)): ap=True
            if ap and (ct or pn):
                cmb+=1
                if 'address' in x and x['address']: x['address']='[REDACTED_ADDRESS]'
                if 'city' in x and x['city']: x['city']=x['city'][0]+'X'*(max(0,len(x['city'])-1))
                if 'pin_code' in x and x['pin_code']: x['pin_code']='X'*len(str(x['pin_code']))

            # device/ip
            dv,ip=d.get('device_id') or d.get('device'), d.get('ip_address')
            if (dv and str(dv).strip()) or (ip and _rx_ip.search(str(ip))):
                cmb+=1
                if 'device_id' in x and x['device_id']: x['device_id']='[REDACTED_DEVICE]'
                if 'ip_address' in x and x['ip_address']: x['ip_address']=_mip(x['ip_address'])

            if cmb>=2: pii=True; cnt['c']+=1
            if pii: cnt['t']+=1

            for k,v in list(x.items()):
                if isinstance(v,str): x[k]=_mtxt(v)

            R.append({'record_id':rid,'redacted_data_json':json.dumps(x,ensure_ascii=False),'is_pii':str(bool(pii))})

    with open(fout,'w',newline='',encoding='utf-8') as fo:
        w=csv.DictWriter(fo,fieldnames=['record_id','redacted_data_json','is_pii'])
        w.writeheader(); [w.writerow(z) for z in R]
    print('Processed',tot,'rows. PII detected:',cnt['t'])

if __name__=='__main__':
    i=sys.argv[1] if len(sys.argv)>1 else 'iscp_pii_dataset.csv'
    o='redacted_output_candidate_full_name.csv'
    main(i,o)

