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
from datetime import datetime, timedelta, timezone
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
    for fmt in ('%Y-%m-%d %H:%M:%S.%f','%Y-%m-%dT%H:%M:%S.%f','%Y-%m-%d %H:%M:%S','%Y-%m-%dT%H:%M:%S'):
        try: return datetime.strptime(value,fmt)
        except ValueError: pass
    m=re.match(r'^[A-Za-z]{3} ([A-Za-z]{3}) (\d{2}) (\d{4}) (\d{2}:\d{2}:\d{2}) GMT[+-]\d{4}',value)
    return datetime.strptime(' '.join(m.groups()),'%b %d %Y %H:%M:%S') if m else None

ALLOWED_EVIDENCE_STATUSES={
    'DIRECT','DETERMINISTIC_DERIVATION','BOUNDED','CANDIDATE',
    'UNKNOWN','NOT_APPLICABLE','NOT_EVALUATED',
}
ALLOWED_EXECUTION_STATUSES={
    'NOT_AUTHORIZED','AUTHORIZED_NOT_STARTED','RUNNING','BLOCKED',
    'FAILED','COMPLETED','NOT_APPLICABLE',
}
NUMERIC_FIELD_NAMES={
    'amount','total_asset_effect','quantity','order_quantity','executed_quantity',
    'price','order_price','trigger_price','fee','realized_pnl','commission',
    'funding_fee','known_net_effect_excluding_unknown_funding','position_before',
    'position_after','average_price_before','average_price_after','weighted_price',
    'notional','lifecycle_duration_seconds','fill_count',
}

def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()

def source_status_label(row):
    return str(row.get('evidence_level') or row.get('link_level') or row.get('reason_status') or 'SOURCE_RECORDED')

def normalized_evidence_status(label):
    upper=str(label or '').upper()
    if upper in ALLOWED_EVIDENCE_STATUSES: return upper
    if 'NOT_APPLICABLE' in upper: return 'NOT_APPLICABLE'
    if 'UNKNOWN' in upper or 'INSUFFICIENT' in upper: return 'UNKNOWN'
    if 'CANDIDATE' in upper or 'CONTEXT' in upper: return 'CANDIDATE'
    if 'DIRECT' in upper or upper.startswith('E1') or 'E1+' in upper: return 'DIRECT'
    if upper.startswith('E2') or upper.startswith('E3') or upper.startswith('F1'): return 'BOUNDED'
    return 'BOUNDED'

def decimal_candidate(field,value):
    if field not in NUMERIC_FIELD_NAMES and not any(token in field for token in ('price','quantity','amount','pnl','fee','notional','balance','equity','margin')):
        return value
    text=str(value)
    if not re.fullmatch(r'-?(?:\d+)(?:\.\d+)?',text): return value
    return decimal_text(text)

def normalize_row(row):
    return {key:decimal_candidate(key,value) for key,value in row.items()}

def normalize_business_value_tree(value):
    """Preserve JSON business numbers without binary-float or integer coercion."""
    if isinstance(value,bool) or value is None: return value
    if isinstance(value,(int,float,Decimal)): return decimal_text(value)
    if isinstance(value,list): return [normalize_business_value_tree(item) for item in value]
    if isinstance(value,dict): return {key:normalize_business_value_tree(item) for key,item in value.items()}
    return value

def time_identity(table,row):
    original=event_time(table,row)
    basis=str(row.get('time_basis') or 'SOURCE_TIME_BASIS_NOT_RECORDED')
    result={
        'original_value':original,
        'original_timezone':'UNKNOWN',
        'normalized_utc':None,
        'beijing_time':None,
        'precision':('MICROSECOND' if original and re.search(r'\d{2}:\d{2}:\d{2}\.\d+',original) else ('SECOND' if original and re.search(r'\d{2}:\d{2}:\d{2}',original) else ('UNKNOWN' if original else 'NOT_APPLICABLE'))),
        'timezone_basis':basis,
    }
    if not original: return result
    parsed=parse_time(original)
    if parsed is None: return result
    offset_minutes=None
    explicit=re.search(r'GMT([+-])(\d{2})(\d{2})',original)
    if explicit:
        sign=1 if explicit.group(1)=='+' else -1
        offset_minutes=sign*(int(explicit.group(2))*60+int(explicit.group(3)))
        result['original_timezone']=f'UTC{explicit.group(1)}{explicit.group(2)}:{explicit.group(3)}'
    elif basis=='SOURCE_BEIJING_LOCAL_TIME':
        offset_minutes=8*60; result['original_timezone']='Asia/Shanghai'
    elif basis in {'UTC','SOURCE_UTC','EXPLICIT_UTC'}:
        offset_minutes=0; result['original_timezone']='UTC'
    if offset_minutes is None: return result
    aware=parsed.replace(tzinfo=timezone(timedelta(minutes=offset_minutes)))
    utc_value=aware.astimezone(timezone.utc)
    beijing_value=aware.astimezone(timezone(timedelta(hours=8)))
    result['normalized_utc']=utc_value.strftime('%Y-%m-%d %H:%M:%S%z')
    result['beijing_time']=beijing_value.strftime('%Y-%m-%d %H:%M:%S%z')
    return result

def value_state(row):
    unknown=[]; candidates=[]; not_applicable=[]; intervals=[]
    for field,value in row.items():
        text=str(value or '')
        upper=text.upper()
        if upper=='UNKNOWN' or upper.startswith('UNKNOWN_'):
            unknown.append({'field':field,'status':'UNKNOWN','reason':row.get('reason_text') or row.get('notes') or 'SOURCE_RECORDED_UNKNOWN','missing_evidence':'源记录没有给出可确定值。','scope':row.get('position_cycle_id') or row.get('event_id') or 'CURRENT_RECORD'})
        if field.endswith('_candidates') and text:
            candidates.append({'field':field,'candidate_ids':[item for item in text.split('|') if item],'selection_status':'UNRESOLVED','evidence_for_each':'保留源字段中的全部候选；本程序不择一。'})
        if upper=='NOT_APPLICABLE' or upper.startswith('NOT_APPLICABLE_'):
            not_applicable.append({'field':field,'scope':row.get('event_id') or 'CURRENT_RECORD','reason':'SOURCE_RECORDED_NOT_APPLICABLE'})
        if field.endswith('_range') and text:
            intervals.append({'field':field,'raw_interval':text,'status':'SOURCE_INTERVAL_PRESERVED'})
    return {'unknown':unknown,'candidate_sets':candidates,'not_applicable':not_applicable,'intervals':intervals}

def currency_and_units(row):
    currency=row.get('currency') or row.get('fee_asset') or ('UNKNOWN' if any(k in row for k in ('amount','fee','realized_pnl','commission','funding_fee')) else 'NOT_APPLICABLE')
    units={}
    for field in row:
        if 'quantity' in field or field in {'position_before','position_after'}:
            units[field]='SOURCE_QUANTITY_UNIT_NOT_EXPLICIT'
        elif field in {'amount','total_asset_effect','fee','realized_pnl','commission','funding_fee','known_net_effect_excluding_unknown_funding'}:
            units[field]=currency
    return str(currency),units

PLAIN_VALUE_LABELS={
    'BUY':'买入','SELL':'卖出','LONG':'做多','SHORT':'做空',
    'LIMIT':'限价委托','MARKET':'市价委托',
    'OPEN_INITIAL':'首次开仓','ADD_POSITION':'加仓','REDUCE_POSITION':'减仓','CLOSE_FULL':'全部平仓',
    'OPEN_ATTEMPT':'尝试开仓','ADD_ATTEMPT':'尝试加仓','REDUCE_ATTEMPT':'尝试减仓','CLOSE_ATTEMPT':'尝试平仓',
    'CANCELED':'已取消','FILLED':'已成交','EXPIRED':'已过期','COMPLETED':'已完成',
    'EARN_REDEMPTION_PRINCIPAL':'理财赎回本金','EARN_SUBSCRIPTION_PRINCIPAL':'理财申购本金',
    'INTERNAL_TRANSFER_OUT':'内部转出','INTERNAL_TRANSFER_IN':'内部转入',
    'EXTERNAL_FUND':'外部资金事件','TRANSFER':'账户内部划转',
    'ORDER_FILL':'委托与成交的对应关系','CONDITIONAL_ORDER':'条件委托关系',
    'ORDER_POSITION_ACTION':'委托与仓位动作的对应关系','COPY_FUNDS_NODE':'跟单资金节点关系',
    'STABLE_KEY_DIRECT':'稳定关键字直接对应','STABLE_KEY_DIRECT_FUNDS_ONLY':'仅资金对象的稳定关键字直接对应',
    'STRONG_CONTEXT':'强上下文关系','DIRECT_ORDER':'委托直接对应','CANDIDATE':'候选关系',
    'EXECUTION_FACT_ONLY_NOT_INTENT_OR_PSYCHOLOGY':'只确认执行事实，不确认主观意图或心理',
    'SOURCE_FACT_LINK_LEVEL_PRESERVED_NO_PROMOTION':'保留来源事实和原关系等级，不升级为更强结论',
    'DIRECT_ORDER_FILL_POSITION_STATE':'委托、成交与仓位状态直接对应','DIRECT_FACT':'直接事实',
    'DIRECT_SOURCE_FACT_NO_CYCLE_CAUSAL_INFERENCE':'直接来源事实，不推断与交易周期的因果关系',
    'FUNDS_TRAJECTORY_ONLY':'只作为资金轨迹',
    'FIELD_PRESERVING_EVENT_PROJECTION':'原字段保留的事件投影',
    'PRESERVE_FROZEN_LIFECYCLE_AND_LINK_LEVEL_NO_PROMOTION':'保留已冻结生命周期和关系等级，不升级',
    'DIRECT_KEY_ENRICHMENT':'用直接关键字补全关联信息',
    'CONTEXT_LABEL_RETAINED_WITHOUT_DEFINITE_LINK':'保留上下文标签，但不写成确定归属',
    'PRESERVE_COPY_FUNDS_ONLY_BOUNDARY':'保留“仅跟单资金影响”边界',
    'PASS':'检查通过','LOADED_FOR_BOUNDED_CANDIDATE_TEST_ONLY':'仅为有界候选测试装载',
}

def plain_value(value,empty='未记录'):
    if value is None or value=='': return empty
    text=str(value)
    return PLAIN_VALUE_LABELS.get(text,text)

def selector_plain(value):
    try:
        selector=json.loads(value) if isinstance(value,str) else value
    except json.JSONDecodeError:
        return str(value)
    if not isinstance(selector,dict): return str(value)
    kind_labels={
        'CSV_FULL':'整份CSV','CSV_FULL_FILE_SUBOBJECT':'整份CSV作为一个输入对象',
        'CSV_FULL_BOUNDED_ROWS':'CSV中已限定的数据行','CSV_SELECTED_COLUMNS':'CSV指定字段',
        'CSV_FULL_TWO_VARIANTS':'CSV中两个合法候选','CSV_METHOD_SUPPORT':'CSV方法证据',
        'EXISTING_SELECTED_COLUMNS':'已有工作表的指定字段','XLSX_SHEET':'指定工作表',
        'XLSX_SHEETS':'多张指定工作表','JSON_FULL':'整份JSON','JSON_FULL_FILE_SUBOBJECT':'整份JSON作为一个输入对象',
        'JSON_SELECTED_FIELDS':'JSON指定字段','JSON_SELECTED_POINTERS':'JSON指定位置',
        'JSON_METHOD_OBJECT':'JSON方法对象','JSON_FULL_PRECISION_BOUNDARY':'JSON精度边界',
        'JSONL_FULL_FILE_SUBOBJECT':'整份JSONL作为一个输入对象','JSONL_FULL_LINEAGE_INTERFACE':'整份JSONL来源链接口',
        'IMAGE_VISIBLE_FIELD':'图片中的指定可见字段',
    }
    parts=[kind_labels.get(selector.get('kind'),selector.get('kind') or '已限定选择范围')]
    if selector.get('sheet'): parts.append('工作表：'+str(selector['sheet']))
    if selector.get('sheets'):
        parts.append('工作表：'+'、'.join(str(item.get('sheet') or '未命名') for item in selector['sheets']))
    if selector.get('range'): parts.append('范围：'+str(selector['range']))
    if selector.get('ranges'): parts.append('范围：'+'、'.join(map(str,selector['ranges'])))
    if selector.get('row_count') is not None: parts.append('记录数：'+str(selector['row_count']))
    selected=selector.get('columns') or selector.get('include_fields') or selector.get('fields') or selector.get('json_pointers')
    if selected:
        count=len(selected) if isinstance(selected,(dict,list)) else 1
        parts.append(f'只取{count}个已点名字段或位置')
    excluded=selector.get('excluded_columns') or selector.get('excluded_fields') or selector.get('excluded_pointers')
    if excluded:
        count=len(excluded) if isinstance(excluded,(dict,list)) else 1
        parts.append(f'排除{count}个已点名字段或位置')
    if selector.get('boundary'): parts.append('边界：'+str(selector['boundary']))
    return '；'.join(parts)

def plain_summary(table,row):
    symbol=row.get('symbol') or '未注明品种'
    if table=='order':
        return f'{symbol}委托：{plain_value(row.get("side"),"方向未知")} {plain_value(row.get("order_type"),"类型未知")}，委托量{row.get("order_quantity") or "未知"}，成交量{row.get("executed_quantity") or "未知"}，状态{plain_value(row.get("status"),"未知")}。'
    if table=='fill':
        return f'{symbol}成交：{plain_value(row.get("position_action"),"动作未知")}，数量{row.get("quantity") or "未知"}，价格{row.get("price") or "未知"}，手续费{row.get("fee") or "未知"} {row.get("fee_asset") or "币种未知"}。'
    if table=='position':
        return f'{symbol}仓位动作：{plain_value(row.get("action_type"),"动作未知")}，仓位从{row.get("position_before") or "未知"}变为{row.get("position_after") or "未知"}，加权价格{row.get("weighted_price") or "未知"}。'
    if table=='condition':
        return f'{symbol}条件委托：{row.get("condition_role") or "角色未知"}/{row.get("condition_type") or "类型未知"}，触发价{row.get("trigger_price") or "未知"}，最终{row.get("raw_status") or row.get("status") or "状态未知"}。'
    if table=='fund':
        return f'账户资金事件：{plain_value(row.get("fund_event_subtype") or row.get("fund_event_type"),"类型未知")}，金额{row.get("amount") or "未知"} {row.get("currency") or "币种未知"}，总资产影响{row.get("total_asset_effect") or "未知"}。'
    if table=='copy':
        return f'跟单资金影响：{symbol} {plain_value(row.get("direction"),"方向未知")}，已知净影响{row.get("known_net_effect_excluding_unknown_funding") or "未知"}，资金费{row.get("funding_fee") or "未知"}。'
    if table=='linkage':
        return f'关系：{row.get("source_event_id") or row.get("source_object_id") or "来源未知"} —{plain_value(row.get("link_scope"),"关系类型未知")}/{plain_value(row.get("link_level"),"等级未知")}→ {row.get("target_event_id") or row.get("target_object_id") or "目标未知"}。'
    if table=='lineage':
        return f'来源追溯：{row.get("event_id") or "事件未知"}来自{Path(row.get("source_path") or "来源未知").name}，{row.get("source_sheet") or "表未知"}第{row.get("source_row") or "未知"}行。'
    return '方法证据：保留获准方法、多个合法候选和证明边界；没有运行真实业务重新计算。'

def source_identity(source,path,row_no,selector):
    path=Path(path)
    return {
        'source_identity_id':stable_id('SRC',source['sha256'],str(path),selector if isinstance(selector,str) else canonical(selector)),
        'source_path':str(path),
        'source_bytes':source['bytes'],
        'source_sha256':source['sha256'],
        'source_locator':None if row_no is None else f'data-row-{row_no}',
        'selector':selector,
        'selected_input_id':source.get('input_id'),
        'selected_object_index':source.get('selected_object_index'),
        'selected_mirror_path':source.get('mirror_path'),
        'selected_content_sha256':source.get('selected_content_sha256'),
    }

def validate_selected_payload(receipt,payload):
    selector=receipt['original_selector']; kind=selector.get('kind') or ('XLSX_SHEETS' if 'sheets' in selector else 'XLSX_SHEET')
    if kind=='JSON_SELECTED_POINTERS':
        expected_keys=list(selector['json_pointers'])
        if not isinstance(payload,dict) or set(payload)!=set(expected_keys) or len(payload)!=len(expected_keys):
            raise RuntimeError('SELECTED_POINTER_SET_MISMATCH:'+receipt['input_id'])
        payload={pointer:payload[pointer] for pointer in expected_keys}
        encoded=(json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8')
        actual=len(payload); content_sha=sha_bytes(encoded)
    elif kind in {'CSV_FULL_TWO_VARIANTS','CSV_FULL','CSV_FULL_FILE_SUBOBJECT','CSV_METHOD_SUPPORT','CSV_FULL_BOUNDED_ROWS'}:
        if not isinstance(payload,list): raise RuntimeError('SELECTED_CSV_PAYLOAD_INVALID:'+receipt['input_id'])
        actual=len(payload); content_sha=receipt['extracted_content_sha256']
    else:
        raise RuntimeError('METHOD_SELECTOR_KIND_NOT_ALLOWED:'+kind)
    if actual!=receipt['actual_count'] or content_sha!=receipt['extracted_content_sha256']:
        raise RuntimeError('SELECTED_EXTRACTION_MISMATCH:'+receipt['input_id'])
    return payload

def selected_payload(receipt):
    mirror=Path(receipt['mirror_path']); selector=receipt['original_selector']
    if not mirror.is_file() or sha_file(mirror)!=receipt['extracted_content_sha256']:
        raise RuntimeError('SELECTED_MIRROR_IDENTITY_MISMATCH:'+receipt['input_id'])
    kind=selector.get('kind') or ('XLSX_SHEETS' if 'sheets' in selector else 'XLSX_SHEET')
    if kind=='JSON_SELECTED_POINTERS':
        payload=json.load(open(mirror,encoding='utf-8'))
    elif kind in {'CSV_FULL_TWO_VARIANTS','CSV_FULL','CSV_FULL_FILE_SUBOBJECT','CSV_METHOD_SUPPORT','CSV_FULL_BOUNDED_ROWS'}:
        payload=read_csv(mirror)
    else:
        raise RuntimeError('METHOD_SELECTOR_KIND_NOT_ALLOWED:'+kind)
    return validate_selected_payload(receipt,payload)

def recompute_target_minute_mark_synthetic(node_time_utc,source_available,quantity,contract_multiplier,entry_price,mark_low,mark_high,side):
    if source_available is not True: raise ValueError('SYNTHETIC_MARK_SOURCE_UNAVAILABLE')
    node_time=parse_time(node_time_utc)
    if node_time is None: raise ValueError('SYNTHETIC_NODE_TIME_INVALID')
    target_minute=node_time.replace(second=0,microsecond=0).strftime('%Y-%m-%d %H:%M:00')
    q=Decimal(str(quantity)); m=Decimal(str(contract_multiplier)); entry=Decimal(str(entry_price)); low=Decimal(str(mark_low)); high=Decimal(str(mark_high))
    if low>high: raise ValueError('SYNTHETIC_MARK_RANGE_REVERSED')
    if side=='LONG': lower=q*m*(low-entry); upper=q*m*(high-entry)
    elif side=='SHORT': lower=q*m*(entry-high); upper=q*m*(entry-low)
    else: raise ValueError('SYNTHETIC_SIDE_UNSUPPORTED')
    return {'target_minute_utc':target_minute,'mark_low':format(low,'f'),'mark_high':format(high,'f'),'lower':format(lower,'f'),'upper':format(upper,'f'),'source_available':True,'status':'FICTIONAL_TEST_ONLY_NOT_FORMAL_RESULT'}

def recompute_t087_outer_envelope_synthetic(paths):
    if len(paths)!=2 or {item['path_id'] for item in paths}!={'PATH_A','PATH_B'}: raise ValueError('SYNTHETIC_T087_REQUIRES_TWO_PATHS')
    event_sets=[list(item.get('source_event_ids') or []) for item in paths]
    if not event_sets[0] or event_sets[0]!=event_sets[1]: raise ValueError('SYNTHETIC_T087_EVENT_SET_MISMATCH')
    if len(event_sets[0])!=len(set(event_sets[0])): raise ValueError('SYNTHETIC_T087_DUPLICATE_EVENT')
    lower=min(Decimal(str(item['lower'])) for item in paths); upper=max(Decimal(str(item['upper'])) for item in paths)
    if any(lower>Decimal(str(item['lower'])) or upper<Decimal(str(item['upper'])) for item in paths): raise ValueError('SYNTHETIC_T087_OUTER_ENVELOPE_INVALID')
    return {'paths':paths,'source_event_ids':event_sets[0],'outer_lower':format(lower,'f'),'outer_upper':format(upper,'f'),'unique_order_proven':False,'status':'FICTIONAL_TEST_ONLY_NOT_FORMAL_RESULT'}

def recompute_joint_interval_synthetic(affected_node_id,currency,precision,input_fact_ids,run_id,method_objects,opening_interval,delta_intervals):
    if not affected_node_id or not currency or not precision or not run_id: raise ValueError('SYNTHETIC_JOINT_INTERVAL_IDENTITY_MISSING')
    if not input_fact_ids or len(input_fact_ids)!=len(set(input_fact_ids)): raise ValueError('SYNTHETIC_JOINT_INTERVAL_INPUT_FACTS_INVALID')
    if len(method_objects)!=5 or len(set(method_objects))!=5: raise ValueError('SYNTHETIC_JOINT_INTERVAL_REQUIRES_FIVE_METHOD_OBJECTS')
    lower=Decimal(str(opening_interval['lower'])); upper=Decimal(str(opening_interval['upper']))
    for item in delta_intervals:
        lower+=Decimal(str(item['lower'])); upper+=Decimal(str(item['upper']))
    if lower>upper: raise ValueError('SYNTHETIC_JOINT_INTERVAL_INVALID')
    return {'affected_node_id':affected_node_id,'lower':format(lower,'f'),'upper':format(upper,'f'),'currency':currency,'precision':precision,'input_fact_ids':input_fact_ids,'run_id':run_id,'method_object_count':'5','status':'FICTIONAL_TEST_ONLY_NOT_FORMAL_RESULT'}

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

def verify_sources(config,receipts):
    receipt_map={(item['input_id'],int(item['selected_object_index'])):item for item in receipts}
    verified={}
    for name,item in config['bounded_sample_sources'].items():
        key=(item.get('input_id'),int(item.get('selected_object_index',-1)))
        receipt=receipt_map.get(key)
        if receipt is None or receipt['source_path']!=item['path'] or receipt['actual_bytes']!=item['bytes'] or receipt['actual_sha256']!=item['sha256']:
            raise RuntimeError('SOURCE_RECEIPT_IDENTITY_MISMATCH:'+name)
        mirror=Path(receipt['mirror_path'])
        if not mirror.is_file() or sha_file(mirror)!=receipt['extracted_content_sha256']:
            raise RuntimeError('SOURCE_MIRROR_IDENTITY_MISMATCH:'+name)
        verified[name]={
            **item,
            'mirror_path':str(mirror),
            'selected_content_sha256':receipt['extracted_content_sha256'],
            'input_id':receipt['input_id'],
            'selected_object_index':int(receipt['selected_object_index']),
        }
    if str(config['forbidden_extra_sample_summary']) in {x['path'] for x in config['bounded_sample_sources'].values()}:
        raise RuntimeError('FORBIDDEN_SUMMARY_INCLUDED')
    return verified

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

def resolve_config_file(config_path,item):
    path=Path(item['path'])
    if not path.is_absolute(): path=Path(config_path).resolve().parent/path
    return path

def verify_config_file(config_path,item,label):
    path=resolve_config_file(config_path,item)
    verify_file_identity(path,item,label)
    return path

def validate_gap_mapping(gap_records,stage3_records):
    expected=stage3_records[446:465]
    if len(expected)!=19 or any(item.get('record_type')!='STAGE3_PRE_GAP_ADJUDICATION' for item in expected):
        raise RuntimeError('STAGE3_GAP_REFERENCE_RANGE_INVALID')
    if len(gap_records)!=19: raise RuntimeError('GAP_MAPPING_COUNT_MISMATCH')
    for index,(actual,source) in enumerate(zip(gap_records,expected),1):
        checks={
            'object_id':f'GAP-{index:02d}',
            'source_stage3_line':446+index,
            'source_stage3_record_id':source['record_id'],
            'source_stage3_capability_id':source['capability_id'],
            'source_stage3_missing_statement':source['what_is_missing'],
        }
        for field,value in checks.items():
            if actual.get(field)!=value:
                raise RuntimeError(f'GAP_MAPPING_SEMANTIC_MISMATCH:{actual.get("object_id")}:{field}')
    return {'gap_count':19,'stage3_lines':'447-465','semantic_pairing_exact':True}

def receipt_schema_fields(receipt):
    selector=receipt['original_selector']
    mirror=Path(receipt['mirror_path'])
    if not mirror.is_file(): raise RuntimeError('CAPABILITY_RECEIPT_MIRROR_MISSING:'+str(mirror))
    if sha_file(mirror)!=receipt.get('extracted_content_sha256'):
        raise RuntimeError('CAPABILITY_RECEIPT_MIRROR_IDENTITY_MISMATCH:'+str(mirror))
    if selector.get('kind')=='JSON_SELECTED_POINTERS':
        return set(selector['json_pointers'])
    if mirror.suffix=='.csv':
        with open(mirror,encoding='utf-8-sig',newline='') as handle:
            return set(next(csv.reader(handle)))
    if mirror.suffix=='.jsonl':
        with open(mirror,encoding='utf-8') as handle:
            first=next((json.loads(line) for line in handle if line.strip()),{})
        return set(first)
    if mirror.suffix=='.json':
        value=json.load(open(mirror,encoding='utf-8'))
        return (set(value)|{'/'+str(key) for key in value}) if isinstance(value,dict) else set()
    raise RuntimeError('CAPABILITY_RECEIPT_MIRROR_TYPE_UNSUPPORTED:'+mirror.suffix)

def validate_capability_specs(capability_records,adoption_records,schema,receipts):
    if len(capability_records)!=94: raise RuntimeError('CAPABILITY_SPEC_COUNT_MISMATCH')
    ids=[item['object_id'] for item in capability_records]
    if len(set(ids))!=94: raise RuntimeError('CAPABILITY_SPEC_ID_DUPLICATE')
    input_ids={item['input_id'] for item in adoption_records}
    allowed_output_roots=set(schema['information_layers'])|{'objective_chain','candidate_capabilities','facts','relations','boundaries','capabilities'}
    receipt_map={(item['input_id'],int(item['selected_object_index'])):item for item in receipts}
    required_check_kinds={
        'SOURCE_BINDING_INPUT_IDS_EQUAL_DECLARED_MAIN_SUPPLEMENT_AND_VERIFICATION_SET',
        'CAPABILITY_OUTPUT_PATH_EQUALS_DECLARED_OUTPUT_LOCATION',
        'ROW_ORDER_OR_SIMILAR_TEXT_JOIN_IS_FORBIDDEN',
        'UNRESOLVED_OR_PENDING_CAPABILITY_CANNOT_EMIT_CONFIRMED_FACT',
        'EACH_EMITTED_FACT_HAS_INPUT_ID_SELECTED_OBJECT_INDEX_AND_SOURCE_LOCATOR',
    }
    required_missing_join_key_behavior=(
        'KEEP_SOURCE_FACTS_SEPARATE_AND_MARK_RELATION_UNKNOWN; '
        'NEVER_JOIN_BY_ROW_ORDER_OR_SIMILAR_TEXT'
    )
    status_counts=Counter(); binding_count=0; field_binding_count=0
    for item in capability_records:
        spec=item.get('assembly_spec')
        if not isinstance(spec,dict): raise RuntimeError('CAPABILITY_ASSEMBLY_SPEC_MISSING:'+item['object_id'])
        bindings=spec.get('source_bindings')
        if not isinstance(bindings,list): raise RuntimeError('CAPABILITY_SOURCE_BINDINGS_MISSING:'+item['object_id'])
        if not bindings and not any(token in item.get('closure_status','') for token in ('LIMITATION','PARTIAL','UNRESOLVED','NON_OBJECTIVE_BOUNDARY','PENDING_USER_ACCEPTANCE')):
            raise RuntimeError('CAPABILITY_SOURCE_BINDINGS_EMPTY_WITH_CLOSED_STATUS:'+item['object_id'])
        roles=set(); actual_by_role=defaultdict(set); binding_scope={}
        for binding in bindings:
            if binding.get('input_id') not in input_ids: raise RuntimeError('CAPABILITY_UNKNOWN_INPUT:'+item['object_id'])
            if binding.get('role') not in {'MAIN','SUPPLEMENT','VERIFICATION'}: raise RuntimeError('CAPABILITY_SOURCE_ROLE_INVALID:'+item['object_id'])
            roles.add(binding['role'])
            actual_by_role[binding['role']].add(binding['input_id'])
            if not binding.get('selected_object_indexes'): raise RuntimeError('CAPABILITY_SELECTED_OBJECT_INDEX_MISSING:'+item['object_id'])
            if not binding.get('source_fields'): raise RuntimeError('CAPABILITY_SOURCE_FIELDS_MISSING:'+item['object_id'])
            if not binding.get('selector_reference'): raise RuntimeError('CAPABILITY_SELECTOR_REFERENCE_MISSING:'+item['object_id'])
            for selected_index in binding['selected_object_indexes']:
                key=(binding['input_id'],int(selected_index))
                if key not in receipt_map: raise RuntimeError('CAPABILITY_RECEIPT_NOT_FOUND:'+item['object_id']+':'+str(key))
                receipt=receipt_map[key]
                if binding.get('source_path')!=receipt.get('source_path'):
                    raise RuntimeError('CAPABILITY_SOURCE_PATH_RECEIPT_MISMATCH:'+item['object_id']+':'+str(key))
                expected_selector_sha=hashlib.sha256(canonical(receipt['original_selector']).encode('utf-8')).hexdigest()
                if binding['selector_reference'].get('selector_sha256')!=expected_selector_sha:
                    raise RuntimeError('CAPABILITY_SELECTOR_IDENTITY_MISMATCH:'+item['object_id']+':'+str(key))
                if int(binding['selector_reference'].get('selected_object_index',-1))!=int(selected_index):
                    raise RuntimeError('CAPABILITY_SELECTOR_OBJECT_INDEX_MISMATCH:'+item['object_id']+':'+str(key))
                missing=set(binding['source_fields'])-receipt_schema_fields(receipt)
                if missing: raise RuntimeError('CAPABILITY_SOURCE_FIELD_MISSING:'+item['object_id']+':'+','.join(sorted(missing)))
                binding_scope[(binding['input_id'],int(selected_index))]=set(binding['source_fields'])
                binding_count+=1; field_binding_count+=len(binding['source_fields'])
        declared={
            'MAIN':[] if item.get('unique_main_source_candidate') is None else ([item['unique_main_source_candidate']] if isinstance(item['unique_main_source_candidate'],str) else item['unique_main_source_candidate']),
            'SUPPLEMENT':item.get('supplement_source_candidates') or [],
            'VERIFICATION':item.get('verification_source_candidates') or [],
        }
        for role,expected_ids in declared.items():
            if set(expected_ids)!=actual_by_role.get(role,set()):
                raise RuntimeError('CAPABILITY_DECLARED_SOURCE_SET_MISMATCH:'+item['object_id']+':'+role)
        if bindings and 'MAIN' not in roles: raise RuntimeError('CAPABILITY_MAIN_SOURCE_MISSING:'+item['object_id'])
        detailed_bindings=item.get('source_bindings')
        if not isinstance(detailed_bindings,list):
            raise RuntimeError('CAPABILITY_DETAILED_SOURCE_BINDINGS_MISSING:'+item['object_id'])
        assembly_binding_rows=sorted(
            (binding['input_id'],binding['role'],int(index),binding['selector_reference']['selector_sha256'],tuple(binding['source_fields']))
            for binding in bindings for index in binding['selected_object_indexes']
        )
        detailed_binding_rows=sorted(
            (binding.get('input_id'),binding.get('source_role'),int(binding.get('selected_object_index',-1)),binding.get('selector_sha256'),tuple(binding.get('source_fields_or_pointers') or []))
            for binding in detailed_bindings
        )
        if assembly_binding_rows!=detailed_binding_rows:
            raise RuntimeError('CAPABILITY_DETAILED_BINDING_MISMATCH:'+item['object_id'])
        output=item.get('capability_output')
        if not isinstance(output,dict) or item.get('output_location')!=output.get('path'):
            raise RuntimeError('CAPABILITY_OUTPUT_PATH_DECLARATION_MISMATCH:'+item['object_id'])
        expected_target_fields=output.get('fields') or []
        for detailed in detailed_bindings:
            key=(detailed.get('input_id'),int(detailed.get('selected_object_index',-1)))
            receipt=receipt_map.get(key)
            if receipt is None:
                raise RuntimeError('CAPABILITY_DETAILED_RECEIPT_NOT_FOUND:'+item['object_id']+':'+str(key))
            selector=receipt.get('original_selector') or {}
            expected_selector_kind=selector.get('kind') or ('XLSX_SHEETS' if selector.get('sheets') else 'XLSX_SHEET' if selector.get('sheet') else None)
            if detailed.get('selector_kind')!=expected_selector_kind:
                raise RuntimeError('CAPABILITY_DETAILED_SELECTOR_KIND_MISMATCH:'+item['object_id']+':'+str(key))
            source_fields=detailed.get('source_fields_or_pointers') or []
            expected_field_sha=hashlib.sha256(canonical(source_fields).encode('utf-8')).hexdigest()
            if detailed.get('source_fields_or_pointers_sha256')!=expected_field_sha:
                raise RuntimeError('CAPABILITY_DETAILED_FIELD_HASH_MISMATCH:'+item['object_id']+':'+str(key))
            if detailed.get('target_fields')!=expected_target_fields:
                raise RuntimeError('CAPABILITY_DETAILED_TARGET_FIELDS_MISMATCH:'+item['object_id']+':'+str(key))
            expected_assertions={
                'INPUT_ID_EXISTS_IN_ADOPTION_LIST':True,
                'SELECTED_OBJECT_RECEIPT_EXISTS':True,
                'CANONICAL_SELECTOR_SHA256_EQUALS_RECEIPT':hashlib.sha256(canonical(selector).encode('utf-8')).hexdigest(),
                'SELECTED_FIELD_OR_POINTER_LIST_SHA256_EQUALS_MIRROR_SCHEMA':expected_field_sha,
                'DECLARED_JOIN_KEY_FIELDS_EXIST_IN_SELECTED_SCOPE':True,
            }
            assertions=detailed.get('check_assertions')
            if not isinstance(assertions,list) or len(assertions)!=len(expected_assertions):
                raise RuntimeError('CAPABILITY_DETAILED_CHECK_SET_INVALID:'+item['object_id']+':'+str(key))
            actual_assertions={assertion.get('kind'):assertion.get('expected') for assertion in assertions}
            if actual_assertions!=expected_assertions or len(actual_assertions)!=len(assertions):
                raise RuntimeError('CAPABILITY_DETAILED_CHECK_EXPECTATION_MISMATCH:'+item['object_id']+':'+str(key))
            expected_check_ids={
                kind:f'{item["object_id"]}::{key[0]}::{key[1]}::{suffix}'
                for kind,suffix in {
                    'INPUT_ID_EXISTS_IN_ADOPTION_LIST':'INPUT_DECLARED',
                    'SELECTED_OBJECT_RECEIPT_EXISTS':'RECEIPT_MATCH',
                    'CANONICAL_SELECTOR_SHA256_EQUALS_RECEIPT':'SELECTOR_MATCH',
                    'SELECTED_FIELD_OR_POINTER_LIST_SHA256_EQUALS_MIRROR_SCHEMA':'FIELD_SCOPE_MATCH',
                    'DECLARED_JOIN_KEY_FIELDS_EXIST_IN_SELECTED_SCOPE':'JOIN_KEYS_EXIST',
                }.items()
            }
            if {assertion.get('kind'):assertion.get('check_id') for assertion in assertions}!=expected_check_ids:
                raise RuntimeError('CAPABILITY_DETAILED_CHECK_ID_MISMATCH:'+item['object_id']+':'+str(key))
        contract=item.get('assembly_contract')
        if not isinstance(contract,dict): raise RuntimeError('CAPABILITY_ASSEMBLY_CONTRACT_MISSING:'+item['object_id'])
        join=spec.get('join')
        if not isinstance(join,dict) or 'required' not in join: raise RuntimeError('CAPABILITY_JOIN_SPEC_MISSING:'+item['object_id'])
        if not join.get('operator') or join['operator']!=contract.get('operator'):
            raise RuntimeError('CAPABILITY_JOIN_OPERATOR_MISMATCH:'+item['object_id'])
        if join.get('missing_join_key_behavior')!=contract.get('missing_join_key_behavior'):
            raise RuntimeError('CAPABILITY_MISSING_JOIN_KEY_BEHAVIOR_MISMATCH:'+item['object_id'])
        if join.get('missing_join_key_behavior')!=required_missing_join_key_behavior:
            raise RuntimeError('CAPABILITY_MISSING_JOIN_KEY_BEHAVIOR_INVALID:'+item['object_id'])
        if join.get('direction')!=contract.get('relation_direction') or join.get('cardinality')!=contract.get('cardinality'):
            raise RuntimeError('CAPABILITY_JOIN_CONTRACT_MISMATCH:'+item['object_id'])
        if canonical(join.get('keys') or [])!=canonical(contract.get('join_key_families') or []):
            raise RuntimeError('CAPABILITY_JOIN_KEYS_CONTRACT_MISMATCH:'+item['object_id'])
        for detailed in detailed_bindings:
            relation=detailed.get('relation') or {}
            if relation.get('operator')!=join.get('operator') or relation.get('direction')!=join.get('direction') or relation.get('cardinality')!=join.get('cardinality'):
                raise RuntimeError('CAPABILITY_DETAILED_RELATION_MISMATCH:'+item['object_id'])
            key=(detailed.get('input_id'),int(detailed.get('selected_object_index',-1)))
            expected_join_keys=sorted(
                (family['canonical_key'],alias['source_field'])
                for family in join.get('keys') or [] for alias in family.get('verified_source_aliases') or []
                if (alias.get('input_id'),int(alias.get('selected_object_index',-1)))==key
            )
            actual_join_keys=sorted((value.get('canonical_key'),value.get('source_field')) for value in detailed.get('join_keys') or [])
            if expected_join_keys!=actual_join_keys:
                raise RuntimeError('CAPABILITY_DETAILED_JOIN_KEY_MISMATCH:'+item['object_id']+':'+str(key))
        if join['required']:
            if not join.get('keys') or not join.get('direction') or not join.get('cardinality'):
                raise RuntimeError('CAPABILITY_JOIN_DETAIL_MISSING:'+item['object_id'])
        elif not join.get('reason'):
            raise RuntimeError('CAPABILITY_JOIN_NA_REASON_MISSING:'+item['object_id'])
        for key_family in join.get('keys') or []:
            if not key_family.get('canonical_key') or not key_family.get('verified_source_aliases'):
                raise RuntimeError('CAPABILITY_JOIN_KEY_FAMILY_INVALID:'+item['object_id'])
            for alias in key_family['verified_source_aliases']:
                key=(alias.get('input_id'),int(alias.get('selected_object_index',-1)))
                if key not in binding_scope or alias.get('source_field') not in binding_scope[key]:
                    raise RuntimeError('CAPABILITY_JOIN_ALIAS_OUTSIDE_BINDING:'+item['object_id']+':'+str(key)+':'+str(alias.get('source_field')))
        outputs=spec.get('output_fields')
        if not isinstance(outputs,list) or not outputs: raise RuntimeError('CAPABILITY_OUTPUT_FIELDS_MISSING:'+item['object_id'])
        if any(not isinstance(value,str) or '.' not in value for value in outputs):
            raise RuntimeError('CAPABILITY_OUTPUT_FIELD_INVALID:'+item['object_id'])
        if any(value.split('.',1)[0] not in allowed_output_roots for value in outputs):
            raise RuntimeError('CAPABILITY_OUTPUT_ROOT_INVALID:'+item['object_id'])
        expected_outputs=[output['path']+'.'+field for field in output.get('fields') or []]
        if outputs!=expected_outputs:
            raise RuntimeError('CAPABILITY_OUTPUT_FIELDS_DECLARATION_MISMATCH:'+item['object_id'])
        checks=spec.get('executable_checks')
        if not isinstance(checks,list) or not checks: raise RuntimeError('CAPABILITY_EXECUTABLE_CHECK_MISSING:'+item['object_id'])
        if set(checks)!=required_check_kinds or len(checks)!=len(required_check_kinds):
            raise RuntimeError('CAPABILITY_EXECUTABLE_CHECK_SET_INVALID:'+item['object_id'])
        declared_checks=item.get('executable_checks')
        if not isinstance(declared_checks,list) or {check.get('kind') for check in declared_checks}!=required_check_kinds or len(declared_checks)!=len(required_check_kinds):
            raise RuntimeError('CAPABILITY_DECLARED_CHECK_SET_INVALID:'+item['object_id'])
        check_map={check['kind']:check for check in declared_checks}
        declared_source_ids=sorted(set().union(*actual_by_role.values())) if actual_by_role else []
        if sorted(check_map['SOURCE_BINDING_INPUT_IDS_EQUAL_DECLARED_MAIN_SUPPLEMENT_AND_VERIFICATION_SET'].get('expected') or [])!=declared_source_ids:
            raise RuntimeError('CAPABILITY_SOURCE_CHECK_EXPECTATION_MISMATCH:'+item['object_id'])
        if check_map['CAPABILITY_OUTPUT_PATH_EQUALS_DECLARED_OUTPUT_LOCATION'].get('expected')!=output['path']:
            raise RuntimeError('CAPABILITY_OUTPUT_CHECK_EXPECTATION_MISMATCH:'+item['object_id'])
        if check_map['ROW_ORDER_OR_SIMILAR_TEXT_JOIN_IS_FORBIDDEN'].get('expected') is not True:
            raise RuntimeError('CAPABILITY_ROW_ORDER_CHECK_EXPECTATION_MISMATCH:'+item['object_id'])
        if check_map['EACH_EMITTED_FACT_HAS_INPUT_ID_SELECTED_OBJECT_INDEX_AND_SOURCE_LOCATOR'].get('expected') is not True:
            raise RuntimeError('CAPABILITY_LINEAGE_CHECK_EXPECTATION_MISMATCH:'+item['object_id'])
        no_confirmed_fact=item.get('closure_status') in {
            'UNRESOLVED_PRESERVED_NO_FACT_CLOSURE',
            'NON_OBJECTIVE_BOUNDARY_CLOSED_NO_FACT_OUTPUT',
            'PENDING_USER_ACCEPTANCE_NO_PRODUCTION_CLOSURE',
        }
        if check_map['UNRESOLVED_OR_PENDING_CAPABILITY_CANNOT_EMIT_CONFIRMED_FACT'].get('expected') is not no_confirmed_fact:
            raise RuntimeError('CAPABILITY_UNRESOLVED_GATE_EXPECTATION_MISMATCH:'+item['object_id'])
        sample_status=spec.get('bounded_sample_status')
        if sample_status not in {'NOT_YET_RUN','NOT_YET_RUN_GAP_MUST_REMAIN_EXPLICIT','NOT_APPLICABLE_BOUNDARY_ONLY','NOT_AUTHORIZED_PENDING_USER_ACCEPTANCE'}:
            raise RuntimeError('CAPABILITY_SAMPLE_STATUS_INVALID:'+item['object_id'])
        status_counts[sample_status]+=1
    return {
        'capability_count':94,
        'source_binding_applications_checked':binding_count,
        'source_fields_checked':field_binding_count,
        'bounded_sample_status_counts':dict(sorted(status_counts.items())),
        'all_specs_machine_valid':True,
        'candidate_specs_are_not_formal_adoption':True,
    }

def validate_recomputation_contracts(contract,receipts):
    if contract.get('real_business_run_authorized') is not False:
        raise RuntimeError('REAL_RECOMPUTATION_AUTHORIZATION_MUST_BE_FALSE')
    items=contract.get('items') or []
    by_id={item.get('recomputation_id'):item for item in items}
    if set(by_id)!={'S3INPUT-40','S3INPUT-41','S3INPUT-42'} or len(items)!=3:
        raise RuntimeError('RECOMPUTATION_CONTRACT_ID_SET_INVALID')
    required={
        'S3INPUT-40':{
            'formula':{
                'aggregation':'CONSERVATIVE_OUTER_BOUND',
                'long_upnl_lower':'quantity * contract_multiplier * (mark_low - entry_price)',
                'long_upnl_upper':'quantity * contract_multiplier * (mark_high - entry_price)',
                'minute':'floor(node_time_utc/60000ms)',
                'short_upnl_lower':'quantity * contract_multiplier * (entry_price - mark_high)',
                'short_upnl_upper':'quantity * contract_multiplier * (entry_price - mark_low)',
            },
            'output':['target_key','target_minute_utc','mark_low','mark_high','source_file_sha256','precision'],
            'checks':['11份输入身份一致','58目标键唯一','分钟闭开区间正确','不得用minute close代替区间','无行情即停止该目标'],
        },
        'S3INPUT-41':{
            'formula':'分别按PATH_A和PATH_B计算相同输出字段；外包络lower=min(A.lower,B.lower)，upper=max(A.upper,B.upper)。',
            'output':['path_A','path_B','outer_lower','outer_upper','unique_order_proven=false','source_event_ids'],
            'checks':['两条路径都存在','同一事件不重复','外包络包含两条路径','不出现唯一真实顺序主张'],
        },
        'S3INPUT-42':{
            'formula':'以期初域和纠正证据为输入，按冻结传播规则形成每个受影响节点的联合lower/upper；具体公式以五个获准方法对象为唯一来源。',
            'output':['affected_node_id','lower','upper','currency','precision','input_fact_ids','run_id'],
            'checks':['受影响节点唯一列清','权威资金与收益输入身份一致','币种单位不丢失','旧结果不进入当前输出','区间包含全部合法传播结果'],
        },
    }
    for recomputation_id,rules in required.items():
        item=by_id[recomputation_id]
        if item.get('status')!='PREPARATION_CANDIDATE_NOT_RUN':
            raise RuntimeError('RECOMPUTATION_STATUS_INVALID:'+recomputation_id)
        if not item.get('formula') or not item.get('failure') or not item.get('method_selected_objects'):
            raise RuntimeError('RECOMPUTATION_METHOD_CONTRACT_INCOMPLETE:'+recomputation_id)
        if item.get('formula')!=rules['formula'] or item.get('output')!=rules['output'] or item.get('check')!=rules['checks']:
            raise RuntimeError('RECOMPUTATION_OUTPUT_OR_CHECK_MISMATCH:'+recomputation_id)
    if len(by_id['S3INPUT-40']['method_selected_objects'])!=1 or len(by_id['S3INPUT-41']['method_selected_objects'])!=2 or len(by_id['S3INPUT-42']['method_selected_objects'])!=5:
        raise RuntimeError('RECOMPUTATION_METHOD_OBJECT_COUNT_INVALID')
    receipt_map={(item['input_id'],int(item['selected_object_index'])):item for item in receipts}
    for recomputation_id,item in by_id.items():
        seen=set()
        for method_object in item['method_selected_objects']:
            key=(recomputation_id,int(method_object.get('selected_object_index',-1)))
            if key in seen or key not in receipt_map:
                raise RuntimeError('RECOMPUTATION_METHOD_RECEIPT_NOT_UNIQUE:'+str(key))
            seen.add(key); receipt=receipt_map[key]
            checks={
                'source_path':receipt['source_path'],
                'bytes':receipt['actual_bytes'],
                'sha256':receipt['actual_sha256'],
                'actual_count':receipt['actual_count'],
                'extracted_content_sha256':receipt['extracted_content_sha256'],
            }
            for field,expected in checks.items():
                if method_object.get(field)!=expected:
                    raise RuntimeError('RECOMPUTATION_METHOD_RECEIPT_IDENTITY_MISMATCH:'+recomputation_id+':'+str(key[1])+':'+field)
            if canonical(method_object.get('original_selector'))!=canonical(receipt.get('original_selector')):
                raise RuntimeError('RECOMPUTATION_METHOD_SELECTOR_MISMATCH:'+recomputation_id+':'+str(key[1]))
            if method_object.get('normalized_selector')!=canonical(receipt.get('original_selector')):
                raise RuntimeError('RECOMPUTATION_METHOD_NORMALIZED_SELECTOR_MISMATCH:'+recomputation_id+':'+str(key[1]))
            mirror=Path(receipt['mirror_path'])
            if not mirror.is_file() or sha_file(mirror)!=receipt['extracted_content_sha256']:
                raise RuntimeError('RECOMPUTATION_METHOD_MIRROR_IDENTITY_MISMATCH:'+recomputation_id+':'+str(key[1]))
    return by_id

def load_and_validate_specifications(config_path,config):
    specs=config['specification_inputs']
    adoption_path=verify_config_file(config_path,specs['adoption_candidates'],'adoption_candidates')
    receipts_path=verify_config_file(config_path,specs['input_receipts'],'input_receipts')
    mapping_path=verify_config_file(config_path,specs['assembly_mapping'],'assembly_mapping')
    schema_path=verify_config_file(config_path,specs['normalization_schema'],'normalization_schema')
    recomputation_path=verify_config_file(config_path,specs['recomputation_contract'],'recomputation_contract')
    stage3_path=verify_config_file(config_path,specs['stage3_machine_ledger'],'stage3_machine_ledger')
    adoption=read_jsonl(adoption_path); receipts=read_jsonl(receipts_path); mapping=read_jsonl(mapping_path); schema=json.load(open(schema_path,encoding='utf-8')); recomputation=json.load(open(recomputation_path,encoding='utf-8')); stage3=read_jsonl(stage3_path)
    capabilities=[item for item in mapping if item.get('record_type')=='CAPABILITY_CLOSURE_CANDIDATE']
    gaps=[item for item in mapping if item.get('record_type')=='STRICT_GAP_HANDLING_CANDIDATE']
    return {
        'adoption':adoption,
        'mapping':mapping,
        'schema':schema,
        'receipts':receipts,
        'recomputation_contract':recomputation,
        'recomputation_items':validate_recomputation_contracts(recomputation,receipts),
        'capabilities':capabilities,
        'capability_validation':validate_capability_specs(capabilities,adoption,schema,receipts),
        'gap_validation':validate_gap_mapping(gaps,stage3),
        'identities':{name:{'path':str(resolve_config_file(config_path,item)),'bytes':item['bytes'],'sha256':item['sha256']} for name,item in specs.items()},
    }

def capability_ids_for_table(capabilities,table):
    index_by_table={'order':1,'fill':2,'position':3,'condition':4,'fund':5,'copy':6,'linkage':7,'lineage':8}
    selected_index=index_by_table[table]; out=[]
    for item in capabilities:
        for binding in item['assembly_spec']['source_bindings']:
            if binding['input_id']!='S3INPUT-35': continue
            tables=binding.get('source_tables') or []
            indexes=[int(value) for value in binding.get('selected_object_indexes',[])]
            if table in tables or selected_index in indexes:
                out.append(item['object_id']); break
    return sorted(set(out))

def object_class(navigation_id):
    if re.fullmatch(r'T\d{3}',navigation_id or ''): return 'ACTIVE_TRADE'
    if navigation_id=='SHARED_ACCOUNT_EFFECT': return 'SHARED_ACCOUNT_EFFECT'
    if (navigation_id or '').startswith('UNASSIGNED:'): return 'UNASSIGNED'
    if (navigation_id or '').startswith('U'): return 'COPY_FUNDS_ONLY'
    if navigation_id=='CROSS_OBJECT_RELATIONS': return 'CROSS_OBJECT_RELATION'
    if navigation_id=='T087_METHOD': return 'METHOD'
    return 'BOUNDED_OBJECT'

def navigation_sort_key(navigation_id):
    kind=object_class(navigation_id)
    ranks={'ACTIVE_TRADE':0,'SHARED_ACCOUNT_EFFECT':1,'UNASSIGNED':2,'COPY_FUNDS_ONLY':3,'CROSS_OBJECT_RELATION':4,'METHOD':5,'BOUNDED_OBJECT':6}
    return ranks[kind],navigation_id or ''

def make_common_record(record_type,fact_id,table,row,source,row_no,navigation_id,sample_categories,capability_ids,can_prove,cannot_prove):
    raw=dict(row); normalized=normalize_row(raw); currency,units=currency_and_units(raw); label=source_status_label(raw)
    time_data=time_identity(table,raw)
    source_data=source_identity(source,source['path'],row_no,'BOUNDED_SAMPLE_MANIFEST_FILTER')
    return {
        'record_type':record_type,
        'fact_id':fact_id,
        'navigation_object_id':navigation_id,
        'object_class':object_class(navigation_id),
        'object_id':raw.get('position_cycle_id') or raw.get('event_id') or raw.get('linkage_id') or raw.get('lineage_id') or navigation_id,
        'trade_id':raw.get('trade_id') or (navigation_id if re.fullmatch(r'T\d{3}',navigation_id or '') else None),
        'position_cycle_id':raw.get('position_cycle_id') or None,
        'symbol':raw.get('symbol') or None,
        'sample_categories':sorted(set(sample_categories)),
        'plain_summary':plain_summary(table,raw),
        'raw_value':raw,
        'normalized_value':normalized,
        'time':time_data,
        'event_time_original':time_data['original_value'],
        'currency':currency,
        'units':units,
        'value_state':value_state(raw),
        'evidence_status':normalized_evidence_status(label),
        'source_evidence_status':label,
        'execution_status':'NOT_APPLICABLE',
        'adoption_status':'NOT_FORMALLY_ADOPTED',
        'applicability_scope':raw.get('position_cycle_id') or navigation_id,
        'conflict_ids':[],
        'relation_ids':[],
        'user_statement':None,
        'ai_interpretation':None,
        'applied_capability_ids':[],
        'candidate_capability_spec_ids':capability_ids,
        'capability_application_status':'NOT_RUN_FIRST_PACKAGE_BOUNDED_SAMPLE; 94项只完成候选规格校验，本样本投影不冒充能力实样运行。',
        'input_id':source.get('input_id'),
        'selected_object_index':source.get('selected_object_index'),
        'source_table':table,
        'source_event_id':raw.get('event_id') or raw.get('linkage_id') or raw.get('lineage_id'),
        'source_identity_id':source_data['source_identity_id'],
        'source_identity':source_data,
        'source_path':source['path'],
        'source_sha256':source['sha256'],
        'source_row':row_no,
        'can_prove':can_prove,
        'cannot_prove':cannot_prove,
    }

def make_relation_target_endpoint_records(selected_linkage_rows,link_src,linkage_capabilities,categories):
    grouped=defaultdict(list)
    for row_no,row in selected_linkage_rows:
        if not (row.get('target_event_id') or '').strip() and (row.get('target_object_id') or '').strip():
            grouped[(row.get('target_object_type') or 'UNKNOWN',(row.get('target_object_id') or '').strip())].append((row_no,row))
    records=[]; endpoint_by_object={}
    for (target_type,target_id),group in sorted(grouped.items()):
        relation_ids=[row.get('linkage_id') or str(row_no) for row_no,row in group]
        source_rows=[row_no for row_no,_row in group]
        levels=sorted({source_status_label(row) for _row_no,row in group})
        relation_types=sorted({row.get('link_scope') or 'UNKNOWN' for _row_no,row in group})
        candidate_ids=[item for item in target_id.split('|') if item] if target_type=='POSITION_CYCLE_CANDIDATE' else []
        aggregate={
            'target_object_type':target_type,
            'target_object_id':target_id,
            'target_object_candidates':'|'.join(candidate_ids),
            'supporting_relation_ids':relation_ids,
            'supporting_source_rows':source_rows,
            'source_relation_levels':levels,
            'source_relation_types':relation_types,
            'time_basis':'NOT_APPLICABLE',
        }
        locator='data-rows-'+','.join(str(value) for value in source_rows)
        fact_id=stable_id('FACT',link_src['sha256'],locator,target_type+'\x1f'+target_id)
        only_funds=relation_types==['COPY_FUNDS_NODE']
        can_prove=('固定K05连接表的准确来源行确实把这个跟单资金对象写成关系目标。' if only_funds else
                   '固定K05连接表的准确来源行确实把该对象或候选对象集合写成关系目标。')
        cannot_prove=('该端点只用于跟单资金节点关系；不证明它属于136笔主动交易，也不扩大成完整交易归属。' if only_funds else
                      '该端点不是新交易事件；不证明候选归属已经择一、关系已经正式采用、因果或用户意图已经确定。')
        record=make_common_record(
            'FACT_STATEMENT',fact_id,'relation_target_object',aggregate,link_src,None,
            'CROSS_OBJECT_RELATIONS',sorted({cat for _row_no,row in group for cat in categories.get(row.get('position_cycle_id',''),set())}),
            linkage_capabilities,can_prove,cannot_prove,
        )
        record.update({
            'fact_subtype':'RELATION_TARGET_OBJECT_REFERENCE',
            'endpoint_reference_only':True,
            'promotion_prohibited':True,
            'object_id':target_id,
            'target_object_type':target_type,
            'target_object_id':target_id,
            'target_candidate_ids':candidate_ids,
            'source_relation_types':relation_types,
            'supporting_relation_ids':relation_ids,
            'supporting_source_rows':source_rows,
            'raw_value':aggregate,
            'normalized_value':normalize_business_value_tree(aggregate),
            'time':time_identity('relation_target_object',aggregate),
            'event_time_original':None,
            'currency':'NOT_APPLICABLE',
            'units':{},
            'value_state':value_state(aggregate),
            'evidence_status':('DIRECT' if only_funds and all(normalized_evidence_status(level)=='DIRECT' for level in levels) else 'CANDIDATE'),
            'source_evidence_status':' | '.join(levels),
            'execution_status':'NOT_APPLICABLE',
            'adoption_status':'NOT_FORMALLY_ADOPTED',
            'applicability_scope':target_id,
            'source_event_id':None,
            'source_row':None,
            'plain_summary':f'关系目标对象引用：固定连接表以{target_type}身份记录目标{target_id}；这里只补齐关系端点，不新增交易事件。',
        })
        record['source_identity']['source_locator']=locator
        record['source_identity']['selector']='BOUNDED_SAMPLE_RELATION_TARGET_OBJECT_GROUP'
        record['source_identity']['source_identity_id']=stable_id('SRC',link_src['sha256'],link_src['path'],locator)
        record['source_identity_id']=record['source_identity']['source_identity_id']
        endpoint_by_object[(target_type,target_id)]=fact_id
        records.append(record)
    return records,endpoint_by_object

def _contains_json_business_number(value):
    if isinstance(value,bool) or value is None: return False
    if isinstance(value,(int,float,Decimal)): return True
    if isinstance(value,list): return any(_contains_json_business_number(item) for item in value)
    if isinstance(value,dict): return any(_contains_json_business_number(item) for item in value.values())
    return False

def validate_fact_base_against_schema(records,schema):
    allowed_record_types={'FACT_STATEMENT','RELATION_STATEMENT','LINEAGE_STATEMENT','METHOD_EVIDENCE'}
    required_fact=set(schema['information_layers']['fact_statement'])
    allowed_evidence=set(schema['statuses']['evidence']); allowed_execution=set(schema['statuses']['execution']); allowed_adoption=set(schema['statuses']['adoption'])
    ids=[record.get('fact_id') for record in records]
    if None in ids or len(ids)!=len(set(ids)): raise RuntimeError('FACT_BASE_ID_MISSING_OR_DUPLICATE')
    fact_records={record['fact_id']:record for record in records if record.get('record_type')=='FACT_STATEMENT'}
    endpoint_records={record['fact_id']:record for record in fact_records.values() if record.get('fact_subtype')=='RELATION_TARGET_OBJECT_REFERENCE'}
    relations=[record for record in records if record.get('record_type')=='RELATION_STATEMENT']
    for record in records:
        if record.get('record_type') not in allowed_record_types: raise RuntimeError('FACT_BASE_RECORD_TYPE_INVALID:'+str(record.get('record_type')))
        if record.get('record_type')=='FACT_STATEMENT' and not required_fact.issubset(record):
            raise RuntimeError('FACT_BASE_REQUIRED_FACT_FIELD_MISSING:'+record['fact_id'])
        if record.get('evidence_status') not in allowed_evidence or record.get('execution_status') not in allowed_execution or record.get('adoption_status') not in allowed_adoption:
            raise RuntimeError('FACT_BASE_STATUS_INVALID:'+record['fact_id'])
        if not record.get('input_id') or record.get('selected_object_index') is None or not (record.get('source_identity') or {}).get('source_locator'):
            raise RuntimeError('FACT_BASE_LINEAGE_IDENTITY_INCOMPLETE:'+record['fact_id'])
        if not set(schema['information_layers']['source_identity']).issubset(record.get('source_identity') or {}):
            raise RuntimeError('FACT_BASE_SOURCE_IDENTITY_FIELDS_INCOMPLETE:'+record['fact_id'])
        time_data=record.get('time') or {}
        if not {'original_value','original_timezone','normalized_utc','beijing_time','precision','timezone_basis'}.issubset(time_data):
            raise RuntimeError('FACT_BASE_TIME_IDENTITY_INCOMPLETE:'+record['fact_id'])
        if _contains_json_business_number(record.get('normalized_value')):
            raise RuntimeError('FACT_BASE_NORMALIZED_BUSINESS_NUMBER_NOT_STRING:'+record['fact_id'])
        value_states=record.get('value_state') or {}
        for unknown in value_states.get('unknown') or []:
            if unknown.get('status')!='UNKNOWN' or not {'reason','missing_evidence','scope'}.issubset(unknown):
                raise RuntimeError('FACT_BASE_UNKNOWN_STRUCTURE_INVALID:'+record['fact_id'])
        for candidate_set in value_states.get('candidate_sets') or []:
            if not set(schema['candidate_set']['required']).issubset(candidate_set) or candidate_set.get('selection_status')!='UNRESOLVED':
                raise RuntimeError('FACT_BASE_CANDIDATE_SET_STRUCTURE_INVALID:'+record['fact_id'])
        for not_applicable in value_states.get('not_applicable') or []:
            if not set(schema['not_applicable']['required']).issubset(not_applicable):
                raise RuntimeError('FACT_BASE_NOT_APPLICABLE_STRUCTURE_INVALID:'+record['fact_id'])
        raw=record.get('raw_value') or {}; raw=raw if isinstance(raw,dict) else {}; units=record.get('units') or {}
        money_fields={'amount','total_asset_effect','fee','realized_pnl','commission','funding_fee','known_net_effect_excluding_unknown_funding'}
        quantity_fields={field for field in raw if 'quantity' in field or field in {'position_before','position_after'}}
        if any(raw.get(field) not in (None,'') for field in money_fields) and record.get('currency') in (None,''):
            raise RuntimeError('FACT_BASE_MONEY_CURRENCY_MISSING:'+record['fact_id'])
        if any(raw.get(field) not in (None,'') and field not in units for field in quantity_fields):
            raise RuntimeError('FACT_BASE_QUANTITY_UNIT_MISSING:'+record['fact_id'])
        if record.get('applied_capability_ids'):
            raise RuntimeError('FACT_BASE_UNRUN_CAPABILITY_MARKED_APPLIED:'+record['fact_id'])
    endpoint_relation_ids=defaultdict(list); endpoint_source_rows=defaultdict(list)
    for record in relations:
        relation=record.get('relation') or {}
        source_id=relation.get('source_fact_id'); target_id=relation.get('target_fact_id')
        if not source_id or not target_id or source_id not in fact_records or target_id not in fact_records:
            raise RuntimeError('FACT_BASE_RELATION_ENDPOINT_INVALID:'+record['fact_id'])
        if relation.get('direction')!='SOURCE_TO_TARGET': raise RuntimeError('FACT_BASE_RELATION_DIRECTION_INVALID:'+record['fact_id'])
        if relation.get('target_event_id'):
            if fact_records[target_id].get('source_event_id')!=relation['target_event_id']:
                raise RuntimeError('FACT_BASE_EVENT_TARGET_MISMATCH:'+record['fact_id'])
        else:
            if not relation.get('target_object_id') or target_id not in endpoint_records:
                raise RuntimeError('FACT_BASE_OBJECT_TARGET_ENDPOINT_MISSING:'+record['fact_id'])
            endpoint=endpoint_records[target_id]
            if (endpoint.get('target_object_type'),endpoint.get('target_object_id'))!=(relation.get('target_object_type'),relation.get('target_object_id')):
                raise RuntimeError('FACT_BASE_OBJECT_TARGET_ENDPOINT_MISMATCH:'+record['fact_id'])
            endpoint_relation_ids[target_id].append(relation['relation_id']); endpoint_source_rows[target_id].append(record['source_row'])
    for endpoint_id,endpoint in endpoint_records.items():
        if sorted(endpoint.get('supporting_relation_ids') or [])!=sorted(endpoint_relation_ids[endpoint_id]):
            raise RuntimeError('FACT_BASE_ENDPOINT_RELATION_SET_MISMATCH:'+endpoint_id)
        if sorted(endpoint.get('supporting_source_rows') or [])!=sorted(endpoint_source_rows[endpoint_id]):
            raise RuntimeError('FACT_BASE_ENDPOINT_SOURCE_ROW_SET_MISMATCH:'+endpoint_id)
        if endpoint.get('target_object_type')=='POSITION_CYCLE_CANDIDATE':
            candidates=endpoint.get('target_candidate_ids') or []
            if len(candidates)!=2 or (endpoint.get('value_state') or {}).get('candidate_sets',[{}])[0].get('selection_status')!='UNRESOLVED':
                raise RuntimeError('FACT_BASE_COMPOSITE_CANDIDATE_BOUNDARY_INVALID:'+endpoint_id)
        if endpoint.get('endpoint_reference_only') is not True or endpoint.get('promotion_prohibited') is not True or endpoint.get('object_class')!='CROSS_OBJECT_RELATION':
            raise RuntimeError('FACT_BASE_ENDPOINT_REFERENCE_BOUNDARY_INVALID:'+endpoint_id)
        relation_types=endpoint.get('source_relation_types') or []
        if 'COPY_FUNDS_NODE' in relation_types:
            if (
                endpoint.get('evidence_status')!='DIRECT'
                or endpoint.get('cannot_prove')!='该端点只用于跟单资金节点关系；不证明它属于136笔主动交易，也不扩大成完整交易归属。'
            ):
                raise RuntimeError('FACT_BASE_COPY_FUNDS_BOUNDARY_MISSING:'+endpoint_id)
        elif endpoint.get('evidence_status')!='CANDIDATE':
            raise RuntimeError('FACT_BASE_ENDPOINT_EVIDENCE_PROMOTION_DETECTED:'+endpoint_id)
    object_target_relations=sum(1 for record in relations if not (record.get('relation') or {}).get('target_event_id'))
    if len(endpoint_records)!=6 or object_target_relations!=63:
        raise RuntimeError('FACT_BASE_OBJECT_TARGET_EXPECTED_COUNTS_MISMATCH')
    object_target_evidence=Counter(record['evidence_status'] for record in relations if not (record.get('relation') or {}).get('target_event_id'))
    if object_target_evidence!={'CANDIDATE':62,'DIRECT':1}:
        raise RuntimeError('FACT_BASE_OBJECT_TARGET_EVIDENCE_PROMOTION_DETECTED')
    return {
        'record_count':len(records),
        'fact_count':len(fact_records),
        'relation_count':len(relations),
        'relation_target_endpoint_fact_count':len(endpoint_records),
        'event_target_relation_count':len(relations)-object_target_relations,
        'object_target_relation_count':object_target_relations,
        'object_target_relation_evidence_counts':dict(sorted(object_target_evidence.items())),
        'all_relations_resolve_to_fact_statements':True,
        'normalized_business_numbers_are_strings':True,
    }

def build(config_path, manifest_path, output_path):
    config=json.load(open(config_path,encoding='utf-8')); manifest=json.load(open(manifest_path,encoding='utf-8'))
    specifications=load_and_validate_specifications(config_path,config)
    bounded_sources=verify_sources(config,specifications['receipts'])
    data={name:read_csv(item['mirror_path']) for name,item in bounded_sources.items()}
    cycles,exact_events,shared_events,categories=selected_scope(manifest)
    cycle_to_trade={}
    for table in ('order','fill','position','condition','fund','copy'):
        for row in data[table]:
            if row.get('position_cycle_id') and row.get('trade_id'): cycle_to_trade[row['position_cycle_id']]=row['trade_id']
            if table=='copy' and row.get('position_cycle_id') and row.get('legacy_copy_id'): cycle_to_trade[row['position_cycle_id']]=row['legacy_copy_id']
    selected_event_ids=set(); event_to_navigation={}; records=[]
    for table in ('order','fill','position','condition','fund','copy'):
        src=bounded_sources[table]
        applied=capability_ids_for_table(specifications['capabilities'],table)
        for row_no,row in enumerate(data[table],2):
            eid=(row.get('event_id') or '').strip(); cyc=(row.get('position_cycle_id') or '').strip()
            if cyc not in cycles and eid not in exact_events and eid not in shared_events: continue
            selected_event_ids.add(eid)
            scope=sorted(categories.get(cyc,set()))
            if eid in exact_events: scope.append('exact_unassigned_condition_object')
            if eid in shared_events: scope.append('account_level_time_overlap_object')
            if table=='copy': navigation=row.get('legacy_copy_id') or cycle_to_trade.get(cyc) or f'COPY:{cyc}'
            elif eid in exact_events: navigation=f'UNASSIGNED:{row.get("condition_record_id") or eid}'
            elif eid in shared_events and not cyc: navigation='SHARED_ACCOUNT_EFFECT'
            else: navigation=row.get('trade_id') or cycle_to_trade.get(cyc) or cyc or eid
            event_to_navigation[eid]=navigation
            locator=f'{Path(src["path"]).name}:data-row-{row_no}'
            record=make_common_record('FACT_STATEMENT',stable_id('FACT',src['sha256'],locator,eid),table,row,src,row_no,navigation,scope,applied,'该行在固定K05源表中的原始字段和值。','不自动证明候选关系、原因、意图、资金归属或时间重叠的因果。')
            records.append(record)
    event_to_fact={record['source_event_id']:record['fact_id'] for record in records if record['record_type']=='FACT_STATEMENT'}
    fact_by_id={record['fact_id']:record for record in records if record['record_type']=='FACT_STATEMENT'}
    link_src=bounded_sources['linkage']
    linkage_capabilities=capability_ids_for_table(specifications['capabilities'],'linkage')
    selected_linkage_rows=[]
    for row_no,row in enumerate(data['linkage'],2):
        if (row.get('position_cycle_id') or '') not in cycles and row.get('source_event_id') not in selected_event_ids and row.get('target_event_id') not in selected_event_ids: continue
        selected_linkage_rows.append((row_no,row))
    endpoint_records,endpoint_by_object=make_relation_target_endpoint_records(selected_linkage_rows,link_src,linkage_capabilities,categories)
    records.extend(endpoint_records)
    fact_by_id.update({record['fact_id']:record for record in endpoint_records})
    for row_no,row in selected_linkage_rows:
        key=row.get('linkage_id') or f'{row_no}'
        locator=f'{Path(link_src["path"]).name}:data-row-{row_no}'
        source_nav=event_to_navigation.get(row.get('source_event_id')); target_nav=event_to_navigation.get(row.get('target_event_id'))
        if not source_nav and row.get('source_event_id') in exact_events: source_nav='UNASSIGNED:'+row.get('source_object_id','UNKNOWN')
        if source_nav and target_nav and source_nav==target_nav: navigation=source_nav
        elif row.get('source_event_id') in exact_events or (source_nav and target_nav and source_nav!=target_nav): navigation='CROSS_OBJECT_RELATIONS'
        else: navigation=source_nav or target_nav or cycle_to_trade.get(row.get('position_cycle_id')) or row.get('position_cycle_id') or 'CROSS_OBJECT_RELATIONS'
        source_fact_id=event_to_fact.get(row.get('source_event_id'))
        if not source_fact_id:
            raise RuntimeError('RELATION_SOURCE_FACT_NOT_FOUND:'+key)
        target_event_id=(row.get('target_event_id') or '').strip()
        if target_event_id:
            target_fact_id=event_to_fact.get(target_event_id)
            if not target_fact_id: raise RuntimeError('RELATION_TARGET_EVENT_FACT_NOT_FOUND:'+key)
        else:
            target_key=(row.get('target_object_type') or 'UNKNOWN',(row.get('target_object_id') or '').strip())
            target_fact_id=endpoint_by_object.get(target_key)
            if not target_fact_id: raise RuntimeError('RELATION_TARGET_OBJECT_FACT_NOT_FOUND:'+key)
        record=make_common_record('RELATION_STATEMENT',stable_id('REL',link_src['sha256'],locator,key),'linkage',row,link_src,row_no,navigation,sorted(categories.get(row.get('position_cycle_id',''),set())),linkage_capabilities,'固定连接表记录了该关系声明及其等级。','候选或上下文关系不升级为直接因果或唯一归属。')
        record['relation']={
            'relation_id':key,
            'source_fact_id':source_fact_id,
            'target_fact_id':target_fact_id,
            'source_event_id':row.get('source_event_id') or None,
            'target_event_id':row.get('target_event_id') or None,
            'source_object_type':row.get('source_object_type') or None,
            'target_object_type':row.get('target_object_type') or None,
            'source_object_id':row.get('source_object_id') or None,
            'target_object_id':row.get('target_object_id') or None,
            'relation_type':row.get('link_scope') or 'UNKNOWN',
            'direction':'SOURCE_TO_TARGET',
            'cardinality':'EDGE_RECORD_ONE_TO_ONE_OVERALL_CARDINALITY_NOT_ASSERTED',
            'evidence_status':record['evidence_status'],
        }
        record['relation_ids']=[key]
        for endpoint in (record['relation']['source_fact_id'],record['relation']['target_fact_id']):
            if endpoint in fact_by_id:
                fact_by_id[endpoint]['relation_ids'].append(key)
        records.append(record)
    lin_src=bounded_sources['lineage']
    lineage_capabilities=capability_ids_for_table(specifications['capabilities'],'lineage')
    for row_no,row in enumerate(data['lineage'],2):
        if row.get('event_id') not in selected_event_ids: continue
        key=row.get('lineage_id') or f'{row.get("event_id")}:{row_no}'
        locator=f'{Path(lin_src["path"]).name}:data-row-{row_no}'
        navigation=event_to_navigation[row.get('event_id')]
        records.append(make_common_record('LINEAGE_STATEMENT',stable_id('LIN',lin_src['sha256'],locator,key),'lineage',row,lin_src,row_no,navigation,[],lineage_capabilities,'固定来源链表记录了事件与源对象的追溯关系。','来源链本身不提高业务结论的证据等级。'))
    receipts=read_jsonl(verify_config_file(config_path,config['specification_inputs']['input_receipts'],'input_receipts'))
    receipt_map={(item['input_id'],int(item['selected_object_index'])):item for item in receipts}
    for method in config.get('bounded_method_test_sources',[]):
        receipt=receipt_map[(method['input_id'],int(method['selected_object_index']))]
        payload=selected_payload(receipt); path=Path(receipt['source_path'])
        row={'event_id':None,'position_cycle_id':'T087','method_payload':payload,'time_basis':'NOT_APPLICABLE'}
        method_source={
            'path':receipt['source_path'],'sha256':receipt['actual_sha256'],'bytes':receipt['actual_bytes'],
            'input_id':receipt['input_id'],'selected_object_index':int(receipt['selected_object_index']),
            'mirror_path':receipt['mirror_path'],'selected_content_sha256':receipt['extracted_content_sha256'],
        }
        record=make_common_record('METHOD_EVIDENCE',stable_id('METHOD',receipt['extracted_content_sha256'],f'{method["input_id"]}:{method["selected_object_index"]}',method['role']),'method',row,method_source,None,'T087_METHOD',method['sample_categories'],[],method['can_prove'],method['cannot_prove'])
        record['object_id']=method['object_id']; record['raw_value']=payload; record['normalized_value']=normalize_business_value_tree(payload)
        record['evidence_status']='BOUNDED'; record['source_evidence_status']='METHOD_ONLY_NOT_RUN'; record['execution_status']='NOT_AUTHORIZED'; record['applicability_scope']=method['role']
        record['conflict_ids']=['T087-SAME-SECOND-UNIQUE-ORDER-NOT-PROVEN']
        record['source_identity']['selector']=receipt['original_selector']; record['source_identity']['selected_content_sha256']=receipt['extracted_content_sha256']
        record['source_identity']['source_locator']=f'selected-object-{int(receipt["selected_object_index"])}'
        record['source_identity']['source_identity_id']=stable_id('SRC',receipt['actual_sha256'],str(path),canonical(receipt['original_selector']))
        record['source_identity_id']=record['source_identity']['source_identity_id']
        record['source_event_id']=None; record['plain_summary']='方法证据：T087保留两条合法路径及外包络；唯一真实顺序没有得到证明，本次没有运行真实重算。'
        records.append(record)
    for record in records:
        record['relation_ids']=sorted(set(record.get('relation_ids',[])))
        record['conflict_ids']=sorted(set(record.get('conflict_ids',[])))
    records.sort(key=lambda r:(navigation_sort_key(r['navigation_object_id']),r['time']['beijing_time'] or r['event_time_original'] or '',r['record_type'],r['fact_id']))
    for index,record in enumerate(records,1): record['stable_display_sequence']=index
    schema_validation=validate_fact_base_against_schema(records,specifications['schema'])
    with open(output_path,'w',encoding='utf-8',newline='\n') as f:
        for record in records: f.write(canonical(record)+'\n')
    business_sha=sha_file(output_path)
    print(canonical({'record_count':len(records),'business_content_sha256':business_sha,'selected_event_count':len(selected_event_ids),'capability_validation':specifications['capability_validation'],'gap_validation':specifications['gap_validation'],'schema_validation':schema_validation}))

def verify_file_identity(path, identity, label):
    path=Path(path)
    if not path.is_file():
        raise RuntimeError(f'VIEW_INPUT_MISSING:{label}:{path}')
    if path.stat().st_size!=identity['bytes'] or sha_file(path)!=identity['sha256']:
        raise RuntimeError(f'VIEW_INPUT_IDENTITY_MISMATCH:{label}:{path}')

def build_ai_view_text(records, fact_path, sample_manifest, view_config):
    counts=Counter(record['record_type'] for record in records)
    ai=view_config['ai_view']
    grouped=defaultdict(list)
    for record in records: grouped[record['navigation_object_id']].append(record)
    object_order=sorted(grouped,key=navigation_sort_key)
    lines=[ai['title'],'',ai['identity'],'',ai['boundary'],'',
        '## 一、怎样读取这份文件','',
        '1. 先看“对象目录”，按交易或特殊对象进入对应小节。',
        '2. 每个对象内部按稳定展示顺序连续排列；长对象只在对象内部继续分块，不会与其他对象混在一起。',
        '3. 每条完整事实只在JSONL正文出现一次；目录和说明只是导航，不是第二套事实。',
        '4. `UNKNOWN`、多个候选、共享账户影响和同秒多路径都必须按原边界理解，不能自行升级为确定事实。',
        '', '## 二、样本覆盖','','| 类别 | 选中对象 |','|---|---|']
    for category,item in sample_manifest['selected_by_category'].items():
        lines.append(f'| {category.replace("|","/")} | {item["stable_id"].replace("|","/")} |')
    lines += ['', '## 三、事实底座对账', '', f'- 总记录：{len(records)}']
    lines += [f'- {name}：{count}' for name,count in sorted(counts.items())]
    lines += [f'- 对象入口数量：{len(grouped)}', f'- 业务内容SHA-256：`{sha_file(fact_path)}`', '', '## 四、对象目录','',
        '| 对象入口 | 对象类型 | 记录数 | 记录类型 | 起始时间 | 结束时间 |',
        '|---|---|---:|---|---|---|']
    for object_id in object_order:
        group=grouped[object_id]; times=[r['time']['beijing_time'] or r['event_time_original'] for r in group if r['time']['beijing_time'] or r['event_time_original']]
        lines.append(f'| `{object_id}` | {object_type_plain(group[0]["object_class"])} | {len(group)} | {"、".join(sorted({r["record_type"] for r in group}))} | {min(times) if times else "不适用"} | {max(times) if times else "不适用"} |')
    lines += ['', '## 五、按对象连续读取正文', '', ai['body_note'], '']
    chunk_size=int(ai.get('object_internal_chunk_size',ai.get('chunk_size',250)))
    for object_number,object_id in enumerate(object_order,1):
        object_records=grouped[object_id]
        lines += [f'### {object_number}. 对象 `{object_id}`','',f'- 对象类型：{object_type_plain(object_records[0]["object_class"])}',f'- 本对象记录数：{len(object_records)}','']
        for start in range(0,len(object_records),chunk_size):
            group=object_records[start:start+chunk_size]
            lines += [
                f'#### {object_id}｜对象内分块 {start//chunk_size+1:02d}',
                '',
                f'- 起始事实ID：`{group[0]["fact_id"]}`',
                f'- 结束事实ID：`{group[-1]["fact_id"]}`',
                f'- 对象内上一分块结束：`{object_records[start-1]["fact_id"] if start else "NONE"}`',
                f'- 对象内下一分块开始：`{object_records[start+chunk_size]["fact_id"] if start+chunk_size<len(object_records) else "NONE"}`',
                '',
                '```jsonl',
            ]
            lines.extend(canonical(record) for record in group)
            lines += ['```','']
    lines += ['## 六、读取结论边界','']
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

def evidence_status_plain(value):
    return {
        'DIRECT':'直接证据','DETERMINISTIC_DERIVATION':'确定性推导','BOUNDED':'有边界证据',
        'CANDIDATE':'候选关系','UNKNOWN':'未知','NOT_APPLICABLE':'不适用','NOT_EVALUATED':'尚未评估',
    }.get(value,value)

def object_type_plain(value):
    return {
        'ACTIVE_TRADE':'主动交易样本','COPY_FUNDS_ONLY':'跟单资金影响对象','SHARED_ACCOUNT_EFFECT':'共享账户影响',
        'UNASSIGNED':'未归属对象','CROSS_OBJECT_RELATION':'跨对象关系','METHOD':'方法与边界证据','BOUNDED_OBJECT':'有界对象',
    }.get(value,value)

def uncertainty_plain(record):
    parts=[]
    states=record.get('value_state') or {}
    if states.get('unknown'): parts.append('含未知值：'+'、'.join(item['field'] for item in states['unknown']))
    if states.get('candidate_sets'): parts.append('含多个候选：'+'、'.join(item['field'] for item in states['candidate_sets']))
    if states.get('intervals'): parts.append('含区间：'+'、'.join(item['field'] for item in states['intervals']))
    if record.get('conflict_ids'): parts.append('冲突：'+'、'.join(record['conflict_ids']))
    if record.get('evidence_status')=='CANDIDATE': parts.append('关系或结论仍是候选，不能当作已确定事实')
    return '；'.join(parts) if parts else '未发现需要单独提示的未知、候选或冲突'

def build_workbook_payload(records, sample_manifest, receipts, contract_id):
    facts=[record for record in records if record['record_type']=='FACT_STATEMENT']
    endpoint_facts=[record for record in facts if record.get('fact_subtype')=='RELATION_TARGET_OBJECT_REFERENCE']
    event_facts=[record for record in facts if record.get('fact_subtype')!='RELATION_TARGET_OBJECT_REFERENCE']
    relations=[record for record in records if record['record_type']=='RELATION_STATEMENT']
    lineage=[record for record in records if record['record_type']=='LINEAGE_STATEMENT']
    methods=[record for record in records if record['record_type']=='METHOD_EVIDENCE']
    if len(facts)+len(relations)+len(lineage)+len(methods)!=len(records): raise RuntimeError('UNKNOWN_FACT_RECORD_TYPE')
    grouped=defaultdict(list)
    for record in records: grouped[record['navigation_object_id']].append(record)
    start_rows=[
        {'项目':'这是什么','白话说明':'这是第一工作包的小范围用户核对测试版，用来确认同一事实底座能否变成用户看得懂的连续记录。','当前状态':'等待用户实际核对'},
        {'项目':'从哪里开始','白话说明':'先看“对象目录”，再选一个对象到“事件时间线”；关系不清时看“关系与归属”，需要查来源时看“来源追溯”。','当前状态':'可按对象阅读'},
        {'项目':'合同ID','白话说明':contract_id,'当前状态':'固定'},
        {'项目':'事实底座记录数','白话说明':str(len(records))+'条；事实、关系、来源链和方法记录均来自同一底座。','当前状态':'程序对账通过'},
        {'项目':'事实底座SHA-256','白话说明':'待生成时填入','当前状态':'程序自动填写'},
        {'项目':'正式采用','白话说明':'本表中的44项候选仍未被正式采用。','当前状态':'尚未正式采用'},
        {'项目':'136笔构建','白话说明':'本表只含获准的困难样本，不是一百三十六笔完整交易链。','当前状态':'未开始'},
        {'项目':'三项真实重新计算','白话说明':'这里只验证合成测试函数；没有运行真实业务重新计算。','当前状态':'未授权、未运行'},
        {'项目':'怎样看待未知','白话说明':'未知、区间、多个候选、共享影响和同秒多路径必须原样保留，不能因为表格方便阅读就挑一个当真。','当前状态':'边界必须保留'},
    ]
    directory=[]
    for object_id in sorted(grouped,key=navigation_sort_key):
        group=grouped[object_id]; record_counts=Counter(item['record_type'] for item in group)
        times=[item['time']['beijing_time'] or item['event_time_original'] for item in group if item['time']['beijing_time'] or item['event_time_original']]
        categories=sorted({category for item in group for category in item.get('sample_categories',[])})
        directory.append({
            '对象入口':object_id,'对象类型':object_type_plain(group[0]['object_class']),'记录数':len(group),
            '事实数':record_counts['FACT_STATEMENT'],'关系数':record_counts['RELATION_STATEMENT'],
            '来源链数':record_counts['LINEAGE_STATEMENT'],'方法记录数':record_counts['METHOD_EVIDENCE'],
            '起始时间':min(times) if times else '不适用','结束时间':max(times) if times else '不适用',
            '涉及样本':'；'.join(categories) if categories else '无单独样本标签',
            '阅读提示':'到“事件时间线”按对象入口筛选；特殊对象还应同时查看“特殊对象与边界”。',
        })
    timeline=[]
    for record in event_facts:
        raw=record['raw_value']; position_change=''
        if raw.get('position_before')!='' or raw.get('position_after')!='': position_change=f'{raw.get("position_before") or "未知"} → {raw.get("position_after") or "未知"}'
        timeline.append({
            '顺序':record['stable_display_sequence'],'对象入口':record['navigation_object_id'],'北京时间':record['time']['beijing_time'] or '未能可靠换算',
            '原始时间':record['event_time_original'] or '未记录','品种':record.get('symbol') or '未注明','发生了什么':record['plain_summary'],
            '委托ID':raw.get('order_id') or raw.get('generated_order_id') or '','成交ID':raw.get('fill_id') or raw.get('source_fill_id') or '',
            '动作':plain_value(raw.get('actual_position_action') or raw.get('position_action') or raw.get('action_type') or raw.get('attempt_role') or raw.get('condition_role') or raw.get('fund_event_subtype') or raw.get('direction'),''),
            '状态':plain_value(raw.get('raw_status') or raw.get('status') or raw.get('confirmation_status'),''),
            '数量':raw.get('quantity') or raw.get('order_quantity') or '', '价格':raw.get('price') or raw.get('order_price') or raw.get('trigger_price') or '',
            '手续费':raw.get('fee') or raw.get('commission') or '', '费用币种':raw.get('fee_asset') or raw.get('currency') or '',
            '已实现盈亏':raw.get('realized_pnl') or raw.get('known_net_effect_excluding_unknown_funding') or '',
            '仓位变化':position_change,'证据状态':evidence_status_plain(record['evidence_status']),
            '不确定或候选说明':uncertainty_plain(record),'事实ID':record['fact_id'],
        })
    relation_rows=[]
    for record in relations:
        relation=record.get('relation') or {}
        relation_rows.append({
            '对象入口':record['navigation_object_id'],'关系说明':record['plain_summary'],'关系类型':plain_value(relation.get('relation_type'),'未知'),
            '来源事件':relation.get('source_event_id') or '未记录','目标事件':relation.get('target_event_id') or '未记录',
            '目标对象类型':relation.get('target_object_type') or '未记录','目标对象ID':relation.get('target_object_id') or '未记录',
            '来源事实ID':relation.get('source_fact_id') or '未能连接','目标事实ID':relation.get('target_fact_id') or '未能连接',
            '证据状态':evidence_status_plain(record['evidence_status']),'能证明':record['can_prove'],'不能证明':record['cannot_prove'],
            '关系ID':relation.get('relation_id') or '','事实ID':record['fact_id'],
        })
    special=[]
    for object_id in sorted(grouped):
        group=[item for item in grouped[object_id] if item.get('fact_subtype')!='RELATION_TARGET_OBJECT_REFERENCE']
        if not group or group[0]['object_class']=='ACTIVE_TRADE': continue
        special.append({
            '对象入口':object_id,'对象身份':object_type_plain(group[0]['object_class']),'记录数':len(group),
            '白话说明':'；'.join(dict.fromkeys(item['plain_summary'] for item in group[:12])),
            '必须保留的边界':'；'.join(dict.fromkeys(item['cannot_prove'] for item in group[:12])),
            '相关事实ID':'；'.join(item['fact_id'] for item in group),
        })
    for endpoint in sorted(endpoint_facts,key=lambda item:(item.get('target_object_type') or '',item.get('target_object_id') or '')):
        special.append({
            '对象入口':endpoint['target_object_id'],
            '对象身份':'关系目标对象引用（不是交易事件）',
            '记录数':1,
            '白话说明':endpoint['plain_summary'],
            '必须保留的边界':endpoint['cannot_prove'],
            '相关事实ID':endpoint['fact_id'],
        })
    lineage_rows=[]
    for record in lineage:
        raw=record['raw_value']
        lineage_rows.append({
            '对象入口':record['navigation_object_id'],'事件ID':raw.get('event_id') or '',
            '直接来源文件':raw.get('source_path') or record['source_path'],'来源表':raw.get('source_sheet') or '',
            '来源行':raw.get('source_row') or '','变换规则':plain_value(raw.get('transformation_rule'),''),
            '值保留状态':plain_value(raw.get('value_preservation_status'),''),'事实ID':record['fact_id'],
        })
    input_rows=[]
    for category,item in sample_manifest['selected_by_category'].items():
        sorting_tuple=item.get('metrics',{}).get('sorting_tuple')
        selector_text='09样本清单已固定选中该对象'
        selector_text+=('；固定排序元组：'+canonical(sorting_tuple)) if sorting_tuple is not None else '；本项不需要额外排序元组'
        input_rows.append({'记录类别':'困难样本','输入编号或样本类别':category,'对象序号':'','对象或选中范围':item['stable_id'],'来源文件':'09_有界验证样本清单候选.json中的确定性选择','选择器':selector_text,'装载数量':'','当前状态':'本工作包有界测试样本','能证明':'样本覆盖该困难情形。','不能证明':item.get('relationship_boundary') or item.get('relation_boundary') or item.get('selection_or_rejection_reason'),'内容指纹':''})
    for item in receipts:
        input_rows.append({'记录类别':'获准输入对象','输入编号或样本类别':item['input_id'],'对象序号':item['selected_object_index'],'对象或选中范围':item.get('stage2_engineering_object_id') or Path(item['source_path']).name,'来源文件':item['source_path'],'选择器':selector_plain(item['normalized_selector']),'装载数量':item['actual_count'],'当前状态':plain_value(item['load_status']),'能证明':item['can_prove'],'不能证明':item['cannot_prove'],'内容指纹':item['extracted_content_sha256']})
    technical=[{'顺序':record['stable_display_sequence'],'对象入口':record['navigation_object_id'],'记录类型':record['record_type'],'事实ID':record['fact_id'],'完整记录JSON':canonical(record)} for record in records]
    return {'从这里开始':start_rows,'对象目录':directory,'事件时间线':timeline,'关系与归属':relation_rows,'特殊对象与边界':special,'来源追溯':lineage_rows,'输入范围':input_rows,'技术原文':technical}

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
                if header in {'类别','样本类别','输入编号或样本类别','涉及样本'} and isinstance(value,str):
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
  if (!["类别","样本类别","输入编号或样本类别","涉及样本"].includes(header) || typeof normalized!=="string") return normalized;
  let display=normalized;
  for (const [technical,plain] of Object.entries(categoryLabels)) display=display.split(technical).join(plain);
  return display;
}
function widthFor(header) {
  if (["完整记录JSON"].includes(header)) return 90;
  if (["白话说明","发生了什么","不确定或候选说明","关系说明","必须保留的边界","能证明","不能证明","阅读提示"].includes(header)) return 44;
  if (["来源文件","直接来源文件"].includes(header)) return 60;
  if (header==="选择器") return 65;
  if (["输入编号或样本类别","对象或选中范围"].includes(header)) return 36;
  if (header.includes("ID") || header.includes("SHA")) return 30;
  if (header.includes("时间")) return 24;
  if (header.includes("来源") || header.includes("对象")) return 25;
  return Math.max(14,Math.min(28,String(header).length*2+4));
}
function rowHeightFor(sheetName) {
  const heights={
    "从这里开始":58,
    "对象目录":68,
    "事件时间线":64,
    "关系与归属":74,
    "特殊对象与边界":112,
    "来源追溯":56,
    "输入范围":96,
    "技术原文":60,
  };
  return heights[sheetName]||56;
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
  sheet.getRange(`A4:${lastCol}${lastRow}`).format.rowHeight=rowHeightFor(name);
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
    sheet.getRange(`${statusCol}4:${statusCol}${lastRow}`).conditionalFormats.add("containsText",{text:"未知",format:{fill:"#FFF2CC",font:{color:"#9C5700",bold:true}}});
    sheet.getRange(`${statusCol}4:${statusCol}${lastRow}`).conditionalFormats.add("containsText",{text:"候选",format:{fill:"#FCE4D6",font:{color:"#C65911",bold:true}}});
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
    for item in payload['从这里开始']:
        if item['项目']=='事实底座SHA-256':
            item['白话说明']=sha_file(fact_path); item['当前状态']='固定来源身份'
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
        renderer_path=temp/'build_user_workbook.mjs'
        actual_preview_dir=Path(preview_dir).resolve() if preview_dir else temp/'previews'
        ai_temp.write_text(ai_text,encoding='utf-8',newline='\n')
        json_write(payload_path,payload)
        json_write(view_config_path,view['user_workbook'])
        renderer_path.write_text(WORKBOOK_RENDERER,encoding='utf-8',newline='\n')
        node_result=subprocess.run(
            [str(node),str(renderer_path),str(module),str(payload_path),str(workbook_temp),str(actual_preview_dir),str(view_config_path)],
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
        'user_workbook':{
            'path':str(workbook_output),'bytes':workbook_output.stat().st_size,'sha256':sha_file(workbook_output),
            'user_understandability_status':view['user_workbook']['user_understandability']['current_status'],
            'user_understandability_cannot_be_self_passed':True,
            **workbook_check,
        },
        'one_command':view['command'],
    }
    if verification_output:
        json_write(Path(verification_output),result)
    print(canonical(result))

def set_nested(value,path,replacement):
    parts=path.split('.'); current=value
    for part in parts[:-1]: current=current[int(part)] if isinstance(current,list) else current[part]
    final=parts[-1]
    if isinstance(current,list): current[int(final)]=replacement
    else: current[final]=replacement

def receipt_from_file(path,input_id,selected_object_index):
    matches=[item for item in read_jsonl(path) if item['input_id']==input_id and int(item['selected_object_index'])==int(selected_object_index)]
    if len(matches)!=1: raise RuntimeError('TEST_RECEIPT_NOT_UNIQUE:'+input_id)
    return matches[0]

def validated_recomputation_test_item(base,inp):
    contract=json.load(open((base/inp['contract_file']).resolve(),encoding='utf-8'))
    receipts=read_jsonl((base/inp['receipt_file']).resolve())
    items=validate_recomputation_contracts(contract,receipts)
    return items[inp['recomputation_id']]

def run_tests(test_path):
    test_path=Path(test_path).resolve(); base=test_path.parent
    tests=[json.loads(x) for x in open(test_path,encoding='utf-8') if x.strip()]; out=[]
    for t in tests:
        kind=t['test_kind']; inp=t['input']; exp=t['expected']
        if kind=='stable_id': actual=stable_id(**inp)
        elif kind=='decimal_text': actual=decimal_text(inp['value'])
        elif kind=='canonical': actual=canonical(inp['value'])
        elif kind=='preserve_value': actual=inp['value']
        elif kind=='time_identity': actual=time_identity(inp['table'],inp['row'])
        elif kind=='currency_units':
            currency,units=currency_and_units(inp['row']); actual={'currency':currency,'units':units}
        elif kind=='value_state': actual=value_state(inp['row'])
        elif kind=='status_separation':
            actual={**inp,'all_three_distinct':len({inp['evidence_status'],inp['execution_status'],inp['adoption_status']})==3}
        elif kind=='relation_endpoints':
            relation=inp['relation']; actual=bool(relation.get('source_fact_id') and relation.get('target_fact_id') and relation.get('direction')=='SOURCE_TO_TARGET')
        elif kind in {'gap_mapping_valid','gap_mapping_swap_rejected'}:
            mapping=read_jsonl((base/inp['mapping_file']).resolve()); stage3=read_jsonl((base/inp['stage3_machine_ledger']).resolve())
            gaps=[item for item in mapping if item.get('record_type')=='STRICT_GAP_HANDLING_CANDIDATE']
            if kind=='gap_mapping_valid': actual=validate_gap_mapping(gaps,stage3)
            else:
                first,second=inp['swap_gap_ids']; by_id={item['object_id']:item for item in gaps}
                source_fields=('source_stage3_line','source_stage3_record_id','source_stage3_capability_id','source_stage3_missing_statement')
                for field in source_fields: by_id[first][field],by_id[second][field]=by_id[second][field],by_id[first][field]
                try: validate_gap_mapping(gaps,stage3); actual=False
                except RuntimeError: actual=True
        elif kind in {'t087_selected_keys_exact','t087_extra_key_excluded','t087_missing_pointer_rejected'}:
            receipt=receipt_from_file((base/inp['receipt_file']).resolve(),inp['input_id'],inp['selected_object_index'])
            if kind=='t087_selected_keys_exact': actual=list(selected_payload(receipt))
            elif kind=='t087_extra_key_excluded':
                receipt=json.loads(json.dumps(receipt,ensure_ascii=False)); receipt['source_path']='/THIS/PARENT/MUST/NOT/BE/READ.json'
                payload=selected_payload(receipt); actual=inp['forbidden_pointer'] not in payload and set(payload)==set(receipt['original_selector']['json_pointers'])
            else:
                receipt=json.loads(json.dumps(receipt,ensure_ascii=False)); receipt['original_selector']['json_pointers'].remove(inp['remove_pointer'])
                try: selected_payload(receipt); actual=False
                except RuntimeError: actual=True
        elif kind in {'capability_mapping_valid','capability_mapping_mutation_rejected','capability_mapping_mirror_tamper_rejected'}:
            mapping=read_jsonl((base/inp['mapping_file']).resolve()); adoption=read_jsonl((base/inp['adoption_file']).resolve()); schema=json.load(open((base/inp['schema_file']).resolve(),encoding='utf-8'))
            receipts=read_jsonl(base/'02_输入身份_选择器与装载回执候选.jsonl')
            capabilities=[item for item in mapping if item.get('record_type')=='CAPABILITY_CLOSURE_CANDIDATE']
            if kind=='capability_mapping_valid':
                result=validate_capability_specs(capabilities,adoption,schema,receipts); actual={key:result[key] for key in exp}
            elif kind=='capability_mapping_mutation_rejected':
                mutations=inp.get('mutations') or [inp['mutation']]
                target=next(item for item in capabilities if item['object_id']==mutations[0]['capability_id'])
                for mutation in mutations:
                    set_nested(target,mutation['field'],mutation['value'])
                try: validate_capability_specs(capabilities,adoption,schema,receipts); actual=False
                except RuntimeError: actual=True
            else:
                receipt=next(item for item in receipts if item['input_id']==inp['input_id'] and int(item['selected_object_index'])==int(inp['selected_object_index']))
                with tempfile.TemporaryDirectory() as temp_dir:
                    tampered=Path(temp_dir)/Path(receipt['mirror_path']).name
                    shutil.copyfile(receipt['mirror_path'],tampered)
                    with open(tampered,'ab') as handle: handle.write(b'\n')
                    receipt['mirror_path']=str(tampered)
                    try: validate_capability_specs(capabilities,adoption,schema,receipts); actual=False
                    except RuntimeError: actual=True
        elif kind=='synthetic_target_minute_mark':
            if inp.get('synthetic_only') is not True: raise RuntimeError('REAL_RECOMPUTATION_FORBIDDEN')
            item=validated_recomputation_test_item(base,inp)
            actual=recompute_target_minute_mark_synthetic(**{key:value for key,value in inp.items() if key not in {'synthetic_only','contract_file','receipt_file','recomputation_id'}})
            actual['method_selected_object_count']=str(len(item['method_selected_objects']))
        elif kind=='synthetic_t087_outer_envelope':
            if inp.get('synthetic_only') is not True: raise RuntimeError('REAL_RECOMPUTATION_FORBIDDEN')
            item=validated_recomputation_test_item(base,inp); actual=recompute_t087_outer_envelope_synthetic(inp['paths'])
            actual['method_selected_object_count']=str(len(item['method_selected_objects']))
        elif kind=='synthetic_joint_interval':
            if inp.get('synthetic_only') is not True: raise RuntimeError('REAL_RECOMPUTATION_FORBIDDEN')
            item=validated_recomputation_test_item(base,inp)
            args={key:value for key,value in inp.items() if key not in {'synthetic_only','contract_file','receipt_file','recomputation_id'}}
            args['method_objects']=[f'{inp["recomputation_id"]}:{index}' for index in range(1,len(item['method_selected_objects'])+1)]
            actual=recompute_joint_interval_synthetic(**args)
        elif kind in {'synthetic_target_minute_mark_rejected','synthetic_t087_outer_envelope_rejected','synthetic_joint_interval_rejected'}:
            if inp.get('synthetic_only') is not True: raise RuntimeError('REAL_RECOMPUTATION_FORBIDDEN')
            try:
                if kind=='synthetic_target_minute_mark_rejected':
                    recompute_target_minute_mark_synthetic(**{key:value for key,value in inp.items() if key!='synthetic_only'})
                elif kind=='synthetic_t087_outer_envelope_rejected':
                    recompute_t087_outer_envelope_synthetic(inp['paths'])
                else:
                    recompute_joint_interval_synthetic(**{key:value for key,value in inp.items() if key!='synthetic_only'})
                actual=False
            except ValueError: actual=True
        elif kind=='recomputation_contract_mutation_rejected':
            contract=json.load(open((base/inp['contract_file']).resolve(),encoding='utf-8')); receipts=read_jsonl((base/inp['receipt_file']).resolve())
            target=next(item for item in contract['items'] if item['recomputation_id']==inp['recomputation_id'])
            for mutation in inp.get('mutations') or [inp['mutation']]:
                set_nested(target,mutation['field'],mutation['value'])
            try: validate_recomputation_contracts(contract,receipts); actual=False
            except RuntimeError: actual=True
        elif kind=='dual_view_ids': actual=sorted(inp['fact_base_ids'])==sorted(inp['ai_ids'])==sorted(inp['user_ids'])
        elif kind=='selected_csv_load':
            receipt=receipt_from_file((base/inp['receipt_file']).resolve(),inp['input_id'],inp['selected_object_index'])
            receipt=json.loads(json.dumps(receipt,ensure_ascii=False)); receipt['source_path']='/THIS/PARENT/MUST/NOT/BE/READ.csv'
            rows=selected_payload(receipt); actual={'selected_content_sha256':receipt['extracted_content_sha256'],'row_count':len(rows)}
        elif kind in {
            'fact_base_schema_valid','fact_base_missing_endpoint_rejected','fact_base_empty_target_rejected',
            'fact_base_composite_candidate_promotion_rejected','fact_base_endpoint_evidence_promotion_rejected',
            'fact_base_copy_funds_boundary_erasure_rejected',
        }:
            records=read_jsonl((base/inp['fact_base_file']).resolve()); schema=json.load(open((base/inp['schema_file']).resolve(),encoding='utf-8'))
            if kind=='fact_base_schema_valid':
                result=validate_fact_base_against_schema(records,schema); actual={key:result[key] for key in exp}
            else:
                if kind=='fact_base_missing_endpoint_rejected':
                    index=next(i for i,item in enumerate(records) if item.get('fact_subtype')=='RELATION_TARGET_OBJECT_REFERENCE'); records.pop(index)
                elif kind=='fact_base_empty_target_rejected':
                    target=next(item for item in records if item.get('record_type')=='RELATION_STATEMENT' and not (item.get('relation') or {}).get('target_event_id')); target['relation']['target_fact_id']=None
                elif kind=='fact_base_composite_candidate_promotion_rejected':
                    target=next(item for item in records if item.get('fact_subtype')=='RELATION_TARGET_OBJECT_REFERENCE' and item.get('target_object_type')=='POSITION_CYCLE_CANDIDATE'); target['target_candidate_ids']=[target['target_candidate_ids'][0]]
                elif kind=='fact_base_endpoint_evidence_promotion_rejected':
                    target=next(item for item in records if item.get('fact_subtype')=='RELATION_TARGET_OBJECT_REFERENCE' and 'COPY_FUNDS_NODE' not in (item.get('source_relation_types') or [])); target['evidence_status']='DIRECT'
                else:
                    target=next(item for item in records if item.get('fact_subtype')=='RELATION_TARGET_OBJECT_REFERENCE' and 'COPY_FUNDS_NODE' in (item.get('source_relation_types') or []))
                    target['object_class']='ACTIVE_TRADE'; target['promotion_prohibited']=False; target['cannot_prove']=''
                try: validate_fact_base_against_schema(records,schema); actual=False
                except RuntimeError: actual=True
        else: raise RuntimeError('UNKNOWN_TEST_KIND:'+kind)
        out.append({'test_id':t['test_id'],'pass':actual==exp,'expected':exp,'actual':actual,'purpose':t.get('purpose')})
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
