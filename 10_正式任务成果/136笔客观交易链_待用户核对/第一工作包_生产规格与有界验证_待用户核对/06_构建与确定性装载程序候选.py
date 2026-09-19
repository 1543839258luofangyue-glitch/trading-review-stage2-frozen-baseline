#!/usr/bin/env python3
"""Deterministic bounded loader for the first 136-chain preparation package.

This candidate program never writes source files, never performs the three real
business recomputations, and never builds the full 136-trade chain.  It verifies
the exact eight K05 files, loads only manifest-selected sample objects, preserves
all original values as strings, emits one canonical JSONL fact base, and rebuilds
both the AI-readable view and the user-review visual page from that same fact base.
"""

import argparse, contextlib, csv, hashlib, io, json, os, re, shutil, stat, subprocess, sys, tempfile, zipfile
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

# Version 2 is the authoritative callable layer used only for approved bounded
# execution.  It is intentionally separate from the original declarative
# witness registry so the historical witness hashes remain reproducible.  Each
# operator is bound to one closed handler and one explicit semantic rule.  The
# handlers emit candidate business results, never formal adopted facts.
BUSINESS_OPERATOR_REGISTRY_VERSION='2.0'
BUSINESS_OPERATOR_SEMANTIC_RULES={
    'ACTIVE_AND_COPY_SCOPE_PARTITION':('CLASSIFICATION','ACTIVE_COPY_SCOPE_EXACT_SOURCE_CLASSIFICATION'),
    'ADJACENT_REVERSE_POSITION_OBJECTIVE_LINKAGE':('RELATION','EXACT_DECLARED_KEY_RELATION_NO_CAUSAL_INFERENCE'),
    'ANALYSIS_STRATEGY_AND_COUNTERFACTUAL_BOUNDARY':('BOUNDARY','ZERO_OBJECTIVE_OUTPUT_FOR_ANALYSIS_OR_COUNTERFACTUAL'),
    'CANONICAL_CASH_EVENT_DEDUPLICATION_AND_TRANSFER_PAIRING':('RELATION','EXACT_TRANSFER_PAIR_KEYS_PRESERVE_UNMATCHED'),
    'CONDITION_TO_ORDER_FILL_AND_CYCLE_RELATION_GRAPH':('RELATION','EXACT_CONDITION_ORDER_FILL_CYCLE_EDGES_ONLY'),
    'FACT_USER_STATEMENT_INTERPRETATION_AND_STATUS_LAYERING':('CLASSIFICATION','SEPARATE_FACT_USER_STATEMENT_AI_INTERPRETATION_AND_STATUS'),
    'FEE_AND_NET_RESULT_COMPONENT_SEPARATION':('MEASURE','PRESERVE_FEE_PNL_FUNDING_COMPONENTS_WITH_CURRENCY'),
    'FILL_PRICE_AND_WEIGHTED_AVERAGE_TRANSITION':('MEASURE','DECIMAL_FILL_AND_WEIGHTED_PRICE_TRANSITION_NO_FLOAT'),
    'FILL_TO_ORDER_AND_CYCLE_LINKAGE':('RELATION','EXACT_FILL_ORDER_CYCLE_KEYS_ONLY'),
    'FUTURE_SCHEMA_AND_FORMAT_BOUNDARY':('BOUNDARY','ZERO_OBJECTIVE_OUTPUT_FOR_FUTURE_PRODUCT_FORMAT'),
    'IDENTIFIER_MAPPING_WITHOUT_ID_REPLACEMENT':('IDENTITY','PRESERVE_SOURCE_NAMESPACE_AND_NEVER_REPLACE_IDS'),
    'IDENTITY_RESOLUTION_WITH_SOURCE_BOUNDARIES':('IDENTITY','RESOLVE_ONLY_BY_DECLARED_KEYS_AND_SOURCE_BOUNDARIES'),
    'MARGIN_AND_RISK_FIELDS_SEPARATED_NO_INFERENCE_FOR_MISSING_VALUES':('MEASURE','PRESERVE_MARGIN_RISK_FIELDS_AND_UNKNOWN_NO_INFERENCE'),
    'MARKET_DATA_IDENTITY_WINDOW_AND_COVERAGE':('COVERAGE','LOCK_MARKET_IDENTITY_WINDOW_AND_MISSING_COVERAGE'),
    'MFE_MAE_BY_CYCLE_OR_POSITION_STAGE':('MEASURE','PRESERVE_MFE_MAE_BY_DECLARED_CYCLE_OR_STAGE'),
    'NON_OBJECTIVE_USER_REASON_BOUNDARY':('BOUNDARY','ZERO_OBJECTIVE_OUTPUT_FOR_USER_REASON'),
    'OBJECTIVE_ACTION_CLASSIFICATION_WITH_EVIDENCE':('CLASSIFICATION','CLASSIFY_ACTION_ONLY_FROM_DECLARED_EVIDENCE_FIELDS'),
    'ORDER_AND_CONDITION_LIFECYCLE_LINKAGE':('LIFECYCLE','ORDER_CONDITION_STATES_AND_EXACT_RELATIONS'),
    'POSITION_QUANTITY_STATE_TRANSITION':('MEASURE','DECIMAL_POSITION_BEFORE_AFTER_TRANSITION'),
    'POSITION_ZERO_TO_NONZERO_TO_ZERO_CYCLE_GROUPING':('LIFECYCLE','ZERO_NONZERO_ZERO_CYCLE_WITHOUT_ROW_ORDER_JOIN'),
    'REALIZED_PNL_BY_FILL_AND_CYCLE':('MEASURE','PRESERVE_REALIZED_PNL_COMPONENTS_BY_EXACT_FILL_OR_CYCLE'),
    'REFERENTIAL_AND_QUANTITY_INTEGRITY_CHECKS':('INTEGRITY','REQUIRE_REFERENTIAL_AND_QUANTITY_CHECKS_NO_SILENT_REPAIR'),
    'SCREENSHOT_CONDITION_AND_CYCLE_LINEAGE_BRIDGE':('LINEAGE','PRESERVE_SCREENSHOT_CONDITION_CYCLE_SOURCE_CHAIN'),
    'SIDE_POSITION_SIDE_AND_POSITION_EFFECT_SEPARATION':('CLASSIFICATION','SEPARATE_SIDE_POSITION_SIDE_AND_POSITION_EFFECT'),
    'STABLE_ID_AND_SOURCE_NAMESPACE_PRESERVATION':('IDENTITY','STABLE_ID_WITH_SOURCE_NAMESPACE_PRESERVED'),
    'STOP_LOSS_LIFECYCLE_WITH_UNKNOWN_RELATION_PRESERVATION':('LIFECYCLE','STOP_LOSS_LIFECYCLE_PRESERVE_UNKNOWN_RELATION'),
    'TAKE_PROFIT_LIFECYCLE_WITH_UNKNOWN_RELATION_PRESERVATION':('LIFECYCLE','TAKE_PROFIT_LIFECYCLE_PRESERVE_UNKNOWN_RELATION'),
    'TIMELINE_UNION_PRESERVE_EQUAL_TIME_PARALLEL_EVENTS':('TIMELINE','SORT_FOR_DISPLAY_AND_PRESERVE_EQUAL_TIME_PARALLEL'),
    'TIME_BOUNDED_EQUITY_ANCHORS_AND_UNKNOWN_GAPS':('TIMELINE','BOUND_EQUITY_ANCHORS_AND_PRESERVE_TIME_GAPS'),
    'TIME_NORMALIZATION_WITH_ORIGINAL_VALUE_AND_PRECISION':('TIMELINE','PRESERVE_ORIGINAL_TIME_TIMEZONE_AND_PRECISION'),
    'USER_INTERFACE_PRODUCT_BOUNDARY':('BOUNDARY','ZERO_OBJECTIVE_OUTPUT_FOR_USER_INTERFACE_PRODUCT'),
    'USER_STAGE_AGGREGATION_ACROSS_POSITION_PRICE_AND_MFE_MAE_COMPONENTS':('MEASURE','USER_ACCEPTANCE_GATE_BEFORE_STAGE_AGGREGATION'),
    'VERSION_CORRECTION_AND_SOURCE_IDENTITY_LINEAGE':('LINEAGE','PRESERVE_VERSION_CORRECTION_AND_SOURCE_IDENTITY_LINEAGE'),
}
BUSINESS_HANDLER_IDS={
    'BOUNDARY','CLASSIFICATION','COVERAGE','IDENTITY','INTEGRITY',
    'LIFECYCLE','LINEAGE','MEASURE','RELATION','TIMELINE',
}
SEMANTIC_RULE_PRIMARY_OUTPUT_KEY={
    'ACTIVE_COPY_SCOPE_EXACT_SOURCE_CLASSIFICATION':'scope_partitions',
    'EXACT_DECLARED_KEY_RELATION_NO_CAUSAL_INFERENCE':'reverse_link_candidates',
    'ZERO_OBJECTIVE_OUTPUT_FOR_ANALYSIS_OR_COUNTERFACTUAL':'boundary',
    'EXACT_TRANSFER_PAIR_KEYS_PRESERVE_UNMATCHED':'canonical_cash_groups',
    'EXACT_CONDITION_ORDER_FILL_CYCLE_EDGES_ONLY':'condition_graph_edges',
    'SEPARATE_FACT_USER_STATEMENT_AI_INTERPRETATION_AND_STATUS':'separated_layers',
    'PRESERVE_FEE_PNL_FUNDING_COMPONENTS_WITH_CURRENCY':'financial_components',
    'DECIMAL_FILL_AND_WEIGHTED_PRICE_TRANSITION_NO_FLOAT':'price_transitions',
    'EXACT_FILL_ORDER_CYCLE_KEYS_ONLY':'fill_relation_edges',
    'ZERO_OBJECTIVE_OUTPUT_FOR_FUTURE_PRODUCT_FORMAT':'boundary',
    'PRESERVE_SOURCE_NAMESPACE_AND_NEVER_REPLACE_IDS':'identifier_mappings',
    'RESOLVE_ONLY_BY_DECLARED_KEYS_AND_SOURCE_BOUNDARIES':'identity_resolution_groups',
    'PRESERVE_MARGIN_RISK_FIELDS_AND_UNKNOWN_NO_INFERENCE':'margin_and_risk',
    'LOCK_MARKET_IDENTITY_WINDOW_AND_MISSING_COVERAGE':'market_coverage',
    'PRESERVE_MFE_MAE_BY_DECLARED_CYCLE_OR_STAGE':'mfe_mae_groups',
    'ZERO_OBJECTIVE_OUTPUT_FOR_USER_REASON':'boundary',
    'CLASSIFY_ACTION_ONLY_FROM_DECLARED_EVIDENCE_FIELDS':'action_classifications',
    'ORDER_CONDITION_STATES_AND_EXACT_RELATIONS':'lifecycle_events',
    'DECIMAL_POSITION_BEFORE_AFTER_TRANSITION':'position_transitions',
    'ZERO_NONZERO_ZERO_CYCLE_WITHOUT_ROW_ORDER_JOIN':'cycle_boundaries',
    'PRESERVE_REALIZED_PNL_COMPONENTS_BY_EXACT_FILL_OR_CYCLE':'realized_pnl_components',
    'REQUIRE_REFERENTIAL_AND_QUANTITY_CHECKS_NO_SILENT_REPAIR':'integrity_findings',
    'PRESERVE_SCREENSHOT_CONDITION_CYCLE_SOURCE_CHAIN':'screenshot_lineage',
    'SEPARATE_SIDE_POSITION_SIDE_AND_POSITION_EFFECT':'side_layers',
    'STABLE_ID_WITH_SOURCE_NAMESPACE_PRESERVED':'stable_identifiers',
    'STOP_LOSS_LIFECYCLE_PRESERVE_UNKNOWN_RELATION':'stop_loss_lifecycle',
    'TAKE_PROFIT_LIFECYCLE_PRESERVE_UNKNOWN_RELATION':'take_profit_lifecycle',
    'SORT_FOR_DISPLAY_AND_PRESERVE_EQUAL_TIME_PARALLEL':'timeline_groups',
    'BOUND_EQUITY_ANCHORS_AND_PRESERVE_TIME_GAPS':'equity_anchor_intervals',
    'PRESERVE_ORIGINAL_TIME_TIMEZONE_AND_PRECISION':'normalized_times',
    'ZERO_OBJECTIVE_OUTPUT_FOR_USER_INTERFACE_PRODUCT':'boundary',
    'USER_ACCEPTANCE_GATE_BEFORE_STAGE_AGGREGATION':'user_acceptance_gate',
    'PRESERVE_VERSION_CORRECTION_AND_SOURCE_IDENTITY_LINEAGE':'version_lineage',
}

def semantic_callable_id(semantic_rule_id):
    return 'semantic_'+semantic_rule_id.lower()

def business_operator_registry_manifest():
    operators={
        operator_id:{
            'handler_group':handler_id,
            'semantic_rule_id':semantic_rule_id,
            'callable_id':semantic_callable_id(semantic_rule_id),
            'required_output_key':SEMANTIC_RULE_PRIMARY_OUTPUT_KEY[semantic_rule_id],
            'positive_test_id':'SEMANTIC_POSITIVE_'+semantic_rule_id,
            'negative_test_id':'SEMANTIC_NEGATIVE_'+semantic_rule_id,
        }
        for operator_id,(handler_id,semantic_rule_id) in sorted(BUSINESS_OPERATOR_SEMANTIC_RULES.items())
    }
    return {
        'record_type':'BUSINESS_OPERATOR_IMPLEMENTATION_REGISTRY',
        'registry_version':BUSINESS_OPERATOR_REGISTRY_VERSION,
        'operator_count':len(operators),
        'operators':operators,
        'implementation_id':'AUTHORITATIVE_BOUNDED_OPERATOR_DISPATCH',
        'implementation_version':'2.0',
        'input_contract':'LOCKED_SOURCE_WITNESSES_PLUS_DECLARED_JOIN_WITNESS',
        'output_contract':'ELEVEN_DECLARED_CAPABILITY_FIELDS_PLUS_RULE_SPECIFIC_NORMALIZED_VALUE',
        'default_execution_mode':'APPROVED_BOUNDED_REAL_MIRROR_ONLY',
        'unregistered_operator_action':'REJECT',
        'real_recomputation_allowed':False,
        'formal_adoption_allowed':False,
        'full_136_execution_allowed':False,
    }

def business_operator_coverage_manifest(capability_records):
    by_operator=defaultdict(list); by_status=Counter()
    for item in capability_records:
        operator=item['assembly_spec']['join']['operator']
        by_operator[operator].append(item['object_id']); by_status[item['closure_status']]+=1
    return {
        'record_type':'CAPABILITY_EXECUTABLE_COVERAGE_MATRIX',
        'registry_version':BUSINESS_OPERATOR_REGISTRY_VERSION,
        'capability_count':len(capability_records),
        'operator_count':len(by_operator),
        'capability_ids_by_operator':{
            operator:sorted(capability_ids) for operator,capability_ids in sorted(by_operator.items())
        },
        'closure_status_counts':dict(sorted(by_status.items())),
        'runnable_capability_action':'EXECUTE_AUTHORITATIVE_BOUNDED_OPERATOR',
        'unresolved_capability_action':'REJECT_OUTPUT_AND_PRESERVE_UNKNOWN',
        'non_objective_boundary_action':'EXECUTE_ZERO_OBJECTIVE_OUTPUT_GATE',
        'pending_user_action':'REJECT_OUTPUT_UNTIL_USER_DECISION',
        'formal_fact_output_count':0,
    }

def validate_business_operator_registry_records(mapping_records,capability_records):
    registries=[item for item in mapping_records if item.get('record_type')=='BUSINESS_OPERATOR_IMPLEMENTATION_REGISTRY']
    matrices=[item for item in mapping_records if item.get('record_type')=='CAPABILITY_EXECUTABLE_COVERAGE_MATRIX']
    if len(registries)!=1 or registries[0]!=business_operator_registry_manifest():
        raise RuntimeError('BUSINESS_OPERATOR_IMPLEMENTATION_REGISTRY_MISMATCH')
    expected_matrix=business_operator_coverage_manifest(capability_records)
    if len(matrices)!=1 or matrices[0]!=expected_matrix:
        raise RuntimeError('CAPABILITY_EXECUTABLE_COVERAGE_MATRIX_MISMATCH')
    if set(BUSINESS_OPERATOR_SEMANTIC_RULES)!=set(SUPPORTED_OPERATOR_REGISTRY):
        raise RuntimeError('BUSINESS_OPERATOR_IMPLEMENTATION_SET_MISMATCH')
    if any(handler_id not in BUSINESS_HANDLER_IDS for handler_id,_rule in BUSINESS_OPERATOR_SEMANTIC_RULES.values()):
        raise RuntimeError('BUSINESS_OPERATOR_HANDLER_NOT_CALLABLE')
    if set(SEMANTIC_RULE_CALLABLES)!=set(SEMANTIC_RULE_PRIMARY_OUTPUT_KEY):
        raise RuntimeError('BUSINESS_SEMANTIC_CALLABLE_SET_MISMATCH')
    if len({id(callable_) for callable_ in SEMANTIC_RULE_CALLABLES.values()})!=33 or len({callable_.__name__ for callable_ in SEMANTIC_RULE_CALLABLES.values()})!=33:
        raise RuntimeError('BUSINESS_SEMANTIC_CALLABLE_NOT_UNIQUE')
    return {
        'operator_count':len(BUSINESS_OPERATOR_SEMANTIC_RULES),
        'capability_count':len(capability_records),
        'registry_version':BUSINESS_OPERATOR_REGISTRY_VERSION,
        'all_operators_have_authoritative_callable_implementation':True,
        'unique_semantic_callable_count':len(SEMANTIC_RULE_CALLABLES),
        'all_semantic_rules_have_rule_specific_output_validator':True,
        'coverage_matrix_exact':True,
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
        'selected_mirror_path':source.get('receipt_identity_mirror_path') or source.get('mirror_path'),
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

def business_values_by_usage(source_witnesses):
    """Collect exactly witnessed values by declared business usage."""
    values=defaultdict(list); unknown=[]
    for witness in source_witnesses:
        normalized=witness.get('normalized_value') or {}
        for rule in witness.get('applied_field_rules') or []:
            field=rule['source_field']; value=normalized.get(field)
            entry={
                'input_id':witness['input_id'],
                'selected_object_index':int(witness['selected_object_index']),
                'source_locator':witness['source_locator'],
                'source_field':field,
                'normalized_value':value,
            }
            values[rule['usage']].append(entry)
            if isinstance(value,dict) and value.get('status')=='UNKNOWN':
                unknown.append({
                    'owner_binding':f'{witness["input_id"]}#{int(witness["selected_object_index"])}',
                    'field_path':field,
                    'reason':value.get('reason') or 'SOURCE_FIELD_MISSING_OR_EMPTY',
                    'missing_evidence':'LOCKED_SOURCE_FIELD_HAS_NO_VALUE',
                    'scope':'BOUNDED_OPERATOR_SOURCE_WITNESS',
                })
    return {key:sorted(items,key=lambda item:(item['input_id'],item['selected_object_index'],item['source_locator'],item['source_field'])) for key,items in values.items()},sorted(unknown,key=canonical)

def business_join_pairs(join_witness):
    pairs=[]
    for match in join_witness.get('matches') or []:
        pairs.append({
            'canonical_key':match['canonical_key'],
            'raw_value':match['raw_value'],
            'match_scope':match['match_scope'],
            'match_count_left':int(match['match_count_left']),
            'match_count_right':int(match['match_count_right']),
            'aliases':match['aliases'],
        })
    return sorted(pairs,key=canonical)

DECLARED_CAPABILITY_OUTPUT_FIELDS=(
    'capability_id','capability_name','fact_id','object_id','raw_value',
    'normalized_value','evidence_status','applicability_scope',
    'source_identity_id','relation_ids','conflict_ids',
)

def semantic_field_entries(source_witnesses,tokens=(),usages=()):
    """Return exact source fields selected by a rule; never infer an absent field."""
    entries=[]; lower_tokens=tuple(str(token).lower() for token in tokens)
    for witness in source_witnesses:
        raw=witness.get('raw_value') or {}; normalized=witness.get('normalized_value') or {}
        usage_by_field={rule['source_field']:rule['usage'] for rule in witness.get('applied_field_rules') or []}
        for field in sorted(normalized):
            lowered=field.lower(); usage=usage_by_field.get(field)
            if lower_tokens and not any(token in lowered for token in lower_tokens): continue
            if usages and usage not in usages: continue
            entries.append({
                'input_id':witness['input_id'],'selected_object_index':int(witness['selected_object_index']),
                'source_locator':witness['source_locator'],'source_field':field,'usage':usage,
                'raw_value':raw.get(field),'normalized_value':normalized[field],
            })
    return entries

def require_semantic_entries(rule_id,entries,condition):
    if condition and not entries:
        raise RuntimeError('SEMANTIC_RULE_REQUIRED_INPUT_MISSING:'+rule_id)
    return entries

def semantic_exact_decimal(value):
    if isinstance(value,bool) or value is None or isinstance(value,(dict,list)): return None
    text=str(value).strip().strip("'")
    if not re.fullmatch(r'-?\d+(?:\.\d+)?',text): return None
    return Decimal(text)

def semantic_relation_edges(rule_id,pairs):
    edges=[]
    for pair in pairs:
        relation_id=stable_id('REL',hashlib.sha256(canonical(pair).encode('utf-8')).hexdigest(),rule_id,pair['canonical_key'])
        edges.append({'relation_id':relation_id,'relation_type':rule_id,'exact_key_witness':pair})
    return edges

def semantic_payload(rule_id,item,source_witnesses,join_witness):
    """Execute one rule-specific bounded transformation on locked witnesses."""
    values,unknown=business_values_by_usage(source_witnesses); pairs=business_join_pairs(join_witness)
    all_entries=semantic_field_entries(source_witnesses)
    common={
        'semantic_rule_id':rule_id,'callable_id':semantic_callable_id(rule_id),
        'source_witness_count':len(source_witnesses),
        'source_locators':sorted(witness['source_locator'] for witness in source_witnesses),
        'unknown_items':unknown,'no_ai_causal_inference':True,'no_formal_fact_promotion':True,
        'bounded_sample_only':True,
    }
    boundary_rules={
        'ZERO_OBJECTIVE_OUTPUT_FOR_ANALYSIS_OR_COUNTERFACTUAL',
        'ZERO_OBJECTIVE_OUTPUT_FOR_FUTURE_PRODUCT_FORMAT',
        'ZERO_OBJECTIVE_OUTPUT_FOR_USER_REASON',
        'ZERO_OBJECTIVE_OUTPUT_FOR_USER_INTERFACE_PRODUCT',
    }
    if rule_id in boundary_rules:
        return {**common,'output_mode':'ZERO_OBJECTIVE_OUTPUT','boundary':{'reason':item['business_meaning'],'objective_fact_output_count':0}}
    if rule_id=='USER_ACCEPTANCE_GATE_BEFORE_STAGE_AGGREGATION':
        return {**common,'output_mode':'USER_ACCEPTANCE_REQUIRED','user_acceptance_gate':{'passed':False,'production_output_count':0}}
    if not source_witnesses:
        raise RuntimeError('SEMANTIC_RULE_SOURCE_WITNESS_MISSING:'+rule_id)
    if rule_id=='ACTIVE_COPY_SCOPE_EXACT_SOURCE_CLASSIFICATION':
        fields=require_semantic_entries(rule_id,semantic_field_entries(source_witnesses,('交易来源分类','是否个人主动','是否自动跟单','record_type','source_business_type','新增5笔记录性质')),True)
        partitions={'USER_ACTIVE':[],'COPY_OR_AUTOMATED':[],'NON_TRADE_CASH_OR_OTHER':[],'UNRESOLVED':[]}
        for witness in source_witnesses:
            witness_fields=[entry for entry in fields if entry['input_id']==witness['input_id'] and entry['source_locator']==witness['source_locator']]
            if not witness_fields: continue
            texts=[canonical(entry['normalized_value']).lower() for entry in witness_fields]
            targets=set()
            if any(any(x in text for x in ('个人主动','user_active','主动交易')) for text in texts): targets.add('USER_ACTIVE')
            if any(any(x in text for x in ('跟单','copy','自动')) for text in texts): targets.add('COPY_OR_AUTOMATED')
            if any(any(x in text for x in ('transfer','funding','划转','资金费')) for text in texts): targets.add('NON_TRADE_CASH_OR_OTHER')
            target=next(iter(targets)) if len(targets)==1 else 'UNRESOLVED'
            partitions[target].append({'input_id':witness['input_id'],'source_locator':witness['source_locator'],'classification_evidence':witness_fields,'conflicting_scope_labels':sorted(targets) if len(targets)>1 else []})
        return {**common,'output_mode':'CANDIDATE_SCOPE_PARTITION','scope_partitions':partitions}
    if rule_id=='EXACT_DECLARED_KEY_RELATION_NO_CAUSAL_INFERENCE':
        generic_edges=semantic_relation_edges(rule_id,pairs); qualifications=[]
        for witness in source_witnesses:
            row=witness.get('normalized_value') or {}
            before_end=next((semantic_exact_decimal(row.get(key)) for key in ('previous_cycle_end_quantity','previous_position_after','前周期结束持仓') if semantic_exact_decimal(row.get(key)) is not None),None)
            next_start=next((semantic_exact_decimal(row.get(key)) for key in ('next_cycle_start_quantity','next_position_after','后周期开始持仓') if semantic_exact_decimal(row.get(key)) is not None),None)
            previous_direction=str(next((row.get(key) for key in ('previous_direction','previous_position_side','前周期方向') if row.get(key) not in (None,'')),'')).upper()
            next_direction=str(next((row.get(key) for key in ('next_direction','next_position_side','后周期方向') if row.get(key) not in (None,'')),'')).upper()
            opposite=(previous_direction,next_direction) in {('LONG','SHORT'),('SHORT','LONG'),('多','空'),('空','多')}
            if before_end==0 and next_start not in (None,Decimal(0)) and opposite:
                qualifications.append({'source_locator':witness['source_locator'],'previous_cycle_ended_at_zero':True,'next_cycle_started_nonzero':True,'directions_opposite':True,'previous_direction':previous_direction,'next_direction':next_direction})
        edges=generic_edges if qualifications else []
        directions=semantic_field_entries(source_witnesses,('direction','side','方向','仓位方向'))
        return {**common,'output_mode':'CANDIDATE_REVERSE_LINK','reverse_link_candidates':{'edges':edges,'qualification_evidence':qualifications,'generic_join_edges_ignored_without_objective_reverse_qualification':len(generic_edges) if not qualifications else 0,'direction_evidence':directions,'adjacency_or_causality_inferred':False}}
    if rule_id=='EXACT_TRANSFER_PAIR_KEYS_PRESERVE_UNMATCHED':
        identifiers=require_semantic_entries(rule_id,semantic_field_entries(source_witnesses,('canonical_economic_event_id','unified_event_record_id','internal_transfer_pair_id','mirror_of_source_record_id','source_record_id')),True)
        groups=defaultdict(list); transfer_groups=defaultdict(list); net_checks=[]
        for entry in identifiers:
            value=canonical(entry['normalized_value'])
            namespace=('TRANSFER_PAIR' if 'transfer_pair' in entry['source_field'] else 'CANONICAL_EVENT' if 'canonical' in entry['source_field'] or 'unified_event' in entry['source_field'] else 'SOURCE_RECORD')
            groups[(namespace,value)].append(entry)
            if namespace=='TRANSFER_PAIR': transfer_groups[value].append(entry)
        pair_amounts=defaultdict(list); unknown_currency_components=[]
        for witness in source_witnesses:
            row=witness.get('normalized_value') or {}
            pair_id=row.get('internal_transfer_pair_id')
            if pair_id in (None,''): continue
            currency=next((str(row.get(key)) for key in ('asset','currency','margin_asset','币种') if row.get(key) not in (None,'')),None)
            for field in ('in_amount_signed_exact','in_amount','transfer_in','out_amount_signed_exact','out_amount','transfer_out','amount_signed'):
                parsed=semantic_exact_decimal(row.get(field))
                if parsed is None: continue
                component={'field':field,'value':parsed,'source_locator':witness['source_locator'],'internal_transfer_pair_id':str(pair_id),'currency':currency}
                if currency is None: unknown_currency_components.append({**component,'value':decimal_text(parsed),'unknown_reason':'CURRENCY_REQUIRED_FOR_TRANSFER_NET_CHECK'})
                else: pair_amounts[(str(pair_id),currency)].append(component)
        for (pair_id,currency),components in sorted(pair_amounts.items()):
            incoming=sum((row['value'] for row in components if row['value']>0),Decimal(0)); outgoing=sum((row['value'] for row in components if row['value']<0),Decimal(0)); net=incoming+outgoing
            net_checks.append({'internal_transfer_pair_id':pair_id,'currency':currency,'component_count':len(components),'in_exact':decimal_text(incoming),'out_exact':decimal_text(outgoing),'net_exact':decimal_text(net),'external_wealth_effect_zero':net==0,'components':[{**row,'value':decimal_text(row['value'])} for row in components]})
        unmatched=[entry for entry in identifiers if entry['normalized_value'] in (None,'') or isinstance(entry['normalized_value'],dict) and entry['normalized_value'].get('status')=='UNKNOWN']
        canonical_groups=[{'namespace':key[0],'value':json.loads(key[1]),'members':members,'duplicate_mirror_candidate':key[0]=='CANONICAL_EVENT' and len(members)>1} for key,members in sorted(groups.items())]
        return {**common,'output_mode':'CANDIDATE_CANONICAL_CASH_GROUPS','canonical_cash_groups':{'exact_identifier_groups':canonical_groups,'transfer_pair_groups':[{'pair_id':json.loads(key),'members':members} for key,members in sorted(transfer_groups.items())],'transfer_net_checks':net_checks,'unknown_currency_components':unknown_currency_components,'transfer_edges':semantic_relation_edges(rule_id,pairs),'unmatched':unmatched,'deduplication_key_is_explicit_identity_not_amount_or_time':True,'net_check_partition_keys':['internal_transfer_pair_id','currency'],'deduplicated_total_not_computed':True}}
    if rule_id=='EXACT_CONDITION_ORDER_FILL_CYCLE_EDGES_ONLY':
        ids=require_semantic_entries(rule_id,semantic_field_entries(source_witnesses,('condition_record_id','algorithm_id','generated_order_id','order_id','position_cycle_id','候选周期id')),True)
        typed_edges=[]
        for witness in source_witnesses:
            row=witness.get('normalized_value') or {}
            condition=next((row.get(key) for key in ('condition_record_id','algorithm_id') if row.get(key) not in (None,'')),None)
            order=next((row.get(key) for key in ('generated_order_id','order_id') if row.get(key) not in (None,'') and not isinstance(row.get(key),dict)),None)
            fill=next((row.get(key) for key in ('fill_reconstruction_id','fill_id','trade_id') if row.get(key) not in (None,'')),None)
            cycle=next((row.get(key) for key in ('position_cycle_id','候选周期id') if row.get(key) not in (None,'')),None)
            for source,target,relation_type in ((condition,order,'CONDITION_GENERATES_ORDER'),(order,fill,'ORDER_HAS_FILL'),(fill,cycle,'FILL_BELONGS_TO_CYCLE')):
                if source is not None and target is not None:
                    typed_edges.append({'relation_id':stable_id('REL','SYNTHETIC_OR_LOCKED',witness['source_locator'],f'{relation_type}:{source}:{target}'),'relation_type':relation_type,'source_id':str(source),'target_id':str(target),'source_locator':witness['source_locator']})
        return {**common,'output_mode':'CANDIDATE_CONDITION_GRAPH','condition_graph_edges':{'nodes':ids,'typed_multi_hop_edges':sorted(typed_edges,key=canonical),'declared_cross_source_edges':semantic_relation_edges(rule_id,pairs),'similar_text_or_row_order_edges_created':False}}
    if rule_id=='SEPARATE_FACT_USER_STATEMENT_AI_INTERPRETATION_AND_STATUS':
        user_entries=semantic_field_entries(source_witnesses,('用户原话','user_statement'))
        ai_entries=semantic_field_entries(source_witnesses,('ai_interpretation','人工智能判断'))
        status_entries=semantic_field_entries(source_witnesses,('status','状态','evidence','证据'))
        excluded={(entry['input_id'],entry['source_locator'],entry['source_field']) for entry in user_entries+ai_entries+status_entries}
        fact_entries=[entry for entry in semantic_field_entries(source_witnesses,usages=('SOURCE_VALUE','MEASURE','TIME','OBJECT_ID','JOIN_KEY')) if (entry['input_id'],entry['source_locator'],entry['source_field']) not in excluded]
        return {**common,'output_mode':'CANDIDATE_SEPARATED_LAYERS','separated_layers':{'facts':fact_entries,'user_statements':user_entries,'ai_interpretations':ai_entries,'statuses':status_entries,'layers_merged':False}}
    if rule_id=='PRESERVE_FEE_PNL_FUNDING_COMPONENTS_WITH_CURRENCY':
        components=require_semantic_entries(rule_id,semantic_field_entries(source_witnesses,('fee','commission','pnl','funding','rebate','盈亏','手续费','资金费','返佣','result')),True)
        currencies=semantic_field_entries(source_witnesses,('asset','currency','币种','手续费资产'))
        return {**common,'output_mode':'CANDIDATE_FINANCIAL_COMPONENTS','financial_components':{'components':components,'currency_evidence':currencies,'components_summed_across_sources':False}}
    if rule_id=='DECIMAL_FILL_AND_WEIGHTED_PRICE_TRANSITION_NO_FLOAT':
        price_entries=require_semantic_entries(rule_id,semantic_field_entries(source_witnesses,('price','均价','成交价','加权成交价','成交额','notional')),True)
        quantity_entries=semantic_field_entries(source_witnesses,('quantity','数量','仓位前','仓位后','成交额'))
        components=[]; ungrouped=[]; grouped=defaultdict(lambda:{'components':[],'quantity':Decimal(0),'notional':Decimal(0)})
        for witness in source_witnesses:
            row=witness.get('normalized_value') or {}
            amount=next((semantic_exact_decimal(row.get(key)) for key in ('成交额','notional','quote_quantity') if semantic_exact_decimal(row.get(key)) is not None),None)
            qty=next((semantic_exact_decimal(row.get(key)) for key in ('成交数量','fill_quantity','quantity') if semantic_exact_decimal(row.get(key)) is not None),None)
            price=next((semantic_exact_decimal(row.get(key)) for key in ('成交价格（精确文本）','fill_price','price','成交价格') if semantic_exact_decimal(row.get(key)) is not None),None)
            if amount is None and price is not None and qty is not None: amount=price*qty
            if amount is not None and qty not in (None,Decimal(0)):
                symbol=str(row.get('symbol') or ''); owner_type=next((key for key in ('order_id','position_cycle_id','trade_id') if row.get(key) not in (None,'')),None); owner_value=str(row.get(owner_type) or '') if owner_type else ''; asset=str(row.get('asset') or row.get('margin_asset') or '')
                group_key=(symbol,owner_type or '',owner_value,asset)
                component={'input_id':witness['input_id'],'source_locator':witness['source_locator'],'group_identity':list(group_key),'quantity_exact':decimal_text(qty),'notional_exact':decimal_text(amount),'price_exact':decimal_text(amount/qty)}
                components.append(component)
                if not symbol or not owner_type:
                    ungrouped.append({**component,'unknown_reason':'SYMBOL_AND_ORDER_OR_CYCLE_OWNER_REQUIRED_FOR_WEIGHTED_AGGREGATION'})
                else:
                    grouped[group_key]['components'].append(component); grouped[group_key]['quantity']+=qty; grouped[group_key]['notional']+=amount
        aggregates=[]
        for group_key,value in sorted(grouped.items()):
            if value['quantity']==0: continue
            aggregates.append({'group_identity':list(group_key),'component_count':len(value['components']),'total_quantity_exact':decimal_text(value['quantity']),'total_notional_exact':decimal_text(value['notional']),'weighted_price_exact':decimal_text(value['notional']/value['quantity']),'formula':'SUM_EXACT_NOTIONAL_DIV_SUM_EXACT_QUANTITY'})
        aggregate=aggregates[0] if len(aggregates)==1 else None
        return {**common,'output_mode':'CANDIDATE_PRICE_TRANSITIONS','price_transitions':{'prices':price_entries,'quantities':quantity_entries,'components':components,'ungrouped_components':ungrouped,'aggregates':aggregates,'aggregate':aggregate,'grouping_keys':['symbol','one_of_order_id_position_cycle_id_trade_id','asset_when_available'],'binary_float_used':False}}
    if rule_id=='EXACT_FILL_ORDER_CYCLE_KEYS_ONLY':
        identifiers=require_semantic_entries(rule_id,semantic_field_entries(source_witnesses,('fill','order_id','position_cycle_id','trade_id','新t编号')),True)
        typed_edges=[]
        for witness in source_witnesses:
            row=witness.get('normalized_value') or {}; fill=next((row.get(key) for key in ('fill_reconstruction_id','fill_id','trade_id') if row.get(key) not in (None,'')),None); order=row.get('order_id'); cycle=row.get('position_cycle_id')
            if fill is not None and order not in (None,''): typed_edges.append({'relation_type':'FILL_TO_ORDER','source_id':str(fill),'target_id':str(order),'source_locator':witness['source_locator']})
            if fill is not None and cycle not in (None,''): typed_edges.append({'relation_type':'FILL_TO_CYCLE','source_id':str(fill),'target_id':str(cycle),'source_locator':witness['source_locator']})
        return {**common,'output_mode':'CANDIDATE_FILL_RELATIONS','fill_relation_edges':{'identifiers':identifiers,'typed_edges':sorted(typed_edges,key=canonical),'declared_cross_source_edges':semantic_relation_edges(rule_id,pairs),'fallback_fuzzy_join_used':False}}
    if rule_id=='PRESERVE_SOURCE_NAMESPACE_AND_NEVER_REPLACE_IDS':
        identifiers=require_semantic_entries(rule_id,semantic_field_entries(source_witnesses,usages=('OBJECT_ID','JOIN_KEY','SEQUENCE')),True)
        mappings=[{**entry,'preserved_identifier':entry['normalized_value'],'replacement_performed':False} for entry in identifiers]
        return {**common,'output_mode':'CANDIDATE_IDENTIFIER_MAP','identifier_mappings':mappings}
    if rule_id=='RESOLVE_ONLY_BY_DECLARED_KEYS_AND_SOURCE_BOUNDARIES':
        identifiers=require_semantic_entries(rule_id,semantic_field_entries(source_witnesses,usages=('OBJECT_ID','JOIN_KEY')),True)
        return {**common,'output_mode':'CANDIDATE_IDENTITY_RESOLUTION','identity_resolution_groups':{'identifiers':identifiers,'exact_key_edges':semantic_relation_edges(rule_id,pairs),'unjoined_bindings':join_witness.get('unjoined_bindings') or [],'cross_source_guess_used':False}}
    if rule_id=='PRESERVE_MARGIN_RISK_FIELDS_AND_UNKNOWN_NO_INFERENCE':
        margin=semantic_field_entries(source_witnesses,('margin','保证金','leverage','杠杆'))
        risk=semantic_field_entries(source_witnesses,('liquidation','爆仓','risk','风险','止损','止盈'))
        unclassified=[] if margin or risk else [entry for entry in all_entries if entry['source_field'] not in ('_sheet','_source_row')]
        require_semantic_entries(rule_id,margin+risk+unclassified,True)
        return {**common,'output_mode':'CANDIDATE_MARGIN_RISK','margin_and_risk':{'margin_fields':margin,'risk_fields':risk,'unclassified_source_fields_preserved_without_meaning_inference':unclassified,'unknown_items':unknown,'missing_values_inferred':False}}
    if rule_id=='LOCK_MARKET_IDENTITY_WINDOW_AND_MISSING_COVERAGE':
        identities=require_semantic_entries(rule_id,semantic_field_entries(source_witnesses,('symbol','品种','date','日期','market','aggtrade','kline','source_file','sha256')),True)
        times=semantic_field_entries(source_witnesses,usages=('TIME','DATE_SET'))
        windows=defaultdict(set)
        for witness in source_witnesses:
            row=witness.get('normalized_value') or {}; symbol=str(row.get('symbol') or row.get('品种') or 'UNKNOWN_SYMBOL'); source=str(row.get('market_file') or row.get('source_file') or 'UNKNOWN_SOURCE')
            for key in ('date','日期'):
                value=row.get(key); date_text=(value.get('normalized_date') if isinstance(value,dict) else value)
                if isinstance(date_text,str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}',date_text): windows[(symbol,source)].add(date_text)
        coverage=[]
        for key,dates in sorted(windows.items()):
            ordered=sorted(dates); missing=[]
            if ordered:
                cursor=datetime.fromisoformat(ordered[0]).date(); end=datetime.fromisoformat(ordered[-1]).date()
                while cursor<=end:
                    text=cursor.isoformat()
                    if text not in dates: missing.append(text)
                    cursor+=timedelta(days=1)
            coverage.append({'symbol':key[0],'source_file':key[1],'first_date':ordered[0] if ordered else None,'last_date':ordered[-1] if ordered else None,'observed_dates':ordered,'missing_dates_between_bounds':missing,'continuous_between_bounds':not missing})
        return {**common,'output_mode':'CANDIDATE_MARKET_COVERAGE','market_coverage':{'identities':identities,'windows':times,'computed_date_coverage':coverage,'join_edges':semantic_relation_edges(rule_id,pairs),'missing_coverage':unknown,'coverage_outside_observed_bounds_not_inferred':True}}
    if rule_id=='PRESERVE_MFE_MAE_BY_DECLARED_CYCLE_OR_STAGE':
        metrics=require_semantic_entries(rule_id,semantic_field_entries(source_witnesses,('mfe','mae','extreme','极值','price_lower','price_upper','amount_lower','amount_upper')),True)
        owners=semantic_field_entries(source_witnesses,('cycle','stage','周期','阶段','new_t_id','新t编号'))
        return {**common,'output_mode':'CANDIDATE_MFE_MAE','mfe_mae_groups':{'metrics':metrics,'declared_owners':owners,'cross_owner_reaggregation_performed':False}}
    if rule_id=='CLASSIFY_ACTION_ONLY_FROM_DECLARED_EVIDENCE_FIELDS':
        actions=require_semantic_entries(rule_id,semantic_field_entries(source_witnesses,('action','作用','是否','方向','reduce_only','side','type','类型','classification','分类')),True)
        evidence=semantic_field_entries(source_witnesses,usages=('EVIDENCE','LINEAGE'))
        classifications=[]
        for witness in source_witnesses:
            row=witness.get('normalized_value') or {}
            executed=next((semantic_exact_decimal(row.get(key)) for key in ('executed_quantity','fill_quantity','成交数量（精确文本）') if semantic_exact_decimal(row.get(key)) is not None),None)
            status=next((row.get(key) for key in ('order_status_standard_code','status','状态') if row.get(key) not in (None,'')),None)
            explicit=next((row.get(key) for key in ('对当前周期的仓位作用','position_effect','action','classification') if row.get(key) not in (None,'')),None)
            if explicit is not None: classification=str(explicit)
            elif executed is not None and executed!=0: classification='EXECUTED_ACTION_EFFECT_REQUIRES_POSITION_CONTEXT'
            elif status is not None: classification='ORDER_ATTEMPT_NOT_PROVEN_EXECUTED'
            else: classification='UNKNOWN_ACTION'
            classifications.append({'input_id':witness['input_id'],'source_locator':witness['source_locator'],'classification':classification,'executed_quantity_exact':decimal_text(executed) if executed is not None else None,'terminal_status':status,'one_order_multiple_fills_not_counted_as_multiple_decisions':True})
        return {**common,'output_mode':'CANDIDATE_ACTION_CLASSIFICATION','action_classifications':{'declared_action_fields':actions,'classifications':classifications,'evidence':evidence,'unstated_intent_inferred':False}}
    if rule_id=='ORDER_CONDITION_STATES_AND_EXACT_RELATIONS':
        states=require_semantic_entries(rule_id,semantic_field_entries(source_witnesses,('status','状态','trigger','terminal','cancel','expire','完成')),True)
        times=semantic_field_entries(source_witnesses,usages=('TIME',))
        ids=semantic_field_entries(source_witnesses,('order','condition','algorithm','周期','cycle'))
        events=[]; grouped=defaultdict(list); unassigned_events=[]
        for witness in source_witnesses:
            row=witness.get('normalized_value') or {}
            object_type=('CONDITION' if any(row.get(key) not in (None,'') for key in ('condition_record_id','algorithm_id')) else 'ORDER')
            identity=next((row.get(key) for key in (('condition_record_id','algorithm_id') if object_type=='CONDITION' else ('order_id',)) if row.get(key) not in (None,'')),None)
            status=next((row.get(key) for key in ('order_status_standard_code','status','terminal_type','状态') if row.get(key) not in (None,'')),None)
            executed=next((semantic_exact_decimal(row.get(key)) for key in ('executed_quantity','fill_quantity','成交数量（精确文本）') if semantic_exact_decimal(row.get(key)) is not None),None)
            lifecycle=('PARTIALLY_FILLED_THEN_TERMINATED' if executed not in (None,Decimal(0)) and str(status).upper() in {'CANCELED','CANCELLED','已取消','已撤销','撤销'} else 'TERMINAL_OR_CURRENT_STATE_PRESERVED')
            time_value=next((row.get(key) for key in ('event_time','order_update_time_utc','terminal_at','created_at','triggered_at') if row.get(key) not in (None,'')),None)
            event={'input_id':witness['input_id'],'source_locator':witness['source_locator'],'object_type':object_type,'object_identity':identity,'state':status,'time_value':time_value,'executed_quantity_exact':decimal_text(executed) if executed is not None else None,'lifecycle_classification':lifecycle,'cancel_or_expire_not_treated_as_zero_fill_without_quantity_evidence':True}
            events.append(event)
            if identity in (None,''):
                unassigned_events.append({**event,'unknown_reason':'EXACT_ORDER_OR_CONDITION_ID_REQUIRED_FOR_LIFECYCLE_GROUPING'})
            else:
                grouped[(object_type,str(identity))].append(event)
        object_lifecycles=[{'object_type':key[0],'object_identity':key[1],'events':sorted(rows,key=lambda row:(canonical(row.get('time_value')),row['source_locator'])),'event_count':len(rows)} for key,rows in sorted(grouped.items())]
        return {**common,'output_mode':'CANDIDATE_LIFECYCLE','lifecycle_events':{'events':events,'object_lifecycles':object_lifecycles,'unassigned_events':unassigned_events,'state_fields':states,'time_fields':times,'identity_fields':ids,'exact_relation_edges':semantic_relation_edges(rule_id,pairs),'unknown_relations':join_witness.get('unjoined_bindings') or []}}
    if rule_id=='DECIMAL_POSITION_BEFORE_AFTER_TRANSITION':
        transitions=[]
        for witness in source_witnesses:
            row=witness.get('normalized_value') or {}
            before=next((row.get(key) for key in ('处理前持仓数量','仓位前','position_before','position_quantity_before') if key in row),None)
            after=next((row.get(key) for key in ('处理后持仓数量','仓位后','position_after','position_quantity_after') if key in row),None)
            if before is None and after is None: continue
            b=semantic_exact_decimal(before); a=semantic_exact_decimal(after)
            transitions.append({'input_id':witness['input_id'],'source_locator':witness['source_locator'],'before':before,'after':after,'delta_exact':decimal_text(a-b) if a is not None and b is not None else None,'unknown_preserved':a is None or b is None})
        if not transitions:
            observed=semantic_field_entries(source_witnesses,('position_quantity','持仓数量','数量（精确文本）'))
            transitions=[{'input_id':entry['input_id'],'source_locator':entry['source_locator'],'before':None,'after':None,'observed_quantity':entry['normalized_value'],'delta_exact':None,'unknown_preserved':True} for entry in observed]
        require_semantic_entries(rule_id,transitions,True)
        return {**common,'output_mode':'CANDIDATE_POSITION_TRANSITION','position_transitions':transitions}
    if rule_id=='ZERO_NONZERO_ZERO_CYCLE_WITHOUT_ROW_ORDER_JOIN':
        quantity=semantic_field_entries(source_witnesses,('position_quantity','position_before','position_after','仓位前','仓位后','持仓数量','是否最终归零'))
        times=semantic_field_entries(source_witnesses,('cycle_start','cycle_end','首开','归零','持仓开始','持仓结束'))
        require_semantic_entries(rule_id,quantity+times,True)
        transitions=[]
        for witness in source_witnesses:
            row=witness.get('normalized_value') or {}
            before=next((semantic_exact_decimal(row.get(key)) for key in ('position_before','position_quantity_before','处理前持仓数量','仓位前') if semantic_exact_decimal(row.get(key)) is not None),None)
            after=next((semantic_exact_decimal(row.get(key)) for key in ('position_after','position_quantity_after','处理后持仓数量','仓位后') if semantic_exact_decimal(row.get(key)) is not None),None)
            seq=next((semantic_exact_decimal(row.get(key)) for key in ('technical_sequence','event_sequence','事件顺序','fill_time_ms') if semantic_exact_decimal(row.get(key)) is not None),None)
            if before is not None and after is not None and seq is not None:
                account=str(row.get('account_id') or row.get('wallet') or 'SOURCE:'+witness['input_id']); symbol=str(row.get('symbol') or ''); position_side=str(row.get('position_side') or row.get('仓位方向') or '')
                if not symbol or not position_side: continue
                partition=(account,symbol,position_side)
                transitions.append({'partition':partition,'sequence_exact':seq,'before':before,'after':after,'source_locator':witness['source_locator']})
        transitions.sort(key=lambda row:(row['partition'],row['sequence_exact'],row['source_locator']))
        cycles=[]; partitions=[]
        for partition,rows in sorted(((key,[row for row in transitions if row['partition']==key]) for key in {row['partition'] for row in transitions}),key=lambda item:item[0]):
            active=None; previous_after=None; continuity=True; part_cycles=[]
            for transition in rows:
                if previous_after is not None and transition['before']!=previous_after: continuity=False
                previous_after=transition['after']
                if active is None and transition['before']==0 and transition['after']!=0:
                    active={'partition':list(partition),'start_sequence_exact':decimal_text(transition['sequence_exact']),'transition_count':1,'direction':'LONG_OR_POSITIVE' if transition['after']>0 else 'SHORT_OR_NEGATIVE','end_sequence_exact':None,'complete':False}
                elif active is not None:
                    active['transition_count']+=1
                    if transition['after']==0:
                        active['end_sequence_exact']=decimal_text(transition['sequence_exact']); active['complete']=True; part_cycles.append(active); active=None
                    elif transition['before']==0: raise RuntimeError('SEMANTIC_CYCLE_OVERLAPPING_START')
            if active is not None: part_cycles.append(active)
            if len(rows)>1 and not continuity: raise RuntimeError('SEMANTIC_CYCLE_QUANTITY_CONTINUITY_BROKEN')
            cycles.extend(part_cycles); partitions.append({'partition':list(partition),'transition_count':len(rows),'quantity_continuity_passed':continuity,'cycle_count':len(part_cycles)})
        return {**common,'output_mode':'CANDIDATE_CYCLE_BOUNDARY','cycle_boundaries':{'quantity_evidence':quantity,'boundary_times':times,'transition_count':len(transitions),'partitions':partitions,'cycles':cycles,'partition_keys':['account_or_wallet','symbol','position_side'],'exact_key_edges':semantic_relation_edges(rule_id,pairs),'explicit_technical_sequence_required':True,'row_order_grouping_used':False}}
    if rule_id=='PRESERVE_REALIZED_PNL_COMPONENTS_BY_EXACT_FILL_OR_CYCLE':
        pnl=require_semantic_entries(rule_id,semantic_field_entries(source_witnesses,('realized_pnl','盈亏','cycle_cash_result','commission','fee','funding')),True)
        owners=semantic_field_entries(source_witnesses,('fill','order_id','cycle','周期','trade_id'))
        components=defaultdict(list); unassigned=[]
        for witness in source_witnesses:
            row=witness.get('normalized_value') or {}
            owner_type=next((key for key in ('fill_reconstruction_id','fill_id','position_cycle_id','cycle_id','trade_id') if row.get(key) not in (None,'')),None)
            owner=str(row.get(owner_type)) if owner_type else 'UNASSIGNED'
            currency=next((str(row.get(key)) for key in ('asset','currency','margin_asset','币种','手续费资产') if row.get(key) not in (None,'')),'UNKNOWN_CURRENCY')
            value=next((semantic_exact_decimal(row.get(key)) for key in ('realized_pnl','已实现盈亏（来源事实）','cycle_cash_result') if semantic_exact_decimal(row.get(key)) is not None),None)
            if value is not None:
                component_id_type=next((key for key in ('pnl_component_id','event_id','fill_reconstruction_id','fill_id') if row.get(key) not in (None,'')),None)
                component_id=str(row.get(component_id_type)) if component_id_type else None
                if owner=='UNASSIGNED' or currency=='UNKNOWN_CURRENCY' or component_id is None:
                    unassigned.append({'source_locator':witness['source_locator'],'owner_type':owner_type,'owner_id':owner,'currency':currency,'component_id':component_id,'value_exact':decimal_text(value),'unknown_reason':'EXACT_COMPONENT_OWNER_CURRENCY_AND_ID_REQUIRED_FOR_REALIZED_PNL_AGGREGATION'})
                else:
                    components[(owner_type,owner,currency,component_id)].append({'source_locator':witness['source_locator'],'value_exact':decimal_text(value)})
        deduplicated=[]; conflicts=[]; grouped_totals=defaultdict(lambda:{'values':[],'total':Decimal(0),'component_ids':[]})
        for key,rows in sorted(components.items()):
            unique_values=sorted({row['value_exact'] for row in rows},key=semantic_exact_decimal)
            if len(unique_values)!=1:
                conflicts.append({'owner_type':key[0],'owner_id':key[1],'currency':key[2],'component_id':key[3],'claims':rows,'conflict_reason':'SAME_EXACT_COMPONENT_ID_HAS_DIFFERENT_VALUES_NO_AGGREGATION'})
                continue
            value=semantic_exact_decimal(unique_values[0]); owner_key=(key[0],key[1],key[2]); grouped_totals[owner_key]['values'].append(unique_values[0]); grouped_totals[owner_key]['total']+=value; grouped_totals[owner_key]['component_ids'].append(key[3])
            deduplicated.append({'owner_type':key[0],'owner_id':key[1],'currency':key[2],'component_id':key[3],'value_exact':unique_values[0],'source_locators':sorted(row['source_locator'] for row in rows),'source_claim_count':len(rows),'counted_once':True})
        totals=[{'owner_type':key[0],'owner_id':key[1],'currency':key[2],'component_ids':value['component_ids'],'component_values':value['values'],'realized_pnl_total_exact':decimal_text(value['total'])} for key,value in sorted(grouped_totals.items())]
        return {**common,'output_mode':'CANDIDATE_REALIZED_PNL','realized_pnl_components':{'values':pnl,'owners':owners,'deduplicated_components':deduplicated,'conflicting_components':conflicts,'exact_owner_currency_totals':totals,'unassigned_components':unassigned,'fees_and_funding_excluded':True,'cross_source_double_count_prevented':True,'aggregation_requires_exact_component_identity':True}}
    if rule_id=='REQUIRE_REFERENTIAL_AND_QUANTITY_CHECKS_NO_SILENT_REPAIR':
        checks=[check for witness in source_witnesses for check in witness.get('field_checks') or []]
        quantity=semantic_field_entries(source_witnesses,('quantity','数量','仓位前','仓位后','count','总数'))
        quantity_findings=[]; order_rows={}; fill_rows=defaultdict(list)
        for witness in source_witnesses:
            row=witness.get('normalized_value') or {}
            declared=next((semantic_exact_decimal(row.get(key)) for key in ('order_executed_quantity','executed_quantity') if semantic_exact_decimal(row.get(key)) is not None),None)
            fills=row.get('fill_quantities')
            if declared is not None and isinstance(fills,list):
                parsed=[semantic_exact_decimal(value) for value in fills]
                if any(value is None for value in parsed): raise RuntimeError('SEMANTIC_INTEGRITY_FILL_QUANTITY_NOT_DECIMAL')
                total=sum(parsed,Decimal(0)); quantity_findings.append({'declared_exact':decimal_text(declared),'fill_sum_exact':decimal_text(total),'pass':declared==total,'difference_exact':decimal_text(declared-total)})
            order_id=row.get('order_id'); record_type=str(row.get('record_type') or '').upper()
            if order_id not in (None,'') and declared is not None and record_type=='ORDER': order_rows[str(order_id)]=declared
            fill_quantity=semantic_exact_decimal(row.get('fill_quantity'))
            if order_id not in (None,'') and fill_quantity is not None and record_type=='FILL': fill_rows[str(order_id)].append(fill_quantity)
        cross_row=[]
        for order_id,declared in sorted(order_rows.items()):
            if order_id not in fill_rows: continue
            total=sum(fill_rows[order_id],Decimal(0)); cross_row.append({'order_id':order_id,'declared_exact':decimal_text(declared),'fill_sum_exact':decimal_text(total),'difference_exact':decimal_text(declared-total),'pass':declared==total})
        orphan_fill_order_ids=sorted(set(fill_rows)-set(order_rows))
        return {**common,'output_mode':'CANDIDATE_INTEGRITY','integrity_findings':{'field_checks':checks,'all_field_checks_pass':all(check.get('pass') for check in checks),'exact_relation_edges':semantic_relation_edges(rule_id,pairs),'unjoined_bindings':join_witness.get('unjoined_bindings') or [],'quantity_evidence':quantity,'quantity_conservation_checks':quantity_findings,'cross_row_order_fill_checks':cross_row,'orphan_fill_order_ids':orphan_fill_order_ids,'silent_repair_performed':False}}
    if rule_id=='PRESERVE_SCREENSHOT_CONDITION_CYCLE_SOURCE_CHAIN':
        sources=require_semantic_entries(rule_id,semantic_field_entries(source_witnesses,('screenshot','截图','安卓','source_path','来源文件','证据定位','condition','周期','cycle')),True)
        return {**common,'output_mode':'CANDIDATE_SCREENSHOT_LINEAGE','screenshot_lineage':{'source_nodes':sources,'exact_relation_edges':semantic_relation_edges(rule_id,pairs),'ocr_treated_as_source_not_fact_override':True}}
    if rule_id=='SEPARATE_SIDE_POSITION_SIDE_AND_POSITION_EFFECT':
        side=require_semantic_entries(rule_id,semantic_field_entries(source_witnesses,('side','方向','买卖方向','仓位方向')),True)
        order_side=[entry for entry in side if entry['source_field'].lower() in {'side','order_side','buy/sell原始方向'} or entry['source_field'] in {'方向','买卖方向'}]
        position_side=[entry for entry in side if entry['source_field'].lower() in {'position_side'} or '仓位' in entry['source_field']]
        effect=semantic_field_entries(source_witnesses,('作用','reduce_only','是否改变持仓','是否最终归零','是否部分减仓'))
        return {**common,'output_mode':'CANDIDATE_SIDE_LAYERS','side_layers':{'order_side':order_side,'position_side':position_side,'position_effect':effect,'layers_collapsed':False}}
    if rule_id=='STABLE_ID_WITH_SOURCE_NAMESPACE_PRESERVED':
        identifiers=require_semantic_entries(rule_id,semantic_field_entries(source_witnesses,usages=('OBJECT_ID','JOIN_KEY','SEQUENCE','LINEAGE')),True)
        stable=[]
        for entry in identifiers:
            source_hash=hashlib.sha256(canonical({'input_id':entry['input_id'],'locator':entry['source_locator']}).encode('utf-8')).hexdigest()
            stable.append({**entry,'stable_identifier':stable_id('SRCID',source_hash,entry['source_locator'],canonical(entry['normalized_value'])),'source_namespace':entry['input_id']})
        return {**common,'output_mode':'CANDIDATE_STABLE_IDENTIFIERS','stable_identifiers':stable}
    if rule_id in {'STOP_LOSS_LIFECYCLE_PRESERVE_UNKNOWN_RELATION','TAKE_PROFIT_LIFECYCLE_PRESERVE_UNKNOWN_RELATION'}:
        kind='STOP_LOSS' if rule_id.startswith('STOP_LOSS') else 'TAKE_PROFIT'
        tokens=('stop_loss','止损','sl') if kind=='STOP_LOSS' else ('take_profit','止盈','tp')
        possible_role=semantic_field_entries(source_witnesses,tokens+('condition_role','condition_type','条件作用类别'))
        def matches_kind(entry):
            text=canonical(entry.get('normalized_value')).lower()
            return any(token in text for token in (('stop','止损','sl') if kind=='STOP_LOSS' else ('take_profit','止盈','tp')))
        role=[entry for entry in possible_role if matches_kind(entry)]
        # State/time evidence may live in a second source joined by an exact
        # condition identifier, so do not require it to share the role row.
        states=require_semantic_entries(rule_id,semantic_field_entries(source_witnesses,('status','terminal','trigger','状态','完成','取消','过期')),True)
        times=semantic_field_entries(source_witnesses,usages=('TIME',))
        key='stop_loss_lifecycle' if kind=='STOP_LOSS' else 'take_profit_lifecycle'
        kind_unknown=[] if role else [{'status':'UNKNOWN','reason':'SELECTED_BOUNDED_WITNESS_DOES_NOT_CONFIRM_REQUESTED_PROTECTION_KIND','missing_evidence':'MATCHING_CONDITION_ROLE_OR_TYPE','scope':item['object_id']}]
        return {**common,'output_mode':'CANDIDATE_PROTECTION_LIFECYCLE',key:{'protection_kind':kind,'protection_kind_confirmed_from_source':bool(role),'role_evidence':role,'state_evidence':states,'time_evidence':times,'exact_relation_edges':semantic_relation_edges(rule_id,pairs),'unknown_relations':(join_witness.get('unjoined_bindings') or [])+kind_unknown,'opposite_protection_kind_excluded':True}}
    if rule_id=='SORT_FOR_DISPLAY_AND_PRESERVE_EQUAL_TIME_PARALLEL':
        times=require_semantic_entries(rule_id,semantic_field_entries(source_witnesses,usages=('TIME',)),True)
        groups=defaultdict(list)
        for entry in times:
            value=entry['normalized_value']; domain=(value.get('representation') if isinstance(value,dict) else 'RAW_TIME_DOMAIN')
            key=canonical({'domain':domain,'value':value})
            groups[key].append(entry)
        ordered=[{'time_identity':json.loads(key),'events':sorted(entries,key=canonical),'parallel_when_multiple':len(entries)>1} for key,entries in sorted(groups.items())]
        return {**common,'output_mode':'CANDIDATE_TIMELINE','timeline_groups':{'comparable_domain_groups':ordered,'display_order_only':True,'equal_time_unique_order_inferred':False,'cross_domain_chronology_inferred':False}}
    if rule_id=='BOUND_EQUITY_ANCHORS_AND_PRESERVE_TIME_GAPS':
        anchors=require_semantic_entries(rule_id,semantic_field_entries(source_witnesses,('equity','balance','资产','余额','anchor','快照','滚动值','amount','金额','planned_snapshot','user_confirmed')),True)
        times=semantic_field_entries(source_witnesses,usages=('TIME',))
        gaps=semantic_field_entries(source_witnesses,('gap','差额','未分配','unknown'))
        return {**common,'output_mode':'CANDIDATE_EQUITY_INTERVALS','equity_anchor_intervals':{'anchors':anchors,'time_boundaries':times,'unallocated_or_unknown_gaps':gaps+unknown,'interpolation_performed':False}}
    if rule_id=='PRESERVE_ORIGINAL_TIME_TIMEZONE_AND_PRECISION':
        times=require_semantic_entries(rule_id,semantic_field_entries(source_witnesses,usages=('TIME',)),True)
        return {**common,'output_mode':'CANDIDATE_NORMALIZED_TIMES','normalized_times':[{'input_id':entry['input_id'],'source_locator':entry['source_locator'],'source_field':entry['source_field'],'raw_value':entry['raw_value'],'normalized_value':entry['normalized_value'],'timezone_inferred':False} for entry in times]}
    if rule_id=='PRESERVE_VERSION_CORRECTION_AND_SOURCE_IDENTITY_LINEAGE':
        versions=require_semantic_entries(rule_id,semantic_field_entries(source_witnesses,('version','freeze','sha256','source_file','来源文件','修正版','mapping_version')),True)
        return {**common,'output_mode':'CANDIDATE_VERSION_LINEAGE','version_lineage':{'version_and_source_nodes':versions,'exact_relation_edges':semantic_relation_edges(rule_id,pairs),'latest_or_correct_version_inferred':False}}
    raise RuntimeError('SEMANTIC_RULE_CALLABLE_NOT_IMPLEMENTED:'+rule_id)

def _make_semantic_rule_callable(rule_id):
    """Bind one registered rule to one callable object while sharing safe utilities."""
    def execute(item,source_witnesses,join_witness):
        return semantic_payload(rule_id,item,source_witnesses,join_witness)
    execute.__name__=semantic_callable_id(rule_id)
    execute.__qualname__=execute.__name__
    return execute

SEMANTIC_RULE_CALLABLES={
    rule_id:_make_semantic_rule_callable(rule_id)
    for rule_id in sorted(SEMANTIC_RULE_PRIMARY_OUTPUT_KEY)
}

def validate_semantic_rule_payload(rule_id,payload):
    """Validate the business meaning of one rule, not merely a non-empty wrapper."""
    if payload.get('semantic_rule_id')!=rule_id or payload.get('callable_id')!=semantic_callable_id(rule_id):
        raise RuntimeError('SEMANTIC_PAYLOAD_IDENTITY_INVALID:'+rule_id)
    primary=SEMANTIC_RULE_PRIMARY_OUTPUT_KEY[rule_id]
    if primary not in payload:
        raise RuntimeError('SEMANTIC_PAYLOAD_PRIMARY_OUTPUT_MISSING:'+rule_id)
    value=payload[primary]
    if rule_id in {
        'ZERO_OBJECTIVE_OUTPUT_FOR_ANALYSIS_OR_COUNTERFACTUAL','ZERO_OBJECTIVE_OUTPUT_FOR_FUTURE_PRODUCT_FORMAT',
        'ZERO_OBJECTIVE_OUTPUT_FOR_USER_REASON','ZERO_OBJECTIVE_OUTPUT_FOR_USER_INTERFACE_PRODUCT',
    }:
        if not isinstance(value,dict) or value.get('objective_fact_output_count')!=0 or payload.get('output_mode')!='ZERO_OBJECTIVE_OUTPUT':
            raise RuntimeError('SEMANTIC_BOUNDARY_ZERO_OUTPUT_INVALID:'+rule_id)
    elif rule_id=='USER_ACCEPTANCE_GATE_BEFORE_STAGE_AGGREGATION':
        if value.get('passed') is not False or value.get('production_output_count')!=0:
            raise RuntimeError('SEMANTIC_USER_ACCEPTANCE_GATE_INVALID')
    elif rule_id=='ACTIVE_COPY_SCOPE_EXACT_SOURCE_CLASSIFICATION':
        if set(value)!={'USER_ACTIVE','COPY_OR_AUTOMATED','NON_TRADE_CASH_OR_OTHER','UNRESOLVED'}:
            raise RuntimeError('SEMANTIC_SCOPE_PARTITION_SET_INVALID')
        locators=[row['source_locator'] for rows in value.values() for row in rows]
        if len(locators)!=len(set(locators)):
            raise RuntimeError('SEMANTIC_SCOPE_RECORD_ASSIGNED_TO_MULTIPLE_PARTITIONS')
    elif rule_id=='EXACT_DECLARED_KEY_RELATION_NO_CAUSAL_INFERENCE':
        if value.get('adjacency_or_causality_inferred') is not False:
            raise RuntimeError('SEMANTIC_REVERSE_LINK_CAUSAL_INFERENCE_DETECTED')
        if bool(value.get('edges'))!=bool(value.get('qualification_evidence')):
            raise RuntimeError('SEMANTIC_REVERSE_LINK_OBJECTIVE_QUALIFICATION_MISMATCH')
    elif rule_id=='EXACT_TRANSFER_PAIR_KEYS_PRESERVE_UNMATCHED':
        if value.get('deduplication_key_is_explicit_identity_not_amount_or_time') is not True or value.get('net_check_partition_keys')!=['internal_transfer_pair_id','currency']:
            raise RuntimeError('SEMANTIC_CASH_DEDUPLICATION_KEY_INVALID')
        for check in value.get('transfer_net_checks') or []:
            if check.get('currency') in (None,'') or any(component.get('currency')!=check.get('currency') for component in check.get('components') or []):
                raise RuntimeError('SEMANTIC_TRANSFER_CURRENCY_PARTITION_INVALID')
            expected=semantic_exact_decimal(check.get('in_exact'))+semantic_exact_decimal(check.get('out_exact'))
            if semantic_exact_decimal(check.get('net_exact'))!=expected or check.get('external_wealth_effect_zero') is not (expected==0):
                raise RuntimeError('SEMANTIC_TRANSFER_NET_CHECK_INVALID')
        if any(row.get('currency') not in (None,'') for row in value.get('unknown_currency_components') or []):
            raise RuntimeError('SEMANTIC_TRANSFER_UNKNOWN_CURRENCY_CLASSIFICATION_INVALID')
    elif rule_id=='EXACT_CONDITION_ORDER_FILL_CYCLE_EDGES_ONLY':
        if value.get('similar_text_or_row_order_edges_created') is not False:
            raise RuntimeError('SEMANTIC_CONDITION_GRAPH_FUZZY_EDGE_DETECTED')
    elif rule_id=='SEPARATE_FACT_USER_STATEMENT_AI_INTERPRETATION_AND_STATUS':
        if value.get('layers_merged') is not False or not {'facts','user_statements','ai_interpretations','statuses'}.issubset(value):
            raise RuntimeError('SEMANTIC_INFORMATION_LAYERS_COLLAPSED')
    elif rule_id=='PRESERVE_FEE_PNL_FUNDING_COMPONENTS_WITH_CURRENCY':
        if value.get('components_summed_across_sources') is not False:
            raise RuntimeError('SEMANTIC_FINANCIAL_COMPONENTS_UNSAFE_SUM')
    elif rule_id=='DECIMAL_FILL_AND_WEIGHTED_PRICE_TRANSITION_NO_FLOAT':
        if value.get('binary_float_used') is not False:
            raise RuntimeError('SEMANTIC_WEIGHTED_PRICE_FLOAT_USED')
        aggregates=value.get('aggregates') or []; components=value.get('components') or []
        grouped_components=defaultdict(list)
        for component in components:
            group_identity=tuple(component.get('group_identity') or [])
            if len(group_identity)==4 and group_identity[0] and group_identity[1] and group_identity[2]:
                grouped_components[group_identity].append(component)
        if {tuple(row.get('group_identity') or []) for row in aggregates}!=set(grouped_components):
            raise RuntimeError('SEMANTIC_WEIGHTED_PRICE_AGGREGATE_GROUP_SET_INVALID')
        for aggregate in aggregates:
            group_identity=tuple(aggregate.get('group_identity') or [])
            group=grouped_components[group_identity]
            qty=sum((semantic_exact_decimal(row['quantity_exact']) for row in group),Decimal(0))
            notional=sum((semantic_exact_decimal(row['notional_exact']) for row in group),Decimal(0))
            if (
                qty==0
                or semantic_exact_decimal(aggregate.get('total_quantity_exact'))!=qty
                or semantic_exact_decimal(aggregate.get('total_notional_exact'))!=notional
                or semantic_exact_decimal(aggregate.get('weighted_price_exact'))!=notional/qty
                or int(aggregate.get('component_count',-1))!=len(group)
                or aggregate.get('formula')!='SUM_EXACT_NOTIONAL_DIV_SUM_EXACT_QUANTITY'
            ):
                raise RuntimeError('SEMANTIC_WEIGHTED_PRICE_FORMULA_INVALID')
        expected_single=aggregates[0] if len(aggregates)==1 else None
        if value.get('aggregate')!=expected_single:
            raise RuntimeError('SEMANTIC_WEIGHTED_PRICE_SINGLE_AGGREGATE_ALIAS_INVALID')
    elif rule_id=='EXACT_FILL_ORDER_CYCLE_KEYS_ONLY':
        if value.get('fallback_fuzzy_join_used') is not False:
            raise RuntimeError('SEMANTIC_FILL_LINK_FUZZY_JOIN_DETECTED')
    elif rule_id=='PRESERVE_SOURCE_NAMESPACE_AND_NEVER_REPLACE_IDS':
        if any(row.get('replacement_performed') is not False or row.get('preserved_identifier')!=row.get('normalized_value') for row in value):
            raise RuntimeError('SEMANTIC_IDENTIFIER_REPLACEMENT_DETECTED')
    elif rule_id=='RESOLVE_ONLY_BY_DECLARED_KEYS_AND_SOURCE_BOUNDARIES':
        if value.get('cross_source_guess_used') is not False:
            raise RuntimeError('SEMANTIC_IDENTITY_CROSS_SOURCE_GUESS_DETECTED')
    elif rule_id=='PRESERVE_MARGIN_RISK_FIELDS_AND_UNKNOWN_NO_INFERENCE':
        if value.get('missing_values_inferred') is not False:
            raise RuntimeError('SEMANTIC_MARGIN_RISK_INFERENCE_DETECTED')
    elif rule_id=='LOCK_MARKET_IDENTITY_WINDOW_AND_MISSING_COVERAGE':
        if not {'identities','windows','missing_coverage'}.issubset(value):
            raise RuntimeError('SEMANTIC_MARKET_COVERAGE_FIELDS_MISSING')
    elif rule_id=='PRESERVE_MFE_MAE_BY_DECLARED_CYCLE_OR_STAGE':
        if value.get('cross_owner_reaggregation_performed') is not False:
            raise RuntimeError('SEMANTIC_MFE_MAE_CROSS_OWNER_AGGREGATION')
    elif rule_id=='CLASSIFY_ACTION_ONLY_FROM_DECLARED_EVIDENCE_FIELDS':
        if value.get('unstated_intent_inferred') is not False or not isinstance(value.get('classifications'),list):
            raise RuntimeError('SEMANTIC_ACTION_INTENT_INFERENCE_DETECTED')
    elif rule_id=='ORDER_CONDITION_STATES_AND_EXACT_RELATIONS':
        if not isinstance(value.get('events'),list) or any(row.get('cancel_or_expire_not_treated_as_zero_fill_without_quantity_evidence') is not True for row in value['events']):
            raise RuntimeError('SEMANTIC_LIFECYCLE_TERMINAL_STATE_INVALID')
        if any(row.get('object_identity') in (None,'','None') for row in value.get('object_lifecycles') or []):
            raise RuntimeError('SEMANTIC_LIFECYCLE_UNASSIGNED_OBJECT_GROUPED')
        unassigned=value.get('unassigned_events') or []
        if any(row.get('object_identity') not in (None,'') or not row.get('unknown_reason') for row in unassigned):
            raise RuntimeError('SEMANTIC_LIFECYCLE_UNASSIGNED_EVENT_INVALID')
    elif rule_id=='DECIMAL_POSITION_BEFORE_AFTER_TRANSITION':
        for row in value:
            before=semantic_exact_decimal(row.get('before')); after=semantic_exact_decimal(row.get('after'))
            if before is not None and after is not None and semantic_exact_decimal(row.get('delta_exact'))!=after-before:
                raise RuntimeError('SEMANTIC_POSITION_DELTA_INVALID')
    elif rule_id=='ZERO_NONZERO_ZERO_CYCLE_WITHOUT_ROW_ORDER_JOIN':
        if value.get('row_order_grouping_used') is not False or value.get('explicit_technical_sequence_required') is not True:
            raise RuntimeError('SEMANTIC_CYCLE_ROW_ORDER_GROUPING_DETECTED')
        if any(row.get('complete') and row.get('end_sequence_exact') is None for row in value.get('cycles') or []):
            raise RuntimeError('SEMANTIC_CYCLE_END_MISSING')
    elif rule_id=='PRESERVE_REALIZED_PNL_COMPONENTS_BY_EXACT_FILL_OR_CYCLE':
        if value.get('fees_and_funding_excluded') is not True or value.get('cross_source_double_count_prevented') is not True or value.get('aggregation_requires_exact_component_identity') is not True:
            raise RuntimeError('SEMANTIC_REALIZED_PNL_COMPONENT_CONTAMINATION')
        component_ids=[]
        for component in value.get('deduplicated_components') or []:
            if component.get('counted_once') is not True or not component.get('component_id') or not component.get('source_locators'):
                raise RuntimeError('SEMANTIC_REALIZED_PNL_DEDUPLICATED_COMPONENT_INVALID')
            component_ids.append((component.get('owner_type'),component.get('owner_id'),component.get('currency'),component.get('component_id')))
        if len(component_ids)!=len(set(component_ids)):
            raise RuntimeError('SEMANTIC_REALIZED_PNL_COMPONENT_DOUBLE_COUNTED')
        conflicted={(row.get('owner_type'),row.get('owner_id'),row.get('currency'),row.get('component_id')) for row in value.get('conflicting_components') or []}
        if conflicted & set(component_ids):
            raise RuntimeError('SEMANTIC_REALIZED_PNL_CONFLICT_AGGREGATED')
        for row in value.get('exact_owner_currency_totals') or []:
            total=sum((semantic_exact_decimal(v) for v in row['component_values']),Decimal(0))
            if semantic_exact_decimal(row['realized_pnl_total_exact'])!=total or len(row.get('component_ids') or [])!=len(row['component_values']):
                raise RuntimeError('SEMANTIC_REALIZED_PNL_TOTAL_INVALID')
    elif rule_id=='REQUIRE_REFERENTIAL_AND_QUANTITY_CHECKS_NO_SILENT_REPAIR':
        if value.get('silent_repair_performed') is not False:
            raise RuntimeError('SEMANTIC_INTEGRITY_SILENT_REPAIR_DETECTED')
        for row in value.get('quantity_conservation_checks') or []:
            if row.get('pass') is not (semantic_exact_decimal(row['difference_exact'])==0):
                raise RuntimeError('SEMANTIC_INTEGRITY_RESULT_INVALID')
    elif rule_id=='PRESERVE_SCREENSHOT_CONDITION_CYCLE_SOURCE_CHAIN':
        if value.get('ocr_treated_as_source_not_fact_override') is not True:
            raise RuntimeError('SEMANTIC_SCREENSHOT_OCR_FACT_OVERRIDE')
    elif rule_id=='SEPARATE_SIDE_POSITION_SIDE_AND_POSITION_EFFECT':
        if value.get('layers_collapsed') is not False:
            raise RuntimeError('SEMANTIC_SIDE_LAYER_COLLAPSE')
        order_fields={(row['input_id'],row['source_locator'],row['source_field']) for row in value.get('order_side') or []}
        position_fields={(row['input_id'],row['source_locator'],row['source_field']) for row in value.get('position_side') or []}
        if order_fields & position_fields:
            raise RuntimeError('SEMANTIC_SIDE_LAYER_FIELD_OVERLAP')
    elif rule_id=='STABLE_ID_WITH_SOURCE_NAMESPACE_PRESERVED':
        if any(not row.get('source_namespace') or not row.get('stable_identifier') for row in value):
            raise RuntimeError('SEMANTIC_STABLE_ID_NAMESPACE_MISSING')
    elif rule_id in {'STOP_LOSS_LIFECYCLE_PRESERVE_UNKNOWN_RELATION','TAKE_PROFIT_LIFECYCLE_PRESERVE_UNKNOWN_RELATION'}:
        if value.get('protection_kind') not in {'STOP_LOSS','TAKE_PROFIT'} or 'unknown_relations' not in value or value.get('opposite_protection_kind_excluded') is not True:
            raise RuntimeError('SEMANTIC_PROTECTION_LIFECYCLE_INVALID')
    elif rule_id=='SORT_FOR_DISPLAY_AND_PRESERVE_EQUAL_TIME_PARALLEL':
        if value.get('equal_time_unique_order_inferred') is not False or value.get('display_order_only') is not True:
            raise RuntimeError('SEMANTIC_TIMELINE_UNIQUE_ORDER_INFERRED')
    elif rule_id=='BOUND_EQUITY_ANCHORS_AND_PRESERVE_TIME_GAPS':
        if value.get('interpolation_performed') is not False:
            raise RuntimeError('SEMANTIC_EQUITY_INTERPOLATION_DETECTED')
    elif rule_id=='PRESERVE_ORIGINAL_TIME_TIMEZONE_AND_PRECISION':
        if any(row.get('timezone_inferred') is not False or 'raw_value' not in row or 'normalized_value' not in row for row in value):
            raise RuntimeError('SEMANTIC_TIME_INFERENCE_OR_ORIGINAL_LOSS')
    elif rule_id=='PRESERVE_VERSION_CORRECTION_AND_SOURCE_IDENTITY_LINEAGE':
        if value.get('latest_or_correct_version_inferred') is not False:
            raise RuntimeError('SEMANTIC_VERSION_INFERENCE_DETECTED')
    else:
        raise RuntimeError('SEMANTIC_PAYLOAD_VALIDATOR_NOT_IMPLEMENTED:'+rule_id)
    return True

def _synthetic_semantic_witness(input_id,index,row,usage_overrides=None):
    """Create an explicitly synthetic witness for operator semantics tests only."""
    usage_overrides=usage_overrides or {}
    rules=[]
    for field in sorted(row):
        lowered=field.lower()
        usage=usage_overrides.get(field)
        if usage is None:
            if any(token in lowered for token in ('time','date','created','terminal','triggered')): usage='TIME'
            elif field.endswith('_id') or any(token in lowered for token in ('id','编号')): usage='OBJECT_ID'
            elif any(token in lowered for token in ('quantity','price','amount','pnl','fee','commission','mfe','mae','margin','equity','balance')): usage='MEASURE'
            elif any(token in lowered for token in ('status','side','type','classification','role')): usage='CLASSIFICATION'
            else: usage='SOURCE_VALUE'
        rules.append({'source_field':field,'usage':usage})
    return {
        'input_id':input_id,'selected_object_index':index,
        'source_locator':f'SYNTHETIC_SEMANTIC_FIXTURE:{input_id}:{index}',
        'selected_row_sha256':hashlib.sha256(canonical(row).encode('utf-8')).hexdigest(),
        'relation_participation':'SYNTHETIC_EXACT_DECLARED_KEY_WITNESS',
        'raw_value':json.loads(canonical(row)),'normalized_value':json.loads(canonical(row)),
        'field_checks':[{'source_field':field,'check':FIELD_RESULT_CHECK,'pass':True} for field in sorted(row)],
        'applied_field_rules':rules,
    }

def semantic_rule_synthetic_fixture():
    """One non-business, synthetic multi-event fixture shared by the 33 rule tests."""
    rows=[
        {
            '交易来源分类':'个人主动','record_type':'ORDER','source_business_type':'USER_ACTIVE','account_id':'SYNTHETIC-ACCOUNT',
            'canonical_economic_event_id':'E-1','internal_transfer_pair_id':'PAIR-1',
            'in_amount_signed_exact':'5','source_record_id':'SRC-1',
            'condition_record_id':'COND-1','algorithm_id':'ALG-1','generated_order_id':'ORDER-1','order_id':'ORDER-1',
            'fill_reconstruction_id':'FILL-1','position_cycle_id':'CYCLE-1','trade_id':'TRADE-1',
            'user_statement':'SYNTHETIC_USER_TEXT','ai_interpretation':'SYNTHETIC_AI_TEXT','evidence_status':'DIRECT',
            'fee':'-1','realized_pnl':'5','funding':'-0.5','asset':'USDT',
            'fill_price':'100','fill_quantity':'1','notional':'100',
            'margin':'20','leverage':'5','risk':'SYNTHETIC_LOW',
            'symbol':'BTCUSDT','market_file':'synthetic-market.csv','source_file':'synthetic-source.csv','sha256':'1'*64,
            'event_time':'2026-01-01T00:00:00+00:00','date':'2026-01-01','mfe':'10','mae':'-5',
            'action':'OPEN_POSITION','side':'BUY','position_side':'LONG','position_effect':'OPEN',
            'status':'CANCELED','executed_quantity':'3','order_executed_quantity':'2','fill_quantities':['1','1'],
            'position_before':'0','position_after':'2','technical_sequence':'1',
            'previous_cycle_end_quantity':'0','next_cycle_start_quantity':'-1','previous_direction':'LONG','next_direction':'SHORT',
            'screenshot_path':'synthetic.png','condition_role':'STOP_LOSS','condition_type':'STOP_MARKET',
            'mapping_version':'SYNTHETIC-V2','previous_version':'SYNTHETIC-V1',
            'planned_snapshot_amount_usdt':'1000','unknown_gap':'5',
        },
        {
            '交易来源分类':'自动跟单','record_type':'FILL','source_business_type':'COPY','account_id':'SYNTHETIC-ACCOUNT',
            'canonical_economic_event_id':'E-1','internal_transfer_pair_id':'PAIR-1','source_record_id':'SRC-2',
            'out_amount_signed_exact':'-5',
            'condition_record_id':'COND-1','generated_order_id':'ORDER-1','order_id':'ORDER-1',
            'fill_reconstruction_id':'FILL-2','position_cycle_id':'CYCLE-1','trade_id':'TRADE-1',
            'fee':'-0.5','realized_pnl':'-2','asset':'USDT','symbol':'BTCUSDT','fill_price':'103','fill_quantity':'2','notional':'206',
            'event_time':'2026-01-01T00:00:00+00:00','date':'2026-01-03','mfe':'8','mae':'-3',
            'side':'BUY','position_side':'LONG','position_effect':'INCREASE','status':'FILLED',
            'position_before':'2','position_after':'5','technical_sequence':'2',
            'screenshot_path':'synthetic.png','condition_role':'TAKE_PROFIT','condition_type':'TAKE_PROFIT_MARKET',
            'mapping_version':'SYNTHETIC-V2','planned_snapshot_amount_usdt':'1005',
        },
        {
            '交易来源分类':'个人主动','record_type':'POSITION','source_business_type':'USER_ACTIVE','account_id':'SYNTHETIC-ACCOUNT',
            'source_record_id':'SRC-3','order_id':'ORDER-2','fill_reconstruction_id':'FILL-3',
            'position_cycle_id':'CYCLE-1','trade_id':'TRADE-1','symbol':'BTCUSDT','event_time':'2026-01-01T00:00:01+00:00',
            'side':'SELL','position_side':'LONG','position_effect':'CLOSE','status':'FILLED',
            'position_before':'5','position_after':'0','technical_sequence':'3','mapping_version':'SYNTHETIC-V2',
        },
    ]
    witnesses=[_synthetic_semantic_witness(f'SYNTH-{index}',index,row) for index,row in enumerate(rows,1)]
    join={
        'status':'EXACT_DECLARED_KEY_PAIR_WITNESSES_ON_SYNTHETIC_FIXTURE',
        'matches':[{
            'canonical_key':'order_id','raw_value':'ORDER-1','match_scope':'PAIRWISE_DECLARED_KEY_WITNESS_ONLY',
            'match_count_left':1,'match_count_right':1,
            'aliases':[{'input_id':'SYNTH-1','selected_object_index':1,'source_field':'order_id','source_locator':witnesses[0]['source_locator'],'selected_row_sha256':witnesses[0]['selected_row_sha256']},{'input_id':'SYNTH-2','selected_object_index':2,'source_field':'order_id','source_locator':witnesses[1]['source_locator'],'selected_row_sha256':witnesses[1]['selected_row_sha256']}],
        }],
        'unjoined_bindings':[['SYNTH-3',3]],
        'claim_limit':'SYNTHETIC_FIXTURE_ONLY_NOT_BUSINESS_FACT',
    }
    return witnesses,join

def semantic_rule_fixture_item(rule_id):
    operator=next(operator for operator,(_handler,rule) in BUSINESS_OPERATOR_SEMANTIC_RULES.items() if rule==rule_id)
    return {
        'object_id':'SYNTHETIC-'+rule_id,
        'business_meaning':'SYNTHETIC_SEMANTIC_TEST_ONLY',
        'applicability':'SYNTHETIC_FIXTURE_ONLY',
        'assembly_spec':{'join':{'operator':operator,'required':False}},
    }

def semantic_rule_positive_assertion(rule_id,payload):
    validate_semantic_rule_payload(rule_id,payload)
    value=payload[SEMANTIC_RULE_PRIMARY_OUTPUT_KEY[rule_id]]
    if rule_id=='DECIMAL_FILL_AND_WEIGHTED_PRICE_TRANSITION_NO_FLOAT':
        return (value.get('aggregate') or {}).get('weighted_price_exact')=='102'
    if rule_id=='ZERO_NONZERO_ZERO_CYCLE_WITHOUT_ROW_ORDER_JOIN':
        return value.get('transition_count')==3 and len(value.get('cycles') or [])==1 and value['cycles'][0].get('complete') is True
    if rule_id=='EXACT_TRANSFER_PAIR_KEYS_PRESERVE_UNMATCHED':
        return any(check.get('external_wealth_effect_zero') is True for check in value.get('transfer_net_checks') or [])
    if rule_id=='ORDER_CONDITION_STATES_AND_EXACT_RELATIONS':
        return any(row.get('lifecycle_classification')=='PARTIALLY_FILLED_THEN_TERMINATED' for row in value.get('events') or [])
    if rule_id=='PRESERVE_REALIZED_PNL_COMPONENTS_BY_EXACT_FILL_OR_CYCLE':
        return sorted((row.get('realized_pnl_total_exact') for row in value.get('exact_owner_currency_totals') or []),key=semantic_exact_decimal)==['-2','5']
    if rule_id=='REQUIRE_REFERENTIAL_AND_QUANTITY_CHECKS_NO_SILENT_REPAIR':
        return any(row.get('pass') is True for row in value.get('quantity_conservation_checks') or [])
    if rule_id=='SORT_FOR_DISPLAY_AND_PRESERVE_EQUAL_TIME_PARALLEL':
        return any(row.get('parallel_when_multiple') is True for row in value.get('comparable_domain_groups') or [])
    if isinstance(value,dict): return bool(value) or rule_id.startswith('ZERO_OBJECTIVE_OUTPUT')
    if isinstance(value,list): return bool(value)
    return value is not None

def invalidate_semantic_rule_payload(rule_id,payload):
    """Create one rule-specific invalid result; validators must reject every one."""
    bad=json.loads(canonical(payload)); key=SEMANTIC_RULE_PRIMARY_OUTPUT_KEY[rule_id]; value=bad[key]
    if rule_id in {'ZERO_OBJECTIVE_OUTPUT_FOR_ANALYSIS_OR_COUNTERFACTUAL','ZERO_OBJECTIVE_OUTPUT_FOR_FUTURE_PRODUCT_FORMAT','ZERO_OBJECTIVE_OUTPUT_FOR_USER_REASON','ZERO_OBJECTIVE_OUTPUT_FOR_USER_INTERFACE_PRODUCT'}: value['objective_fact_output_count']=1
    elif rule_id=='USER_ACCEPTANCE_GATE_BEFORE_STAGE_AGGREGATION': value['passed']=True
    elif rule_id=='ACTIVE_COPY_SCOPE_EXACT_SOURCE_CLASSIFICATION': value.pop('UNRESOLVED')
    elif rule_id=='EXACT_DECLARED_KEY_RELATION_NO_CAUSAL_INFERENCE': value['adjacency_or_causality_inferred']=True
    elif rule_id=='EXACT_TRANSFER_PAIR_KEYS_PRESERVE_UNMATCHED': value['deduplication_key_is_explicit_identity_not_amount_or_time']=False
    elif rule_id=='EXACT_CONDITION_ORDER_FILL_CYCLE_EDGES_ONLY': value['similar_text_or_row_order_edges_created']=True
    elif rule_id=='SEPARATE_FACT_USER_STATEMENT_AI_INTERPRETATION_AND_STATUS': value['layers_merged']=True
    elif rule_id=='PRESERVE_FEE_PNL_FUNDING_COMPONENTS_WITH_CURRENCY': value['components_summed_across_sources']=True
    elif rule_id=='DECIMAL_FILL_AND_WEIGHTED_PRICE_TRANSITION_NO_FLOAT': value['binary_float_used']=True
    elif rule_id=='EXACT_FILL_ORDER_CYCLE_KEYS_ONLY': value['fallback_fuzzy_join_used']=True
    elif rule_id=='PRESERVE_SOURCE_NAMESPACE_AND_NEVER_REPLACE_IDS': value[0]['replacement_performed']=True
    elif rule_id=='RESOLVE_ONLY_BY_DECLARED_KEYS_AND_SOURCE_BOUNDARIES': value['cross_source_guess_used']=True
    elif rule_id=='PRESERVE_MARGIN_RISK_FIELDS_AND_UNKNOWN_NO_INFERENCE': value['missing_values_inferred']=True
    elif rule_id=='LOCK_MARKET_IDENTITY_WINDOW_AND_MISSING_COVERAGE': value.pop('windows')
    elif rule_id=='PRESERVE_MFE_MAE_BY_DECLARED_CYCLE_OR_STAGE': value['cross_owner_reaggregation_performed']=True
    elif rule_id=='CLASSIFY_ACTION_ONLY_FROM_DECLARED_EVIDENCE_FIELDS': value['unstated_intent_inferred']=True
    elif rule_id=='ORDER_CONDITION_STATES_AND_EXACT_RELATIONS': value['events'][0]['cancel_or_expire_not_treated_as_zero_fill_without_quantity_evidence']=False
    elif rule_id=='DECIMAL_POSITION_BEFORE_AFTER_TRANSITION': value[0]['delta_exact']='999'
    elif rule_id=='ZERO_NONZERO_ZERO_CYCLE_WITHOUT_ROW_ORDER_JOIN': value['row_order_grouping_used']=True
    elif rule_id=='PRESERVE_REALIZED_PNL_COMPONENTS_BY_EXACT_FILL_OR_CYCLE': value['fees_and_funding_excluded']=False
    elif rule_id=='REQUIRE_REFERENTIAL_AND_QUANTITY_CHECKS_NO_SILENT_REPAIR': value['silent_repair_performed']=True
    elif rule_id=='PRESERVE_SCREENSHOT_CONDITION_CYCLE_SOURCE_CHAIN': value['ocr_treated_as_source_not_fact_override']=False
    elif rule_id=='SEPARATE_SIDE_POSITION_SIDE_AND_POSITION_EFFECT': value['layers_collapsed']=True
    elif rule_id=='STABLE_ID_WITH_SOURCE_NAMESPACE_PRESERVED': value[0]['source_namespace']=''
    elif rule_id in {'STOP_LOSS_LIFECYCLE_PRESERVE_UNKNOWN_RELATION','TAKE_PROFIT_LIFECYCLE_PRESERVE_UNKNOWN_RELATION'}: value.pop('unknown_relations')
    elif rule_id=='SORT_FOR_DISPLAY_AND_PRESERVE_EQUAL_TIME_PARALLEL': value['equal_time_unique_order_inferred']=True
    elif rule_id=='BOUND_EQUITY_ANCHORS_AND_PRESERVE_TIME_GAPS': value['interpolation_performed']=True
    elif rule_id=='PRESERVE_ORIGINAL_TIME_TIMEZONE_AND_PRECISION': value[0]['timezone_inferred']=True
    elif rule_id=='PRESERVE_VERSION_CORRECTION_AND_SOURCE_IDENTITY_LINEAGE': value['latest_or_correct_version_inferred']=True
    else: raise RuntimeError('SEMANTIC_NEGATIVE_MUTATOR_NOT_IMPLEMENTED:'+rule_id)
    return bad

def validate_all_semantic_rule_synthetic_fixtures():
    witnesses,join=semantic_rule_synthetic_fixture(); positive=[]; negative=[]; invalid_input_safe=[]; invalid_input_rejected=0; invalid_input_zero_gated=0
    zero_gate_rules={
        'ZERO_OBJECTIVE_OUTPUT_FOR_ANALYSIS_OR_COUNTERFACTUAL','ZERO_OBJECTIVE_OUTPUT_FOR_FUTURE_PRODUCT_FORMAT',
        'ZERO_OBJECTIVE_OUTPUT_FOR_USER_REASON','ZERO_OBJECTIVE_OUTPUT_FOR_USER_INTERFACE_PRODUCT',
        'USER_ACCEPTANCE_GATE_BEFORE_STAGE_AGGREGATION',
    }
    missing_input_behavior={}
    for rule_id in sorted(SEMANTIC_RULE_CALLABLES):
        item=semantic_rule_fixture_item(rule_id)
        payload=SEMANTIC_RULE_CALLABLES[rule_id](item,witnesses,join)
        positive.append(rule_id) if semantic_rule_positive_assertion(rule_id,payload) else (_ for _ in ()).throw(RuntimeError('SEMANTIC_POSITIVE_FIXTURE_FAILED:'+rule_id))
        bad=invalidate_semantic_rule_payload(rule_id,payload)
        try:
            validate_semantic_rule_payload(rule_id,bad)
        except RuntimeError:
            negative.append(rule_id)
        else:
            raise RuntimeError('SEMANTIC_NEGATIVE_FIXTURE_NOT_REJECTED:'+rule_id)
        # Every callable also receives a missing-input negative case.  Data
        # rules must reject it; the four objective-boundary rules and the user
        # acceptance gate must produce an explicit zero-output gate.
        try:
            missing=SEMANTIC_RULE_CALLABLES[rule_id](item,[],{'matches':[],'unjoined_bindings':[]})
            validate_semantic_rule_payload(rule_id,missing)
            primary=missing[SEMANTIC_RULE_PRIMARY_OUTPUT_KEY[rule_id]]
            zero_safe=(
                isinstance(primary,dict)
                and (primary.get('objective_fact_output_count')==0 or primary.get('production_output_count')==0)
            )
            if not zero_safe or rule_id not in zero_gate_rules: raise RuntimeError('SEMANTIC_MISSING_INPUT_NOT_REJECTED_OR_ZERO_GATED:'+rule_id)
            invalid_input_zero_gated+=1
            missing_input_behavior[rule_id]='ZERO_GATE'
        except RuntimeError as error:
            if str(error).startswith('SEMANTIC_MISSING_INPUT_NOT_REJECTED_OR_ZERO_GATED:'): raise
            if rule_id in zero_gate_rules or not str(error).startswith('SEMANTIC_RULE_SOURCE_WITNESS_MISSING:'+rule_id):
                raise RuntimeError('SEMANTIC_MISSING_INPUT_ERROR_PREFIX_OR_RULE_BEHAVIOR_MISMATCH:'+rule_id+':'+str(error))
            invalid_input_rejected+=1
            missing_input_behavior[rule_id]='REJECT'
        invalid_input_safe.append(rule_id)
    edge_cases=[]
    cash_rule='EXACT_TRANSFER_PAIR_KEYS_PRESERVE_UNMATCHED'; cash_item=semantic_rule_fixture_item(cash_rule)
    cash_witnesses=[
        _synthetic_semantic_witness('EDGE-CASH-BTC',1,{'internal_transfer_pair_id':'PAIR-X','in_amount_signed_exact':'1','asset':'BTC'}),
        _synthetic_semantic_witness('EDGE-CASH-USDT',2,{'internal_transfer_pair_id':'PAIR-X','out_amount_signed_exact':'-1','asset':'USDT'}),
    ]
    cash_payload=SEMANTIC_RULE_CALLABLES[cash_rule](cash_item,cash_witnesses,{'matches':[],'unjoined_bindings':[]}); validate_semantic_rule_payload(cash_rule,cash_payload)
    cash_checks=cash_payload['canonical_cash_groups']['transfer_net_checks']
    if len(cash_checks)!=2 or any(row['external_wealth_effect_zero'] for row in cash_checks): raise RuntimeError('SEMANTIC_CROSS_CURRENCY_TRANSFER_FALSE_NET_ZERO')
    edge_cases.append('CROSS_CURRENCY_TRANSFER_NOT_NETTED')
    weighted_rule='DECIMAL_FILL_AND_WEIGHTED_PRICE_TRANSITION_NO_FLOAT'; weighted_item=semantic_rule_fixture_item(weighted_rule)
    weighted_witnesses=[
        _synthetic_semantic_witness('EDGE-WEIGHT-A1',1,{'symbol':'BTCUSDT','order_id':'ORDER-A','fill_reconstruction_id':'FA1','fill_price':'100','fill_quantity':'1','asset':'USDT'}),
        _synthetic_semantic_witness('EDGE-WEIGHT-A2',2,{'symbol':'BTCUSDT','order_id':'ORDER-A','fill_reconstruction_id':'FA2','fill_price':'102','fill_quantity':'1','asset':'USDT'}),
        _synthetic_semantic_witness('EDGE-WEIGHT-B1',3,{'symbol':'ETHUSDT','order_id':'ORDER-B','fill_reconstruction_id':'FB1','fill_price':'200','fill_quantity':'2','asset':'USDT'}),
        _synthetic_semantic_witness('EDGE-WEIGHT-B2',4,{'symbol':'ETHUSDT','order_id':'ORDER-B','fill_reconstruction_id':'FB2','fill_price':'300','fill_quantity':'1','asset':'USDT'}),
    ]
    weighted_payload=SEMANTIC_RULE_CALLABLES[weighted_rule](weighted_item,weighted_witnesses,{'matches':[],'unjoined_bindings':[]}); validate_semantic_rule_payload(weighted_rule,weighted_payload)
    weighted_value=weighted_payload['price_transitions']
    if len(weighted_value['aggregates'])!=2 or weighted_value['aggregate'] is not None: raise RuntimeError('SEMANTIC_WEIGHTED_MULTI_GROUP_FIXTURE_INVALID')
    weighted_bad=json.loads(canonical(weighted_payload)); weighted_bad['price_transitions']['aggregates'][1]['weighted_price_exact']='0'
    try: validate_semantic_rule_payload(weighted_rule,weighted_bad)
    except RuntimeError as error:
        if not str(error).startswith('SEMANTIC_WEIGHTED_PRICE_FORMULA_INVALID'): raise
    else: raise RuntimeError('SEMANTIC_WEIGHTED_SECOND_GROUP_MUTATION_NOT_REJECTED')
    edge_cases.append('MULTI_GROUP_WEIGHTED_PRICE_EACH_GROUP_RECOMPUTED')
    lifecycle_rule='ORDER_CONDITION_STATES_AND_EXACT_RELATIONS'; lifecycle_item=semantic_rule_fixture_item(lifecycle_rule)
    lifecycle_witnesses=[
        _synthetic_semantic_witness('EDGE-LIFE-A',1,{'status':'CANCELED','event_time':'2026-01-01T00:00:00+00:00'}),
        _synthetic_semantic_witness('EDGE-LIFE-B',2,{'status':'FILLED','event_time':'2026-01-01T00:00:01+00:00'}),
    ]
    lifecycle_payload=SEMANTIC_RULE_CALLABLES[lifecycle_rule](lifecycle_item,lifecycle_witnesses,{'matches':[],'unjoined_bindings':[]}); validate_semantic_rule_payload(lifecycle_rule,lifecycle_payload)
    if lifecycle_payload['lifecycle_events']['object_lifecycles'] or len(lifecycle_payload['lifecycle_events']['unassigned_events'])!=2: raise RuntimeError('SEMANTIC_MISSING_ID_LIFECYCLE_EVENTS_MERGED')
    edge_cases.append('MISSING_ID_LIFECYCLE_EVENTS_UNASSIGNED')
    pnl_rule='PRESERVE_REALIZED_PNL_COMPONENTS_BY_EXACT_FILL_OR_CYCLE'; pnl_item=semantic_rule_fixture_item(pnl_rule)
    duplicate_witnesses=[
        _synthetic_semantic_witness('EDGE-PNL-A',1,{'fill_reconstruction_id':'FILL-DUP','realized_pnl':'5','asset':'USDT'}),
        _synthetic_semantic_witness('EDGE-PNL-B',2,{'fill_reconstruction_id':'FILL-DUP','realized_pnl':'5','asset':'USDT'}),
    ]
    duplicate_payload=SEMANTIC_RULE_CALLABLES[pnl_rule](pnl_item,duplicate_witnesses,{'matches':[],'unjoined_bindings':[]}); validate_semantic_rule_payload(pnl_rule,duplicate_payload)
    pnl_value=duplicate_payload['realized_pnl_components']
    if len(pnl_value['deduplicated_components'])!=1 or pnl_value['deduplicated_components'][0]['source_claim_count']!=2 or pnl_value['exact_owner_currency_totals'][0]['realized_pnl_total_exact']!='5': raise RuntimeError('SEMANTIC_REALIZED_PNL_DUPLICATE_COUNTED_TWICE')
    edge_cases.append('SAME_EXACT_PNL_COMPONENT_COUNTED_ONCE')
    conflict_witnesses=[duplicate_witnesses[0],_synthetic_semantic_witness('EDGE-PNL-C',3,{'fill_reconstruction_id':'FILL-DUP','realized_pnl':'6','asset':'USDT'})]
    conflict_payload=SEMANTIC_RULE_CALLABLES[pnl_rule](pnl_item,conflict_witnesses,{'matches':[],'unjoined_bindings':[]}); validate_semantic_rule_payload(pnl_rule,conflict_payload)
    conflict_value=conflict_payload['realized_pnl_components']
    if conflict_value['exact_owner_currency_totals'] or len(conflict_value['conflicting_components'])!=1: raise RuntimeError('SEMANTIC_REALIZED_PNL_CONFLICT_SILENTLY_AGGREGATED')
    edge_cases.append('CONFLICTING_EXACT_PNL_COMPONENT_NOT_AGGREGATED')
    return {
        'semantic_rule_count':33,'unique_callable_count':len({id(value) for value in SEMANTIC_RULE_CALLABLES.values()}),
        'positive_pass_count':len(positive),'negative_rejection_count':len(negative),
        'invalid_input_safe_count':len(invalid_input_safe),'invalid_input_rejected_count':invalid_input_rejected,
        'invalid_input_zero_gated_count':invalid_input_zero_gated,
        'missing_input_behavior_by_rule_exact':missing_input_behavior=={rule_id:('ZERO_GATE' if rule_id in zero_gate_rules else 'REJECT') for rule_id in sorted(SEMANTIC_RULE_CALLABLES)},
        'missing_input_error_prefix_exact':True,
        'specialized_input_edge_case_pass_count':len(edge_cases),
        'synthetic_fixture_only_no_formal_fact_output':True,
    }

def capability_output_relation_ids(payload):
    ids=[]
    def visit(value):
        if isinstance(value,dict):
            if isinstance(value.get('relation_id'),str): ids.append(value['relation_id'])
            for child in value.values(): visit(child)
        elif isinstance(value,list):
            for child in value: visit(child)
    visit(payload); return sorted(set(ids))

def build_declared_capability_output(item,declarative_receipt,payload):
    source_witnesses=declarative_receipt.get('source_witnesses') or []
    raw_value=[{
        'input_id':witness['input_id'],'selected_object_index':int(witness['selected_object_index']),
        'source_locator':witness['source_locator'],'raw_value':witness.get('raw_value') or {},
    } for witness in source_witnesses]
    source_identity_id=stable_id('SOURCESET',declarative_receipt['receipt_sha256'],item['object_id'],canonical([row['source_locator'] for row in raw_value]))
    fact_id=stable_id('CAPFACT',declarative_receipt['receipt_sha256'],item['object_id'],payload['semantic_rule_id'])
    conflicts=[]
    for entry in semantic_field_entries(source_witnesses,('conflict','冲突')):
        if entry['normalized_value'] not in (None,'',[],{}): conflicts.append(stable_id('CONFLICT',source_identity_id,entry['source_locator'],canonical(entry['normalized_value'])))
    output={
        'capability_id':item['object_id'],'capability_name':item.get('capability_name') or item['business_meaning'],
        'fact_id':fact_id,'object_id':item['object_id'],'raw_value':raw_value,'normalized_value':payload,
        'evidence_status':'BOUNDED_LOCKED_SOURCE_WITNESS','applicability_scope':item.get('applicability'),
        'source_identity_id':source_identity_id,'relation_ids':capability_output_relation_ids(payload),
        'conflict_ids':sorted(set(conflicts)),
    }
    validate_declared_capability_output(item,output)
    return output

def build_boundary_capability_output(item,declarative_receipt,semantic_rule_id):
    """Build the five-field zero-objective-output record declared by boundary capabilities."""
    declared=tuple(item['capability_output']['fields'])
    expected=('capability_id','capability_name','boundary_status','reason','applicability_scope')
    if declared!=expected:
        raise RuntimeError('BOUNDARY_CAPABILITY_DECLARED_OUTPUT_FIELDS_MISMATCH:'+item['object_id'])
    output={
        'capability_id':item['object_id'],
        'capability_name':item.get('capability_name') or item['business_meaning'],
        'boundary_status':'ZERO_OBJECTIVE_OUTPUT',
        'reason':item['business_meaning'],
        'applicability_scope':item.get('applicability'),
    }
    if item['capability_output'].get('fact_emission_policy')!='NO_OBJECTIVE_FACT_OUTPUT; EMIT_BOUNDARY_RECORD_ONLY':
        raise RuntimeError('BOUNDARY_CAPABILITY_FACT_POLICY_MISMATCH:'+item['object_id'])
    return output

def validate_declared_capability_output(item,output):
    declared=tuple(item['capability_output']['fields'])
    if declared!=DECLARED_CAPABILITY_OUTPUT_FIELDS:
        raise RuntimeError('CAPABILITY_DECLARED_OUTPUT_FIELDS_MISMATCH:'+item['object_id'])
    if any(field not in output for field in DECLARED_CAPABILITY_OUTPUT_FIELDS):
        raise RuntimeError('CAPABILITY_OUTPUT_FIELD_MISSING:'+item['object_id'])
    if output['capability_id']!=item['object_id'] or not output['fact_id'] or not output['source_identity_id']:
        raise RuntimeError('CAPABILITY_OUTPUT_IDENTITY_INVALID:'+item['object_id'])
    rule_id=BUSINESS_OPERATOR_SEMANTIC_RULES[item['assembly_spec']['join']['operator']][1]
    normalized=output.get('normalized_value')
    if not isinstance(normalized,dict) or normalized.get('semantic_rule_id')!=rule_id:
        raise RuntimeError('CAPABILITY_OUTPUT_SEMANTIC_RULE_MISMATCH:'+item['object_id'])
    validate_semantic_rule_payload(rule_id,normalized)
    primary=SEMANTIC_RULE_PRIMARY_OUTPUT_KEY[rule_id]
    if primary not in normalized:
        raise RuntimeError('CAPABILITY_OUTPUT_RULE_SPECIFIC_FIELD_MISSING:'+item['object_id']+':'+primary)
    if not isinstance(output['relation_ids'],list) or not isinstance(output['conflict_ids'],list):
        raise RuntimeError('CAPABILITY_OUTPUT_RELATION_OR_CONFLICT_TYPE_INVALID:'+item['object_id'])
    return True

def execute_authoritative_business_operator(item,declarative_receipt):
    operator=item['assembly_spec']['join']['operator']
    if operator not in BUSINESS_OPERATOR_SEMANTIC_RULES:
        raise RuntimeError('BUSINESS_OPERATOR_IMPLEMENTATION_NOT_FOUND:'+operator)
    handler_id,semantic_rule_id=BUSINESS_OPERATOR_SEMANTIC_RULES[operator]
    closure_status=item['closure_status']
    result={
        'record_type':'CAPABILITY_BOUNDED_BUSINESS_RESULT',
        'capability_id':item['object_id'],
        'operator_id':operator,
        'implementation_id':'AUTHORITATIVE_BOUNDED_OPERATOR_DISPATCH',
        'implementation_version':'2.0',
        'registry_version':BUSINESS_OPERATOR_REGISTRY_VERSION,
        'handler_group':handler_id,
        'callable_id':semantic_callable_id(semantic_rule_id),
        'semantic_rule_id':semantic_rule_id,
        'closure_status':closure_status,
        'applicability_scope':item.get('applicability'),
        'source_receipt_sha256':declarative_receipt['receipt_sha256'],
        'candidate_output':None,
        'candidate_business_output_count':0,
        'formal_fact_output_count':0,
        'business_operator_semantics_executed':False,
        'semantic_callable_invoked':False,
        'boundary_gate_executed':False,
        'pre_callable_rejected':False,
        'gate_status':None,
        'rejection_reason':None,
        'adoption_status':'NOT_FORMALLY_ADOPTED_BY_THIS_BOUNDED_TEST',
        'execution_scope':'APPROVED_BOUNDED_LOCKED_MIRROR_ONLY_NOT_FULL_136',
    }
    if closure_status==UNRESOLVED_CAPABILITY_STATUS:
        result['gate_status']='REJECTED_UNRESOLVED_PRESERVE_UNKNOWN'
        result['rejection_reason']='UNRESOLVED_CAPABILITY_CANNOT_EMIT_BUSINESS_OUTPUT'
        result['pre_callable_rejected']=True
    elif closure_status==PENDING_CAPABILITY_STATUS:
        result['gate_status']='REJECTED_PENDING_USER_DECISION'
        result['rejection_reason']='USER_ACCEPTANCE_REQUIRED_BEFORE_PRODUCTION_CLOSURE'
        result['pre_callable_rejected']=True
    elif closure_status==BOUNDARY_CAPABILITY_STATUS:
        result['candidate_output']=build_boundary_capability_output(item,declarative_receipt,semantic_rule_id)
        result['gate_status']='ZERO_OBJECTIVE_OUTPUT_BOUNDARY_EXECUTED'
        result['boundary_gate_executed']=True
    elif closure_status==RUNNABLE_CAPABILITY_STATUS:
        payload=SEMANTIC_RULE_CALLABLES[semantic_rule_id](item,declarative_receipt.get('source_witnesses') or [],declarative_receipt.get('join_witness') or {})
        result['candidate_output']=build_declared_capability_output(item,declarative_receipt,payload)
        result['gate_status']='BOUNDED_BUSINESS_SEMANTICS_EXECUTED'
        result['business_operator_semantics_executed']=True
        result['semantic_callable_invoked']=True
        result['candidate_business_output_count']=1
    else:
        raise RuntimeError('BUSINESS_OPERATOR_CLOSURE_STATUS_UNSUPPORTED:'+closure_status)
    result['result_sha256']=hashlib.sha256(canonical(result).encode('utf-8')).hexdigest()
    return result

def execute_authoritative_business_operators(capability_records,declarative_receipts):
    receipt_map={item['capability_id']:item for item in declarative_receipts}
    if set(receipt_map)!={item['object_id'] for item in capability_records}:
        raise RuntimeError('BUSINESS_OPERATOR_DECLARATIVE_RECEIPT_SET_MISMATCH')
    results=[execute_authoritative_business_operator(item,receipt_map[item['object_id']]) for item in sorted(capability_records,key=lambda row:row['object_id'])]
    status_counts=Counter(item['gate_status'] for item in results)
    overall_sha=hashlib.sha256(('\n'.join(canonical(item) for item in results)+'\n').encode('utf-8')).hexdigest()
    summary={
        'capability_count':len(results),
        'operator_count':len({item['operator_id'] for item in results}),
        'registered_operator_count':len(BUSINESS_OPERATOR_SEMANTIC_RULES),
        'routed_capability_count':len(results),
        'semantic_callable_invocation_count':sum(item['semantic_callable_invoked'] for item in results),
        'distinct_semantic_callable_invoked_count':len({item['semantic_rule_id'] for item in results if item['semantic_callable_invoked']}),
        'boundary_gate_execution_count':sum(item['boundary_gate_executed'] for item in results),
        'pre_callable_rejected_count':sum(item['pre_callable_rejected'] for item in results),
        'runnable_business_semantics_executed_count':sum(item['gate_status']=='BOUNDED_BUSINESS_SEMANTICS_EXECUTED' for item in results),
        'boundary_zero_output_executed_count':sum(item['gate_status']=='ZERO_OBJECTIVE_OUTPUT_BOUNDARY_EXECUTED' for item in results),
        'unresolved_rejected_count':sum(item['gate_status']=='REJECTED_UNRESOLVED_PRESERVE_UNKNOWN' for item in results),
        'pending_user_rejected_count':sum(item['gate_status']=='REJECTED_PENDING_USER_DECISION' for item in results),
        'candidate_business_output_count':sum(item['candidate_business_output_count'] for item in results),
        'formal_fact_output_count':sum(item['formal_fact_output_count'] for item in results),
        'gate_status_counts':dict(sorted(status_counts.items())),
        'all_33_operators_callable':{item['operator_id'] for item in results}==set(BUSINESS_OPERATOR_SEMANTIC_RULES),
        'all_results_bound_to_declarative_receipts':all(bool(item['source_receipt_sha256']) for item in results),
        'execution_results_sha256':overall_sha,
        'scope_statement':'BOUNDED_CANDIDATE_BUSINESS_SEMANTICS_ONLY_NOT_FORMAL_FACT_NOT_FULL_136',
    }
    expected={
        'capability_count':94,'operator_count':33,
        'registered_operator_count':33,'routed_capability_count':94,
        'semantic_callable_invocation_count':69,'distinct_semantic_callable_invoked_count':28,
        'boundary_gate_execution_count':5,'pre_callable_rejected_count':20,
        'runnable_business_semantics_executed_count':69,
        'boundary_zero_output_executed_count':5,
        'unresolved_rejected_count':19,'pending_user_rejected_count':1,
        'candidate_business_output_count':69,'formal_fact_output_count':0,
    }
    if any(summary[key]!=value for key,value in expected.items()) or not summary['all_33_operators_callable']:
        raise RuntimeError('BUSINESS_OPERATOR_EXECUTION_COVERAGE_MISMATCH:'+canonical(summary))
    return results,summary

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
            'mirror_path':receipt.get('receipt_identity_mirror_path') or receipt['mirror_path'],
            'mirror_sha256':receipt['extracted_content_sha256'],
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

RECOMPUTATION_DRY_RUN_MODES={'SYNTHETIC_FIXTURE','LOCKED_INPUT_IDENTITY_DRY_RUN'}

def recomputation_method_identity(item):
    identities=[]
    for method in sorted(item['method_selected_objects'],key=lambda row:int(row['selected_object_index'])):
        identities.append({
            'input_id':item['recomputation_id'],
            'selected_object_index':int(method['selected_object_index']),
            'source_path':method['source_path'],
            'source_sha256':method['sha256'],
            'selected_content_sha256':method['extracted_content_sha256'],
            'actual_count':int(method['actual_count']),
        })
    return identities

def run_recomputation_dry_run(contract_path,receipts_path,recomputation_id,mode,fixture_path,output_path):
    """Run only a synthetic fixture or locked-identity validation; real values stay locked."""
    if mode not in RECOMPUTATION_DRY_RUN_MODES:
        raise RuntimeError('REAL_RECOMPUTATION_NOT_AUTHORIZED:'+str(mode))
    contract_path=Path(contract_path).resolve(); receipts_path=Path(receipts_path).resolve(); output_path=Path(output_path).resolve()
    if output_path.exists():
        raise RuntimeError('RECOMPUTATION_DRY_RUN_OUTPUT_ALREADY_EXISTS:'+str(output_path))
    contract=json.load(open(contract_path,encoding='utf-8'))
    receipts=read_jsonl(receipts_path)
    items=validate_recomputation_contracts(contract,receipts)
    if recomputation_id not in items:
        raise RuntimeError('RECOMPUTATION_ID_NOT_ALLOWED:'+str(recomputation_id))
    item=items[recomputation_id]
    method_identity=recomputation_method_identity(item)
    record={
        'record_type':'RECOMPUTATION_DRY_RUN_RECEIPT',
        'recomputation_id':recomputation_id,
        'mode':mode,
        'contract_sha256':sha_file(contract_path),
        'receipts_sha256':sha_file(receipts_path),
        'program_sha256':sha_file(Path(__file__).resolve()),
        'method_identity':method_identity,
        'method_identity_sha256':hashlib.sha256(canonical(method_identity).encode('utf-8')).hexdigest(),
        'real_business_values_read':False,
        'real_recomputation_run':False,
        'network_used':False,
        'formal_result_output_count':0,
        'candidate_result':None,
    }
    if mode=='LOCKED_INPUT_IDENTITY_DRY_RUN':
        if fixture_path is not None:
            raise RuntimeError('IDENTITY_DRY_RUN_FIXTURE_NOT_ALLOWED')
        record['status']='LOCKED_METHOD_INPUT_IDENTITIES_VERIFIED_NO_NUMERIC_RESULT'
    else:
        if fixture_path is None:
            raise RuntimeError('SYNTHETIC_FIXTURE_REQUIRED')
        fixture_path=Path(fixture_path).resolve()
        fixture=json.loads(fixture_path.read_text(encoding='utf-8'),parse_float=str,parse_int=str)
        required=set(item['runtime_adapter']['required_fixture_fields'])
        if set(fixture)!=required:
            raise RuntimeError('SYNTHETIC_FIXTURE_FIELD_SET_MISMATCH:'+recomputation_id)
        if recomputation_id=='S3INPUT-40':
            result=recompute_target_minute_mark_synthetic(**fixture)
        elif recomputation_id=='S3INPUT-41':
            result=recompute_t087_outer_envelope_synthetic(fixture['paths'])
        else:
            result=recompute_joint_interval_synthetic(**fixture)
        record.update({
            'status':'SYNTHETIC_FIXTURE_EXECUTED_NOT_FORMAL_RESULT',
            'fixture_sha256':sha_file(fixture_path),
            'fixture_fields':sorted(fixture),
            'candidate_result':result,
        })
    record['receipt_sha256']=hashlib.sha256(canonical(record).encode('utf-8')).hexdigest()
    output_path.parent.mkdir(parents=True,exist_ok=True)
    json_write(output_path,record)
    print(canonical(record)); return record

def read_csv(path):
    with open(path,encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))

def jsonl_write(path, records):
    with open(path,'w',encoding='utf-8',newline='\n') as f:
        for record in records: f.write(canonical(record)+'\n')

def json_write(path, value):
    with open(path,'w',encoding='utf-8',newline='\n') as f:
        json.dump(value,f,ensure_ascii=False,sort_keys=True,indent=2); f.write('\n')

def canonicalize_xlsx_package(path):
    """Remove random relationship IDs and ZIP metadata from an XLSX package."""
    path=Path(path)
    with zipfile.ZipFile(path,'r') as source:
        members={name:source.read(name) for name in source.namelist() if not name.endswith('/')}
    relationship_namespace='{http://schemas.openxmlformats.org/package/2006/relationships}'
    replacements={}
    for member_name in sorted(name for name in members if name.endswith('.rels')):
        root=ET.fromstring(members[member_name])
        relationships=[]
        for relation in root.findall(relationship_namespace+'Relationship'):
            identity=tuple(sorted((key,value) for key,value in relation.attrib.items() if key!='Id'))
            relationships.append((identity,relation.attrib['Id']))
        for ordinal,(identity,old_id) in enumerate(sorted(relationships),1):
            seed=canonical({'member':member_name,'ordinal':ordinal,'identity':identity})
            new_id='R'+hashlib.sha256(seed.encode('utf-8')).hexdigest()[:16]
            if new_id in replacements.values() and replacements.get(old_id)!=new_id:
                raise RuntimeError('XLSX_CANONICAL_RELATIONSHIP_ID_COLLISION')
            replacements[old_id]=new_id
    canonical_members={}
    for member_name,payload in members.items():
        for old_id,new_id in replacements.items():
            payload=payload.replace(old_id.encode('ascii'),new_id.encode('ascii'))
        canonical_members[member_name]=payload
    temp_path=path.with_name(path.name+'.canonicalizing')
    with zipfile.ZipFile(temp_path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as target:
        for member_name in sorted(canonical_members):
            info=zipfile.ZipInfo(member_name,date_time=(1980,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.create_system=3
            info.external_attr=0o600 << 16
            target.writestr(info,canonical_members[member_name],compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    os.replace(temp_path,path)

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
            'receipt_identity_mirror_path':receipt.get('receipt_identity_mirror_path') or receipt['mirror_path'],
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
    expected_policy={
        'allowed_modes_in_first_package':['SYNTHETIC_FIXTURE','LOCKED_INPUT_IDENTITY_DRY_RUN'],
        'default_real_business_run_gate':'DENY',
        'command_line_flag_is_not_user_authorization':True,
        'existing_output_overwrite_allowed':False,
        'network_access_allowed':False,
        'program_file':'06_构建与确定性装载程序候选.py',
        'real_business_input_value_calculation_allowed':False,
        'required_program_entry':'recompute-dry-run',
        'result_identity_rule':'每个输出必须绑定重算编号、程序版本、方法对象指纹、输入指纹、运行模式和输出指纹。',
        'unauthorized_mode_action':'STOP_WITH_REAL_RECOMPUTATION_NOT_AUTHORIZED',
    }
    if contract.get('execution_policy')!=expected_policy:
        raise RuntimeError('RECOMPUTATION_EXECUTION_POLICY_INVALID')
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
        expected_runnability=(
            'DRY_RUN_READY_REAL_RUN_NOT_AUTHORIZED'
            if recomputation_id=='S3INPUT-40'
            else 'DRY_RUN_READY_REAL_VALUE_RUNTIME_INPUTS_NOT_AUTHORIZED_AND_NOT_CLOSED'
        )
        if item.get('runnability_status')!=expected_runnability:
            raise RuntimeError('RECOMPUTATION_RUNNABILITY_STATUS_INVALID:'+recomputation_id)
        entry=item.get('program_entry') or {}
        if entry.get('function')!='run_recomputation_dry_run' or entry.get('implementation_version')!='1.0' or entry.get('real_business_mode_available') is not False or 'recompute-dry-run' not in str(entry.get('command_template')):
            raise RuntimeError('RECOMPUTATION_PROGRAM_ENTRY_INVALID:'+recomputation_id)
        adapter=item.get('runtime_adapter') or {}
        if adapter.get('receipt_authority')!='02_输入身份_选择器与装载回执候选.jsonl':
            raise RuntimeError('RECOMPUTATION_RECEIPT_AUTHORITY_INVALID:'+recomputation_id)
        if adapter.get('implicit_field_guessing_allowed') is not False or adapter.get('row_number_or_file_order_join_allowed') is not False or adapter.get('output_overwrite_allowed') is not False:
            raise RuntimeError('RECOMPUTATION_RUNTIME_SAFETY_POLICY_INVALID:'+recomputation_id)
        if not adapter.get('required_fixture_fields') or not adapter.get('stop_gates') or not adapter.get('input_order') or not adapter.get('precision_policy'):
            raise RuntimeError('RECOMPUTATION_RUNTIME_ADAPTER_INCOMPLETE:'+recomputation_id)
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
        runtime_inputs=item.get('actual_runtime_inputs') or []
        if recomputation_id=='S3INPUT-40':
            if len(runtime_inputs)!=11 or any(not {'input_id','source_path','size_bytes','sha256','symbol','UTC_date','role','allowed_use','prohibited_use'}.issubset(value) for value in runtime_inputs):
                raise RuntimeError('S3INPUT_40_LOCKED_MARK_INPUT_MANIFEST_INVALID')
            if len({value['input_id'] for value in runtime_inputs})!=11:
                raise RuntimeError('S3INPUT_40_LOCKED_MARK_INPUT_ID_DUPLICATE')
        else:
            expected_indexes=set(range(1,3 if recomputation_id=='S3INPUT-41' else 6))
            if {int(value.get('selected_object_index',-1)) for value in runtime_inputs}!=expected_indexes:
                raise RuntimeError('RECOMPUTATION_RUNTIME_INPUT_INDEX_SET_INVALID:'+recomputation_id)
            for value in runtime_inputs:
                key=(recomputation_id,int(value['selected_object_index']))
                if value.get('read_from_verified_mirror_only') is not True or value.get('extracted_content_sha256')!=receipt_map[key]['extracted_content_sha256']:
                    raise RuntimeError('RECOMPUTATION_RUNTIME_INPUT_IDENTITY_INVALID:'+recomputation_id+':'+str(key[1]))
        if recomputation_id=='S3INPUT-41' and [value.get('role') for value in runtime_inputs]!=['CURRENT_EFFECTIVE_RULE_AND_OUTER_ENVELOPE','TWO_LAWFUL_VARIANT_ROWS']:
            raise RuntimeError('S3INPUT_41_RUNTIME_ROLE_OR_ORDER_INVALID')
        if recomputation_id=='S3INPUT-42' and runtime_inputs[-1].get('role')!='REGRESSION_ONLY_NOT_VALUE_REUSE':
            raise RuntimeError('S3INPUT_42_REGRESSION_ROLE_INVALID')
    return by_id

def receipts_rebound_to_mirror_root(receipts,mirror_root):
    mirror_root=Path(mirror_root).resolve()
    rebound=[]
    for receipt in receipts:
        item=json.loads(json.dumps(receipt,ensure_ascii=False))
        mirror=mirror_root/Path(receipt['mirror_path']).name
        if not mirror.is_file() or sha_file(mirror)!=receipt['extracted_content_sha256']:
            raise RuntimeError('CLEAN_ROOT_MIRROR_IDENTITY_MISMATCH:'+receipt['input_id']+':'+str(receipt['selected_object_index']))
        item['receipt_identity_mirror_path']=receipt['mirror_path']
        item['mirror_path']=str(mirror)
        rebound.append(item)
    return rebound

def load_and_validate_specifications(config_path,config,mirror_root=None):
    specs=config['specification_inputs']
    adoption_path=verify_config_file(config_path,specs['adoption_candidates'],'adoption_candidates')
    receipts_path=verify_config_file(config_path,specs['input_receipts'],'input_receipts')
    mapping_path=verify_config_file(config_path,specs['assembly_mapping'],'assembly_mapping')
    schema_path=verify_config_file(config_path,specs['normalization_schema'],'normalization_schema')
    recomputation_path=verify_config_file(config_path,specs['recomputation_contract'],'recomputation_contract')
    stage3_path=verify_config_file(config_path,specs['stage3_machine_ledger'],'stage3_machine_ledger')
    adoption=read_jsonl(adoption_path); receipts=read_jsonl(receipts_path); mapping=read_jsonl(mapping_path); schema=json.load(open(schema_path,encoding='utf-8')); recomputation=json.load(open(recomputation_path,encoding='utf-8')); stage3=read_jsonl(stage3_path)
    if mirror_root is not None:
        receipts=receipts_rebound_to_mirror_root(receipts,mirror_root)
    capabilities=[item for item in mapping if item.get('record_type')=='CAPABILITY_CLOSURE_CANDIDATE']
    gaps=[item for item in mapping if item.get('record_type')=='STRICT_GAP_HANDLING_CANDIDATE']
    business_operator_validation=validate_business_operator_registry_records(mapping,capabilities)
    return {
        'adoption':adoption,
        'mapping':mapping,
        'schema':schema,
        'receipts':receipts,
        'recomputation_contract':recomputation,
        'recomputation_items':validate_recomputation_contracts(recomputation,receipts),
        'capabilities':capabilities,
        'capability_validation':validate_capability_specs(capabilities,adoption,schema,receipts),
        'business_operator_validation':business_operator_validation,
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

def validate_trade_object_package_schema(schema):
    layers=schema.get('information_layers') or {}
    required_layers={'trade_object','process_event','result_statement','trade_object_package','user_semantic_link'}
    if not required_layers.issubset(layers):
        raise RuntimeError('TRADE_OBJECT_INFORMATION_LAYER_MISSING')
    package=schema.get('objective_trade_object_package') or {}
    required_sections={'object_identity','process_package','result_package','relation_package','unknown_package','conflict_package','source_package','minimal_user_semantics_attachment'}
    if set(package.get('required_sections') or [])!=required_sections:
        raise RuntimeError('TRADE_OBJECT_REQUIRED_SECTION_SET_INVALID')
    for section in required_sections:
        if not (package.get(section) or {}).get('required'):
            raise RuntimeError('TRADE_OBJECT_SECTION_REQUIREMENT_MISSING:'+section)
    unknown_required={'unknown_items','owner_object_or_fact_id','field_path','reason','missing_evidence','scope','source_fact_ids'}
    if not unknown_required.issubset(package['unknown_package']['required']) or package['unknown_package'].get('unknown_as_empty_zero_false_or_not_happened_allowed') is not False:
        raise RuntimeError('TRADE_OBJECT_UNKNOWN_POLICY_INVALID')
    conflict_required={'conflict_ids','claim_fact_ids','nature','resolution_status','resolution_fact_id_or_explicit_unresolved'}
    if not conflict_required.issubset(package['conflict_package']['required']) or package['conflict_package'].get('silent_resolution_allowed') is not False or package['conflict_package'].get('last_write_wins_allowed') is not False:
        raise RuntimeError('TRADE_OBJECT_CONFLICT_POLICY_INVALID')
    source_required={'source_identity_ids','source_paths','source_sha256_values','source_locators','selectors','lineage_fact_ids'}
    if not source_required.issubset(package['source_package']['required']) or package['source_package'].get('every_reference_must_resolve_exactly_once') is not True:
        raise RuntimeError('TRADE_OBJECT_SOURCE_POLICY_INVALID')
    semantics=package['minimal_user_semantics_attachment']
    if semantics.get('objective_fact_override_allowed') is not False or semantics.get('ai_inference_as_user_semantics_allowed') is not False:
        raise RuntimeError('TRADE_OBJECT_USER_SEMANTICS_BOUNDARY_INVALID')
    if package.get('ai_causal_analysis_allowed') is not False or (package.get('causality_policy') or {}).get('ai_interpretation_must_remain_separate_and_not_a_fact') is not True:
        raise RuntimeError('TRADE_OBJECT_CAUSALITY_BOUNDARY_INVALID')
    if (package.get('reference_integrity') or {}).get('all_fact_relation_lineage_conflict_unknown_and_user_semantic_references_resolve_exactly_once') is not True:
        raise RuntimeError('TRADE_OBJECT_REFERENCE_INTEGRITY_POLICY_INVALID')
    return {
        'required_section_count':len(required_sections),'new_information_layer_count':len(required_layers),
        'unknown_owner_and_source_required':True,'conflicts_preserve_all_claims':True,
        'source_references_resolve_exactly_once':True,'user_semantics_cannot_override_fact':True,
        'ai_causal_analysis_allowed':False,
    }

def validate_fact_base_against_schema(records,schema):
    validate_trade_object_package_schema(schema)
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
        # This bounded package has no approved user-semantics source.  Null is
        # therefore the only valid value in both attachment fields.  Merely
        # generating nulls is not a pollution gate: validation must reject a
        # later injected statement or AI interpretation before it can be read
        # as part of the objective fact base.
        if record.get('user_statement') is not None:
            raise RuntimeError('FACT_BASE_UNAPPROVED_USER_STATEMENT_REJECTED:'+record['fact_id'])
        if record.get('ai_interpretation') is not None:
            raise RuntimeError('FACT_BASE_AI_INTERPRETATION_REJECTED:'+record['fact_id'])
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
        'user_semantics_zero_instance_gate_passed':True,
        'ai_interpretation_zero_instance_gate_passed':True,
    }

def build(config_path, manifest_path, output_path, mirror_root=None):
    config=json.load(open(config_path,encoding='utf-8')); manifest=json.load(open(manifest_path,encoding='utf-8'))
    specifications=load_and_validate_specifications(config_path,config,mirror_root)
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
    receipts=specifications['receipts']
    receipt_map={(item['input_id'],int(item['selected_object_index'])):item for item in receipts}
    for method in config.get('bounded_method_test_sources',[]):
        receipt=receipt_map[(method['input_id'],int(method['selected_object_index']))]
        payload=selected_payload(receipt); path=Path(receipt['source_path'])
        row={'event_id':None,'position_cycle_id':'T087','method_payload':payload,'time_basis':'NOT_APPLICABLE'}
        method_source={
            'path':receipt['source_path'],'sha256':receipt['actual_sha256'],'bytes':receipt['actual_bytes'],
            'input_id':receipt['input_id'],'selected_object_index':int(receipt['selected_object_index']),
            'mirror_path':receipt.get('receipt_identity_mirror_path') or receipt['mirror_path'],
            'selected_content_sha256':receipt['extracted_content_sha256'],
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
    legacy={
        '从这里开始':start_rows,'对象目录':directory,'事件时间线':timeline,
        '关系与归属':relation_rows,'特殊对象与边界':special,'来源追溯':lineage_rows,
        '输入范围':input_rows,'技术原文':technical,
    }
    return humanize_workbook_payload(legacy,records,contract_id)

WORKBOOK_SOURCE_TABLE_NAMES={
    'position':'仓位变化记录','order':'委托记录','fill':'成交记录','condition':'条件委托记录',
    'fund':'资金记录','linkage':'关系连接记录','lineage':'来源追溯记录','method':'方法边界记录',
}
WORKBOOK_FIELD_NAMES={
    'reason_status':'取消或未触发的具体原因','currency':'币种','domain_class':'这条资金影响属于哪一类交易',
    'funding_fee':'资金费','target_object_candidates':'可能归属的目标对象',
}
WORKBOOK_CONFLICT_NAMES={
    'T087-SAME-SECOND-UNIQUE-ORDER-NOT-PROVEN':'T087 同一秒的先后顺序没有唯一证据',
}
WORKBOOK_OBJECT_DESCRIPTIONS={
    'T020':'一笔主动交易样本；用来查看止盈止损变化、共享账户影响和很长的连续记录。',
    'T087':'一笔主动交易样本；同一秒存在两种合法先后顺序，目前没有证据证明哪一种才是唯一真实顺序。',
    'T092':'一笔主动交易样本；要和相邻的 T093 以及一个暂时无法归属的条件对象一起看。',
    'T093':'一笔主动交易样本；要和相邻的 T092 以及一个暂时无法归属的条件对象一起看。',
    'T112':'一笔主动交易样本；用来查看部分成交、减仓、平仓和仓位连续变化。',
    'T120':'一笔主动交易样本；用来查看多次开仓或加仓尝试、撤单和替换。',
    'SHARED_ACCOUNT_EFFECT':'账户层的共享影响；只能说明账户在同一时间范围内受到影响，不能自动归到某一笔交易。',
    'UNASSIGNED:COND-0218':'一个目前无法可靠归入 T092 或 T093 的条件对象，必须保持未归属。',
    'U016':'跟单资金影响对象；它不是一笔主动交易，不能硬塞进主动交易链。',
    'CROSS_OBJECT_RELATIONS':'跨对象关系入口；这里只保存会跨越单笔交易的连接或关系端点。',
    'T087_METHOD':'T087 的方法与边界；保存两条合法路径和外包络，但没有证明唯一真实顺序。',
}

def workbook_record_needs_attention(record):
    state=record.get('value_state') or {}
    return bool(
        state.get('unknown') or state.get('candidate_sets') or state.get('intervals')
        or record.get('conflict_ids') or record.get('evidence_status')=='CANDIDATE'
    )

def workbook_evidence_plain(record):
    labels={
        'DIRECT':'有直接记录支持这条内容',
        'BOUNDED':'有记录支持，但只能证明到现有说明的范围',
        'CANDIDATE':'只是候选，不能当成已经确定',
        'UNKNOWN':'目前没有足够证据确认',
    }
    return labels.get(record.get('evidence_status'),'当前证据身份：'+str(record.get('evidence_status') or '未记录'))

def workbook_attention_plain(record):
    state=record.get('value_state') or {}; parts=[]
    unknown=state.get('unknown') or []
    if unknown:
        parts.append('这些内容没有可确定值：'+'、'.join(WORKBOOK_FIELD_NAMES.get(item.get('field'),str(item.get('field') or '未命名字段')) for item in unknown))
    candidates=state.get('candidate_sets') or []
    if candidates:
        descriptions=[]
        for item in candidates:
            label=WORKBOOK_FIELD_NAMES.get(item.get('field'),str(item.get('field') or '候选关系'))
            ids='、'.join(str(value) for value in (item.get('candidate_ids') or []))
            descriptions.append(label+('有多个可能对象（'+ids+'）' if ids else '有多个可能对象'))
        parts.append('；'.join(descriptions))
    intervals=state.get('intervals') or []
    if intervals:
        parts.append('只能保留区间：'+'、'.join(WORKBOOK_FIELD_NAMES.get(item.get('field'),str(item.get('field') or '未命名字段')) for item in intervals))
    conflicts=record.get('conflict_ids') or []
    if conflicts:
        parts.append('存在不能强行消除的冲突或多路径：'+'、'.join(WORKBOOK_CONFLICT_NAMES.get(value,value) for value in conflicts))
    if record.get('evidence_status')=='CANDIDATE': parts.append('这条关系或结论仍是候选')
    return ('；'.join(parts)+'。') if parts else '没有另外标出的未知、多个候选或冲突。'

def workbook_user_check_plain(record):
    state=record.get('value_state') or {}; parts=[]
    if state.get('unknown'): parts.append('确认这里继续按“未知”保留，不要补猜成确定值')
    if state.get('candidate_sets'): parts.append('确认所有候选都保留，不要替它选一个')
    if state.get('intervals'): parts.append('确认只写区间，不改成单一数字')
    if record.get('conflict_ids'): parts.append('确认冲突或多条合法路径同时保留，不指定唯一答案')
    if record.get('evidence_status')=='CANDIDATE': parts.append('确认它仍明确标成候选，没有写成确定归属')
    return ('；'.join(parts)+'。') if parts else '不用作新的业务选择；如要抽查，只核对时间和“发生了什么”是否连贯。'

def workbook_source_pointer(record):
    file_name=Path(str(record.get('source_path') or '来源文件未记录')).name
    table=WORKBOOK_SOURCE_TABLE_NAMES.get(record.get('source_table'),str(record.get('source_table') or '来源表未记录'))
    row=record.get('source_row'); row_text='位置未单独记录' if row in (None,'') else f'第 {row} 行'
    return f'{file_name} / {table} / {row_text}'

def workbook_relation_plain(record):
    relation=record.get('relation') or {}
    source=relation.get('source_object_id') or relation.get('source_event_id') or '来源对象未记录'
    target=relation.get('target_object_id') or relation.get('target_event_id') or '目标对象未记录'
    relation_type=relation.get('relation_type')
    if relation_type=='ORDER_FILL': return f'成交记录 {source} 对应委托 {target}。'
    if relation_type=='ORDER_POSITION_ACTION': return f'仓位变化 {source} 对应委托 {target}。'
    if relation_type=='CONDITIONAL_ORDER': return f'条件委托 {source} 可能与仓位周期 {target} 有关；目前仍按候选关系保留。'
    if relation_type=='COPY_FUNDS_NODE': return f'跟单资金节点 {source} 对应仓位周期 {target}；这里只说明资金节点关系。'
    return record.get('plain_summary') or ''

def workbook_special_action(object_id):
    fixed={
        'CROSS_OBJECT_RELATIONS':'把它当作跨对象连接查看，不放进任何一笔交易。',
        'SHARED_ACCOUNT_EFFECT':'只确认账户层共享影响存在，不把资金影响自动分给某一笔交易。',
        'T087_METHOD':'同时保留两条合法路径和外包络，不替它选择唯一顺序。',
        'U016':'只当作跟单资金影响，不当作主动交易。',
        'UNASSIGNED:COND-0218':'继续保持未归属，不强行放进 T092 或 T093。',
    }
    if object_id in fixed: return fixed[object_id]
    if str(object_id).startswith('S05-CYC-'): return '把它当作关系端点，不当作一条新交易事件。'
    return '按本行写明的边界保留，不扩大为确定事实。'

def humanize_workbook_payload(legacy,records,contract_id):
    by_id={record['fact_id']:record for record in records}
    attention=Counter(record['navigation_object_id'] for record in records if workbook_record_needs_attention(record))
    timeline_first={}
    for index,row in enumerate(legacy['事件时间线'],start=4): timeline_first.setdefault(row['对象入口'],index)
    special_first={row['对象入口']:index for index,row in enumerate(legacy['特殊对象与边界'],start=4)}
    directory=[]
    for row in legacy['对象目录']:
        object_id=row['对象入口']; start=row['起始时间']; end=row['结束时间']
        if object_id in timeline_first: first=f'到“事件时间线”第 {timeline_first[object_id]} 行开始看；同一对象可用第一列筛选。'
        elif object_id in special_first: first=f'到“特殊对象与边界”第 {special_first[object_id]} 行查看。'
        else: first='到“关系与归属”或“特殊对象与边界”按对象名称查找。'
        directory.append({
            '对象':object_id,'这是什么':WORKBOOK_OBJECT_DESCRIPTIONS.get(object_id,row['对象类型']),
            '时间范围':'不适用' if start=='不适用' and end=='不适用' else f'{start} 至 {end}',
            '事件记录':row['事实数'],'关系记录':row['关系数'],'来源记录':row['来源链数'],
            '需要特别留意':f'{attention[object_id]} 条记录含未知、候选、区间或冲突；优先看带提醒的行。' if attention[object_id] else '没有单独标出的未知、候选、区间或冲突。',
            '从哪里开始看':first,'全部记录数（技术）':row['记录数'],'方法记录数（技术）':row['方法记录数'],'样本标签（技术）':row['涉及样本'],
        })
    timeline=[]
    for row in legacy['事件时间线']:
        record=by_id[row['事实ID']]
        display_time=(str(row['北京时间'])+'（北京时间）') if row['北京时间']!='未能可靠换算' else str(row['原始时间'] or '时间未记录')+'（沿用原记录，时区未能可靠换算）'
        timeline.append({
            '对象':row['对象入口'],'时间':display_time,'发生了什么':row['发生了什么'],
            '目前能确定到什么程度':workbook_evidence_plain(record),'还不知道或必须保留什么':workbook_attention_plain(record),
            '你需要核对什么':workbook_user_check_plain(record),'来源怎么展开':workbook_source_pointer(record),'事实编号':record['fact_id'],
            '顺序（技术）':row['顺序'],'北京时间（技术）':row['北京时间'],'原始时间（技术）':row['原始时间'],'品种（技术）':row['品种'],
            '委托ID（技术）':row['委托ID'],'成交ID（技术）':row['成交ID'],'动作（技术）':row['动作'],'状态（技术）':row['状态'],
            '数量与价格（技术）':f'数量：{row["数量"] or "未记录"}；价格：{row["价格"] or "未记录"}',
            '费用与盈亏（技术）':f'手续费：{row["手续费"] or "未记录"} {row["费用币种"] or ""}；已实现盈亏：{row["已实现盈亏"] or "未记录"}',
            '仓位变化（技术）':row['仓位变化'],
        })
    relations=[]
    for row in legacy['关系与归属']:
        record=by_id[row['事实ID']]; relation=record.get('relation') or {}
        source=relation.get('source_object_id') or relation.get('source_event_id') or '来源未记录'
        target=relation.get('target_object_id') or relation.get('target_event_id') or '目标未记录'
        relations.append({
            '对象':row['对象入口'],'这条关系在说什么':workbook_relation_plain(record),'目前能确定到什么程度':workbook_evidence_plain(record),
            '不能把它理解成什么':record['cannot_prove'],'你需要核对什么':workbook_user_check_plain(record),
            '来源对象 → 目标对象':f'{source} → {target}','来源怎么展开':workbook_source_pointer(record),'关系事实编号':record['fact_id'],
            '关系类型（技术）':row['关系类型'],'目标对象类型（技术）':row['目标对象类型'],'来源事实ID（技术）':row['来源事实ID'],
            '目标事实ID（技术）':row['目标事实ID'],'关系ID（技术）':row['关系ID'],'证据状态代码（技术）':record['evidence_status'],
        })
    special=[]
    for row in legacy['特殊对象与边界']:
        object_id=row['对象入口']
        special.append({
            '对象':object_id,'这是什么':WORKBOOK_OBJECT_DESCRIPTIONS.get(object_id,row['对象身份']),
            '现在已经知道什么':row['白话说明'],'仍然不能确定什么':row['必须保留的边界'],
            '用户现在怎么处理':workbook_special_action(object_id),'相关记录编号':row['相关事实ID'],
        })
    lineage=[]
    for row in legacy['来源追溯']:
        record=by_id[row['事实ID']]; file_name=Path(str(row['直接来源文件'] or '来源文件未记录')).name
        source_row=row['来源行']; source_location='行号未记录' if source_row in (None,'') else f'第 {source_row} 行'
        preserved='本次记录显示原值保持检查通过' if ('通过' in str(row['值保留状态']) or 'PASS' in str(row['值保留状态'])) else str(row['值保留状态'] or '未单独记录')
        lineage.append({
            '对象':row['对象入口'],'对应哪一条事件':row['事件ID'],'原始文件名':file_name,
            '工作表和行号':f'{row["来源表"] or "工作表未记录"} / {source_location}','原值是否保持':preserved,
            '普通核对怎么找':f'打开 {file_name}，进入 {row["来源表"] or "对应工作表"}，查看{source_location if source_row not in (None,"") else "记录位置"}。',
            '完整路径（技术）':row['直接来源文件'],'来源事实编号（技术）':record['fact_id'],
        })
    inputs=[]
    for row in legacy['输入范围']:
        is_sample=row['记录类别']=='困难样本'
        inputs.append({
            '本次用了什么':row['对象或选中范围'],'这是什么':row['输入编号或样本类别'] if is_sample else Path(str(row['来源文件'])).name,
            '本次实际取了多少':'按固定样本选中' if row['装载数量'] in (None,'') else f'{row["装载数量"]} 条/个记录',
            '本次为什么用它':row['能证明'],'本次不能证明什么':row['不能证明'],'当前身份':row['当前状态'],
            '来源路径（技术）':row['来源文件'],'选择范围（技术）':row['选择器'],'输入编号（技术）':row['输入编号或样本类别'],
            '内容指纹（技术）':row['内容指纹'],'对象序号（技术）':row['对象序号'],
        })
    start=[{
        '合同ID':contract_id,'事实底座记录数':len(records),
        '用户原话空值数':sum(record.get('user_statement') is None for record in records),
    }]
    return {
        '从这里开始':start,'对象目录':directory,'事件时间线':timeline,'关系与归属':relations,
        '特殊对象与边界':special,'来源追溯':lineage,'输入范围':inputs,'技术原文':legacy['技术原文'],
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
                if header in {
                    '类别','样本类别','输入编号或样本类别','涉及样本',
                    '样本标签（技术）','这是什么','输入编号（技术）',
                } and isinstance(value,str):
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
  if (!["类别","样本类别","输入编号或样本类别","涉及样本","样本标签（技术）","这是什么","输入编号（技术）"].includes(header) || typeof normalized!=="string") return normalized;
  let display=normalized;
  for (const [technical,plain] of Object.entries(categoryLabels)) display=display.split(technical).join(plain);
  return display;
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
function setColumnWidths(sheet,widths,lastRow) {
  widths.forEach((width,index)=>sheet.getRange(`${colLabel(index)}1:${colLabel(index)}${lastRow}`).format.columnWidth=width);
}

await fs.mkdir(path.dirname(outputPath),{recursive:true});
await fs.mkdir(previewDir,{recursive:true});
const landing=workbook.worksheets.add("从这里开始");
landing.showGridLines=false;
landing.tabColor=cfg.tab_colors[0];
landing.mergeCells("A1:H1");
landing.getRange("A1").values=[["用户核对版｜先从一笔交易看起"]];
landing.getRange("A1:H1").format={fill:"#17365D",font:{name:cfg.font_family,size:18,bold:true,color:"#FFFFFF"},verticalAlignment:"center"};
landing.getRange("A1:H1").format.rowHeight=38;
landing.mergeCells("A2:H3");
landing.getRange("A2").values=[["这不是136笔正式交易链，也不是分析报告。它只用少量困难样本测试：同一批客观记录能不能让用户和人工智能连续读懂。"]];
landing.getRange("A2:H3").format={fill:"#EAF2F8",font:{name:cfg.font_family,size:12,bold:true,color:"#1F2937"},wrapText:true,verticalAlignment:"center",borders:{preset:"outside",style:"thin",color:"#9FBAD0"}};
landing.getRange("A2:H2").format.rowHeight=34;
landing.getRange("A3:H3").format.rowHeight=36;
landing.getRange("A4:H4").format.rowHeight=58;
landing.getRange("A10:H10").format.rowHeight=58;
for (const [row,value] of [[5,"按这四步看，不需要先懂技术名词"],[11,"你真正需要核对什么"],[16,"颜色和提醒怎么理解"],[21,"这份表没有替你决定的事情"],[27,"技术身份（只供复核）"]]) {
  landing.mergeCells(`A${row}:H${row}`); landing.getRange(`A${row}`).values=[[value]];
  landing.getRange(`A${row}:H${row}`).format={fill:row===21?"#9A6700":"#0F766E",font:{name:cfg.font_family,size:12,bold:true,color:"#FFFFFF"},verticalAlignment:"center"};
  landing.getRange(`A${row}:H${row}`).format.rowHeight=26;
}
const steps=[
  [6,"1","到“对象目录”挑一个对象。第一次建议看 T120（开仓尝试、撤单和替换）或 T087（同秒两条合法路径）。"],
  [7,"2","到“事件时间线”按同一个对象连续看。前六列已经把时间、发生了什么、确定程度、未知和核对动作放在一起。"],
  [8,"3","如果想知道两条记录为什么连在一起，再看“关系与归属”。候选关系仍然只按候选理解。"],
  [9,"4","只有需要追查原始位置时，才看“来源追溯”。“输入范围”和“技术原文”不是普通用户必须阅读的页面。"],
];
for (const [row,number,value] of steps) {
  landing.mergeCells(`A${row}:B${row}`); landing.mergeCells(`C${row}:H${row}`);
  landing.getRange(`A${row}`).values=[[number]]; landing.getRange(`C${row}`).values=[[value]];
  landing.getRange(`A${row}:B${row}`).format={fill:"#2F75B5",font:{name:cfg.font_family,size:16,bold:true,color:"#FFFFFF"},horizontalAlignment:"center",verticalAlignment:"center",borders:{preset:"all",style:"thin",color:"#B4C6E7"}};
  landing.getRange(`C${row}:H${row}`).format={fill:"#FFFFFF",font:{name:cfg.font_family,size:11,color:"#1F2937"},wrapText:true,verticalAlignment:"center",borders:{preset:"all",style:"thin",color:"#B4C6E7"}};
  landing.getRange(`A${row}:H${row}`).format.rowHeight=42;
}
for (const [row,label,value] of [
  [12,"发生了什么","看“事件时间线”的普通中文说明是否能够顺着时间读下去。"],
  [13,"哪里不确定","黄色提醒必须继续写成未知、多个候选、区间或冲突，不能为了整齐挑一个当真。"],
  [14,"用户要做什么","只按每行“你需要核对什么”行动；没有要求你为每条记录补写原话或重新判断业务。只有你实际看懂，用户版才算通过，程序或人工智能检查不能替代。"],
]) {
  landing.mergeCells(`A${row}:B${row}`); landing.mergeCells(`C${row}:H${row}`);
  landing.getRange(`A${row}`).values=[[label]]; landing.getRange(`C${row}`).values=[[value]];
  landing.getRange(`A${row}:B${row}`).format={fill:"#D9EAD3",font:{name:cfg.font_family,size:10,bold:true,color:"#274E13"},verticalAlignment:"center",borders:{preset:"all",style:"thin",color:"#A9D18E"}};
  landing.getRange(`C${row}:H${row}`).format={fill:"#F7FCF5",font:{name:cfg.font_family,size:10,color:"#1F2937"},wrapText:true,verticalAlignment:"center",borders:{preset:"all",style:"thin",color:"#A9D18E"}};
  landing.getRange(`A${row}:H${row}`).format.rowHeight=34;
}
for (const [row,label,value,fill,color] of [
  [17,"蓝色或绿色","普通导航或已有直接记录；可以按时间连续阅读。","#DDEBF7","#1F4E78"],
  [18,"黄色或橙色","有未知、候选、区间或冲突；必须保留原边界，不能自行补答案。","#FFF2CC","#9C5700"],
  [19,"灰色技术列","为人工智能和复核者保留；用户第一次核对时可以不看。","#E7E6E6","#595959"],
]) {
  landing.mergeCells(`A${row}:B${row}`); landing.mergeCells(`C${row}:H${row}`);
  landing.getRange(`A${row}`).values=[[label]]; landing.getRange(`C${row}`).values=[[value]];
  landing.getRange(`A${row}:B${row}`).format={fill,font:{name:cfg.font_family,size:10,bold:true,color},verticalAlignment:"center",borders:{preset:"all",style:"thin",color:"#D0D0D0"}};
  landing.getRange(`C${row}:H${row}`).format={fill:"#FFFFFF",font:{name:cfg.font_family,size:10,color:"#1F2937"},wrapText:true,verticalAlignment:"center",borders:{preset:"all",style:"thin",color:"#D0D0D0"}};
  landing.getRange(`A${row}:H${row}`).format.rowHeight=32;
}
const landingInfo=payload["从这里开始"][0];
for (const [row,label,value] of [
  [22,"44项候选","仍未正式采用；本表出现它们不等于用户已经同意使用。"],
  [23,"136笔构建","还没有开始；本表只有获准的小范围困难样本。"],
  [24,"真实重新计算","没有运行；这里只保留当前获准范围内的测试结果。"],
  [25,"用户原话层",`${landingInfo["用户原话空值数"]} 条机器记录里的“用户原话”字段（技术名 user_statement）都是空值。这只说明本次小范围事实底座没有装入用户原话层，不能证明历史里没有用户说明，也不表示用户要为 ${landingInfo["用户原话空值数"]} 条记录逐条补话。`],
  [26,"分析方法","本表只检验客观事实怎样让人看懂，不做交易分析。以后正式分析采用什么方法、怎样结合用户语义和人工复盘，仍需单独确认。"],
]) {
  landing.mergeCells(`A${row}:B${row}`); landing.mergeCells(`C${row}:H${row}`);
  landing.getRange(`A${row}`).values=[[label]]; landing.getRange(`C${row}`).values=[[value]];
  landing.getRange(`A${row}:B${row}`).format={fill:"#FCE4D6",font:{name:cfg.font_family,size:10,bold:true,color:"#C65911"},verticalAlignment:"center",borders:{preset:"all",style:"thin",color:"#F4B183"}};
  landing.getRange(`C${row}:H${row}`).format={fill:"#FFF8F3",font:{name:cfg.font_family,size:10,color:"#1F2937"},wrapText:true,verticalAlignment:"center",borders:{preset:"all",style:"thin",color:"#F4B183"}};
  landing.getRange(`A${row}:H${row}`).format.rowHeight=row===25?54:40;
}
landing.mergeCells("A28:B28"); landing.mergeCells("C28:H28");
landing.getRange("A28").values=[["事实底座"]];
landing.getRange("C28").values=[[`${landingInfo["事实底座记录数"]} 条；SHA-256：${landingInfo["事实底座SHA-256"]}；合同：${landingInfo["合同ID"]}`]];
landing.getRange("A28:B28").format={fill:"#E7E6E6",font:{name:cfg.font_family,size:9,bold:true,color:"#595959"},verticalAlignment:"center",borders:{preset:"all",style:"thin",color:"#BFBFBF"}};
landing.getRange("C28:H28").format={fill:"#F2F2F2",font:{name:cfg.font_family,size:8,color:"#595959"},wrapText:true,verticalAlignment:"center",borders:{preset:"all",style:"thin",color:"#BFBFBF"}};
landing.getRange("A28:H28").format.rowHeight=36;
setColumnWidths(landing,[10,10,18,18,18,18,18,18],28); landing.freezePanes.freezeRows(3);

for (let sheetIndex=1;sheetIndex<sheetOrder.length;sheetIndex+=1) {
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
  const lastCol=colLabel(headers.length-1),userColumnCount=cfg.user_column_counts[name];
  const userLastCol=userColumnCount>0?colLabel(userColumnCount-1):lastCol;
  const lastRow=rows.length+3;
  sheet.mergeCells(`A1:${userLastCol}1`);
  sheet.getRange("A1").values=[[cfg.titles[name]]];
  sheet.getRange(`A1:${userLastCol}1`).format={fill:"#17365D",font:{name:cfg.font_family,size:16,bold:true,color:"#FFFFFF"},verticalAlignment:"center"};
  sheet.getRange(`A1:${userLastCol}1`).format.rowHeight=32;
  sheet.mergeCells(`A2:${userLastCol}2`);
  sheet.getRange("A2").values=[[cfg.subtitles[name]]];
  sheet.getRange(`A2:${userLastCol}2`).format={fill:"#DCE6F1",font:{name:cfg.font_family,size:10,color:"#334155"},wrapText:true,verticalAlignment:"center"};
  sheet.getRange(`A2:${userLastCol}2`).format.rowHeight=40;
  if (userColumnCount>0 && userColumnCount<headers.length) {
    const techStart=colLabel(userColumnCount);
    sheet.mergeCells(`${techStart}1:${lastCol}1`); sheet.getRange(`${techStart}1`).values=[["右侧是技术明细，普通核对可以不看"]];
    sheet.getRange(`${techStart}1:${lastCol}1`).format={fill:"#475569",font:{name:cfg.font_family,size:11,bold:true,color:"#FFFFFF"},wrapText:true,verticalAlignment:"center"};
    sheet.mergeCells(`${techStart}2:${lastCol}2`); sheet.getRange(`${techStart}2`).values=[["这些列只为保留编号、原值和复核路径；不需要用户第一次阅读。"]];
    sheet.getRange(`${techStart}2:${lastCol}2`).format={fill:"#E2E8F0",font:{name:cfg.font_family,size:9,color:"#475569"},wrapText:true,verticalAlignment:"center"};
  }
  sheet.getRange(`A3:${lastCol}3`).values=[headers];
  sheet.getRange(`A3:${lastCol}3`).format={fill:"#2F75B5",font:{name:cfg.font_family,size:10,bold:true,color:"#FFFFFF"},wrapText:true,verticalAlignment:"center",borders:{preset:"all",style:"thin",color:"#B4C6E7"}};
  if (userColumnCount<headers.length) sheet.getRange(`${colLabel(userColumnCount)}3:${lastCol}3`).format.fill="#64748B";
  sheet.getRange(`A3:${lastCol}3`).format.rowHeight=42;
  sheet.getRange(`A4:${lastCol}${lastRow}`).values=matrix;
  sheet.getRange(`A4:${lastCol}${lastRow}`).format={font:{name:cfg.font_family,size:9,color:"#1F2937"},wrapText:true,verticalAlignment:"top",borders:{preset:"all",style:"thin",color:"#D9E2F3"}};
  sheet.getRange(`A4:${lastCol}${lastRow}`).format.rowHeight=cfg.row_heights[name];
  sheet.getRange(`A4:${lastCol}${lastRow}`).setNumberFormat("@");
  if (userColumnCount<headers.length) {
    const techStart=colLabel(userColumnCount);
    sheet.getRange(`${techStart}4:${lastCol}${lastRow}`).format={fill:"#F1F5F9",font:{name:cfg.font_family,size:8,color:"#475569"},wrapText:true,verticalAlignment:"top",borders:{preset:"all",style:"thin",color:"#CBD5E1"}};
  }
  setColumnWidths(sheet,cfg.column_widths[name],lastRow);
  const table=sheet.tables.add(`A3:${lastCol}${lastRow}`,true,`UserView${String(sheetIndex+1).padStart(2,"0")}`);
  table.style=name==="技术原文"?"TableStyleMedium4":"TableStyleMedium2";
  table.showHeaders=true;
  table.showBandedColumns=false;
  table.showFilterButton=true;
  sheet.freezePanes.freezeRows(3);
  sheet.freezePanes.freezeColumns(name==="技术原文"?2:Math.min(2,userColumnCount));
  if (name==="事件时间线") {
    sheet.getRange(`E4:E${lastRow}`).conditionalFormats.add("containsText",{text:"未知",format:{fill:"#FFF2CC",font:{color:"#9C5700",bold:true}}});
    sheet.getRange(`E4:E${lastRow}`).conditionalFormats.add("containsText",{text:"候选",format:{fill:"#FCE4D6",font:{color:"#C65911",bold:true}}});
    sheet.getRange(`E4:E${lastRow}`).conditionalFormats.add("containsText",{text:"冲突",format:{fill:"#F4CCCC",font:{color:"#9C0006",bold:true}}});
    sheet.getRange(`F4:F${lastRow}`).conditionalFormats.add("containsText",{text:"确认",format:{fill:"#FFF2CC",font:{color:"#7F6000",bold:true}}});
  }
  if (name==="关系与归属") {
    sheet.getRange(`C4:C${lastRow}`).conditionalFormats.add("containsText",{text:"候选",format:{fill:"#FCE4D6",font:{color:"#C65911",bold:true}}});
    sheet.getRange(`E4:E${lastRow}`).conditionalFormats.add("containsText",{text:"确认",format:{fill:"#FFF2CC",font:{color:"#7F6000",bold:true}}});
  }
}
workbook.recalculate();
for (const name of sheetOrder) {
  const preview=await workbook.render({sheetName:name,range:cfg.render_ranges[name],scale:1.15,format:"png"});
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
  if (name==="从这里开始") {
    const values=imported.worksheets.getItem(name).getUsedRange().values;
    const text=values.flat().map(String).join("\n");
    sheetChecks[name]={
      headers_exact:true,row_count_expected:1,row_count_actual:1,
      all_display_values_exact:text.includes("不是136笔正式交易链") && text.includes("程序或人工智能检查不能替代") && text.includes(landingInfo["事实底座SHA-256"]),
      first_difference:null,
    };
    continue;
  }
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

COMPACT_AI_DIRECT_FIELDS=(
    'stable_display_sequence','fact_id','canonical_record_sha256','raw_value_sha256',
)
COMPACT_AI_SEMANTIC_FIELDS=('normalized_value','relation','source_identity')
COMPACT_AI_DICTIONARY_FIELDS=(
    'record_type','navigation_object_id','object_class','object_id','trade_id','position_cycle_id','symbol',
    'plain_summary','event_time_original','time','evidence_status','source_evidence_status','execution_status',
    'adoption_status','applicability_scope','applied_capability_ids','candidate_capability_spec_ids',
    'capability_application_status','conflict_ids','relation_ids','input_id','selected_object_index','source_table',
    'source_event_id','source_identity_id','source_path','source_sha256','source_row','can_prove','cannot_prove',
    'value_state','user_statement','ai_interpretation','units','currency','sample_categories','fact_subtype',
    'endpoint_reference_only','target_object_type','target_object_id','target_candidate_ids','promotion_prohibited',
    'source_relation_types','supporting_relation_ids','supporting_source_rows',
)
COMPACT_AI_FIELDS=COMPACT_AI_DIRECT_FIELDS+COMPACT_AI_SEMANTIC_FIELDS+COMPACT_AI_DICTIONARY_FIELDS
COMPACT_AI_SECTION_BY_RECORD_TYPE={
    'FACT_STATEMENT':'F','RELATION_STATEMENT':'R','LINEAGE_STATEMENT':'L','METHOD_EVIDENCE':'M',
}

def compact_collect_semantic_strings(value,counter):
    if isinstance(value,str): counter[value]+=1
    elif isinstance(value,dict):
        for item in value.values(): compact_collect_semantic_strings(item,counter)
    elif isinstance(value,list):
        for item in value: compact_collect_semantic_strings(item,counter)

def compact_collect_schema_keys(value,keys):
    if isinstance(value,dict):
        keys.add(tuple(sorted(value)))
        for item in value.values(): compact_collect_schema_keys(item,keys)
    elif isinstance(value,list):
        for item in value: compact_collect_schema_keys(item,keys)

def compact_semantic_codecs(records):
    string_counts=Counter(); schema_keys=set()
    for record in records:
        for field in COMPACT_AI_SEMANTIC_FIELDS:
            value=record.get(field)
            compact_collect_semantic_strings(value,string_counts)
            compact_collect_schema_keys(value,schema_keys)
    # Only repeated, non-trivial strings are interned.  Sorting makes the code
    # assignment independent of source traversal order.
    strings=sorted(
        value for value,count in string_counts.items()
        if count>=2 and len(canonical(value).encode('utf-8'))>=8
    )
    schemas=[list(item) for item in sorted(schema_keys)]
    return strings,{value:index for index,value in enumerate(strings)},schemas,{tuple(value):index for index,value in enumerate(schemas)}

def compact_encode_semantic(value,string_index,schema_index):
    if isinstance(value,str):
        return -1-string_index[value] if value in string_index else value
    if isinstance(value,bool) or value is None: return value
    if isinstance(value,(int,float)):
        if value<0: raise RuntimeError('COMPACT_AI_NEGATIVE_NUMBER_COLLIDES_WITH_STRING_CODE')
        return value
    if isinstance(value,dict):
        keys=tuple(sorted(value))
        return ['@',schema_index[keys],[compact_encode_semantic(value[key],string_index,schema_index) for key in keys]]
    if isinstance(value,list):
        if len(value)==3 and value[0]=='@': raise RuntimeError('COMPACT_AI_RESERVED_LIST_SHAPE_COLLISION')
        return [compact_encode_semantic(item,string_index,schema_index) for item in value]
    raise RuntimeError('COMPACT_AI_UNSUPPORTED_SEMANTIC_VALUE:'+type(value).__name__)

def compact_decode_semantic(value,strings,schemas):
    if isinstance(value,bool) or value is None: return value
    if isinstance(value,int) and value<0:
        index=-1-value
        if index<0 or index>=len(strings): raise RuntimeError('COMPACT_AI_STRING_CODE_OUT_OF_RANGE')
        return strings[index]
    if isinstance(value,list):
        if len(value)==3 and value[0]=='@':
            schema_index=value[1]
            if not isinstance(schema_index,int) or schema_index<0 or schema_index>=len(schemas):
                raise RuntimeError('COMPACT_AI_SCHEMA_CODE_OUT_OF_RANGE')
            keys=schemas[schema_index]; values=value[2]
            if not isinstance(values,list) or len(keys)!=len(values):
                raise RuntimeError('COMPACT_AI_SCHEMA_VALUE_COUNT_MISMATCH')
            return {key:compact_decode_semantic(item,strings,schemas) for key,item in zip(keys,values)}
        return [compact_decode_semantic(item,strings,schemas) for item in value]
    return value

def compact_value_dictionaries(records):
    dictionaries={}
    indexes={}
    for field in COMPACT_AI_DICTIONARY_FIELDS:
        by_canonical={canonical(record.get(field)):record.get(field) for record in records}
        values=[by_canonical[key] for key in sorted(by_canonical)]
        dictionaries[field]=values
        indexes[field]={canonical(value):index for index,value in enumerate(values)}
    return dictionaries,indexes

def compact_ai_record(record,string_index,schema_index,dictionary_indexes):
    mapped=(set(COMPACT_AI_DIRECT_FIELDS)-{'canonical_record_sha256','raw_value_sha256'})|set(COMPACT_AI_SEMANTIC_FIELDS)|set(COMPACT_AI_DICTIONARY_FIELDS)|{'raw_value'}
    unmapped=set(record)-mapped
    if unmapped: raise RuntimeError('COMPACT_AI_UNMAPPED_SOURCE_FIELD:'+','.join(sorted(unmapped)))
    direct={
        'stable_display_sequence':record['stable_display_sequence'],
        'fact_id':record['fact_id'],
        'canonical_record_sha256':hashlib.sha256(canonical(record).encode('utf-8')).hexdigest(),
        'raw_value_sha256':hashlib.sha256(canonical(record.get('raw_value')).encode('utf-8')).hexdigest(),
    }
    values=[]
    for field in COMPACT_AI_FIELDS:
        if field in direct: values.append(direct[field])
        elif field in COMPACT_AI_SEMANTIC_FIELDS:
            values.append(compact_encode_semantic(record.get(field),string_index,schema_index))
        else:
            values.append(dictionary_indexes[field][canonical(record.get(field))])
    return values

def compact_fact_time_domain(record):
    time=record.get('time') or {}
    if time.get('normalized_utc'): return 'NORMALIZED_UTC',time['normalized_utc']
    if time.get('beijing_time'): return 'SOURCE_BEIJING_TIME',time['beijing_time']
    if record.get('event_time_original'): return 'SOURCE_LOCAL_TIME_TIMEZONE_UNKNOWN',record['event_time_original']
    return 'UNTIMED',None

def compact_fact_time_key(record):
    domain,value=compact_fact_time_domain(record)
    domain_order={'NORMALIZED_UTC':0,'SOURCE_BEIJING_TIME':1,'SOURCE_LOCAL_TIME_TIMEZONE_UNKNOWN':2,'UNTIMED':3}
    return (domain_order[domain],str(value or ''),int(record['stable_display_sequence']))

def stable_unique(values):
    result=[]; seen=set()
    for value in values:
        if value not in seen: seen.add(value); result.append(value)
    return result

def compact_ai_document(records,fact_path,sample_manifest):
    strings,string_index,schemas,schema_index=compact_semantic_codecs(records)
    dictionaries,dictionary_indexes=compact_value_dictionaries(records)
    rows_by_fact_id={
        record['fact_id']:compact_ai_record(record,string_index,schema_index,dictionary_indexes)
        for record in records
    }
    grouped=defaultdict(list)
    for record in records: grouped[record['navigation_object_id']].append(record)
    objects=[]
    record_by_fact_id={record['fact_id']:record for record in records}
    for object_id in sorted(grouped,key=navigation_sort_key):
        group=grouped[object_id]
        sections={
            'F':sorted((item for item in group if item['record_type']=='FACT_STATEMENT'),key=compact_fact_time_key),
            'R':sorted((item for item in group if item['record_type']=='RELATION_STATEMENT'),key=lambda item:item['stable_display_sequence']),
            'L':sorted((item for item in group if item['record_type']=='LINEAGE_STATEMENT'),key=lambda item:item['stable_display_sequence']),
            'M':sorted((item for item in group if item['record_type']=='METHOD_EVIDENCE'),key=lambda item:item['stable_display_sequence']),
        }
        time_groups=defaultdict(list); untimed=[]
        for item in sections['F']:
            domain,_value=compact_fact_time_domain(item)
            (untimed if domain=='UNTIMED' else time_groups[domain]).append(item['fact_id'])
        owned=[item['fact_id'] for item in sections['R']]
        incoming=[]; outgoing=[]
        for relation_record in (item for item in records if item['record_type']=='RELATION_STATEMENT'):
            relation=relation_record.get('relation') or {}
            source=record_by_fact_id.get(relation.get('source_fact_id'))
            target=record_by_fact_id.get(relation.get('target_fact_id'))
            if source and source['navigation_object_id']==object_id and relation_record['navigation_object_id']!=object_id:
                outgoing.append(relation_record['fact_id'])
            if target and target['navigation_object_id']==object_id and relation_record['navigation_object_id']!=object_id:
                incoming.append(relation_record['fact_id'])
        unmatched_lineage=[]
        fact_events={item.get('source_event_id') for item in sections['F'] if item.get('source_event_id')}
        for item in sections['L']:
            if item.get('source_event_id') not in fact_events: unmatched_lineage.append(item['fact_id'])
        all_relation_ids=sorted(stable_unique(owned+incoming+outgoing),key=lambda fact_id:record_by_fact_id[fact_id]['stable_display_sequence'])
        objects.append({
            'navigation_object_id':object_id,
            'counts':{key:len(value) for key,value in sections.items()},
            'fact_time_groups':dict(time_groups),
            'fact_timeline_ids':[item['fact_id'] for item in sections['F'] if compact_fact_time_domain(item)[0]!='UNTIMED'],
            'untimed_fact_ids':untimed,
            'owned_relation_fact_ids':owned,
            'incoming_relation_fact_ids':sorted(incoming,key=lambda fact_id:record_by_fact_id[fact_id]['stable_display_sequence']),
            'outgoing_relation_fact_ids':sorted(outgoing,key=lambda fact_id:record_by_fact_id[fact_id]['stable_display_sequence']),
            'relation_fact_ids':all_relation_ids,
            'lineage_fact_ids':[item['fact_id'] for item in sections['L']],
            'unmatched_lineage_fact_ids':unmatched_lineage,
            'method_fact_ids':[item['fact_id'] for item in sections['M']],
            'sections':sections,
        })
    header={
        'k':'HEADER','representation_version':'2.0',
        'identity':'同一事实底座的完整规范事实语义紧凑读取版，不是第二套事实。',
        'authoritative_fact_base':Path(fact_path).name,
        'authoritative_fact_base_bytes':Path(fact_path).stat().st_size,
        'authoritative_fact_base_sha256':sha_file(fact_path),
        'record_count':len(records),'object_count':len(objects),
        'row_fields':list(COMPACT_AI_FIELDS),
        'row_locator_fields':['stable_display_sequence','fact_id','canonical_record_sha256'],
        'stable_display_sequence_meaning':'SOURCE_FACT_BASE_STABLE_DISPLAY_SEQUENCE_NOT_COMPACT_PHYSICAL_ROW_AND_NOT_CAUSAL_ORDER',
        'normalized_value_policy':'FULL_EXACT_VALUE_PRESERVED_AND_DECODABLE',
        'raw_value_policy':'SHA256_ONLY; FULL_VALUE_IN_AUTHORITATIVE_FACT_BASE_LOCATED_BY_SEQUENCE_FACT_ID_AND_RECORD_SHA256',
        'section_order':['F_FACTS_GROUPED_BY_COMPARABLE_TIME_DOMAIN_UNTIMED_LAST','R_OWNED_RELATION_BODIES','L_LINEAGE','M_METHOD'],
        'time_order_boundary':'ONLY_SORT_WITHIN_THE_SAME_RELIABLE_TIME_DOMAIN; DOMAIN_ORDER_IS_DISPLAY_ONLY; UNKNOWN_TIMEZONE_VALUES_ARE_NOT_COMPARED_TO_UTC_OR_BEIJING_VALUES',
        'dictionary_rule':'D记录按name给出完整值数组；行内整数是对应字段字典的下标。',
        'semantic_rule':'S记录保存规范值、关系和来源身份中的重复字符串与对象字段模板；负整数表示S.strings下标，[@,模板下标,值数组]可无损还原对象。',
        'sample_category_count':len(sample_manifest['selected_by_category']),
        'formal_adoption':False,
    }
    return header,strings,schemas,dictionaries,rows_by_fact_id,objects

def compact_chunked(values,limit=200):
    for start in range(0,len(values),limit): yield start,values[start:start+limit]

def build_compact_ai_view_text(records,fact_path,sample_manifest,view):
    header,strings,schemas,dictionaries,rows_by_fact_id,objects=compact_ai_document(records,fact_path,sample_manifest)
    lines=[view['ai_view']['title'],'',view['ai_view']['boundary'],'','## 机器可直接还原的紧凑格式','',
           '每条事实先按对象归组；对象内先给事实时间线，再给关系、来源追溯和方法。`10_有界测试事实底座候选.jsonl`仍是唯一完整原值底座。','',
           '```jsonl',canonical(header)]
    for start,values in compact_chunked(strings):
        lines.append(canonical({'k':'S','name':'strings','start':start,'values':values}))
    for start,values in compact_chunked(schemas):
        lines.append(canonical({'k':'S','name':'schemas','start':start,'values':values}))
    for field in COMPACT_AI_DICTIONARY_FIELDS:
        for start,values in compact_chunked(dictionaries[field]):
            lines.append(canonical({'k':'D','name':field,'start':start,'values':values}))
    for package in objects:
        lines.append(canonical({key:value for key,value in package.items() if key!='sections'}|{'k':'O'}))
        for section in ('F','R','L','M'):
            for record in package['sections'][section]:
                lines.append(canonical({'k':section,'v':rows_by_fact_id[record['fact_id']]}))
        lines.append(canonical({'k':'E','navigation_object_id':package['navigation_object_id']}))
    lines.extend(['```','','## 读取边界',''])
    lines.extend(f'- {item}' for item in view['ai_view']['closing_boundaries'])
    return '\n'.join(lines)+'\n'

def compact_ai_parse(text):
    parsed=[]; inside=False
    for line in text.splitlines():
        if line=='```jsonl': inside=True
        elif line=='```' and inside: inside=False
        elif inside and line.strip(): parsed.append(json.loads(line))
    if not parsed or parsed[0].get('k')!='HEADER': raise RuntimeError('COMPACT_AI_HEADER_MISSING')
    header=parsed[0]; dictionaries=defaultdict(list); strings=[]; schemas=[]; objects=[]; rows=[]; current=None; object_started=False
    for item in parsed[1:]:
        kind=item.get('k')
        if kind in {'S','D'}:
            if object_started: raise RuntimeError('COMPACT_AI_DICTIONARY_AFTER_OBJECT_START')
            if (kind=='S' and item.get('name') not in {'strings','schemas'}) or (kind=='D' and item.get('name') not in COMPACT_AI_DICTIONARY_FIELDS):
                raise RuntimeError('COMPACT_AI_DICTIONARY_NAME_INVALID')
            target=(strings if item['name']=='strings' else schemas if item['name']=='schemas' else dictionaries[item['name']])
            if item['start']!=len(target): raise RuntimeError('COMPACT_AI_DICTIONARY_CHUNK_GAP:'+item['name'])
            target.extend(item['values'])
        elif kind=='O':
            object_started=True
            if current is not None: raise RuntimeError('COMPACT_AI_OBJECT_NESTING_INVALID')
            current=item; current['actual_section_ids']={key:[] for key in ('F','R','L','M')}; objects.append(current)
        elif kind in {'F','R','L','M'}:
            if current is None: raise RuntimeError('COMPACT_AI_ROW_OUTSIDE_OBJECT')
            current['actual_section_ids'][kind].append(item['v'][1]); rows.append((kind,item['v'],current['navigation_object_id']))
        elif kind=='E':
            if current is None or item['navigation_object_id']!=current['navigation_object_id']:
                raise RuntimeError('COMPACT_AI_OBJECT_END_MISMATCH')
            current=None
        else: raise RuntimeError('COMPACT_AI_UNKNOWN_LINE_TYPE:'+str(kind))
    if current is not None: raise RuntimeError('COMPACT_AI_OBJECT_NOT_CLOSED')
    return header,strings,schemas,dict(dictionaries),objects,rows

def validate_compact_ai_view(text,records,fact_path,maximum_bytes=4*1024*1024):
    header,strings,schemas,dictionaries,objects,rows=compact_ai_parse(text)
    if len(text.encode('utf-8'))>=maximum_bytes: raise RuntimeError('COMPACT_AI_VIEW_TOO_LARGE')
    fact_path=Path(fact_path)
    if (
        header.get('record_count')!=len(records) or header.get('row_fields')!=list(COMPACT_AI_FIELDS)
        or header.get('authoritative_fact_base')!=fact_path.name
        or header.get('authoritative_fact_base_bytes')!=fact_path.stat().st_size
        or header.get('authoritative_fact_base_sha256')!=sha_file(fact_path)
    ):
        raise RuntimeError('COMPACT_AI_HEADER_IDENTITY_MISMATCH')
    if set(dictionaries)!=set(COMPACT_AI_DICTIONARY_FIELDS):
        raise RuntimeError('COMPACT_AI_DICTIONARY_SET_MISMATCH')
    expected_strings,_string_index,expected_schemas,_schema_index=compact_semantic_codecs(records)
    expected_dictionaries,_dictionary_indexes=compact_value_dictionaries(records)
    if strings!=expected_strings or schemas!=expected_schemas or dictionaries!=expected_dictionaries:
        raise RuntimeError('COMPACT_AI_DICTIONARY_CANONICALIZATION_MISMATCH')
    field_index={field:index for index,field in enumerate(COMPACT_AI_FIELDS)}
    original_by_id={record['fact_id']:record for record in records}
    if len(rows)!=len(records) or {row[field_index['fact_id']] for _kind,row,_object in rows}!=set(original_by_id):
        raise RuntimeError('COMPACT_AI_VIEW_FACT_COVERAGE_FAILED')
    for kind,row,object_id in rows:
        fact_id=row[field_index['fact_id']]; record=original_by_id[fact_id]
        if COMPACT_AI_SECTION_BY_RECORD_TYPE[record['record_type']]!=kind or record['navigation_object_id']!=object_id:
            raise RuntimeError('COMPACT_AI_OBJECT_OR_SECTION_MISMATCH:'+fact_id)
        if row[field_index['stable_display_sequence']]!=record['stable_display_sequence']:
            raise RuntimeError('COMPACT_AI_SEQUENCE_MISMATCH:'+fact_id)
        if row[field_index['canonical_record_sha256']]!=hashlib.sha256(canonical(record).encode('utf-8')).hexdigest():
            raise RuntimeError('COMPACT_AI_CANONICAL_RECORD_SHA256_MISMATCH:'+fact_id)
        if row[field_index['raw_value_sha256']]!=hashlib.sha256(canonical(record.get('raw_value')).encode('utf-8')).hexdigest():
            raise RuntimeError('COMPACT_AI_RAW_VALUE_SHA256_MISMATCH:'+fact_id)
        for field in COMPACT_AI_SEMANTIC_FIELDS:
            if compact_decode_semantic(row[field_index[field]],strings,schemas)!=record.get(field):
                raise RuntimeError('COMPACT_AI_SEMANTIC_FIELD_MISMATCH:'+fact_id+':'+field)
        for field in COMPACT_AI_DICTIONARY_FIELDS:
            index=row[field_index[field]]; values=dictionaries[field]
            if not isinstance(index,int) or index<0 or index>=len(values) or values[index]!=record.get(field):
                raise RuntimeError('COMPACT_AI_DICTIONARY_FIELD_MISMATCH:'+fact_id+':'+field)
    actual_object_ids=[item['navigation_object_id'] for item in objects]
    expected_object_ids=sorted({record['navigation_object_id'] for record in records},key=navigation_sort_key)
    if header.get('object_count')!=len(objects) or actual_object_ids!=expected_object_ids or len(actual_object_ids)!=len(set(actual_object_ids)):
        raise RuntimeError('COMPACT_AI_OBJECT_COUNT_UNIQUENESS_OR_ORDER_MISMATCH')
    package_by_id={item['navigation_object_id']:item for item in objects}
    grouped=defaultdict(list)
    for record in records: grouped[record['navigation_object_id']].append(record)
    if set(package_by_id)!=set(grouped): raise RuntimeError('COMPACT_AI_OBJECT_COVERAGE_MISMATCH')
    for object_id,group in grouped.items():
        package=package_by_id[object_id]
        expected={
            'F':[item['fact_id'] for item in sorted((x for x in group if x['record_type']=='FACT_STATEMENT'),key=compact_fact_time_key)],
            'R':[item['fact_id'] for item in sorted((x for x in group if x['record_type']=='RELATION_STATEMENT'),key=lambda x:x['stable_display_sequence'])],
            'L':[item['fact_id'] for item in sorted((x for x in group if x['record_type']=='LINEAGE_STATEMENT'),key=lambda x:x['stable_display_sequence'])],
            'M':[item['fact_id'] for item in sorted((x for x in group if x['record_type']=='METHOD_EVIDENCE'),key=lambda x:x['stable_display_sequence'])],
        }
        record_by_fact_id={record['fact_id']:record for record in records}
        time_groups=defaultdict(list); untimed=[]
        for fact_id in expected['F']:
            domain,_value=compact_fact_time_domain(record_by_fact_id[fact_id])
            (untimed if domain=='UNTIMED' else time_groups[domain]).append(fact_id)
        owned=expected['R']; incoming=[]; outgoing=[]
        for relation_record in (item for item in records if item['record_type']=='RELATION_STATEMENT'):
            relation=relation_record.get('relation') or {}
            source=record_by_fact_id.get(relation.get('source_fact_id')); target=record_by_fact_id.get(relation.get('target_fact_id'))
            if source and source['navigation_object_id']==object_id and relation_record['navigation_object_id']!=object_id: outgoing.append(relation_record['fact_id'])
            if target and target['navigation_object_id']==object_id and relation_record['navigation_object_id']!=object_id: incoming.append(relation_record['fact_id'])
        incoming=sorted(incoming,key=lambda fact_id:record_by_fact_id[fact_id]['stable_display_sequence'])
        outgoing=sorted(outgoing,key=lambda fact_id:record_by_fact_id[fact_id]['stable_display_sequence'])
        all_relations=sorted(stable_unique(owned+incoming+outgoing),key=lambda fact_id:record_by_fact_id[fact_id]['stable_display_sequence'])
        fact_events={item.get('source_event_id') for item in group if item['record_type']=='FACT_STATEMENT' and item.get('source_event_id')}
        unmatched=[item['fact_id'] for item in group if item['record_type']=='LINEAGE_STATEMENT' and item.get('source_event_id') not in fact_events]
        if (
            package['actual_section_ids']!=expected
            or package['counts']!={key:len(value) for key,value in expected.items()}
            or package['fact_time_groups']!=dict(time_groups)
            or package['fact_timeline_ids']!=[fact_id for fact_id in expected['F'] if compact_fact_time_domain(record_by_fact_id[fact_id])[0]!='UNTIMED']
            or package['untimed_fact_ids']!=untimed or package['owned_relation_fact_ids']!=owned
            or package['incoming_relation_fact_ids']!=incoming or package['outgoing_relation_fact_ids']!=outgoing
            or package['relation_fact_ids']!=all_relations or package['lineage_fact_ids']!=expected['L']
            or package['unmatched_lineage_fact_ids']!=unmatched or package['method_fact_ids']!=expected['M']
        ):
            raise RuntimeError('COMPACT_AI_OBJECT_INDEX_OR_ORDER_MISMATCH:'+object_id)
    return {
        'record_count':len(rows),'object_count':len(objects),'bytes':len(text.encode('utf-8')),
        'under_4_mib':True,'fact_id_coverage_exact':True,'canonical_locator_exact':True,
        'normalized_value_exact':True,'relation_coverage_exact':True,'source_coverage_exact':True,
        'status_coverage_exact':True,'fact_timeline_first':True,
        'relation_fact_id_index_exact':True,'lineage_fact_id_index_exact':True,
        'cross_object_relation_index_exact':True,'unmatched_lineage_count':sum(len(item['unmatched_lineage_fact_ids']) for item in objects),
        'raw_value_preserved_only_in_fact_base_and_bound_by_sha256':True,
    }

VISUAL_EVIDENCE_LABELS={
    'DIRECT':'直接证据','DETERMINISTIC_DERIVATION':'可重现推导','BOUNDED':'限定范围证据',
    'CANDIDATE':'候选关系','UNKNOWN':'尚不确定','NOT_APPLICABLE':'不适用','NOT_EVALUATED':'尚未判定',
}
VISUAL_RECORD_LABELS={
    'FACT_STATEMENT':'事实事件','RELATION_STATEMENT':'关系连接',
    'LINEAGE_STATEMENT':'来源依据','METHOD_EVIDENCE':'方法与边界',
}
VISUAL_OBJECT_LABELS={
    'T020':'主动交易 T020（长时间线样本）','T087':'主动交易 T087','T092':'主动交易 T092',
    'T093':'主动交易 T093','T112':'主动交易 T112','T120':'主动交易 T120',
    'SHARED_ACCOUNT_EFFECT':'共享账户影响','UNASSIGNED:COND-0218':'无法可靠归属的条件单',
    'U016':'跟单资金影响 U016','CROSS_OBJECT_RELATIONS':'跨对象关系',
    'T087_METHOD':'T087 方法与同秒边界',
}
VISUAL_DETAIL_LABELS={
    'symbol':'交易品种','event_type':'事件类型','action_type':'操作类型','side':'买卖方向',
    'position_direction':'持仓方向','status':'当前状态','order_status':'委托状态','condition_status':'条件单状态',
    'order_id':'委托编号','fill_id':'成交编号','quantity':'数量','order_quantity':'委托数量',
    'executed_quantity':'已成交数量','price':'价格','weighted_price':'加权成交价','trigger_price':'触发价格',
    'fee':'手续费','realized_pnl':'已实现盈亏','position_before':'操作前仓位','position_after':'操作后仓位',
    'amount':'金额','currency':'币种',
}
VISUAL_VALUE_LABELS={
    'BUY':'买入','SELL':'卖出','LONG':'多头','SHORT':'空头','OPEN':'开仓','CLOSE':'平仓',
    'REDUCE':'减仓','INCREASE':'加仓','NEW':'已创建','ACTIVE':'生效中','FILLED':'已成交',
    'PARTIALLY_FILLED':'部分成交','CANCELED':'已取消','CANCELLED':'已取消','EXPIRED':'已过期',
    'REJECTED':'已拒绝','STOP_LOSS':'止损','TAKE_PROFIT':'止盈','MARKET':'市价','LIMIT':'限价',
    'FILL':'成交','ORDER':'委托','POSITION_ACTION':'仓位变化','CONDITIONAL_ORDER_LIFECYCLE':'条件委托变化',
    'EXTERNAL_FUND':'外部资金','TRANSFER':'内部划转','COPY_FUNDS_ONLY':'跟单资金影响',
    'OPEN_INITIAL':'首次开仓','ADD_POSITION':'加仓','REDUCE_POSITION':'减仓','CLOSE_FULL':'全部平仓',
    'COMPLETED':'已完成','UNKNOWN':'尚不确定',
}

def visual_plain_value(value,maximum=180):
    text=canonical(value) if isinstance(value,(dict,list)) else VISUAL_VALUE_LABELS.get(str(value),str(value))
    return text if len(text)<=maximum else text[:maximum-1]+'…'

def visual_record_has_attention(record):
    state=record.get('value_state') or {}
    return bool(
        record.get('evidence_status') in {'UNKNOWN','CANDIDATE','NOT_EVALUATED'}
        or record.get('conflict_ids')
        or any(state.get(key) for key in ('unknown','intervals','candidate_sets'))
        or record.get('record_type')=='METHOD_EVIDENCE'
    )

def visual_record(record):
    normalized=record.get('normalized_value')
    details=[]
    if isinstance(normalized,dict):
        for key,label in VISUAL_DETAIL_LABELS.items():
            if key in normalized and normalized[key] not in (None,'',[],{}):
                details.append({'label':label,'value':visual_plain_value(normalized[key])})
    relation=record.get('relation') or {}
    state=record.get('value_state') or {}
    warning_parts=[]
    if record.get('evidence_status') in {'UNKNOWN','CANDIDATE','NOT_EVALUATED'}:
        warning_parts.append(VISUAL_EVIDENCE_LABELS.get(record.get('evidence_status'),record.get('evidence_status')))
    if record.get('conflict_ids'): warning_parts.append('存在冲突：'+'、'.join(record['conflict_ids']))
    if state.get('unknown'): warning_parts.append('有未知值')
    if state.get('intervals'): warning_parts.append('保留区间值')
    if state.get('candidate_sets'): warning_parts.append('保留多个候选')
    if record.get('record_type')=='METHOD_EVIDENCE': warning_parts.append('这是方法边界，不是新计算结果')
    source_path=str(record.get('source_path') or '')
    return {
        'id':record['fact_id'],'sequence':record['stable_display_sequence'],
        'canonical_record_sha256':hashlib.sha256(canonical(record).encode('utf-8')).hexdigest(),
        'type':record['record_type'],'type_label':VISUAL_RECORD_LABELS[record['record_type']],
        'time':(record.get('time') or {}).get('beijing_time') or record.get('event_time_original') or '时间未记录',
        'summary':record.get('plain_summary') or '当前记录没有白话摘要',
        'evidence':VISUAL_EVIDENCE_LABELS.get(record.get('evidence_status'),record.get('evidence_status')),
        'can_prove':record.get('can_prove') or '',
        'cannot_prove':record.get('cannot_prove') or '',
        'attention':visual_record_has_attention(record),'attention_text':'；'.join(warning_parts),
        'adoption_status':record.get('adoption_status'),'execution_status':record.get('execution_status'),
        'symbol':record.get('symbol'),'details':details,
        'source':{
            'file':Path(source_path).name if source_path else '来源文件未记录',
            'table':record.get('source_table'),'row':record.get('source_row'),
            'path':source_path,'locator':(record.get('source_identity') or {}).get('source_locator'),
        },
        'relation':{
            'type':relation.get('relation_type'),'source':relation.get('source_object_id'),
            'target':relation.get('target_object_id'),'source_fact':relation.get('source_fact_id'),
            'target_fact':relation.get('target_fact_id'),
        } if relation else None,
    }

def build_user_visual_payload(records,fact_path,contract_id):
    grouped=defaultdict(list)
    for record in records: grouped[record['navigation_object_id']].append(record)
    objects=[]
    for object_id in sorted(grouped,key=navigation_sort_key):
        group=sorted(grouped[object_id],key=lambda item:item['stable_display_sequence'])
        times=[item.get('event_time_original') or (item.get('time') or {}).get('beijing_time') for item in group]
        times=[value for value in times if value]
        records_out=[visual_record(item) for item in group]
        counts=Counter(item['record_type'] for item in group)
        classes=sorted({str(item.get('object_class') or '') for item in group if item.get('object_class')})
        symbols=sorted({str(item.get('symbol') or '') for item in group if item.get('symbol')})
        objects.append({
            'id':object_id,'label':VISUAL_OBJECT_LABELS.get(object_id,object_id),
            'object_classes':classes,'symbols':symbols,'record_count':len(group),
            'attention_count':sum(1 for item in records_out if item['attention']),
            'time_start':min(times) if times else '时间未记录','time_end':max(times) if times else '时间未记录',
            'counts':{key:counts.get(key,0) for key in VISUAL_RECORD_LABELS},'records':records_out,
        })
    counts=Counter(record['record_type'] for record in records)
    return {
        'meta':{
            'title':'客观交易链｜用户可视化核对测试版',
            'identity':'这是由同一份有界事实底座自动生成的用户阅读页，不是第二套事实。',
            'boundary':'只展示获准的小范围测试对象；不代表136笔已经建立，不代表候选已经正式采用，也没有运行三项真实重新计算。',
            'contract_id':contract_id,'fact_base_file':Path(fact_path).name,
            'fact_base_bytes':Path(fact_path).stat().st_size,'fact_base_sha256':sha_file(fact_path),
            'record_count':len(records),'object_count':len(objects),
            'record_type_counts':{key:counts.get(key,0) for key in VISUAL_RECORD_LABELS},
            'default_object_id':'T120' if 'T120' in grouped else objects[0]['id'],
            'page_size':25,'user_understandability_status':'WAITING_FOR_USER_ACTUAL_REVIEW',
        },
        'objects':objects,
    }

def validate_user_visual_payload(payload,records,fact_path):
    actual=[item['id'] for obj in payload['objects'] for item in obj['records']]
    expected=[item['fact_id'] for item in records]
    if len(actual)!=len(expected) or len(actual)!=len(set(actual)) or set(actual)!=set(expected):
        raise RuntimeError('USER_VISUAL_RECORD_COVERAGE_MISMATCH')
    if payload['meta']['fact_base_sha256']!=sha_file(fact_path) or payload['meta']['fact_base_bytes']!=Path(fact_path).stat().st_size:
        raise RuntimeError('USER_VISUAL_FACT_BASE_IDENTITY_MISMATCH')
    actual_objects=[obj['id'] for obj in payload['objects']]
    expected_objects=sorted({item['navigation_object_id'] for item in records},key=navigation_sort_key)
    if actual_objects!=expected_objects or len(actual_objects)!=len(set(actual_objects)):
        raise RuntimeError('USER_VISUAL_OBJECT_COVERAGE_OR_ORDER_MISMATCH')
    counts=Counter(item['type'] for obj in payload['objects'] for item in obj['records'])
    if dict(counts)!=dict(Counter(item['record_type'] for item in records)):
        raise RuntimeError('USER_VISUAL_RECORD_TYPE_COUNTS_MISMATCH')
    source_by_id={item['fact_id']:item for item in records}
    for obj in payload['objects']:
        expected_group=sorted(
            (item for item in records if item['navigation_object_id']==obj['id']),
            key=lambda item:item['stable_display_sequence'],
        )
        if [item['id'] for item in obj['records']]!=[item['fact_id'] for item in expected_group]:
            raise RuntimeError('USER_VISUAL_OBJECT_RECORD_ORDER_MISMATCH:'+obj['id'])
        for item in obj['records']:
            expected_hash=hashlib.sha256(canonical(source_by_id[item['id']]).encode('utf-8')).hexdigest()
            if item.get('canonical_record_sha256')!=expected_hash:
                raise RuntimeError('USER_VISUAL_CANONICAL_RECORD_BINDING_MISMATCH:'+item['id'])
    return {
        'record_count':len(actual),'object_count':len(actual_objects),'record_id_coverage_exact':True,
        'record_id_unique':True,'record_type_counts_exact':True,'fact_base_identity_exact':True,
        'canonical_record_binding_exact':True,
        'user_understandability_status':payload['meta']['user_understandability_status'],
        'user_understandability_cannot_be_self_passed':True,
    }

USER_VISUAL_TEMPLATE='''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>客观交易链｜用户可视化核对测试版</title>
<style>
:root{color-scheme:light dark;--bg:#f4f6f3;--panel:#fff;--ink:#18231d;--muted:#68736c;--line:#d9e0da;--accent:#126b4f;--on-accent:#fff;--accent2:#dcefe7;--warn:#9b4b15;--warnbg:#fff1e4;--shadow:0 14px 36px rgba(23,43,32,.08)}
@media(prefers-color-scheme:dark){:root{--bg:#111713;--panel:#18201b;--ink:#eef6f0;--muted:#a9b7ae;--line:#344139;--accent:#77d1ad;--on-accent:#0b241a;--accent2:#203e32;--warn:#ffb77e;--warnbg:#3b281c;--shadow:0 14px 36px rgba(0,0,0,.28)}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}.shell{max-width:1180px;margin:auto;padding:28px 20px 70px}.hero,.panel{background:var(--panel);border:1px solid var(--line);border-radius:22px;box-shadow:var(--shadow)}.hero{padding:28px;background:linear-gradient(135deg,var(--panel),var(--accent2))}.eyebrow{font-size:13px;font-weight:750;letter-spacing:.08em;color:var(--accent)}h1{font-size:clamp(28px,5vw,48px);line-height:1.15;margin:8px 0 14px;max-width:780px}.lead{font-size:18px;max-width:860px;margin:0}.guide{margin-top:18px;padding:14px 16px;border:1px solid var(--line);border-radius:14px;background:var(--panel)}.guide ol{margin:6px 0 0;padding-left:22px}.boundary{margin-top:12px;border-left:5px solid var(--warn);background:var(--warnbg);padding:12px 15px;border-radius:10px;color:var(--ink)}.control{margin:20px 0;padding:18px 20px;display:grid;grid-template-columns:minmax(240px,1fr) auto;gap:16px;align-items:end}.control label{display:block;font-weight:750;margin-bottom:7px}select{width:100%;padding:12px 14px;border:1px solid var(--line);border-radius:12px;background:var(--panel);color:var(--ink);font:inherit}.scope{font-size:14px;color:var(--muted);text-align:right}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:0 0 20px}.metric{padding:15px 17px;background:var(--panel);border:1px solid var(--line);border-radius:16px}.metric strong{display:block;font-size:24px}.metric span{color:var(--muted);font-size:13px}.tabs{display:flex;gap:8px;overflow:auto;padding:7px;background:var(--panel);border:1px solid var(--line);border-radius:15px;position:sticky;top:8px;z-index:3}.tab{border:0;background:transparent;color:var(--muted);padding:10px 15px;border-radius:10px;font:inherit;font-weight:750;white-space:nowrap;cursor:pointer}.tab[aria-selected="true"]{background:var(--accent);color:var(--on-accent)}.section-head{display:flex;justify-content:space-between;gap:16px;align-items:flex-end;margin:25px 2px 14px}.section-head h2{margin:0;font-size:25px}.section-head p{margin:0;color:var(--muted)}.cards{display:grid;gap:13px}.card{background:var(--panel);border:1px solid var(--line);border-radius:17px;padding:17px 18px;box-shadow:0 6px 20px rgba(23,43,32,.045)}.card.attention{border-left:5px solid var(--warn)}.card-top{display:flex;gap:10px;justify-content:space-between;align-items:flex-start}.badge{display:inline-flex;align-items:center;border-radius:999px;padding:3px 9px;background:var(--accent2);color:var(--accent);font-size:12px;font-weight:800}.time{color:var(--muted);font-size:13px;text-align:right}.card h3{font-size:18px;line-height:1.45;margin:11px 0}.proof{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:13px}.proof div{padding:10px 12px;border-radius:11px;background:var(--bg);font-size:14px}.proof strong{display:block;margin-bottom:3px}.warn{margin-top:11px;padding:9px 11px;background:var(--warnbg);color:var(--ink);border-radius:10px;font-size:14px}.relation{margin-top:10px;padding:10px 12px;border:1px dashed var(--accent);border-radius:11px;color:var(--accent);font-weight:700}.details{display:flex;flex-wrap:wrap;gap:7px;margin-top:12px}.detail{font-size:13px;border:1px solid var(--line);padding:5px 8px;border-radius:8px}.source{margin-top:12px}details summary{cursor:pointer;color:var(--accent);font-weight:700}details p{white-space:pre-wrap;overflow-wrap:anywhere;color:var(--muted);font-size:13px}.pager{display:flex;justify-content:center;align-items:center;gap:12px;margin:20px}.pager button{border:1px solid var(--line);background:var(--panel);color:var(--ink);padding:9px 13px;border-radius:10px;font:inherit;cursor:pointer}.pager button:disabled{opacity:.35;cursor:not-allowed}.empty{padding:35px;text-align:center;color:var(--muted);background:var(--panel);border:1px dashed var(--line);border-radius:17px}.integrity{margin-top:30px;padding:18px 20px;color:var(--muted);font-size:14px}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
@media(max-width:760px){.shell{padding:14px 12px 50px}.hero{padding:21px}.control{grid-template-columns:1fr}.scope{text-align:left}.metrics{grid-template-columns:1fr 1fr}.proof{grid-template-columns:1fr}.card-top{display:block}.time{text-align:left;margin-top:5px}.section-head{display:block}.section-head p{margin-top:4px}}
@media(max-width:380px){.metrics{grid-template-columns:1fr}.tab{padding:9px 11px}.card{padding:15px}.lead{font-size:16px}}
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;transition:none!important}}
</style>
</head>
<body>
<main class="shell">
<section class="hero"><div class="eyebrow">第一工作包 · 可视化核对页</div><h1>不看表格，按一笔交易的过程来看</h1><p class="lead" id="identity"></p><div class="guide"><strong>怎么核对</strong><ol><li>先选择一笔交易或一个对象。</li><li>先看“交易过程”，再看“未知与冲突”。</li><li>发现不对时，记下卡片底部的事实编号告诉我们。</li></ol></div><div class="boundary" id="boundary"></div></section>
<section class="panel control"><div><label for="objectSelect">选择要查看的交易或对象</label><select id="objectSelect"></select></div><div class="scope" id="scope"></div></section>
<section class="metrics" id="metrics" aria-label="当前对象概况"></section>
<nav class="tabs" aria-label="查看方式" role="tablist">
<button class="tab" id="tab-events" role="tab" aria-controls="reviewPanel" aria-selected="true" data-tab="events">交易过程</button><button class="tab" id="tab-relations" role="tab" aria-controls="reviewPanel" aria-selected="false" data-tab="relations">关系连接</button><button class="tab" id="tab-attention" role="tab" aria-controls="reviewPanel" aria-selected="false" data-tab="attention">未知与冲突</button><button class="tab" id="tab-sources" role="tab" aria-controls="reviewPanel" aria-selected="false" data-tab="sources">来源依据</button>
</nav>
<section id="reviewPanel" role="tabpanel" aria-labelledby="tab-events"><div class="section-head"><div><h2 id="sectionTitle"></h2><p id="sectionHint"></p></div><p id="resultCount" aria-live="polite"></p></div><div id="cards" class="cards"></div><div id="pager" class="pager"></div></section>
<section class="panel integrity" id="integrity"></section>
</main>
<script id="visual-data" type="application/json">__VISUAL_DATA__</script>
<script>
(()=>{'use strict';
const data=JSON.parse(document.getElementById('visual-data').textContent);const byId=new Map(data.objects.map(o=>[o.id,o]));const reduceMotion=Boolean(window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches);
const select=document.getElementById('objectSelect'),cards=document.getElementById('cards'),pager=document.getElementById('pager');let current=data.meta.default_object_id,tab='events',page=1;
const labels={events:['交易过程','按时间和固定展示顺序查看事实事件。'],relations:['关系连接','查看委托、成交、仓位或资金之间怎样相连。'],attention:['未知、候选与冲突','这些内容必须保留不确定性，不能被写成已确定事实。'],sources:['来源依据','查看每条记录来自哪个文件、哪张表或哪一行。']};
function el(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n}
function filtered(obj){if(tab==='events')return obj.records.filter(r=>r.type==='FACT_STATEMENT');if(tab==='relations')return obj.records.filter(r=>r.type==='RELATION_STATEMENT');if(tab==='sources')return obj.records.filter(r=>r.type==='LINEAGE_STATEMENT');return obj.records.filter(r=>r.attention)}
function metric(value,label){const n=el('div','metric');n.append(el('strong','',String(value)),el('span','',label));return n}
function renderMetrics(obj){const n=document.getElementById('metrics');n.replaceChildren(metric(obj.record_count,'全部记录'),metric(obj.counts.FACT_STATEMENT,'事实事件'),metric(obj.counts.RELATION_STATEMENT,'关系连接'),metric(obj.attention_count,'需要特别留意'))}
function selectTab(next){tab=next;page=1;document.querySelectorAll('.tab').forEach(x=>x.setAttribute('aria-selected',String(x.dataset.tab===tab)));document.getElementById('reviewPanel').setAttribute('aria-labelledby','tab-'+tab);render()}
function card(record){const n=el('article','card'+(record.attention?' attention':''));const top=el('div','card-top');top.append(el('span','badge',record.type_label+' · '+record.evidence),el('span','time',record.time));n.append(top,el('h3','',record.summary));const proof=el('div','proof'),yes=el('div'),no=el('div');yes.append(el('strong','', '现在能证明'),document.createTextNode(record.can_prove||'尚无额外说明'));no.append(el('strong','', '不能当成什么'),document.createTextNode(record.cannot_prove||'不得超出当前证据范围'));proof.append(yes,no);n.append(proof);
if(record.relation){const r=el('div','relation',(record.relation.source||'来源对象不明')+'  →  '+(record.relation.target||'目标对象不明'));n.append(r)}
if(record.attention_text)n.append(el('div','warn','需要保留：'+record.attention_text));if(record.details.length){const d=el('div','details');record.details.forEach(x=>d.append(el('span','detail',x.label+'：'+x.value)));n.append(d)}
const source=el('details','source'),summary=el('summary','', '展开看来源和技术编号'),p=el('p','');p.textContent='\u4e8b\u5b9e\u7f16\u53f7\uff1a'+record.id+'\\n\u6765\u6e90\uff1a'+record.source.file+'\uff5c'+(record.source.table||'\u8868\u540d\u672a\u8bb0\u5f55')+'\uff5c\u884c '+(record.source.row??record.source.locator??'\u672a\u8bb0\u5f55')+'\\n\u8def\u5f84\uff1a'+record.source.path;source.append(summary,p);n.append(source);return n}
function movePage(delta){page+=delta;render();window.scrollTo({top:document.querySelector('.tabs').offsetTop,behavior:reduceMotion?'auto':'smooth'})}
function render(){const obj=byId.get(current),items=filtered(obj),size=data.meta.page_size,pages=Math.max(1,Math.ceil(items.length/size));if(page>pages)page=pages;document.getElementById('sectionTitle').textContent=labels[tab][0];document.getElementById('sectionHint').textContent=labels[tab][1];document.getElementById('resultCount').textContent='共 '+items.length+' 条';cards.replaceChildren();const slice=items.slice((page-1)*size,page*size);if(!slice.length)cards.append(el('div','empty','这个对象在当前分类中没有记录。'));else slice.forEach(r=>cards.append(card(r)));pager.replaceChildren();const prev=el('button','', '上一页'),next=el('button','', '下一页');prev.disabled=page===1;next.disabled=page===pages;prev.onclick=()=>movePage(-1);next.onclick=()=>movePage(1);pager.append(prev,el('span','',page+' / '+pages),next);renderMetrics(obj);document.getElementById('scope').textContent=obj.time_start+' → '+obj.time_end}
data.objects.forEach(o=>{const option=el('option','',o.label+' · '+o.record_count+'条');option.value=o.id;select.append(option)});select.value=current;select.onchange=()=>{current=select.value;if(current==='T087_METHOD'&&tab==='events')selectTab('attention');else{page=1;render()}};document.querySelectorAll('.tab').forEach(button=>button.addEventListener('click',()=>selectTab(button.dataset.tab)));
document.getElementById('identity').textContent=data.meta.identity;document.getElementById('boundary').textContent=data.meta.boundary;document.getElementById('integrity').textContent='完整性核对：本页包含 '+data.meta.record_count+' 条记录、'+data.meta.object_count+' 个导航对象；每条都保留事实编号，可回到 '+data.meta.fact_base_file+'。用户是否真正看懂，仍必须由用户本人实际查看后确认，程序不能自己宣布通过。';render();
})();
</script>
</body></html>
'''

def build_user_visual_html(payload):
    embedded=canonical(payload).replace('<','\\u003c')
    return USER_VISUAL_TEMPLATE.replace('__VISUAL_DATA__',embedded)

def user_visual_embedded_payload(html):
    match=re.search(r'<script id="visual-data" type="application/json">(.*?)</script>',html,re.S)
    if not match: raise RuntimeError('USER_VISUAL_EMBEDDED_PAYLOAD_MISSING')
    return json.loads(match.group(1))

def validate_user_visual_inline_javascript(html):
    matches=re.findall(r'<script(?: [^>]*)?>(.*?)</script>',html,re.S)
    if len(matches)!=2: raise RuntimeError('USER_VISUAL_SCRIPT_COUNT_INVALID')
    script=matches[1]; stack=[]; quote=None; escaped=False; line_comment=False; block_comment=False; index=0
    pairs={')':'(',']':'[','}':'{'}
    while index<len(script):
        char=script[index]; following=script[index+1] if index+1<len(script) else ''
        if quote:
            if escaped: escaped=False
            elif char=='\\': escaped=True
            elif char==quote: quote=None
            elif char in '\r\n': raise RuntimeError('USER_VISUAL_JAVASCRIPT_RAW_NEWLINE_IN_STRING')
        elif line_comment:
            if char in '\r\n': line_comment=False
        elif block_comment:
            if char=='*' and following=='/': block_comment=False; index+=1
        elif char=='/' and following=='/': line_comment=True; index+=1
        elif char=='/' and following=='*': block_comment=True; index+=1
        elif char in "'\"": quote=char
        elif char in '([{': stack.append(char)
        elif char in ')]}':
            if not stack or stack.pop()!=pairs[char]: raise RuntimeError('USER_VISUAL_JAVASCRIPT_BRACKET_MISMATCH')
        index+=1
    if quote or escaped or block_comment or stack: raise RuntimeError('USER_VISUAL_JAVASCRIPT_UNTERMINATED_STRUCTURE')
    return True

def validate_user_visual_html(html,payload,records,fact_path,maximum_bytes=12*1024*1024):
    if len(html.encode('utf-8'))>maximum_bytes: raise RuntimeError('USER_VISUAL_HTML_TOO_LARGE')
    embedded=user_visual_embedded_payload(html)
    if canonical(embedded)!=canonical(payload): raise RuntimeError('USER_VISUAL_EMBEDDED_PAYLOAD_MISMATCH')
    checked=validate_user_visual_payload(embedded,records,fact_path)
    forbidden=(
        r'<script[^>]+src=',r'<link[^>]+href=',r'<img[^>]+src=["\']https?://',r'<(?:iframe|object|embed)\b',
        r'@import\b',r'url\(\s*["\']?https?://',r'\bfetch\s*\(',r'XMLHttpRequest',r'WebSocket\s*\(',
        r'EventSource\s*\(',r'sendBeacon\s*\(',r'\bimport\s*\(',
    )
    if any(re.search(pattern,html,re.I) for pattern in forbidden): raise RuntimeError('USER_VISUAL_EXTERNAL_RESOURCE_OR_NETWORK_CALL_FOUND')
    required=('objectSelect','metrics','cards','pager','visual-data','交易过程','关系连接','未知与冲突','来源依据')
    if any(value not in html for value in required): raise RuntimeError('USER_VISUAL_REQUIRED_CONTROL_OR_SECTION_MISSING')
    if "record.id+'\n" in html or "record.id+'\\n" not in html: raise RuntimeError('USER_VISUAL_JAVASCRIPT_NEWLINE_ESCAPE_INVALID')
    validate_user_visual_inline_javascript(html)
    if '用户核对表格' in html: raise RuntimeError('USER_VISUAL_ACTIVE_EXCEL_LANGUAGE_FOUND')
    return {**checked,'bytes':len(html.encode('utf-8')),'self_contained_no_external_resources':True,'plain_chinese_visual_sections_present':True,'responsive_rules_present':'@media(max-width:380px)' in html,'reduced_motion_rule_present':'prefers-reduced-motion' in html and "reduceMotion?'auto':'smooth'" in html,'inline_javascript_static_structure_valid':True}

def build_views(config_path, output_dir=None, preview_dir=None, verification_output=None, fact_base_override=None):
    config_path=Path(config_path).resolve()
    config=json.load(open(config_path,encoding='utf-8'))
    view=config['view_generation']
    base_dir=config_path.parent
    inputs=view['inputs']
    fact_path=Path(fact_base_override).resolve() if fact_base_override else base_dir/inputs['fact_base']['file']
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
    visual_output=target_dir/view['outputs']['user_visual']
    if ai_output==visual_output: raise RuntimeError('VIEW_OUTPUT_PATH_COLLISION')
    compact_mode=view['ai_view'].get('representation')=='COMPACT_COMPLETE_NORMALIZED_SEMANTICS_BY_OBJECT_V2'
    ai_text=(build_compact_ai_view_text(records,fact_path,sample_manifest,view) if compact_mode else build_ai_view_text(records,fact_path,sample_manifest,view))
    compact_check=(validate_compact_ai_view(ai_text,records,fact_path,int(view['ai_view']['maximum_bytes'])) if compact_mode else None)
    if not compact_mode and ai_view_records(ai_text)!=records: raise RuntimeError('AI_VIEW_FACT_RECONCILIATION_FAILED')
    visual_payload=build_user_visual_payload(records,fact_path,config['contract_id'])
    visual_payload_check=validate_user_visual_payload(visual_payload,records,fact_path)
    visual_html=build_user_visual_html(visual_payload)
    visual_check=validate_user_visual_html(visual_html,visual_payload,records,fact_path,int(view['user_visual']['maximum_bytes']))
    with tempfile.TemporaryDirectory(prefix='.view-build-',dir=target_dir) as temp_name:
        temp=Path(temp_name)
        ai_temp=temp/'ai.md'
        visual_temp=temp/'user.html'
        ai_temp.write_text(ai_text,encoding='utf-8',newline='\n')
        visual_temp.write_text(visual_html,encoding='utf-8',newline='\n')
        os.replace(ai_temp,ai_output)
        os.replace(visual_temp,visual_output)
    result={
        'all_pass':True,
        'source_fact_base':str(fact_path),
        'fact_base_record_count':len(records),
        'fact_base_sha256':sha_file(fact_path),
        'view_content_sha256':hashlib.sha256(canonical(visual_payload).encode('utf-8')).hexdigest(),
        'ai_view':{'path':str(ai_output),'bytes':ai_output.stat().st_size,'sha256':sha_file(ai_output),'record_order_exact':True,'compact_complete_index':compact_check},
        'user_visual':{'path':str(visual_output),'bytes':visual_output.stat().st_size,'sha256':sha_file(visual_output),**visual_payload_check,**visual_check},
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

def verify_capabilities(mapping_path,adoption_path,schema_path,receipts_path,output_path=None,business_output_path=None):
    mapping=read_jsonl(mapping_path); capabilities=[item for item in mapping if item.get('record_type')=='CAPABILITY_CLOSURE_CANDIDATE']
    adoption=read_jsonl(adoption_path); schema=json.load(open(schema_path,encoding='utf-8')); receipts=read_jsonl(receipts_path)
    specification=validate_capability_specs(capabilities,adoption,schema,receipts)
    implementation=validate_business_operator_registry_records(mapping,capabilities)
    execution_receipts,execution=execute_capability_bounded_witnesses(capabilities,receipts)
    business_results,business_execution=execute_authoritative_business_operators(capabilities,execution_receipts)
    if output_path:
        output=Path(output_path)
        if output.exists(): raise RuntimeError('CAPABILITY_RECEIPT_OUTPUT_ALREADY_EXISTS:'+str(output))
        jsonl_write(output,execution_receipts)
        execution['written_receipt_file']={'path':str(output),'bytes':output.stat().st_size,'sha256':sha_file(output)}
    if business_output_path:
        business_output=Path(business_output_path)
        if business_output.exists(): raise RuntimeError('BUSINESS_RESULT_OUTPUT_ALREADY_EXISTS:'+str(business_output))
        jsonl_write(business_output,business_results)
        business_execution['written_business_result_file']={'path':str(business_output),'bytes':business_output.stat().st_size,'sha256':sha_file(business_output)}
    result={'all_pass':True,'specification':specification,'business_operator_implementation':implementation,'bounded_execution':execution,'bounded_business_execution':business_execution}
    print(canonical(result)); return result

CLEAN_ZONE_KEYS=('read_only_inputs','rules_program_config','temporary_run','candidate_outputs')

def clean_environment_policy(config):
    policy=config.get('clean_production_environment') or {}
    zones=policy.get('zones') or {}
    if set(zones)!=set(CLEAN_ZONE_KEYS) or len(set(zones.values()))!=4:
        raise RuntimeError('CLEAN_ENVIRONMENT_ZONE_CONFIGURATION_INVALID')
    if policy.get('input_source_policy')!='COPY_VERIFIED_LOCKED_MIRRORS_ONLY' or policy.get('real_recomputation_allowed') is not False:
        raise RuntimeError('CLEAN_ENVIRONMENT_INPUT_OR_RECOMPUTATION_POLICY_INVALID')
    if policy.get('overwrite_or_delete_existing_root_allowed') is not False or policy.get('unexpected_file_action')!='STOP':
        raise RuntimeError('CLEAN_ENVIRONMENT_DESTRUCTIVE_OR_POLLUTION_POLICY_INVALID')
    if policy.get('expected_input_file_count')!=74:
        raise RuntimeError('CLEAN_ENVIRONMENT_INPUT_COUNT_POLICY_INVALID')
    return policy

def ensure_within(parent,child):
    parent=Path(parent).resolve(); child=Path(child).resolve()
    if child!=parent and parent not in child.parents:
        raise RuntimeError('PATH_OUTSIDE_CLEAN_ROOT:'+str(child))
    return child

def clean_root_paths(config,root):
    policy=clean_environment_policy(config); root=Path(root).resolve()
    return root,{key:ensure_within(root,root/name) for key,name in policy['zones'].items()}

def clean_rule_destination(identity):
    return identity.get('destination_name') or Path(identity['path']).name

def clean_runtime_config(config):
    runtime=json.loads(canonical(config)); policy=clean_environment_policy(config)
    destination_by_source={item['path']:clean_rule_destination(item) for item in policy['rule_package_fixed_files']}
    for identity in runtime['specification_inputs'].values():
        if identity['path'] not in destination_by_source:
            raise RuntimeError('CLEAN_RUNTIME_SPECIFICATION_NOT_IN_RULE_PACKAGE:'+identity['path'])
        identity['path']=destination_by_source[identity['path']]
    runtime['view_generation']['inputs']['sample_manifest']['file']=policy['sample_manifest_file']
    runtime['view_generation']['inputs']['input_receipts']['file']=policy['input_receipts_file']
    runtime['view_generation']['inputs']['fact_base']['file']=policy['fact_base_file']
    runtime['worktree']='.'
    runtime['clean_runtime_identity']={
        'derived_from_original_config_sha256':hashlib.sha256(canonical(config).encode('utf-8')).hexdigest(),
        'all_specification_paths_rebound_to_rules_zone':True,
        'all_selected_object_reads_rebound_to_read_only_input_zone':True,
        'post_initialization_config_must_be_rules_zone_runtime_copy':True,
        'post_initialization_program_must_be_rules_zone_copy':True,
        'real_recomputation_allowed':False,'full_136_chain_build_allowed':False,
    }
    return runtime

def clean_active_program_name(policy):
    explicit=policy.get('active_program_file')
    if explicit: return explicit
    candidates=[clean_rule_destination(item) for item in policy['rule_package_fixed_files'] if clean_rule_destination(item).startswith('06_')]
    if len(candidates)!=1: raise RuntimeError('CLEAN_ENVIRONMENT_ACTIVE_PROGRAM_NOT_UNIQUE')
    return candidates[0]

def clean_expected_initialization_manifest(source_config,config_destination,runtime_config_path,zones,input_manifest,rule_manifest):
    policy=clean_environment_policy(source_config); active_program=zones['rules_program_config']/clean_active_program_name(policy)
    return {
        'record_type':'CLEAN_ENVIRONMENT_INITIALIZATION_MANIFEST','manifest_version':'2.0',
        'source_config_file':config_destination.name,'source_config_bytes':config_destination.stat().st_size,
        'source_config_sha256':sha_file(config_destination),
        'runtime_config_file':runtime_config_path.name,'runtime_config_bytes':runtime_config_path.stat().st_size,
        'runtime_config_sha256':sha_file(runtime_config_path),
        'active_program_file':active_program.name,'active_program_bytes':active_program.stat().st_size,
        'active_program_sha256':sha_file(active_program),
        'input_files':sorted(input_manifest,key=lambda item:(item['input_id'],item['selected_object_index'])),
        'rule_files':sorted(rule_manifest,key=lambda item:item['file']),
        'zone_names':policy['zones'],
        'initial_state':{'temporary_run_files':[],'candidate_output_files':[]},
        'no_source_parent_read_required_after_initialization':True,
        'post_initialization_execution_entry':'RULES_ZONE_PROGRAM_AND_RUNTIME_CONFIG_ONLY',
    }

def init_clean_root(config_path,root):
    config_path=Path(config_path).resolve(); config=json.load(open(config_path,encoding='utf-8'))
    root,zones=clean_root_paths(config,root)
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise RuntimeError('CLEAN_ROOT_MUST_BE_MISSING_OR_EMPTY:'+str(root))
    root.mkdir(parents=True,exist_ok=True)
    for zone in zones.values(): zone.mkdir()
    receipts_path=verify_config_file(config_path,config['specification_inputs']['input_receipts'],'input_receipts')
    receipts=read_jsonl(receipts_path)
    if len(receipts)!=74 or len({Path(item['mirror_path']).name for item in receipts})!=74:
        raise RuntimeError('CLEAN_ROOT_INPUT_MIRROR_NAME_OR_COUNT_INVALID')
    input_manifest=[]
    for receipt in sorted(receipts,key=lambda item:(item['input_id'],int(item['selected_object_index']))):
        source=Path(receipt['mirror_path'])
        if not source.is_file() or source.is_symlink() or sha_file(source)!=receipt['extracted_content_sha256']:
            raise RuntimeError('CLEAN_ROOT_LOCKED_MIRROR_SOURCE_INVALID:'+receipt['input_id'])
        destination=zones['read_only_inputs']/source.name
        shutil.copyfile(source,destination)
        os.chmod(destination,stat.S_IRUSR|stat.S_IRGRP|stat.S_IROTH)
        input_manifest.append({
            'file':source.name,'input_id':receipt['input_id'],'selected_object_index':int(receipt['selected_object_index']),
            'bytes':destination.stat().st_size,'sha256':sha_file(destination),'actual_count':int(receipt['actual_count']),
        })
    rule_manifest=[]; used_names=set()
    for identity in config['clean_production_environment']['rule_package_fixed_files']:
        source=verify_config_file(config_path,identity,'clean_rule:'+identity['path'])
        destination=zones['rules_program_config']/clean_rule_destination(identity)
        if destination.name in used_names or destination.exists(): raise RuntimeError('CLEAN_RULE_FILE_NAME_COLLISION:'+destination.name)
        used_names.add(destination.name)
        shutil.copyfile(source,destination); os.chmod(destination,stat.S_IRUSR|stat.S_IRGRP|stat.S_IROTH)
        rule_manifest.append({'file':destination.name,'source_path':identity['path'],'bytes':destination.stat().st_size,'sha256':sha_file(destination)})
    config_destination=zones['rules_program_config']/config['clean_production_environment']['source_config_file']
    if config_destination.name in used_names or config_destination.exists(): raise RuntimeError('CLEAN_CONFIG_FILE_NAME_COLLISION')
    shutil.copyfile(config_path,config_destination); os.chmod(config_destination,stat.S_IRUSR|stat.S_IRGRP|stat.S_IROTH)
    rule_manifest.append({'file':config_destination.name,'bytes':config_destination.stat().st_size,'sha256':sha_file(config_destination),'self_identity_policy':'CAPTURE_EXACT_CANDIDATE_CONFIG_AT_INITIALIZATION'})
    runtime_config_path=zones['rules_program_config']/config['clean_production_environment']['runtime_config_file']
    if runtime_config_path.name in used_names or runtime_config_path.exists(): raise RuntimeError('CLEAN_RUNTIME_CONFIG_FILE_NAME_COLLISION')
    json_write(runtime_config_path,clean_runtime_config(config)); os.chmod(runtime_config_path,stat.S_IRUSR|stat.S_IRGRP|stat.S_IROTH)
    rule_manifest.append({'file':runtime_config_path.name,'bytes':runtime_config_path.stat().st_size,'sha256':sha_file(runtime_config_path),'identity':'DETERMINISTIC_PATH_REBOUND_RUNTIME_CONFIG'})
    manifest=clean_expected_initialization_manifest(config,config_destination,runtime_config_path,zones,input_manifest,rule_manifest)
    manifest_path=zones['rules_program_config']/config['clean_production_environment']['initialization_manifest_file']
    json_write(manifest_path,manifest); os.chmod(manifest_path,stat.S_IRUSR|stat.S_IRGRP|stat.S_IROTH)
    result=_verify_clean_root_state(runtime_config_path,root,'INITIALIZED',require_internal_program=False)
    print(canonical(result)); return result

def directory_regular_files(path):
    files=[]
    for item in path.iterdir():
        if item.is_symlink() or not item.is_file():
            raise RuntimeError('CLEAN_ENVIRONMENT_NON_REGULAR_OBJECT:'+str(item))
        files.append(item)
    return sorted(files,key=lambda value:value.name)

def clean_internal_execution_context(config_path,root,require_internal_program=True):
    config_path=Path(config_path).resolve(); config=json.load(open(config_path,encoding='utf-8'))
    root,zones=clean_root_paths(config,root); policy=clean_environment_policy(config)
    expected_config=zones['rules_program_config']/policy['runtime_config_file']
    if config_path!=expected_config:
        raise RuntimeError('CLEAN_ENVIRONMENT_EXTERNAL_CONFIG_FORBIDDEN_AFTER_INITIALIZATION:'+str(config_path))
    expected_program=zones['rules_program_config']/clean_active_program_name(policy)
    if require_internal_program and Path(__file__).resolve()!=expected_program:
        raise RuntimeError('CLEAN_ENVIRONMENT_EXTERNAL_PROGRAM_FORBIDDEN_AFTER_INITIALIZATION:'+str(Path(__file__).resolve()))
    return config_path,config,root,zones,policy,expected_program

def clean_normalized_quality_receipt(receipt):
    value=json.loads(canonical(receipt))
    if isinstance(value.get('source_fact_base'),str): value['source_fact_base']=Path(value['source_fact_base']).name
    for key in ('ai_view','user_visual'):
        if isinstance(value.get(key),dict) and isinstance(value[key].get('path'),str):
            value[key]['path']=Path(value[key]['path']).name
    return value

def clean_expected_build_receipt(config_path,manifest_path,sample_path,active_program,declarative_summary,business_summary,temporary,outputs,policy):
    file_identities={
        'temporary_run':{name:{'bytes':path.stat().st_size,'sha256':sha_file(path)} for name,path in sorted(temporary.items()) if name!=policy['build_receipt_file']},
        'candidate_outputs':{name:{'bytes':path.stat().st_size,'sha256':sha_file(path)} for name,path in sorted(outputs.items())},
    }
    return {
        'record_type':'CLEAN_ENVIRONMENT_BOUNDED_BUILD_RECEIPT','build_version':'2.0',
        'runtime_config_sha256':sha_file(config_path),'initialization_manifest_sha256':sha_file(manifest_path),
        'active_program_sha256':sha_file(active_program),'sample_manifest_sha256':sha_file(sample_path),
        'declarative_summary':declarative_summary,'bounded_business_summary':business_summary,
        'file_identities':file_identities,'real_recomputation_run':False,'full_136_chain_built':False,
        'receipt_is_not_sole_authority':True,'independent_deterministic_rebuild_required_for_verification':True,
    }

def _verify_clean_root_state(config_path,root,phase,require_internal_program=True):
    config_path,config,root,zones,policy,active_program=clean_internal_execution_context(config_path,root,require_internal_program)
    if not root.is_dir() or {item.name for item in root.iterdir()}!=set(policy['zones'].values()):
        raise RuntimeError('CLEAN_ENVIRONMENT_ZONE_SET_MISMATCH')
    if any(not zone.is_dir() or zone.is_symlink() for zone in zones.values()):
        raise RuntimeError('CLEAN_ENVIRONMENT_ZONE_TYPE_INVALID')
    manifest_path=zones['rules_program_config']/policy['initialization_manifest_file']
    if not manifest_path.is_file(): raise RuntimeError('CLEAN_ENVIRONMENT_INITIALIZATION_MANIFEST_MISSING')
    manifest=json.load(open(manifest_path,encoding='utf-8'))
    if manifest_path.stat().st_mode & (stat.S_IWUSR|stat.S_IWGRP|stat.S_IWOTH):
        raise RuntimeError('CLEAN_ENVIRONMENT_INITIALIZATION_MANIFEST_NOT_READ_ONLY')
    actual_inputs={item.name:item for item in directory_regular_files(zones['read_only_inputs'])}
    if len(actual_inputs)!=policy['expected_input_file_count']:
        raise RuntimeError('CLEAN_ENVIRONMENT_INPUT_FILE_SET_MISMATCH')
    expected_rules={clean_rule_destination(item):item for item in policy['rule_package_fixed_files']}
    expected_rule_names=set(expected_rules)|{
        policy['source_config_file'],policy['runtime_config_file'],policy['initialization_manifest_file'],
    }
    actual_rules={item.name:item for item in directory_regular_files(zones['rules_program_config'])}
    if set(actual_rules)!=expected_rule_names:
        raise RuntimeError('CLEAN_ENVIRONMENT_RULE_FILE_SET_MISMATCH')
    for name,identity in expected_rules.items():
        path=actual_rules[name]
        if path.stat().st_size!=identity['bytes'] or sha_file(path)!=identity['sha256'] or path.stat().st_mode & (stat.S_IWUSR|stat.S_IWGRP|stat.S_IWOTH):
            raise RuntimeError('CLEAN_ENVIRONMENT_RULE_IDENTITY_MISMATCH:'+name)
    config_copy=actual_rules[policy['source_config_file']]
    source_config=json.load(open(config_copy,encoding='utf-8'))
    runtime_config=actual_rules[policy['runtime_config_file']]
    expected_runtime=clean_runtime_config(source_config)
    if json.load(open(runtime_config,encoding='utf-8'))!=expected_runtime:
        raise RuntimeError('CLEAN_ENVIRONMENT_RUNTIME_CONFIG_CONTENT_MISMATCH')
    if config_copy.stat().st_mode & (stat.S_IWUSR|stat.S_IWGRP|stat.S_IWOTH) or runtime_config.stat().st_mode & (stat.S_IWUSR|stat.S_IWGRP|stat.S_IWOTH):
        raise RuntimeError('CLEAN_ENVIRONMENT_CONFIG_NOT_READ_ONLY')
    receipt_file=actual_rules[policy['input_receipts_file']]
    receipts=read_jsonl(receipt_file)
    if len(receipts)!=policy['expected_input_file_count']:
        raise RuntimeError('CLEAN_ENVIRONMENT_INTERNAL_RECEIPT_COUNT_MISMATCH')
    expected_input_manifest=[]
    seen_input_keys=set()
    for receipt in sorted(receipts,key=lambda item:(item['input_id'],int(item['selected_object_index']))):
        key=(receipt['input_id'],int(receipt['selected_object_index']))
        if key in seen_input_keys: raise RuntimeError('CLEAN_ENVIRONMENT_INTERNAL_RECEIPT_KEY_DUPLICATE:'+str(key))
        seen_input_keys.add(key); name=Path(receipt['mirror_path']).name
        if name not in actual_inputs: raise RuntimeError('CLEAN_ENVIRONMENT_INPUT_NOT_BOUND_BY_INTERNAL_RECEIPT:'+name)
        path=actual_inputs[name]
        if sha_file(path)!=receipt['extracted_content_sha256'] or path.stat().st_mode & (stat.S_IWUSR|stat.S_IWGRP|stat.S_IWOTH):
            raise RuntimeError('CLEAN_ENVIRONMENT_INPUT_IDENTITY_OR_READ_ONLY_MISMATCH:'+name)
        expected_input_manifest.append({'file':name,'input_id':receipt['input_id'],'selected_object_index':int(receipt['selected_object_index']),'bytes':path.stat().st_size,'sha256':sha_file(path),'actual_count':int(receipt['actual_count'])})
    if set(actual_inputs)!={item['file'] for item in expected_input_manifest}:
        raise RuntimeError('CLEAN_ENVIRONMENT_INPUT_FILE_SET_NOT_EXACTLY_RECEIPT_BOUND')
    expected_rule_manifest=[]
    for identity in source_config['clean_production_environment']['rule_package_fixed_files']:
        name=clean_rule_destination(identity); path=actual_rules[name]
        expected_rule_manifest.append({'file':name,'source_path':identity['path'],'bytes':path.stat().st_size,'sha256':sha_file(path)})
    expected_rule_manifest.append({'file':config_copy.name,'bytes':config_copy.stat().st_size,'sha256':sha_file(config_copy),'self_identity_policy':'CAPTURE_EXACT_CANDIDATE_CONFIG_AT_INITIALIZATION'})
    expected_rule_manifest.append({'file':runtime_config.name,'bytes':runtime_config.stat().st_size,'sha256':sha_file(runtime_config),'identity':'DETERMINISTIC_PATH_REBOUND_RUNTIME_CONFIG'})
    expected_manifest=clean_expected_initialization_manifest(source_config,config_copy,runtime_config,zones,expected_input_manifest,expected_rule_manifest)
    if manifest!=expected_manifest:
        raise RuntimeError('CLEAN_ENVIRONMENT_INITIALIZATION_MANIFEST_NOT_DERIVABLE_FROM_INTERNAL_LOCKS')
    temporary={item.name:item for item in directory_regular_files(zones['temporary_run'])}
    outputs={item.name:item for item in directory_regular_files(zones['candidate_outputs'])}
    if phase=='INITIALIZED':
        if temporary or outputs: raise RuntimeError('CLEAN_ENVIRONMENT_INITIAL_STATE_POLLUTED')
    elif phase=='BUILT':
        if set(temporary)!=set(policy['built_temporary_files']) or set(outputs)!=set(policy['built_output_files']):
            raise RuntimeError('CLEAN_ENVIRONMENT_BUILT_FILE_SET_MISMATCH')
        if any(path.stat().st_mode & (stat.S_IWUSR|stat.S_IWGRP|stat.S_IWOTH) for path in [*temporary.values(),*outputs.values()]):
            raise RuntimeError('CLEAN_ENVIRONMENT_BUILT_FILE_NOT_READ_ONLY')
        zone_samples=zones['rules_program_config']/policy['sample_manifest_file']
        specs=load_and_validate_specifications(config_path,config,zones['read_only_inputs'])
        expected_declarative,declarative_summary=execute_capability_bounded_witnesses(specs['capabilities'],specs['receipts'])
        expected_business,business_summary=execute_authoritative_business_operators(specs['capabilities'],expected_declarative)
        actual_declarative=read_jsonl(temporary[policy['declarative_receipt_file']]); actual_business=read_jsonl(temporary[policy['business_result_file']])
        if canonical(actual_declarative)!=canonical(expected_declarative) or canonical(actual_business)!=canonical(expected_business):
            raise RuntimeError('CLEAN_ENVIRONMENT_BOUNDED_OPERATOR_OUTPUT_CONTENT_MISMATCH')
        with tempfile.TemporaryDirectory(prefix='.clean-root-independent-verify-') as temp_name:
            temp=Path(temp_name); expected_fact=temp/policy['fact_base_file']; expected_qa=temp/policy['quality_receipt_file']
            with contextlib.redirect_stdout(io.StringIO()):
                build(config_path,zone_samples,expected_fact,zones['read_only_inputs'])
                build_views(config_path,temp,None,expected_qa,expected_fact)
            for name,expected_path in (
                (policy['fact_base_file'],expected_fact),
                (config['view_generation']['outputs']['ai_view'],temp/config['view_generation']['outputs']['ai_view']),
                (config['view_generation']['outputs']['user_visual'],temp/config['view_generation']['outputs']['user_visual']),
            ):
                actual_path=outputs[name]
                if actual_path.stat().st_size!=expected_path.stat().st_size or sha_file(actual_path)!=sha_file(expected_path):
                    raise RuntimeError('CLEAN_ENVIRONMENT_INDEPENDENT_REBUILD_MISMATCH:'+name)
            actual_qa=json.load(open(outputs[policy['quality_receipt_file']],encoding='utf-8')); regenerated_qa=json.load(open(expected_qa,encoding='utf-8'))
            if clean_normalized_quality_receipt(actual_qa)!=clean_normalized_quality_receipt(regenerated_qa):
                raise RuntimeError('CLEAN_ENVIRONMENT_QUALITY_RECEIPT_CONTENT_MISMATCH')
        receipt_path=temporary[policy['build_receipt_file']]
        receipt=json.load(open(receipt_path,encoding='utf-8'))
        expected_receipt=clean_expected_build_receipt(config_path,manifest_path,zone_samples,active_program,declarative_summary,business_summary,temporary,outputs,policy)
        if receipt!=expected_receipt:
            raise RuntimeError('CLEAN_ENVIRONMENT_BUILD_RECEIPT_NOT_INDEPENDENTLY_DERIVABLE')
    else: raise RuntimeError('CLEAN_ENVIRONMENT_PHASE_INVALID:'+str(phase))
    return {
        'all_pass':True,'phase':phase,'root':str(root),'zone_names':policy['zones'],
        'input_file_count':len(actual_inputs),'rule_file_count':len(actual_rules),
        'temporary_file_count':len(temporary),'output_file_count':len(outputs),
        'unexpected_file_count':0,'real_recomputation_run':False,
        'config_inside_clean_root':config_path==zones['rules_program_config']/policy['runtime_config_file'],
        'active_program_inside_clean_root':Path(__file__).resolve()==active_program if require_internal_program else None,
        'input_manifest_cross_checked_with_internal_receipts':True,
        'built_outputs_independently_rebuilt_and_compared':phase=='BUILT',
    }

def verify_clean_root(config_path,root,phase):
    return _verify_clean_root_state(config_path,root,phase,require_internal_program=True)

def build_clean_root_bounded(config_path,sample_manifest_path,root):
    config_path,config,root,zones,policy,active_program=clean_internal_execution_context(config_path,root,require_internal_program=True)
    sample_manifest_path=Path(sample_manifest_path).resolve(); expected_samples=zones['rules_program_config']/policy['sample_manifest_file']
    if sample_manifest_path!=expected_samples:
        raise RuntimeError('CLEAN_ENVIRONMENT_EXTERNAL_SAMPLE_MANIFEST_FORBIDDEN_AFTER_INITIALIZATION:'+str(sample_manifest_path))
    verify_clean_root(config_path,root,'INITIALIZED')
    zone_config=config_path; zone_samples=sample_manifest_path
    if not zone_samples.is_file(): raise RuntimeError('CLEAN_ENVIRONMENT_SAMPLE_MANIFEST_MISSING')
    specs=load_and_validate_specifications(zone_config,json.load(open(zone_config,encoding='utf-8')),zones['read_only_inputs'])
    declarative,declarative_summary=execute_capability_bounded_witnesses(specs['capabilities'],specs['receipts'])
    business,business_summary=execute_authoritative_business_operators(specs['capabilities'],declarative)
    declarative_path=zones['temporary_run']/policy['declarative_receipt_file']
    business_path=zones['temporary_run']/policy['business_result_file']
    jsonl_write(declarative_path,declarative); jsonl_write(business_path,business)
    fact_path=zones['candidate_outputs']/policy['fact_base_file']
    build(zone_config,zone_samples,fact_path,zones['read_only_inputs'])
    qa_path=zones['candidate_outputs']/policy['quality_receipt_file']
    build_views(zone_config,zones['candidate_outputs'],None,qa_path,fact_path)
    temporary={path.name:path for path in (declarative_path,business_path)}
    outputs={path.name:path for path in directory_regular_files(zones['candidate_outputs'])}
    manifest_path=zones['rules_program_config']/policy['initialization_manifest_file']
    receipt=clean_expected_build_receipt(config_path,manifest_path,zone_samples,active_program,declarative_summary,business_summary,temporary,outputs,policy)
    receipt_path=zones['temporary_run']/policy['build_receipt_file']; json_write(receipt_path,receipt)
    for zone in zones.values():
        for path in directory_regular_files(zone): os.chmod(path,stat.S_IRUSR|stat.S_IRGRP|stat.S_IROTH)
    result=verify_clean_root(config_path,root,'BUILT')
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
        elif kind in {
            'business_operator_registry_and_coverage','business_operator_execution_summary',
            'business_operator_replay_deterministic','business_operator_registry_mutation_rejected',
            'business_operator_gates_exact','business_config_expected_execution_match_summary',
        }:
            mapping=read_jsonl((base/inp['mapping_file']).resolve()); adoption=read_jsonl((base/inp['adoption_file']).resolve())
            schema=json.load(open((base/inp['schema_file']).resolve(),encoding='utf-8')); receipts=read_jsonl((base/inp['receipt_file']).resolve())
            capabilities=[item for item in mapping if item.get('record_type')=='CAPABILITY_CLOSURE_CANDIDATE']
            if kind=='business_operator_registry_and_coverage':
                checked=validate_business_operator_registry_records(mapping,capabilities); actual={key:checked[key] for key in exp}
            elif kind=='business_operator_registry_mutation_rejected':
                target=next(item for item in mapping if item.get('record_type')=='BUSINESS_OPERATOR_IMPLEMENTATION_REGISTRY')
                target['operators'].pop(inp['operator_id'])
                try: validate_business_operator_registry_records(mapping,capabilities); actual=False
                except RuntimeError as error: actual=str(error).startswith('BUSINESS_OPERATOR_IMPLEMENTATION_REGISTRY_MISMATCH')
            else:
                validate_capability_specs(capabilities,adoption,schema,receipts)
                declarative,_=execute_capability_bounded_witnesses(capabilities,receipts)
                first,summary=execute_authoritative_business_operators(capabilities,declarative)
                if kind=='business_operator_execution_summary': actual={key:summary[key] for key in exp}
                elif kind=='business_config_expected_execution_match_summary':
                    config=json.load(open((base/inp['config_file']).resolve(),encoding='utf-8'))
                    locked=config['bounded_business_operator_execution_v2']
                    summary_keys=(
                        'registered_operator_count','routed_capability_count','semantic_callable_invocation_count',
                        'distinct_semantic_callable_invoked_count','boundary_gate_execution_count','pre_callable_rejected_count',
                        'unresolved_rejected_count','pending_user_rejected_count','candidate_business_output_count',
                        'formal_fact_output_count','execution_results_sha256','scope_statement',
                    )
                    actual=(
                        locked.get('registry_version')==BUSINESS_OPERATOR_REGISTRY_VERSION
                        and all(locked.get(key)==summary.get(key) for key in summary_keys)
                    )
                elif kind=='business_operator_gates_exact':
                    actual={
                        'runnable':sum(item['gate_status']=='BOUNDED_BUSINESS_SEMANTICS_EXECUTED' and item['semantic_callable_invoked'] and item['business_operator_semantics_executed'] for item in first),
                        'boundary_zero':sum(item['gate_status']=='ZERO_OBJECTIVE_OUTPUT_BOUNDARY_EXECUTED' and item['boundary_gate_executed'] and not item['semantic_callable_invoked'] and not item['business_operator_semantics_executed'] and item['candidate_business_output_count']==0 for item in first),
                        'unresolved_rejected':sum(item['gate_status']=='REJECTED_UNRESOLVED_PRESERVE_UNKNOWN' and item['pre_callable_rejected'] and not item['semantic_callable_invoked'] and item['candidate_output'] is None for item in first),
                        'pending_rejected':sum(item['gate_status']=='REJECTED_PENDING_USER_DECISION' and item['pre_callable_rejected'] and not item['semantic_callable_invoked'] and item['candidate_output'] is None for item in first),
                        'formal_fact_output_count':sum(item['formal_fact_output_count'] for item in first),
                    }
                else:
                    second,second_summary=execute_authoritative_business_operators(capabilities,declarative)
                    actual=canonical(first)==canonical(second) and summary['execution_results_sha256']==second_summary['execution_results_sha256']
        elif kind=='semantic_rule_positive_negative_matrix':
            actual=validate_all_semantic_rule_synthetic_fixtures()
        elif kind=='capability_output_contract_all_runnable':
            mapping=read_jsonl((base/inp['mapping_file']).resolve()); receipts=read_jsonl((base/inp['receipt_file']).resolve())
            capabilities=[item for item in mapping if item.get('record_type')=='CAPABILITY_CLOSURE_CANDIDATE']
            declarative,_=execute_capability_bounded_witnesses(capabilities,receipts)
            results,_=execute_authoritative_business_operators(capabilities,declarative)
            runnable=[]
            for item,result in zip(sorted(capabilities,key=lambda row:row['object_id']),results):
                if result['gate_status']!='BOUNDED_BUSINESS_SEMANTICS_EXECUTED': continue
                validate_declared_capability_output(item,result['candidate_output']); runnable.append(result)
            actual={
                'runnable_count':len(runnable),'full_eleven_field_contract_count':len(runnable),
                'rule_specific_payload_valid_count':len(runnable),
                'all_candidate_outputs_have_exact_declared_fields':all(set(result['candidate_output'])==set(DECLARED_CAPABILITY_OUTPUT_FIELDS) for result in runnable),
            }
        elif kind in {'trade_object_package_schema_valid','trade_object_package_schema_mutation_rejected'}:
            schema=json.load(open((base/inp['schema_file']).resolve(),encoding='utf-8'))
            if kind=='trade_object_package_schema_valid': actual=validate_trade_object_package_schema(schema)
            else:
                set_nested(schema,inp['mutation']['field'],inp['mutation']['value'])
                try: validate_trade_object_package_schema(schema); actual=False
                except RuntimeError as error: actual=str(error).startswith(inp['expected_error_prefix'])
        elif kind=='user_semantics_zero_instance_gate':
            fact_path=(base/inp['fact_base_file']).resolve(); schema=json.load(open((base/inp['schema_file']).resolve(),encoding='utf-8'))
            records=read_jsonl(fact_path); original_sha=sha_file(fact_path)
            checked=validate_fact_base_against_schema(records,schema)
            def rejected(field,value,prefix):
                mutated=json.loads(canonical(records)); mutated[0][field]=value
                try: validate_fact_base_against_schema(mutated,schema); return False
                except RuntimeError as error: return str(error).startswith(prefix)
            actual={
                'record_count':len(records),
                'all_user_statement_null':all(item.get('user_statement') is None for item in records),
                'all_ai_interpretation_null':all(item.get('ai_interpretation') is None for item in records),
                'unapproved_user_statement_rejected':rejected('user_statement',{'statement_id':'UNAPPROVED','does_not_override_fact':True},'FACT_BASE_UNAPPROVED_USER_STATEMENT_REJECTED:'),
                'ai_interpretation_rejected':rejected('ai_interpretation',{'interpretation_id':'AI-AS-USER'},'FACT_BASE_AI_INTERPRETATION_REJECTED:'),
                'false_override_flag_rejected':rejected('user_statement',{'statement_id':'UNAPPROVED','does_not_override_fact':False},'FACT_BASE_UNAPPROVED_USER_STATEMENT_REJECTED:'),
                'fact_base_file_identity_unchanged':sha_file(fact_path)==original_sha,
                'zero_instance_gate_passed':checked['user_semantics_zero_instance_gate_passed'] and checked['ai_interpretation_zero_instance_gate_passed'],
            }
        elif kind=='recomputation_dry_run_modes_and_gates':
            contract_path=(base/inp['contract_file']).resolve(); receipts_path=(base/inp['receipt_file']).resolve()
            with tempfile.TemporaryDirectory() as temp_name:
                temp=Path(temp_name); synthetic=[]; identity=[]
                with contextlib.redirect_stdout(io.StringIO()):
                    for recomputation_id,fixture in inp['fixtures'].items():
                        fixture_path=temp/(recomputation_id+'.json'); json_write(fixture_path,fixture)
                        synthetic.append(run_recomputation_dry_run(contract_path,receipts_path,recomputation_id,'SYNTHETIC_FIXTURE',fixture_path,temp/(recomputation_id+'-synthetic.json')))
                        identity.append(run_recomputation_dry_run(contract_path,receipts_path,recomputation_id,'LOCKED_INPUT_IDENTITY_DRY_RUN',None,temp/(recomputation_id+'-identity.json')))
                    try: run_recomputation_dry_run(contract_path,receipts_path,'S3INPUT-40','REAL',(temp/'none'),temp/'real.json'); real_rejected=False
                    except RuntimeError as error: real_rejected=str(error).startswith('REAL_RECOMPUTATION_NOT_AUTHORIZED:')
                    existing=temp/'exists.json'; json_write(existing,{})
                    try: run_recomputation_dry_run(contract_path,receipts_path,'S3INPUT-40','LOCKED_INPUT_IDENTITY_DRY_RUN',None,existing); overwrite_rejected=False
                    except RuntimeError as error: overwrite_rejected=str(error).startswith('RECOMPUTATION_DRY_RUN_OUTPUT_ALREADY_EXISTS:')
                actual={
                    'synthetic_count':len(synthetic),'identity_only_count':len(identity),
                    'all_real_business_values_unread':all(item['real_business_values_read'] is False for item in synthetic+identity),
                    'all_formal_output_zero':all(item['formal_result_output_count']==0 for item in synthetic+identity),
                    'real_mode_rejected':real_rejected,'overwrite_rejected':overwrite_rejected,
                }
        elif kind in {'clean_root_initialize_twice','clean_root_pollution_rejected','clean_root_bounded_rebuild_twice'}:
            config_path=(base/inp['config_file']).resolve(); sample_path=(base/inp['sample_file']).resolve()
            with tempfile.TemporaryDirectory() as temp_name:
                temp=Path(temp_name); roots=[temp/'root-a',temp/'root-b']
                with contextlib.redirect_stdout(io.StringIO()):
                    initialized=[init_clean_root(config_path,root) for root in roots]
                config=json.load(open(config_path,encoding='utf-8')); policy=config['clean_production_environment']; rule_zone=policy['zones']['rules_program_config']
                def internal_paths(root):
                    zone=root/rule_zone
                    return zone/clean_active_program_name(policy),zone/policy['runtime_config_file'],zone/policy['sample_manifest_file']
                def internal_run(root,command,phase=None):
                    program,runtime,samples=internal_paths(root)
                    args=[sys.executable,str(program),command,'--config',str(runtime),'--root',str(root)]
                    if command=='build-clean-root-bounded': args.extend(['--samples',str(samples)])
                    if phase is not None: args.extend(['--phase',phase])
                    result=subprocess.run(args,text=True,capture_output=True)
                    return result
                if kind=='clean_root_initialize_twice':
                    verification=[internal_run(root,'verify-clean-root','INITIALIZED') for root in roots]
                    actual=all(item['phase']=='INITIALIZED' and item['input_file_count']==74 for item in initialized) and all(item.returncode==0 for item in verification)
                elif kind=='clean_root_pollution_rejected':
                    zone=roots[0]/policy['zones']['temporary_run']; (zone/'unexpected.txt').write_text('pollution',encoding='utf-8')
                    result=internal_run(roots[0],'verify-clean-root','INITIALIZED')
                    actual=result.returncode!=0 and 'CLEAN_ENVIRONMENT_INITIAL_STATE_POLLUTED' in result.stderr
                else:
                    results=[internal_run(root,'build-clean-root-bounded') for root in roots]
                    if any(item.returncode!=0 for item in results):
                        failed=next(item for item in results if item.returncode!=0)
                        raise RuntimeError('CLEAN_ROOT_INTERNAL_BUILD_FAILED:'+failed.stderr[-4000:])
                    output_zone=policy['zones']['candidate_outputs']; names=policy['built_output_files']
                    deterministic_names=[name for name in names if name!=policy['quality_receipt_file']]
                    hashes=[{name:sha_file(root/output_zone/name) for name in deterministic_names} for root in roots]
                    reported=[json.loads([line for line in item.stdout.splitlines() if line.strip()][-1]) for item in results]
                    actual=all(item['phase']=='BUILT' and item['active_program_inside_clean_root'] and item['config_inside_clean_root'] and item['built_outputs_independently_rebuilt_and_compared'] for item in reported) and hashes[0]==hashes[1]
        elif kind=='clean_root_internal_binding_and_synchronized_tamper_rejected':
            config_path=(base/inp['config_file']).resolve()
            with tempfile.TemporaryDirectory() as temp_name:
                root=Path(temp_name)/'root'; input_tamper_root=Path(temp_name)/'input-tamper-root'
                with contextlib.redirect_stdout(io.StringIO()):
                    init_clean_root(config_path,root); init_clean_root(config_path,input_tamper_root)
                config=json.load(open(config_path,encoding='utf-8')); policy=config['clean_production_environment']; rules=root/policy['zones']['rules_program_config']
                program=rules/clean_active_program_name(policy); runtime=rules/policy['runtime_config_file']; samples=rules/policy['sample_manifest_file']
                build_result=subprocess.run([sys.executable,str(program),'build-clean-root-bounded','--config',str(runtime),'--samples',str(samples),'--root',str(root)],text=True,capture_output=True)
                if build_result.returncode!=0: raise RuntimeError('CLEAN_ROOT_INTERNAL_BUILD_FAILED:'+build_result.stderr[-4000:])
                external_config_rejected=False
                try: verify_clean_root(config_path,root,'BUILT')
                except RuntimeError as error: external_config_rejected=str(error).startswith('CLEAN_ENVIRONMENT_EXTERNAL_CONFIG_FORBIDDEN_AFTER_INITIALIZATION:')
                outputs=root/policy['zones']['candidate_outputs']; temporary=root/policy['zones']['temporary_run']; ai_path=outputs/config['view_generation']['outputs']['ai_view']; receipt_path=temporary/policy['build_receipt_file']
                os.chmod(ai_path,stat.S_IRUSR|stat.S_IWUSR); ai_path.write_text(ai_path.read_text(encoding='utf-8')+'\nTAMPER',encoding='utf-8'); os.chmod(ai_path,stat.S_IRUSR|stat.S_IRGRP|stat.S_IROTH)
                os.chmod(receipt_path,stat.S_IRUSR|stat.S_IWUSR); receipt=json.load(open(receipt_path,encoding='utf-8')); receipt['file_identities']['candidate_outputs'][ai_path.name]={'bytes':ai_path.stat().st_size,'sha256':sha_file(ai_path)}; json_write(receipt_path,receipt); os.chmod(receipt_path,stat.S_IRUSR|stat.S_IRGRP|stat.S_IROTH)
                tamper_result=subprocess.run([sys.executable,str(program),'verify-clean-root','--config',str(runtime),'--root',str(root),'--phase','BUILT'],text=True,capture_output=True)
                input_rules=input_tamper_root/policy['zones']['rules_program_config']; input_zone=input_tamper_root/policy['zones']['read_only_inputs']; input_program=input_rules/clean_active_program_name(policy); input_runtime=input_rules/policy['runtime_config_file']; input_manifest_path=input_rules/policy['initialization_manifest_file']
                input_manifest=json.load(open(input_manifest_path,encoding='utf-8')); target_meta=input_manifest['input_files'][0]; target_input=input_zone/target_meta['file']
                os.chmod(target_input,stat.S_IRUSR|stat.S_IWUSR); target_input.write_bytes(target_input.read_bytes()+b'\n'); os.chmod(target_input,stat.S_IRUSR|stat.S_IRGRP|stat.S_IROTH)
                target_meta['bytes']=target_input.stat().st_size; target_meta['sha256']=sha_file(target_input)
                os.chmod(input_manifest_path,stat.S_IRUSR|stat.S_IWUSR); json_write(input_manifest_path,input_manifest); os.chmod(input_manifest_path,stat.S_IRUSR|stat.S_IRGRP|stat.S_IROTH)
                input_tamper_result=subprocess.run([sys.executable,str(input_program),'verify-clean-root','--config',str(input_runtime),'--root',str(input_tamper_root),'--phase','INITIALIZED'],text=True,capture_output=True)
                actual={
                    'external_config_rejected':external_config_rejected,
                    'synchronized_output_and_receipt_tamper_rejected':tamper_result.returncode!=0 and 'CLEAN_ENVIRONMENT_INDEPENDENT_REBUILD_MISMATCH' in tamper_result.stderr,
                    'synchronized_input_and_manifest_tamper_rejected':input_tamper_result.returncode!=0 and 'CLEAN_ENVIRONMENT_INPUT_IDENTITY_OR_READ_ONLY_MISMATCH' in input_tamper_result.stderr,
                }
        elif kind in {
            'user_visual_payload_complete','user_visual_mutations_rejected','user_visual_deterministic',
            'user_visual_external_resource_rejected','user_visual_plain_sections',
        }:
            fact_path=(base/inp['fact_base_file']).resolve(); records=read_jsonl(fact_path)
            config=json.load(open((base/inp['config_file']).resolve(),encoding='utf-8'))
            payload=build_user_visual_payload(records,fact_path,config['contract_id'])
            html=build_user_visual_html(payload)
            maximum=int(config['view_generation']['user_visual']['maximum_bytes'])
            if kind=='user_visual_payload_complete':
                checked=validate_user_visual_payload(payload,records,fact_path)
                actual={key:checked[key] for key in exp}
            elif kind=='user_visual_mutations_rejected':
                mutations=[]
                removed=json.loads(canonical(payload)); removed['objects'][0]['records'].pop(); mutations.append(removed)
                duplicated=json.loads(canonical(payload)); duplicated['objects'][0]['records'].append(json.loads(canonical(duplicated['objects'][0]['records'][0]))); mutations.append(duplicated)
                reordered=json.loads(canonical(payload)); reordered['objects'][0]['records'][0],reordered['objects'][0]['records'][1]=reordered['objects'][0]['records'][1],reordered['objects'][0]['records'][0]; mutations.append(reordered)
                tampered=json.loads(canonical(payload)); tampered['objects'][0]['records'][0]['canonical_record_sha256']='0'*64; mutations.append(tampered)
                rejected=[]
                for mutated in mutations:
                    try: validate_user_visual_payload(mutated,records,fact_path); rejected.append(False)
                    except RuntimeError: rejected.append(True)
                actual=all(rejected) and len(rejected)==4
            elif kind=='user_visual_deterministic':
                second=build_user_visual_html(build_user_visual_payload(records,fact_path,config['contract_id']))
                actual=html==second and hashlib.sha256(html.encode('utf-8')).hexdigest()==hashlib.sha256(second.encode('utf-8')).hexdigest()
            elif kind=='user_visual_external_resource_rejected':
                injected_variants=(
                    html.replace('</head>','<script src="https://example.invalid/forbidden.js"></script></head>',1),
                    html.replace('</style>','@import "https://example.invalid/forbidden.css";</style>',1),
                    html.replace('</main>','<iframe src="https://example.invalid/"></iframe></main>',1),
                    html.replace('</body>','<script>fetch("https://example.invalid/")</script></body>',1),
                )
                rejected=[]
                for injected in injected_variants:
                    try: validate_user_visual_html(injected,payload,records,fact_path,maximum); rejected.append(False)
                    except RuntimeError as error: rejected.append(str(error).startswith('USER_VISUAL_EXTERNAL_RESOURCE_OR_NETWORK_CALL_FOUND'))
                actual=all(rejected)
            else:
                checked=validate_user_visual_html(html,payload,records,fact_path,maximum)
                outputs=config['view_generation']['outputs']
                detail_labels={detail['label'] for obj in payload['objects'] for record in obj['records'] for detail in record['details']}
                actual={
                    'no_active_excel_output':outputs.get('user_visual','').endswith('.html') and all(not str(value).endswith('.xlsx') for value in outputs.values()),
                    'plain_chinese_sections_present':checked['plain_chinese_visual_sections_present'],
                    'responsive_rules_present':checked['responsive_rules_present'],
                    'reduced_motion_respected':checked['reduced_motion_rule_present'],
                    'inline_javascript_static_structure_valid':checked['inline_javascript_static_structure_valid'],
                    'plain_detail_labels_in_chinese':detail_labels.issubset(set(VISUAL_DETAIL_LABELS.values())),
                    'short_user_guide_present':'怎么核对' in html and '记下卡片底部的事实编号' in html,
                    'user_understandability_waiting':checked['user_understandability_status']=='WAITING_FOR_USER_ACTUAL_REVIEW',
                }
        elif kind in {'compact_ai_view_complete_and_smaller','compact_ai_view_mutations_rejected'}:
            records=read_jsonl((base/inp['fact_base_file']).resolve()); manifest=json.load(open((base/inp['sample_file']).resolve(),encoding='utf-8')); config=json.load(open((base/inp['config_file']).resolve(),encoding='utf-8'))
            fact_path=(base/inp['fact_base_file']).resolve(); text_view=build_compact_ai_view_text(records,fact_path,manifest,config['view_generation'])
            maximum_bytes=int(config['view_generation']['ai_view']['maximum_bytes'])
            if kind=='compact_ai_view_complete_and_smaller':
                checked=validate_compact_ai_view(text_view,records,fact_path,maximum_bytes)
                actual={key:checked[key] for key in exp if key in checked}
                actual['smaller_than_fact_base']=len(text_view.encode('utf-8'))<fact_path.stat().st_size
            else:
                def mutated_view(predicate,mutator):
                    lines=text_view.splitlines(keepends=True); inside=False
                    for index,line in enumerate(lines):
                        content=line[:-1] if line.endswith('\n') else line
                        if content=='```jsonl': inside=True; continue
                        if content=='```' and inside: inside=False; continue
                        if not inside or not content.strip(): continue
                        item=json.loads(content)
                        if predicate(item):
                            changed=mutator(json.loads(canonical(item)))
                            lines[index]=canonical(changed)+('\n' if line.endswith('\n') else '')
                            return ''.join(lines)
                    raise RuntimeError('COMPACT_AI_MUTATION_TARGET_NOT_FOUND')
                field_index={field:index for index,field in enumerate(COMPACT_AI_FIELDS)}
                mutations={
                    'fact_base_identity':mutated_view(
                        lambda item:item.get('k')=='HEADER',
                        lambda item:{**item,'authoritative_fact_base_sha256':'0'*64},
                    ),
                    'normalized_value':mutated_view(
                        lambda item:item.get('k')=='F',
                        lambda item:{**item,'v':item['v'][:field_index['normalized_value']]+[None]+item['v'][field_index['normalized_value']+1:]},
                    ),
                    'dictionary':mutated_view(
                        lambda item:item.get('k')=='D' and item.get('name')=='evidence_status' and item.get('values'),
                        lambda item:{**item,'values':['MUTATED_VALUE',*item['values'][1:]]},
                    ),
                    'object_counts':mutated_view(
                        lambda item:item.get('k')=='O',
                        lambda item:{**item,'counts':{**item['counts'],'F':item['counts']['F']+1}},
                    ),
                    'relation_index':mutated_view(
                        lambda item:item.get('k')=='O' and item.get('relation_fact_ids'),
                        lambda item:{**item,'relation_fact_ids':[item['relation_fact_ids'][0],*item['relation_fact_ids']]},
                    ),
                }
                rejected={}
                for name,mutated in mutations.items():
                    try: validate_compact_ai_view(mutated,records,fact_path,maximum_bytes); rejected[name]=False
                    except RuntimeError: rejected[name]=True
                actual=all(rejected.values()) and set(rejected)==set(inp['required_mutations'])
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
    b=sub.add_parser('build-bounded'); b.add_argument('--config',required=True); b.add_argument('--samples',required=True); b.add_argument('--output',required=True); b.add_argument('--mirror-root')
    v=sub.add_parser('build-views'); v.add_argument('--config',required=True); v.add_argument('--output-dir'); v.add_argument('--preview-dir'); v.add_argument('--verification-output'); v.add_argument('--fact-base')
    c=sub.add_parser('verify-capabilities'); c.add_argument('--mapping',required=True); c.add_argument('--adoption',required=True); c.add_argument('--schema',required=True); c.add_argument('--receipts',required=True); c.add_argument('--output'); c.add_argument('--business-output')
    r=sub.add_parser('recompute-dry-run'); r.add_argument('--contract',required=True); r.add_argument('--receipts',required=True); r.add_argument('--recomputation-id',required=True); r.add_argument('--mode',required=True); r.add_argument('--fixture'); r.add_argument('--output',required=True)
    ci=sub.add_parser('init-clean-root'); ci.add_argument('--config',required=True); ci.add_argument('--root',required=True)
    cv=sub.add_parser('verify-clean-root'); cv.add_argument('--config',required=True); cv.add_argument('--root',required=True); cv.add_argument('--phase',choices=['INITIALIZED','BUILT'],required=True)
    cb=sub.add_parser('build-clean-root-bounded'); cb.add_argument('--config',required=True); cb.add_argument('--samples',required=True); cb.add_argument('--root',required=True)
    t=sub.add_parser('self-test'); t.add_argument('--tests',required=True)
    a=p.parse_args()
    if a.cmd=='load-selected-objects': load_selected_objects(a.receipts,a.output_dir)
    elif a.cmd=='build-bounded': build(a.config,a.samples,a.output,a.mirror_root)
    elif a.cmd=='build-views': build_views(a.config,a.output_dir,a.preview_dir,a.verification_output,a.fact_base)
    elif a.cmd=='verify-capabilities': verify_capabilities(a.mapping,a.adoption,a.schema,a.receipts,a.output,a.business_output)
    elif a.cmd=='recompute-dry-run': run_recomputation_dry_run(a.contract,a.receipts,a.recomputation_id,a.mode,a.fixture,a.output)
    elif a.cmd=='init-clean-root': init_clean_root(a.config,a.root)
    elif a.cmd=='verify-clean-root': print(canonical(verify_clean_root(a.config,a.root,a.phase)))
    elif a.cmd=='build-clean-root-bounded': build_clean_root_bounded(a.config,a.samples,a.root)
    else: run_tests(a.tests)
