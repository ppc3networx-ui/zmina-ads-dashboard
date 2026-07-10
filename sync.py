"""
sync.py - тянет данные по продукту Zmina из Google Ads (read-only, LAST_30_DAYS)
и сохраняет компактный JSON для generate.py. Ничего не пишет в аккаунт.

Схема названий кампаний: Type_COUNTRY_LANG
(тип - первый токен, страна - токен сразу после типа).

Запуск: python3 sync.py
Требует: GOOGLE_ADS_DEVELOPER_TOKEN в окружении + настроенный ADC (см. gads.py).
"""
import json
import os
from datetime import datetime, timezone

from gads import get_client, run_search

# ---- Настройки продукта -------------------------------------------------
PRODUCT_KEY = "zmina"
PRODUCT_NAME = "Zmina"
CUSTOMER_ID = "1705189268"

# Аккаунт содержит только этот продукт -> фильтр по названию кампании не нужен.
# Если понадобится (аккаунт станет общим для нескольких продуктов), задать,
# например, "%zmina%".
CAMPAIGN_NAME_FILTER = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

CAMPAIGN_QUERY = """
    SELECT
        campaign.name,
        segments.date,
        metrics.cost_micros,
        metrics.impressions,
        metrics.clicks,
        metrics.conversions,
        metrics.conversions_value
    FROM campaign
    WHERE segments.date DURING LAST_30_DAYS
      AND metrics.impressions > 0
    ORDER BY campaign.name, segments.date
"""

# Без segments.date в SELECT - метрики агрегируются за весь период LAST_30_DAYS.
AD_GROUP_QUERY = """
    SELECT
        campaign.name,
        ad_group.name,
        metrics.cost_micros,
        metrics.impressions,
        metrics.clicks,
        metrics.conversions
    FROM ad_group
    WHERE segments.date DURING LAST_30_DAYS
      AND metrics.impressions > 0
    ORDER BY metrics.cost_micros DESC
    LIMIT 40
"""


def _mmdd(date_str: str) -> str:
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%m-%d")


def _country_from_name(name: str) -> str:
    """Страна = токен сразу после токена типа кампании (Type_COUNTRY_LANG).
    Кампании с дефолтным именем Google Ads (без "_", например
    "Local store visits and promotions-Performance Max-1") страну в названии
    не содержат - помечаем их отдельной меткой, а не роняем весь пайплайн."""
    parts = name.split("_")
    return parts[1] if len(parts) > 1 else "Не указана"


def _apply_name_filter(query: str) -> str:
    if not CAMPAIGN_NAME_FILTER:
        return query
    return query.replace(
        "WHERE segments.date",
        f"WHERE campaign.name LIKE '{CAMPAIGN_NAME_FILTER}' AND segments.date",
    )


def main():
    client = get_client()

    camp_rows = run_search(client, CUSTOMER_ID, _apply_name_filter(CAMPAIGN_QUERY))
    ag_rows = run_search(client, CUSTOMER_ID, _apply_name_filter(AD_GROUP_QUERY))

    # --- кампании и дни -----------------------------------------------
    raw = []
    camp_names = set()
    day_set = set()
    for r in camp_rows:
        name = r.campaign.name
        mmdd = _mmdd(r.segments.date)
        camp_names.add(name)
        day_set.add(mmdd)
        raw.append(
            (
                name,
                mmdd,
                r.metrics.cost_micros / 1_000_000,
                r.metrics.impressions,
                r.metrics.clicks,
                r.metrics.conversions,
                r.metrics.conversions_value,
            )
        )

    camps = sorted(camp_names)
    camp_idx = {c: i for i, c in enumerate(camps)}
    countries = [_country_from_name(c) for c in camps]

    days = sorted(day_set)
    day_idx = {d: i for i, d in enumerate(days)}

    rows = [
        [
            camp_idx[name],
            day_idx[mmdd],
            round(cost, 2),
            int(impr),
            int(clicks),
            round(conv, 2),
            round(cval, 2),
        ]
        for name, mmdd, cost, impr, clicks, conv, cval in raw
    ]

    # --- топ-40 групп объявлений по расходу -----------------------------
    groups = []
    for r in ag_rows:
        name = r.campaign.name
        if name not in camp_idx:
            camp_idx[name] = len(camps)
            camps.append(name)
            countries.append(_country_from_name(name))
        groups.append(
            [
                camp_idx[name],
                r.ad_group.name,
                round(r.metrics.cost_micros / 1_000_000, 2),
                int(r.metrics.impressions),
                int(r.metrics.clicks),
                round(r.metrics.conversions, 2),
            ]
        )

    payload = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "days": days,
        "camps": camps,
        "countries": countries,
        "rows": rows,
        "groups": groups,
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    out_path = os.path.join(DATA_DIR, f"compact_{PRODUCT_KEY}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

    _update_manifest()
    print(
        f"OK: {out_path} "
        f"({len(rows)} строк, {len(camps)} кампаний, {len(groups)} групп объявлений)"
    )


def _update_manifest():
    manifest_path = os.path.join(DATA_DIR, "manifest.json")
    manifest = []
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            try:
                manifest = json.load(f)
            except json.JSONDecodeError:
                manifest = []
    manifest = [m for m in manifest if m.get("key") != PRODUCT_KEY]
    manifest.append(
        {
            "key": PRODUCT_KEY,
            "name": PRODUCT_NAME,
            "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
    )
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
