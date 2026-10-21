"""BEAN tests BEAN: host-defined retrieval candidates, BEAN Core ranking, independent exact oracle."""
from __future__ import annotations
import argparse
import json
import statistics
import tempfile
import time
from pathlib import Path
from indexed_ledger import IndexedLedger, junit_events, linear_lookup


def run(cases: int = 1200, queries: int = 35) -> dict:
    if cases < 100 or queries < 10:
        raise ValueError('require meaningful case and query counts')
    cases_xml=[]
    for i in range(cases):
        status = '<failure message="test regression">source frame</failure>' if i%37==0 else ''
        cases_xml.append(f'<testcase classname="bean.core" name="case_{i:05d}" time="0.001">{status}</testcase>')
    xml=('<testsuite name="BEAN" tests="'+str(cases)+'">'+''.join(cases_xml)+'</testsuite>').encode()
    with tempfile.TemporaryDirectory(prefix='bean_selftest_') as tmp:
        ledger=IndexedLedger(tmp)
        events=junit_events(xml)
        manifest=ledger.append('synthetic-cases',events)
        ledger.rebuild()
        assert ledger.original_junit('synthetic-cases')==xml
        refs=[m['id'] for m in manifest['items'] if m['kind']=='test']
        sampled=[refs[(i*97)%len(refs)] for i in range(queries)]
        compressed=ledger.archive/'synthetic-cases.jsonl.gz'
        correct=sum(ledger.get(i)==linear_lookup(compressed,i) for i in refs)
        assert correct==cases, 'incomplete retrieval: reject candidate'
        results={}
        for kind in ('linear_scan','indexed_sqlite'):
            samples=[]
            for trial in range(3):
                begin=time.perf_counter_ns()
                for ident in sampled:
                    (linear_lookup(compressed,ident) if kind=='linear_scan' else ledger.get(ident))
                samples.append((time.perf_counter_ns()-begin)/1_000_000)
            results[kind]={'total_ms_median':round(statistics.median(samples),4),
                           'lookup_ms_median':round(statistics.median(samples)/queries,5)}
        speedup=results['linear_scan']['total_ms_median']/max(results['indexed_sqlite']['total_ms_median'],0.000001)
        from bean.optimization.selection import ImprovementOpportunity, rank_improvements
        candidates=[
            ImprovementOpportunity('scan_baseline','Scan compressed records',
                ('oracle:all-case-equality','benchmark:linear_scan'),0,5,1.0,0,True),
            ImprovementOpportunity('indexed_recall','Rebuild SQLite index from immutable gzip files',
                ('oracle:all-case-equality','benchmark:indexed_sqlite'),
                5 if speedup>1.2 else 0,5,1.0,0,speedup>1.2),
        ]
        ranking=rank_improvements(candidates)
        winner=ranking[0].opportunity.identifier if ranking else None
        return {
            'schema':'bean.self_recall_benchmark.v1',
            'scope':'synthetic, not model learning',
            'original_cases':cases,'fully_retrievable_cases':correct,
            'failed_cases_preserved':sum(e.get('status')=='failed' for e in events),
            'queries_per_trial':queries,'trials_per_method':3,
            'archive_bytes':compressed.stat().st_size,'index_bytes':ledger.cache.stat().st_size,
            'original_junit_bytes':len(xml),'measurements':results,
            'speedup_index_vs_scan':round(speedup,3),
            'bean_core_selector':'bean.optimization.selection.rank_improvements',
            'bean_ranked_winner':winner,
            'validation':'exact independent equality for every case before ranking',
            'limitations':['synthetic data','warm lookup only, not rebuild time',
                           'predefined candidates; BEAN ranker does not create new algorithms',
                           'neural representation training not yet implemented'],
        }


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--cases',type=int,default=1200)
    p.add_argument('--queries',type=int,default=35)
    p.add_argument('--out',type=Path)
    a=p.parse_args()
    result=run(a.cases,a.queries)
    report=json.dumps(result,indent=2,sort_keys=True)+'\n'
    if a.out:
        a.out.write_text(report,encoding='utf-8')
    print(report)


if __name__=='__main__':main()
