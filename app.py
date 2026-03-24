import re
import unicodedata
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import japanize_matplotlib
from matplotlib.patches import Patch

st.set_page_config(page_title="UV防御剤チェッカー", layout="wide")

# ====== 帯域定義 ======
BAND_DEFS = [
    {"label": "UVB", "start": 280, "end": 320, "color": "#8ecae6"},
    {"label": "UVA", "start": 320, "end": 340, "color": "#bde0fe"},
    {"label": "ロングUVA", "start": 340, "end": 400, "color": "#ffd6a5"},
]

ABSORBER_COLOR = "#1f77b4"   # 吸収剤
SCATTER_COLOR = "#6c757d"    # 散乱剤

# ====== 紫外線防御剤辞書 ======
UV_FILTERS = [
    {
        "name_jp": "メトキシケイヒ酸エチルヘキシル",
        "name_en": "Octinoxate",
        "kind": "紫外線吸収剤",
        "aliases": [
            "メトキシケイヒ酸エチルヘキシル",
            "ethylhexyl methoxycinnamate",
            "octinoxate",
            "octyl methoxycinnamate",
        ],
        "ranges": [(280, 320)],
        "memo": "UVB中心",
    },
    {
        "name_jp": "オクトクリレン",
        "name_en": "Octocrylene",
        "kind": "紫外線吸収剤",
        "aliases": ["オクトクリレン", "octocrylene"],
        "ranges": [(290, 360)],
        "memo": "UVB中心、UVAにも一部",
    },
    {
        "name_jp": "ジエチルアミノヒドロキシベンゾイル安息香酸ヘキシル",
        "name_en": "DHHB / Uvinul A Plus",
        "kind": "紫外線吸収剤",
        "aliases": [
            "ジエチルアミノヒドロキシベンゾイル安息香酸ヘキシル",
            "diethylamino hydroxybenzoyl hexyl benzoate",
            "dhhb",
            "uvinul a plus",
        ],
        "ranges": [(320, 400)],
        "memo": "UVA〜ロングUVA中心",
    },
    {
        "name_jp": "ビスエチルヘキシルオキシフェノールメトキシフェニルトリアジン",
        "name_en": "BEMT / Tinosorb S",
        "kind": "紫外線吸収剤",
        "aliases": [
            "ビスエチルヘキシルオキシフェノールメトキシフェニルトリアジン",
            "bis-ethylhexyloxyphenol methoxyphenyl triazine",
            "bisethylhexyloxyphenol methoxyphenyl triazine",
            "bemotrizinol",
            "bemt",
            "tinosorb s",
        ],
        "ranges": [(280, 400)],
        "memo": "広帯域",
    },
    {
        "name_jp": "メチレンビスベンゾトリアゾリルテトラメチルブチルフェノール",
        "name_en": "MBBT / Tinosorb M",
        "kind": "紫外線吸収剤",
        "aliases": [
            "メチレンビスベンゾトリアゾリルテトラメチルブチルフェノール",
            "methylene bis-benzotriazolyl tetramethylbutylphenol",
            "methylene bis benzotriazolyl tetramethylbutylphenol",
            "bisoctrizole",
            "mbbt",
            "tinosorb m",
        ],
        "ranges": [(280, 400)],
        "memo": "広帯域",
    },
    {
        "name_jp": "フェニルベンズイミダゾールスルホン酸",
        "name_en": "Ensulizole / PBSA",
        "kind": "紫外線吸収剤",
        "aliases": [
            "フェニルベンズイミダゾールスルホン酸",
            "phenylbenzimidazole sulfonic acid",
            "ensulizole",
            "pbsa",
        ],
        "ranges": [(280, 340)],
        "memo": "UVB〜UVA短波長側",
    },
    {
        "name_jp": "エチルヘキシルトリアゾン",
        "name_en": "Ethylhexyl Triazone",
        "kind": "紫外線吸収剤",
        "aliases": [
            "エチルヘキシルトリアゾン",
            "ethylhexyl triazone",
            "uvinul t 150",
        ],
        "ranges": [(280, 320)],
        "memo": "UVB中心",
    },
    {
        "name_jp": "ドロメトリゾールトリシロキサン",
        "name_en": "Drometrizole Trisiloxane",
        "kind": "紫外線吸収剤",
        "aliases": [
            "ドロメトリゾールトリシロキサン",
            "drometrizole trisiloxane",
            "mexoryl xl",
        ],
        "ranges": [(290, 360)],
        "memo": "UVB〜UVA",
    },
    {
        "name_jp": "テレフタリリデンジカンフルスルホン酸",
        "name_en": "Ecamsule / Mexoryl SX",
        "kind": "紫外線吸収剤",
        "aliases": [
            "テレフタリリデンジカンフルスルホン酸",
            "terephthalylidene dicamphor sulfonic acid",
            "ecamsule",
            "mexoryl sx",
        ],
        "ranges": [(320, 390)],
        "memo": "UVA中心",
    },
    {
        "name_jp": "t-ブチルメトキシジベンゾイルメタン",
        "name_en": "Avobenzone",
        "kind": "紫外線吸収剤",
        "aliases": [
            "t-ブチルメトキシジベンゾイルメタン",
            "ｔ-ブチルメトキシジベンゾイルメタン",
            "butyl methoxydibenzoylmethane",
            "avobenzone",
        ],
        "ranges": [(320, 400)],
        "memo": "UVA〜ロングUVA中心",
    },
    {
        "name_jp": "酸化亜鉛",
        "name_en": "Zinc Oxide",
        "kind": "紫外線散乱剤",
        "aliases": ["酸化亜鉛", "zinc oxide"],
        "ranges": [(280, 400)],
        "memo": "広帯域",
    },
    {
        "name_jp": "酸化チタン",
        "name_en": "Titanium Dioxide",
        "kind": "紫外線散乱剤",
        "aliases": ["酸化チタン", "titanium dioxide"],
        "ranges": [(280, 340)],
        "memo": "UVB〜UVA短波長側",
    },
]

def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    text = re.sub(r"\s+", "", text)
    return text

def extract_uv_filters(text: str):
    norm = normalize(text)
    found = []
    seen = set()

    for item in UV_FILTERS:
        for alias in item["aliases"]:
            if normalize(alias) in norm:
                key = item["name_jp"]
                if key not in seen:
                    found.append(item)
                    seen.add(key)
                break
    return found

def overlap(start1, end1, start2, end2):
    return max(start1, start2) < min(end1, end2)

def covered_labels(ranges):
    labels = []
    for band in BAND_DEFS:
        band_hit = False
        for start, end in ranges:
            if overlap(start, end, band["start"], band["end"]):
                band_hit = True
                break
        if band_hit:
            labels.append(band["label"])
    return " / ".join(labels)

def plot_filters(found, product_name=""):
    if not found:
        return None

    fig_h = max(4, 0.7 * len(found) + 2.5)
    fig, ax = plt.subplots(figsize=(12, fig_h))

    # 背景帯
    for band in BAND_DEFS:
        ax.axvspan(
            band["start"],
            band["end"],
            color=band["color"],
            alpha=0.35,
            zorder=0
        )
        ax.text(
            (band["start"] + band["end"]) / 2,
            1.02,
            band["label"],
            transform=ax.get_xaxis_transform(),
            ha="center",
            va="bottom",
            fontsize=12,
            fontweight="bold"
        )

    y_positions = list(range(len(found)))
    y_labels = [item["name_jp"] for item in found]

    for y, item in zip(y_positions, found):
        bar_color = ABSORBER_COLOR if item["kind"] == "紫外線吸収剤" else SCATTER_COLOR
        for start, end in item["ranges"]:
            ax.broken_barh(
                [(start, end - start)],
                (y - 0.35, 0.7),
                facecolors=bar_color,
                edgecolors="none",
                zorder=2
            )

    ax.set_xlim(280, 400)
    ax.set_ylim(-0.5, len(found) - 0.5)
    ax.set_yticks(y_positions)
    ax.set_yticklabels(y_labels, fontsize=10)
    ax.invert_yaxis()
    ax.set_xlabel("波長 (nm)")
    ax.set_ylabel("")
    ax.grid(axis="x", linestyle="--", alpha=0.3)

    title = "紫外線防御剤のカバー領域"
    if product_name.strip():
        title = f"{product_name.strip()} の紫外線防御剤カバー領域"
    ax.set_title(title, fontsize=14, pad=20)

    legend_handles = [
        Patch(facecolor=ABSORBER_COLOR, label="紫外線吸収剤"),
        Patch(facecolor=SCATTER_COLOR, label="紫外線散乱剤"),
    ]
    ax.legend(handles=legend_handles, loc="lower right")

    plt.tight_layout()
    return fig

# ====== UI ======
st.title("日焼け止め 紫外線防御剤チェッカー")

product_name = st.text_input("商品名（任意）", placeholder="例: by365 パウダリーUVジェル")

sample = "水、エタノール、メトキシケイヒ酸エチルヘキシル、ビスエチルヘキシルオキシフェノールメトキシフェニルトリアジン、ジエチルアミノヒドロキシベンゾイル安息香酸ヘキシル、オクトクリレン"

ingredients = st.text_area(
    "全成分をここに貼ってください",
    value=sample,
    height=180
)

if st.button("解析する"):
    found = extract_uv_filters(ingredients)

    if product_name.strip():
        st.subheader(f"{product_name.strip()} の解析結果")
    else:
        st.subheader("解析結果")

    st.write(f"**見つかった紫外線防御剤: {len(found)}種類**")

    if not found:
        st.warning("紫外線防御剤が見つかりませんでした。")
    else:
        rows = []
        for item in found:
            rows.append({
                "成分名": item["name_jp"],
                "英名": item["name_en"],
                "分類": item["kind"],
                "カバー領域": covered_labels(item["ranges"]),
                "メモ": item["memo"],
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)

        absorber_count = sum(1 for x in found if x["kind"] == "紫外線吸収剤")
        scatter_count = sum(1 for x in found if x["kind"] == "紫外線散乱剤")
        st.write(f"吸収剤: **{absorber_count}** / 散乱剤: **{scatter_count}**")

        fig = plot_filters(found, product_name)
        st.pyplot(fig, use_container_width=True)

st.caption("※ カバー領域は実務用の簡易表示です。厳密な吸収スペクトルそのものではありません。")
st.caption("※ 効果の強さは配合量・製剤設計・SPF/PA試験結果で大きく変わるため、この図だけでは断定できません。")
