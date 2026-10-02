"""AST + independent core and real Tk UI checks. No network or API keys."""
import argparse
import ast
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--core-only',action='store_true');args=parser.parse_args()
    for folder in ('desk_helper_ui','tests','scripts','examples'):
        for file in (ROOT/folder).glob('*.py'):ast.parse(file.read_text('utf-8'),filename=str(file))
    report={'syntax':'passed','live_models':'not_tested','ui': 'not_run' if args.core_only else 'pending','steps':[]}
    for pattern in (['test_core.py'] if args.core_only else ['test_core.py','test_ui.py']):
        suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=pattern)
        result=unittest.TextTestRunner(verbosity=2).run(suite)
        passed=result.wasSuccessful() and result.testsRun>0 and not result.skipped
        report['steps'].append({'suite':pattern,'count':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),'passed':passed})
        if pattern=='test_ui.py':report['ui']='passed' if passed else 'failed'
        if not passed:break
    report['passed']=all(s['passed'] for s in report['steps'])
    output=ROOT/'artifacts/check.json';output.parent.mkdir(exist_ok=True);output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report));return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
