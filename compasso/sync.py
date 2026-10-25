#!/usr/bin/env python3
"""Coleta enxuta de resultado unificado do TSE. Sem projeções e sem dados fictícios."""
import datetime as dt
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen

OUT=Path(__file__).resolve().with_name("live.json")
UFS="ac al ap am ba ce df es go ma mt ms mg pa pb pr pe pi rj rn ro rr rs sc sp se to".split()
def get(uf, election):
    url=f"https://resultados.tse.jus.br/oficial/ele2026/{election}/dados/{uf}/{uf}-c0001-e00{election}-u.json"
    req=Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; CompassoEleitoral/1.0)","Accept":"application/json"})
    with urlopen(req,timeout=15) as response: original=json.load(response)
    if not original.get("carg") or not original.get("s"):
        raise ValueError(f"Sem apuração válida: {uf}/{election}")
    # Preserva números e datas originais do TSE; descarta campos não usados.
    candidates=[]
    for cargo in original.get("carg",[]):
        for group in cargo.get("agr",[]):
            for party in group.get("par",[]):
                for cand in party.get("cand",[]):
                    if str(cand.get("n")) in ("13","22"):
                        candidates.append({k:cand[k] for k in ("n","nmu","nm","vap","pvap") if k in cand})
    if not candidates: raise ValueError(f"Sem presidenciáveis: {uf}/{election}")
    return {
        "carg":[{"agr":[{"par":[{"cand":candidates}]}]}],
        "s":{k:original.get("s",{}).get(k) for k in ("pst","st","ts")},
        "e":{k:original.get("e",{}).get(k) for k in ("a","est","c","pa","pc")},
        "v":{k:original.get("v",{}).get(k) for k in ("vv","vb","pvb","tvn","ptvn","tv")},
        "dg":original.get("dg"),"hg":original.get("hg")}
def main():
    old={}
    if OUT.exists():
        try:old=json.loads(OUT.read_text(encoding="utf-8"))
        except (ValueError,OSError):pass
    new={"first":old.get("first"),"second":old.get("second"),"ufs":old.get("ufs",{}),"checked_utc":dt.datetime.now(dt.timezone.utc).isoformat()}
    tasks=[("first","br",6257),("second","br",6258)]+[("ufs",uf,6258) for uf in UFS]
    ok=0
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures={executor.submit(get,uf,election):(kind,uf) for kind,uf,election in tasks}
        for future in as_completed(futures):
            kind,uf=futures[future]
            try:
                value=future.result()
                if kind=="ufs":new["ufs"][uf]=value
                else:new[kind]=value
                ok+=1
            except Exception as exc:
                print(f"Indisponível {kind}/{uf}: {exc}")
    # Arquivo novo só é criado quando há pelo menos um resultado real do TSE.
    if not new.get("second"):
        print("Sem dados do 2º turno; preservando último snapshot.")
        return
    OUT.write_text(json.dumps(new,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    print(f"Arquivos conferidos: {ok}/{len(tasks)}. Gerado: {new['checked_utc']}")
if __name__=="__main__":main()
