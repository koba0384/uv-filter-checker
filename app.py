import re
import unicodedata
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

st.set_page_config(page_title="UV防御剤チェッカー", layout="wide")

BANDS = {
    "UVB": (280, 320),
    "UVA": (320, 400),
    "ロングUVA": (340, 400),
}

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
    },
    {
        "name_jp": "オクトクリレン",
        "name_en": "Octocrylene",
        "kind": "紫外線吸収剤",
        "aliases": ["オクトクリレン", "octocrylene"],
        "ranges": [(290, 360)],
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
    },
    {
        "name_jp": "ビスエチルヘキシルオキシフェノールメトキシフェニルトリアジン",
        "name_en": "BEMT / Tinosorb S",
        "kind": "紫外線吸収剤",
        "aliases": [
            "ビスエチルヘキシルオキシフェノールメトキシフェニルトリアジン",
            "bis-ethylhexyloxyphenol methoxyphenyl triazine",
            "bemotrizinol",
            "bemt",
            "tinosorb s",
        ],
        "ranges": [(280, 400)],
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
    },
    {
        "name_jp": "酸化亜鉛",
        "name_en": "Zinc Oxide",
        "kind": "紫外線散乱剤",
        "aliases": ["酸化亜鉛", "zinc oxide"],
        "ranges": [(280, 400)],
    },
    {
        "name_jp": "酸化チタン",
        "name_en": "Titanium Dioxide",
        "kind": "紫外線散乱剤",
        "aliases": ["酸化チタン", "titanium dioxide"],
        "ranges": [(280, 340)],
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

def covered_labels(ranges):
    labels = set()
    for start, end in ranges:
        if start < 320 and end > 280:
            labels.add("UVB")
        if start < 400 and end > 320:
            labels.add("UVA")
        if start < 400 and end > 340:
            labels.add("ロングUVA")
    order = ["UVB", "UVA", "ロングUVA"]
    return " / ".join([x for x in order if x in labels])

def plot_filters(found):
    if not found:
        return None

    fig_h = max(3, 0.7 * len(found) + 2)
    fig, ax = plt.subplots(figsize=(12, fig_h))

    ax.axvspan(280, 320, alpha=0.12)
    ax.axvspan(320, 400, alpha=0.08)
    ax.axvspan(340, 400, alpha=0.10)

    ax.text(300, len(found) + 0.1, "UVB", ha="center", va="bottom", fontsize=11)
    ax.text(360, len(found) + 0.1, "UVA", ha="center", va="bottom", fontsize=11)
    ax.text(370, len(found) + 0.5, "ロングUVA", ha="center", va="bottom", fontsize=11)

    y_positions = list(range(len(found)))

    for y, item in zip(y_positions, found):
        for start, end in item["ranges"]:
            ax.broken_barh([(start, end - start)], (y - 0.35, 0.7))
        ax.text(281, y, item["name_jp"], va="center", fontsize=10)

    ax.set_xlim(280, 400)
    ax.set_ylim(-1, len(found))
    ax.set_yticks([])
    ax.set_xlabel("波長 (nm)")
    ax.set_title("紫外線防御剤のカバー領域")
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    plt.tight_layout()
    return fig

st.title("日焼け止め 紫外線防御剤チェッカー")
st.write("全成分を貼ると、紫外線防御剤を抜き出して種類数とカバー領域を表示します。")

sample = "水、エタノール、メトキシケイヒ酸エチルヘキシル、ビスエチルヘキシルオキシフェノールメトキシフェニルトリアジン、ジエチルアミノヒドロキシベンゾイル安息香酸ヘキシル、オクトクリレン"

ingredients = st.text_area("全成分をここに貼ってください", value=sample, height=180)

if st.button("解析する"):
    found = extract_uv_filters(ingredients)

    st.subheader(f"見つかった紫外線防御剤: {len(found)}種類")

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
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)

        fig = plot_filters(found)
        st.pyplot(fig)

st.caption("※ カバー領域は実務用の簡易表示です。厳密な吸収スペクトルそのものではありません。")
