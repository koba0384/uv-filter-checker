import re
import unicodedata
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="UV防御剤チェッカー", layout="wide")

# ========= 帯域定義 =========
BAND_DEFS = [
    {"label": "UVB", "start": 280, "end": 320, "color": "rgba(102, 178, 255, 0.28)"},
    {"label": "UVA", "start": 320, "end": 340, "color": "rgba(170, 220, 255, 0.28)"},
    {"label": "ロングUVA", "start": 340, "end": 400, "color": "rgba(255, 204, 102, 0.28)"},
]

ABSORBER_COLOR = "#1f77b4"   # 紫外線吸収剤
SCATTER_COLOR = "#6c757d"    # 紫外線散乱剤

# ========= 紫外線防御剤辞書 =========
UV_FILTERS = [
    {
        "name_jp": "メトキシケイヒ酸エチルヘキシル",
        "name_en": "Octinoxate",
        "short_label": "Octinoxate",
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
        "short_label": "Octocrylene",
        "kind": "紫外線吸収剤",
        "aliases": ["オクトクリレン", "octocrylene"],
        "ranges": [(290, 360)],
        "memo": "UVB中心、UVAにも一部",
    },
    {
        "name_jp": "ジエチルアミノヒドロキシベンゾイル安息香酸ヘキシル",
        "name_en": "DHHB / Uvinul A Plus",
        "short_label": "DHHB",
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
        "short_label": "BEMT",
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
        "short_label": "MBBT",
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
        "short_label": "PBSA",
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
        "short_label": "EHT",
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
        "name_en": "Drometrizole Trisiloxane / Mexoryl XL",
        "short_label": "Mexoryl XL",
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
        "short_label": "Mexoryl SX",
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
        "short_label": "Avobenzone",
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
        "short_label": "酸化亜鉛",
        "kind": "紫外線散乱剤",
        "aliases": ["酸化亜鉛", "zinc oxide"],
        "ranges": [(280, 400)],
        "memo": "広帯域",
    },
    {
        "name_jp": "酸化チタン",
        "name_en": "Titanium Dioxide",
        "short_label": "酸化チタン",
        "kind": "紫外線散乱剤",
        "aliases": ["酸化チタン", "titanium dioxide"],
        "ranges": [(280, 340)],
        "memo": "UVB〜UVA短波長側",
    },
]

# ========= ユーティリティ =========
def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    text = re.sub(r"\s+", "", text)
    return text

def overlap(start1, end1, start2, end2):
    return max(start1, start2) < min(end1, end2)

def covered_labels(ranges):
    labels = []
    for band in BAND_DEFS:
        if any(overlap(start, end, band["start"], band["end"]) for start, end in ranges):
            labels.append(band["label"])
    return " / ".join(labels)

def extract_uv_filters(text: str):
    norm = normalize(text)
    found = []

    for item in UV_FILTERS:
        hit_positions = []
        for alias in item["aliases"]:
            alias_norm = normalize(alias)
            pos = norm.find(alias_norm)
            if pos != -1:
                hit_positions.append(pos)

        if hit_positions:
            item_copy = item.copy()
            item_copy["_first_pos"] = min(hit_positions)
            found.append(item_copy)

    found.sort(key=lambda x: x["_first_pos"])

    unique = []
    seen = set()
    for item in found:
        if item["name_jp"] not in seen:
            unique.append(item)
            seen.add(item["name_jp"])

    return unique

def plot_filters(found, product_name=""):
    fig = go.Figure()

    # 背景帯
    for band in BAND_DEFS:
        fig.add_vrect(
            x0=band["start"],
            x1=band["end"],
            fillcolor=band["color"],
            line_width=0,
            layer="below",
        )
        fig.add_annotation(
            x=(band["start"] + band["end"]) / 2,
            y=1.08,
            yref="paper",
            text=f"<b>{band['label']}</b>",
            showarrow=False,
            font=dict(size=13),
        )

    short_names = [item["short_label"] for item in found]

    for item in found:
        color = ABSORBER_COLOR if item["kind"] == "紫外線吸収剤" else SCATTER_COLOR
        for start, end in item["ranges"]:
            fig.add_trace(
                go.Bar(
                    x=[end - start],
                    y=[item["short_label"]],
                    base=[start],
                    orientation="h",
                    marker=dict(color=color),
                    hovertemplate=(
                        f"<b>{item['name_jp']}</b><br>"
                        f"{item['name_en']}<br>"
                        f"{item['kind']}<br>"
                        f"{start}–{end} nm<br>"
                        f"{item['memo']}<extra></extra>"
                    ),
                    showlegend=False,
                )
            )

    # 凡例用ダミー
    fig.add_trace(
        go.Bar(
            x=[0],
            y=[None],
            name="紫外線吸収剤",
            marker=dict(color=ABSORBER_COLOR),
            showlegend=True,
        )
    )
    fig.add_trace(
        go.Bar(
            x=[0],
            y=[None],
            name="紫外線散乱剤",
            marker=dict(color=SCATTER_COLOR),
            showlegend=True,
        )
    )

    title = "紫外線防御剤のカバー領域"
    if product_name.strip():
        title = f"{product_name.strip()} の紫外線防御剤カバー領域"

    fig.update_layout(
        title=title,
        barmode="overlay",
        xaxis=dict(
            title="波長 (nm)",
            range=[280, 400],
            dtick=20,
            showgrid=True,
            gridcolor="rgba(0,0,0,0.08)",
            zeroline=False,
        ),
        yaxis=dict(
            title="",
            autorange="reversed",
            automargin=True,
            categoryorder="array",
            categoryarray=short_names,
            tickfont=dict(size=13),
        ),
        height=max(430, 72 * len(found) + 130),
        margin=dict(l=110, r=20, t=95, b=30),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="right",
            x=1,
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )

    return fig

# ========= UI =========
st.title("日焼け止め 紫外線防御剤チェッカー")

st.write("全成分を貼ると、紫外線防御剤を抽出して種類数とカバー領域を表示します。")

product_name = st.text_input(
    "商品名（任意）",
    placeholder="例: by365 パウダリーUVジェル"
)

sample = (
    "水、エタノール、メトキシケイヒ酸エチルヘキシル、"
    "ビスエチルヘキシルオキシフェノールメトキシフェニルトリアジン、"
    "ジエチルアミノヒドロキシベンゾイル安息香酸ヘキシル、"
    "オクトクリレン"
)

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

        col1, col2 = st.columns(2)
        with col1:
            st.metric("紫外線吸収剤", absorber_count)
        with col2:
            st.metric("紫外線散乱剤", scatter_count)

        fig = plot_filters(found, product_name)
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False},
        )

st.caption("※ カバー領域は実務用の簡易表示です。厳密な吸収スペクトルそのものではありません。")
st.caption("※ 効果の強さは配合量・製剤設計・SPF/PA試験結果で大きく変わるため、この図だけでは断定できません。")
st.caption("※ 商品名だけで自動的に全成分を取得する機能は、現時点ではまだ入っていません。")
