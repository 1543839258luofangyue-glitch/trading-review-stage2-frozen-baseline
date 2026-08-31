# PRE-K01与双向统一结果｜目的3 USER证据与认可核验

## 1. 裁定结论

本报告不做“770 条消息 vs PRE-K01 条目数”的数量比较。770 是修复后的作者裁定消息分母；本次分母是 PRE-K01 `final_answer` 中实际作出的 **15 条 USER 原话、确认、同意、修改、WPS验收、阶段认可或综合认可层级声明**。

- PRE-K01 USER证据声明：**15/15 已核验并闭合**。
- USER 行为与本人逐字措辞均成立：**9**。
- USER 确认/发送行为成立，但逐字措辞由前序 assistant 提供：**3**。
- USER 行为成立，但消息本身没有可归属为 USER 原创的文字：**2**。
- 综合认可层级判断：**1，SUPPORTED_WITH_QUALIFICATION**。
- 认可层级扩大：**0**。
- 需要修正的逐字作者归属：**3**。
- 未解决：**0**。

核心规则是把“谁写了这句话”“谁点击/发送/确认了它”“这个确认覆盖哪个阶段”“是否构成逐文件逐字段正式认可”分开判断。

## 2. 15/15逐项核验

| 核验ID | PRE-K01声明 | 证据指针 | 作者裁定 | USER行为 | 最终裁定 | 说明 |
|---|---|---|---|---|---|---|
| PK01-USER-0001 | K01授权启动行为与逐字句 | W04:L25711 | OUTSIDE_770_DIRECT_SOURCE | 成立 | CONFIRMATION_BEHAVIOR_TRUE_WORDING_AI_SUPPLIED | USER确实发出授权；紧邻前序assistant已逐字给出同一句，故不能称USER原创措辞 |
| PK01-USER-0002 | K01阶段切换USER提出/批准 | CHANGE-K01-20260803-001 | POST_K01_RECORD | 成立 | BEHAVIOR_TRUE_NO_VERBATIM_AUTHORSHIP_CLAIM | USER行为成立；仅作后验角色证明 |
| PK01-USER-0003 | 四份Binance文件是30天复盘原始来源 | P3MSG-0084 | FULL_USER | 成立 | FULL_USER | 行为与逐字措辞均成立；只证明所指四份，不扩展第五份账户流水的同一USER句 |
| PK01-USER-0004 | 成交笔数来自Binance合约交易历史并属后台技术数据 | P3MSG-0734 | FULL_USER | 成立 | FULL_USER | 行为与逐字措辞成立 |
| PK01-USER-0005 | 只有旧131母表被136版替代，其余列举资料为原始数据 | P3MSG-0742 | FULL_USER | 成立 | FULL_USER | 行为与逐字措辞成立；截图需结构化不等于绝对覆盖 |
| PK01-USER-0006 | 人工正式源纠正为136人工补全版 | P3MSG-0669 | FULL_USER | 成立 | FULL_USER | 行为与逐字措辞成立 |
| PK01-USER-0007 | 上传A136_07用户确认清单 | P3MSG-0385 | PURE_NONUSER | 成立 | BEHAVIOR_TRUE_NO_USER_TEXT | USER上传行为成立；消息卡只有附件，无USER原创文字 |
| PK01-USER-0008 | 同意M0—M5并表示后续对照检查 | P3MSG-0388 | FULL_USER | 成立 | FULL_USER | 阶段级同意成立，不等于逐文件验收 |
| PK01-USER-0009 | 开始执行M0 | P3MSG-0389 | FULL_USER | 成立 | FULL_USER | 启动行为与逐字措辞成立 |
| PK01-USER-0010 | 检查T087且依据136人工补全版更新 | P3MSG-0439 | MIXED_SEPARABLE | 成立 | FULL_USER_SEPARABLE | USER文字可与截图分离；只证明实际检查范围 |
| PK01-USER-0011 | M4-F2 WPS实测通过 | P3MSG-0465 | PURE_NONUSER | 成立 | CONFIRMATION_BEHAVIOR_TRUE_WORDING_AI_SUPPLIED | USER发送确认行为成立；逐字短句来自前序assistant |
| PK01-USER-0012 | M2 WPS实测通过 | P3MSG-0412 | PURE_NONUSER | 成立 | CONFIRMATION_BEHAVIOR_TRUE_WORDING_AI_SUPPLIED | USER发送确认行为成立；逐字短句来自前序assistant |
| PK01-USER-0013 | 同意CONFIRM_01—16推荐答案 | P3MSG-0689 | FULL_USER | 成立 | FULL_USER_CONFIRMATION_OF_AI_CONTENT | USER同意句为本人原创；被同意的推荐答案内容仍是AI文本，只证明确认行为与相应层级 |
| PK01-USER-0014 | WORKING HYPOTHESIS由USER提出 | 主Thread第371行 | DIRECT_PREK01_USER_PROMPT | 成立 | FULL_USER | 假设确由当前PRE-K01任务USER消息提出 |
| PK01-USER-0015 | 核心家族有阶段/产品级认可但无逐文件逐字段签字的综合判断 | multiple | SYNTHESIS | 成立 | SUPPORTED_WITH_QUALIFICATION | 由上述行为与P2角色共同支持；PRE-K01已明确限制层级，未扩大 |

## 3. 作者归属纠正

### K01授权启动句

W04 定点读取前已按 00A 验证：当前文件 size=1,210,396、SHA-256=`464e806514fc33ea00924524919f789f3eb3ca291233c03ff0d05a9cd1226436`，与快照一致。W04 的紧邻前序 assistant 已先逐字给出授权句，随后 USER 发送同一句。因此：

- USER 的授权行为成立；
- 该句不能标为 USER 本人原创措辞；
- 该证据在目的3统一 770 消息窗口之后，故标为 `OUTSIDE_770_DIRECT_SOURCE`，但经过 00A 定点身份验证；
- 它只证明 K01 授权行为，不倒灌为 PRE-K01 数据资产事实。

### M2与M4-F2的“WPS实测通过”

`P3MSG-0412` 与 `P3MSG-0465` 均显示 USER 发送确认行为成立，但固定短句由前序 assistant 先提供。因此两项均是：

`CONFIRMATION_BEHAVIOR_TRUE_WORDING_AI_SUPPLIED`

这不取消 WPS 验收行为，也不允许把逐字短句标成 USER 原创。

## 4. 行为成立但无USER原创文本

- K01 阶段切换记录：定点验证后的记录显示提出者/最终批准者为 USER、实施者为 Codex。它是结构化后验角色证明，不是 USER 原话证据。
- `P3MSG-0385`：消息卡只有 A136 附件，USER 上传行为成立，但没有可分离的 USER 原创文字。

## 5. USER本人文字与确认层级

以下九项的 USER 行为和相应 USER 文字身份成立：

1. 四份 Binance 文件是 30 天复盘原始来源（`P3MSG-0084`）。
2. 成交笔数来自 Binance 合约交易历史、属于后台技术数据（`P3MSG-0734`）。
3. 只有旧 131 母表被 136 版替代，其余列举资料为原始数据（`P3MSG-0742`）。
4. 人工正式源纠正为 136 人工补全版（`P3MSG-0669`）。
5. 同意 M0—M5，并表示后续对照检查（`P3MSG-0388`）。
6. 开始执行 M0（`P3MSG-0389`）。
7. 检查 T087，并依据 136 人工补全版更新（`P3MSG-0439`；USER 文字可与截图分离）。
8. 同意 CONFIRM_01—16 推荐答案（`P3MSG-0689`；同意句是 USER 文字，被同意的推荐答案内容仍是 AI 文本）。
9. WORKING HYPOTHESIS 由 USER 在 PRE-K01 主 Thread 第371行提出。

这些证据只支持各自声明的资料、阶段或确认范围。特别是：

- “四份 Binance 文件”不能自动扩成第五份账户流水也被同一句逐字认可。
- “截图需要结构化”不等于截图已经绝对覆盖。
- M0—M5 的阶段级同意不等于逐文件逐字段验收。
- T087 实际检查不等于对全部 136 笔逐笔签字。
- CONFIRM_01—16 的 USER 同意不把 AI 推荐答案改写为 USER 原创内容。
- WPS通过说明特定版本在当时通过测试，不自动批准其作为未来构建输入。

## 6. 综合认可层级判断

`PK01-USER-0015` 的结论是：

> 核心数据/产品家族存在阶段级或产品级 USER 确认与流程使用证据；没有证据支持把这种确认扩大为每个文件、每个字段、每个派生结果均被 USER 逐项正式认可。

裁定：**SUPPORTED_WITH_QUALIFICATION**。

依据包括上述 15 项核验与 P2FACT 的角色修正。PRE-K01 已明确限制认可层级，因此本次没有发现权威级扩大，但修正了三处“确认行为成立却把固定措辞当作 USER 原创”的作者归属。

## 7. 完整性断言

- `USER_EVIDENCE_CHECK`：15 条。
- 15 条均 `closed=true`。
- 15 条均有证据指针、作者/确认层级裁定和处置说明。
- `unresolved=true`：0。
- 没有把 770 条消息与 15 条 PRE-K01 声明相减或生成伪覆盖百分比。
- 没有执行 USER 筛选、user_trade_language 合并、clean production 或正式交易分析。

