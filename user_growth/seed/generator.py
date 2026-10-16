# -*- coding: utf-8 -*-
"""Mock 数据生成器（纯 Python，不依赖 Frappe）。

生成「用户服务开通/流失单据」的演示数据，特点：
    * 可复现：固定 random seed，每次生成结果一致，报表/大屏数字稳定。
    * 口径正确：每个客户先"新开通"再"续费/升级"，部分客户在后续月份"流失"，
      与 analytics.py 的新增/流失/净增口径完全对齐。
    * 真实锚点：产品、价格、区域、渠道均来自真实业务（内容工厂产品目录）。

被两处复用：
    * ``seed/mock_data.py``  -> 写入 Frappe（bench execute 调用）。
    * ``preview/generate_mock_data.py`` -> 写出离线 JSON 供大屏/报表预览。
"""

from __future__ import annotations

import datetime as _dt
import random

from .products import PRODUCTS

REGIONS = ["包头", "呼和浩特", "鄂尔多斯", "内蒙古其他", "全国线上"]
CHANNELS = ["公众号", "小红书", "抖音", "视频号", "美团到店", "闲鱼", "转介绍", "企业直销"]
CUSTOMER_TYPES = ["个人", "企业", "政府/国企"]
CHURN_REASONS = ["价格偏高", "效果不符预期", "服务到期未续", "转投竞品", "自身业务调整", "失联无响应", "产品下架", "其他"]
NPS_TYPES = ["未评估", "推荐者", "中立", "贬损者"]
SALES_OWNERS = ["user@muze.local", "sales2@muze.local", "sales3@muze.local"]

SURNAMES = list("赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜")
GIVEN = ["伟", "芳", "娜", "秀英", "敏", "静", "丽", "强", "磊", "军", "洋", "勇", "艳", "杰", "娟", "涛", "明", "超", "霞", "平"]
COMPANY_PREFIX = ["包头", "内蒙古", "草原", "黄河", "钢城", "鹿城", "北疆", "塞外"]
COMPANY_SUFFIX = ["科技", "商贸", "教育", "文化传媒", "网络", "智能", "咨询", "实业"]


def _random_name(rng):
    if rng.random() < 0.7:
        return rng.choice(SURNAMES) + rng.choice(GIVEN)
    return (
        rng.choice(COMPANY_PREFIX)
        + rng.choice(["", "市", "区"])
        + rng.choice(COMPANY_SUFFIX)
        + "有限公司"
    )


def _random_mobile(rng):
    return "1" + str(rng.randint(3, 9)) + "".join(str(rng.randint(0, 9)) for _ in range(9))


def build_records(n_customers=420, end_month=None, seed=20261015):
    """生成演示单据。

    :param n_customers: 客户数量（每个客户 1~4 张单据，420 客户 => 789 条单据）。
        2026-10-16 修正：默认值恢复为 420。交付文档 / 演示文档 / 离线预览 /
        大屏截图全部以「789 条单据、420 个客户」为口径，默认值必须与之死死锁住，
        否则文档里的数字和真机灌出来的数字会对不上。
    :param end_month: 数据截止月份 'YYYY-MM'，默认当前月
    :param seed: 随机种子（固定 -> 结果可复现）
    :return: list[dict]，字段与 User Service Record 对应
    """
    rng = random.Random(seed)
    today = _dt.date.today()
    end = (
        _dt.date(int(end_month[:4]), int(end_month[5:7]), 1)
        if end_month
        else _dt.date(today.year, today.month, 1)
    )
    # 数据窗口：截止月往前 12 个月
    window_start = _add_months(end, -11)
    months = [_add_months(window_start, i) for i in range(12)] + [end]
    month_strs = [m.strftime("%Y-%m-%d") for m in months]

    records = []
    used_mobiles = set()
    for i in range(n_customers):
        ctype = rng.choices(CUSTOMER_TYPES, weights=[0.6, 0.3, 0.1])[0]
        name = _random_name(rng)
        mobile = _random_mobile(rng)
        while mobile in used_mobiles:
            mobile = _random_mobile(rng)
        used_mobiles.add(mobile)
        customer_code = "C%08d" % (i + 1)

        # 客户首单月份（偏向近期，制造增长趋势）
        start_idx = rng.choices(range(len(months)), weights=[1, 1, 1, 2, 2, 3, 3, 4, 4, 5, 6, 7, 8])[0]
        prod = rng.choice(PRODUCTS)
        region = rng.choices(REGIONS, weights=[40, 18, 12, 10, 20])[0]
        channel = rng.choices(CHANNELS, weights=[20, 16, 16, 10, 12, 10, 10, 6])[0]
        owner = rng.choice(SALES_OWNERS)

        start_day = rng.randint(1, 27)
        start_date = _date_in_month(months[start_idx], start_day)
        amount = round(prod["price"] * rng.uniform(0.95, 1.15), 2)
        if prod["price"] == 0:
            amount = 0.0

        base = {
            "customer_name": name,
            "customer_code": customer_code,
            "customer_type": ctype,
            "mobile": mobile,
            "region": region,
            "channel": channel,
            "sales_owner": owner,
            "product_line": prod["category"],
            "product": prod["product_code"],
            "billing_cycle": prod["billing_cycle"],
            "activity_score": rng.randint(20, 100),
            "last_active_on": start_date.strftime("%Y-%m-%d"),
            "is_key_account": 1 if (prod["price"] >= 1999 and rng.random() < 0.4) else 0,
            "nps_type": rng.choices(NPS_TYPES, weights=[30, 35, 25, 10])[0],
            "remark": "演示数据",
        }

        # 首单：新开通
        records.append(_mk(base, "新开通", amount, start_date, prod, rng))

        # 续费/升级次数
        n_follow = rng.choices([0, 1, 1, 2, 2, 3], weights=[25, 25, 20, 15, 10, 5])[0]
        cur = start_idx
        for k in range(n_follow):
            nxt = cur + rng.randint(1, 3)
            if nxt >= len(months):
                break
            cur = nxt
            fdate = _date_in_month(months[cur], rng.randint(1, 27))
            if rng.random() < 0.25 and prod["price"] >= 399:
                stype = "升级"
                uprod = rng.choice([p for p in PRODUCTS if p["price"] > prod["price"]] or [prod])
                amount2 = round(uprod["price"] * rng.uniform(0.95, 1.1), 2)
                records.append(_mk(base, "升级", amount2, fdate, uprod, rng))
            else:
                stype = "续费"
                records.append(_mk(base, "续费", amount, fdate, prod, rng))

        # 流失（部分客户）
        churn_prob = 0.18 + 0.10 * (start_idx <= 2)  # 早期客户更易流失
        if rng.random() < churn_prob and len(records) > 0:
            churn_idx = min(cur + rng.randint(1, 3), len(months) - 1)
            if churn_idx > start_idx:
                cdate = _date_in_month(months[churn_idx], rng.randint(1, 27))
                reason = rng.choice(CHURN_REASONS)
                rec = _mk(base, "流失", 0.0, cdate, prod, rng)
                rec["churn_date"] = cdate.strftime("%Y-%m-%d")
                rec["churn_reason"] = reason
                rec["churn_detail"] = "演示流失：" + reason
                rec["is_winback"] = 1 if rng.random() < 0.6 else 0
                rec["winback_score"] = rng.randint(30, 90)
                rec["status"] = "已流失"
                records.append(rec)

    records.sort(key=lambda r: r.get("service_start") or "")
    return records


def _mk(base, service_type, amount, date, prod, rng):
    rec = dict(base)
    rec["service_type"] = service_type
    rec["status"] = "已流失" if service_type == "流失" else "有效"
    rec["amount"] = amount
    rec["service_start"] = date.strftime("%Y-%m-%d")
    end_d = date + _dt.timedelta(days=prod["service_days"] or 30)
    rec["service_end"] = end_d.strftime("%Y-%m-%d")
    rec["order_ref"] = "DEMO-%s-%04d" % (service_type, rng.randint(1000, 9999))
    rec["service_items"] = []
    return rec


def _date_in_month(month_first, day):
    # month_first: date with day=1
    ndays = _days_in_month(month_first.year, month_first.month)
    return _dt.date(month_first.year, month_first.month, min(day, ndays))


def _days_in_month(y, m):
    if m == 12:
        nxt = _dt.date(y + 1, 1, 1)
    else:
        nxt = _dt.date(y, m + 1, 1)
    return (nxt - _dt.date(y, m, 1)).days


def _add_months(d, delta):
    total = (d.year * 12 + (d.month - 1)) + delta
    y, m = total // 12, total % 12 + 1
    return _dt.date(y, m, 1)
