# 阶段二｜POST-K01工程对象九轴拆解×错误传播×后置纠偏总账

当前状态：`STAGE2_POSTK01_AUDIT=FROZEN_CLOSED`

USER_ACCEPTANCE=`ACCEPTED_FOR_STAGE2_FROZEN_AUDIT_BASELINE`。这是对Stage2 POST-K01历史审计基线的全局验收和封存，不是32个POST候选的逐项采用确认。

候选正式采用数：`0`；候选采用层USER验收数：`0`；复制授权数：`0`；正式晋升数：`0`。

所有`UNKNOWN`、`UNRESOLVED`、证据限制、历史字节缺失与`MAIN_PROCESS_BASELINE_CANDIDATE_MULTIPLE`继续原样保留。Stage3及全部下游任务仍未授权。

## 实物分母与证明边界

- 当前有证据指针的工程对象身份：1401。这是实际报告汇合后按路径去重的对象，不声称是全项目所有POST对象。
- 复合工作簿独立内容：19个SHA；覆盖K08/K09 3个、权益专项6个、PC1/RW/QA 10个。
- 每个复合对象按九轴+十笔→136扩容单列。当前路径相同不代表历史字节相同；历史字节缺失必须写UNKNOWN。

## 19个复合对象十轴卡

### S2COMP-001｜K08_M4-F2_10笔同源回归候选.xlsx

- 路径：/Users/luodaluo/Desktop/30天复盘原始数据/08_M4-F2十笔同源回归与136笔扩容准入验收/01_十笔同源回归候选/K08_M4-F2_10笔同源回归候选.xlsx
- 大小/SHA：275313 B；d97c5b44ac01c8865f0369ec0e00168e10a5ec8203fdb3b98b5651aa2eb947ab
- 当前Stage2状态：POST_REFERENCE_ONLY
- 特定边界：十笔初版；后续被D3/V2修正。

|轴|裁定|依据与限制|
|---|---|---|
|客观数据载荷|BOUNDED|23表结构、十笔/136身份与H接口有实物证据；不等全部数据正确。|
|派生或计算结果|MIXED|部分汇总和H值存在；K09四公式静态别名失配。|
|身份与周期映射|BOUNDED|T001—T136与阶段映射可核；四个107别名另禁。|
|算法、公式和口径|NO_WHOLE_PASS|公式元素/缓存静态检查不等重算或全算法通过。|
|字段语义和名称|MIXED|D3客观H与历史M/N分层；K09内部码回露。|
|USER人工内容|SOURCE_PRESERVED_WITH_LIMITS|旧十笔坐标与全域待填分母不同；不推断USER意图。|
|产品结构|HISTORICAL_CANDIDATE|23表、7可见、16隐藏；产品封存不等事实全对。|
|页面布局与展示|NOT_FULLY_RETESTED|静态结构可见，未在本轮执行WPS全页验收。|
|审计版本血缘|BOUND|V1→V2→K09身份与差异可追；初坏版部分缺字节。|
|十笔→136扩容|IMPLEMENTED_WITH_GAPS|结构扩到136，但后置UI/资金和若干公式问题未传播修复。|

### S2COMP-002｜K08_M4-F2_10笔同源回归_D3客观MFE_MAE纠偏候选_V2.xlsx

- 路径：/Users/luodaluo/Desktop/30天复盘原始数据/08_M4-F2十笔同源回归与136笔扩容准入验收/06_D3纠偏候选构建/01_十笔纠偏候选/K08_M4-F2_10笔同源回归_D3客观MFE_MAE纠偏候选_V2.xlsx
- 大小/SHA：294277 B；566859c05118dab219ef5b15c978e37e85799032e203b48c71cc4f119018a7d0
- 当前Stage2状态：POST_CORRECTION_CANDIDATE
- 特定边界：十笔D3纠偏后候选；不等全工作簿已验。

|轴|裁定|依据与限制|
|---|---|---|
|客观数据载荷|BOUNDED|23表结构、十笔/136身份与H接口有实物证据；不等全部数据正确。|
|派生或计算结果|MIXED|部分汇总和H值存在；K09四公式静态别名失配。|
|身份与周期映射|BOUNDED|T001—T136与阶段映射可核；四个107别名另禁。|
|算法、公式和口径|NO_WHOLE_PASS|公式元素/缓存静态检查不等重算或全算法通过。|
|字段语义和名称|MIXED|D3客观H与历史M/N分层；K09内部码回露。|
|USER人工内容|SOURCE_PRESERVED_WITH_LIMITS|旧十笔坐标与全域待填分母不同；不推断USER意图。|
|产品结构|HISTORICAL_CANDIDATE|23表、7可见、16隐藏；产品封存不等事实全对。|
|页面布局与展示|NOT_FULLY_RETESTED|静态结构可见，未在本轮执行WPS全页验收。|
|审计版本血缘|BOUND|V1→V2→K09身份与差异可追；初坏版部分缺字节。|
|十笔→136扩容|IMPLEMENTED_WITH_GAPS|结构扩到136，但后置UI/资金和若干公式问题未传播修复。|

### S2COMP-003｜K09_M4-F2_136笔完整增强版候选产品.xlsx

- 路径：/Users/luodaluo/Desktop/30天复盘原始数据/09_M4-F2结构下的136笔完整增强版候选产品构建/01_136笔候选产品/K09_M4-F2_136笔完整增强版候选产品.xlsx
- 大小/SHA：1129192 B；587f6a2942a1497c7f862997c282ff77c408540f0cf5871c8181861cd545416c
- 当前Stage2状态：POST_EXTRACT_SUBOBJECT_CANDIDATE_WITH_PROHIBITED_FIELDS
- 特定边界：136结构可抽子对象；四个T001→107公式禁用，时区与保护保留未决。

|轴|裁定|依据与限制|
|---|---|---|
|客观数据载荷|BOUNDED|23表结构、十笔/136身份与H接口有实物证据；不等全部数据正确。|
|派生或计算结果|MIXED|部分汇总和H值存在；K09四公式静态别名失配。|
|身份与周期映射|BOUNDED|T001—T136与阶段映射可核；四个107别名另禁。|
|算法、公式和口径|NO_WHOLE_PASS|公式元素/缓存静态检查不等重算或全算法通过。|
|字段语义和名称|MIXED|D3客观H与历史M/N分层；K09内部码回露。|
|USER人工内容|SOURCE_PRESERVED_WITH_LIMITS|旧十笔坐标与全域待填分母不同；不推断USER意图。|
|产品结构|HISTORICAL_CANDIDATE|23表、7可见、16隐藏；产品封存不等事实全对。|
|页面布局与展示|NOT_FULLY_RETESTED|静态结构可见，未在本轮执行WPS全页验收。|
|审计版本血缘|BOUND|V1→V2→K09身份与差异可追；初坏版部分缺字节。|
|十笔→136扩容|IMPLEMENTED_WITH_GAPS|结构扩到136，但后置UI/资金和若干公式问题未传播修复。|

### S2COMP-004｜EQ_P3_POST_DFR_10_TRADE_DUAL_FUND_USER_VIEW.xlsx

- 路径：/Users/luodaluo/Desktop/30天复盘原始数据/00_WORK总控/24_账户权益重建专项/03A_EQ-P3后置_双资金绝对重建可行性专项/EQ_P3_POST_DFR_10_TRADE_DUAL_FUND_USER_VIEW.xlsx
- 大小/SHA：21664 B；e8dc4e6dba13ea39d6c3297925392a769a3a696652603d0ec0e14aa1cc49ddeb
- 当前Stage2状态：POST_RECOMPUTE_METHOD_CANDIDATE
- 特定边界：账户权益专项历史版本；条件模型、用户视图和精确事实必须分开。

|轴|裁定|依据与限制|
|---|---|---|
|客观数据载荷|SOURCE_GRADED|截图、资金事实与行情来源分级；不是交易所原生完整权益。|
|派生或计算结果|CONDITIONAL|双资金、Mark和区间为条件模型或派生结果。|
|身份与周期映射|BOUNDED|十笔/相关周期映射有文件；同秒双路径保留。|
|算法、公式和口径|CHANGED_POST_K01|动作分钟Mark、外包络和区间方法属于POST算法变化。|
|字段语义和名称|MIXED|用户视图白话化与精确字段分开。|
|USER人工内容|ANCHOR_ONLY|用户锚和反馈不是账户原生真值。|
|产品结构|USER_VIEW|主要为十笔有限验收视图。|
|页面布局与展示|PRESENTATION|用户视图改版不证明资金算法。|
|审计版本血缘|BOUND|六个历史版本SHA可核；每版含义单列。|
|十笔→136扩容|PARTIAL_INTERFACE_ONLY|EQ-P4形成136节点接口，不证明十笔产品可直接扩136。|

### S2COMP-005｜EQ_P3_POST_DFR_RW001_10_TRADE_DUAL_FUND_USER_VIEW.xlsx

- 路径：/Users/luodaluo/Desktop/30天复盘原始数据/00_WORK总控/24_账户权益重建专项/03A_EQ-P3后置_双资金绝对重建可行性专项/RW001_38张截图整日合法时间窗盲验补强/EQ_P3_POST_DFR_RW001_10_TRADE_DUAL_FUND_USER_VIEW.xlsx
- 大小/SHA：22845 B；cc38cc7c06f941d2481abab1b8a981ce79829f9be4aa0bfa2dd61dee049291d5
- 当前Stage2状态：POST_RECOMPUTE_METHOD_CANDIDATE
- 特定边界：账户权益专项历史版本；条件模型、用户视图和精确事实必须分开。

|轴|裁定|依据与限制|
|---|---|---|
|客观数据载荷|SOURCE_GRADED|截图、资金事实与行情来源分级；不是交易所原生完整权益。|
|派生或计算结果|CONDITIONAL|双资金、Mark和区间为条件模型或派生结果。|
|身份与周期映射|BOUNDED|十笔/相关周期映射有文件；同秒双路径保留。|
|算法、公式和口径|CHANGED_POST_K01|动作分钟Mark、外包络和区间方法属于POST算法变化。|
|字段语义和名称|MIXED|用户视图白话化与精确字段分开。|
|USER人工内容|ANCHOR_ONLY|用户锚和反馈不是账户原生真值。|
|产品结构|USER_VIEW|主要为十笔有限验收视图。|
|页面布局与展示|PRESENTATION|用户视图改版不证明资金算法。|
|审计版本血缘|BOUND|六个历史版本SHA可核；每版含义单列。|
|十笔→136扩容|PARTIAL_INTERFACE_ONLY|EQ-P4形成136节点接口，不证明十笔产品可直接扩136。|

### S2COMP-006｜EQ_P3_POST_DFR_RW002_10_TRADE_DUAL_FUND_USER_VIEW.xlsx

- 路径：/Users/luodaluo/Desktop/30天复盘原始数据/00_WORK总控/24_账户权益重建专项/03A_EQ-P3后置_双资金绝对重建可行性专项/RW002_35xx期初精度纠正与根因审计/EQ_P3_POST_DFR_RW002_10_TRADE_DUAL_FUND_USER_VIEW.xlsx
- 大小/SHA：24189 B；9300a2664d5f021cb016e34c09c22f4e9a853733e10fdbdd39a11e769227882e
- 当前Stage2状态：POST_RECOMPUTE_METHOD_CANDIDATE
- 特定边界：账户权益专项历史版本；条件模型、用户视图和精确事实必须分开。

|轴|裁定|依据与限制|
|---|---|---|
|客观数据载荷|SOURCE_GRADED|截图、资金事实与行情来源分级；不是交易所原生完整权益。|
|派生或计算结果|CONDITIONAL|双资金、Mark和区间为条件模型或派生结果。|
|身份与周期映射|BOUNDED|十笔/相关周期映射有文件；同秒双路径保留。|
|算法、公式和口径|CHANGED_POST_K01|动作分钟Mark、外包络和区间方法属于POST算法变化。|
|字段语义和名称|MIXED|用户视图白话化与精确字段分开。|
|USER人工内容|ANCHOR_ONLY|用户锚和反馈不是账户原生真值。|
|产品结构|USER_VIEW|主要为十笔有限验收视图。|
|页面布局与展示|PRESENTATION|用户视图改版不证明资金算法。|
|审计版本血缘|BOUND|六个历史版本SHA可核；每版含义单列。|
|十笔→136扩容|PARTIAL_INTERFACE_ONLY|EQ-P4形成136节点接口，不证明十笔产品可直接扩136。|

### S2COMP-007｜EQ_P3_USER_LIMITED_ACCEPTANCE_VIEW.xlsx

- 路径：/Users/luodaluo/Desktop/30天复盘原始数据/00_WORK总控/24_账户权益重建专项/03_EQ-P3_10笔独立复算与用户本人有限验收/03_用户有限验收视图/EQ_P3_USER_LIMITED_ACCEPTANCE_VIEW.xlsx
- 大小/SHA：26241 B；16f4e252713ca1da1d7241a29803b8345d5e3c4e7cd53d5118e8d715760504c7
- 当前Stage2状态：POST_PRESENTATION_ONLY_CANDIDATE
- 特定边界：账户权益专项历史版本；条件模型、用户视图和精确事实必须分开。

|轴|裁定|依据与限制|
|---|---|---|
|客观数据载荷|SOURCE_GRADED|截图、资金事实与行情来源分级；不是交易所原生完整权益。|
|派生或计算结果|CONDITIONAL|双资金、Mark和区间为条件模型或派生结果。|
|身份与周期映射|BOUNDED|十笔/相关周期映射有文件；同秒双路径保留。|
|算法、公式和口径|CHANGED_POST_K01|动作分钟Mark、外包络和区间方法属于POST算法变化。|
|字段语义和名称|MIXED|用户视图白话化与精确字段分开。|
|USER人工内容|ANCHOR_ONLY|用户锚和反馈不是账户原生真值。|
|产品结构|USER_VIEW|主要为十笔有限验收视图。|
|页面布局与展示|PRESENTATION|用户视图改版不证明资金算法。|
|审计版本血缘|BOUND|六个历史版本SHA可核；每版含义单列。|
|十笔→136扩容|PARTIAL_INTERFACE_ONLY|EQ-P4形成136节点接口，不证明十笔产品可直接扩136。|

### S2COMP-008｜EQ_P3_RW002_USER_LIMITED_ACCEPTANCE_VIEW.xlsx

- 路径：/Users/luodaluo/Desktop/30天复盘原始数据/00_WORK总控/24_账户权益重建专项/03_EQ-P3_10笔独立复算与用户本人有限验收/05_RW002_P2当前基线重对齐与用户验收重签发/EQ_P3_RW002_USER_LIMITED_ACCEPTANCE_VIEW.xlsx
- 大小/SHA：26267 B；68f57a62c9f1af399e1a5dc4b882badbe9f8f627973a71127b7766ce7ea98b6d
- 当前Stage2状态：POST_PRESENTATION_ONLY_CANDIDATE
- 特定边界：账户权益专项历史版本；条件模型、用户视图和精确事实必须分开。

|轴|裁定|依据与限制|
|---|---|---|
|客观数据载荷|SOURCE_GRADED|截图、资金事实与行情来源分级；不是交易所原生完整权益。|
|派生或计算结果|CONDITIONAL|双资金、Mark和区间为条件模型或派生结果。|
|身份与周期映射|BOUNDED|十笔/相关周期映射有文件；同秒双路径保留。|
|算法、公式和口径|CHANGED_POST_K01|动作分钟Mark、外包络和区间方法属于POST算法变化。|
|字段语义和名称|MIXED|用户视图白话化与精确字段分开。|
|USER人工内容|ANCHOR_ONLY|用户锚和反馈不是账户原生真值。|
|产品结构|USER_VIEW|主要为十笔有限验收视图。|
|页面布局与展示|PRESENTATION|用户视图改版不证明资金算法。|
|审计版本血缘|BOUND|六个历史版本SHA可核；每版含义单列。|
|十笔→136扩容|PARTIAL_INTERFACE_ONLY|EQ-P4形成136节点接口，不证明十笔产品可直接扩136。|

### S2COMP-009｜EQ_P3_RW003_USER_LIMITED_ACCEPTANCE_VIEW.xlsx

- 路径：/Users/luodaluo/Desktop/30天复盘原始数据/00_WORK总控/24_账户权益重建专项/03_EQ-P3_10笔独立复算与用户本人有限验收/06_RW003_用户验收视图白话化重构/EQ_P3_RW003_USER_LIMITED_ACCEPTANCE_VIEW.xlsx
- 大小/SHA：27741 B；5d58eeb9eff5d91f4cfee793874214c445dfefbfcd8a3bc8a0b8567f7c0390bb
- 当前Stage2状态：POST_PRESENTATION_ONLY_CANDIDATE
- 特定边界：账户权益专项历史版本；条件模型、用户视图和精确事实必须分开。

|轴|裁定|依据与限制|
|---|---|---|
|客观数据载荷|SOURCE_GRADED|截图、资金事实与行情来源分级；不是交易所原生完整权益。|
|派生或计算结果|CONDITIONAL|双资金、Mark和区间为条件模型或派生结果。|
|身份与周期映射|BOUNDED|十笔/相关周期映射有文件；同秒双路径保留。|
|算法、公式和口径|CHANGED_POST_K01|动作分钟Mark、外包络和区间方法属于POST算法变化。|
|字段语义和名称|MIXED|用户视图白话化与精确字段分开。|
|USER人工内容|ANCHOR_ONLY|用户锚和反馈不是账户原生真值。|
|产品结构|USER_VIEW|主要为十笔有限验收视图。|
|页面布局与展示|PRESENTATION|用户视图改版不证明资金算法。|
|审计版本血缘|BOUND|六个历史版本SHA可核；每版含义单列。|
|十笔→136扩容|PARTIAL_INTERFACE_ONLY|EQ-P4形成136节点接口，不证明十笔产品可直接扩136。|

### S2COMP-010｜K08_PC1_10笔用户产品后置纠偏候选_用户审阅副本.xlsx

- 路径：/Users/luodaluo/Desktop/30天复盘原始数据/00_WORK总控/25_K08-PC1_10笔用户产品后置纠偏候选/03_用户审阅副本/K08_PC1_10笔用户产品后置纠偏候选_用户审阅副本.xlsx
- 大小/SHA：289412 B；4ada029619890685aa2f5b55e472030620b1d5c964808126dbae3007b20dc992
- 当前Stage2状态：POST_PROHIBITED
- 特定边界：被否定首稿或失败中间版，不作当前产品。

|轴|裁定|依据与限制|
|---|---|---|
|客观数据载荷|INHERITED_BOUNDED|输入锁及映射CSV可核；后台旧值不是本轮全量重验。|
|派生或计算结果|MIXED|旧14后台继承；10根VALUE只修数据类型，不重算交易数值。|
|身份与周期映射|BOUNDED|十笔映射可核；转账来源5分钟规则不是原生资金批次。|
|算法、公式和口径|NO_WHOLE_PASS|1113公式元素静态可核；无全算法复算。|
|字段语义和名称|PARTLY_CORRECTED|三标签精确修正；部分可见词清洗可能损失原语义。|
|USER人工内容|LIMITED_ACCEPTANCE|USER仅对指定显示/功能/三标签给反馈或通过。|
|产品结构|TEN_TRADE_PRODUCT|七可见十六隐藏；PC1首稿与RW后继分开。|
|页面布局与展示|PRESENTATION_CANDIDATE|49页内导航+12其他链接、5页A6冻结；未重开WPS全页。|
|审计版本血缘|BOUND_WITH_MISSING_BYTES|主链可核；a389和旧68793脚本字节缺失。|
|十笔→136扩容|NOT_IMPLEMENTED|代码/布局仍有十笔约束；没有136产品传播实施。|

### S2COMP-011｜K08_PC1_RW001_10笔用户产品后置纠偏候选_用户审阅副本.xlsx

- 路径：/Users/luodaluo/Desktop/30天复盘原始数据/00_WORK总控/25_K08-PC1_10笔用户产品后置纠偏候选/07_RW001用户审阅副本/K08_PC1_RW001_10笔用户产品后置纠偏候选_用户审阅副本.xlsx
- 大小/SHA：297160 B；23d4e415260fd9f448b2ae142e8773db6a10192568c451101ab1c93164e7ef93
- 当前Stage2状态：POST_REFERENCE_ONLY
- 特定边界：历史/QA/中间版本，仅供血缘和定点验证。

|轴|裁定|依据与限制|
|---|---|---|
|客观数据载荷|INHERITED_BOUNDED|输入锁及映射CSV可核；后台旧值不是本轮全量重验。|
|派生或计算结果|MIXED|旧14后台继承；10根VALUE只修数据类型，不重算交易数值。|
|身份与周期映射|BOUNDED|十笔映射可核；转账来源5分钟规则不是原生资金批次。|
|算法、公式和口径|NO_WHOLE_PASS|1113公式元素静态可核；无全算法复算。|
|字段语义和名称|PARTLY_CORRECTED|三标签精确修正；部分可见词清洗可能损失原语义。|
|USER人工内容|LIMITED_ACCEPTANCE|USER仅对指定显示/功能/三标签给反馈或通过。|
|产品结构|TEN_TRADE_PRODUCT|七可见十六隐藏；PC1首稿与RW后继分开。|
|页面布局与展示|PRESENTATION_CANDIDATE|49页内导航+12其他链接、5页A6冻结；未重开WPS全页。|
|审计版本血缘|BOUND_WITH_MISSING_BYTES|主链可核；a389和旧68793脚本字节缺失。|
|十笔→136扩容|NOT_IMPLEMENTED|代码/布局仍有十笔约束；没有136产品传播实施。|

### S2COMP-012｜K08_PC1_RW002_10笔用户产品后置纠偏候选_用户审阅副本.xlsx

- 路径：/Users/luodaluo/Desktop/30天复盘原始数据/00_WORK总控/25_K08-PC1_10笔用户产品后置纠偏候选/10_RW002用户审阅副本/K08_PC1_RW002_10笔用户产品后置纠偏候选_用户审阅副本.xlsx
- 大小/SHA：299457 B；775e13adc3e20f26530d6d2d252b166307ca3d3306283c2011970d995af88264
- 当前Stage2状态：POST_PRESENTATION_ONLY_CANDIDATE
- 特定边界：历史/QA/中间版本，仅供血缘和定点验证。

|轴|裁定|依据与限制|
|---|---|---|
|客观数据载荷|INHERITED_BOUNDED|输入锁及映射CSV可核；后台旧值不是本轮全量重验。|
|派生或计算结果|MIXED|旧14后台继承；10根VALUE只修数据类型，不重算交易数值。|
|身份与周期映射|BOUNDED|十笔映射可核；转账来源5分钟规则不是原生资金批次。|
|算法、公式和口径|NO_WHOLE_PASS|1113公式元素静态可核；无全算法复算。|
|字段语义和名称|PARTLY_CORRECTED|三标签精确修正；部分可见词清洗可能损失原语义。|
|USER人工内容|LIMITED_ACCEPTANCE|USER仅对指定显示/功能/三标签给反馈或通过。|
|产品结构|TEN_TRADE_PRODUCT|七可见十六隐藏；PC1首稿与RW后继分开。|
|页面布局与展示|PRESENTATION_CANDIDATE|49页内导航+12其他链接、5页A6冻结；未重开WPS全页。|
|审计版本血缘|BOUND_WITH_MISSING_BYTES|主链可核；a389和旧68793脚本字节缺失。|
|十笔→136扩容|NOT_IMPLEMENTED|代码/布局仍有十笔约束；没有136产品传播实施。|

### S2COMP-013｜WORK_WPS_RW003_FINAL_LABEL_FIX_ACCEPTANCE_20260811_V1.xlsx

- 路径：/Users/luodaluo/Desktop/30天复盘原始数据/00_WORK总控/25_K08-PC1_10笔用户产品后置纠偏候选/99_RW003实现与QA/WORK_WPS_RW003_FINAL_LABEL_FIX_ACCEPTANCE_20260811_V1.xlsx
- 大小/SHA：299519 B；e095257905888b54ec0dbeda71055c0bf32489c5c4096b5bac8e0daba236c044
- 当前Stage2状态：POST_EXTRACT_SUBOBJECT_CANDIDATE
- 特定边界：RW003最终十笔版；仅子对象候选，不证明136或全算法。

|轴|裁定|依据与限制|
|---|---|---|
|客观数据载荷|INHERITED_BOUNDED|输入锁及映射CSV可核；后台旧值不是本轮全量重验。|
|派生或计算结果|MIXED|旧14后台继承；10根VALUE只修数据类型，不重算交易数值。|
|身份与周期映射|BOUNDED|十笔映射可核；转账来源5分钟规则不是原生资金批次。|
|算法、公式和口径|NO_WHOLE_PASS|1113公式元素静态可核；无全算法复算。|
|字段语义和名称|PARTLY_CORRECTED|三标签精确修正；部分可见词清洗可能损失原语义。|
|USER人工内容|LIMITED_ACCEPTANCE|USER仅对指定显示/功能/三标签给反馈或通过。|
|产品结构|TEN_TRADE_PRODUCT|七可见十六隐藏；PC1首稿与RW后继分开。|
|页面布局与展示|PRESENTATION_CANDIDATE|49页内导航+12其他链接、5页A6冻结；未重开WPS全页。|
|审计版本血缘|BOUND_WITH_MISSING_BYTES|主链可核；a389和旧68793脚本字节缺失。|
|十笔→136扩容|NOT_IMPLEMENTED|代码/布局仍有十笔约束；没有136产品传播实施。|

### S2COMP-014｜K08_PC1_RW003_FINAL_THREE_LABEL_FIX_PRECHANGE_USER_REVIEW_COPY_QA_ONLY.xlsx

- 路径：/Users/luodaluo/Desktop/30天复盘原始数据/00_WORK总控/25_K08-PC1_10笔用户产品后置纠偏候选/99_RW003实现与QA/K08_PC1_RW003_FINAL_THREE_LABEL_FIX_PRECHANGE_USER_REVIEW_COPY_QA_ONLY.xlsx
- 大小/SHA：299508 B；902a882e13cfe44924d75f5dd25a953be32cb0bbbe0eafb7d34f7227e803e013
- 当前Stage2状态：POST_REFERENCE_ONLY
- 特定边界：历史/QA/中间版本，仅供血缘和定点验证。

|轴|裁定|依据与限制|
|---|---|---|
|客观数据载荷|INHERITED_BOUNDED|输入锁及映射CSV可核；后台旧值不是本轮全量重验。|
|派生或计算结果|MIXED|旧14后台继承；10根VALUE只修数据类型，不重算交易数值。|
|身份与周期映射|BOUNDED|十笔映射可核；转账来源5分钟规则不是原生资金批次。|
|算法、公式和口径|NO_WHOLE_PASS|1113公式元素静态可核；无全算法复算。|
|字段语义和名称|PARTLY_CORRECTED|三标签精确修正；部分可见词清洗可能损失原语义。|
|USER人工内容|LIMITED_ACCEPTANCE|USER仅对指定显示/功能/三标签给反馈或通过。|
|产品结构|TEN_TRADE_PRODUCT|七可见十六隐藏；PC1首稿与RW后继分开。|
|页面布局与展示|PRESENTATION_CANDIDATE|49页内导航+12其他链接、5页A6冻结；未重开WPS全页。|
|审计版本血缘|BOUND_WITH_MISSING_BYTES|主链可核；a389和旧68793脚本字节缺失。|
|十笔→136扩容|NOT_IMPLEMENTED|代码/布局仍有十笔约束；没有136产品传播实施。|

### S2COMP-015｜QA_WPS_FORMAT_BEFORE.xlsx

- 路径：/Users/luodaluo/Desktop/30天复盘原始数据/00_WORK总控/25_K08-PC1_10笔用户产品后置纠偏候选/99_RW003实现与QA/QA_WPS_FORMAT_BEFORE.xlsx
- 大小/SHA：299438 B；64ab0c76747a64f0350de6e0a33c1a366b9e03bf7479c1f8bc80cf8abfa80510
- 当前Stage2状态：POST_PROHIBITED
- 特定边界：被否定首稿或失败中间版，不作当前产品。

|轴|裁定|依据与限制|
|---|---|---|
|客观数据载荷|INHERITED_BOUNDED|输入锁及映射CSV可核；后台旧值不是本轮全量重验。|
|派生或计算结果|MIXED|旧14后台继承；10根VALUE只修数据类型，不重算交易数值。|
|身份与周期映射|BOUNDED|十笔映射可核；转账来源5分钟规则不是原生资金批次。|
|算法、公式和口径|NO_WHOLE_PASS|1113公式元素静态可核；无全算法复算。|
|字段语义和名称|PARTLY_CORRECTED|三标签精确修正；部分可见词清洗可能损失原语义。|
|USER人工内容|LIMITED_ACCEPTANCE|USER仅对指定显示/功能/三标签给反馈或通过。|
|产品结构|TEN_TRADE_PRODUCT|七可见十六隐藏；PC1首稿与RW后继分开。|
|页面布局与展示|PRESENTATION_CANDIDATE|49页内导航+12其他链接、5页A6冻结；未重开WPS全页。|
|审计版本血缘|BOUND_WITH_MISSING_BYTES|主链可核；a389和旧68793脚本字节缺失。|
|十笔→136扩容|NOT_IMPLEMENTED|代码/布局仍有十笔约束；没有136产品传播实施。|

### S2COMP-016｜QA_NUMERIC_COERCION_T049.xlsx

- 路径：/Users/luodaluo/Desktop/30天复盘原始数据/00_WORK总控/25_K08-PC1_10笔用户产品后置纠偏候选/99_RW003实现与QA/QA_NUMERIC_COERCION_T049.xlsx
- 大小/SHA：343195 B；b6469da2a77a154dcd5b87670b7267ec9965e1b3575447a2acc78a5ef79349f6
- 当前Stage2状态：POST_REFERENCE_ONLY
- 特定边界：历史/QA/中间版本，仅供血缘和定点验证。

|轴|裁定|依据与限制|
|---|---|---|
|客观数据载荷|INHERITED_BOUNDED|输入锁及映射CSV可核；后台旧值不是本轮全量重验。|
|派生或计算结果|MIXED|旧14后台继承；10根VALUE只修数据类型，不重算交易数值。|
|身份与周期映射|BOUNDED|十笔映射可核；转账来源5分钟规则不是原生资金批次。|
|算法、公式和口径|NO_WHOLE_PASS|1113公式元素静态可核；无全算法复算。|
|字段语义和名称|PARTLY_CORRECTED|三标签精确修正；部分可见词清洗可能损失原语义。|
|USER人工内容|LIMITED_ACCEPTANCE|USER仅对指定显示/功能/三标签给反馈或通过。|
|产品结构|TEN_TRADE_PRODUCT|七可见十六隐藏；PC1首稿与RW后继分开。|
|页面布局与展示|PRESENTATION_CANDIDATE|49页内导航+12其他链接、5页A6冻结；未重开WPS全页。|
|审计版本血缘|BOUND_WITH_MISSING_BYTES|主链可核；a389和旧68793脚本字节缺失。|
|十笔→136扩容|NOT_IMPLEMENTED|代码/布局仍有十笔约束；没有136产品传播实施。|

### S2COMP-017｜QA_WPS_FORMAT_AFTER.xlsx

- 路径：/Users/luodaluo/Desktop/30天复盘原始数据/00_WORK总控/25_K08-PC1_10笔用户产品后置纠偏候选/99_RW003实现与QA/QA_WPS_FORMAT_AFTER.xlsx
- 大小/SHA：343166 B；b13d71c4de719a1075e62dd29310e95c7bd04d208152ea9f9710c0d506e69a73
- 当前Stage2状态：POST_REFERENCE_ONLY
- 特定边界：历史/QA/中间版本，仅供血缘和定点验证。

|轴|裁定|依据与限制|
|---|---|---|
|客观数据载荷|INHERITED_BOUNDED|输入锁及映射CSV可核；后台旧值不是本轮全量重验。|
|派生或计算结果|MIXED|旧14后台继承；10根VALUE只修数据类型，不重算交易数值。|
|身份与周期映射|BOUNDED|十笔映射可核；转账来源5分钟规则不是原生资金批次。|
|算法、公式和口径|NO_WHOLE_PASS|1113公式元素静态可核；无全算法复算。|
|字段语义和名称|PARTLY_CORRECTED|三标签精确修正；部分可见词清洗可能损失原语义。|
|USER人工内容|LIMITED_ACCEPTANCE|USER仅对指定显示/功能/三标签给反馈或通过。|
|产品结构|TEN_TRADE_PRODUCT|七可见十六隐藏；PC1首稿与RW后继分开。|
|页面布局与展示|PRESENTATION_CANDIDATE|49页内导航+12其他链接、5页A6冻结；未重开WPS全页。|
|审计版本血缘|BOUND_WITH_MISSING_BYTES|主链可核；a389和旧68793脚本字节缺失。|
|十笔→136扩容|NOT_IMPLEMENTED|代码/布局仍有十笔约束；没有136产品传播实施。|

### S2COMP-018｜WORK_WPS_RW003_VALUE_ROOT_FIX_ACCEPTANCE_20260811_V1.xlsx

- 路径：/Users/luodaluo/Desktop/30天复盘原始数据/00_WORK总控/25_K08-PC1_10笔用户产品后置纠偏候选/99_RW003实现与QA/WORK_WPS_RW003_VALUE_ROOT_FIX_ACCEPTANCE_20260811_V1.xlsx
- 大小/SHA：343387 B；68ffee848575bb0c4e1e1d223e2ce7fdb7d6c431ed5594aea6d7156cd413510e
- 当前Stage2状态：POST_REFERENCE_ONLY
- 特定边界：历史/QA/中间版本，仅供血缘和定点验证。

|轴|裁定|依据与限制|
|---|---|---|
|客观数据载荷|INHERITED_BOUNDED|输入锁及映射CSV可核；后台旧值不是本轮全量重验。|
|派生或计算结果|MIXED|旧14后台继承；10根VALUE只修数据类型，不重算交易数值。|
|身份与周期映射|BOUNDED|十笔映射可核；转账来源5分钟规则不是原生资金批次。|
|算法、公式和口径|NO_WHOLE_PASS|1113公式元素静态可核；无全算法复算。|
|字段语义和名称|PARTLY_CORRECTED|三标签精确修正；部分可见词清洗可能损失原语义。|
|USER人工内容|LIMITED_ACCEPTANCE|USER仅对指定显示/功能/三标签给反馈或通过。|
|产品结构|TEN_TRADE_PRODUCT|七可见十六隐藏；PC1首稿与RW后继分开。|
|页面布局与展示|PRESENTATION_CANDIDATE|49页内导航+12其他链接、5页A6冻结；未重开WPS全页。|
|审计版本血缘|BOUND_WITH_MISSING_BYTES|主链可核；a389和旧68793脚本字节缺失。|
|十笔→136扩容|NOT_IMPLEMENTED|代码/布局仍有十笔约束；没有136产品传播实施。|

### S2COMP-019｜formula_normalization_roundtrip.xlsx

- 路径：/Users/luodaluo/Desktop/30天复盘原始数据/00_WORK总控/25_K08-PC1_10笔用户产品后置纠偏候选/99_实现与QA/formula_normalization_roundtrip.xlsx
- 大小/SHA：287521 B；b73aea8ab7db8f9e00aeac25680d6fc1caf4cfb21e136fbdc12e639120e17615
- 当前Stage2状态：POST_REFERENCE_ONLY
- 特定边界：历史/QA/中间版本，仅供血缘和定点验证。

|轴|裁定|依据与限制|
|---|---|---|
|客观数据载荷|INHERITED_BOUNDED|输入锁及映射CSV可核；后台旧值不是本轮全量重验。|
|派生或计算结果|MIXED|旧14后台继承；10根VALUE只修数据类型，不重算交易数值。|
|身份与周期映射|BOUNDED|十笔映射可核；转账来源5分钟规则不是原生资金批次。|
|算法、公式和口径|NO_WHOLE_PASS|1113公式元素静态可核；无全算法复算。|
|字段语义和名称|PARTLY_CORRECTED|三标签精确修正；部分可见词清洗可能损失原语义。|
|USER人工内容|LIMITED_ACCEPTANCE|USER仅对指定显示/功能/三标签给反馈或通过。|
|产品结构|TEN_TRADE_PRODUCT|七可见十六隐藏；PC1首稿与RW后继分开。|
|页面布局与展示|PRESENTATION_CANDIDATE|49页内导航+12其他链接、5页A6冻结；未重开WPS全页。|
|审计版本血缘|BOUND_WITH_MISSING_BYTES|主链可核；a389和旧68793脚本字节缺失。|
|十笔→136扩容|NOT_IMPLEMENTED|代码/布局仍有十笔约束；没有136产品传播实施。|

## 71个根级问题案例

### S2CASE-01｜K01候选/副本身份与角色多轮修正

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：K01
- 后继纠偏：K01-R1→R2→R3→R4
- 根级理由：候选角色多次漏修；当前336/10角色与93副本状态可验证；不推出所有候选可靠。
- 原发现ID：ROOT-E001

### S2CASE-02｜K01修复指令引入非法第11角色

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：K01-R2
- 后继纠偏：K01-R4
- 根级理由：AI修复指令自身改变枚举；最终恢复原10角色。
- 原发现ID：ROOT-E002

### S2CASE-03｜K01修复报告范围缩小

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：K01-R3
- 后继纠偏：K01-R4
- 根级理由：恢复全输入/一致性报告；不是所有数据重新计算。
- 原发现ID：ROOT-E003

### S2CASE-04｜K02/K03指令缺精确输出命名

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：K02/K03准备
- 后继纠偏：完整替换合同
- 根级理由：合法停门；不把未运行算计算失败。
- 原发现ID：ROOT-E004

### S2CASE-05｜K02选择了错误来源/旧版本角色

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：K02初版
- 后继纠偏：原附件恢复+K02-R1
- 根级理由：0144/0145与0179/0180必须按具体来源/身份分开。
- 原发现ID：ROOT-E005；ROOT-E007

### S2CASE-06｜K02固定模板映射及伪USER待确认/悬空测试

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：K02初版
- 后继纠偏：两轮字段和615关系修复
- 根级理由：当前关系分布/双向边可验；旧生成脚本固定赋值仍在，不能无条件重跑。
- 原发现ID：ROOT-E006；ROOT-E008

### S2CASE-07｜K02 Manifest新旧统计并存

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：K02修订
- 后继纠偏：第二轮6文件
- 根级理由：只证明登记矛盾修复，不是数值重算。
- 原发现ID：ROOT-E009

### S2CASE-08｜程序确认被扩大为全项技术认可

- 证据状态：CONFIRMED
- 处理状态：EVIDENCE_LIMIT_RETAINED
- 首发阶段：K02、K04、K06、K07、EQP4等
- 后继纠偏：本轮限制解读，不改旧记录
- 根级理由：当时同意/关闭可以真实存在；65标志或USER_CONFIRMED不证明逐字段、算法、SHA理解。
- 原发现ID：ROOT-E010；MID-E001；MID-E007；MID-E014；W06E-F036；LATE-ERR-021；LATE-ERR-027

### S2CASE-09｜K03首次DS重基线授权作者不明

- 证据状态：UNRESOLVED
- 处理状态：UNKNOWN
- 首发阶段：W04-M229 ASSISTANT
- 后继纠偏：W05-M9是另一授权
- 根级理由：ASSISTANT第一人称不能冒充USER；外部当时是否另授未知。
- 原发现ID：ROOT-E011

### S2CASE-10｜K03跨文件状态/历史扫描语义不同步

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：K03/W05接管
- 后继纠偏：7→5→关闭后6+1治理修正
- 根级理由：历史扫描不是当前保护状态；最后17正式身份可核。
- 原发现ID：ROOT-E012

### S2CASE-11｜把K05和K04自身输出错误前置

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：K04准备
- 后继纠偏：合同评估15门
- 根级理由：不是未具备整个后续系统就不可做前置阶段。
- 原发现ID：ROOT-E013

### S2CASE-12｜把单窗口GUI失败推广成全部工具上限

- 证据状态：CONFIRMED
- 处理状态：PARTIALLY_CORRECTED
- 首发阶段：W05/W06联动
- 后继纠偏：B线程/文件验证
- 根级理由：限定失败入口与后来成功路线；不得把同日回忆当原生执行证据。
- 原发现ID：ROOT-E014；W06E-F004；W06E-F005；W06E-F007

### S2CASE-13｜测试成功后过早建议正式接管

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：W06联动
- 后继纠偏：USER纠正资格/治理先后
- 根级理由：属于建议超前；未证K04真实越权执行。
- 原发现ID：W06E-F008；W06E-F010

### S2CASE-14｜恢复DISPATCH及完成分支范围修正

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：受控恢复测试
- 后继纠偏：保TASK/线程，分未送达和已执行恢复
- 根级理由：不能把E002 FINALIZE覆盖推广到所有首发失败。
- 原发现ID：W06E-F011；W06E-F014；W06E-F015

### S2CASE-15｜盲接管提示预装答案及过度删减

- 证据状态：CONFIRMED
- 处理状态：PARTIALLY_CORRECTED
- 首发阶段：全目标理解草案
- 后继纠偏：USER要求全稿去答案
- 根级理由：最终无提示称号不证明环境隔离；补充方案未发不能称已实施。
- 原发现ID：W06E-F016；W06E-F017

### S2CASE-16｜覆盖/能力/静态PASS超出证明范围

- 证据状态：EVIDENCE_LIMIT
- 处理状态：EVIDENCE_LIMIT_RETAINED
- 首发阶段：接管、G6、WPS、后置审计
- 后继纠偏：保留各自实测/静态边界
- 根级理由：机械数、耗时、截图/报告声明不等全语义或全部运行验证；本轮同样受此限。
- 原发现ID：W06E-F003；W06E-F012；W06E-F013；W06E-F018；W06E-F019；W06E-F028；W06E-F041；MID-E031；MID-E036；MID-E040；LATE-ERR-039

### S2CASE-17｜历史第三层审计扩张及一次性全闭环承诺

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：分层接管第三层
- 后继纠偏：USER停止后收敛/分G1-G7
- 根级理由：停止现场和真实已完成项保留，不重写为未发生。
- 原发现ID：W06E-F022；W06E-F024

### S2CASE-18｜转贴分支中的USER标签/AI文本被混用风险

- 证据状态：EVIDENCE_LIMIT
- 处理状态：EVIDENCE_LIMIT_RETAINED
- 首发阶段：W06-M127
- 后继纠偏：分块作者裁定
- 根级理由：原创外壳与复制31/22/27清单分开，不覆盖较新状态。
- 原发现ID：W06E-F023

### S2CASE-19｜G5历史基线无逐文件值不能逆构

- 证据状态：CONFIRMED
- 处理状态：PARTIALLY_CORRECTED
- 首发阶段：G5保护门
- 后继纠偏：6590前瞻A/B+不同次元数据例外
- 根级理由：前瞻保护通过不能倒证6592开工原基线；各次DS授权范围不通用。
- 原发现ID：W06E-F025；W06E-F026；W06E-F033

### S2CASE-20｜G7把代理比较写成USER独立盲核

- 证据状态：CONFIRMED
- 处理状态：EVIDENCE_LIMIT_RETAINED
- 首发阶段：G7A/#43
- 后继纠偏：#43转Chat代比后7B
- 根级理由：原话证明USER委托AI比较，非USER本人技术核对；#45负面安全门另保留。
- 原发现ID：W06E-F029；W06E-F030

### S2CASE-21｜旧DOCX职责未迁移就拟冻结

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：G7B初稿
- 后继纠偏：USER暂扣→新版职责解释
- 根级理由：DOCX身份可绑；初稿没发不算已执行错误；PRE最后逐字版仍未知。
- 原发现ID：W06E-F031；W06E-F032

### S2CASE-22｜K04逻辑SHA错误及危险修复草案

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：K04完成后
- 后继纠偏：仅HASH字段修正副本+32复验
- 根级理由：独立复算ece2…；原合同保留，未重做业务。
- 原发现ID：W06E-F034；W06E-F035

### S2CASE-23｜K05需要截图但正式输入未准入

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：K05前置
- 后继纠偏：限定截图/OCR准入补充
- 根级理由：源早已有与准入是两回事；AI事后动机解释不是早期证据。
- 原发现ID：W06E-F037；W06E-F038

### S2CASE-24｜正常等待即停不符合无人值守目标

- 证据状态：CONFIRMED
- 处理状态：PARTIALLY_CORRECTED
- 首发阶段：W06-M202建议
- 后继纠偏：USER203/205→V1.1
- 根级理由：长期规则修正不等动态运行成功。
- 原发现ID：W06E-F040

### S2CASE-25｜V1.1旧包六漂移与前置一致门冲突

- 证据状态：CONFIRMED
- 处理状态：UNRESOLVED
- 首发阶段：V1.1 preflight
- 后继纠偏：新包重建不追认前置门
- 根级理由：原授权可绑定M214正文SHA84ff…；允许漂移豁免仍未见。
- 原发现ID：W06E-F044

### S2CASE-26｜V1.1正式规则把执行开始放在派发之前

- 证据状态：CONFIRMED
- 处理状态：PARTIALLY_CORRECTED
- 首发阶段：M214及正式规则10第27行
- 后继纠偏：K06合稿纠正派发次序
- 根级理由：不仅草稿；真实执行是否按错误顺序发生仍未知。
- 原发现ID：W06E-F045

### S2CASE-27｜K06有限资金与授权草案缺口

- 证据状态：EVIDENCE_LIMIT
- 处理状态：EVIDENCE_LIMIT_RETAINED
- 首发阶段：K06准备/完成
- 后继纠偏：3修→11修及完整合稿
- 根级理由：未锚定/币种未知/未分配费用必须传递；无全账户余额承诺。
- 原发现ID：W06E-F047；W06E-F048；MID-E002

### S2CASE-28｜K07源保留与控制边界修复

- 证据状态：CONFIRMED
- 处理状态：PARTIALLY_CORRECTED
- 首发阶段：K07合稿/DS停门
- 后继纠偏：受控恢复，3161源格/10冲突保留
- 根级理由：作者、空白、原型与人工不合并成同一USER事实；共享公式仅原标记匹配。
- 原发现ID：MID-E003；MID-E004；MID-E006

### S2CASE-29｜K08授权稿漏项及SHA少b00

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：K08准备
- 后继纠偏：最终替换稿
- 根级理由：文本确定错误；未证明错SHA执行损害。
- 原发现ID：MID-E008；MID-E009；MID-E011

### S2CASE-30｜K08先PASS却缺客观H真实物化

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：K08初版
- 后继纠偏：D3/P0/P1/P2
- 根级理由：计划12H存在不等产品已实现；K09前USER已指出，非全在关闭后才发现。
- 原发现ID：MID-E012；MID-E013；MID-E015；MID-E017

### S2CASE-31｜T069时间变化在版本间反复

- 证据状态：UNRESOLVED
- 处理状态：UNKNOWN
- 首发阶段：K08初版/V2/K09
- 后继纠偏：K06源时间另为依据
- 根级理由：03:07:24→17→24→17非单调继承；不能只按最新外观判真。
- 原发现ID：MID-E018

### S2CASE-32｜P0区间降级与signed MAE规则缺口

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：K08P0
- 后继纠偏：R1及后续收口
- 根级理由：MIN signed MAE与MAX非负幅度区分；未证明旧金额一定算错。
- 原发现ID：MID-E019；MID-E020

### S2CASE-33｜用户阶段数、同秒证据与技术H不等价

- 证据状态：EVIDENCE_LIMIT
- 处理状态：EVIDENCE_LIMIT_RETAINED
- 首发阶段：P0 405→210
- 后继纠偏：动作→订单→条件单根证据补强
- 根级理由：T112零时长保阶段但无H；不能推心理决定次数。
- 原发现ID：MID-E021

### S2CASE-34｜P0虚假收口/结构越界/枚举与基数混淆

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：K08P0 R1/R2
- 后继纠偏：USER拒延后→V2收口
- 根级理由：23表不变，十笔27阶段，20DATA/12H/3TRACE；产品12H与后台12列多对多。
- 原发现ID：MID-E023；MID-E024；MID-E025；MID-E026；MID-E027；MID-E028

### S2CASE-35｜K08治理PASS后实物仍旧状态

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：K08P1
- 后继纠偏：5文件GOV-FIX
- 根级理由：13业务合同与5治理区别，不据报告PASS推全部同步。
- 原发现ID：MID-E022；MID-E030；MID-E032

### S2CASE-36｜P2准备门检查错文件和字段时点

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：K08P2
- 后继纠偏：原T002继续
- 根级理由：停门零写不算业务重执行。
- 原发现ID：MID-E033

### S2CASE-37｜P2/P3验收对象、映射及数量误写

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：K08纠偏验收
- 后继纠偏：定点报告纠正/最终关闭
- 根级理由：1:1/12列/27↔42/20历史pending/75条/46工单分别纠正，未因此重做业务。
- 原发现ID：MID-E034；MID-E035；MID-E038；MID-E041；MID-E053

### S2CASE-38｜本人验收门被代理WPS和模板同意代替

- 证据状态：CONFIRMED
- 处理状态：PARTIALLY_CORRECTED
- 首发阶段：K08关闭/K09
- 后继纠偏：本人补验收→资金与UI异议
- 根级理由：M359先说未看，K09关闭报告在后，AI拟暂停更晚；授权确有不等本人检查。
- 原发现ID：MID-E037；MID-E047；MID-E048

### S2CASE-39｜K09旧坐标18格修复及披露/角色问题

- 证据状态：CONFIRMED
- 处理状态：PARTIALLY_CORRECTED
- 首发阶段：K09RW001/Work代修
- 后继纠偏：一次性后置追认+披露
- 根级理由：不能认定旧十笔18格真丢：当前旧十T20格都在，新增18格落T002–010；初坏字节缺。
- 原发现ID：MID-E042；MID-E043；MID-E044；MID-E045

### S2CASE-40｜K09持续治理引用/运行状态不同步

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：K09关闭前
- 后继纠偏：19既有文件修正
- 根级理由：不以总报告PASS替代各控制表身份。
- 原发现ID：MID-E046

### S2CASE-41｜K08资金事件滚动被当账户权益

- 证据状态：CONFIRMED
- 处理状态：PARTIALLY_CORRECTED
- 首发阶段：M4-F2→K08
- 后继纠偏：EQ专项→RW003呈现
- 根级理由：旧数字未传播K09，旧语义槽位传播；资金绝对锚未知/条件来源保留。
- 原发现ID：MID-E050；MID-E051；MID-E052；LATE-ERR-001；LATE-ERR-003

### S2CASE-42｜USER近似回忆被改成工程精确数

- 证据状态：CONFIRMED
- 处理状态：EVIDENCE_LIMIT_RETAINED
- 首发阶段：T123资金反馈
- 后继纠偏：保留USER两万多原精度
- 根级理由：AI22,216不变成USER自己精确确认。
- 原发现ID：LATE-ERR-002

### S2CASE-43｜原始USDT未进入K05/K06币种层

- 证据状态：CONFIRMED
- 处理状态：CORRECTED_IN_SUCCESSOR_ONLY
- 首发阶段：K05/K06
- 后继纠偏：EQP1/P2重新来源准入
- 根级理由：不回写旧currency UNKNOWN为当时已知。
- 原发现ID：LATE-ERR-004

### S2CASE-44｜P2目标分钟Mark被阶段极值替代

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：EQ-P2初版
- 后继纠偏：EQ-P2-RW001
- 根级理由：58来源记录/53节点改变；后继计算使用新源，不重跑旧生成器。
- 原发现ID：LATE-ERR-005

### S2CASE-45｜P2 USER产品决定/历史M-N保护/Manifest口径错位

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：EQ-P2验收
- 后继纠偏：RW001及终验补充
- 根级理由：下一阶段授权不是产品决定；H接口不能证明人工格未改；尾LF/排除对象单列。
- 原发现ID：LATE-ERR-006；LATE-ERR-007；LATE-ERR-008

### S2CASE-46｜T087同秒外包络被单路径和USER_RESOLVED消差

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：P2/P3配对返工初轮
- 后继纠偏：P2RW002+P3RW002
- 根级理由：exactfalse但mismatch0的比较器豁免真实存在；用户未裁定9000先后。
- 原发现ID：LATE-ERR-009；LATE-ERR-010；LATE-ERR-011

### S2CASE-47｜EQ-P3用户视图看不懂/旧状态提示

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：EQ-P3-RW002
- 后继纠偏：EQ-P3-RW003纯展示
- 根级理由：不把页面否定扩为P2所有算法错。
- 原发现ID：LATE-ERR-012

### S2CASE-48｜双资金锚点来源与精度/日窗/收益/Copy范围

- 证据状态：CONFIRMED
- 处理状态：PARTIALLY_CORRECTED
- 首发阶段：DFR初版
- 后继纠偏：RW001日窗→RW002精度和口径→EQP4
- 根级理由：35条件exact、[35,36)上限不含、收益联合范围、UI与经济/Copy范围不可混用。
- 原发现ID：LATE-ERR-013；LATE-ERR-014；LATE-ERR-016；LATE-ERR-017；LATE-ERR-019；LATE-ERR-020

### S2CASE-49｜只爱看卡片被推成只在卡片填全部人工

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：W06-M443
- 后继纠偏：USER-M444→445纠正
- 根级理由：阅读习惯不是填写载体决策；早定人工136整合不算新目标。
- 原发现ID：LATE-ERR-015

### S2CASE-50｜DFR封存聚合SHA字段不一致

- 证据状态：HISTORICAL_REPORTED
- 处理状态：CORRECTED
- 首发阶段：DFR-RW001
- 后继纠偏：同TASK技术返工
- 根级理由：31逐文件不变；不能由回执推未读旧中间字节完整。
- 原发现ID：LATE-ERR-018

### S2CASE-51｜PC1首稿用户视角不合格

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：4ada首稿
- 后继纠偏：RW001回归K08V2母版
- 根级理由：错误页面与独立CSV分开；原始业务来源不随页面废弃删除。
- 原发现ID：LATE-ERR-022

### S2CASE-52｜RW001迁移状态和过期脚本SHA

- 证据状态：CONFIRMED
- 处理状态：PARTIALLY_CORRECTED
- 首发阶段：RW001网络恢复
- 后继纠偏：继续唯一后继非重复执行
- 根级理由：68793旧脚本字节不可恢复；当前75721不可冒充旧态。
- 原发现ID：LATE-ERR-023；LATE-ERR-024

### S2CASE-53｜RW001/RW002导航/数字显示验收不足

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：RW001→RW002→RW003
- 后继纠偏：样式失败→VALUE根式10格
- 根级理由：20正式numeric缓存不证明WPS读取数值；保存探针和根式修复另证。
- 原发现ID：LATE-ERR-025；LATE-ERR-029

### S2CASE-54｜内部划转与外部新资本语义混淆

- 证据状态：CONFIRMED
- 处理状态：PARTIALLY_CORRECTED
- 首发阶段：PC1资金展示
- 后继纠偏：RW002八划转映射
- 根级理由：5分钟/金额匹配仍是上下文归因，不是交易所资金批次原生证明。
- 原发现ID：LATE-ERR-026

### S2CASE-55｜RW002删去K12区间原金额

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：RW002
- 后继纠偏：RW003 K12恢复金额+说明
- 根级理由：USER三项通过只对该范围，不是全部资金算法验收。
- 原发现ID：LATE-ERR-028

### S2CASE-56｜RW003脚本版本/49导航验收继承边界

- 证据状态：EVIDENCE_LIMIT
- 处理状态：EVIDENCE_LIMIT_RETAINED
- 首发阶段：RW003修复/预验
- 后继纠偏：保留版本更换和继承验证
- 根级理由：不能把旧49点击改写为最终版新点49次；3标签QA副本未保存不等第二次WPS保存。
- 原发现ID：LATE-ERR-030；LATE-ERR-031

### S2CASE-57｜后置路线忘记已关闭K09/漏合同影响

- 证据状态：CONFIRMED
- 处理状态：PARTIALLY_CORRECTED
- 首发阶段：PC1后置接续建议
- 后继纠偏：25步计划→Step2–5
- 根级理由：不得凭旧K09closed认定已继承后置；新Work误入口已纠正；未执行Step6。
- 原发现ID：LATE-ERR-032；LATE-ERR-034；LATE-ERR-035；LATE-ERR-036

### S2CASE-58｜十笔后置能力尚未传播136

- 证据状态：CONFIRMED
- 处理状态：UNRESOLVED
- 首发阶段：K09与RW003分支
- 后继纠偏：Step4只读设计
- 根级理由：K09导航/验证范围残留十笔；EQP4136节点不等136产品更新。
- 原发现ID：LATE-ERR-033；LATE-ERR-037

### S2CASE-59｜人工18核心/20历史/22接口与完成责任未冻结

- 证据状态：UNRESOLVED
- 处理状态：UNRESOLVED
- 首发阶段：Step5
- 后继纠偏：八叶仍BLOCKED_STEP6
- 根级理由：2992/1580是建议和估计；不能因数量闭合说语义正确。
- 原发现ID：LATE-ERR-038

### S2CASE-60｜历史AI引W01与当前K07报告冲突

- 证据状态：UNRESOLVED
- 处理状态：UNKNOWN
- 首发阶段：Step5/前置引述
- 后继纠偏：本轮不越界读W01
- 根级理由：T024/T071与T025/T073、131与130保留版本/来源疑点。
- 原发现ID：LATE-ERR-040

### S2CASE-61｜M541/M543采用25步不等授权全部执行

- 证据状态：EVIDENCE_LIMIT
- 处理状态：EVIDENCE_LIMIT_RETAINED
- 首发阶段：POST25步
- 后继纠偏：各步单独门直到M575
- 根级理由：保持最后USER复审请求；W06后不能倒灌。
- 原发现ID：LATE-ERR-041

### S2CASE-62｜K09 T001→107四公式键域不匹配

- 证据状态：CONFIRMED
- 处理状态：UNRESOLVED
- 首发阶段：K09
- 后继纠偏：无在范围内修复证据
- 根级理由：C12/E12/I12/K12匹配107但136后端无107；IFERROR空白掩盖。RW003十笔后端有107，不是同一缺陷。
- 原发现ID：

### S2CASE-63｜K09 M/N保护标志与实际sheetProtection差异

- 证据状态：UNRESOLVED
- 处理状态：UNRESOLVED
- 首发阶段：K08V2→K09
- 后继纠偏：未见在范围内实测或修复
- 根级理由：K08V2有sheetProtection，K09所有23表无；locked样式不等强制保护，实际WPS编辑行为未测。
- 原发现ID：

### S2CASE-64｜K09精度内部枚举直接进入408前台格

- 证据状态：CONFIRMED
- 处理状态：UNRESOLVED
- 首发阶段：K09
- 后继纠偏：未见范围内产品回修
- 根级理由：AS6:AU141共408；K08V2无此可见代码。属于解释/展示差异，不因此判对应数值错。
- 原发现ID：

### S2CASE-65｜K09阶段时间与BJT链/旧动作时间口径混合

- 证据状态：UNRESOLVED
- 处理状态：UNKNOWN
- 首发阶段：K08V2→K09
- 后继纠偏：无唯一时区实现解释
- 根级理由：同27阶段25对-8h、另2对-8h±3s；时间为字符串非Excel serial。不能直接判源事件错误。
- 原发现ID：

### S2CASE-66｜PC1历史Manifest引用滚动控制旧版本

- 证据状态：EVIDENCE_LIMIT
- 处理状态：EVIDENCE_LIMIT_RETAINED
- 首发阶段：PC1→RW003
- 后继纠偏：最终控制时间/关闭链解释变化
- 根级理由：旧Manifest两控制SHA不匹配当前，其他24匹配；当前更新至RW003关闭。不能称初版26全部匹配，也不能称本轮写源。
- 原发现ID：

### S2CASE-67｜RW001可见文本转换不是无损数据层

- 证据状态：EVIDENCE_LIMIT
- 处理状态：EVIDENCE_LIMIT_RETAINED
- 首发阶段：RW001
- 后继纠偏：保留原CSV/源等级
- 根级理由：首次时间选择、删上限不含、剥技术词是显示转换；后台十四表值/公式仍旧，不能用页面替代全事实源。
- 原发现ID：

### S2CASE-68｜三标签QA小裁剪前后同字节且空白

- 证据状态：EVIDENCE_LIMIT
- 处理状态：EVIDENCE_LIMIT_RETAINED
- 首发阶段：RW003最后标签
- 后继纠偏：XML3格差异及另一整页历史截图
- 根级理由：小裁剪不能证明标签；完整图和逐XML证据可分别支持，未在本轮新开WPS。
- 原发现ID：

### S2CASE-69｜G5内部字段补齐与G1 Manifest污染行清理

- 证据状态：CONFIRMED
- 处理状态：CORRECTED
- 首发阶段：G5内部自检
- 后继纠偏：G5FIX1+G5FIX2
- 根级理由：遗漏挑战新发现两子任务；只补集中接管字段/剔除错误字符串，不将6原产物重算。
- 原发现ID：

### S2CASE-70｜Step4合同列与叶项列关系不一致但同义未证

- 证据状态：UNRESOLVED
- 处理状态：UNRESOLVED
- 首发阶段：Step4
- 后继纠偏：未见Step5解释全部16合同差集
- 根级理由：18合同中16两集合不同；各自计数正确。未证明它们应互逆，不能选一套真值或修映射。
- 原发现ID：

### S2CASE-71｜Step5零反转例外补记与后继门升级

- 证据状态：EVIDENCE_LIMIT
- 处理状态：EVIDENCE_LIMIT_RETAINED
- 首发阶段：Step5
- 后继纠偏：EXPLICIT_ZERO_FIELDS_AND_ZERO_REVERSAL_EVIDENCE_REGISTRATION
- 根级理由：身份锁另记录零字段/零反转登记，不等责任矩阵重执行；八叶后继门由Step5更新为Step6。
- 原发现ID：

## 17个证据/范围边界（不计作业务错误）

- S2BOUND-W06E-F001｜原发现W06E-F001｜EVIDENCE_SCOPE_OR_ATTRIBUTION_BOUNDARY_NOT_COUNTED_AS_CONFIRMED_BUSINESS_ERROR
- S2BOUND-W06E-F002｜原发现W06E-F002｜EVIDENCE_SCOPE_OR_ATTRIBUTION_BOUNDARY_NOT_COUNTED_AS_CONFIRMED_BUSINESS_ERROR
- S2BOUND-W06E-F006｜原发现W06E-F006｜EVIDENCE_SCOPE_OR_ATTRIBUTION_BOUNDARY_NOT_COUNTED_AS_CONFIRMED_BUSINESS_ERROR
- S2BOUND-W06E-F009｜原发现W06E-F009｜EVIDENCE_SCOPE_OR_ATTRIBUTION_BOUNDARY_NOT_COUNTED_AS_CONFIRMED_BUSINESS_ERROR
- S2BOUND-W06E-F020｜原发现W06E-F020｜EVIDENCE_SCOPE_OR_ATTRIBUTION_BOUNDARY_NOT_COUNTED_AS_CONFIRMED_BUSINESS_ERROR
- S2BOUND-W06E-F021｜原发现W06E-F021｜EVIDENCE_SCOPE_OR_ATTRIBUTION_BOUNDARY_NOT_COUNTED_AS_CONFIRMED_BUSINESS_ERROR
- S2BOUND-W06E-F027｜原发现W06E-F027｜EVIDENCE_SCOPE_OR_ATTRIBUTION_BOUNDARY_NOT_COUNTED_AS_CONFIRMED_BUSINESS_ERROR
- S2BOUND-W06E-F039｜原发现W06E-F039｜EVIDENCE_SCOPE_OR_ATTRIBUTION_BOUNDARY_NOT_COUNTED_AS_CONFIRMED_BUSINESS_ERROR
- S2BOUND-W06E-F042｜原发现W06E-F042｜EVIDENCE_SCOPE_OR_ATTRIBUTION_BOUNDARY_NOT_COUNTED_AS_CONFIRMED_BUSINESS_ERROR
- S2BOUND-W06E-F043｜原发现W06E-F043｜EVIDENCE_SCOPE_OR_ATTRIBUTION_BOUNDARY_NOT_COUNTED_AS_CONFIRMED_BUSINESS_ERROR
- S2BOUND-W06E-F046｜原发现W06E-F046｜EVIDENCE_SCOPE_OR_ATTRIBUTION_BOUNDARY_NOT_COUNTED_AS_CONFIRMED_BUSINESS_ERROR
- S2BOUND-MID-E005｜原发现MID-E005｜EVIDENCE_SCOPE_OR_ATTRIBUTION_BOUNDARY_NOT_COUNTED_AS_CONFIRMED_BUSINESS_ERROR
- S2BOUND-MID-E010｜原发现MID-E010｜EVIDENCE_SCOPE_OR_ATTRIBUTION_BOUNDARY_NOT_COUNTED_AS_CONFIRMED_BUSINESS_ERROR
- S2BOUND-MID-E016｜原发现MID-E016｜EVIDENCE_SCOPE_OR_ATTRIBUTION_BOUNDARY_NOT_COUNTED_AS_CONFIRMED_BUSINESS_ERROR
- S2BOUND-MID-E029｜原发现MID-E029｜EVIDENCE_SCOPE_OR_ATTRIBUTION_BOUNDARY_NOT_COUNTED_AS_CONFIRMED_BUSINESS_ERROR
- S2BOUND-MID-E039｜原发现MID-E039｜EVIDENCE_SCOPE_OR_ATTRIBUTION_BOUNDARY_NOT_COUNTED_AS_CONFIRMED_BUSINESS_ERROR
- S2BOUND-MID-E049｜原发现MID-E049｜EVIDENCE_SCOPE_OR_ATTRIBUTION_BOUNDARY_NOT_COUNTED_AS_CONFIRMED_BUSINESS_ERROR

## 10条错误/限制/纠偏传播边

|ID|从|到|关系|边界|
|---|---|---|---|---|
|S2EDGE-01|M4-F2旧资金事件滚动/分母|K08初版及D3V2旧资金区|ERROR_OR_LIMIT_PROPAGATED|14557.38/29057.38及旧含义在同SHA绑定工作簿可见；不能解释为精确权益。|
|S2EDGE-02|K08V2旧资金字段槽位/名称|K09资金空值/UNKNOWN接口|SEMANTIC_ONLY_PROPAGATION|旧数值未检出；不能把语义传播写成数字传播。|
|S2EDGE-03|K02已写12H要求和强结构约束|K07引用→K08计数验收|ACCEPTANCE_GAP_PROPAGATED|有要求不等落实；USER在K09前发现后进入D3修复。|
|S2EDGE-04|G7A Chat代理比较|G7冻结及V1.1 USER_BLIND标签|ERROR_OR_LIMIT_PROPAGATED|实际作者、接受动作与USER独立技术核验混淆持续保留。|
|S2EDGE-05|K08十笔历史M/N旧坐标|K09 Work新增M7:N15|ERROR_OR_LIMIT_PROPAGATED|按坐标20与按旧十T20不是同一集合，当前全136有38pending；初坏版缺字节。|
|S2EDGE-06|P2RW002漏落地的旧单路径|P3 USER_RESOLVED比较器|ERROR_OR_LIMIT_PROPAGATED|确有exact false而mismatch0；配对P2/P3修正后保两路径。|
|S2EDGE-07|DFR35条件精确锚点|DFR-RW001→RW002→EQP4|CORRECTION_PROPAGATION|改[35,36)及收益/Copy范围；仍是条件模型，不升级原生exact。|
|S2EDGE-08|RW001/RW002上游字符串净结果|RW003格式补丁64ab/WPS显示|ERROR_OR_LIMIT_PROPAGATED|样式或numeric缓存未改变运行时INDEX文本，10根VALUE后20结果数值化。|
|S2EDGE-09|K08V2+EQP4/H0-H/PC1映射|RW001→RW002→RW003|CORRECTION_AND_SOURCE_LINEAGE|RW001不是从被拒PC1页面继续；保其映射CSV并回归K08母版。|
|S2EDGE-10|RW003十笔和EQP4节点|K09/未来136产品|NOT_PROPAGATED|历史Step3—5只是影响/设计/职责报告；无范围内136产品传播实施。|

## 当前对象身份索引

> 全部1401项详见机器索引；本文件不重复制造巨大路径表。
