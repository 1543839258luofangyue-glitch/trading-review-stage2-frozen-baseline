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

EXCEL_DOCUMENTED_CELL_LIMIT_UTF16=32767
EXCEL_SAFE_CELL_LIMIT_UTF16=30000

def utf16_units(value):
    if not isinstance(value,str):
        raise RuntimeError('UTF16_TEXT_REQUIRED')
    return len(value.encode('utf-16-le'))//2

def split_utf16_safe(value,limit=EXCEL_SAFE_CELL_LIMIT_UTF16):
    if not isinstance(limit,int) or limit<=0 or limit>EXCEL_DOCUMENTED_CELL_LIMIT_UTF16:
        raise RuntimeError('EXCEL_TECHNICAL_CHUNK_LIMIT_INVALID')
    if not isinstance(value,str) or value=='':
        raise RuntimeError('EXCEL_TECHNICAL_CHUNK_TEXT_EMPTY_OR_INVALID')
    chunks=[]; current=[]; current_units=0
    for char in value:
        char_units=2 if ord(char)>0xffff else 1
        if char_units>limit:
            raise RuntimeError('EXCEL_TECHNICAL_CHUNK_CHARACTER_TOO_LARGE')
        if current and current_units+char_units>limit:
            chunks.append(''.join(current)); current=[]; current_units=0
        current.append(char); current_units+=char_units
    if current: chunks.append(''.join(current))
    if ''.join(chunks)!=value or any(utf16_units(chunk)>limit for chunk in chunks):
        raise RuntimeError('EXCEL_TECHNICAL_CHUNK_ROUNDTRIP_FAILED')
    return chunks

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

# This registry is deliberately closed.  A capability declaration is not
# executable merely because it contains an operator-shaped string: the exact
# operator, version, declarative profile and result profile must all be present
# here.  The profile is a bounded specification witness, not the future full
# business implementation of that operator.
OPERATOR_REGISTRY_VERSION='1.0'
SUPPORTED_OPERATOR_REGISTRY={
    'ACTIVE_AND_COPY_SCOPE_PARTITION':{'version':'1.0','declarative_profile_id':'DECLARATIVE_CLASSIFICATION_V1','result_profile':'CLASSIFICATION'},
    'ADJACENT_REVERSE_POSITION_OBJECTIVE_LINKAGE':{'version':'1.0','declarative_profile_id':'DECLARATIVE_RELATION_V1','result_profile':'RELATION'},
    'ANALYSIS_STRATEGY_AND_COUNTERFACTUAL_BOUNDARY':{'version':'1.0','declarative_profile_id':'NO_FACT_BOUNDARY_V1','result_profile':'BOUNDARY'},
    'CANONICAL_CASH_EVENT_DEDUPLICATION_AND_TRANSFER_PAIRING':{'version':'1.0','declarative_profile_id':'DECLARATIVE_RELATION_V1','result_profile':'RELATION'},
    'CONDITION_TO_ORDER_FILL_AND_CYCLE_RELATION_GRAPH':{'version':'1.0','declarative_profile_id':'DECLARATIVE_RELATION_V1','result_profile':'RELATION'},
    'FACT_USER_STATEMENT_INTERPRETATION_AND_STATUS_LAYERING':{'version':'1.0','declarative_profile_id':'DECLARATIVE_CLASSIFICATION_V1','result_profile':'CLASSIFICATION'},
    'FEE_AND_NET_RESULT_COMPONENT_SEPARATION':{'version':'1.0','declarative_profile_id':'DECLARATIVE_MEASURE_V1','result_profile':'MEASURE'},
    'FILL_PRICE_AND_WEIGHTED_AVERAGE_TRANSITION':{'version':'1.0','declarative_profile_id':'DECLARATIVE_MEASURE_V1','result_profile':'MEASURE'},
    'FILL_TO_ORDER_AND_CYCLE_LINKAGE':{'version':'1.0','declarative_profile_id':'DECLARATIVE_RELATION_V1','result_profile':'RELATION'},
    'FUTURE_SCHEMA_AND_FORMAT_BOUNDARY':{'version':'1.0','declarative_profile_id':'NO_FACT_BOUNDARY_V1','result_profile':'BOUNDARY'},
    'IDENTIFIER_MAPPING_WITHOUT_ID_REPLACEMENT':{'version':'1.0','declarative_profile_id':'DECLARATIVE_IDENTITY_V1','result_profile':'IDENTITY'},
    'IDENTITY_RESOLUTION_WITH_SOURCE_BOUNDARIES':{'version':'1.0','declarative_profile_id':'DECLARATIVE_IDENTITY_V1','result_profile':'IDENTITY'},
    'MARGIN_AND_RISK_FIELDS_SEPARATED_NO_INFERENCE_FOR_MISSING_VALUES':{'version':'1.0','declarative_profile_id':'DECLARATIVE_MEASURE_V1','result_profile':'MEASURE'},
    'MARKET_DATA_IDENTITY_WINDOW_AND_COVERAGE':{'version':'1.0','declarative_profile_id':'DECLARATIVE_COVERAGE_V1','result_profile':'COVERAGE'},
    'MFE_MAE_BY_CYCLE_OR_POSITION_STAGE':{'version':'1.0','declarative_profile_id':'DECLARATIVE_MEASURE_V1','result_profile':'MEASURE'},
    'NON_OBJECTIVE_USER_REASON_BOUNDARY':{'version':'1.0','declarative_profile_id':'NO_FACT_BOUNDARY_V1','result_profile':'BOUNDARY'},
    'OBJECTIVE_ACTION_CLASSIFICATION_WITH_EVIDENCE':{'version':'1.0','declarative_profile_id':'DECLARATIVE_CLASSIFICATION_V1','result_profile':'CLASSIFICATION'},
    'ORDER_AND_CONDITION_LIFECYCLE_LINKAGE':{'version':'1.0','declarative_profile_id':'DECLARATIVE_LIFECYCLE_V1','result_profile':'LIFECYCLE'},
    'POSITION_QUANTITY_STATE_TRANSITION':{'version':'1.0','declarative_profile_id':'DECLARATIVE_MEASURE_V1','result_profile':'MEASURE'},
    'POSITION_ZERO_TO_NONZERO_TO_ZERO_CYCLE_GROUPING':{'version':'1.0','declarative_profile_id':'DECLARATIVE_LIFECYCLE_V1','result_profile':'LIFECYCLE'},
    'REALIZED_PNL_BY_FILL_AND_CYCLE':{'version':'1.0','declarative_profile_id':'DECLARATIVE_MEASURE_V1','result_profile':'MEASURE'},
    'REFERENTIAL_AND_QUANTITY_INTEGRITY_CHECKS':{'version':'1.0','declarative_profile_id':'DECLARATIVE_INTEGRITY_V1','result_profile':'INTEGRITY'},
    'SCREENSHOT_CONDITION_AND_CYCLE_LINEAGE_BRIDGE':{'version':'1.0','declarative_profile_id':'DECLARATIVE_LINEAGE_V1','result_profile':'LINEAGE'},
    'SIDE_POSITION_SIDE_AND_POSITION_EFFECT_SEPARATION':{'version':'1.0','declarative_profile_id':'DECLARATIVE_CLASSIFICATION_V1','result_profile':'CLASSIFICATION'},
    'STABLE_ID_AND_SOURCE_NAMESPACE_PRESERVATION':{'version':'1.0','declarative_profile_id':'DECLARATIVE_IDENTITY_V1','result_profile':'IDENTITY'},
    'STOP_LOSS_LIFECYCLE_WITH_UNKNOWN_RELATION_PRESERVATION':{'version':'1.0','declarative_profile_id':'DECLARATIVE_LIFECYCLE_V1','result_profile':'LIFECYCLE'},
    'TAKE_PROFIT_LIFECYCLE_WITH_UNKNOWN_RELATION_PRESERVATION':{'version':'1.0','declarative_profile_id':'DECLARATIVE_LIFECYCLE_V1','result_profile':'LIFECYCLE'},
    'TIMELINE_UNION_PRESERVE_EQUAL_TIME_PARALLEL_EVENTS':{'version':'1.0','declarative_profile_id':'DECLARATIVE_TIMELINE_V1','result_profile':'TIMELINE'},
    'TIME_BOUNDED_EQUITY_ANCHORS_AND_UNKNOWN_GAPS':{'version':'1.0','declarative_profile_id':'DECLARATIVE_TIMELINE_V1','result_profile':'TIMELINE'},
    'TIME_NORMALIZATION_WITH_ORIGINAL_VALUE_AND_PRECISION':{'version':'1.0','declarative_profile_id':'DECLARATIVE_TIMELINE_V1','result_profile':'TIMELINE'},
    'USER_INTERFACE_PRODUCT_BOUNDARY':{'version':'1.0','declarative_profile_id':'NO_FACT_BOUNDARY_V1','result_profile':'BOUNDARY'},
    'USER_STAGE_AGGREGATION_ACROSS_POSITION_PRICE_AND_MFE_MAE_COMPONENTS':{'version':'1.0','declarative_profile_id':'DECLARATIVE_MEASURE_V1','result_profile':'MEASURE'},
    'VERSION_CORRECTION_AND_SOURCE_IDENTITY_LINEAGE':{'version':'1.0','declarative_profile_id':'DECLARATIVE_LINEAGE_V1','result_profile':'LINEAGE'},
}
DECLARATIVE_PROFILE_REGISTRY={
    'DECLARATIVE_CLASSIFICATION_V1':'CLASSIFICATION',
    'DECLARATIVE_COVERAGE_V1':'COVERAGE',
    'DECLARATIVE_IDENTITY_V1':'IDENTITY',
    'DECLARATIVE_INTEGRITY_V1':'INTEGRITY',
    'DECLARATIVE_LIFECYCLE_V1':'LIFECYCLE',
    'DECLARATIVE_LINEAGE_V1':'LINEAGE',
    'DECLARATIVE_MEASURE_V1':'MEASURE',
    'DECLARATIVE_RELATION_V1':'RELATION',
    'DECLARATIVE_TIMELINE_V1':'TIMELINE',
    'NO_FACT_BOUNDARY_V1':'BOUNDARY',
}
SUPPORTED_CAPABILITY_TRANSFORMS={
    'PRESERVE_EXACT_VALUE','PRESERVE_AND_DECIMAL_CANONICALIZE_IF_NUMERIC',
    'PRESERVE_TIME_VALUE_WITHOUT_TIMEZONE_INFERENCE','PARSE_JSON_TEXT_PRESERVE_RAW',
}
SUPPORTED_FIELD_USAGES={
    'JOIN_KEY','OBJECT_ID','SEQUENCE','DATE_SET','TIME','MEASURE','CLASSIFICATION','EVIDENCE','LINEAGE','SOURCE_VALUE',
}
SUPPORTED_MISSING_POLICIES={'PRESERVE_UNKNOWN','REJECT_FOR_SELECTED_JOIN_WITNESS'}
FIELD_RESULT_CHECK='SOURCE_VALUE_OR_EXPLICIT_UNKNOWN_AND_DECLARED_TRANSFORM_EXACT'
FORBIDDEN_CROSS_SOURCE_LOCATOR_FIELDS={
    'source_row','_source_row','source_row_number','row_number','row_no','line_no',
    'manual_source_row','来源行号','来源行',
}

def operator_registry_sha256():
    payload={'registry_version':OPERATOR_REGISTRY_VERSION,'operators':SUPPORTED_OPERATOR_REGISTRY}
    return hashlib.sha256(canonical(payload).encode('utf-8')).hexdigest()

def capability_operator_parameters(item):
    """Freeze exact declarative inputs without claiming future business execution."""
    join=item['assembly_spec']['join']
    operator=join['operator']; implementation=SUPPORTED_OPERATOR_REGISTRY[operator]
    field_rule_scope=[{
        'input_id':binding['input_id'],
        'selected_object_index':int(binding['selected_object_index']),
        'source_role':binding['source_role'],
        'field_rules':binding['field_rules'],
    } for binding in item.get('source_bindings') or []]
    return {
        'operator_id':operator,
        'declarative_profile_id':implementation['declarative_profile_id'],
        'business_operator_semantics_execution':'NOT_AUTHORIZED_NOT_RUN',
        'relation_direction':join['direction'],
        'cardinality':join['cardinality'],
        'join_required':bool(join['required']),
        'join_key_families':join.get('keys') or [],
        'missing_join_key_behavior':join['missing_join_key_behavior'],
        'field_rule_scope_sha256':hashlib.sha256(canonical(field_rule_scope).encode('utf-8')).hexdigest(),
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

RUNNABLE_CAPABILITY_STATUS='CANDIDATE_SPECIFIED_PENDING_END_TO_END_VALIDATION'
UNRESOLVED_CAPABILITY_STATUS='UNRESOLVED_PRESERVED_NO_FACT_CLOSURE'
BOUNDARY_CAPABILITY_STATUS='NON_OBJECTIVE_BOUNDARY_CLOSED_NO_FACT_OUTPUT'
PENDING_CAPABILITY_STATUS='PENDING_USER_ACCEPTANCE_NO_PRODUCTION_CLOSURE'

def capability_mirror_rows(receipt):
    """Read only the locked selected-object mirror recorded by receipt 02."""
    mirror=Path(receipt['mirror_path'])
    if not mirror.is_file() or sha_file(mirror)!=receipt['extracted_content_sha256']:
        raise RuntimeError('CAPABILITY_RECEIPT_MIRROR_IDENTITY_MISMATCH:'+receipt['input_id'])
    if mirror.suffix=='.csv':
        with open(mirror,encoding='utf-8-sig',newline='') as handle:
            rows=list(csv.DictReader(handle))
        actual=len(rows)
    elif mirror.suffix=='.jsonl':
        rows=read_jsonl(mirror); actual=len(rows)
    elif mirror.suffix=='.json':
        value=json.load(open(mirror,encoding='utf-8'))
        rows=[value] if isinstance(value,dict) else value
        selector=receipt.get('original_selector') or {}
        actual=len(value) if selector.get('kind')=='JSON_SELECTED_POINTERS' else len(rows)
    else:
        raise RuntimeError('CAPABILITY_RECEIPT_MIRROR_TYPE_UNSUPPORTED:'+mirror.suffix)
    if not isinstance(rows,list) or not all(isinstance(row,dict) for row in rows):
        raise RuntimeError('CAPABILITY_MIRROR_ROW_SHAPE_INVALID:'+receipt['input_id'])
    if actual!=int(receipt['actual_count']):
        raise RuntimeError('CAPABILITY_MIRROR_COUNT_MISMATCH:'+receipt['input_id'])
    return rows

def capability_source_locator(row,original_index):
    parts=['selected-mirror-record-'+str(original_index+1)]
    for field in ('_sheet','source_sheet','sheet'):
        if row.get(field) not in (None,''):
            parts.append(field+'='+str(row[field])); break
    for field in ('_source_row','source_row','source_row_number','row_no','line_no'):
        if row.get(field) not in (None,''):
            parts.append(field+'='+str(row[field])); break
    return ';'.join(parts)

def capability_join_value(value):
    if value in (None,''): return []
    values=value if isinstance(value,list) else [value]
    return [canonical(item) if isinstance(item,(dict,list)) else str(item) for item in values if item not in (None,'')]

def parse_explicit_offset_datetime(value):
    """Parse only a datetime whose value itself carries an explicit UTC/offset marker."""
    text=str(value or '').strip()
    if not text: return None
    normalized=text
    if normalized.endswith('Z'):
        normalized=normalized[:-1]+'+00:00'
    elif re.search(r' UTC$',normalized):
        normalized=re.sub(r' UTC$','+00:00',normalized)
    elif re.search(r' UTC[+-]\d{2}:\d{2}$',normalized):
        normalized=re.sub(r' UTC([+-]\d{2}:\d{2})$',r'\1',normalized)
    elif re.search(r' [+-]\d{2}:\d{2}$',normalized):
        normalized=re.sub(r' ([+-]\d{2}:\d{2})$',r'\1',normalized)
    elif re.search(r'[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?[+-]\d{2}:\d{2}$',normalized):
        pass
    else:
        return None
    try: parsed=datetime.fromisoformat(normalized)
    except ValueError: return None
    return parsed if parsed.tzinfo is not None else None

def capability_transform(transform,value):
    if transform not in SUPPORTED_CAPABILITY_TRANSFORMS:
        raise RuntimeError('CAPABILITY_TRANSFORM_NOT_IMPLEMENTED:'+str(transform))
    if transform=='PRESERVE_EXACT_VALUE': return value
    if transform=='PARSE_JSON_TEXT_PRESERVE_RAW':
        if not isinstance(value,str):
            raise RuntimeError('CAPABILITY_JSON_TEXT_REQUIRED')
        try: parsed=json.loads(value,parse_float=str,parse_int=str)
        except json.JSONDecodeError as error:
            raise RuntimeError('CAPABILITY_JSON_TEXT_PARSE_FAILED') from error
        return normalize_business_value_tree(parsed)
    if transform=='PRESERVE_AND_DECIMAL_CANONICALIZE_IF_NUMERIC':
        if value in (None,''): return value
        text=str(value)
        return decimal_text(text) if re.fullmatch(r'-?(?:\d+)(?:\.\d+)?',text) else value
    if transform=='PRESERVE_TIME_VALUE_WITHOUT_TIMEZONE_INFERENCE':
        if value in (None,''): return value
        text=str(value).strip()
        explicit=parse_explicit_offset_datetime(text)
        if explicit is not None:
            return {
                'raw_value':value,
                'representation':'PARSED_EXPLICIT_OFFSET_DATETIME_NO_TIMEZONE_INFERENCE',
                'normalized_utc':explicit.astimezone(timezone.utc).isoformat(),
            }
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}',text):
            return {
                'raw_value':value,
                'representation':'PARSED_DATE_ONLY_NO_TIMEZONE_INFERENCE',
                'normalized_date':text,
            }
        parsed=parse_time(text)
        if parsed is not None:
            return {
                'raw_value':value,
                'representation':'PARSED_LOCAL_DATETIME_WITHOUT_TIMEZONE_INFERENCE',
                'normalized_local':parsed.strftime('%Y-%m-%d %H:%M:%S.%f').rstrip('0').rstrip('.'),
            }
        if re.fullmatch(r'\d{13}',text):
            representation='EPOCH_MILLISECONDS_PRESERVED_TIMEZONE_BASIS_NOT_DECLARED'
        elif re.fullmatch(r'\d+(?:\.\d+)?',text) and Decimal(text)>0 and Decimal(text)<100000:
            representation='POSSIBLE_EXCEL_SERIAL_PRESERVED_DATE_SYSTEM_NOT_DECLARED'
        else:
            representation='UNPARSED_TIME_TEXT_PRESERVED_NO_TIMEZONE_INFERENCE'
        return {'raw_value':value,'representation':representation,'normalized_local':None}
    raise RuntimeError('CAPABILITY_TRANSFORM_NOT_IMPLEMENTED:'+str(transform))

CAPABILITY_JSON_TEXT_FIELDS={
    'boundary_minutes_json','mark_cycle_mae_candidate_minute_intervals_json',
    'mark_cycle_mfe_candidate_minute_intervals_json','mark_mae_candidate_minute_intervals_json',
    'mark_mfe_candidate_minute_intervals_json','market_input_sha256_json',
    'ordinary_cycle_mae_candidate_minutes_json','ordinary_cycle_mfe_candidate_minutes_json',
    'ordinary_mae_candidate_minutes_json','ordinary_mfe_candidate_minutes_json',
    'precision_summary','source_stage_ids_json','source_zip_list_json','source_zip_sha256_list_json','utc_dates_json',
}
CAPABILITY_CLASSIFICATION_FIELDS={
    'from_account','to_account','source_business_type','source_business_type_standard',
    'cross_source_status','time_in_force','order_create_time_precision','order_update_time_precision',
    '时间精度','时间边界规则','cycle_cash_result_formula','precision_summary',
    'ratio_fields_present','均价重建核对','source_category','source_platform','交易来源分类',
    'order_create_time_source_timezone','order_create_time_source_timezone_basis',
    'order_create_time_source_timezone_confidence','order_update_time_source_timezone',
    'order_update_time_source_timezone_basis','order_update_time_source_timezone_confidence',
    'canonical_cash_inclusion','comparison_operator','condition_role','direction','duplicate_basis',
    'duplicate_class','is_blocking','is_triggered','maker_only','no_fill_flag',
    'partial_fill_then_canceled_or_expired','position_side','reduce_only','reused_after_full_validation',
    'scope','side','side_domain','side_raw','side_standard_cn','side_standard_code','sign_basis','status',
    'trigger_basis','zip_crc_passed','zip_structure_passed','新编号状态','旧编号保留状态',
    'Maker/Taker','对当前周期的仓位作用','新增5笔记录性质',
    'D','E','close_position','order_id_storage','field','warning_codes','checksum_match','interval',
    '关联等级','条件作用类别',
}
CAPABILITY_SOURCE_VALUE_FIELDS={
    'quantity_source_text',
}
CAPABILITY_OBJECT_ID_FIELDS={
    'source_stage_ids_json','raw__用户ID','对应正式Order','技术Fill ID','快照区间ID',
    'C','symbol','symbol_raw','symbol_standard','品种','合约','raw__代币名称/币种名称/币对',
    'asset','base_asset','quote_asset','margin_asset','币种','手续费资产',
    'primary_key','text','旧P3候选TU','形成阶段Fill ID列表','形成阶段trade_id列表',
    'mirror_of_source_record_id',
}
CAPABILITY_SEQUENCE_FIELDS={'stage_no','事件顺序','费用序号','同毫秒组内顺序'}
CAPABILITY_DATE_SET_FIELDS={'阶段涉及UTC日期集合','utc_dates_json'}
CAPABILITY_LINEAGE_FIELDS={
    '_sheet','_source_row','manual_source_row','source_row_number','source_file','source_h0g_file',
    'source_screenshot_path','source_dataset','source_sheet','source_zip_list_json','source_zip_sha256_list_json',
    '技术来源','映射来源SHA-256','来源工作表','来源数据版本','来源文件','来源文件SHA-256','来源行号',
    '编号来源','账户来源','证据来源工作表','证据来源文件','阶段05来源SHA-256','P3来源SHA-256',
    '周期主表SHA-256','复合指纹','zip_url','所需aggTrades日包','所需klines日包','所需markPriceKlines日包',
}
CAPABILITY_TIMEPOINT_FIELDS={
    '前一张08:00实际总资产时间','后一张08:00实际总资产时间','开始边界分钟','结束边界分钟',
    'boundary_minutes_json','mark_cycle_mae_candidate_minute_intervals_json',
    'mark_cycle_mfe_candidate_minute_intervals_json','mark_mae_candidate_minute_intervals_json',
    'mark_mfe_candidate_minute_intervals_json','ordinary_cycle_mae_candidate_minutes_json',
    'ordinary_cycle_mfe_candidate_minutes_json','ordinary_mae_candidate_minutes_json',
    'ordinary_mfe_candidate_minutes_json',
    'M','O','stage_start_ms','stage_end_ms_exclusive','持仓开始','持仓结束',
    '覆盖起点','覆盖终点',
}
CAPABILITY_MEASURE_FIELDS={
    '已实现盈亏（来源事实）','手续费（来源事实）','aggtrades_boundary_minutes_completed',
    'klines_actual_minutes','klines_missing_minutes','klines_required_minutes','time_difference_seconds',
    '全部条件委托覆盖秒数','持仓秒数','最大止损空档秒数',
    '止损未覆盖总秒数','止损覆盖总秒数','止盈覆盖总秒数',
    '前一张08:00实际总资产','后一张08:00实际总资产',
    '前一张实际08:00总资产','后一张实际08:00总资产',
    'candidate_evidence_count','actual_zip_bytes','uncompressed_csv_bytes','head_content_length',
    'OCR_or_visual_extracted_value','ordinary_cycle_mae','ordinary_cycle_mfe','position_before','position_after',
    '仓位变化前','仓位变化后','修正差异','全部条件委托覆盖率','加权成交价',
    '区间canonical事件数','已确认事件滚动到区间末值','已确认资金事件合计',
    '成交笔数','条件委托总数','止损覆盖率','止盈覆盖率_非风险保护率','正式Fill数','正式Order数','覆盖秒数',
}
CAPABILITY_BOOLEAN_OR_FORMAT_SUFFIXES=(
    '_currency_symbol','_is_empty','_negative_sign','_parenthesis_negative',
    '_precision_changed','_scientific_notation','_thousand_separator',
)

def capability_field_semantics(field,is_join_key=False):
    """Return the one deterministic usage/transform/missing policy for a source field."""
    if is_join_key:
        return 'JOIN_KEY','PRESERVE_EXACT_VALUE','REJECT_FOR_SELECTED_JOIN_WITNESS'
    text=str(field); lower=text.lower()
    tokens=set(value for value in re.split(r'[^a-z0-9]+',lower) if value)
    if text in CAPABILITY_CLASSIFICATION_FIELDS or lower.endswith(CAPABILITY_BOOLEAN_OR_FORMAT_SUFFIXES) or lower.endswith('_precision_code'):
        usage='CLASSIFICATION'
    elif text in CAPABILITY_OBJECT_ID_FIELDS:
        usage='OBJECT_ID'
    elif text in CAPABILITY_SEQUENCE_FIELDS:
        usage='SEQUENCE'
    elif text in CAPABILITY_DATE_SET_FIELDS:
        usage='DATE_SET'
    elif text in CAPABILITY_SOURCE_VALUE_FIELDS:
        usage='SOURCE_VALUE'
    elif text in CAPABILITY_LINEAGE_FIELDS:
        usage='LINEAGE'
    elif text in CAPABILITY_TIMEPOINT_FIELDS:
        usage='TIME'
    elif text in CAPABILITY_MEASURE_FIELDS:
        usage='MEASURE'
    elif lower in {'_sheet','_source_row'} or lower in {'source_path','source_sheet','source_row','row_number'} or any(value in lower for value in (
        'sha256','checksum','relative_path','file_name','filename','record_hash','mirror_of','zip_inner','verification_tool',
    )) or any(value in text for value in ('来源SHA','来源行','来源表','来源文件','技术来源','账户来源','编号来源')):
        usage='LINEAGE'
    elif lower.endswith('_id') or lower.endswith('_ids') or lower=='tid' or any(value in text for value in ('编号','组ID','记录ID','交易ID','周期ID')):
        usage='OBJECT_ID'
    elif 'evidence' in lower or '证据' in text:
        usage='EVIDENCE'
    elif any(value in lower for value in (
        '_status','_type','_direction','_scope','_confidence','_method','_rule','_version','recommendation',
    )) or any(value in text for value in ('状态','类型','方向','口径','是否','规则版本','映射等级')):
        usage='CLASSIFICATION'
    elif (
        not lower.endswith(('_minutes','_seconds','_duration','_count'))
        and not any(value in text for value in ('秒数','分钟数','时长'))
        and (
            tokens.intersection({'time','timestamp','date','utc','beijing','millisecond','milliseconds'})
            or lower.endswith(('_time','_timestamp','_utc','_date','_at'))
            or lower.startswith(('time_','timestamp_','utc_','date_'))
            or any(value in lower for value in ('_time_','_timestamp_','_utc_','created_at','updated_at'))
            or any(value in text for value in ('时间','日期','毫秒','开始UTC','结束UTC','周期开始','周期结束'))
        )
    ):
        usage='TIME'
    elif any(value in lower for value in (
        'amount','price','quantity','commission','pnl','fee','balance','equity','margin','count','ratio',
        'multiplier','notional','average','maximum','total_wealth_effect','cash_result','net_exact','duration','minutes','seconds',
    )) or any(value in text for value in (
        '数量','金额','价格','盈亏','手续费','成交额','合约乘数','仓位前','仓位后','滚动值','差额','均价','秒数','分钟数','时长',
    )):
        usage='MEASURE'
    elif lower.startswith('/') or lower.endswith('_json') or lower.endswith('_jsonl'):
        usage='SOURCE_VALUE'
    else:
        usage='SOURCE_VALUE'
    if text in CAPABILITY_JSON_TEXT_FIELDS:
        transform='PARSE_JSON_TEXT_PRESERVE_RAW'
    elif usage=='MEASURE':
        transform='PRESERVE_AND_DECIMAL_CANONICALIZE_IF_NUMERIC'
    elif usage=='TIME':
        transform='PRESERVE_TIME_VALUE_WITHOUT_TIMEZONE_INFERENCE'
    else:
        transform='PRESERVE_EXACT_VALUE'
    return usage,transform,'PRESERVE_UNKNOWN'

def capability_apply_field_rule(rule,value,selected_join_field=False):
    missing=value in (None,'')
    if missing and rule['missing_policy']=='REJECT_FOR_SELECTED_JOIN_WITNESS' and selected_join_field:
        raise RuntimeError('CAPABILITY_SELECTED_JOIN_FIELD_MISSING:'+rule['source_field'])
    if missing:
        normalized={
            'status':'UNKNOWN','reason':'SOURCE_FIELD_MISSING_OR_EMPTY',
            'source_field':rule['source_field'],
        }
    else: normalized=capability_transform(rule['transform'],value)
    if missing:
        passed=normalized=={'status':'UNKNOWN','reason':'SOURCE_FIELD_MISSING_OR_EMPTY','source_field':rule['source_field']}
    elif rule['transform']=='PRESERVE_EXACT_VALUE':
        passed=normalized==value
    elif rule['transform']=='PRESERVE_AND_DECIMAL_CANONICALIZE_IF_NUMERIC':
        text=str(value); passed=(normalized==decimal_text(text) if re.fullmatch(r'-?(?:\d+)(?:\.\d+)?',text) else normalized==value)
    elif rule['transform']=='PARSE_JSON_TEXT_PRESERVE_RAW':
        passed=(
            isinstance(value,str)
            and normalized==normalize_business_value_tree(json.loads(value,parse_float=str,parse_int=str))
        )
    elif rule['transform']=='PRESERVE_TIME_VALUE_WITHOUT_TIMEZONE_INFERENCE':
        allowed={
            'PARSED_EXPLICIT_OFFSET_DATETIME_NO_TIMEZONE_INFERENCE',
            'PARSED_DATE_ONLY_NO_TIMEZONE_INFERENCE',
            'PARSED_LOCAL_DATETIME_WITHOUT_TIMEZONE_INFERENCE',
            'EPOCH_MILLISECONDS_PRESERVED_TIMEZONE_BASIS_NOT_DECLARED',
            'POSSIBLE_EXCEL_SERIAL_PRESERVED_DATE_SYSTEM_NOT_DECLARED',
            'UNPARSED_TIME_TEXT_PRESERVED_NO_TIMEZONE_INFERENCE',
        }
        passed=isinstance(normalized,dict) and normalized.get('raw_value')==value and normalized.get('representation') in allowed
        if passed and normalized['representation']=='PARSED_EXPLICIT_OFFSET_DATETIME_NO_TIMEZONE_INFERENCE':
            explicit=parse_explicit_offset_datetime(value)
            passed=explicit is not None and normalized.get('normalized_utc')==explicit.astimezone(timezone.utc).isoformat()
        elif passed and normalized['representation']=='PARSED_DATE_ONLY_NO_TIMEZONE_INFERENCE':
            passed=bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}',str(value).strip())) and normalized.get('normalized_date')==str(value).strip()
        elif passed and normalized['representation']=='PARSED_LOCAL_DATETIME_WITHOUT_TIMEZONE_INFERENCE':
            parsed=parse_time(str(value).strip())
            expected_local=(parsed.strftime('%Y-%m-%d %H:%M:%S.%f').rstrip('0').rstrip('.') if parsed is not None else None)
            passed=normalized.get('normalized_local')==expected_local
        elif passed and normalized['representation']=='EPOCH_MILLISECONDS_PRESERVED_TIMEZONE_BASIS_NOT_DECLARED':
            passed=bool(re.fullmatch(r'\d{13}',str(value).strip())) and normalized.get('normalized_local') is None
        elif passed and normalized['representation']=='POSSIBLE_EXCEL_SERIAL_PRESERVED_DATE_SYSTEM_NOT_DECLARED':
            text=str(value).strip()
            passed=bool(re.fullmatch(r'\d+(?:\.\d+)?',text)) and Decimal(text)>0 and Decimal(text)<100000 and normalized.get('normalized_local') is None
        elif passed and normalized['representation']=='UNPARSED_TIME_TEXT_PRESERVED_NO_TIMEZONE_INFERENCE':
            text=str(value).strip()
            explicit=parse_explicit_offset_datetime(text)
            passed=(
                explicit is None
                and parse_time(text) is None
                and not re.fullmatch(r'\d{4}-\d{2}-\d{2}',text)
                and not re.fullmatch(r'\d{13}',text)
                and not (re.fullmatch(r'\d+(?:\.\d+)?',text) and Decimal(text)>0 and Decimal(text)<100000)
                and normalized.get('normalized_local') is None
            )
    else: passed=False
    return normalized,passed,missing

def run_capability_declarative_profile_witness(operator,source_witnesses,join_witness,output_path,closure_status,execution_status):
    """Witness a declared operator contract without executing its future business semantics."""
    implementation=SUPPORTED_OPERATOR_REGISTRY.get(operator)
    if implementation is None:
        raise RuntimeError('CAPABILITY_OPERATOR_ID_NOT_REGISTERED:'+str(operator))
    declarative_profile_id=implementation['declarative_profile_id']; profile=implementation['result_profile']
    if DECLARATIVE_PROFILE_REGISTRY.get(declarative_profile_id)!=profile:
        raise RuntimeError('CAPABILITY_DECLARATIVE_PROFILE_NOT_REGISTERED:'+declarative_profile_id)
    usage_counts=Counter(
        rule['usage'] for witness in source_witnesses for rule in witness.get('applied_field_rules') or []
    )
    common={
        'witness_status':(
            'BOUNDED_DECLARATIVE_PROFILE_WITNESS'
            if closure_status==RUNNABLE_CAPABILITY_STATUS else 'STATUS_GATE_NO_DECLARATIVE_PROFILE_OUTPUT'
        ),
        'operator_id':operator,'declarative_profile_id':declarative_profile_id,'result_profile':profile,
        'output_path':output_path,'source_witness_count':len(source_witnesses),
        'usage_counts':dict(sorted(usage_counts.items())),
        'join_status':(join_witness or {}).get('status'),
        'formal_fact_output_count':0,
        'business_operator_semantics_executed':False,
        'claim_limit':'FIELD_MAPPING_JOIN_AND_DECLARATIVE_PROFILE_WITNESS_ONLY; BUSINESS_OPERATOR_SEMANTICS_NOT_EXECUTED; NOT_A_FORMAL_BUSINESS_RESULT',
    }
    if closure_status!=RUNNABLE_CAPABILITY_STATUS:
        common['gate_execution_status']=execution_status
        common['witness_sha256']=hashlib.sha256(canonical(common).encode('utf-8')).hexdigest()
        return common
    profile_details={
        'CLASSIFICATION':{'classification_field_count':usage_counts['CLASSIFICATION']},
        'COVERAGE':{'coverage_pair_count':len((join_witness or {}).get('matches') or [])},
        'IDENTITY':{'identity_field_count':usage_counts['OBJECT_ID']+usage_counts['JOIN_KEY']},
        'INTEGRITY':{'checked_field_count':sum(usage_counts.values()),'unjoined_binding_count':len((join_witness or {}).get('unjoined_bindings') or [])},
        'LIFECYCLE':{'time_field_count':usage_counts['TIME'],'relation_pair_count':len((join_witness or {}).get('matches') or [])},
        'LINEAGE':{'lineage_field_count':usage_counts['LINEAGE'],'source_locators':[item['source_locator'] for item in source_witnesses]},
        'MEASURE':{'measure_field_count':usage_counts['MEASURE']},
        'RELATION':{'pairwise_relation_witness_count':sum(match.get('match_scope')=='PAIRWISE_DECLARED_KEY_WITNESS_ONLY' for match in (join_witness or {}).get('matches') or [])},
        'TIMELINE':{'time_field_count':usage_counts['TIME'],'equal_time_parallel_order_not_inferred':True},
        'BOUNDARY':{'objective_output_forbidden':True},
    }
    if profile not in profile_details:
        raise RuntimeError('CAPABILITY_DECLARATIVE_PROFILE_NOT_REGISTERED:'+profile)
    common['profile_result']=profile_details[profile]
    common['witness_sha256']=hashlib.sha256(canonical(common).encode('utf-8')).hexdigest()
    return common

def capability_payload_cache(receipts,required_keys=None):
    cache={}
    for receipt in receipts:
        key=(receipt['input_id'],int(receipt['selected_object_index']))
        if required_keys is not None and key not in required_keys: continue
        rows=capability_mirror_rows(receipt)
        indexed=[{
            'original_index':index,
            'row':row,
            'row_sha256':hashlib.sha256(canonical(row).encode('utf-8')).hexdigest(),
            'source_locator':capability_source_locator(row,index),
        } for index,row in enumerate(rows)]
        cache[key]=sorted(indexed,key=lambda item:(item['row_sha256'],item['source_locator']))
    return cache

def capability_join_witness(item,payload_cache):
    join=item['assembly_spec']['join']
    if not join['required']:
        return {
            'status':'NOT_REQUIRED_SOURCE_ROWS_REMAIN_SEPARATE','matches':[],
            'unjoined_bindings':sorted([[binding['input_id'],int(binding['selected_object_index'])] for binding in item['source_bindings']]),
            'claim_limit':'NO_CROSS_SOURCE_RELATION_OR_FULL_JOIN_CLAIM',
        },{}
    matches=[]; selected_rows={}; joined_keys=set()
    for family in join.get('keys') or []:
        aliases=family.get('verified_source_aliases') or []
        canonical_key=family.get('canonical_key') or ''
        if canonical_key.lower() in FORBIDDEN_CROSS_SOURCE_LOCATOR_FIELDS:
            raise RuntimeError('CAPABILITY_ROW_LOCATOR_DECLARED_AS_JOIN_KEY:'+item['object_id'])
        if any(str(alias.get('source_field') or '').lower() in FORBIDDEN_CROSS_SOURCE_LOCATOR_FIELDS for alias in aliases):
            raise RuntimeError('CAPABILITY_ROW_LOCATOR_ALIAS_DECLARED_AS_JOIN_KEY:'+item['object_id'])
        value_rows_by_alias=[]
        for alias in aliases:
            key=(alias['input_id'],int(alias['selected_object_index'])); value_rows=defaultdict(list)
            for indexed in payload_cache[key]:
                for value in capability_join_value(indexed['row'].get(alias['source_field'])):
                    value_rows[value].append(indexed)
            value_rows_by_alias.append((alias,key,value_rows))
        for left_index in range(len(value_rows_by_alias)):
            for right_index in range(left_index+1,len(value_rows_by_alias)):
                left,left_key,left_rows=value_rows_by_alias[left_index]
                right,right_key,right_rows=value_rows_by_alias[right_index]
                if left_key==right_key: continue
                common=set(left_rows)&set(right_rows)
                if not common: continue
                selected_value=sorted(common)[0]
                left_row=left_rows[selected_value][0]; right_row=right_rows[selected_value][0]
                selected_rows.setdefault(left_key,left_row); selected_rows.setdefault(right_key,right_row)
                match_scope=('COVERAGE_ONLY_NOT_EVENT_IDENTITY' if canonical_key.lower()=='symbol' else 'PAIRWISE_DECLARED_KEY_WITNESS_ONLY')
                if match_scope=='PAIRWISE_DECLARED_KEY_WITNESS_ONLY':
                    joined_keys.update((left_key,right_key))
                matches.append({
                    'canonical_key':canonical_key,'raw_value':selected_value,
                    'match_scope':match_scope,
                    'match_count_left':len(left_rows[selected_value]),'match_count_right':len(right_rows[selected_value]),
                    'aliases':[
                        {'input_id':left_key[0],'selected_object_index':left_key[1],'source_field':left['source_field'],'source_locator':left_row['source_locator'],'selected_row_sha256':left_row['row_sha256']},
                        {'input_id':right_key[0],'selected_object_index':right_key[1],'source_field':right['source_field'],'source_locator':right_row['source_locator'],'selected_row_sha256':right_row['row_sha256']},
                    ],
                })
    if not matches: raise RuntimeError('CAPABILITY_REAL_JOIN_WITNESS_NOT_FOUND:'+item['object_id'])
    all_keys={(binding['input_id'],int(binding['selected_object_index'])) for binding in item['source_bindings']}
    has_relation_witness=any(match['match_scope']=='PAIRWISE_DECLARED_KEY_WITNESS_ONLY' for match in matches)
    return {
        'status':('EXACT_DECLARED_KEY_PAIR_WITNESSES_ON_LOCKED_MIRRORS' if has_relation_witness else 'COVERAGE_KEY_WITNESS_ONLY_SOURCES_REMAIN_UNJOINED'),
        'matches':matches,
        'unjoined_bindings':sorted([list(key) for key in all_keys-joined_keys]),
        'claim_limit':'PAIRWISE_WITNESSES_ONLY; NO_UNIQUE_OR_FULLY_CONNECTED_BUSINESS_FACT_CLAIM',
    },selected_rows

def capability_expected_execution_status(closure_status):
    return {
        RUNNABLE_CAPABILITY_STATUS:'BOUNDED_REAL_MIRROR_FIELD_AND_JOIN_WITNESS_PASSED',
        UNRESOLVED_CAPABILITY_STATUS:'UNRESOLVED_NO_CONFIRMED_FACT_EMITTED',
        BOUNDARY_CAPABILITY_STATUS:'BOUNDARY_NO_OBJECTIVE_FACT_EMITTED',
        PENDING_CAPABILITY_STATUS:'PENDING_USER_ACCEPTANCE_NO_PRODUCTION_OUTPUT',
    }.get(closure_status)

def build_capability_witness_receipt(item,receipt_map,payload_cache):
    operator=item['assembly_spec']['join']['operator']
    implementation=SUPPORTED_OPERATOR_REGISTRY.get(operator)
    if implementation is None or DECLARATIVE_PROFILE_REGISTRY.get(implementation['declarative_profile_id'])!=implementation['result_profile']:
        raise RuntimeError('CAPABILITY_OPERATOR_ID_NOT_REGISTERED:'+operator)
    closure_status=item['closure_status']
    execution_status=capability_expected_execution_status(closure_status)
    if execution_status is None: raise RuntimeError('CAPABILITY_CLOSURE_STATUS_UNSUPPORTED:'+closure_status)
    source_receipt_identities=[]
    for binding in item.get('source_bindings') or []:
        key=(binding['input_id'],int(binding['selected_object_index']))
        receipt=receipt_map.get(key)
        if receipt is None: raise RuntimeError('CAPABILITY_RECEIPT_NOT_FOUND:'+item['object_id']+':'+str(key))
        source_receipt_identities.append({
            'input_id':key[0],'selected_object_index':key[1],
            'mirror_path':receipt['mirror_path'],'mirror_sha256':receipt['extracted_content_sha256'],
            'actual_count':int(receipt['actual_count']),
        })
    receipt={
        'record_type':'CAPABILITY_BOUNDED_EXECUTION_RECEIPT',
        'capability_id':item['object_id'],'capability_name':item['name'],
        'operator_id':operator,'operator_version':implementation['version'],
        'declarative_profile_id':implementation['declarative_profile_id'],'result_profile':implementation['result_profile'],
        'operator_registry_sha256':operator_registry_sha256(),
        'closure_status':closure_status,'execution_status':execution_status,
        'output_path':item['capability_output']['path'],
        'source_receipt_identities':source_receipt_identities,
        'source_witnesses':[],'join_witness':None,'declarative_profile_witness':None,
        'candidate_witness_output_count':0,'formal_fact_output_count':0,
        'explicit_unknown_field_count':0,
        'adoption_status':'NOT_FORMALLY_ADOPTED_BY_THIS_BOUNDED_TEST',
        'scope_statement':'LOCKED_02_MIRRORS_BOUNDED_WITNESS_ONLY_NOT_FULL_136_BUILD',
        'result_checks':[],
    }
    if closure_status!=RUNNABLE_CAPABILITY_STATUS:
        receipt['join_witness']={'status':'NOT_RUN_BY_CLOSURE_GATE','canonical_key':None,'raw_value':None,'aliases':[]}
        receipt['declarative_profile_witness']=run_capability_declarative_profile_witness(
            operator,[],receipt['join_witness'],receipt['output_path'],closure_status,execution_status
        )
        receipt['result_checks']=[
            {'check_id':item['object_id']+'::STATUS_GATE','pass':True,'actual':execution_status},
            {'check_id':item['object_id']+'::DECLARATIVE_PROFILE_WITNESS','pass':receipt['declarative_profile_witness']['witness_status']=='STATUS_GATE_NO_DECLARATIVE_PROFILE_OUTPUT','actual':receipt['declarative_profile_witness']['declarative_profile_id']},
            {'check_id':item['object_id']+'::NO_FORMAL_FACT','pass':True,'actual':0},
        ]
    else:
        join_witness,join_rows=capability_join_witness(item,payload_cache)
        receipt['join_witness']=join_witness
        joined_bindings={
            (alias['input_id'],int(alias['selected_object_index']))
            for match in join_witness.get('matches') or [] if match['match_scope']=='PAIRWISE_DECLARED_KEY_WITNESS_ONLY'
            for alias in match['aliases']
        }
        witnessed_join_fields={
            (alias['input_id'],int(alias['selected_object_index']),alias['selected_row_sha256'],alias['source_field'])
            for match in join_witness.get('matches') or [] for alias in match['aliases']
        }
        mapped_usage_counts=Counter()
        for binding in item['source_bindings']:
            key=(binding['input_id'],int(binding['selected_object_index']))
            indexed=join_rows.get(key) or payload_cache[key][0]
            raw_values={}; normalized_values={}; field_checks=[]; applied_field_rules=[]
            for rule in binding['field_rules']:
                field=rule['source_field']; value=indexed['row'].get(field)
                raw_values[field]=value
                normalized,passed,missing=capability_apply_field_rule(
                    rule,value,(key[0],key[1],indexed['row_sha256'],field) in witnessed_join_fields
                )
                normalized_values[field]=normalized
                receipt['explicit_unknown_field_count']+=int(missing)
                mapped_usage_counts[rule['usage']]+=1
                field_checks.append({'source_field':field,'check':rule['result_check'],'pass':passed})
                applied_field_rules.append({
                    'source_field':field,'usage':rule['usage'],'transform':rule['transform'],
                    'missing_policy':rule['missing_policy'],'raw_output_path':rule['raw_output_path'],
                    'normalized_output_path':rule['normalized_output_path'],
                })
            receipt['source_witnesses'].append({
                'input_id':key[0],'selected_object_index':key[1],
                'source_locator':indexed['source_locator'],'selected_row_sha256':indexed['row_sha256'],
                'relation_participation':('MATCHED_IN_DECLARED_KEY_WITNESS' if key in joined_bindings else 'INDEPENDENT_CONTEXT_OR_PROJECTION_SOURCE'),
                'raw_value':raw_values,'normalized_value':normalized_values,
                'field_checks':field_checks,'applied_field_rules':applied_field_rules,
            })
        profile_pass=bool(receipt['source_witnesses']) and all(
            check['pass'] for witness in receipt['source_witnesses'] for check in witness['field_checks']
        )
        allowed_join_status=(
            join_witness['status']=='EXACT_DECLARED_KEY_PAIR_WITNESSES_ON_LOCKED_MIRRORS'
            or (
                implementation['result_profile']=='COVERAGE'
                and join_witness['status']=='COVERAGE_KEY_WITNESS_ONLY_SOURCES_REMAIN_UNJOINED'
            )
        )
        if item['assembly_spec']['join']['required']:
            profile_pass=profile_pass and allowed_join_status
        receipt['candidate_witness_output_count']=len(receipt['source_witnesses'])
        receipt['all_bindings_connected']=len(join_witness.get('unjoined_bindings') or [])==0
        receipt['declarative_profile_witness']=run_capability_declarative_profile_witness(
            operator,receipt['source_witnesses'],join_witness,receipt['output_path'],closure_status,execution_status
        )
        receipt['result_checks']=[
            {'check_id':item['object_id']+'::ALL_BOUND_SOURCES_WITNESSED','pass':len(receipt['source_witnesses'])==len(item['source_bindings']),'actual':len(receipt['source_witnesses'])},
            {'check_id':item['object_id']+'::ALL_FIELD_RULES_APPLIED','pass':profile_pass,'actual':sum(mapped_usage_counts.values())},
            {'check_id':item['object_id']+'::DECLARED_JOIN_BEHAVIOR','pass':(not item['assembly_spec']['join']['required'] or allowed_join_status),'actual':join_witness['status']},
            {'check_id':item['object_id']+'::DECLARATIVE_PROFILE_WITNESS','pass':receipt['declarative_profile_witness']['witness_status']=='BOUNDED_DECLARATIVE_PROFILE_WITNESS','actual':receipt['declarative_profile_witness']['declarative_profile_id']},
            {'check_id':item['object_id']+'::OUTPUT_PATH','pass':receipt['output_path']==item['output_location'],'actual':receipt['output_path']},
            {'check_id':item['object_id']+'::NO_FORMAL_FACT','pass':receipt['formal_fact_output_count']==0,'actual':0},
        ]
    if not all(check['pass'] for check in receipt['result_checks']):
        raise RuntimeError('CAPABILITY_RESULT_CHECK_FAILED:'+item['object_id'])
    receipt['receipt_sha256']=hashlib.sha256(canonical(receipt).encode('utf-8')).hexdigest()
    return receipt

def execute_capability_bounded_witnesses(capability_records,receipts,require_expected=True):
    receipt_map={(item['input_id'],int(item['selected_object_index'])):item for item in receipts}
    required_keys={
        (binding['input_id'],int(binding['selected_object_index']))
        for item in capability_records if item.get('closure_status')==RUNNABLE_CAPABILITY_STATUS
        for binding in item.get('source_bindings') or []
    }
    payload_cache=capability_payload_cache(receipts,required_keys)
    execution_receipts=[]
    for item in sorted(capability_records,key=lambda row:row['object_id']):
        execution=build_capability_witness_receipt(item,receipt_map,payload_cache)
        expected=(item.get('bounded_execution_contract') or {}).get('expected_receipt_sha256')
        if require_expected and execution['receipt_sha256']!=expected:
            raise RuntimeError('CAPABILITY_WITNESS_RECEIPT_MISMATCH:'+item['object_id'])
        execution_receipts.append(execution)
    status_counts=Counter(item['execution_status'] for item in execution_receipts)
    operator_ids={item['operator_id'] for item in execution_receipts}
    overall_sha=hashlib.sha256(('\n'.join(canonical(item) for item in execution_receipts)+'\n').encode('utf-8')).hexdigest()
    return execution_receipts,{
        'receipt_count':len(execution_receipts),'operator_count':len(operator_ids),
        'operator_ids_exact':operator_ids==set(SUPPORTED_OPERATOR_REGISTRY),
        'execution_status_counts':dict(sorted(status_counts.items())),
        'all_result_checks_pass':all(all(check['pass'] for check in item['result_checks']) for item in execution_receipts),
        'formal_fact_output_count':sum(item['formal_fact_output_count'] for item in execution_receipts),
        'candidate_witness_output_count':sum(item['candidate_witness_output_count'] for item in execution_receipts),
        'declarative_profile_witness_count':sum(item.get('declarative_profile_witness') is not None for item in execution_receipts),
        'runnable_declarative_profile_witness_count':sum(item.get('declarative_profile_witness',{}).get('witness_status')=='BOUNDED_DECLARATIVE_PROFILE_WITNESS' for item in execution_receipts),
        'status_gate_declarative_profile_witness_count':sum(item.get('declarative_profile_witness',{}).get('witness_status')=='STATUS_GATE_NO_DECLARATIVE_PROFILE_OUTPUT' for item in execution_receipts),
        'all_business_operator_semantics_not_executed':all(item.get('declarative_profile_witness',{}).get('business_operator_semantics_executed') is False for item in execution_receipts),
        'explicit_unknown_field_count':sum(item.get('explicit_unknown_field_count',0) for item in execution_receipts),
        'execution_receipts_sha256':overall_sha,
        'scope_statement':'LOCKED_02_MIRRORS_BOUNDED_WITNESS_ONLY_NOT_FULL_136_BUILD_OR_FORMAL_ADOPTION',
    }

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
        fields=set()
        with open(mirror,encoding='utf-8') as handle:
            for line in handle:
                if line.strip():
                    value=json.loads(line)
                    if not isinstance(value,dict):
                        raise RuntimeError('CAPABILITY_RECEIPT_JSONL_RECORD_NOT_OBJECT:'+str(mirror))
                    fields.update(value)
        return fields
    if mirror.suffix=='.json':
        value=json.load(open(mirror,encoding='utf-8'))
        return set(value) if isinstance(value,dict) else set()
    raise RuntimeError('CAPABILITY_RECEIPT_MIRROR_TYPE_UNSUPPORTED:'+mirror.suffix)

def validate_capability_specs(capability_records,adoption_records,schema,receipts):
    if len(capability_records)!=94: raise RuntimeError('CAPABILITY_SPEC_COUNT_MISMATCH')
    if len(SUPPORTED_OPERATOR_REGISTRY)!=33 or set(SUPPORTED_OPERATOR_REGISTRY)!={
        'ACTIVE_AND_COPY_SCOPE_PARTITION','ADJACENT_REVERSE_POSITION_OBJECTIVE_LINKAGE','ANALYSIS_STRATEGY_AND_COUNTERFACTUAL_BOUNDARY',
        'CANONICAL_CASH_EVENT_DEDUPLICATION_AND_TRANSFER_PAIRING','CONDITION_TO_ORDER_FILL_AND_CYCLE_RELATION_GRAPH',
        'FACT_USER_STATEMENT_INTERPRETATION_AND_STATUS_LAYERING','FEE_AND_NET_RESULT_COMPONENT_SEPARATION',
        'FILL_PRICE_AND_WEIGHTED_AVERAGE_TRANSITION','FILL_TO_ORDER_AND_CYCLE_LINKAGE','FUTURE_SCHEMA_AND_FORMAT_BOUNDARY',
        'IDENTIFIER_MAPPING_WITHOUT_ID_REPLACEMENT','IDENTITY_RESOLUTION_WITH_SOURCE_BOUNDARIES',
        'MARGIN_AND_RISK_FIELDS_SEPARATED_NO_INFERENCE_FOR_MISSING_VALUES','MARKET_DATA_IDENTITY_WINDOW_AND_COVERAGE',
        'MFE_MAE_BY_CYCLE_OR_POSITION_STAGE','NON_OBJECTIVE_USER_REASON_BOUNDARY','OBJECTIVE_ACTION_CLASSIFICATION_WITH_EVIDENCE',
        'ORDER_AND_CONDITION_LIFECYCLE_LINKAGE','POSITION_QUANTITY_STATE_TRANSITION','POSITION_ZERO_TO_NONZERO_TO_ZERO_CYCLE_GROUPING',
        'REALIZED_PNL_BY_FILL_AND_CYCLE','REFERENTIAL_AND_QUANTITY_INTEGRITY_CHECKS','SCREENSHOT_CONDITION_AND_CYCLE_LINEAGE_BRIDGE',
        'SIDE_POSITION_SIDE_AND_POSITION_EFFECT_SEPARATION','STABLE_ID_AND_SOURCE_NAMESPACE_PRESERVATION',
        'STOP_LOSS_LIFECYCLE_WITH_UNKNOWN_RELATION_PRESERVATION','TAKE_PROFIT_LIFECYCLE_WITH_UNKNOWN_RELATION_PRESERVATION',
        'TIMELINE_UNION_PRESERVE_EQUAL_TIME_PARALLEL_EVENTS','TIME_BOUNDED_EQUITY_ANCHORS_AND_UNKNOWN_GAPS',
        'TIME_NORMALIZATION_WITH_ORIGINAL_VALUE_AND_PRECISION','USER_INTERFACE_PRODUCT_BOUNDARY',
        'USER_STAGE_AGGREGATION_ACROSS_POSITION_PRICE_AND_MFE_MAE_COMPONENTS','VERSION_CORRECTION_AND_SOURCE_IDENTITY_LINEAGE',
    }:
        raise RuntimeError('CAPABILITY_OPERATOR_REGISTRY_SET_INVALID')
    if any(DECLARATIVE_PROFILE_REGISTRY.get(item['declarative_profile_id'])!=item['result_profile'] for item in SUPPORTED_OPERATOR_REGISTRY.values()):
        raise RuntimeError('CAPABILITY_DECLARATIVE_PROFILE_NOT_REGISTERED')
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
    status_counts=Counter(); binding_count=0; field_binding_count=0; unique_source_fields=set(); seen_operators=set()
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
                declared_fields=set(binding['source_fields'])
                actual_fields=receipt_schema_fields(receipt)
                missing=actual_fields-declared_fields
                extra=declared_fields-actual_fields
                if missing or extra:
                    raise RuntimeError(
                        'CAPABILITY_SOURCE_FIELD_SCOPE_MISMATCH:'+item['object_id']
                        +':missing='+','.join(sorted(missing))+':extra='+','.join(sorted(extra))
                    )
                binding_scope[(binding['input_id'],int(selected_index))]=set(binding['source_fields'])
                binding_count+=1; field_binding_count+=len(binding['source_fields']); unique_source_fields.update(binding['source_fields'])
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
        for key_family in join.get('keys') or []:
            if str(key_family.get('canonical_key') or '').lower() in FORBIDDEN_CROSS_SOURCE_LOCATOR_FIELDS:
                raise RuntimeError('CAPABILITY_ROW_LOCATOR_DECLARED_AS_JOIN_KEY:'+item['object_id'])
            if any(str(alias.get('source_field') or '').lower() in FORBIDDEN_CROSS_SOURCE_LOCATOR_FIELDS for alias in key_family.get('verified_source_aliases') or []):
                raise RuntimeError('CAPABILITY_ROW_LOCATOR_ALIAS_DECLARED_AS_JOIN_KEY:'+item['object_id'])
        if not join.get('operator') or join['operator']!=contract.get('operator'):
            raise RuntimeError('CAPABILITY_JOIN_OPERATOR_MISMATCH:'+item['object_id'])
        operator=join['operator']; implementation=SUPPORTED_OPERATOR_REGISTRY.get(operator)
        if implementation is None or DECLARATIVE_PROFILE_REGISTRY.get(implementation.get('declarative_profile_id'))!=implementation.get('result_profile'):
            raise RuntimeError('CAPABILITY_OPERATOR_ID_NOT_REGISTERED:'+operator)
        seen_operators.add(operator)
        operator_contract=item.get('operator_contract')
        expected_operator_contract={
            'operator_id':operator,'operator_version':implementation['version'],
            'declarative_profile_id':implementation['declarative_profile_id'],'result_profile':implementation['result_profile'],
            'registry_version':OPERATOR_REGISTRY_VERSION,'registry_sha256':operator_registry_sha256(),
            'business_operator_semantics_executed':False,
            'contract_scope':'DECLARATIVE_OPERATOR_ID_AND_PROFILE; BUSINESS_SEMANTICS_NOT_EXECUTED_IN_FIRST_PACKAGE',
        }
        if operator_contract!=expected_operator_contract:
            raise RuntimeError('CAPABILITY_OPERATOR_CONTRACT_MISMATCH:'+item['object_id'])
        if join.get('missing_join_key_behavior')!=contract.get('missing_join_key_behavior'):
            raise RuntimeError('CAPABILITY_MISSING_JOIN_KEY_BEHAVIOR_MISMATCH:'+item['object_id'])
        if join.get('missing_join_key_behavior')!=required_missing_join_key_behavior:
            raise RuntimeError('CAPABILITY_MISSING_JOIN_KEY_BEHAVIOR_INVALID:'+item['object_id'])
        if join.get('direction')!=contract.get('relation_direction') or join.get('cardinality')!=contract.get('cardinality'):
            raise RuntimeError('CAPABILITY_JOIN_CONTRACT_MISMATCH:'+item['object_id'])
        if canonical(join.get('keys') or [])!=canonical(contract.get('join_key_families') or []):
            raise RuntimeError('CAPABILITY_JOIN_KEYS_CONTRACT_MISMATCH:'+item['object_id'])
        forbidden_locator_keys=FORBIDDEN_CROSS_SOURCE_LOCATOR_FIELDS
        if any(str(family.get('canonical_key') or '').lower() in forbidden_locator_keys for family in join.get('keys') or []):
            raise RuntimeError('CAPABILITY_ROW_LOCATOR_DECLARED_AS_JOIN_KEY:'+item['object_id'])
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
            rules=detailed.get('field_rules')
            if not isinstance(rules,list) or len(rules)!=len(detailed.get('source_fields_or_pointers') or []):
                raise RuntimeError('CAPABILITY_FIELD_RULE_COUNT_MISMATCH:'+item['object_id']+':'+str(key))
            if [rule.get('source_field') for rule in rules]!=(detailed.get('source_fields_or_pointers') or []):
                raise RuntimeError('CAPABILITY_FIELD_RULE_ORDER_OR_SCOPE_MISMATCH:'+item['object_id']+':'+str(key))
            if len({rule.get('source_field') for rule in rules})!=len(rules):
                raise RuntimeError('CAPABILITY_FIELD_RULE_DUPLICATE:'+item['object_id']+':'+str(key))
            alias_fields={
                value.get('source_field') for value in detailed.get('join_keys') or []
                if str(value.get('canonical_key') or '').lower() not in FORBIDDEN_CROSS_SOURCE_LOCATOR_FIELDS
            }
            for rule in rules:
                field=rule['source_field']
                binding_key=key[0]+'#'+str(key[1])
                expected_raw=output['path']+'.source_witnesses['+canonical(binding_key)+'].raw_value['+canonical(field)+']'
                expected_normalized=output['path']+'.source_witnesses['+canonical(binding_key)+'].normalized_value['+canonical(field)+']'
                if rule.get('raw_output_path')!=expected_raw or rule.get('normalized_output_path')!=expected_normalized:
                    raise RuntimeError('CAPABILITY_FIELD_OUTPUT_MAPPING_INVALID:'+item['object_id']+':'+field)
                expected_usage,expected_transform,expected_missing=capability_field_semantics(field,field in alias_fields)
                if rule.get('usage')!=expected_usage:
                    raise RuntimeError('CAPABILITY_FIELD_USAGE_SEMANTIC_MISMATCH:'+item['object_id']+':'+field)
                if rule.get('transform') not in SUPPORTED_CAPABILITY_TRANSFORMS:
                    raise RuntimeError('CAPABILITY_TRANSFORM_NOT_IMPLEMENTED:'+str(rule.get('transform')))
                if rule.get('transform')!=expected_transform:
                    raise RuntimeError('CAPABILITY_FIELD_TRANSFORM_SEMANTIC_MISMATCH:'+item['object_id']+':'+field)
                if rule.get('missing_policy')!=expected_missing or rule.get('result_check')!=FIELD_RESULT_CHECK:
                    raise RuntimeError('CAPABILITY_FIELD_RULE_POLICY_INVALID:'+item['object_id']+':'+field)
            assembly_binding=next(
                binding for binding in bindings
                if binding['input_id']==key[0] and int(binding['selected_object_indexes'][0])==key[1]
            )
            if assembly_binding.get('field_rules')!=rules:
                raise RuntimeError('CAPABILITY_FIELD_RULE_MIRROR_MISMATCH:'+item['object_id']+':'+str(key))
        if item.get('operator_parameters')!=capability_operator_parameters(item):
            raise RuntimeError('CAPABILITY_OPERATOR_PARAMETERS_MISMATCH:'+item['object_id'])
        if join['required']:
            if not join.get('keys') or not join.get('direction') or not join.get('cardinality'):
                raise RuntimeError('CAPABILITY_JOIN_DETAIL_MISSING:'+item['object_id'])
        elif not join.get('reason'):
            raise RuntimeError('CAPABILITY_JOIN_NA_REASON_MISSING:'+item['object_id'])
        for key_family in join.get('keys') or []:
            if not key_family.get('canonical_key') or not key_family.get('verified_source_aliases'):
                raise RuntimeError('CAPABILITY_JOIN_KEY_FAMILY_INVALID:'+item['object_id'])
            for alias in key_family['verified_source_aliases']:
                if str(alias.get('source_field') or '').lower() in forbidden_locator_keys:
                    raise RuntimeError('CAPABILITY_ROW_LOCATOR_ALIAS_DECLARED_AS_JOIN_KEY:'+item['object_id'])
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
        execution_plan=item.get('execution_plan')
        expected_plan={
            'read_policy':'02_LOCKED_READ_ONLY_MIRRORS_ONLY',
            'source_row_selection':'CANONICAL_ROW_SHA256_THEN_SOURCE_LOCATOR',
            'max_witness_rows_per_binding':1,
            'declarative_profile_id':implementation['declarative_profile_id'],
            'business_operator_semantics_execution':'NOT_AUTHORIZED_NOT_RUN',
            'join_policy':'EXACT_DECLARED_KEY_VALUE_ONLY; UNJOINED_BINDINGS_REMAIN_SEPARATE',
            'output_policy':'BOUNDED_WITNESS_RECEIPT_ONLY_NO_FORMAL_FACT',
        }
        if execution_plan!=expected_plan:
            raise RuntimeError('CAPABILITY_EXECUTION_PLAN_MISMATCH:'+item['object_id'])
        result_contract=item.get('capability_result_contract')
        expected_execution_status=capability_expected_execution_status(item['closure_status'])
        if not isinstance(result_contract,dict):
            raise RuntimeError('CAPABILITY_RESULT_CONTRACT_MISSING:'+item['object_id'])
        expected_result_contract={
            'expected_execution_status':expected_execution_status,
            'expected_output_path':output['path'],
            'expected_bound_source_count':len(detailed_bindings),
            'expected_formal_fact_output_count':0,
            'required_checks':[
                'ALL_BOUND_SOURCES_WITNESSED_OR_STATUS_GATE_APPLIED','ALL_FIELD_RULES_APPLIED_OR_STATUS_GATE_APPLIED',
                'DECLARED_JOIN_BEHAVIOR_CHECKED','DECLARATIVE_PROFILE_WITNESS_EXECUTED_OR_STATUS_GATE_APPLIED',
                'OUTPUT_PATH_EXACT','NO_FORMAL_FACT_EMITTED',
            ],
        }
        if result_contract!=expected_result_contract:
            raise RuntimeError('CAPABILITY_RESULT_CONTRACT_MISMATCH:'+item['object_id'])
        bounded_contract=item.get('bounded_execution_contract')
        if not isinstance(bounded_contract,dict) or bounded_contract.get('mirror_authority')!='02_输入身份_选择器与装载回执候选.jsonl':
            raise RuntimeError('CAPABILITY_BOUNDED_EXECUTION_CONTRACT_MISSING:'+item['object_id'])
        if bounded_contract.get('expected_execution_status')!=expected_execution_status:
            raise RuntimeError('CAPABILITY_BOUNDED_EXECUTION_STATUS_MISMATCH:'+item['object_id'])
        if not re.fullmatch(r'[0-9a-f]{64}',str(bounded_contract.get('expected_receipt_sha256') or '')):
            raise RuntimeError('CAPABILITY_BOUNDED_RECEIPT_HASH_INVALID:'+item['object_id'])
        sample_status=spec.get('bounded_sample_status')
        if sample_status not in {
            'BOUNDED_REAL_MIRROR_FIELD_AND_JOIN_WITNESS_PASSED','UNRESOLVED_NO_CONFIRMED_FACT_EMITTED',
            'BOUNDARY_NO_OBJECTIVE_FACT_EMITTED','PENDING_USER_ACCEPTANCE_NO_PRODUCTION_OUTPUT',
        }:
            raise RuntimeError('CAPABILITY_SAMPLE_STATUS_INVALID:'+item['object_id'])
        if sample_status!=expected_execution_status:
            raise RuntimeError('CAPABILITY_SAMPLE_STATUS_RESULT_MISMATCH:'+item['object_id'])
        status_counts[sample_status]+=1
    if seen_operators!=set(SUPPORTED_OPERATOR_REGISTRY):
        raise RuntimeError('CAPABILITY_OPERATOR_REGISTRY_COVERAGE_MISMATCH')
    return {
        'capability_count':94,
        'source_binding_applications_checked':binding_count,
        'source_fields_checked':field_binding_count,
        'unique_source_fields_checked':len(unique_source_fields),
        'bounded_sample_status_counts':dict(sorted(status_counts.items())),
        'operator_registry_count':len(seen_operators),
        'operator_registry_sha256':operator_registry_sha256(),
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
        if not relation.get('source_event_id'):
            raise RuntimeError('FACT_BASE_RELATION_SOURCE_EVENT_MISSING:'+record['fact_id'])
        if fact_records[source_id].get('source_event_id')!=relation['source_event_id']:
            raise RuntimeError('FACT_BASE_EVENT_SOURCE_MISMATCH:'+record['fact_id'])
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
        'all_relation_source_events_match_source_facts':True,
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

def technical_chunk_rows(records,limit=EXCEL_SAFE_CELL_LIMIT_UTF16):
    rows=[]
    for record in records:
        complete=canonical(record)
        chunks=split_utf16_safe(complete,limit)
        complete_sha=hashlib.sha256(complete.encode('utf-8')).hexdigest()
        for index,chunk in enumerate(chunks,1):
            rows.append({
                '顺序':record['stable_display_sequence'],
                '对象入口':record['navigation_object_id'],
                '记录类型':record['record_type'],
                '事实ID':record['fact_id'],
                '第几段':index,
                '一共几段':len(chunks),
                '本段UTF-16长度':utf16_units(chunk),
                '完整原文UTF-16长度':utf16_units(complete),
                '完整原文SHA-256':complete_sha,
                '技术原文分段':chunk,
            })
    validate_technical_chunk_rows(rows,records,limit)
    return rows

def validate_technical_chunk_rows(rows,records,limit=EXCEL_SAFE_CELL_LIMIT_UTF16):
    if not isinstance(limit,int) or limit<=0 or limit>EXCEL_DOCUMENTED_CELL_LIMIT_UTF16:
        raise RuntimeError('EXCEL_TECHNICAL_CHUNK_LIMIT_INVALID')
    expected_by_id={record['fact_id']:record for record in records}
    if len(expected_by_id)!=len(records):
        raise RuntimeError('EXCEL_TECHNICAL_SOURCE_FACT_ID_DUPLICATE')
    grouped=defaultdict(list)
    physical_order=[]
    for row in rows:
        fact_id=row.get('事实ID')
        if fact_id not in expected_by_id:
            raise RuntimeError('EXCEL_TECHNICAL_CHUNK_FACT_ID_UNKNOWN:'+str(fact_id))
        if not physical_order or physical_order[-1]!=fact_id:
            physical_order.append(fact_id)
        grouped[fact_id].append(row)
    expected_order=[record['fact_id'] for record in records]
    if physical_order!=expected_order or set(grouped)!=set(expected_by_id):
        raise RuntimeError('EXCEL_TECHNICAL_CHUNK_RECORD_ORDER_OR_COVERAGE_MISMATCH')
    for fact_id,record in expected_by_id.items():
        group=grouped[fact_id]; total=len(group)
        if [int(row.get('第几段',0)) for row in group]!=list(range(1,total+1)):
            raise RuntimeError('EXCEL_TECHNICAL_CHUNK_INDEX_GAP:'+fact_id)
        if any(int(row.get('一共几段',0))!=total for row in group):
            raise RuntimeError('EXCEL_TECHNICAL_CHUNK_TOTAL_MISMATCH:'+fact_id)
        complete=canonical(record); complete_units=utf16_units(complete)
        complete_sha=hashlib.sha256(complete.encode('utf-8')).hexdigest()
        if any(
            int(row.get('顺序',0))!=int(record['stable_display_sequence'])
            or row.get('对象入口')!=record['navigation_object_id']
            or row.get('记录类型')!=record['record_type']
            or int(row.get('本段UTF-16长度',-1))!=utf16_units(row.get('技术原文分段',''))
            or int(row.get('完整原文UTF-16长度',-1))!=complete_units
            or row.get('完整原文SHA-256')!=complete_sha
            or utf16_units(row.get('技术原文分段',''))>limit
            for row in group
        ):
            raise RuntimeError('EXCEL_TECHNICAL_CHUNK_METADATA_MISMATCH:'+fact_id)
        reassembled=''.join(row['技术原文分段'] for row in group)
        if reassembled!=complete or hashlib.sha256(reassembled.encode('utf-8')).hexdigest()!=complete_sha:
            raise RuntimeError('EXCEL_TECHNICAL_CHUNK_REASSEMBLY_MISMATCH:'+fact_id)
        if json.loads(reassembled)!=record:
            raise RuntimeError('EXCEL_TECHNICAL_CHUNK_JSON_REASSEMBLY_MISMATCH:'+fact_id)
    chunk_counts=Counter(len(group) for group in grouped.values())
    multi=[{
        'fact_id':fact_id,
        'complete_utf16_units':int(group[0]['完整原文UTF-16长度']),
        'complete_utf8_sha256':group[0]['完整原文SHA-256'],
        'chunk_count':len(group),
        'chunk_utf16_units':[int(row['本段UTF-16长度']) for row in group],
    } for fact_id,group in grouped.items() if len(group)>1]
    return {
        'source_record_count':len(records),
        'chunk_row_count':len(rows),
        'single_chunk_record_count':chunk_counts.get(1,0),
        'multi_chunk_record_count':sum(count for size,count in chunk_counts.items() if size>1),
        'extra_chunk_row_count':len(rows)-len(records),
        'maximum_source_record_utf16_units':max(utf16_units(canonical(record)) for record in records),
        'maximum_chunk_utf16_units':max(utf16_units(row['技术原文分段']) for row in rows),
        'reassembled_record_count':len(grouped),
        'multi_chunk_records':multi,
    }

def build_workbook_payload(records, sample_manifest, receipts, contract_id,technical_cell_limit=EXCEL_SAFE_CELL_LIMIT_UTF16):
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
    technical=technical_chunk_rows(records,technical_cell_limit)
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

def validate_workbook_payload_cell_lengths(payload,workbook_config):
    limit=int(workbook_config['technical_text_chunking']['safe_cell_limit_utf16_units'])
    if limit<=0 or limit>EXCEL_DOCUMENTED_CELL_LIMIT_UTF16:
        raise RuntimeError('EXCEL_TECHNICAL_CHUNK_LIMIT_INVALID')
    maximum=0
    for sheet in workbook_display_content(payload,workbook_config):
        for row in [sheet['headers'],*sheet['rows']]:
            for value in row:
                if isinstance(value,str):
                    units=utf16_units(value); maximum=max(maximum,units)
                    if units>limit:
                        raise RuntimeError('WORKBOOK_PAYLOAD_CELL_UTF16_LIMIT_EXCEEDED:'+sheet['sheet_name'])
    return {'maximum_payload_cell_utf16_units':maximum,'cells_over_safe_limit':0}

def verify_workbook_technical_chunks(workbook_path,records,workbook_config):
    limit=int(workbook_config['technical_text_chunking']['safe_cell_limit_utf16_units'])
    maximum=0
    for sheet_name in workbook_config['sheet_order']:
        for cell in xlsx_sheet_cells(workbook_path,sheet_name).values():
            value=cell['value']
            if isinstance(value,str):
                units=utf16_units(value); maximum=max(maximum,units)
                if units>limit:
                    raise RuntimeError('WORKBOOK_OOXML_CELL_UTF16_LIMIT_EXCEEDED:'+sheet_name)
    cells=xlsx_sheet_cells(workbook_path,'技术原文')
    headers=[]
    for column in range(1,len(workbook_config['preferred_columns']['技术原文'])+1):
        headers.append(cells.get(f'{col_label(column)}3',{}).get('value',''))
    if headers!=workbook_config['preferred_columns']['技术原文']:
        raise RuntimeError('WORKBOOK_TECHNICAL_CHUNK_HEADERS_MISMATCH')
    row_numbers=[int(re.search(r'\d+',ref).group()) for ref in cells if int(re.search(r'\d+',ref).group())>=4]
    actual=[]
    for row_number in range(4,max(row_numbers,default=3)+1):
        values=[cells.get(f'{col_label(column)}{row_number}',{}).get('value','') for column in range(1,len(headers)+1)]
        if not any(value!='' for value in values): continue
        row=dict(zip(headers,values))
        for field in ('顺序','第几段','一共几段','本段UTF-16长度','完整原文UTF-16长度'):
            try: row[field]=int(float(str(row[field])))
            except (TypeError,ValueError): raise RuntimeError('WORKBOOK_TECHNICAL_CHUNK_INTEGER_INVALID:'+field)
        actual.append(row)
    summary=validate_technical_chunk_rows(actual,records,limit)
    expected=technical_chunk_rows(records,limit)
    if actual!=expected:
        raise RuntimeError('WORKBOOK_TECHNICAL_CHUNK_OOXML_CONTENT_MISMATCH')
    return {
        **summary,
        'maximum_actual_cell_utf16_units':maximum,
        'cells_over_safe_limit':0,
        'technical_chunk_indices_contiguous':True,
        'technical_chunk_metadata_consistent':True,
        'technical_reassembled_text_exact':True,
        'technical_reassembled_utf8_sha256_exact':True,
        'raw_ooxml_cell_length_scan_passed':True,
    }

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
const safeCellUtf16Limit=cfg.technical_text_chunking.safe_cell_limit_utf16_units;
if (!Number.isInteger(safeCellUtf16Limit) || safeCellUtf16Limit<=0 || safeCellUtf16Limit>32767) throw new Error("技术原文分段阈值无效");

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
  if (["完整记录JSON","技术原文分段"].includes(header)) return 90;
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
  for (const row of matrix) for (const value of row) {
    if (typeof value==="string" && value.length>safeCellUtf16Limit) throw new Error(`工作表 ${name} 有单元格超过UTF-16安全阈值`);
  }
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
let maximumActualCellUtf16Units=0;
let cellsOverSafeLimit=0;
for (const name of sheetOrder) {
  const sheet=imported.worksheets.getItem(name);
  const {headers,rows}=tableRows(sheet);
  const expectedHeaders=preferredColumns[name];
  const expectedRows=payload[name].map(row=>expectedHeaders.map(header=>displayValue(header,row[header])));
  const usedValues=sheet.getUsedRange().values.flat();
  formulaErrorCount+=usedValues.filter(value=>errorTokens.has(String(value))).length;
  for (const value of usedValues) {
    if (typeof value!=="string") continue;
    maximumActualCellUtf16Units=Math.max(maximumActualCellUtf16Units,value.length);
    if (value.length>safeCellUtf16Limit) cellsOverSafeLimit+=1;
  }
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
    && formulaErrorCount===0 && cellsOverSafeLimit===0,
  sheet_order_exact:JSON.stringify(actualSheets)===JSON.stringify(sheetOrder),
  sheet_checks:sheetChecks,
  formula_error_count:formulaErrorCount,
  maximum_actual_cell_utf16_units:maximumActualCellUtf16Units,
  cells_over_safe_limit:cellsOverSafeLimit,
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
    workbook_config=view['user_workbook']
    technical_limit=int(workbook_config['technical_text_chunking']['safe_cell_limit_utf16_units'])
    payload=build_workbook_payload(records,sample_manifest,receipts,config['contract_id'],technical_limit)
    for item in payload['从这里开始']:
        if item['项目']=='事实底座SHA-256':
            item['白话说明']=sha_file(fact_path); item['当前状态']='固定来源身份'
    payload_length_check=validate_workbook_payload_cell_lengths(payload,workbook_config)
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
        raw_workbook_check=verify_workbook_technical_chunks(workbook_temp,records,workbook_config)
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
            'artifact_tool_reopen_and_reconciliation_passed':workbook_check['all_pass'],
            **payload_length_check,
            **raw_workbook_check,
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

def verify_capabilities(mapping_path,adoption_path,schema_path,receipts_path,output_path=None):
    mapping=read_jsonl(mapping_path); capabilities=[item for item in mapping if item.get('record_type')=='CAPABILITY_CLOSURE_CANDIDATE']
    adoption=read_jsonl(adoption_path); schema=json.load(open(schema_path,encoding='utf-8')); receipts=read_jsonl(receipts_path)
    specification=validate_capability_specs(capabilities,adoption,schema,receipts)
    execution_receipts,execution=execute_capability_bounded_witnesses(capabilities,receipts)
    if output_path:
        output=Path(output_path)
        if output.exists(): raise RuntimeError('CAPABILITY_RECEIPT_OUTPUT_ALREADY_EXISTS:'+str(output))
        jsonl_write(output,execution_receipts)
        execution['written_receipt_file']={'path':str(output),'bytes':output.stat().st_size,'sha256':sha_file(output)}
    result={'all_pass':True,'specification':specification,'bounded_execution':execution}
    print(canonical(result)); return result

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
        elif kind=='capability_field_semantics_fixture':
            actual={field:{
                'usage':capability_field_semantics(field,False)[0],
                'transform':capability_field_semantics(field,False)[1],
                'missing_policy':capability_field_semantics(field,False)[2],
            } for field in inp['fields']}
        elif kind=='capability_receipt_schema_union_exact':
            receipts=read_jsonl((base/inp['receipt_file']).resolve())
            receipt=next(
                item for item in receipts
                if item['input_id']==inp['input_id']
                and int(item['selected_object_index'])==int(inp['selected_object_index'])
            )
            mirror=Path(receipt['mirror_path'])
            rows=read_jsonl(mirror)
            actual={
                'record_count':len(rows),
                'schema_variant_count':len({tuple(sorted(row)) for row in rows}),
                'field_count':len(receipt_schema_fields(receipt)),
                'fields':sorted(receipt_schema_fields(receipt)),
            }
        elif kind=='capability_config_expected_receipts_match_summary':
            mapping=read_jsonl((base/inp['mapping_file']).resolve())
            adoption=read_jsonl((base/inp['adoption_file']).resolve())
            schema=json.load(open((base/inp['schema_file']).resolve(),encoding='utf-8'))
            receipts=read_jsonl((base/inp['receipt_file']).resolve())
            config=json.load(open((base/inp['config_file']).resolve(),encoding='utf-8'))
            capabilities=[item for item in mapping if item.get('record_type')=='CAPABILITY_CLOSURE_CANDIDATE']
            validate_capability_specs(capabilities,adoption,schema,receipts)
            _,summary=execute_capability_bounded_witnesses(capabilities,receipts)
            locked=config['capability_field_mapping_join_and_declarative_profile_witness']['expected_receipts']
            actual=all(key in summary and summary[key]==value for key,value in locked.items())
        elif kind=='capability_transform_fixture':
            actual=capability_transform(inp['transform'],inp['value'])
        elif kind=='capability_transform_rejected':
            try: capability_transform(inp['transform'],inp['value']); actual=False
            except RuntimeError as error: actual=str(error).startswith(inp['expected_error_prefix'])
        elif kind in {
            'capability_operator_registry_exact','capability_actual_bounded_witnesses','capability_bounded_replay_deterministic',
            'capability_unsupported_operator_rejected','capability_operator_contract_mutation_rejected',
            'capability_operator_parameters_mutation_rejected',
            'capability_unknown_transform_rejected','capability_field_rule_missing_rejected',
            'capability_row_locator_never_used_as_join','capability_row_alias_locator_rejected',
            'capability_unjoined_bindings_preserved',
            'capability_status_gates_exact','capability_witness_hash_mutation_rejected',
        }:
            mapping=read_jsonl((base/inp['mapping_file']).resolve()); adoption=read_jsonl((base/inp['adoption_file']).resolve())
            schema=json.load(open((base/inp['schema_file']).resolve(),encoding='utf-8')); receipts=read_jsonl((base/inp['receipt_file']).resolve())
            capabilities=[item for item in mapping if item.get('record_type')=='CAPABILITY_CLOSURE_CANDIDATE']
            if kind=='capability_operator_registry_exact':
                actual={
                    'operator_count':len(SUPPORTED_OPERATOR_REGISTRY),
                    'registry_sha256':operator_registry_sha256(),
                    'all_declarative_profiles_registered':all(
                        DECLARATIVE_PROFILE_REGISTRY.get(item['declarative_profile_id'])==item['result_profile']
                        for item in SUPPORTED_OPERATOR_REGISTRY.values()
                    ),
                    'business_operator_semantics_executed':False,
                }
            elif kind in {'capability_actual_bounded_witnesses','capability_status_gates_exact'}:
                validate_capability_specs(capabilities,adoption,schema,receipts); _,summary=execute_capability_bounded_witnesses(capabilities,receipts)
                actual={key:summary[key] for key in exp}
            elif kind=='capability_bounded_replay_deterministic':
                validate_capability_specs(capabilities,adoption,schema,receipts)
                first,first_summary=execute_capability_bounded_witnesses(capabilities,receipts)
                second,second_summary=execute_capability_bounded_witnesses(capabilities,receipts)
                actual=canonical(first)==canonical(second) and first_summary['execution_receipts_sha256']==second_summary['execution_receipts_sha256']
            elif kind=='capability_unsupported_operator_rejected':
                target=next(item for item in capabilities if item['object_id']==inp['capability_id']); unsupported=inp['unsupported_operator']
                target['assembly_spec']['join']['operator']=unsupported; target['assembly_contract']['operator']=unsupported; target['operator_contract']['operator_id']=unsupported
                for binding in target['source_bindings']: binding['relation']['operator']=unsupported
                try: validate_capability_specs(capabilities,adoption,schema,receipts); actual=False
                except RuntimeError as error: actual=str(error).startswith('CAPABILITY_OPERATOR_ID_NOT_REGISTERED:')
            elif kind=='capability_operator_contract_mutation_rejected':
                target=next(item for item in capabilities if item['object_id']==inp['capability_id']); target['operator_contract'][inp['contract_field']]=inp['value']
                try: validate_capability_specs(capabilities,adoption,schema,receipts); actual=False
                except RuntimeError as error: actual=str(error).startswith('CAPABILITY_OPERATOR_CONTRACT_MISMATCH:')
            elif kind=='capability_operator_parameters_mutation_rejected':
                target=next(item for item in capabilities if item['object_id']==inp['capability_id'])
                target['operator_parameters'][inp['parameter_field']]=inp['value']
                try: validate_capability_specs(capabilities,adoption,schema,receipts); actual=False
                except RuntimeError as error: actual=str(error).startswith('CAPABILITY_OPERATOR_PARAMETERS_MISMATCH:')
            elif kind=='capability_unknown_transform_rejected':
                target=next(item for item in capabilities if item['object_id']==inp['capability_id'])
                target['assembly_spec']['source_bindings'][0]['field_rules'][0]['transform']=inp['transform']
                target['source_bindings'][0]['field_rules'][0]['transform']=inp['transform']
                try: validate_capability_specs(capabilities,adoption,schema,receipts); actual=False
                except RuntimeError as error: actual=str(error).startswith('CAPABILITY_TRANSFORM_NOT_IMPLEMENTED:')
            elif kind=='capability_field_rule_missing_rejected':
                target=next(item for item in capabilities if item['object_id']==inp['capability_id'])
                target['assembly_spec']['source_bindings'][0]['field_rules'].pop(); target['source_bindings'][0]['field_rules'].pop()
                try: validate_capability_specs(capabilities,adoption,schema,receipts); actual=False
                except RuntimeError as error: actual=str(error).startswith('CAPABILITY_FIELD_RULE_COUNT_MISMATCH:')
            elif kind=='capability_row_locator_never_used_as_join':
                validate_capability_specs(capabilities,adoption,schema,receipts); executions,_=execute_capability_bounded_witnesses(capabilities,receipts)
                actual=all(
                    match.get('canonical_key','').lower() not in FORBIDDEN_CROSS_SOURCE_LOCATOR_FIELDS
                    and all(str(alias.get('source_field') or '').lower() not in FORBIDDEN_CROSS_SOURCE_LOCATOR_FIELDS for alias in match.get('aliases') or [])
                    for item in executions for match in (item.get('join_witness') or {}).get('matches') or []
                )
            elif kind=='capability_row_alias_locator_rejected':
                forbidden_fields=inp.get('forbidden_source_fields') or [inp['forbidden_source_field']]
                rejected=[]
                for forbidden_field in forbidden_fields:
                    mutated=json.loads(json.dumps(capabilities,ensure_ascii=False))
                    target=next(item for item in mutated if item['object_id']==inp['capability_id'])
                    target['assembly_spec']['join']['keys'][0]['verified_source_aliases'][0]['source_field']=forbidden_field
                    target['assembly_contract']['join_key_families'][0]['verified_source_aliases'][0]['source_field']=forbidden_field
                    try: validate_capability_specs(mutated,adoption,schema,receipts); rejected.append(False)
                    except RuntimeError as error: rejected.append(str(error).startswith('CAPABILITY_ROW_LOCATOR_ALIAS_DECLARED_AS_JOIN_KEY:'))
                actual=all(rejected) and len(rejected)==len(FORBIDDEN_CROSS_SOURCE_LOCATOR_FIELDS)
            elif kind=='capability_unjoined_bindings_preserved':
                validate_capability_specs(capabilities,adoption,schema,receipts); executions,_=execute_capability_bounded_witnesses(capabilities,receipts)
                by_id={item['capability_id']:item for item in executions}
                relation_unjoined={}; coverage_unjoined={}
                for capability in capabilities:
                    if capability['closure_status']!=RUNNABLE_CAPABILITY_STATUS or not capability['assembly_spec']['join']['required']:
                        continue
                    capability_id=capability['object_id']; witness=by_id[capability_id]['join_witness']
                    unjoined=witness.get('unjoined_bindings') or []
                    if not unjoined: continue
                    if witness['status']=='COVERAGE_KEY_WITNESS_ONLY_SOURCES_REMAIN_UNJOINED':
                        coverage_unjoined[capability_id]=unjoined
                    else:
                        relation_unjoined[capability_id]=unjoined
                actual={
                    'required_relation_unjoined_bindings':relation_unjoined,
                    'coverage_only_unjoined_bindings':coverage_unjoined,
                }
            else:
                target=next(item for item in capabilities if item['object_id']==inp['capability_id'])
                target['bounded_execution_contract']['expected_receipt_sha256']='0'*64
                try: execute_capability_bounded_witnesses(capabilities,receipts); actual=False
                except RuntimeError as error: actual=str(error).startswith('CAPABILITY_WITNESS_RECEIPT_MISMATCH:'+inp['capability_id'])
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
            'fact_base_copy_funds_boundary_erasure_rejected','fact_base_source_event_mismatch_rejected',
            'fact_base_source_event_missing_rejected',
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
                elif kind=='fact_base_copy_funds_boundary_erasure_rejected':
                    target=next(item for item in records if item.get('fact_subtype')=='RELATION_TARGET_OBJECT_REFERENCE' and 'COPY_FUNDS_NODE' in (item.get('source_relation_types') or []))
                    target['object_class']='ACTIVE_TRADE'; target['promotion_prohibited']=False; target['cannot_prove']=''
                elif kind=='fact_base_source_event_mismatch_rejected':
                    target=next(item for item in records if item.get('fact_id')==inp['relation_fact_id'])
                    target['relation']['source_fact_id']=inp['wrong_source_fact_id']
                else:
                    target=next(item for item in records if item.get('fact_id')==inp['relation_fact_id'])
                    target['relation']['source_event_id']=None
                try: validate_fact_base_against_schema(records,schema); actual=False
                except RuntimeError as error:
                    expected_prefix=inp.get('expected_error_prefix')
                    actual=(str(error).startswith(expected_prefix) if expected_prefix else True)
        elif kind in {
            'utf16_chunk_boundary','technical_chunk_plan_actual','technical_chunk_missing_rejected',
            'technical_chunk_modified_rejected','technical_chunk_unsafe_limit_rejected',
        }:
            if kind=='utf16_chunk_boundary':
                source='a'*inp['ordinary_prefix_count']+inp['supplementary_character']+inp['ordinary_suffix']
                chunks=split_utf16_safe(source,inp['safe_cell_limit_utf16_units'])
                actual={
                    'chunk_utf16_units':[utf16_units(chunk) for chunk in chunks],
                    'reassembled_exact':''.join(chunks)==source,
                }
            elif kind=='technical_chunk_unsafe_limit_rejected':
                try: split_utf16_safe('test',inp['unsafe_limit']); actual=False
                except RuntimeError as error: actual=str(error).startswith(inp['expected_error_prefix'])
            else:
                records=read_jsonl((base/inp['fact_base_file']).resolve())
                rows=technical_chunk_rows(records,inp['safe_cell_limit_utf16_units'])
                if kind=='technical_chunk_plan_actual':
                    result=validate_technical_chunk_rows(rows,records,inp['safe_cell_limit_utf16_units'])
                    actual={key:result[key] for key in exp}
                elif kind=='technical_chunk_missing_rejected':
                    target_id=inp['fact_id']; target_rows=[index for index,row in enumerate(rows) if row['事实ID']==target_id]
                    del rows[target_rows[inp['remove_chunk_number']-1]]
                    try: validate_technical_chunk_rows(rows,records,inp['safe_cell_limit_utf16_units']); actual=False
                    except RuntimeError as error: actual=str(error).startswith(inp['expected_error_prefix'])
                else:
                    target=next(row for row in rows if row['事实ID']==inp['fact_id'] and row['第几段']==inp['chunk_number'])
                    original=target['技术原文分段']
                    target['技术原文分段']=inp['replacement_character']+original[1:]
                    target['本段UTF-16长度']=utf16_units(target['技术原文分段'])
                    try: validate_technical_chunk_rows(rows,records,inp['safe_cell_limit_utf16_units']); actual=False
                    except RuntimeError as error: actual=str(error).startswith(inp['expected_error_prefix'])
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
    c=sub.add_parser('verify-capabilities'); c.add_argument('--mapping',required=True); c.add_argument('--adoption',required=True); c.add_argument('--schema',required=True); c.add_argument('--receipts',required=True); c.add_argument('--output')
    t=sub.add_parser('self-test'); t.add_argument('--tests',required=True)
    a=p.parse_args()
    if a.cmd=='load-selected-objects': load_selected_objects(a.receipts,a.output_dir)
    elif a.cmd=='build-bounded': build(a.config,a.samples,a.output)
    elif a.cmd=='build-views': build_views(a.config,a.output_dir,a.preview_dir,a.verification_output)
    elif a.cmd=='verify-capabilities': verify_capabilities(a.mapping,a.adoption,a.schema,a.receipts,a.output)
    else: run_tests(a.tests)
