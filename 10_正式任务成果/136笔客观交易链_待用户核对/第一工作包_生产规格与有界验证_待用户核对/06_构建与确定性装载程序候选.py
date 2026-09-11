#!/usr/bin/env python3
"""Deterministic bounded loader for the first 136-chain preparation package.

This candidate program never writes source files, never performs the three real
business recomputations, and never builds the full 136-trade chain.  It verifies
the exact eight K05 files, loads only manifest-selected sample objects, preserves
all original values as strings, emits one canonical JSONL fact base, and rebuilds
both the AI-readable view and the user-review workbook from that same fact base.
"""

import argparse, csv, hashlib, json, os, re, shutil, stat, subprocess, tempfile, zipfile
from collections import Counter, defaultdict
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

def read_jsonl(path):
    with open(path,encoding='utf-8') as handle:
        return [json.loads(line) for line in handle if line.strip()]

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

def verify_file_identity(path, identity, label):
    path=Path(path)
    if not path.is_file():
        raise RuntimeError(f'VIEW_INPUT_MISSING:{label}:{path}')
    if path.stat().st_size!=identity['bytes'] or sha_file(path)!=identity['sha256']:
        raise RuntimeError(f'VIEW_INPUT_IDENTITY_MISMATCH:{label}:{path}')

def build_ai_view_text(records, fact_path, sample_manifest, view_config):
    counts=Counter(record['record_type'] for record in records)
    ai=view_config['ai_view']
    lines=[ai['title'],'',ai['identity'],'',ai['boundary'],'','## 一、样本覆盖','','| 类别 | 选中对象 |','|---|---|']
    for category,item in sample_manifest['selected_by_category'].items():
        lines.append(f'| {category} | {item["stable_id"]} |')
    lines += ['', '## 二、事实底座对账', '', f'- 总记录：{len(records)}']
    lines += [f'- {name}：{count}' for name,count in sorted(counts.items())]
    lines += [f'- 业务内容SHA-256：`{sha_file(fact_path)}`', '', '## 三、连续读取正文', '', ai['body_note'], '']
    chunk_size=int(ai['chunk_size'])
    for start in range(0,len(records),chunk_size):
        group=records[start:start+chunk_size]
        lines += [
            f'### 分块 {start//chunk_size+1:03d}',
            '',
            f'- 起始事实ID：`{group[0]["fact_id"]}`',
            f'- 结束事实ID：`{group[-1]["fact_id"]}`',
            f'- 上一分块结束：`{records[start-1]["fact_id"] if start else "NONE"}`',
            f'- 下一分块开始：`{records[start+chunk_size]["fact_id"] if start+chunk_size<len(records) else "NONE"}`',
            '',
            '```jsonl',
        ]
        lines.extend(canonical(record) for record in group)
        lines += ['```','']
    lines += ['## 四、读取结论边界','']
    lines.extend(f'- {item}' for item in ai['closing_boundaries'])
    return '\n'.join(lines)+'\n'

def ai_view_records(text):
    records=[]; inside=False
    for line in text.splitlines():
        if line=='```jsonl':
            inside=True
        elif line=='```' and inside:
            inside=False
        elif inside and line.strip():
            records.append(json.loads(line))
    return records

def build_workbook_payload(records, sample_manifest, receipts, contract_id):
    facts=[]; relations=[]; lineage=[]; methods=[]
    for record in records:
        row={
            '事实ID':record['fact_id'],
            '样本类别':'；'.join(record['sample_categories']),
            '对象ID':record['object_id'],
            '记录类型':record['record_type'],
            '原始时间':record['event_time_original'] or '',
            '来源表':record['source_table'],
            '来源行':record['source_row'] or '',
            '证据状态':record['evidence_status'],
            '来源事件ID':record['source_event_id'] or '',
            '原始记录JSON':canonical(record['raw_record']),
            '能证明':record['can_prove'],
            '不能证明':record['cannot_prove'],
        }
        if record['record_type']=='FACT_STATEMENT': facts.append(row)
        elif record['record_type']=='RELATION_STATEMENT': relations.append(row)
        elif record['record_type']=='LINEAGE_STATEMENT': lineage.append(row)
        elif record['record_type']=='METHOD_EVIDENCE': methods.append(row)
        else: raise RuntimeError('UNKNOWN_FACT_RECORD_TYPE:'+str(record['record_type']))
    selected=[
        {
            '类别':category,
            '选中对象':item['stable_id'],
            '排序元组':canonical(item.get('metrics',{}).get('sorting_tuple')),
            '边界':item.get('relationship_boundary') or item.get('relation_boundary') or item.get('selection_or_rejection_reason'),
        }
        for category,item in sample_manifest['selected_by_category'].items()
    ]
    overview=[
        {'项目':'合同ID','结果':contract_id},
        {'项目':'事实底座记录数','结果':len(records)},
        {'项目':'事实记录','结果':len(facts)},
        {'项目':'关系记录','结果':len(relations)},
        {'项目':'来源链记录','结果':len(lineage)},
        {'项目':'方法记录','结果':len(methods)},
        {'项目':'事实底座SHA-256','结果':None},
        {'项目':'正式采用状态','结果':'尚未正式采用'},
        {'项目':'136笔构建状态','结果':'未开始'},
        {'项目':'三项真实重算','结果':'未授权、未运行'},
    ]
    sources=[
        {
            'S3INPUT':item['input_id'],
            '对象序号':item['selected_object_index'],
            '来源路径':item['source_path'],
            '父文件SHA-256':item['actual_sha256'],
            '选择器':item['normalized_selector'],
            '装载数量':item['actual_count'],
            '抽取SHA-256':item['extracted_content_sha256'],
            '状态':item['load_status'],
            '不能证明':item['cannot_prove'],
        }
        for item in receipts
    ]
    return {
        '核对总览':overview,
        '样本选择':selected,
        '事实明细':facts,
        '关系明细':relations,
        '来源链':lineage,
        '方法与边界':methods,
        '输入来源与限制':sources,
    }

def workbook_display_content(payload, workbook_config):
    category_labels=workbook_config['category_labels']
    sheets=[]
    for name in workbook_config['sheet_order']:
        headers=workbook_config['preferred_columns'][name]
        rows=[]
        for source_row in payload[name]:
            row=[]
            for header in headers:
                value=source_row.get(header)
                if value is None:
                    value=''
                elif isinstance(value,(dict,list)):
                    value=canonical(value)
                if header in {'类别','样本类别'} and isinstance(value,str):
                    for technical,plain in category_labels.items():
                        value=value.replace(technical,plain)
                row.append(value)
            rows.append(row)
        sheets.append({'sheet_name':name,'headers':headers,'rows':rows})
    return sheets

WORKBOOK_RENDERER=r'''
import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

const [artifactModulePath,payloadPath,outputPath,previewDir,viewConfigPath] = process.argv.slice(2);
const { FileBlob, SpreadsheetFile, Workbook } = await import(pathToFileURL(artifactModulePath).href);
const payload=JSON.parse(await fs.readFile(payloadPath,"utf8"));
const cfg=JSON.parse(await fs.readFile(viewConfigPath,"utf8"));
const workbook=Workbook.create();
const sheetOrder=cfg.sheet_order;
const preferredColumns=cfg.preferred_columns;
const categoryLabels=cfg.category_labels;

function colLabel(index) {
  let n=index+1,out="";
  while (n>0) {
    const rem=(n-1)%26;
    out=String.fromCharCode(65+rem)+out;
    n=Math.floor((n-1)/26);
  }
  return out;
}
function normalizedValue(value) {
  if (value===null || value===undefined) return "";
  if (typeof value==="object") return JSON.stringify(value);
  return value;
}
function displayValue(header,value) {
  const normalized=normalizedValue(value);
  if (!["类别","样本类别"].includes(header) || typeof normalized!=="string") return normalized;
  let display=normalized;
  for (const [technical,plain] of Object.entries(categoryLabels)) display=display.split(technical).join(plain);
  return display;
}
function widthFor(header) {
  if (header==="原始记录JSON") return 90;
  if (["能证明","不能证明","边界","结果"].includes(header)) return 42;
  if (header==="来源路径") return 72;
  if (header==="选择器") return 65;
  if (["类别","排序元组"].includes(header)) return 40;
  if (header.includes("ID") || header.includes("SHA")) return 30;
  if (header.includes("时间")) return 24;
  if (header.includes("来源") || header.includes("对象")) return 25;
  return Math.max(14,Math.min(28,String(header).length*2+4));
}
function tableRows(sheet) {
  const values=sheet.getUsedRange().values;
  if (!Array.isArray(values) || values.length<3) throw new Error(`工作表 ${sheet.name} 无法读取`);
  const headers=values[2].map(String);
  const rows=values.slice(3)
    .filter(row=>row.some(value=>value!=="" && value!==null))
    .map(row=>row.map(normalizedValue));
  return {headers,rows};
}

await fs.mkdir(path.dirname(outputPath),{recursive:true});
await fs.mkdir(previewDir,{recursive:true});
for (let sheetIndex=0;sheetIndex<sheetOrder.length;sheetIndex+=1) {
  const name=sheetOrder[sheetIndex];
  const rows=payload[name]||[];
  if (rows.length===0) throw new Error(`工作表 ${name} 没有数据`);
  const headers=preferredColumns[name];
  const matrix=rows.map(row=>headers.map(header=>displayValue(header,row[header])));
  const sheet=workbook.worksheets.add(name);
  sheet.showGridLines=false;
  sheet.tabColor=cfg.tab_colors[sheetIndex];
  const lastCol=colLabel(headers.length-1);
  const lastRow=rows.length+3;
  sheet.mergeCells(`A1:${lastCol}1`);
  sheet.getRange("A1").values=[[`第一工作包·${name}`]];
  sheet.getRange(`A1:${lastCol}1`).format={fill:"#17365D",font:{name:cfg.font_family,size:16,bold:true,color:"#FFFFFF"},verticalAlignment:"center"};
  sheet.getRange(`A1:${lastCol}1`).format.rowHeight=30;
  sheet.mergeCells(`A2:${lastCol}2`);
  sheet.getRange("A2").values=[[cfg.subtitles[name]]];
  sheet.getRange(`A2:${lastCol}2`).format={fill:"#DCE6F1",font:{name:cfg.font_family,size:10,color:"#334155"},wrapText:true,verticalAlignment:"center"};
  sheet.getRange(`A2:${lastCol}2`).format.rowHeight=34;
  sheet.getRange(`A3:${lastCol}3`).values=[headers];
  sheet.getRange(`A3:${lastCol}3`).format={fill:"#2F75B5",font:{name:cfg.font_family,size:10,bold:true,color:"#FFFFFF"},wrapText:true,verticalAlignment:"center",borders:{preset:"all",style:"thin",color:"#B4C6E7"}};
  sheet.getRange(`A3:${lastCol}3`).format.rowHeight=36;
  sheet.getRange(`A4:${lastCol}${lastRow}`).values=matrix;
  sheet.getRange(`A4:${lastCol}${lastRow}`).format={font:{name:cfg.font_family,size:9,color:"#1F2937"},wrapText:true,verticalAlignment:"top",borders:{preset:"all",style:"thin",color:"#D9E2F3"}};
  sheet.getRange(`A4:${lastCol}${lastRow}`).format.rowHeight=42;
  for (let column=0;column<headers.length;column+=1) sheet.getRange(`${colLabel(column)}1:${colLabel(column)}${lastRow}`).format.columnWidth=widthFor(headers[column]);
  const table=sheet.tables.add(`A3:${lastCol}${lastRow}`,true,`Pkg1Table${String(sheetIndex+1).padStart(2,"0")}`);
  table.style=sheetIndex%2===0?"TableStyleMedium2":"TableStyleMedium4";
  table.showHeaders=true;
  table.showBandedColumns=false;
  table.showFilterButton=true;
  sheet.freezePanes.freezeRows(3);
  if (headers.length>5) sheet.freezePanes.freezeColumns(2);
  if (headers.includes("证据状态")) {
    const statusCol=colLabel(headers.indexOf("证据状态"));
    sheet.getRange(`${statusCol}4:${statusCol}${lastRow}`).conditionalFormats.add("containsText",{text:"UNKNOWN",format:{fill:"#FFF2CC",font:{color:"#9C5700",bold:true}}});
  }
}
workbook.recalculate();
for (const name of sheetOrder) {
  const headers=preferredColumns[name];
  const lastCol=colLabel(headers.length-1);
  const renderLastRow=Math.min(payload[name].length+3,24);
  const preview=await workbook.render({sheetName:name,range:`A1:${lastCol}${renderLastRow}`,scale:0.8,format:"png"});
  await fs.writeFile(path.join(previewDir,`${String(sheetOrder.indexOf(name)+1).padStart(2,"0")}_${name}.png`),new Uint8Array(await preview.arrayBuffer()));
}
const exported=await SpreadsheetFile.exportXlsx(workbook);
await exported.save(outputPath);
const imported=await SpreadsheetFile.importXlsx(await FileBlob.load(outputPath));
const actualSheets=imported.worksheets.items.map(sheet=>sheet.name);
const sheetChecks={};
const errorTokens=new Set(["#REF!","#DIV/0!","#VALUE!","#NAME?","#N/A","#NUM!","#NULL!","#SPILL!","#CALC!"]);
let formulaErrorCount=0;
for (const name of sheetOrder) {
  const sheet=imported.worksheets.getItem(name);
  const {headers,rows}=tableRows(sheet);
  const expectedHeaders=preferredColumns[name];
  const expectedRows=payload[name].map(row=>expectedHeaders.map(header=>displayValue(header,row[header])));
  formulaErrorCount+=sheet.getUsedRange().values.flat().filter(value=>errorTokens.has(String(value))).length;
  let firstDifference=null;
  for (let rowIndex=0;rowIndex<Math.min(rows.length,expectedRows.length) && firstDifference===null;rowIndex+=1) {
    for (let columnIndex=0;columnIndex<expectedHeaders.length;columnIndex+=1) {
      if (JSON.stringify(rows[rowIndex][columnIndex])!==JSON.stringify(expectedRows[rowIndex][columnIndex])) {
        firstDifference={
          row_index:rowIndex,
          column:expectedHeaders[columnIndex],
          actual:String(rows[rowIndex][columnIndex]).slice(0,300),
          expected:String(expectedRows[rowIndex][columnIndex]).slice(0,300),
          actual_length:String(rows[rowIndex][columnIndex]).length,
          expected_length:String(expectedRows[rowIndex][columnIndex]).length,
        };
        break;
      }
    }
  }
  sheetChecks[name]={
    headers_exact:JSON.stringify(headers)===JSON.stringify(expectedHeaders),
    row_count_expected:expectedRows.length,
    row_count_actual:rows.length,
    all_display_values_exact:JSON.stringify(rows)===JSON.stringify(expectedRows),
    first_difference:firstDifference,
  };
}
const result={
  all_pass:JSON.stringify(actualSheets)===JSON.stringify(sheetOrder)
    && Object.values(sheetChecks).every(item=>item.headers_exact && item.row_count_expected===item.row_count_actual && item.all_display_values_exact)
    && formulaErrorCount===0,
  sheet_order_exact:JSON.stringify(actualSheets)===JSON.stringify(sheetOrder),
  sheet_checks:sheetChecks,
  formula_error_count:formulaErrorCount,
};
console.log(JSON.stringify(result));
if (!result.all_pass) process.exit(2);
'''

def build_views(config_path, output_dir=None, preview_dir=None, verification_output=None):
    config_path=Path(config_path).resolve()
    config=json.load(open(config_path,encoding='utf-8'))
    view=config['view_generation']
    base_dir=config_path.parent
    inputs=view['inputs']
    fact_path=base_dir/inputs['fact_base']['file']
    sample_path=base_dir/inputs['sample_manifest']['file']
    receipts_path=base_dir/inputs['input_receipts']['file']
    verify_file_identity(fact_path,inputs['fact_base'],'fact_base')
    verify_file_identity(sample_path,inputs['sample_manifest'],'sample_manifest')
    verify_file_identity(receipts_path,inputs['input_receipts'],'input_receipts')
    records=read_jsonl(fact_path)
    sample_manifest=json.load(open(sample_path,encoding='utf-8'))
    receipts=read_jsonl(receipts_path)
    expected=view['verification']
    counts=Counter(record['record_type'] for record in records)
    if len(records)!=expected['record_count'] or dict(counts)!=expected['record_type_counts']:
        raise RuntimeError('VIEW_FACT_BASE_COUNT_MISMATCH')
    if len(sample_manifest['selected_by_category'])!=expected['sample_category_count']:
        raise RuntimeError('VIEW_SAMPLE_CATEGORY_COUNT_MISMATCH')
    if len(receipts)!=expected['input_receipt_count']:
        raise RuntimeError('VIEW_INPUT_RECEIPT_COUNT_MISMATCH')
    target_dir=Path(output_dir).resolve() if output_dir else base_dir
    target_dir.mkdir(parents=True,exist_ok=True)
    ai_output=target_dir/view['outputs']['ai_view']
    workbook_output=target_dir/view['outputs']['user_workbook']
    if ai_output==workbook_output: raise RuntimeError('VIEW_OUTPUT_PATH_COLLISION')
    ai_text=build_ai_view_text(records,fact_path,sample_manifest,view)
    if ai_view_records(ai_text)!=records: raise RuntimeError('AI_VIEW_FACT_RECONCILIATION_FAILED')
    payload=build_workbook_payload(records,sample_manifest,receipts,config['contract_id'])
    for item in payload['核对总览']:
        if item['项目']=='事实底座SHA-256': item['结果']=sha_file(fact_path)
    runtime=view['user_workbook']['runtime']
    node=Path(runtime['node_executable'])
    module=Path(runtime['artifact_tool_module'])
    if not node.is_file() or subprocess.run([str(node),'--version'],check=True,text=True,capture_output=True).stdout.strip()!=runtime['node_version']:
        raise RuntimeError('NODE_RUNTIME_IDENTITY_MISMATCH')
    verify_file_identity(module,{'bytes':runtime['artifact_tool_module_bytes'],'sha256':runtime['artifact_tool_module_sha256']},'artifact_tool_module')
    with tempfile.TemporaryDirectory(prefix='.view-build-',dir=target_dir) as temp_name:
        temp=Path(temp_name)
        ai_temp=temp/'ai.md'
        workbook_temp=temp/'user.xlsx'
        payload_path=temp/'workbook_payload.json'
        view_config_path=temp/'workbook_view_config.json'
        actual_preview_dir=Path(preview_dir).resolve() if preview_dir else temp/'previews'
        ai_temp.write_text(ai_text,encoding='utf-8',newline='\n')
        json_write(payload_path,payload)
        json_write(view_config_path,view['user_workbook'])
        node_result=subprocess.run(
            [str(node),'--input-type=module','-',str(module),str(payload_path),str(workbook_temp),str(actual_preview_dir),str(view_config_path)],
            input=WORKBOOK_RENDERER,
            text=True,
            capture_output=True,
        )
        if node_result.returncode!=0:
            raise RuntimeError(
                'USER_WORKBOOK_GENERATION_FAILED:'
                + canonical({
                    'returncode':node_result.returncode,
                    'stdout_tail':node_result.stdout[-4000:],
                    'stderr_tail':node_result.stderr[-4000:],
                })
            )
        stdout_lines=[line for line in node_result.stdout.splitlines() if line.strip()]
        if not stdout_lines:
            raise RuntimeError('USER_WORKBOOK_VERIFICATION_OUTPUT_MISSING')
        workbook_check=json.loads(stdout_lines[-1])
        if not workbook_check['all_pass']:
            raise RuntimeError('USER_WORKBOOK_RECONCILIATION_FAILED')
        os.replace(ai_temp,ai_output)
        os.replace(workbook_temp,workbook_output)
    result={
        'all_pass':True,
        'source_fact_base':str(fact_path),
        'fact_base_record_count':len(records),
        'fact_base_sha256':sha_file(fact_path),
        'view_content_sha256':hashlib.sha256(canonical(workbook_display_content(payload,view['user_workbook'])).encode('utf-8')).hexdigest(),
        'ai_view':{'path':str(ai_output),'bytes':ai_output.stat().st_size,'sha256':sha_file(ai_output),'record_order_exact':True},
        'user_workbook':{'path':str(workbook_output),'bytes':workbook_output.stat().st_size,'sha256':sha_file(workbook_output),**workbook_check},
        'one_command':view['command'],
    }
    if verification_output:
        json_write(Path(verification_output),result)
    print(canonical(result))

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
    v=sub.add_parser('build-views'); v.add_argument('--config',required=True); v.add_argument('--output-dir'); v.add_argument('--preview-dir'); v.add_argument('--verification-output')
    t=sub.add_parser('self-test'); t.add_argument('--tests',required=True)
    a=p.parse_args()
    if a.cmd=='load-selected-objects': load_selected_objects(a.receipts,a.output_dir)
    elif a.cmd=='build-bounded': build(a.config,a.samples,a.output)
    elif a.cmd=='build-views': build_views(a.config,a.output_dir,a.preview_dir,a.verification_output)
    else: run_tests(a.tests)
