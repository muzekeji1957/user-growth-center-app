# -*- coding: utf-8 -*-
"""生成离线大屏预览数据（与 Frappe 共用同一套 analytics 口径）。

产出 preview/mock_data.json，结构 = user_growth.api.get_growth_dashboard 的返回值，
因此离线大屏 HTML 直接消费它，无需 Frappe 环境。
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
# app 根目录下存在 python 包 user_growth（即 app_root/user_growth/），
# 因此把 app 根目录加入 sys.path 即可 import user_growth.*
sys.path.insert(0, ROOT)

from user_growth.seed.generator import build_records  # noqa: E402
from user_growth.analytics import build_dashboard_payload  # noqa: E402

OUT = os.path.join(HERE, "mock_data.json")


def main(n_customers=420):
    records = build_records(n_customers=n_customers)
    payload = build_dashboard_payload(records, months=13)
    payload["generated_at"] = "2026-10-15 16:00:00"
    payload["record_count"] = len(records)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    print("written:", OUT, "records:", len(records))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 420)
