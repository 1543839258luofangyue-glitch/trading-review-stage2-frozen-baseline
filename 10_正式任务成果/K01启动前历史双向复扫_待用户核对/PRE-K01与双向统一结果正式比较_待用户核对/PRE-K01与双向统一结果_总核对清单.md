# PRE-K01原始结果 ↔ 双向统一结果｜正式比较总核对清单

## 1. 最终结论

**PRE-K01原始结果 ↔ 双向统一结果正式比较完成。**

比较只以 PRE-K01 历史主 Thread 第462行 `assistant/final_answer` 为旧基线，以修复后的双向统一5项冻结成果为新基线。当前 USER 转贴仅作为本次授权载体，未替代历史原件；上游子执行 transcript 仅作来源证明，未把未进入第462行的业务内容加入比较。

结论：

- 两个基线在 PRE-K01 任务范围内没有真实资产遗漏、真实事实遗漏或实质冲突。
- 主要差异来自对象颗粒、集合哈希方法、同字节副本的路径/角色、历史采用与当前候选的状态维度，以及三处“确认行为成立但固定措辞由 AI 先提供”的作者归属。
- PRE-K01 的 9 项明确排除均仍有效或属于状态维度不同但不冲突；13 项独立未知均仍未解决。
- WORKING HYPOTHESIS：**SUPPORTED_WITH_QUALIFICATION**。核心家族有 USER 阶段/产品确认和流程使用证据，但不能扩大为每个文件、每个字段、每个结果均获 USER 逐项正式认可。
- `POTENTIAL_BOTH_BASELINES_MISSED=0`；`SOURCE_EVIDENCE_CHANGED=0`；其他阻断=0。

## 2. 输入身份硬门

| 输入 | 稳定身份 | 结果 | 使用边界 |
|---|---|---|---|
| 04A进入前状态 | SHA-256 `3af72dc863c72d204fa705e2544b5883a517d9b5abb411389429c66716c3d7f4` | PASS；无其他ACTIVE任务 | 激活后仅执行本比较 |
| PRE-K01主session第462行record | `0b24a69e96593a4543cc7b08285e829687a17ac310157d2508c6ccb68030e391` | PASS | 唯一业务比较基线 |
| PRE-K01第462行解码消息span | `5899a90090fbdcd64d1d49d17be63ee98f21cf599e75603f9894601cfc62018c` | PASS | role=assistant，phase=final_answer |
| PRE-K01主session第1—462行前缀 | `c5d98fb2d300ac22adbf90eaa25d4891f4135a5ba20b024610390cc824a5b6e6` | PASS | 稳定历史前缀 |
| 上游子session第1—666行前缀 | `70dbca15bff0067762fa0b3edc366b06be6e4dd7fd48e6ed0d053e1b416337f9` | PASS | 仅来源证明 |
| 上游子session第666行最终文本 | `ce088ee59a9212c47b8f75797ffa2b2f747d6b6c4fb42b91c4f5037435dac68c` | PASS | 未扩张为业务基线 |
| PRE-K01定位报告 | `208ec5625a1eac91b6faad45374cf398357ee2cf7d87b56fb04d146a691b292e` | PASS | 仅对象身份控制 |
| 双向统一总核对清单 | `54d5197ebb237a86d29d44922e39e517ac7f59a3d544f98cd3798575f409dadd` | PASS | 冻结输入 |
| 双向统一目的1清单 | `f03c42a309a9ec555171a0c370ed7a09f6fd6da9be00b99b1736237a3e4285e1` | PASS | 41项资产 |
| 双向统一目的2清单 | `44f44fb81752a008fecaaf1750c6fcc2a0e88419262c61295ffcada9f4583517` | PASS | 35项事实 |
| 双向统一目的3清单 | `d3f4d13df5914d5af5fa15b1b18fabd48ea30e714c0731041cd5c27a2a9d00a9` | PASS | 770消息作者裁定 |
| 双向统一机器索引 | `bae5a9f5fc92f6d33c533f8da338e64910dec77ee209e4305a663345173e89a4` | PASS | P1=41、P2=35、P3=770、SOURCE_OBJECT=0 |
| 当前USER转贴附件 | 与历史原件分开 | PASS | 只作当前授权/合同，不作旧基线 |

## 3. 比较分母与闭合状态

| 比较单位 | 分母 | 已处置 | 闭合率 |
|---|---:|---:|---:|
| PK01-CLAIM | 65 | 65 | 100% |
| PRE-K01具体资产引用 | 66 | 66 | 100% |
| P1ASSET | 41 | 41 | 100% |
| P2FACT | 35 | 35 | 100% |
| PRE-K01 USER证据声明 | 15 | 15 | 100% |
| PRE-K01明确排除项 | 9 | 9 | 100% |
| PRE-K01独立未知项 | 13 | 13 | 100% |

不同单位没有相加，也没有生成“总体漏扫百分比”。336 个 K01 候选治理项没有与 41 个 P1ASSET 直接相减。

## 4. 65项PK01-CLAIM逐项处置

| PK01-CLAIM | 类别 | 最小完整意义单元 | 原结果位置 | 比较分类 | 处置 |
|---|---|---|---|---|---|
| PK01-CLAIM-0001 | A_BOUNDARY_TIME | 只恢复PRE-K01 DATA BASELINE；K01及后续文件只作边界、锁定和后续读取证据，不作为PRE-K01数据资产 | L1-L10 | EXACT_MATCH, TEMPORAL_CONTEXT_DIFF | SUPPORTED |
| PK01-CLAIM-0002 | E_STATUS_METHOD | 认可/采用必须分为USER明确认可、流程实际采用、K01锁定候选三个维度 | L12-L16 | SEMANTIC_EQUIVALENT, STATUS_DIMENSION_DIFF_NOT_CONFLICT | SUPPORTED |
| PK01-CLAIM-0003 | G_K01_LOCK | K01只锁版本、来源和保护基线，不批准未来构建、重新映射或全部候选准入 | L18-L18 | EXACT_MATCH | SUPPORTED |
| PK01-CLAIM-0004 | A_BOUNDARY_TIME | K01完整名称第一次出现于2026/8/3 04:02:44的assistant消息 | L20-L37 | EXACT_MATCH | SUPPORTED |
| PK01-CLAIM-0005 | A_BOUNDARY_TIME | K01首次命名时状态为READY_NOT_AUTHORIZED，而非已启动 | L39-L49 | EXACT_MATCH | SUPPORTED |
| PK01-CLAIM-0006 | E_USER_AUTHORITY | USER于2026/8/3 04:34:35发出授权启动，assistant于04:34:50开始执行 | L51-L77 | EXACT_MATCH, AUTHORSHIP_CORRECTION | SUPPORTED_WITH_AUTHORSHIP_CORRECTION |
| PK01-CLAIM-0007 | A_BOUNDARY_TIME | PRE-K01截止于USER授权启动之前；此后K01输出只作后验身份与角色证据 | L79-L90 | EXACT_MATCH, POST_K01_VALIDATION_ONLY | SUPPORTED |
| PK01-CLAIM-0008 | G_K01_LOCK | K01因多版本、同SHA副本、错误分支及输入锁风险而建立版本与保护治理 | L92-L112 | SEMANTIC_EQUIVALENT | SUPPORTED |
| PK01-CLAIM-0009 | G_K01_LOCK | K01锁定M4-F2为唯一产品结构母版、136人工母表为唯一人工内容源，含给定SHA | L114-L124 | EXACT_MATCH, SAME_BYTES_DIFFERENT_PATH_ROLE | SUPPORTED |
| PK01-CLAIM-0010 | D_HISTORICAL_ROLE | K01开始前已存在人工母源、M4-F2及交易/周期/资金/条件/行情数据家族，并非空白 | L126-L131 | FAMILY_LEVEL_COVERAGE | SUPPORTED |
| PK01-CLAIM-0011 | D_HISTORICAL_ROLE | K01阶段切换由USER提出与批准、Codex实施，最终Manifest关闭；仅能后验验证 | L133-L162 | POST_K01_VALIDATION_ONLY | SUPPORTED |
| PK01-CLAIM-0012 | B_ASSET_DATA | 五份Binance原始导出的路径、SHA和历史职责 | L164-L214 | EXACT_MATCH | SUPPORTED |
| PK01-CLAIM-0013 | B_ASSET_DATA | 账户结算截图、跟单与仓位补证、条件委托截图三集合及业务成员口径 | L216-L235 | COLLECTION_HASH_METHOD_DIFF | SUPPORTED_WITH_HASH_METHOD_QUALIFICATION |
| PK01-CLAIM-0014 | C_DATA_FAMILY | 632个条件截图原始对象与543条结构化生命周期不是同一数量口径 | L237-L242 | SEMANTIC_EQUIVALENT, GRANULARITY_DIFF | SUPPORTED |
| PK01-CLAIM-0015 | A_BOUNDARY_TIME | W01—W04为历史沟通证据；W04须按消息边界恢复，不能用当前整文件字节冒充PRE-K01快照 | L256-L272 | EXACT_MATCH | SUPPORTED |
| PK01-CLAIM-0016 | D_HISTORICAL_ROLE | 旧131笔人工母表保留历史原文与编号，但已被136版替代，不可作现行正式输入 | L274-L293 | EXACT_MATCH, STATUS_DIMENSION_DIFF_NOT_CONFLICT | SUPPORTED |
| PK01-CLAIM-0017 | B_ASSET_DATA | 136笔人工补全版是K01时点唯一人工内容正式源；当前路径与历史源路径为同SHA不同物理副本 | L295-L322 | SAME_BYTES_DIFFERENT_PATH_ROLE, AUTHORITY_LEVEL_DIFF | SUPPORTED |
| PK01-CLAIM-0018 | H_LINEAGE_VERSION | A136结构审计、131到136映射及126 EXACT、5 STRONG、新增5笔等历史结果成立 | L324-L352 | FAMILY_LEVEL_COVERAGE | SUPPORTED |
| PK01-CLAIM-0019 | H_LINEAGE_VERSION | M4-F2十笔母版的字节身份、M3R到M5血缘、USER确认行为和十笔非136边界成立 | L402-L461 | SAME_BYTES_DIFFERENT_PATH_ROLE, AUTHORSHIP_CORRECTION | SUPPORTED_WITH_AUTHORSHIP_CORRECTION |
| PK01-CLAIM-0020 | C_DATA_FAMILY | P3、148周期、136匹配、最终事实、M0映射及12跟单隔离构成全量交易事实家族 | L463-L493 | FAMILY_LEVEL_COVERAGE | SUPPORTED |
| PK01-CLAIM-0021 | H_LINEAGE_VERSION | A136/阶段06到M0、M1、M2的脚本血缘与后续N1-0实际读取成立 | L495-L529 | FAMILY_LEVEL_COVERAGE, POST_K01_VALIDATION_ONLY | SUPPORTED |
| PK01-CLAIM-0022 | D_HISTORICAL_ROLE | N1-0只证明后续读取，且其旧F2.5.4结构选择不能反向证明后产物正确 | L529-L535 | POST_K01_VALIDATION_ONLY, STATUS_DIMENSION_DIFF_NOT_CONFLICT | SUPPORTED |
| PK01-CLAIM-0023 | C_DATA_FAMILY | A497/M4条件委托的497明细、543汇总/主表、周期关联和覆盖资产及血缘成立 | L537-L589 | FAMILY_LEVEL_COVERAGE | SUPPORTED |
| PK01-CLAIM-0024 | E_USER_AUTHORITY | 条件委托家族只有阶段/产品级USER验收与个体文件流程采用，不能扩大为逐文件签字 | L591-L602 | AUTHORITY_LEVEL_DIFF, EVIDENCE_STRENGTH_DIFF | SUPPORTED_WITH_QUALIFICATION |
| PK01-CLAIM-0025 | C_DATA_FAMILY | 四份资金与绩效文件有后续只读采用证据 | L604-L631 | SAME_BYTES_DIFFERENT_PATH_ROLE, POST_K01_VALIDATION_ONLY | SUPPORTED |
| PK01-CLAIM-0026 | J_UNKNOWN | 08_V2行为特征统计已形成并被K01锁定，但独立下游读取与单文件USER认可无法确认 | L633-L644 | UNRESOLVED | SUPPORTED_AS_UNCERTAINTY |
| PK01-CLAIM-0027 | C_DATA_FAMILY | H0-H五文件身份、H0-E至H0-H血缘、后续只读与仅作MFE/MAE最小增补的边界成立 | L646-L721 | EXACT_MATCH, FAMILY_LEVEL_COVERAGE, POST_K01_VALIDATION_ONLY | SUPPORTED_WITH_QUALIFICATION |
| PK01-CLAIM-0028 | B_ASSET_DATA | R1统一事件底表与仓位完整操作链及其十笔原型血缘成立 | L723-L761 | FAMILY_LEVEL_COVERAGE | SUPPORTED |
| PK01-CLAIM-0029 | C_DATA_FAMILY | 阶段04形成流水、Order、Fill、合约流水、仓位摘要、截图索引与跟单对账 | L763-L773 | FAMILY_LEVEL_COVERAGE | SUPPORTED |
| PK01-CLAIM-0030 | C_DATA_FAMILY | 阶段05形成Order执行汇总、Fill增强与完整仓位周期 | L775-L779 | FAMILY_LEVEL_COVERAGE | SUPPORTED |
| PK01-CLAIM-0031 | C_DATA_FAMILY | 阶段06形成真实周期、136主动匹配与12跟单隔离 | L781-L785 | FAMILY_LEVEL_COVERAGE | SUPPORTED |
| PK01-CLAIM-0032 | C_DATA_FAMILY | 阶段07形成周期资金归属、每日桥接、截图核验与跟单资金结果 | L787-L792 | FAMILY_LEVEL_COVERAGE | SUPPORTED |
| PK01-CLAIM-0033 | D_HISTORICAL_ROLE | 阶段04—07资产是真实生成链资产但K01时点相应旧物理版本已历史化 | L794-L825 | STATUS_DIMENSION_DIFF_NOT_CONFLICT, TEMPORAL_CONTEXT_DIFF | SUPPORTED |
| PK01-CLAIM-0034 | H_LINEAGE_VERSION | 交易所Order/Fill/仓位到阶段04—06、M0—M5、M4-F2的血缘链 | L827-L843 | FAMILY_LEVEL_COVERAGE | SUPPORTED |
| PK01-CLAIM-0035 | H_LINEAGE_VERSION | 旧131加新增5笔到136、A136、M0、P3/P4/M4-F2、M5的人工血缘链 | L845-L857 | FAMILY_LEVEL_COVERAGE | SUPPORTED |
| PK01-CLAIM-0036 | H_LINEAGE_VERSION | 条件截图经A497、497明细、543覆盖、M4/M4-F1到M4-F2的血缘链 | L859-L873 | FAMILY_LEVEL_COVERAGE | SUPPORTED |
| PK01-CLAIM-0037 | H_LINEAGE_VERSION | 账户与资金证据经标准化、归属、桥接、隔离到M5和后续读取的血缘链 | L875-L885 | FAMILY_LEVEL_COVERAGE | SUPPORTED |
| PK01-CLAIM-0038 | H_LINEAGE_VERSION | 正式136周期与行情经H0-E/G/H到后续只读增补的血缘链 | L887-L897 | FAMILY_LEVEL_COVERAGE | SUPPORTED |
| PK01-CLAIM-0039 | I_EXCLUSION_BOUNDARY | 405仅为后台技术粒度，Fill不能代表USER决策或心理 | L899-L901 | SEMANTIC_EQUIVALENT | SUPPORTED |
| PK01-CLAIM-0040 | I_EXCLUSION_BOUNDARY | 旧131笔母表不能作为现行136正式输入但保留追溯价值 | L903-L918 | STATUS_DIMENSION_DIFF_NOT_CONFLICT | SUPPORTED |
| PK01-CLAIM-0041 | I_EXCLUSION_BOUNDARY | 165字节临时伴随文件不是有效OOXML，不纳入 | L920-L926 | EXACT_MATCH | SUPPORTED |
| PK01-CLAIM-0042 | I_EXCLUSION_BOUNDARY | 同SHA的136补充目录交付副本不能成为第二独立正式源 | L928-L939 | SAME_BYTES_DIFFERENT_PATH_ROLE, STATUS_DIMENSION_DIFF_NOT_CONFLICT | SUPPORTED |
| PK01-CLAIM-0043 | I_EXCLUSION_BOUNDARY | 旧F2.5.4 WPS版禁止未来构建并已被M3R到M4-F2替代 | L941-L948 | STATUS_DIMENSION_DIFF_NOT_CONFLICT | SUPPORTED |
| PK01-CLAIM-0044 | I_EXCLUSION_BOUNDARY | 首次M3迁移版为失败或中止输出 | L950-L956 | PREK01_ONLY_VALID_FINDING | SUPPORTED |
| PK01-CLAIM-0045 | I_EXCLUSION_BOUNDARY | N1-B为错误分支，只作反例证据 | L958-L964 | STATUS_DIMENSION_DIFF_NOT_CONFLICT | SUPPORTED |
| PK01-CLAIM-0046 | I_EXCLUSION_BOUNDARY | N1-C为失败或中止的WPS临时测试副本 | L966-L972 | PREK01_ONLY_VALID_FINDING | SUPPORTED |
| PK01-CLAIM-0047 | I_EXCLUSION_BOUNDARY | H0-E/F/G不得绕过H0-H作为后续正式输入，但仍保留历史血缘 | L974-L982 | STATUS_DIMENSION_DIFF_NOT_CONFLICT | SUPPORTED |
| PK01-CLAIM-0048 | I_EXCLUSION_BOUNDARY | K01自身版本锁、总账、报告、Manifest等不属于PRE-K01数据资产 | L984-L996 | OUTSIDE_PREK01_TASK_SCOPE, POST_K01_VALIDATION_ONLY | SUPPORTED |
| PK01-CLAIM-0049 | J_UNKNOWN | W04在PRE-K01时点的完整文件字节快照无法恢复 | L998-L1013 | UNRESOLVED | SUPPORTED_AS_UNCERTAINTY |
| PK01-CLAIM-0050 | J_UNKNOWN | 没有全树重哈希，K01关闭后全工程当前物理字节是否变化无法作全局保证 | L1015-L1035 | UNRESOLVED | SUPPORTED_AS_UNCERTAINTY |
| PK01-CLAIM-0051 | J_UNKNOWN | 不能确认USER逐文件验收每个CSV/XLSX | L1037-L1051 | UNRESOLVED | SUPPORTED_AS_UNCERTAINTY |
| PK01-CLAIM-0052 | J_UNKNOWN | 不能确认USER逐列确认每个字段 | L1037-L1051 | UNRESOLVED | SUPPORTED_AS_UNCERTAINTY |
| PK01-CLAIM-0053 | J_UNKNOWN | 不能确认USER逐项确认每个计算结果 | L1037-L1051 | UNRESOLVED | SUPPORTED_AS_UNCERTAINTY |
| PK01-CLAIM-0054 | J_UNKNOWN | P4当前用户工作簿是否被下游独立读取无法确认 | L1053-L1064 | UNRESOLVED | SUPPORTED_AS_UNCERTAINTY |
| PK01-CLAIM-0055 | J_UNKNOWN | A497部分辅助表是否被下游独立读取无法确认 | L1053-L1064 | UNRESOLVED | SUPPORTED_AS_UNCERTAINTY |
| PK01-CLAIM-0056 | J_UNKNOWN | 08_V2行为特征统计是否被下游独立读取无法确认 | L1053-L1064 | UNRESOLVED | SUPPORTED_AS_UNCERTAINTY |
| PK01-CLAIM-0057 | J_UNKNOWN | 部分异常表和校验载体是否被下游独立读取无法确认 | L1053-L1064 | UNRESOLVED | SUPPORTED_AS_UNCERTAINTY |
| PK01-CLAIM-0058 | J_UNKNOWN | 账户截图日期代表日初还是日末未确认 | L1066-L1075 | UNRESOLVED | SUPPORTED_AS_UNCERTAINTY |
| PK01-CLAIM-0059 | J_UNKNOWN | 条件委托截图覆盖是否绝对完整未确认 | L1066-L1075 | UNRESOLVED | SUPPORTED_AS_UNCERTAINTY |
| PK01-CLAIM-0060 | J_UNKNOWN | 取消或过期的具体原因未确认 | L1066-L1075 | UNRESOLVED | SUPPORTED_AS_UNCERTAINTY |
| PK01-CLAIM-0061 | J_UNKNOWN | OCR或结构化结果不能据此确认USER主观意图 | L1066-L1075 | UNRESOLVED | SUPPORTED_AS_UNCERTAINTY |
| PK01-CLAIM-0062 | G_K01_LOCK | K01锁定336项候选不等于336项全部获得未来构建准入 | L1079-L1092 | EXACT_MATCH, STATUS_DIMENSION_DIFF_NOT_CONFLICT | SUPPORTED |
| PK01-CLAIM-0063 | K_WORKING_HYPOTHESIS | 阶段和数据家族层面获得认可/采用支持，但不能扩大到每文件每字段逐项USER认可 | L1094-L1145 | SEMANTIC_EQUIVALENT, AUTHORITY_LEVEL_DIFF | SUPPORTED_WITH_QUALIFICATION |
| PK01-CLAIM-0064 | C_DATA_FAMILY | 最终直接回答归纳为人工、M4-F2、交易事实、条件、资金、H0-H、历史化底座七类 | L1147-L1272 | FAMILY_LEVEL_COVERAGE, GRANULARITY_DIFF | SUPPORTED |
| PK01-CLAIM-0065 | K_WORKING_HYPOTHESIS | 最终综合结论：核心家族获阶段/产品级认可，单个中间文件部分仅能证明流程读取 | L1274-L1278 | SEMANTIC_EQUIVALENT, AUTHORITY_LEVEL_DIFF | SUPPORTED_WITH_QUALIFICATION |

## 5. 目的1摘要

- PRE-K01具体资产引用：66/66有去向。
- P1ASSET：41/41完成比较。
- 完全一致/等义：8。
- 集合哈希方法差：3；不是业务冲突。
- 同字节不同路径/角色：5。
- 部分覆盖/粒度差：3。
- 家族级覆盖：18。
- PRE-K01任务范围外：4。
- 状态维度差（交叉维度）：4；不是实质冲突。
- PRE-K01真正漏项：0。
- 双向统一真正漏项：0。
- 实质冲突：0。
- 未解决：0。

完整的66项引用和41项资产逐行映射见《目的1资产版本与采用状态比较》。

## 6. 目的2摘要

- 35/35完成比较。
- PRE-K01明确覆盖：16。
- 家族级覆盖：12。
- 部分覆盖：3。
- PRE-K01范围外：4。
- PRE-K01真正in-scope遗漏：0。
- 双向统一真正遗漏：0。
- 角色/时序/作者层级差：3（`P2FACT-006`、`P2FACT-010`、`P2FACT-020`）。
- 实质冲突：0。
- 未解决：0。

完整35项逐行裁定见《目的2历史事实角色与范围比较》。

## 7. 目的3 USER证据摘要

- PRE-K01 USER声明：15/15。
- USER行为与本人逐字措辞均成立：9。
- 确认/发送行为成立但逐字措辞由前序assistant提供：3。
- 行为成立但消息无USER原创文本：2。
- 综合认可层级判断：1，`SUPPORTED_WITH_QUALIFICATION`。
- 阶段级确认均被限制在实际阶段、对象或行为范围内。
- 认可层级扩大：0。
- 作者归属修正：3。
- 未解决：0。

完整15项核验见《目的3 USER证据与认可核验》。

## 8. 排除与未知逐项裁定

### 8.1 明确排除：9/9

| ID | 项目 | 裁定 | 被新证据修正 | 闭合 |
|---|---|---|---|---|
| PK01-EXCLUSION-0001 | 旧131不能作现行136正式输入 | DIRECTLY_STILL_VALID | 否 | 是 |
| PK01-EXCLUSION-0002 | 165字节临时伴随文件无效 | DIRECTLY_STILL_VALID | 否 | 是 |
| PK01-EXCLUSION-0003 | 同SHA交付副本不能成为第二独立正式源 | STATUS_DIMENSION_DIFF_NOT_CONFLICT | 否 | 是 |
| PK01-EXCLUSION-0004 | 旧F2.5.4不得用于未来构建 | STATUS_DIMENSION_DIFF_NOT_CONFLICT | 否 | 是 |
| PK01-EXCLUSION-0005 | 首次M3迁移版为失败输出 | DIRECTLY_STILL_VALID | 否 | 是 |
| PK01-EXCLUSION-0006 | N1-B为错误分支 | STATUS_DIMENSION_DIFF_NOT_CONFLICT | 否 | 是 |
| PK01-EXCLUSION-0007 | N1-C为临时失败副本 | DIRECTLY_STILL_VALID | 否 | 是 |
| PK01-EXCLUSION-0008 | H0-E/F/G不得绕过H0-H正式接口 | STATUS_DIMENSION_DIFF_NOT_CONFLICT | 否 | 是 |
| PK01-EXCLUSION-0009 | K01自身文件不属于PRE-K01数据资产 | DIRECTLY_STILL_VALID | 否 | 是 |

统计：直接仍成立 **5**；状态维度不同但不冲突 **4**；被新证据修正 **0**。

### 8.2 独立未知：13/13

| ID | 项目 | 裁定 | 已解决 | 仍未解决 |
|---|---|---|---|---|
| PK01-UNKNOWN-0010 | W04 PRE-K01整体字节快照 | STILL_UNRESOLVED | 否 | 是 |
| PK01-UNKNOWN-0011 | K01关闭后全工程当前物理字节是否变化的全局保证 | STILL_UNRESOLVED | 否 | 是 |
| PK01-UNKNOWN-0012 | USER是否逐文件验收每个CSV/XLSX | STILL_UNRESOLVED | 否 | 是 |
| PK01-UNKNOWN-0013 | USER是否逐列确认每个字段 | STILL_UNRESOLVED | 否 | 是 |
| PK01-UNKNOWN-0014 | USER是否逐项确认每个计算结果 | STILL_UNRESOLVED | 否 | 是 |
| PK01-UNKNOWN-0015 | P4当前用户工作簿独立下游读取 | STILL_UNRESOLVED | 否 | 是 |
| PK01-UNKNOWN-0016 | A497部分辅助表独立下游读取 | STILL_UNRESOLVED | 否 | 是 |
| PK01-UNKNOWN-0017 | 08_V2行为特征统计独立下游读取 | STILL_UNRESOLVED | 否 | 是 |
| PK01-UNKNOWN-0018 | 部分异常表和校验载体独立下游读取 | STILL_UNRESOLVED | 否 | 是 |
| PK01-UNKNOWN-0019 | 账户截图日期是日初还是日末 | STILL_UNRESOLVED | 否 | 是 |
| PK01-UNKNOWN-0020 | 条件委托截图是否绝对完整覆盖 | STILL_UNRESOLVED | 否 | 是 |
| PK01-UNKNOWN-0021 | 取消或过期的具体原因 | STILL_UNRESOLVED | 否 | 是 |
| PK01-UNKNOWN-0022 | OCR或结构化结果能否解释USER主观意图 | STILL_UNRESOLVED | 否 | 是 |

统计：已解决 **0**；仍未解决 **13**。本任务没有用推断填补这些未知。

## 9. WORKING HYPOTHESIS

状态：**SUPPORTED_WITH_QUALIFICATION**。

支持依据：

- 关键原始资料来源、136人工正式源纠正、M0—M5阶段同意、M0启动、T087检查、两项WPS实测确认及CONFIRM_01—16确认等行为均有证据。
- PRE-K01对核心家族的历史服务关系、实际流程使用、K01锁定候选和当前候选状态进行了分层，而不是直接等同为正式权威。
- P1 41项与P2 35项均无范围内真实遗漏、实质冲突或未决比较项。

限定条件：

- 三个固定确认句的逐字措辞由assistant先提供，USER确认行为仍成立。
- 阶段/产品级确认不能扩大为逐文件、逐字段、逐计算结果签字。
- 13项独立未知仍未知，因此不能宣称全工程逐对象认可或全局物理字节不变。

## 10. 定点回源与异常

仅在已有差异点需要裁决时定点读取；没有第三次扫描。

- W04 Chat：按00A验证路径、文件类型、size=1,210,396、SHA-256=`464e806514fc33ea00924524919f789f3eb3ca291233c03ff0d05a9cd1226436` 后读取授权句上下文。
- K01阶段切换记录：按00A验证 size=11,427、SHA-256=`1fe40eadbf24f614953304feb3fb361bc19791be89e1bee64fa451df99779173` 后读取角色字段。
- 六组同字节不同路径工作簿：均先按00A验证两端路径、size与SHA，再裁定副本角色。
- `SOURCE_EVIDENCE_CHANGED`：0。
- `POTENTIAL_BOTH_BASELINES_MISSED`：0。
- 其他结构阻断：0。

## 11. 04B影响索引（只读）

04B文件保持未修改；本任务不关闭、不解决、不改状态。新证据方向如下：

| 04B编号 | 新证据方向 |
|---|---|
| 5—7 | 给出PRE-K01数据基线与更广双向统一结果的闭合比较；支持区分“数据基线恢复”与“更广历史覆盖”，但不替代用户审查 |
| 8 | 支持“差异定点回源、无条件禁扫不成立”的方法边界；本任务本身未重扫 |
| 9 | 提供已审阅历史中的较早证据方向，但不据此定义PROJECT START |
| 10—11 | 证明候选、历史采用、USER确认、K01锁定、禁止未来使用等状态必须分轴；不生成权威资产清单 |
| 34—47 | P2FACT为生命周期、Order/Fill/周期、主动/跟单隔离、资金链、事实/USER/AI分层、AI层与用户层等问题提供历史证据；不作正式定义或范围冻结 |

04B当前只读身份：334行、23,050字节、SHA-256=`15d1cb192aa9275e5a049f84ba42f8d0ebf8dbd2a3a8fbded4fa993c7cbbf732`。

## 12. 完成标准20项验收

| # | 标准 | 结果 |
|---:|---|---|
| 1 | PRE-K01原始final_answer稳定身份PASS | PASS |
| 2 | 双向统一5项冻结身份PASS | PASS |
| 3 | 当前USER转贴未被当成历史原件 | PASS |
| 4 | 子执行transcript未被扩张为业务基线 | PASS |
| 5 | PRE-K01所有比较单元完整提取并处置 | PASS（65/65） |
| 6 | PRE-K01所有资产引用有去向 | PASS（66/66） |
| 7 | 41/41 P1ASSET完成比较 | PASS |
| 8 | 35/35 P2FACT完成比较 | PASS |
| 9 | 全部PRE-K01 USER证据完成作者/认可层级核验 | PASS（15/15） |
| 10 | 全部PRE-K01明确排除项完成比较 | PASS（9/9） |
| 11 | 全部PRE-K01未知项完成比较 | PASS（13/13） |
| 12 | 没有336 vs 41直接减法 | PASS |
| 13 | 没有把范围差异冒充漏扫 | PASS |
| 14 | 没有把候选状态与历史采用状态混成一条轴 | PASS |
| 15 | 没有把集合hash算法差异冒充业务冲突 | PASS |
| 16 | 没有把post-K01证据倒灌为pre-K01当时事实 | PASS |
| 17 | 所有实质差异已定点裁决或明确UNRESOLVED | PASS |
| 18 | 没有第三次扫描 | PASS |
| 19 | 没有资产晋升 | PASS |
| 20 | 没有进入其他后续任务 | PASS |

## 13. 停止门

以下均未执行：

- 资产晋升；
- 客观交易链正式定义；
- USER筛选；
- user_trade_language语义合并；
- clean production；
- 正式交易分析；
- PRE-K01重做；
- 两遍扫描重做；
- 第三次扫描。

本报告及同目录另外4项成果仅用于比较覆盖和裁定完整性；不建设长期数据库。

## 14. 结束前保护复验

终验阶段再次核对：

- PRE-K01主session：第462行record（去除JSONL行尾换行）SHA-256=`0b24a69e96593a4543cc7b08285e829687a17ac310157d2508c6ccb68030e391`；消息span与1—462行前缀仍分别为 `5899a90090fbdcd64d1d49d17be63ee98f21cf599e75603f9894601cfc62018c`、`c5d98fb2d300ac22adbf90eaa25d4891f4135a5ba20b024610390cc824a5b6e6`。
- PRE-K01子session：1—666行前缀与第666行文本仍分别为 `70dbca15bff0067762fa0b3edc366b06be6e4dd7fd48e6ed0d053e1b416337f9`、`ce088ee59a9212c47b8f75797ffa2b2f747d6b6c4fb42b91c4f5037435dac68c`。
- 定位报告与双向统一5项：全部仍等于合同冻结SHA。
- `00`：SHA-256=`7dffb4fa132241ed1051b20f143c2cf7b68cbde218c5ec004993c0314ed58a17`。
- `00A`：SHA-256=`2e2994df6656c10ea2b0455f81b766e152cd48467243e906610101d1d77c33e1`。
- `01A`：SHA-256=`8bfc313546a1f851b12410dd3294947c11faf896a371b81908c9ca2b530eadf3`。
- `01B`：SHA-256=`1dd0a9dc7215f18caf6ced68091d4bf216ea8b5f69942e84acd27087df5eafd1`。
- `04B`：SHA-256=`15d1cb192aa9275e5a049f84ba42f8d0ebf8dbd2a3a8fbded4fa993c7cbbf732`，未修改。
- 第一遍5项、第二遍5项、差异对账5项：均只读，写入目标审计修改数0。
- `user_trade_language`、K01历史文件、Recovery历史文件、原始扫描根：均无写入；修改数0。
- 本任务的实际写入目标严格只有本目录5项新成果及 `04A_当前任务授权.md` 生命周期文件。

保护复验：**PASS**。

