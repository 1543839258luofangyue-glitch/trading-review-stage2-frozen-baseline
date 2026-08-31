# PRE-K01与双向统一结果｜目的1资产版本与采用状态比较

## 1. 裁定结论

本报告只比较历史 PRE-K01 `final_answer` 与修复后的双向统一结果。它不执行资产晋升，不把“历史采用”“USER 明确认可”“K01 锁定候选”“当前候选状态”压成一条轴，也不以路径相同代替字节身份。

- PRE-K01 具体资产引用：**66/66 已映射，100% 有去向**。
- 双向统一目的1资产：**41/41 已比较**。
- 主分类：完全一致/等义 **8**；集合哈希方法差 **3**；同字节不同路径/角色 **5**；部分覆盖/粒度差 **3**；家族级覆盖 **18**；PRE-K01 任务范围外 **4**。
- P1ASSET 状态维度差异（交叉维度）：**4**；这类差异不等于业务冲突。
- PRE-K01 真正漏项：**0**。
- 双向统一真正漏项：**0**。
- 实质冲突：**0**。
- 未解决：**0**。

## 2. 比较口径：五条独立轴

| 轴 | 本次如何判断 | 禁止的替代判断 |
|---|---|---|
| 字节身份 | 单文件按 SHA-256 与 size；集合先区分集合哈希方法 | 不以文件名或目录名代替字节身份 |
| 路径身份 | 保存所有实际出现路径和副本角色 | 不把同字节副本折叠成“同一条路径” |
| 版本/血缘 | 只使用已冻结记录能够证明的替代、派生、母版、子资产关系 | 不推断未被证据证明的父子关系 |
| 历史采用/USER认可/K01锁定 | 分轴保留“USER 明确认可”“流程实际采用”“K01 锁定候选” | 不把流程使用自动扩大为 USER 正式认可 |
| 当前候选 | 沿用双向统一结果的“候选可采用/相关但仍需核验”等状态 | 本任务不晋升为权威或 production |

## 3. 关键身份与角色裁决

| 对象对 | 字节身份 | 路径/角色裁决 |
|---|---|---|
| 136人工母表：现行正式版副本 ↔ 补充输入交付副本 | SHA-256 `26e1…a687`，113,225 字节，完全相同 | 同字节、不同路径；前者是现行内容源，后者是交付副本 |
| M4-F2：历史工程副本 ↔ 现行正式版副本 | SHA-256 `5d6a…32d4`，275,373 字节，完全相同 | 同字节、不同路径；现行副本承担当前产品母版角色 |
| 148周期主表：历史副本 ↔ 现行正式版副本 | SHA-256 `052d…dae7`，189,292 字节，完全相同 | 同字节、不同路径/阶段角色 |
| 136匹配表：历史副本 ↔ 现行正式版副本 | SHA-256 `c303…049c`，98,701 字节，完全相同 | 同字节、不同路径/阶段角色 |
| 周期盈亏与资金节点：历史副本 ↔ 现行正式版副本 | SHA-256 `f0bf…adc4`，36,638 字节，完全相同 | 同字节、不同路径/阶段角色 |
| 账户权益轨迹：历史副本 ↔ 现行正式版副本 | SHA-256 `4071…8e0`，20,874 字节，完全相同 | 同字节、不同路径/阶段角色 |
| 三个截图/补证集合 | 对象成员由 00A 冻结；两份结果采用的集合摘要方法不同 | `COLLECTION_HASH_METHOD_DIFF`，不是内容冲突 |
| 旧131母表 | 同一物理对象 | PRE-K01 记为历史已被替代；统一清单仍列“相关但仍需核验”，属于状态维度差 |
| F2.5.4 WPS实测通过版 | 物理对象匹配 P1ASSET-031 | 历史通过不等于未来构建可用；PRE-K01 的禁止未来构建状态保留 |
| N1-B工作簿 | 与 P1ASSET-040 部分重叠 | PRE-K01 保存“错误分支”；统一清单保存候选对象，属于粒度与状态维度差 |

所有上述定点原始证据在读取前均以 00A 的路径、类型、size、SHA 完成身份验证；发现 `SOURCE_EVIDENCE_CHANGED=0`。

## 4. PRE-K01具体资产引用：66/66

下表保留每个引用的实际路径、PRE-K01 角色、双向统一映射及其去向。历史 Chat、K01 治理对象和 Recovery 索引属于证据对象，不应强行塞入 41 个业务资产的同义分母。

| PRE-K01引用 | 名称 | 实际路径 | PRE-K01角色 | 映射/去向 | 处置 |
|---|---|---|---|---|---|
| PK01-ASSET-REF-0001 | 历史Chat目录集合 | `/Users/luodaluo/Desktop/30天复盘原始数据/00_项目历史与聊天证据/01_完整聊天记录` | HISTORICAL_EVIDENCE_SET | — | EVIDENCE_ONLY_OUTSIDE_P1 |
| PK01-ASSET-REF-0002 | W01历史Chat | `/Users/luodaluo/Desktop/30天复盘原始数据/00_项目历史与聊天证据/01_完整聊天记录/ChatGPT-W01｜交易心理分析.md` | HISTORICAL_EVIDENCE | — | EVIDENCE_ONLY_OUTSIDE_P1 |
| PK01-ASSET-REF-0003 | W02历史Chat | `/Users/luodaluo/Desktop/30天复盘原始数据/00_项目历史与聊天证据/01_完整聊天记录/ChatGPT-W02｜旧窗口接管与复盘.md` | HISTORICAL_EVIDENCE | — | EVIDENCE_ONLY_OUTSIDE_P1 |
| PK01-ASSET-REF-0004 | W03历史Chat | `/Users/luodaluo/Desktop/30天复盘原始数据/00_项目历史与聊天证据/01_完整聊天记录/ChatGPT-W03｜接管与复盘.md` | HISTORICAL_EVIDENCE | — | EVIDENCE_ONLY_OUTSIDE_P1 |
| PK01-ASSET-REF-0005 | W04历史Chat | `/Users/luodaluo/Desktop/30天复盘原始数据/00_项目历史与聊天证据/01_完整聊天记录/ChatGPT-W04｜救援审计与全项目恢复.md` | HISTORICAL_EVIDENCE | — | EVIDENCE_ONLY_OUTSIDE_P1 |
| PK01-ASSET-REF-0006 | K01阶段目录 | `/Users/luodaluo/Desktop/30天复盘原始数据/01_未来正式构建输入版本锁与旧文件保护基线` | POST_K01_GOVERNANCE_EVIDENCE | — | POST_K01_VALIDATION_ONLY |
| PK01-ASSET-REF-0007 | K01阶段切换记录 | `/Users/luodaluo/Desktop/30天复盘原始数据/01_未来正式构建输入版本锁与旧文件保护基线/00_任务控制/CHANGE-K01-20260803-001_阶段切换与接管材料更新.json` | POST_K01_GOVERNANCE_EVIDENCE | — | POST_K01_VALIDATION_ONLY |
| PK01-ASSET-REF-0008 | K01执行指令 | `/Users/luodaluo/Desktop/30天复盘原始数据/01_未来正式构建输入版本锁与旧文件保护基线/00_任务控制/K01_Codex完整执行指令_v1.md` | POST_K01_GOVERNANCE_EVIDENCE | — | POST_K01_VALIDATION_ONLY |
| PK01-ASSET-REF-0009 | K01输入版本锁 | `/Users/luodaluo/Desktop/30天复盘原始数据/01_未来正式构建输入版本锁与旧文件保护基线/00_任务控制/K01_INPUT_VERSION_LOCK.json` | POST_K01_GOVERNANCE_EVIDENCE | — | POST_K01_VALIDATION_ONLY |
| PK01-ASSET-REF-0010 | K01旧文件保护基线 | `/Users/luodaluo/Desktop/30天复盘原始数据/01_未来正式构建输入版本锁与旧文件保护基线/00_任务控制/K01_旧文件保护基线.csv` | POST_K01_GOVERNANCE_EVIDENCE | — | POST_K01_VALIDATION_ONLY |
| PK01-ASSET-REF-0011 | K01候选输入总账 | `/Users/luodaluo/Desktop/30天复盘原始数据/01_未来正式构建输入版本锁与旧文件保护基线/01_候选输入总账/K01_未来正式构建候选输入总账.csv` | POST_K01_GOVERNANCE_EVIDENCE | — | POST_K01_VALIDATION_ONLY |
| PK01-ASSET-REF-0012 | K01完成报告 | `/Users/luodaluo/Desktop/30天复盘原始数据/01_未来正式构建输入版本锁与旧文件保护基线/03_验收与封存/K01_完成报告.md` | POST_K01_GOVERNANCE_EVIDENCE | — | POST_K01_VALIDATION_ONLY |
| PK01-ASSET-REF-0013 | K01 Manifest | `/Users/luodaluo/Desktop/30天复盘原始数据/01_未来正式构建输入版本锁与旧文件保护基线/K01_MANIFEST.json` | POST_K01_GOVERNANCE_EVIDENCE | — | POST_K01_VALIDATION_ONLY |
| PK01-ASSET-REF-0014 | 旧131笔人工复盘母表 | `/Users/luodaluo/Desktop/30天复盘原始数据/30天复盘(9).xlsx` | HISTORICAL_SUPERSEDED | P1ASSET-009 | EXACT_MATCH |
| PK01-ASSET-REF-0015 | Binance账户交易流水 | `/Users/luodaluo/Desktop/30天复盘原始数据/Binance-交易流水-a.xlsx` | RAW_SOURCE | P1ASSET-001 | EXACT_MATCH |
| PK01-ASSET-REF-0016 | Binance合约成交历史 | `/Users/luodaluo/Desktop/30天复盘原始数据/Binance-合约交易历史记录-a.xlsx` | RAW_FILL_SOURCE | P1ASSET-003 | EXACT_MATCH |
| PK01-ASSET-REF-0017 | Binance合约资金流水 | `/Users/luodaluo/Desktop/30天复盘原始数据/Binance-合约交易流水-a.xlsx` | RAW_FUND_SOURCE | P1ASSET-004 | EXACT_MATCH |
| PK01-ASSET-REF-0018 | Binance合约仓位历史 | `/Users/luodaluo/Desktop/30天复盘原始数据/Binance-合约仓位历史记录-a.xlsx` | RAW_POSITION_SUMMARY | P1ASSET-005 | EXACT_MATCH |
| PK01-ASSET-REF-0019 | Binance合约订单历史 | `/Users/luodaluo/Desktop/30天复盘原始数据/Binance-合约订单历史记录-a.xlsx` | RAW_ORDER_SOURCE | P1ASSET-002 | EXACT_MATCH |
| PK01-ASSET-REF-0020 | H0-H阶段客观指标冻结CSV | `/Users/luodaluo/Desktop/30天复盘原始数据/H0_历史行情与MFE_MAE技术底座/H0-H_全量终验与客观行情指标冻结/02_阶段终验与冻结/H0-H_STAGE_OBJECTIVE_METRICS_FROZEN.csv` | FROZEN_INTERFACE_CHILD | P1ASSET-037 | FAMILY_LEVEL_COVERAGE |
| PK01-ASSET-REF-0021 | H0-H周期客观指标冻结CSV | `/Users/luodaluo/Desktop/30天复盘原始数据/H0_历史行情与MFE_MAE技术底座/H0-H_全量终验与客观行情指标冻结/03_周期终验与冻结/H0-H_CYCLE_OBJECTIVE_METRICS_FROZEN.csv` | FROZEN_INTERFACE | P1ASSET-017 | EXACT_MATCH |
| PK01-ASSET-REF-0022 | H0-H精度与发布状态CSV | `/Users/luodaluo/Desktop/30天复盘原始数据/H0_历史行情与MFE_MAE技术底座/H0-H_全量终验与客观行情指标冻结/04_精度发布状态与区间语义/H0-H_PRECISION_AND_PUBLISH_STATUS_FROZEN.csv` | FROZEN_INTERFACE_CHILD | P1ASSET-037 | FAMILY_LEVEL_COVERAGE |
| PK01-ASSET-REF-0023 | H0-H接口Schema | `/Users/luodaluo/Desktop/30天复盘原始数据/H0_历史行情与MFE_MAE技术底座/H0-H_全量终验与客观行情指标冻结/06_O线N线接口/H0-H_OBJECTIVE_INTERFACE_SCHEMA.json` | FROZEN_INTERFACE_CHILD | P1ASSET-037 | FAMILY_LEVEL_COVERAGE |
| PK01-ASSET-REF-0024 | H0-H只读合同 | `/Users/luodaluo/Desktop/30天复盘原始数据/H0_历史行情与MFE_MAE技术底座/H0-H_全量终验与客观行情指标冻结/06_O线N线接口/H0-H_O_N_OBJECTIVE_READ_CONTRACT.json` | FROZEN_INTERFACE_CHILD | P1ASSET-037 | FAMILY_LEVEL_COVERAGE |
| PK01-ASSET-REF-0025 | N1-0输入版本锁 | `/Users/luodaluo/Desktop/30天复盘原始数据/N线_136笔完整增强复盘与交易系统/N1_136笔完整增强版构建/N1-0_正式输入锁定与映射准备/01_输入清单与SHA/N1-0_INPUT_VERSION_LOCK.json` | POST_K01_READ_EVIDENCE | — | POST_K01_VALIDATION_ONLY |
| PK01-ASSET-REF-0026 | N1-0输入锁报告 | `/Users/luodaluo/Desktop/30天复盘原始数据/N线_136笔完整增强复盘与交易系统/N1_136笔完整增强版构建/N1-0_正式输入锁定与映射准备/N1-0_开始与正式输入锁定报告.md` | POST_K01_READ_EVIDENCE | — | POST_K01_VALIDATION_ONLY |
| PK01-ASSET-REF-0027 | N1-B错误分支工作簿 | `/Users/luodaluo/Desktop/30天复盘原始数据/N线_136笔完整增强复盘与交易系统/N1_136笔完整增强版构建/N1-B_136笔全中文用户工作版构建/02_工作簿/30天逐笔人工复盘增强版_136笔全中文用户工作版_N1-B.xlsx` | ERROR_BRANCH | P1ASSET-040 | PARTIAL_OVERLAP_STATUS_DIMENSION_DIFF |
| PK01-ASSET-REF-0028 | N1-C WPS临时测试副本 | `/Users/luodaluo/Desktop/30天复盘原始数据/N线_136笔完整增强复盘与交易系统/N1_136笔完整增强版构建/N1-C_136笔全中文用户工作版验收/N1-C_WPS临时测试副本.xlsx` | FAILED_OR_ABORTED_OUTPUT | — | PREK01_ONLY_VALID_EXCLUSION |
| PK01-ASSET-REF-0029 | F2.5.4 WPS实测通过版 | `/Users/luodaluo/Desktop/30天复盘原始数据/人工复盘增强版_修正工程/R1_10笔成品原型/30天逐笔人工复盘增强版_10笔成品原型_F2.5.4_WPS实测通过版.xlsx` | PROHIBITED_FOR_FUTURE_BUILD | P1ASSET-031 | EXACT_BYTES_STATUS_DIMENSION_DIFF |
| PK01-ASSET-REF-0030 | R1统一事件底表 | `/Users/luodaluo/Desktop/30天复盘原始数据/人工复盘增强版_修正工程/R1_10笔成品原型/技术中间结果/01_统一事件底表.csv` | VALID_INTERMEDIATE | P1ASSET-030 | FAMILY_LEVEL_COVERAGE |
| PK01-ASSET-REF-0031 | R1仓位完整操作链 | `/Users/luodaluo/Desktop/30天复盘原始数据/人工复盘增强版_修正工程/R1_10笔成品原型/技术中间结果/02_仓位完整操作链.csv` | VALID_INTERMEDIATE | P1ASSET-030 | FAMILY_LEVEL_COVERAGE |
| PK01-ASSET-REF-0032 | 首次M3迁移失败版 | `/Users/luodaluo/Desktop/30天复盘原始数据/人工复盘增强版_修正工程_V2_136笔主动交易/05_最终交付/30天逐笔人工复盘增强版_10笔成品原型_F2.5.4_M3迁移版.xlsx` | FAILED_OR_ABORTED_OUTPUT | — | PREK01_ONLY_VALID_EXCLUSION |
| PK01-ASSET-REF-0033 | 救援审计血缘CSV | `/Users/luodaluo/Desktop/30天复盘原始数据/救援审计_全项目工程谱系与数据血缘恢复/03_数据血缘矩阵/救援审计_原始证据到正式派生结果血缘.csv` | SECONDARY_LINEAGE_EVIDENCE | P1ASSET-038 | FAMILY_LEVEL_EVIDENCE |
| PK01-ASSET-REF-0034 | 救援审计关系报告 | `/Users/luodaluo/Desktop/30天复盘原始数据/救援审计_全项目工程谱系与数据血缘恢复/07_报告/救援审计_全项目工程谱系与产品服务关系报告.md` | SECONDARY_AUDIT_EVIDENCE | P1ASSET-038 | FAMILY_LEVEL_EVIDENCE |
| PK01-ASSET-REF-0035 | 现行136人工母表物理副本 | `/Users/luodaluo/Desktop/30天复盘原始数据/现行正式版_V2.1_136笔主动交易_A497生命周期/01_人工复盘母表/30天复盘_136笔主动交易人工补全版.xlsx` | UNIQUE_CURRENT_MANUAL_CONTENT_SOURCE | P1ASSET-010 | SAME_BYTES_DIFFERENT_PATH_ROLE |
| PK01-ASSET-REF-0036 | 现行P3全量中文交易链 | `/Users/luodaluo/Desktop/30天复盘原始数据/现行正式版_V2.1_136笔主动交易_A497生命周期/02_全量中文交易链/P3_V2.1-F1_148个真实仓位全量中文交易链_A497字段修正版.xlsx` | CURRENT_FACT_LAYER_VERSION | P1ASSET-015, P1ASSET-029, P1ASSET-033 | VERSION_AND_FAMILY_COVERAGE |
| PK01-ASSET-REF-0037 | 现行M4-F2物理副本 | `/Users/luodaluo/Desktop/30天复盘原始数据/现行正式版_V2.1_136笔主动交易_A497生命周期/03_十笔增强原型/30天逐笔人工复盘增强版_10笔成品原型_F2.5.4_M4-F2仓位链连续性修正版.xlsx` | UNIQUE_CURRENT_PRODUCT_MASTER | P1ASSET-016, P1ASSET-034 | SAME_BYTES_DIFFERENT_PATH_ROLE |
| PK01-ASSET-REF-0038 | 现行148周期主表物理副本 | `/Users/luodaluo/Desktop/30天复盘原始数据/现行正式版_V2.1_136笔主动交易_A497生命周期/04_统一编号与事实台账/05_V2_148个真实仓位周期主表.xlsx` | CURRENT_FACT_LAYER | P1ASSET-011 | SAME_BYTES_DIFFERENT_PATH_ROLE |
| PK01-ASSET-REF-0039 | 现行136匹配表物理副本 | `/Users/luodaluo/Desktop/30天复盘原始数据/现行正式版_V2.1_136笔主动交易_A497生命周期/04_统一编号与事实台账/06_V2_136笔人工复盘与周期匹配表.xlsx` | CURRENT_FACT_LAYER | P1ASSET-013 | SAME_BYTES_DIFFERENT_PATH_ROLE |
| PK01-ASSET-REF-0040 | 现行148周期最终事实台账 | `/Users/luodaluo/Desktop/30天复盘原始数据/现行正式版_V2.1_136笔主动交易_A497生命周期/04_统一编号与事实台账/09_V2_148周期最终事实台账.xlsx` | CURRENT_FACT_LAYER | P1ASSET-021, P1ASSET-028 | FAMILY_LEVEL_COVERAGE |
| PK01-ASSET-REF-0041 | 现行M0 148周期映射 | `/Users/luodaluo/Desktop/30天复盘原始数据/现行正式版_V2.1_136笔主动交易_A497生命周期/04_统一编号与事实台账/M0_02_148周期统一编号映射.xlsx` | CURRENT_MAPPING | P1ASSET-027 | FAMILY_LEVEL_COVERAGE |
| PK01-ASSET-REF-0042 | 现行M0 131到136映射 | `/Users/luodaluo/Desktop/30天复盘原始数据/现行正式版_V2.1_136笔主动交易_A497生命周期/04_统一编号与事实台账/M0_03_旧131到新136编号映射冻结.xlsx` | CURRENT_MAPPING | P1ASSET-027 | FAMILY_LEVEL_COVERAGE |
| PK01-ASSET-REF-0043 | 现行M0 12跟单隔离 | `/Users/luodaluo/Desktop/30天复盘原始数据/现行正式版_V2.1_136笔主动交易_A497生命周期/04_统一编号与事实台账/M0_05_自动跟单12周期隔离冻结.xlsx` | CURRENT_MAPPING | P1ASSET-027 | FAMILY_LEVEL_COVERAGE |
| PK01-ASSET-REF-0044 | 现行A497 543一对一匹配 | `/Users/luodaluo/Desktop/30天复盘原始数据/现行正式版_V2.1_136笔主动交易_A497生命周期/05_条件委托生命周期/A497_03_原543条条件委托一对一匹配表.xlsx` | CURRENT_CONDITION_ASSET | P1ASSET-026, P1ASSET-033 | FAMILY_LEVEL_COVERAGE |
| PK01-ASSET-REF-0045 | 现行M4-F1 543生命周期主表 | `/Users/luodaluo/Desktop/30天复盘原始数据/现行正式版_V2.1_136笔主动交易_A497生命周期/05_条件委托生命周期/M4-F1_543条条件委托生命周期主表.xlsx` | CURRENT_CONDITION_ASSET | P1ASSET-033 | FAMILY_LEVEL_COVERAGE |
| PK01-ASSET-REF-0046 | 现行M4-F1条件与周期关联 | `/Users/luodaluo/Desktop/30天复盘原始数据/现行正式版_V2.1_136笔主动交易_A497生命周期/05_条件委托生命周期/M4-F1_条件委托与148周期关联表.xlsx` | CURRENT_CONDITION_ASSET | P1ASSET-033 | FAMILY_LEVEL_COVERAGE |
| PK01-ASSET-REF-0047 | 现行M4 136周期覆盖 | `/Users/luodaluo/Desktop/30天复盘原始数据/现行正式版_V2.1_136笔主动交易_A497生命周期/05_条件委托生命周期/M4_05_136主动周期条件委托覆盖分析.xlsx` | CURRENT_CONDITION_ASSET | P1ASSET-033 | FAMILY_LEVEL_COVERAGE |
| PK01-ASSET-REF-0048 | 现行主动与跟单资金拆分 | `/Users/luodaluo/Desktop/30天复盘原始数据/现行正式版_V2.1_136笔主动交易_A497生命周期/06_资金与绩效/07_V2_个人主动与自动跟单资金影响拆分.xlsx` | CURRENT_FUND_ASSET | P1ASSET-024, P1ASSET-028, P1ASSET-035 | FAMILY_LEVEL_COVERAGE |
| PK01-ASSET-REF-0049 | 现行周期盈亏与资金节点物理副本 | `/Users/luodaluo/Desktop/30天复盘原始数据/现行正式版_V2.1_136笔主动交易_A497生命周期/06_资金与绩效/07_V2_周期盈亏与资金节点表.xlsx` | CURRENT_FUND_ASSET | P1ASSET-014 | SAME_BYTES_DIFFERENT_PATH_ROLE |
| PK01-ASSET-REF-0050 | 现行账户权益轨迹物理副本 | `/Users/luodaluo/Desktop/30天复盘原始数据/现行正式版_V2.1_136笔主动交易_A497生命周期/06_资金与绩效/07_V2_账户权益轨迹.xlsx` | CURRENT_FUND_ASSET | P1ASSET-014 | SAME_BYTES_DIFFERENT_PATH_ROLE |
| PK01-ASSET-REF-0051 | 现行136主动绩效统计 | `/Users/luodaluo/Desktop/30天复盘原始数据/现行正式版_V2.1_136笔主动交易_A497生命周期/06_资金与绩效/08_V2_136笔个人主动绩效统计.xlsx` | CURRENT_PERFORMANCE_ASSET | P1ASSET-024, P1ASSET-028, P1ASSET-035 | FAMILY_LEVEL_COVERAGE |
| PK01-ASSET-REF-0052 | 现行行为特征统计 | `/Users/luodaluo/Desktop/30天复盘原始数据/现行正式版_V2.1_136笔主动交易_A497生命周期/06_资金与绩效/08_V2_行为特征统计.xlsx` | LOCKED_CANDIDATE_USE_UNKNOWN | P1ASSET-035 | FAMILY_LEVEL_COVERAGE_UNRESOLVED_USAGE |
| PK01-ASSET-REF-0053 | M4-F2完成报告 | `/Users/luodaluo/Desktop/30天复盘原始数据/现行正式版_V2.1_136笔主动交易_A497生命周期/07_证据索引与审计/M4-F2_完成报告.md` | SECONDARY_AUDIT_EVIDENCE | P1ASSET-034 | FAMILY_LEVEL_EVIDENCE |
| PK01-ASSET-REF-0054 | M5最终审计报告 | `/Users/luodaluo/Desktop/30天复盘原始数据/现行正式版_V2.1_136笔主动交易_A497生命周期/07_证据索引与审计/M5_最终审计报告.md` | SECONDARY_AUDIT_EVIDENCE | P1ASSET-035 | FAMILY_LEVEL_EVIDENCE |
| PK01-ASSET-REF-0055 | A136结构审计工作簿 | `/Users/luodaluo/Desktop/30天复盘原始数据/用户版_中文交易链路/技术支持文件/A136_136笔编号迁移只读预案与用户确认/A136_02_136笔人工复盘文件识别与结构审计.xlsx` | A136_CHILD_ASSET | P1ASSET-025 | FAMILY_LEVEL_COVERAGE |
| PK01-ASSET-REF-0056 | A136 131到136映射候选 | `/Users/luodaluo/Desktop/30天复盘原始数据/用户版_中文交易链路/技术支持文件/A136_136笔编号迁移只读预案与用户确认/A136_03_旧131笔到新136笔映射候选.xlsx` | A136_CHILD_ASSET | P1ASSET-025 | FAMILY_LEVEL_COVERAGE |
| PK01-ASSET-REF-0057 | A136完成报告 | `/Users/luodaluo/Desktop/30天复盘原始数据/用户版_中文交易链路/技术支持文件/A136_136笔编号迁移只读预案与用户确认/A136_完成报告.md` | SECONDARY_AUDIT_EVIDENCE | P1ASSET-025 | FAMILY_LEVEL_EVIDENCE |
| PK01-ASSET-REF-0058 | A497 497张结构化明细 | `/Users/luodaluo/Desktop/30天复盘原始数据/用户版_中文交易链路/技术支持文件/A497_安卓端条件委托生命周期证据验收/A497_02_安卓端497张生命周期结构化明细.xlsx` | A497_CHILD_ASSET | P1ASSET-026 | FAMILY_LEVEL_COVERAGE |
| PK01-ASSET-REF-0059 | A497 543覆盖汇总 | `/Users/luodaluo/Desktop/30天复盘原始数据/用户版_中文交易链路/技术支持文件/A497_安卓端条件委托生命周期证据验收/A497_06_全543条生命周期覆盖汇总.xlsx` | A497_CHILD_ASSET | P1ASSET-026 | FAMILY_LEVEL_COVERAGE |
| PK01-ASSET-REF-0060 | 条件委托截图集合 | `/Users/luodaluo/Desktop/30天复盘原始数据/补充证据_历史委托条件委托截图` | RAW_SCREENSHOT_SET | P1ASSET-007 | COLLECTION_HASH_METHOD_DIFF |
| PK01-ASSET-REF-0061 | 跟单与仓位补证集合 | `/Users/luodaluo/Desktop/30天复盘原始数据/补充证据_币安跟单与仓位记录` | RAW_EVIDENCE_SET | P1ASSET-008 | COLLECTION_HASH_METHOD_DIFF |
| PK01-ASSET-REF-0062 | 165字节临时伴随文件 | `/Users/luodaluo/Desktop/30天复盘原始数据/补充输入_136笔人工复盘/.~30天复盘_136笔主动交易人工补全版.xlsx` | INVALID_TEMPORARY | — | PREK01_ONLY_VALID_EXCLUSION |
| PK01-ASSET-REF-0063 | 136人工母表交付副本 | `/Users/luodaluo/Desktop/30天复盘原始数据/补充输入_136笔人工复盘/30天复盘_136笔主动交易人工补全版.xlsx` | IDENTICAL_DELIVERY_COPY | P1ASSET-010 | EXACT_BYTES_STATUS_DIMENSION_DIFF |
| PK01-ASSET-REF-0064 | 账户结算原始截图集合 | `/Users/luodaluo/Desktop/30天复盘原始数据/账户结算单_原始截图` | RAW_SCREENSHOT_SET | P1ASSET-006 | COLLECTION_HASH_METHOD_DIFF |
| PK01-ASSET-REF-0065 | Recovery P2消息索引 | `/Users/luodaluo/Desktop/30天复盘原始数据_Recovery_v19/IH-P2_Seven_Chat_Structural_Parser_Hardening/IH-P2_MESSAGES.jsonl` | RECOVERY_EVIDENCE_ONLY | — | EVIDENCE_ONLY_OUTSIDE_P1 |
| PK01-ASSET-REF-0066 | Recovery P3 USER片段索引 | `/Users/luodaluo/Desktop/30天复盘原始数据_Recovery_v19/IH-P3_Origin_Echo_Lineage_Artifact/results/IH-P3_USER_SEGMENTS.jsonl` | RECOVERY_EVIDENCE_ONLY | — | EVIDENCE_ONLY_OUTSIDE_P1 |

## 4A. 66项引用的字节/集合、历史阶段与三条状态轴

以下逐项登记满足“字节/集合身份、历史阶段、USER认可、流程采用、K01锁定”分轴要求。若 PRE-K01 final 没有逐字给出某对象 SHA，本表明确写为“未给出”，不会用当前文件或推断补值。集合摘要与单文件 SHA 不混用。

| 引用 | 字节/集合身份（PRE-K01记录口径） | 历史阶段 | USER认可层级 | 流程采用层级 | K01锁定/记录状态 | 原结果位置 |
|---|---|---|---|---|---|---|
| PK01-ASSET-REF-0001 | 目录集合；W01/W02/W03及W04的PRE-K01消息边界；当前W04整体字节不充当PRE-K01快照 | PRE-K01历史Chat证据 | K01阶段授权/治理行为；非PRE-K01数据资产认可 | 治理/来源证据，不计业务流程采用 | 非K01数据资产；历史Chat边界证据 | L256-L260 |
| PK01-ASSET-REF-0002 | PRE-K01 final仅记录路径/角色，未逐字给出本对象SHA；不得推断 | PRE-K01历史Chat证据 | K01阶段授权/治理行为；非PRE-K01数据资产认可 | 治理/来源证据，不计业务流程采用 | 非K01数据资产；历史Chat边界证据 | multiple |
| PK01-ASSET-REF-0003 | PRE-K01 final仅记录路径/角色，未逐字给出本对象SHA；不得推断 | PRE-K01历史Chat证据 | K01阶段授权/治理行为；非PRE-K01数据资产认可 | 治理/来源证据，不计业务流程采用 | 非K01数据资产；历史Chat边界证据 | multiple |
| PK01-ASSET-REF-0004 | PRE-K01 final仅记录路径/角色，未逐字给出本对象SHA；不得推断 | PRE-K01历史Chat证据 | K01阶段授权/治理行为；非PRE-K01数据资产认可 | 治理/来源证据，不计业务流程采用 | 非K01数据资产；历史Chat边界证据 | multiple |
| PK01-ASSET-REF-0005 | PRE-K01 final仅记录路径/角色，未逐字给出本对象SHA；不得推断 | PRE-K01历史Chat证据 | K01阶段授权/治理行为；非PRE-K01数据资产认可 | 治理/来源证据，不计业务流程采用 | 非K01数据资产；历史Chat边界证据 | multiple |
| PK01-ASSET-REF-0006 | K01治理目录；子对象另列；不作为PRE-K01数据资产 | post-K01治理证据 | K01阶段授权/治理行为；非PRE-K01数据资产认可 | 治理/来源证据，不计业务流程采用 | K01治理对象本身；非PRE-K01数据资产 | L133-L162 |
| PK01-ASSET-REF-0007 | PRE-K01 final仅记录路径/角色，未逐字给出本对象SHA；不得推断 | post-K01治理证据 | K01阶段授权/治理行为；非PRE-K01数据资产认可 | 治理/来源证据，不计业务流程采用 | K01治理对象本身；非PRE-K01数据资产 | L151-L158 |
| PK01-ASSET-REF-0008 | PRE-K01 final仅记录路径/角色，未逐字给出本对象SHA；不得推断 | post-K01治理证据 | K01阶段授权/治理行为；非PRE-K01数据资产认可 | 治理/来源证据，不计业务流程采用 | K01治理对象本身；非PRE-K01数据资产 | multiple |
| PK01-ASSET-REF-0009 | PRE-K01 final仅记录路径/角色，未逐字给出本对象SHA；不得推断 | post-K01治理证据 | K01阶段授权/治理行为；非PRE-K01数据资产认可 | 治理/来源证据，不计业务流程采用 | K01治理对象本身；非PRE-K01数据资产 | multiple |
| PK01-ASSET-REF-0010 | PRE-K01 final仅记录路径/角色，未逐字给出本对象SHA；不得推断 | post-K01治理证据 | K01阶段授权/治理行为；非PRE-K01数据资产认可 | 治理/来源证据，不计业务流程采用 | K01治理对象本身；非PRE-K01数据资产 | L139-L149 |
| PK01-ASSET-REF-0011 | PRE-K01 final仅记录路径/角色，未逐字给出本对象SHA；不得推断 | post-K01治理证据 | K01阶段授权/治理行为；非PRE-K01数据资产认可 | 治理/来源证据，不计业务流程采用 | K01治理对象本身；非PRE-K01数据资产 | multiple |
| PK01-ASSET-REF-0012 | PRE-K01 final仅记录路径/角色，未逐字给出本对象SHA；不得推断 | post-K01治理证据 | K01阶段授权/治理行为；非PRE-K01数据资产认可 | 治理/来源证据，不计业务流程采用 | K01治理对象本身；非PRE-K01数据资产 | L1027-L1035,L1079-L1092 |
| PK01-ASSET-REF-0013 | PRE-K01 final仅记录路径/角色，未逐字给出本对象SHA；不得推断 | post-K01治理证据 | K01阶段授权/治理行为；非PRE-K01数据资产认可 | 治理/来源证据，不计业务流程采用 | K01治理对象本身；非PRE-K01数据资产 | L151-L162 |
| PK01-ASSET-REF-0014 | SHA-256=5ecd6b57c95f9007077a375609d503330d73a5b5d571f8e763b9df33ae8098f4 | PRE-K01已存在资产/历史派生 | USER明确声明被136版替代 | 历史使用后被替代 | K01记录为历史/错误/失败/禁止状态 | L278-L293,L907-L918 |
| PK01-ASSET-REF-0015 | SHA-256=ba4f0c754bdda9f4b3dbb162e6df678d7d546fbf4151c02158591c536fe4d997 | PRE-K01已存在资产/历史派生 | 未由同一“四文件”USER原句覆盖；K01锁定原始源 | 原始输入/补证家族被流程使用 | K01候选总账/版本锁所记录；本任务不晋升 | L182-L185 |
| PK01-ASSET-REF-0016 | SHA-256=cbdb83ea624606cd950fb01736ddbc3f92555978b412a0efd5709bb5dcae302a | PRE-K01已存在资产/历史派生 | USER四文件来源声明＋Fill后台数据声明 | 原始输入/补证家族被流程使用 | K01候选总账/版本锁所记录；本任务不晋升 | L192-L195 |
| PK01-ASSET-REF-0017 | SHA-256=dcee862006858ced9f32db8b3d985f12eaf8428ace49fdff41d5c15aa8648b7e | PRE-K01已存在资产/历史派生 | USER四文件原始来源家族声明 | 原始输入/补证家族被流程使用 | K01候选总账/版本锁所记录；本任务不晋升 | L197-L200 |
| PK01-ASSET-REF-0018 | SHA-256=b7402b01d8f23633006e542d8201f55201487b352aac8d6eac12a8cb7860719a | PRE-K01已存在资产/历史派生 | USER四文件原始来源家族声明 | 原始输入/补证家族被流程使用 | K01候选总账/版本锁所记录；本任务不晋升 | L202-L205 |
| PK01-ASSET-REF-0019 | SHA-256=e53c7aff833c374a059c3de6552ec3961ac45a343619bf9da75145fee3f391fa | PRE-K01已存在资产/历史派生 | USER四文件原始来源家族声明 | 原始输入/补证家族被流程使用 | K01候选总账/版本锁所记录；本任务不晋升 | L187-L190 |
| PK01-ASSET-REF-0020 | SHA-256=c3ecd12b6dacd7a15af27f889f63cf48506f176b4de46cae068d267bc490f388 | PRE-K01已存在资产/历史派生 | USER同意H0-H家族推荐；非逐文件原创说明 | PRE-K01流程形成、读取或锁定证据成立；具体层级见原结果 | K01候选总账/版本锁所记录；本任务不晋升 | L650-L652 |
| PK01-ASSET-REF-0021 | SHA-256=09388081fc0faf30cff9545049bb86e3ec89b49965ad648c0d94342dbe393651 | PRE-K01已存在资产/历史派生 | USER同意H0-H家族推荐；非逐文件原创说明 | PRE-K01流程形成、读取或锁定证据成立；具体层级见原结果 | K01候选总账/版本锁所记录；本任务不晋升 | L654-L656 |
| PK01-ASSET-REF-0022 | SHA-256=3d73953c2cc3687f023e5e62126c37ae02f39efd475c26b0aebef42cfd2ab6c7 | PRE-K01已存在资产/历史派生 | USER同意H0-H家族推荐；非逐文件原创说明 | PRE-K01流程形成、读取或锁定证据成立；具体层级见原结果 | K01候选总账/版本锁所记录；本任务不晋升 | L658-L660 |
| PK01-ASSET-REF-0023 | SHA-256=09b07dd418deb7fc28aa1882e10f89b461978f0bdd2da35e9e46c3e232a34465 | PRE-K01已存在资产/历史派生 | USER同意H0-H家族推荐；非逐文件原创说明 | PRE-K01流程形成、读取或锁定证据成立；具体层级见原结果 | K01候选总账/版本锁所记录；本任务不晋升 | L662-L664 |
| PK01-ASSET-REF-0024 | SHA-256=1a4cbf1ace5e9ddd47d7c93d49d7d757aaeb22b165dbd5cdf7237c9f56f7af7a | PRE-K01已存在资产/历史派生 | USER同意H0-H家族推荐；非逐文件原创说明 | PRE-K01流程形成、读取或锁定证据成立；具体层级见原结果 | K01候选总账/版本锁所记录；本任务不晋升 | L666-L668 |
| PK01-ASSET-REF-0025 | PRE-K01 final仅记录路径/角色，未逐字给出本对象SHA；不得推断 | post-K01状态/验证证据 | 未证明单文件级USER正式认可 | post-K01状态证据；不得倒灌 | post-K01验证，不作为PRE-K01锁状态 | multiple |
| PK01-ASSET-REF-0026 | PRE-K01 final仅记录路径/角色，未逐字给出本对象SHA；不得推断 | post-K01状态/验证证据 | 未证明单文件级USER正式认可 | post-K01状态证据；不得倒灌 | post-K01验证，不作为PRE-K01锁状态 | L676-L682 |
| PK01-ASSET-REF-0027 | SHA-256=5f6183f6c67acb39146455a903f849d743f121b4b4c66692473fd5b43bc57313 | post-K01状态/验证证据 | 未证明单文件级USER正式认可 | post-K01状态证据；不得倒灌 | post-K01验证，不作为PRE-K01锁状态 | L958-L964 |
| PK01-ASSET-REF-0028 | PRE-K01 final仅记录路径/角色，未逐字给出本对象SHA；不得推断 | post-K01状态/验证证据 | 未证明单文件级USER正式认可 | post-K01状态证据；不得倒灌 | post-K01验证，不作为PRE-K01锁状态 | L966-L972 |
| PK01-ASSET-REF-0029 | SHA-256=a1e73e8aeca77c0db9670630a0cb3aedeea430dbe88f225f88fda4dc3e72750f | PRE-K01已存在资产/历史派生 | 历史WPS通过不等于未来构建批准 | 历史过程存在；未来使用被禁止/错误分支 | K01记录为历史/错误/失败/禁止状态 | L941-L948 |
| PK01-ASSET-REF-0030 | SHA-256=548b5ee96b26ee4b9bcbc9af6b4f9e844a581391770bda17c46aaa7d6c16b39c | PRE-K01已存在资产/历史派生 | 未证明单文件级USER正式认可 | PRE-K01流程形成、读取或锁定证据成立；具体层级见原结果 | K01候选总账/版本锁所记录；本任务不晋升 | L727-L730 |
| PK01-ASSET-REF-0031 | SHA-256=2977e338b42ccb1db1211d682a2574d24c4dd702c20b0056325e69ca3b96ede2 | PRE-K01已存在资产/历史派生 | 未证明单文件级USER正式认可 | PRE-K01流程形成、读取或锁定证据成立；具体层级见原结果 | K01候选总账/版本锁所记录；本任务不晋升 | L732-L735 |
| PK01-ASSET-REF-0032 | PRE-K01 final仅记录路径/角色，未逐字给出本对象SHA；不得推断 | PRE-K01已存在资产/历史派生 | 未证明单文件级USER正式认可 | 失败/无效，不纳入 | K01记录为历史/错误/失败/禁止状态 | L950-L956 |
| PK01-ASSET-REF-0033 | SHA-256=16ba2a94cddddbf88a26035f1b820d2d52c195d60b350aa8bcb49eeb0dfae1f8 | PRE-K01已存在资产/历史派生 | 未证明单文件级USER正式认可 | 审计/血缘证据，不等于独立业务输入 | K01候选总账/版本锁所记录；本任务不晋升 | multiple |
| PK01-ASSET-REF-0034 | SHA-256=16ba2a94cddddbf88a26035f1b820d2d52c195d60b350aa8bcb49eeb0dfae1f8 | PRE-K01已存在资产/历史派生 | 未证明单文件级USER正式认可 | 审计/血缘证据，不等于独立业务输入 | K01候选总账/版本锁所记录；本任务不晋升 | multiple |
| PK01-ASSET-REF-0035 | SHA-256=26e1d560097b8a6eaf25eb538ed4935ea6ce8b0577ce28eb38c403915075a687 | PRE-K01已存在资产/历史派生 | USER直接纠正136正式人工源；副本角色分开 | PRE-K01流程形成、读取或锁定证据成立；具体层级见原结果 | K01唯一锁定核心源 | L297-L310 |
| PK01-ASSET-REF-0036 | SHA-256=064396b00fc31856deb404bd9febaf592bfaa0b93e53a4c9b5d4d6acb159d92a | PRE-K01已存在资产/历史派生 | M2阶段WPS确认行为；不等于逐文件签字 | PRE-K01流程形成、读取或锁定证据成立；具体层级见原结果 | K01候选总账/版本锁所记录；本任务不晋升 | L467-L469 |
| PK01-ASSET-REF-0037 | SHA-256=5d6a0b3236bbda2fae443d0a51a4ee9a33537538119a17b067d37a1038332d4a | PRE-K01已存在资产/历史派生 | USER确认行为成立；WPS固定措辞由assistant先提供 | PRE-K01流程形成、读取或锁定证据成立；具体层级见原结果 | K01唯一锁定核心源 | L408-L435 |
| PK01-ASSET-REF-0038 | SHA-256=052d27c8f797933225f0d6180bf5772f9ebce555bbc231b3c6f0c0465db7dae7 | PRE-K01已存在资产/历史派生 | 未证明单文件级USER正式认可 | PRE-K01流程形成、读取或锁定证据成立；具体层级见原结果 | K01候选总账/版本锁所记录；本任务不晋升 | L471-L473 |
| PK01-ASSET-REF-0039 | SHA-256=c303a9a29749a834db3e9cc1cd0305eeb3c72c8885cf51920507ab1116e5049c | PRE-K01已存在资产/历史派生 | 未证明单文件级USER正式认可 | PRE-K01流程形成、读取或锁定证据成立；具体层级见原结果 | K01候选总账/版本锁所记录；本任务不晋升 | L475-L477 |
| PK01-ASSET-REF-0040 | SHA-256=554faaa71a1f8629e9e3273a53e3ff9595215f40a94b501f6b6818c07f4fb3c8 | PRE-K01已存在资产/历史派生 | 未证明单文件级USER正式认可 | PRE-K01流程形成、读取或锁定证据成立；具体层级见原结果 | K01候选总账/版本锁所记录；本任务不晋升 | L479-L481 |
| PK01-ASSET-REF-0041 | SHA-256=c888c7848ffd24941e5ee012cd120a018b0d36954cc3f387803cc9b2ac0044a4 | PRE-K01已存在资产/历史派生 | USER同意M0—M5并启动M0；非逐文件签字 | PRE-K01流程形成、读取或锁定证据成立；具体层级见原结果 | K01候选总账/版本锁所记录；本任务不晋升 | L483-L485 |
| PK01-ASSET-REF-0042 | SHA-256=cc030c532c82f490b2812e7768d6f0b688c66b969029facfbecd283bc4c8b576 | PRE-K01已存在资产/历史派生 | USER同意M0—M5并启动M0；非逐文件签字 | PRE-K01流程形成、读取或锁定证据成立；具体层级见原结果 | K01候选总账/版本锁所记录；本任务不晋升 | L487-L489 |
| PK01-ASSET-REF-0043 | SHA-256=7a8cd20998603b6bbaabeb8f5d3df22bfff3fa7654c8d12d2939394b3a521e0f | PRE-K01已存在资产/历史派生 | USER同意M0—M5并启动M0；非逐文件签字 | PRE-K01流程形成、读取或锁定证据成立；具体层级见原结果 | K01候选总账/版本锁所记录；本任务不晋升 | L491-L493 |
| PK01-ASSET-REF-0044 | SHA-256=c6376f9e9c12fd22c4a3d34de61525d93faf5a6865afae719ff3c327e7fd66c1 | PRE-K01已存在资产/历史派生 | 未证明单文件级USER正式认可 | PRE-K01流程形成、读取或锁定证据成立；具体层级见原结果 | K01候选总账/版本锁所记录；本任务不晋升 | L549-L551 |
| PK01-ASSET-REF-0045 | PRE-K01 final仅记录路径/角色，未逐字给出本对象SHA；不得推断 | PRE-K01已存在资产/历史派生 | 未证明单文件级USER正式认可 | PRE-K01流程形成、读取或锁定证据成立；具体层级见原结果 | K01候选总账/版本锁所记录；本任务不晋升 | L553-L555 |
| PK01-ASSET-REF-0046 | PRE-K01 final仅记录路径/角色，未逐字给出本对象SHA；不得推断 | PRE-K01已存在资产/历史派生 | 未证明单文件级USER正式认可 | PRE-K01流程形成、读取或锁定证据成立；具体层级见原结果 | K01候选总账/版本锁所记录；本任务不晋升 | L557-L559 |
| PK01-ASSET-REF-0047 | PRE-K01 final仅记录路径/角色，未逐字给出本对象SHA；不得推断 | PRE-K01已存在资产/历史派生 | 未证明单文件级USER正式认可 | PRE-K01流程形成、读取或锁定证据成立；具体层级见原结果 | K01候选总账/版本锁所记录；本任务不晋升 | L561-L563 |
| PK01-ASSET-REF-0048 | SHA-256=c5e4b1321dc361719f2d05b73e47b4bdb645f2242baec2539b363241fc949fc7 | PRE-K01已存在资产/历史派生 | 未证明单文件级USER正式认可 | PRE-K01流程形成、读取或锁定证据成立；具体层级见原结果 | K01候选总账/版本锁所记录；本任务不晋升 | L608-L610 |
| PK01-ASSET-REF-0049 | SHA-256=f0bfeeae6e7f4793113952f4bd70052ec8c6e7049ddf80f1ae2c9d97742eadc4 | PRE-K01已存在资产/历史派生 | 未证明单文件级USER正式认可 | PRE-K01流程形成、读取或锁定证据成立；具体层级见原结果 | K01候选总账/版本锁所记录；本任务不晋升 | L612-L614 |
| PK01-ASSET-REF-0050 | SHA-256=4071e6efa72c92f6e0467775d813c73c78348c026b5e38ab75daeb46bea8a8e0 | PRE-K01已存在资产/历史派生 | 未证明单文件级USER正式认可 | PRE-K01流程形成、读取或锁定证据成立；具体层级见原结果 | K01候选总账/版本锁所记录；本任务不晋升 | L616-L618 |
| PK01-ASSET-REF-0051 | SHA-256=b5cf356f15ff078d6043bf77960498bd3d549d56c895684c956ecabc5962c379 | PRE-K01已存在资产/历史派生 | 未证明单文件级USER正式认可 | PRE-K01流程形成、读取或锁定证据成立；具体层级见原结果 | K01候选总账/版本锁所记录；本任务不晋升 | L620-L622 |
| PK01-ASSET-REF-0052 | SHA-256=46c9dd68824412f2e9b078aa925962c79ae0167fe217a113c919376b20f3a99c | PRE-K01已存在资产/历史派生 | 未证明单文件级USER正式认可 | 是否独立下游读取仍未知 | K01候选总账/版本锁所记录；本任务不晋升 | L633-L644 |
| PK01-ASSET-REF-0053 | PRE-K01 final仅记录路径/角色，未逐字给出本对象SHA；不得推断 | PRE-K01已存在资产/历史派生 | 未证明单文件级USER正式认可 | 审计/血缘证据，不等于独立业务输入 | K01候选总账/版本锁所记录；本任务不晋升 | L424-L435 |
| PK01-ASSET-REF-0054 | SHA-256=0e452ccd432dd450224fb8bc68bea1145bae3192702bc81ffb5b9ded07bf6998 | PRE-K01已存在资产/历史派生 | 未证明单文件级USER正式认可 | 审计/血缘证据，不等于独立业务输入 | K01候选总账/版本锁所记录；本任务不晋升 | L391-L396 |
| PK01-ASSET-REF-0055 | SHA-256=915cbe0bfe02fe1696279e051acf3dec8ba120b538e1707aa319c11258b49dc1 | PRE-K01已存在资产/历史派生 | A136阶段参与/上传/同意；非逐文件原创认可 | PRE-K01流程形成、读取或锁定证据成立；具体层级见原结果 | K01候选总账/版本锁所记录；本任务不晋升 | L328-L330 |
| PK01-ASSET-REF-0056 | SHA-256=6114620f94284b0cb77aae4b8b1e5abbe1370fbef814f94bb87525a7f9c025f5 | PRE-K01已存在资产/历史派生 | A136阶段参与/上传/同意；非逐文件原创认可 | PRE-K01流程形成、读取或锁定证据成立；具体层级见原结果 | K01候选总账/版本锁所记录；本任务不晋升 | L332-L334 |
| PK01-ASSET-REF-0057 | SHA-256=118560141200a0cd94c3b6dbf6da9dd7960201bb07468bb13bdae80b2a449ab4 | PRE-K01已存在资产/历史派生 | A136阶段参与/上传/同意；非逐文件原创认可 | 审计/血缘证据，不等于独立业务输入 | K01候选总账/版本锁所记录；本任务不晋升 | L336-L352 |
| PK01-ASSET-REF-0058 | SHA-256=c6376f9e9c12fd22c4a3d34de61525d93faf5a6865afae719ff3c327e7fd66c1 | PRE-K01已存在资产/历史派生 | 未证明单文件级USER正式认可 | PRE-K01流程形成、读取或锁定证据成立；具体层级见原结果 | K01候选总账/版本锁所记录；本任务不晋升 | L541-L543 |
| PK01-ASSET-REF-0059 | SHA-256=c6376f9e9c12fd22c4a3d34de61525d93faf5a6865afae719ff3c327e7fd66c1 | PRE-K01已存在资产/历史派生 | 未证明单文件级USER正式认可 | PRE-K01流程形成、读取或锁定证据成立；具体层级见原结果 | K01候选总账/版本锁所记录；本任务不晋升 | L545-L547 |
| PK01-ASSET-REF-0060 | 集合632对象；aggregate SHA-256=0e64b29454e6ff89631641bb16a4a19079c2c430733daf6f9a6a05173daa6f01 | PRE-K01已存在资产/历史派生 | USER原始数据家族声明；不扩为集合绝对完整性 | 原始输入/补证家族被流程使用 | K01候选总账/版本锁所记录；本任务不晋升 | L230-L233 |
| PK01-ASSET-REF-0061 | 集合27对象；aggregate SHA-256=9a0ccaaf1328949de3b90a02ad03343bc1d443dddaa0ecee1df68cc32458b9b1 | PRE-K01已存在资产/历史派生 | USER原始数据家族声明；不扩为集合绝对完整性 | 原始输入/补证家族被流程使用 | K01候选总账/版本锁所记录；本任务不晋升 | L225-L228 |
| PK01-ASSET-REF-0062 | SHA-256=801ee416bd8234cc69f83090e4caa9272839fcbecb27ef4166f8c7cecca2d315 | PRE-K01已存在资产/历史派生 | 未证明单文件级USER正式认可 | 失败/无效，不纳入 | K01记录为历史/错误/失败/禁止状态 | L920-L926 |
| PK01-ASSET-REF-0063 | SHA-256=26e1d560097b8a6eaf25eb538ed4935ea6ce8b0577ce28eb38c403915075a687 | PRE-K01已存在资产/历史派生 | USER直接纠正136正式人工源；副本角色分开 | PRE-K01流程形成、读取或锁定证据成立；具体层级见原结果 | K01候选总账/版本锁所记录；本任务不晋升 | L928-L939 |
| PK01-ASSET-REF-0064 | 集合38对象；aggregate SHA-256=859d637a6beabf3c2433ab064b581fa9ac5bf30ff8bd17027c65b1d7d6c54b7e | PRE-K01已存在资产/历史派生 | USER原始数据家族声明；不扩为集合绝对完整性 | 原始输入/补证家族被流程使用 | K01候选总账/版本锁所记录；本任务不晋升 | L220-L223 |
| PK01-ASSET-REF-0065 | PRE-K01 final仅记录路径/角色，未逐字给出本对象SHA；不得推断 | Recovery来源证据 | 无；来源索引 | 来源证明，不计业务流程采用 | Recovery证据，不作为K01数据资产 | multiple |
| PK01-ASSET-REF-0066 | PRE-K01 final仅记录路径/角色，未逐字给出本对象SHA；不得推断 | Recovery来源证据 | 无；来源索引 | 来源证明，不计业务流程采用 | Recovery证据，不作为K01数据资产 | multiple |

## 5. 双向统一41项资产：41/41

“当前状态”来自冻结的双向统一清单；“正式晋升”全部为 false。比较结论只说明两个历史基线之间的关系，不改变当前状态。

| P1ASSET | 统一名称 | 当前状态 | 历史路径 | PRE-K01映射 | 主分类 | 状态维度差 | 漏项/冲突/未决 |
|---|---|---|---|---|---|---|---|
| P1ASSET-001 | 币安账户交易流水原始导出 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/Binance-交易流水-a.xlsx | PK01-ASSET-REF-0015 | EXACT_MATCH | 否 | 均无 |
| P1ASSET-002 | 币安合约基础订单历史原始导出 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/Binance-合约订单历史记录-a.xlsx | PK01-ASSET-REF-0019 | EXACT_MATCH | 否 | 均无 |
| P1ASSET-003 | 币安合约成交历史原始导出 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/Binance-合约交易历史记录-a.xlsx | PK01-ASSET-REF-0016 | EXACT_MATCH | 否 | 均无 |
| P1ASSET-004 | 币安合约资金流水原始导出 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/Binance-合约交易流水-a.xlsx | PK01-ASSET-REF-0017 | EXACT_MATCH | 否 | 均无 |
| P1ASSET-005 | 币安合约仓位历史原始导出 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/Binance-合约仓位历史记录-a.xlsx | PK01-ASSET-REF-0018 | EXACT_MATCH | 否 | 均无 |
| P1ASSET-006 | 账户结算单原始截图集合 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/账户结算单_原始截图 | PK01-ASSET-REF-0064 | COLLECTION_HASH_METHOD_DIFF | 否 | 均无 |
| P1ASSET-007 | 条件委托截图业务集合与目录元数据 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/补充证据_历史委托条件委托截图 | PK01-ASSET-REF-0060 | COLLECTION_HASH_METHOD_DIFF | 否 | 均无 |
| P1ASSET-008 | 跟单与仓位补证业务集合与目录元数据 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/补充证据_币安跟单与仓位记录 | PK01-ASSET-REF-0061 | COLLECTION_HASH_METHOD_DIFF | 否 | 均无 |
| P1ASSET-009 | 旧131笔人工复盘母表 | 相关，但仍待验证 | /Users/luodaluo/Desktop/30天复盘原始数据/30天复盘(9).xlsx | PK01-ASSET-REF-0014 | EXACT_MATCH | 是（非冲突） | 均无 |
| P1ASSET-010 | 136笔主动交易人工复盘母表 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/补充输入_136笔人工复盘/30天复盘_136笔主动交易人工补全版.xlsx | PK01-ASSET-REF-0035, PK01-ASSET-REF-0063 | SAME_BYTES_DIFFERENT_PATH_ROLE | 是（非冲突） | 均无 |
| P1ASSET-011 | 148个真实仓位周期主表 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/输出_新版_V2_136笔主动交易/05_交易事件与仓位链重建_V2/05_V2_148个真实仓位周期主表.xlsx | PK01-ASSET-REF-0038 | SAME_BYTES_DIFFERENT_PATH_ROLE | 否 | 均无 |
| P1ASSET-012 | Order/Fill归属与交易事件数据组 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/输出_新版_V2_136笔主动交易/05_交易事件与仓位链重建_V2/05_V2_Order与Fill归属表.xlsx, /Users/luodaluo/Desktop/30天复盘原始数据/输出_新版_V2_136笔主动交易/05_交易事件与仓位链重建_V2/05_V2_交易事件明细.xlsx, /Users/luodaluo/Desktop/30天复盘原始数据/输出_新版_V2_136笔主动交易/05_交易事件与仓位链重建_V2/05_V2_自动跟单隔离标记.xlsx | — | PARTIAL_OVERLAP | 否 | 均无 |
| P1ASSET-013 | 136笔人工复盘与客观周期匹配表 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/输出_新版_V2_136笔主动交易/06_人工复盘匹配_V2/06_V2_136笔人工复盘与周期匹配表.xlsx | PK01-ASSET-REF-0039 | SAME_BYTES_DIFFERENT_PATH_ROLE | 否 | 均无 |
| P1ASSET-014 | 周期资金节点与账户权益轨迹数据组 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/输出_新版_V2_136笔主动交易/07_资金与权益重建_V2/07_V2_周期盈亏与资金节点表.xlsx, /Users/luodaluo/Desktop/30天复盘原始数据/输出_新版_V2_136笔主动交易/07_资金与权益重建_V2/07_V2_账户权益轨迹.xlsx | PK01-ASSET-REF-0049, PK01-ASSET-REF-0050 | SAME_BYTES_DIFFERENT_PATH_ROLE | 否 | 均无 |
| P1ASSET-015 | P3｜148个真实仓位全量中文交易链 | 相关，但仍待验证 | /Users/luodaluo/Desktop/30天复盘原始数据/用户版_中文交易链路/技术支持文件/P3_148个真实仓位全量中文交易链构建/P3_148个真实仓位全量中文交易链.xlsx | PK01-ASSET-REF-0036 | PARTIAL_OVERLAP | 否 | 均无 |
| P1ASSET-016 | M4-F2十笔增强原型仓位链连续性修正版 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/人工复盘增强版_修正工程_V2_136笔主动交易/M4-F2_十笔增强原型仓位链连续性修正/05_最终交付/30天逐笔人工复盘增强版_10笔成品原型_F2.5.4_M4-F2仓位链连续性修正版.xlsx | PK01-ASSET-REF-0037 | SAME_BYTES_DIFFERENT_PATH_ROLE | 否 | 均无 |
| P1ASSET-017 | H0-H 136周期客观MFE/MAE冻结数据 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/H0_历史行情与MFE_MAE技术底座/H0-H_全量终验与客观行情指标冻结/03_周期终验与冻结/H0-H_CYCLE_OBJECTIVE_METRICS_FROZEN.csv | PK01-ASSET-REF-0021 | EXACT_MATCH | 否 | 均无 |
| P1ASSET-018 | N1-2 136笔增强版验收工作簿 | 相关，但仍待验证 | /Users/luodaluo/Desktop/30天复盘原始数据/N线_136笔完整增强复盘与交易系统/N1_136笔完整增强版构建/N1-2_136笔完整增强版正式构建与技术验收/02_正式工作簿/30天逐笔人工复盘增强版_136笔_N1-2验收版.xlsx | — | OUTSIDE_PREK01_TASK_SCOPE | 否 | 均无 |
| P1ASSET-019 | P4/P5中文可视化交易复盘主工作簿 | 相关，但仍待验证 | /Users/luodaluo/Desktop/30天复盘原始数据/用户版_中文交易链路/最终用户文件/中文可视化交易复盘主工作簿.xlsx | — | FAMILY_LEVEL_COVERAGE | 否 | 均无 |
| P1ASSET-020 | 早期原始数据审计集合 | 相关，但仍待验证 | /Users/luodaluo/Desktop/30天复盘原始数据/输出_新版/03_原始数据审计 | — | OUTSIDE_PREK01_TASK_SCOPE | 否 | 均无 |
| P1ASSET-021 | 阶段05 v2交易事件与仓位链核心集合 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/输出_新版/05_交易事件与仓位链重建/重建数据_v2 | PK01-ASSET-REF-0040 | FAMILY_LEVEL_COVERAGE | 否 | 均无 |
| P1ASSET-022 | 阶段05-B01跟单隔离与重建集合 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/输出_新版/05_交易事件与仓位链重建/补充证据_B01 | — | FAMILY_LEVEL_COVERAGE | 否 | 均无 |
| P1ASSET-023 | 阶段06人工复盘与真实周期匹配集合 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/输出_新版/06_人工复盘匹配 | — | FAMILY_LEVEL_COVERAGE | 否 | 均无 |
| P1ASSET-024 | 阶段07账户资金与权益重建集合 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/输出_新版/07_账户资金与权益重建 | PK01-ASSET-REF-0048, PK01-ASSET-REF-0049, PK01-ASSET-REF-0050, PK01-ASSET-REF-0051 | FAMILY_LEVEL_COVERAGE | 否 | 均无 |
| P1ASSET-025 | A136旧131到新136编号迁移证据集合 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/用户版_中文交易链路/技术支持文件/A136_136笔编号迁移只读预案与用户确认 | PK01-ASSET-REF-0055, PK01-ASSET-REF-0056, PK01-ASSET-REF-0057 | FAMILY_LEVEL_COVERAGE | 否 | 均无 |
| P1ASSET-026 | A497条件委托生命周期结构化与匹配集合 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/用户版_中文交易链路/技术支持文件/A497_安卓端条件委托生命周期证据验收 | PK01-ASSET-REF-0044, PK01-ASSET-REF-0058, PK01-ASSET-REF-0059 | FAMILY_LEVEL_COVERAGE | 否 | 均无 |
| P1ASSET-027 | M0现行编号映射冻结集合 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/用户版_中文交易链路/技术支持文件/M0_现行编号映射冻结 | PK01-ASSET-REF-0041, PK01-ASSET-REF-0042, PK01-ASSET-REF-0043 | FAMILY_LEVEL_COVERAGE | 否 | 均无 |
| P1ASSET-028 | M1阶段00—09技术底座升级集合 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/用户版_中文交易链路/技术支持文件/M1_阶段00-09技术底座升级 | PK01-ASSET-REF-0040, PK01-ASSET-REF-0048, PK01-ASSET-REF-0049, PK01-ASSET-REF-0050, PK01-ASSET-REF-0051 | FAMILY_LEVEL_COVERAGE | 否 | 均无 |
| P1ASSET-029 | M2 P0—P5中文交易链升级集合 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/用户版_中文交易链路/技术支持文件/M2_P0-P5中文交易链升级 | PK01-ASSET-REF-0036 | FAMILY_LEVEL_COVERAGE | 否 | 均无 |
| P1ASSET-030 | R1十笔逐笔人工复盘原型与技术中间结果 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/人工复盘增强版_修正工程/R1_10笔成品原型 | PK01-ASSET-REF-0029, PK01-ASSET-REF-0030, PK01-ASSET-REF-0031 | FAMILY_LEVEL_COVERAGE | 否 | 均无 |
| P1ASSET-031 | F2.5.4 WPS实测通过版工作簿 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/人工复盘增强版_修正工程/R1_10笔成品原型/30天逐笔人工复盘增强版_10笔成品原型_F2.5.4_WPS实测通过版.xlsx | PK01-ASSET-REF-0029 | EXACT_MATCH | 是（非冲突） | 均无 |
| P1ASSET-032 | M3R-F1人工内容与技术口径定点修正集合 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/用户版_中文交易链路/技术支持文件/M3R-F1_人工内容与技术口径定点修正 | — | FAMILY_LEVEL_COVERAGE | 否 | 均无 |
| P1ASSET-033 | M4与M4-F1条件委托生命周期接入集合 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/用户版_中文交易链路/技术支持文件/M4_A497条件委托生命周期接入, /Users/luodaluo/Desktop/30天复盘原始数据/用户版_中文交易链路/技术支持文件/M4-F1_条件委托字段继承与证据来源口径修正 | PK01-ASSET-REF-0044, PK01-ASSET-REF-0045, PK01-ASSET-REF-0046, PK01-ASSET-REF-0047 | FAMILY_LEVEL_COVERAGE | 否 | 均无 |
| P1ASSET-034 | M4-F2十笔增强原型仓位链连续性修正版与审计集合 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/人工复盘增强版_修正工程_V2_136笔主动交易/M4-F2_十笔增强原型仓位链连续性修正, /Users/luodaluo/Desktop/30天复盘原始数据/用户版_中文交易链路/技术支持文件/M4-F2_十笔增强原型仓位链连续性修正 | PK01-ASSET-REF-0037, PK01-ASSET-REF-0053 | FAMILY_LEVEL_COVERAGE | 否 | 均无 |
| P1ASSET-035 | M5全项目最终验收与现行版本切换集合 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/用户版_中文交易链路/技术支持文件/M5_全项目最终验收与现行版本切换 | PK01-ASSET-REF-0035, PK01-ASSET-REF-0036, PK01-ASSET-REF-0037, PK01-ASSET-REF-0040, PK01-ASSET-REF-0044, PK01-ASSET-REF-0045, PK01-ASSET-REF-0046, PK01-ASSET-REF-0047, PK01-ASSET-REF-0048, PK01-ASSET-REF-0049, PK01-ASSET-REF-0050, PK01-ASSET-REF-0051, PK01-ASSET-REF-0052, PK01-ASSET-REF-0054 | FAMILY_LEVEL_COVERAGE | 否 | 均无 |
| P1ASSET-036 | H0-B至H0-D十笔行情、MFE/MAE与边界精度集合 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/H0_历史行情与MFE_MAE技术底座/H0-B_10笔历史行情下载与完整性验收, /Users/luodaluo/Desktop/30天复盘原始数据/H0_历史行情与MFE_MAE技术底座/H0-C_10笔MFE_MAE计算与结果核验, /Users/luodaluo/Desktop/30天复盘原始数据/H0_历史行情与MFE_MAE技术底座/H0-D_边界精度复核与136笔扩展决策 | — | FAMILY_LEVEL_COVERAGE | 否 | 均无 |
| P1ASSET-037 | H0-E至H0-H的136周期、405阶段与冻结客观指标集合 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/H0_历史行情与MFE_MAE技术底座/H0-E_136笔客观仓位阶段冻结, /Users/luodaluo/Desktop/30天复盘原始数据/H0_历史行情与MFE_MAE技术底座/H0-F_136笔历史行情下载与完整性验收, /Users/luodaluo/Desktop/30天复盘原始数据/H0_历史行情与MFE_MAE技术底座/H0-G_136笔MFE_MAE全量计算与精度分级, /Users/luodaluo/Desktop/30天复盘原始数据/H0_历史行情与MFE_MAE技术底座/H0-H_全量终验与客观行情指标冻结 | PK01-ASSET-REF-0020, PK01-ASSET-REF-0021, PK01-ASSET-REF-0022, PK01-ASSET-REF-0023, PK01-ASSET-REF-0024 | FAMILY_LEVEL_COVERAGE | 否 | 均无 |
| P1ASSET-038 | 救援审计工程谱系、阶段总账与数据血缘集合 | 候选可采用 | /Users/luodaluo/Desktop/30天复盘原始数据/救援审计_全项目工程谱系与数据血缘恢复 | PK01-ASSET-REF-0033, PK01-ASSET-REF-0034 | FAMILY_LEVEL_COVERAGE | 否 | 均无 |
| P1ASSET-039 | N1-A全中文用户版产品规格补充冻结集合 | 相关，但仍待验证 | /Users/luodaluo/Desktop/30天复盘原始数据/N线_136笔完整增强复盘与交易系统/N1_136笔完整增强版构建/N1-A_136笔全中文用户版产品规格补充冻结 | — | OUTSIDE_PREK01_TASK_SCOPE | 否 | 均无 |
| P1ASSET-040 | N1-B错误分支工作簿与证据 | 相关，但仍待验证 | /Users/luodaluo/Desktop/30天复盘原始数据/N线_136笔完整增强复盘与交易系统/N1_136笔完整增强版构建/N1-B_136笔全中文用户工作版构建 | PK01-ASSET-REF-0027 | PARTIAL_OVERLAP | 是（非冲突） | 均无 |
| P1ASSET-041 | 只读三方差异审计报告 | 相关，但仍待验证 | /Users/luodaluo/Desktop/30天复盘原始数据/只读差异审计_阶段1_三方总报告.md | — | OUTSIDE_PREK01_TASK_SCOPE | 否 | 均无 |

## 6. 双向闭合与范围裁决

- `P1ASSET-018`、`P1ASSET-020`、`P1ASSET-039`、`P1ASSET-041` 属于 PRE-K01 “恢复 DATA BASELINE”任务范围外；不能把范围外对象计作漏扫。
- 家族级覆盖表示 PRE-K01 通过“现行正式版”“A136/A497/H0/R1”等家族或阶段对象覆盖统一清单中的更细颗粒对象；它不是逐文件精确同义，也不是遗漏。
- PRE-K01 单独列出的 Chat、K01、Recovery 对象是身份、来源或边界证据；统一目的1的 41 项分母是数据/文件候选资产。两类单位不同，已分别闭合。
- `PK01-ASSET-REF-0052` 的“行为特征统计”在 PRE-K01 中保存为“锁定候选、流程采用未知”；统一清单的家族级候选覆盖不能扩大为已被 USER 认可。
- “相关但仍需核验”的统一资产不会因本次比较自动变为“候选可采用”；PRE-K01 的历史采用角色也不会自动改写统一清单当前候选状态。
- 没有做 `336 vs 41` 或任何非同义分母直接减法。

## 7. 完整性断言

- 66 个 PRE-K01 资产引用均有一条 `ASSET_COMPARISON / PK01_ASSET_REF` 记录。
- 41 个统一资产均有一条 `ASSET_COMPARISON / P1ASSET` 记录。
- 所有 107 条资产比较记录均 `closed=true`。
- `prek01_true_omission=true`：0。
- `unified_true_omission=true`：0。
- `substantive_conflict=true`：0。
- `unresolved=true`：0。
- 本报告不执行复制、重命名、晋升、production 指定或未来构建输入批准。
