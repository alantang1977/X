#!/usr/bin/env python3

import sys
import re
import json
import requests
import time

p=re.compile(r'.*/s/(.*)')
reqcount=1
sharedict=set()

def getlist(shareid, fileid):
    global reqcount
    global sharedict

    reqcount += 1
    if reqcount % 5 == 0:
        print(f"reqcount:{reqcount} shareid:{shareid} fileid:{fileid}",file=sys.stderr)
        #time.sleep(1)
    url = f'http://192.168.101.188:9978/proxy?do=pikpak&type=list&share_id={shareid}&file_id={fileid}&pass_code='
    print(f"url: {url}",file=sys.stderr)
    resp = requests.get(url)
    content = resp.content.decode('utf-8')
    lines = content.split("\n")
    if "folder" not in content and len(lines)<=4:
        return
    for line in lines:
        linearr = line.split('\t')
        if len(linearr)>2:
            if linearr[2] == "folder":
                m = p.match(linearr[0])
                if m:
                    arr = m.group(1).split("/")
                else:
                    arr = linearr[0].split("/")
                shareid=arr[0]
                fileid=arr[1] if len(arr)>1 else ""
                if shareid+"/"+fileid in sharedict:
                    continue
                print(line)
                sys.stdout.flush()
                getlist(shareid,fileid)
            else:
                print(line)
                sys.stdout.flush()

    
def main():
    try:
        with(open(sys.argv[1]+".txt","r",encoding="utf-8")) as f:
            while True:
                lines = f.readlines()
                if len(lines)<=0:
                    break
                for line in lines:
                    linearr = line.split("\t")
                    m = p.match(linearr[0])
                    if m:
                        arr = m.group(1).split("/")
                    else:
                        arr = linearr[0].split("/")
                    if len(arr)>1:
                        shareid = arr[0]
                        fileid = arr[1]
                        sharedict.add(shareid+"/"+fileid)
    except:
        pass
    with(open(sys.argv[1],"r",encoding="utf-8")) as f:
        j = json.load(f)
        for c in j:
            shareid=c.get("type_id")
            fileid=""
            m = p.match(shareid)
            if m:
                arr = m.group(1).split("/")
            else:
                arr = shareid.split("/")
            shareid=arr[0]
            fileid=arr[1] if len(arr)>1 else ""
            if shareid+"/"+fileid in sharedict:
                continue
            getlist(shareid,fileid)

main()
