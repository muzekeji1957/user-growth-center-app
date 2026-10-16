# -*- coding: utf-8 -*-
"""产品主数据（复用「内容工厂」真实在售 20 款产品，价格锚点 9.9→9999）。

这份清单同时被两处使用：
    1. ``user_growth.install`` 安装时写入 Growth Product 主数据；
    2. ``seed/generator.py`` 生成 mock 服务单据时使用，保证演示数据"是你真在卖的东西"。
"""

PRODUCTS = [
    {"product_code": "XF-001", "product_name": "AI 副业实战引流课", "category": "引流课", "price": 9.9, "service_days": 30, "billing_cycle": "一次性", "platform": "公众号/小红书", "audience": "0 基础想做副业的小白", "selling_point": "9.9 元低成本试错，快速跑通第一单", "description": "面向副业小白的入门引流课，含 AI 副业路径图与 3 个可执行小项目。"},
    {"product_code": "XF-002", "product_name": "4 引流品（AI 副业/DeepSeek/Coze/建站）", "category": "引流课", "price": 9.9, "service_days": 30, "billing_cycle": "一次性", "platform": "抖音/视频号", "audience": "泛流量用户", "selling_point": "四选一低价引流，覆盖热门 AI 主题", "description": "四款 9.9 引流课聚合，分别对应 AI 副业、DeepSeek、Coze、建站四个方向。"},
    {"product_code": "XF-003", "product_name": "0 基础 AI 副业变现 8 周营", "category": "正价课", "price": 399, "service_days": 56, "billing_cycle": "一次性", "platform": "公众号", "audience": "想系统学副业的个体", "selling_point": "8 周陪跑，从 0 到变现闭环", "description": "8 周系统化训练营，带作业批改与变现路径设计。"},
    {"product_code": "XF-004", "product_name": "AI 智能体开发实战营（Coze+Dify+LangChain）", "category": "正价课", "price": 999, "service_days": 60, "billing_cycle": "一次性", "platform": "小红书/公众号", "audience": "想做智能体的开发者/转型者", "selling_point": "三大主流框架横向打通", "description": "覆盖 Coze、Dify、LangChain 三套主流智能体开发范式。"},
    {"product_code": "XF-005", "product_name": "3 天 Coze 智能体入门", "category": "正价课", "price": 99, "service_days": 3, "billing_cycle": "一次性", "platform": "抖音", "audience": "想快速上手 Coze 的运营", "selling_point": "3 天做出第一个可用智能体", "description": "极短周期入门课，快速产出第一个 Coze 智能体。"},
    {"product_code": "XF-006", "product_name": "微信小程序开发实战营", "category": "正价课", "price": 999, "service_days": 60, "billing_cycle": "一次性", "platform": "公众号", "audience": "想做小程序的个体户", "selling_point": "从 0 上线一款小程序", "description": "小程序开发全流程实战，含上架与基础运营。"},
    {"product_code": "XF-007", "product_name": "AI 一对一私教", "category": "私教面授", "price": 999, "service_days": 30, "billing_cycle": "月度", "platform": "转介绍/企业直销", "audience": "需要定向辅导的转型学员", "selling_point": "一对一陪跑，按目标定制", "description": "面向转型学员与小微老板的一对一 AI 私教服务。"},
    {"product_code": "XF-008", "product_name": "8 周 AI 全栈工程师面授班", "category": "私教面授", "price": 8999, "service_days": 56, "billing_cycle": "一次性", "platform": "美团到店/转介绍", "audience": "想转行 AI 全栈的学员", "selling_point": "8 周面授，结业即具备交付能力", "description": "高强度面授班，覆盖 AI 应用全栈开发。"},
    {"product_code": "XF-009", "product_name": "AI 智能体定制·轻量版", "category": "智能体定制", "price": 299, "service_days": 15, "billing_cycle": "一次性", "platform": "美团经营宝", "audience": "需要轻量智能体的小微商家", "selling_point": "299 元快速拥有一个数字员工", "description": "轻量级智能体定制，适合单一场景自动化。"},
    {"product_code": "XF-010", "product_name": "AI 智能体定制·标准版", "category": "智能体定制", "price": 1999, "service_days": 30, "billing_cycle": "一次性", "platform": "美团经营宝", "audience": "有多场景自动化需求的企业", "selling_point": "标准版覆盖多业务线", "description": "标准版智能体定制，覆盖多场景工作流。"},
    {"product_code": "XF-011", "product_name": "AI 智能体定制·企业版", "category": "智能体定制", "price": 9999, "service_days": 90, "billing_cycle": "一次性", "platform": "企业直销", "audience": "有体系化数字员工需求的企业", "selling_point": "企业级私有部署与集成", "description": "企业版智能体定制，含私有部署与系统集成。"},
    {"product_code": "XF-012", "product_name": "抖音来客·AI 副业实战课", "category": "抖音来客", "price": 30, "service_days": 30, "billing_cycle": "一次性", "platform": "抖音来客", "audience": "抖音生态商家", "selling_point": "30 元入门抖音 AI 副业", "description": "面向抖音来客商家的 AI 副业实战课。"},
    {"product_code": "XF-013", "product_name": "闲鱼·AI 短视频带货脚本包", "category": "闲鱼工具", "price": 39, "service_days": 30, "billing_cycle": "一次性", "platform": "闲鱼", "audience": "做带货短视频的个人", "selling_point": "39 元拿到可直接拍的脚本", "description": "闲鱼售卖的 AI 短视频带货脚本包。"},
    {"product_code": "XF-014", "product_name": "闲鱼·AI 办公自动化工具包", "category": "闲鱼工具", "price": 49, "service_days": 30, "billing_cycle": "一次性", "platform": "闲鱼", "audience": "想提效办公的职场人", "selling_point": "49 元 Excel/Word/PPT 一键自动化", "description": "闲鱼售卖的 AI 办公自动化工具包。"},
    {"product_code": "XF-015", "product_name": "美团到店·AI 体验课（到店 1 次·引流）", "category": "美团到店", "price": 0, "service_days": 1, "billing_cycle": "一次性", "platform": "美团到店", "audience": "到店体验的本地用户", "selling_point": "0 元到店体验 AI 课", "description": "美团到店 0 元引流体验课，到店 1 次。"},
    {"product_code": "XF-016", "product_name": "美团到店·Coze 智能体搭建周末班", "category": "美团到店", "price": 0, "service_days": 2, "billing_cycle": "一次性", "platform": "美团到店", "audience": "周末学习的本地用户", "selling_point": "周末两天搭出智能体", "description": "美团到店周末班，两天完成 Coze 智能体搭建。"},
    {"product_code": "XF-017", "product_name": "美团到店·成人电脑+AI 综合次卡（8 次）", "category": "美团到店", "price": 0, "service_days": 60, "billing_cycle": "一次性", "platform": "美团到店", "audience": "成人再教育用户", "selling_point": "8 次综合学习次卡", "description": "成人电脑与 AI 综合次卡，8 次课。"},
    {"product_code": "XF-018", "product_name": "美团到店·AI 应用实操 4 次卡", "category": "美团到店", "price": 0, "service_days": 30, "billing_cycle": "一次性", "platform": "美团到店", "audience": "想实操 AI 应用的本地用户", "selling_point": "4 次实操卡", "description": "美团到店 AI 应用实操 4 次卡。"},
    {"product_code": "XF-019", "product_name": "美团到店·AI 职场提效 4 次卡", "category": "美团到店", "price": 0, "service_days": 30, "billing_cycle": "一次性", "platform": "美团到店", "audience": "职场提效需求用户", "selling_point": "4 次职场提效课", "description": "美团到店 AI 职场提效 4 次卡。"},
    {"product_code": "XF-020", "product_name": "B 端·企业 AI 培训（定制）", "category": "企业培训", "price": 3000, "service_days": 30, "billing_cycle": "一次性", "platform": "企业直销/转介绍", "audience": "政府/国企/中小企业培训负责人", "selling_point": "¥3000-50000 按规模定制", "description": "面向企业的 AI 应用培训，按规模与深度定制报价。"},
]
