#!/usr/bin/env python3
"""Deterministic bounded loader for the first 136-chain preparation package.

This candidate program never writes source files, never performs the three real
business recomputations, and never builds the full 136-trade chain.  It verifies
the exact eight K05 files, loads only manifest-selected sample objects, preserves
all original values as strings, and emits one canonical JSONL fact base.
"""

import argparse, csv, hashlib, json, os, re, shutil, stat, zipfile
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree as ET

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))

def sha_file(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def stable_id(namespace, source_sha256, source_locator, raw_business_key):
    payload='\x1f'.join([namespace,source_sha256,source_locator,str(raw_business_key)])
    return namespace+'-'+hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]

def decimal_text(value):
    if value is None or value=='': return value
    return format(Decimal(str(value)),'f')

def parse_time(value):
    value=(value or '').strip()
    if not value or value=='--': return None
    for fmt in ('%Y-%m-%d %H:%M:%S','%Y-%m-%dT%H:%M:%S','%Y-%m-%d %H:%M:%S.%f'):
        try: return datetime.strptime(value,fmt)
        except ValueError: pass
    m=re.match(r'^[A-Za-z]{3} ([A-Za-z]{3}) (\d{2}) (\d{4}) (\d{2}:\d{2}:\d{2}) GMT[+-]\d{4}',value)
    return datetime.strptime(' '.join(m.groups()),'%b %d %Y %H:%M:%S') if m else None

def read_csv(path):
    with open(path,encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))

def jsonl_write(path, records):
    with open(path,'w',encoding='utf-8',newline='\n') as f:
        for record in records: f.write(canonical(record)+'\n')

def json_write(path, value):
    with open(path,'w',encoding='utf-8',newline='\n') as f:
        json.dump(value,f,ensure_ascii=False,sort_keys=True,indent=2); f.write('\n')

def col_index(label):
    n=0
    for char in label: n=n*26+ord(char.upper())-64
    return n

def col_label(index):
    out=''
    while index:
        index,rem=divmod(index-1,26); out=chr(65+rem)+out
    return out

def parse_range(value):
    m=re.fullmatch(r'([A-Z]+)(\d+):([A-Z]+)(\d+)',value)
    if not m: raise ValueError('UNSUPPORTED_RANGE:'+value)
    return col_index(m.group(1)),int(m.group(2)),col_index(m.group(3)),int(m.group(4))

def xlsx_sheet_cells(path, requested_sheet):
    ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
    rel_ns={'p':'http://schemas.openxmlformats.org/package/2006/relationships'}
    with zipfile.ZipFile(path) as z:
        shared=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            root=ET.fromstring(z.read('xl/sharedStrings.xml'))
            shared=[''.join(t.text or '' for t in si.iter('{%s}t'%ns['m'])) for si in root.findall('m:si',ns)]
        wb=ET.fromstring(z.read('xl/workbook.xml')); rels=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        relmap={x.attrib['Id']:x.attrib['Target'] for x in rels.findall('p:Relationship',rel_ns)}; target=None
        for sheet in wb.find('m:sheets',ns):
            if sheet.attrib.get('name')==requested_sheet:
                target=relmap[sheet.attrib['{%s}id'%ns['r']]]; break
        if target is None: raise KeyError('SHEET_NOT_FOUND:'+requested_sheet)
        member=target.lstrip('/') if target.startswith('/') else 'xl/'+target.lstrip('/')
        root=ET.fromstring(z.read(os.path.normpath(member))); cells={}
        for cell in root.findall('.//m:c',ns):
            ref=cell.attrib['r']; cell_type=cell.attrib.get('t'); value_node=cell.find('m:v',ns); formula_node=cell.find('m:f',ns)
            if cell_type=='inlineStr': value=''.join(x.text or '' for x in cell.iter('{%s}t'%ns['m']))
            elif value_node is None: value=''
            elif cell_type=='s': value=shared[int(value_node.text)]
            elif cell_type=='b': value='TRUE' if value_node.text=='1' else 'FALSE'
            else: value=value_node.text or ''
            cells[ref]={'value':value,'formula':formula_node.text if formula_node is not None else None}
        return cells

def xlsx_extract(path, selector):
    result=[]; sheet_results=[]
    for spec in selector.get('sheets') or [selector]:
        ranges=[item for item in (spec.get('ranges') or [spec.get('range')]) if item]
        if not ranges: raise ValueError('XLSX_RANGE_MISSING')
        parsed=[parse_range(item) for item in ranges]; expected=spec.get('row_count')
        first_row=min(item[1] for item in parsed); last_row=max(item[3] for item in parsed)
        explicit_header=spec.get('header_row')
        header_row=int(explicit_header) if explicit_header is not None else (None if expected is not None and last_row-first_row+1==int(expected) else first_row)
        min_data_row=first_row if header_row is None else header_row+1; allowed_cols=set(); max_row=0
        for c1,_r1,c2,r2 in parsed:
            allowed_cols.update(range(c1,c2+1)); max_row=max(max_row,r2)
        for context_col in spec.get('join_context_columns',[]): allowed_cols.add(col_index(context_col))
        for excluded in spec.get('excluded_columns',[]): allowed_cols.discard(col_index(excluded))
        column_map=spec.get('columns') or {}; cells=xlsx_sheet_cells(path,spec['sheet']); headers={}
        for col in sorted(allowed_cols):
            letter=col_label(col); actual='' if header_row is None else cells.get(f'{letter}{header_row}',{}).get('value','')
            headers[col]=column_map.get(letter) or actual or letter
        rows=[]
        for row_no in range(min_data_row,max_row+1):
            record={}; formulas={}
            for col in sorted(allowed_cols):
                letter=col_label(col); cell=cells.get(f'{letter}{row_no}',{'value':'','formula':None})
                record[headers[col]]=cell['value']
                if cell['formula'] is not None: formulas[headers[col]]=cell['formula']
            if all(value=='' for value in record.values()): continue
            if formulas: record['_formulas']=formulas
            record['_source_row']=row_no; rows.append(record)
        row_filter=spec.get('row_filter')
        if row_filter:
            field=row_filter.get('field') or headers.get(col_index(row_filter['column']))
            rows=[row for row in rows if str(row.get(field,''))==str(row_filter.get('equals'))]
        sheet_results.append({'sheet':spec['sheet'],'expected_rows':expected,'actual_rows':len(rows)})
        result.extend({'_sheet':spec['sheet'],**row} for row in rows)
    return result,sheet_results

def json_pointer(value, pointer):
    if pointer in ('','/'): return value
    current=value
    for token in pointer.lstrip('$.').lstrip('/').split('/'):
        token=token.replace('~1','/').replace('~0','~')
        current=current[int(token)] if isinstance(current,list) else current[token]
    return current

def extract_selected_object(receipt, output_dir):
    path=Path(receipt['source_path']); selector=receipt['original_selector']
    if not path.is_file() or path.stat().st_size!=receipt['actual_bytes'] or sha_file(path)!=receipt['actual_sha256']:
        raise RuntimeError('SELECTED_SOURCE_IDENTITY_MISMATCH:'+receipt['input_id'])
    kind=selector.get('kind') or ('XLSX_SHEETS' if 'sheets' in selector else 'XLSX_SHEET')
    stem=f"{receipt['input_id']}__OBJ-{int(receipt['selected_object_index']):02d}"; expected=selector.get('row_count') or selector.get('expected_data_rows')
    if kind in {'CSV_FULL','CSV_FULL_FILE_SUBOBJECT','CSV_METHOD_SUPPORT','CSV_FULL_TWO_VARIANTS','CSV_FULL_BOUNDED_ROWS'}:
        actual=len(read_csv(path)); destination=output_dir/f'{stem}__{path.name}'; shutil.copyfile(path,destination)
    elif kind=='CSV_SELECTED_COLUMNS':
        rows=read_csv(path); row_filter=selector.get('row_filter')
        if row_filter: rows=[row for row in rows if str(row.get(row_filter.get('field'),''))==str(row_filter.get('equals'))]
        fields=selector.get('columns') or selector.get('include_fields')
        if isinstance(fields,dict): fields=list(fields.values())
        if fields: rows=[{field:row.get(field,'') for field in fields} for row in rows]
        actual=len(rows); destination=output_dir/f'{stem}.jsonl'; jsonl_write(destination,rows)
    elif kind in {'JSON_FULL','JSON_FULL_FILE_SUBOBJECT','JSON_METHOD_OBJECT','JSON_FULL_PRECISION_BOUNDARY'}:
        json.load(open(path,encoding='utf-8')); actual=1; destination=output_dir/f'{stem}__{path.name}'; shutil.copyfile(path,destination)
    elif kind=='JSON_SELECTED_POINTERS':
        value=json.load(open(path,encoding='utf-8')); selected={pointer:json_pointer(value,pointer) for pointer in selector['json_pointers']}
        actual=len(selected); expected=len(selector['json_pointers']); destination=output_dir/f'{stem}.json'; json_write(destination,selected)
    elif kind=='JSON_SELECTED_FIELDS':
        value=json.load(open(path,encoding='utf-8')); rows=json_pointer(value,selector['json_pointer']); row_filter=selector.get('row_filter')
        if row_filter: rows=[row for row in rows if str(row.get(row_filter['field'],''))==str(row_filter.get('equals'))]
        rows=[{field:row.get(field) for field in selector['fields']} for row in rows]
        actual=len(rows); destination=output_dir/f'{stem}.jsonl'; jsonl_write(destination,rows)
    elif kind in {'JSONL_FULL_FILE_SUBOBJECT','JSONL_FULL_LINEAGE_INTERFACE'}:
        with open(path,encoding='utf-8') as handle: actual=sum(1 for line in handle if line.strip())
        destination=output_dir/f'{stem}__{path.name}'; shutil.copyfile(path,destination)
    elif kind in {'XLSX_SHEET','XLSX_SHEETS','EXISTING_SELECTED_COLUMNS'}:
        rows,sheet_results=xlsx_extract(path,selector); actual=len(rows)
        if len(sheet_results)==1: expected=sheet_results[0]['expected_rows']
        else: expected=sum(item['expected_rows'] for item in sheet_results if item['expected_rows'] is not None)
        destination=output_dir/f'{stem}.jsonl'; jsonl_write(destination,rows)
    elif kind=='IMAGE_VISIBLE_FIELD':
        record={'field':selector['field'],'text':selector['text'],'scope':selector['scope']}; actual=1; expected=1
        destination=output_dir/f'{stem}.json'; json_write(destination,record)
    else: raise RuntimeError('UNSUPPORTED_SELECTOR_KIND:'+kind)
    if expected is not None and int(expected)!=int(actual): raise RuntimeError('SELECTED_COUNT_MISMATCH:'+receipt['input_id'])
    extracted_sha=sha_file(destination)
    if actual!=receipt['actual_count'] or extracted_sha!=receipt['extracted_content_sha256']:
        raise RuntimeError('SELECTED_EXTRACTION_MISMATCH:'+receipt['input_id'])
    os.chmod(destination,stat.S_IRUSR|stat.S_IRGRP|stat.S_IROTH)
    return {'input_id':receipt['input_id'],'selected_object_index':receipt['selected_object_index'],'actual_count':actual,'extracted_content_sha256':extracted_sha,'output_path':str(destination)}

def load_selected_objects(receipts_path, output_dir):
    receipts=[json.loads(line) for line in open(receipts_path,encoding='utf-8') if line.strip()]
    output_dir=Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()): raise RuntimeError('OUTPUT_DIRECTORY_NOT_EMPTY')
    output_dir.mkdir(parents=True,exist_ok=True)
    results=[extract_selected_object(receipt,output_dir) for receipt in receipts]
    print(canonical({'selected_object_count':len(results),'unique_source_path_count':len({r['source_path'] for r in receipts}),'all_extractions_match':True}))

def verify_sources(config):
    for name,item in config['bounded_sample_sources'].items():
        path=Path(item['path'])
        if not path.is_file() or path.stat().st_size!=item['bytes'] or sha_file(path)!=item['sha256']:
            raise RuntimeError('SOURCE_IDENTITY_MISMATCH:'+name)
    if str(config['forbidden_extra_sample_summary']) in {x['path'] for x in config['bounded_sample_sources'].values()}:
        raise RuntimeError('FORBIDDEN_SUMMARY_INCLUDED')

def selected_scope(manifest):
    selected=manifest['selected_by_category']
    cycles=set(); exact_events=set(); shared_events=set(); categories=defaultdict(set)
    for cat,item in selected.items():
        for key in ('cycle_id',):
            if item.get(key): cycles.add(item[key]); categories[item[key]].add(cat)
        for cyc in item.get('active_cycle_ids',[]) + item.get('cycle_ids',[]):
            cycles.add(cyc); categories[cyc].add(cat)
        if item.get('condition_event_id'): exact_events.add(item['condition_event_id'])
        for eid in item.get('overlapping_shared_fund_event_ids',[]): shared_events.add(eid)
    return cycles,exact_events,shared_events,categories

def event_time(table,row):
    fields={'order':['order_created_at','order_updated_at'],'fill':['fill_time'],'position':['action_start_time','action_end_time'],'condition':['created_at','terminal_at','triggered_at'],'fund':['event_time'],'copy':['cycle_start_time','cycle_end_time']}
    return next((row.get(x) for x in fields.get(table,[]) if row.get(x)),None)

def build(config_path, manifest_path, output_path):
    config=json.load(open(config_path,encoding='utf-8')); manifest=json.load(open(manifest_path,encoding='utf-8'))
    verify_sources(config)
    data={name:read_csv(item['path']) for name,item in config['bounded_sample_sources'].items()}
    cycles,exact_events,shared_events,categories=selected_scope(manifest)
    selected_event_ids=set(); records=[]
    for table in ('order','fill','position','condition','fund','copy'):
        src=config['bounded_sample_sources'][table]
        for row_no,row in enumerate(data[table],2):
            eid=(row.get('event_id') or '').strip(); cyc=(row.get('position_cycle_id') or '').strip()
            if cyc not in cycles and eid not in exact_events and eid not in shared_events: continue
            selected_event_ids.add(eid)
            scope=sorted(categories.get(cyc,set()))
            if eid in exact_events: scope.append('exact_unassigned_condition_object')
            if eid in shared_events: scope.append('account_level_time_overlap_object')
            locator=f'{Path(src["path"]).name}:data-row-{row_no}'
            records.append({'record_type':'FACT_STATEMENT','fact_id':stable_id('FACT',src['sha256'],locator,eid),'sample_categories':sorted(set(scope)),'object_id':cyc or eid,'source_table':table,'source_path':src['path'],'source_sha256':src['sha256'],'source_row':row_no,'source_event_id':eid,'event_time_original':event_time(table,row),'evidence_status':row.get('evidence_level') or row.get('link_level') or row.get('reason_status') or 'SOURCE_RECORDED','execution_lifecycle':'NOT_A_RECOMPUTATION','applicability_scope':cyc or 'ACCOUNT_OR_UNASSIGNED','conflict_ids':[],'user_statement':None,'ai_interpretation':None,'raw_record':row,'can_prove':'该行在固定K05源表中的原始字段和值。','cannot_prove':'不自动证明候选关系、原因、意图、资金归属或时间重叠的因果。'})
    link_src=config['bounded_sample_sources']['linkage']
    for row_no,row in enumerate(data['linkage'],2):
        if (row.get('position_cycle_id') or '') not in cycles and row.get('source_event_id') not in selected_event_ids and row.get('target_event_id') not in selected_event_ids: continue
        key=row.get('linkage_id') or f'{row_no}'
        locator=f'{Path(link_src["path"]).name}:data-row-{row_no}'
        records.append({'record_type':'RELATION_STATEMENT','fact_id':stable_id('REL',link_src['sha256'],locator,key),'sample_categories':sorted(categories.get(row.get('position_cycle_id',''),set())),'object_id':row.get('position_cycle_id') or key,'source_table':'linkage','source_path':link_src['path'],'source_sha256':link_src['sha256'],'source_row':row_no,'source_event_id':key,'event_time_original':None,'evidence_status':row.get('link_level') or row.get('evidence_level') or 'SOURCE_RECORDED','execution_lifecycle':'NOT_A_RECOMPUTATION','applicability_scope':row.get('position_cycle_id') or 'CROSS_OBJECT','conflict_ids':[],'user_statement':None,'ai_interpretation':None,'raw_record':row,'can_prove':'固定连接表记录了该关系声明及其等级。','cannot_prove':'候选或上下文关系不升级为直接因果或唯一归属。'})
    lin_src=config['bounded_sample_sources']['lineage']
    for row_no,row in enumerate(data['lineage'],2):
        if row.get('event_id') not in selected_event_ids: continue
        key=row.get('lineage_id') or f'{row.get("event_id")}:{row_no}'
        locator=f'{Path(lin_src["path"]).name}:data-row-{row_no}'
        records.append({'record_type':'LINEAGE_STATEMENT','fact_id':stable_id('LIN',lin_src['sha256'],locator,key),'sample_categories':[],'object_id':row.get('event_id'),'source_table':'lineage','source_path':lin_src['path'],'source_sha256':lin_src['sha256'],'source_row':row_no,'source_event_id':row.get('event_id'),'event_time_original':None,'evidence_status':'SOURCE_LINEAGE','execution_lifecycle':'NOT_A_RECOMPUTATION','applicability_scope':row.get('event_id'),'conflict_ids':[],'user_statement':None,'ai_interpretation':None,'raw_record':row,'can_prove':'固定来源链表记录了事件与源对象的追溯关系。','cannot_prove':'来源链本身不提高业务结论的证据等级。'})
    for method in config.get('bounded_method_test_sources',[]):
        path=Path(method['path'])
        if path.stat().st_size!=method['bytes'] or sha_file(path)!=method['sha256']: raise RuntimeError('METHOD_SOURCE_IDENTITY_MISMATCH')
        if path.suffix.lower()=='.csv': payload=read_csv(path)
        else: payload=json.load(open(path,encoding='utf-8'))
        records.append({'record_type':'METHOD_EVIDENCE','fact_id':stable_id('METHOD',method['sha256'],path.name,method['role']),'sample_categories':method['sample_categories'],'object_id':method['object_id'],'source_table':'method','source_path':str(path),'source_sha256':method['sha256'],'source_row':None,'source_event_id':None,'event_time_original':None,'evidence_status':'METHOD_ONLY_NOT_RUN','execution_lifecycle':'NOT_AUTHORIZED_FOR_REAL_RECOMPUTATION','applicability_scope':method['role'],'conflict_ids':[],'user_statement':None,'ai_interpretation':None,'raw_record':payload,'can_prove':method['can_prove'],'cannot_prove':method['cannot_prove']})
    records.sort(key=lambda r:(r['object_id'],r['event_time_original'] or '',r['record_type'],r['fact_id']))
    with open(output_path,'w',encoding='utf-8',newline='\n') as f:
        for record in records: f.write(canonical(record)+'\n')
    business_sha=sha_file(output_path)
    print(canonical({'record_count':len(records),'business_content_sha256':business_sha,'selected_event_count':len(selected_event_ids)}))

def run_tests(test_path):
    tests=[json.loads(x) for x in open(test_path,encoding='utf-8') if x.strip()]; out=[]
    for t in tests:
        kind=t['test_kind']; inp=t['input']; exp=t['expected']
        if kind=='stable_id': actual=stable_id(**inp)
        elif kind=='decimal_text': actual=decimal_text(inp['value'])
        elif kind=='canonical': actual=canonical(inp['value'])
        elif kind=='preserve_value': actual=inp['value']
        elif kind=='dual_view_ids': actual=sorted(inp['fact_base_ids'])==sorted(inp['ai_ids'])==sorted(inp['user_ids'])
        elif kind=='selector_compile': actual=canonical(inp['selector'])
        elif kind=='selected_csv_load':
            path=Path(inp['path']); actual={'sha256':sha_file(path),'row_count':len(read_csv(path))}
        else: raise RuntimeError('UNKNOWN_TEST_KIND:'+kind)
        out.append({'test_id':t['test_id'],'pass':actual==exp,'expected':exp,'actual':actual})
    result={'tests':out,'pass_count':sum(x['pass'] for x in out),'fail_count':sum(not x['pass'] for x in out)}
    print(canonical(result))
    if result['fail_count']: raise SystemExit(1)

if __name__=='__main__':
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='cmd',required=True)
    l=sub.add_parser('load-selected-objects'); l.add_argument('--receipts',required=True); l.add_argument('--output-dir',required=True)
    b=sub.add_parser('build-bounded'); b.add_argument('--config',required=True); b.add_argument('--samples',required=True); b.add_argument('--output',required=True)
    t=sub.add_parser('self-test'); t.add_argument('--tests',required=True)
    a=p.parse_args()
    if a.cmd=='load-selected-objects': load_selected_objects(a.receipts,a.output_dir)
    elif a.cmd=='build-bounded': build(a.config,a.samples,a.output)
    else: run_tests(a.tests)
