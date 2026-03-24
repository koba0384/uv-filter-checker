import re
import unicodedata
import csv
from io import StringIO
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="UV防御剤チェッカー", layout="wide")

st.markdown(
    """
    <style>
    .stApp { background: #ffffff; }
    .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1080px; }
    h1, h2, h3 { color: #3f3a36; letter-spacing: 0.01em; }
    .soft-card {
        padding: 0.9rem 1rem;
        background: #ffffff;
        border: 1px solid #ebe5dc;
        border-radius: 16px;
        color: #5a554f;
    }
    div[data-testid="stTextArea"] textarea { background-color: #fffdf9 !important; }
    div[data-testid="stDataFrame"] { border-radius: 14px; overflow: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

BAND_DEFS = [
    {"label": "UVB", "start": 280, "end": 320, "color": "rgba(88, 163, 255, 0.16)"},
    {"label": "UVA", "start": 320, "end": 340, "color": "rgba(255, 170, 92, 0.16)"},
    {"label": "ロングUVA", "start": 340, "end": 400, "color": "rgba(255, 107, 107, 0.14)"},
]

ABSORBER_FILL = "#7E848C"
ABSORBER_LINE = "#686E76"
SCATTER_FILL = "#F7F4EE"
SCATTER_LINE = "#B8B1A6"

PLOT_BG = "#FFFCF8"
GRID_COLOR = "rgba(120,120,120,0.10)"
AXIS_COLOR = "#DAD2C7"
TEXT_COLOR = "#4B4741"

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
        "stability": 1,
    },
    {
        "name_jp": "オクトクリレン",
        "name_en": "Octocrylene",
        "short_label": "Octocrylene",
        "kind": "紫外線吸収剤",
        "aliases": ["オクトクリレン", "octocrylene"],
        "ranges": [(290, 360)],
        "memo": "UVB中心、UVAにも一部",
        "stability": 2,
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
        "stability": 4,
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
        "stability": 5,
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
        "stability": 5,
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
        "stability": 2,
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
        "stability": 4,
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
        "stability": 4,
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
        "stability": 4,
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
        "stability": 1,
    },
    {
        "name_jp": "酸化亜鉛",
        "name_en": "Zinc Oxide",
        "short_label": "酸化亜鉛",
        "kind": "紫外線散乱剤",
        "aliases": ["酸化亜鉛", "zinc oxide"],
        "ranges": [(280, 400)],
        "memo": "広帯域",
        "stability": 5,
    },
    {
        "name_jp": "酸化チタン",
        "name_en": "Titanium Dioxide",
        "short_label": "酸化チタン",
        "kind": "紫外線散乱剤",
        "aliases": ["酸化チタン", "titanium dioxide"],
        "ranges": [(280, 340)],
        "memo": "UVB〜UVA短波長側",
        "stability": 4,
    },
]

if "manual_product_name" not in st.session_state:
    st.session_state["manual_product_name"] = ""
if "manual_brand" not in st.session_state:
    st.session_state["manual_brand"] = ""
if "manual_spf" not in st.session_state:
    st.session_state["manual_spf"] = ""
if "manual_pa" not in st.session_state:
    st.session_state["manual_pa"] = ""
if "manual_ingredients" not in st.session_state:
    st.session_state["manual_ingredients"] = ""
if "manual_notes" not in st.session_state:
    st.session_state["manual_notes"] = ""

def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").lower()
    text = re.sub(r"\s+", "", text)
    return text

def merge_ranges(ranges):
    if not ranges:
        return []
    sorted_ranges = sorted(ranges, key=lambda x: x[0])
    merged = [list(sorted_ranges[0])]
    for start, end in sorted_ranges[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(s, e) for s, e in merged]

def clip_ranges_to_band(ranges, band_start, band_end):
    clipped = []
    for start, end in ranges:
        s = max(start, band_start)
        e = min(end, band_end)
        if s < e:
            clipped.append((s, e))
    return merge_ranges(clipped)

def coverage_width(ranges, band_start, band_end):
    return sum(e - s for s, e in clip_ranges_to_band(ranges, band_start, band_end))

def covered_labels(ranges):
    labels = []
    for band in BAND_DEFS:
        if coverage_width(ranges, band["start"], band["end"]) > 0:
            labels.append(band["label"])
    return " / ".join(labels)

def extract_uv_filters(text: str):
    norm = normalize(text)
    found = []
    for item in UV_FILTERS:
        positions = []
        for alias in item["aliases"]:
            alias_norm = normalize(alias)
            pos = norm.find(alias_norm)
            if pos != -1:
                positions.append(pos)
        if positions:
            copied = dict(item)
            copied["_first_pos"] = min(positions)
            found.append(copied)
    found.sort(key=lambda x: x["_first_pos"])
    unique = []
    seen = set()
    for item in found:
        if item["name_jp"] not in seen:
            unique.append(item)
            seen.add(item["name_jp"])
    return unique

def score_analysis(found):
    all_ranges = []
    for item in found:
        all_ranges.extend(item["ranges"])

    uvb_width = coverage_width(all_ranges, 280, 320)
    uva_width = coverage_width(all_ranges, 320, 340)
    long_uva_width = coverage_width(all_ranges, 340, 400)

    uvb_score = round(25 * (uvb_width / 40)) if uvb_width else 0
    uva_score = round(20 * (uva_width / 20)) if uva_width else 0
    long_uva_score = round(25 * (long_uva_width / 60)) if long_uva_width else 0

    diversity_score = min(10, len(found) * 2)
    stability_score = min(10, round(sum(item.get("stability", 0) for item in found) / 2))
    broad_count = sum(1 for item in found if len(set(covered_labels(item["ranges"]).split(" / "))) == 3)
    broad_score = 5 if broad_count >= 1 else 0

    kinds = {item["kind"] for item in found}
    type_score = 5 if len(kinds) == 2 else (3 if len(kinds) == 1 and found else 0)

    total = min(
        100,
        uvb_score + uva_score + long_uva_score + diversity_score + stability_score + broad_score + type_score
    )

    band_summary = {
        "UVB": f"{int(uvb_width)}/40 nm",
        "UVA": f"{int(uva_width)}/20 nm",
        "ロングUVA": f"{int(long_uva_width)}/60 nm",
    }

    return {
        "total": total,
        "uvb_score": uvb_score,
        "uva_score": uva_score,
        "long_uva_score": long_uva_score,
        "diversity_score": diversity_score,
        "stability_score": stability_score,
        "broad_score": broad_score,
        "type_score": type_score,
        "band_summary": band_summary,
    }

def build_found_df(found):
    rows = []
    for item in found:
        rows.append({
            "成分名": item["name_jp"],
            "英名": item["name_en"],
            "分類": item["kind"],
            "カバー領域": covered_labels(item["ranges"]),
            "メモ": item["memo"],
        })
    return pd.DataFrame(rows)

def plot_filters(found, title_text="紫外線防御剤のカバー領域"):
    fig = go.Figure()

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
            y=1.03,
            yref="paper",
            text=f"<b>{band['label']}</b>",
            showarrow=False,
            font=dict(size=12, color=TEXT_COLOR),
        )

    short_names = [item["short_label"] for item in found]

    for item in found:
        fill_color = ABSORBER_FILL if item["kind"] == "紫外線吸収剤" else SCATTER_FILL
        line_color = ABSORBER_LINE if item["kind"] == "紫外線吸収剤" else SCATTER_LINE

        for start, end in item["ranges"]:
            fig.add_trace(
                go.Bar(
                    x=[end - start],
                    y=[item["short_label"]],
                    base=[start],
                    orientation="h",
                    marker=dict(
                        color=fill_color,
                        line=dict(color=line_color, width=1.2),
                    ),
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

    fig.add_trace(
        go.Bar(
            x=[0],
            y=[None],
            name="紫外線吸収剤",
            marker=dict(color=ABSORBER_FILL, line=dict(color=ABSORBER_LINE, width=1.2)),
            showlegend=True,
        )
    )
    fig.add_trace(
        go.Bar(
            x=[0],
            y=[None],
            name="紫外線散乱剤",
            marker=dict(color=SCATTER_FILL, line=dict(color=SCATTER_LINE, width=1.2)),
            showlegend=True,
        )
    )

    fig.update_layout(
        title=title_text,
        barmode="overlay",
        xaxis=dict(
            title="波長 (nm)",
            range=[280, 400],
            dtick=20,
            showgrid=True,
            gridcolor=GRID_COLOR,
            zeroline=False,
            showline=True,
            linecolor=AXIS_COLOR,
            tickfont=dict(color=TEXT_COLOR),
            title_font=dict(color=TEXT_COLOR),
        ),
        yaxis=dict(
            title="",
            autorange="reversed",
            automargin=True,
            categoryorder="array",
            categoryarray=short_names,
            tickfont=dict(size=13, color=TEXT_COLOR),
            showline=False,
        ),
        height=max(430, 74 * len(found) + 130),
        margin=dict(l=115, r=18, t=52, b=95),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.18,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(255,255,255,0)",
            font=dict(color=TEXT_COLOR),
        ),
        plot_bgcolor=PLOT_BG,
        paper_bgcolor=PLOT_BG,
        font=dict(
            family="-apple-system, BlinkMacSystemFont, 'Hiragino Sans', 'Yu Gothic', sans-serif",
            color=TEXT_COLOR,
        ),
    )

    return fig

def make_score_chart(score_dict, title_text="参考スコア内訳"):
    labels = ["UVB", "UVA", "ロングUVA", "種類数", "安定性目安", "広帯域", "剤タイプ"]
    values = [
        score_dict["uvb_score"],
        score_dict["uva_score"],
        score_dict["long_uva_score"],
        score_dict["diversity_score"],
        score_dict["stability_score"],
        score_dict["broad_score"],
        score_dict["type_score"],
    ]
    colors = [
        "rgba(88, 163, 255, 0.70)",
        "rgba(255, 170, 92, 0.70)",
        "rgba(255, 107, 107, 0.70)",
        "rgba(145, 145, 145, 0.70)",
        "rgba(145, 145, 145, 0.55)",
        "rgba(145, 145, 145, 0.42)",
        "rgba(145, 145, 145, 0.32)",
    ]

    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker=dict(color=colors),
            text=values,
            textposition="outside",
            hovertemplate="%{y}: %{x}点<extra></extra>",
        )
    )
    fig.update_layout(
        title=title_text,
        xaxis=dict(range=[0, 25], showgrid=True, gridcolor=GRID_COLOR, zeroline=False),
        yaxis=dict(autorange="reversed"),
        margin=dict(l=40, r=20, t=50, b=20),
        height=360,
        plot_bgcolor=PLOT_BG,
        paper_bgcolor=PLOT_BG,
        font=dict(
            family="-apple-system, BlinkMacSystemFont, 'Hiragino Sans', 'Yu Gothic', sans-serif",
            color=TEXT_COLOR,
        ),
    )
    return fig

@st.cache_data
def load_product_db():
    path = Path("products.csv")
    columns = ["product_name", "brand", "spf", "pa", "ingredients", "notes"]

    if not path.exists():
        return pd.DataFrame(columns=columns)

    try:
        df = pd.read_csv(path)
    except Exception:
        return pd.DataFrame(columns=columns)

    for col in columns:
        if col not in df.columns:
            df[col] = ""

    df = df[columns].fillna("")
    df = df[
        (df["product_name"].astype(str).str.strip() != "")
        | (df["ingredients"].astype(str).str.strip() != "")
    ].reset_index(drop=True)

    return df

def filter_product_db(df, query):
    if df.empty:
        return df
    if not query.strip():
        return df

    q = normalize(query)
    mask = (
        df["product_name"].astype(str).apply(normalize).str.contains(q, regex=False)
        | df["brand"].astype(str).apply(normalize).str.contains(q, regex=False)
    )
    return df[mask].reset_index(drop=True)

def make_csv_row(product_name, brand, spf, pa, ingredients, notes):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([product_name, brand, spf, pa, ingredients, notes])
    return output.getvalue().strip("\r\n")

def render_analysis_block(product_name, brand, spf, pa, ingredients, notes):
    ingredients = (ingredients or "").strip()
    if not ingredients:
        st.warning("全成分が空です。")
        return

    found = extract_uv_filters(ingredients)
    score = score_analysis(found)

    title = product_name.strip() if str(product_name).strip() else "解析結果"
    st.subheader(title)

    meta_parts = []
    if brand:
        meta_parts.append(f"ブランド: {brand}")
    if spf:
        meta_parts.append(f"SPF: {spf}")
    if pa:
        meta_parts.append(f"PA: {pa}")
    if notes:
        meta_parts.append(f"メモ: {notes}")

    if meta_parts:
        st.caption(" / ".join(meta_parts))

    st.write(f"**見つかった紫外線防御剤: {len(found)}種類**")

    if not found:
        st.warning("紫外線防御剤が見つかりませんでした。")
        return

    absorber_count = sum(1 for x in found if x["kind"] == "紫外線吸収剤")
    scatter_count = sum(1 for x in found if x["kind"] == "紫外線散乱剤")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("参考スコア", f'{score["total"]}/100')
    with c2:
        st.metric("紫外線吸収剤", absorber_count)
    with c3:
        st.metric("紫外線散乱剤", scatter_count)

    st.dataframe(build_found_df(found), use_container_width=True)

    left, right = st.columns([1.35, 1])
    with left:
        fig = plot_filters(found, f"{title} のカバー領域")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with right:
        score_fig = make_score_chart(score)
        st.plotly_chart(score_fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown(
            f"""
            <div class="soft-card">
            <b>参考スコア内訳</b><br>
            UVB: {score["uvb_score"]}点（{score["band_summary"]["UVB"]}）<br>
            UVA: {score["uva_score"]}点（{score["band_summary"]["UVA"]}）<br>
            ロングUVA: {score["long_uva_score"]}点（{score["band_summary"]["ロングUVA"]}）<br>
            種類数: {score["diversity_score"]}点<br>
            安定性目安: {score["stability_score"]}点<br>
            広帯域: {score["broad_score"]}点<br>
            剤タイプ: {score["type_score"]}点
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.expander("全成分を表示"):
        st.write(ingredients)

def make_comparison_summary(df, selected_names):
    rows = []
    for name in selected_names:
        row = df[df["product_name"] == name].iloc[0]
        found = extract_uv_filters(str(row["ingredients"]))
        score = score_analysis(found)
        rows.append({
            "商品名": row["product_name"],
            "ブランド": row["brand"],
            "参考スコア": score["total"],
            "吸収剤": sum(1 for x in found if x["kind"] == "紫外線吸収剤"),
            "散乱剤": sum(1 for x in found if x["kind"] == "紫外線散乱剤"),
            "防御剤合計": len(found),
            "UVB": score["band_summary"]["UVB"],
            "UVA": score["band_summary"]["UVA"],
            "ロングUVA": score["band_summary"]["ロングUVA"],
            "SPF": row["spf"],
            "PA": row["pa"],
        })
    return pd.DataFrame(rows)

def make_comparison_chart(summary_df):
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=summary_df["商品名"],
            y=summary_df["参考スコア"],
            marker=dict(color="rgba(120, 126, 136, 0.82)"),
            hovertemplate="%{x}<br>参考スコア: %{y}<extra></extra>",
        )
    )
    fig.update_layout(
        title="比較: 参考スコア",
        xaxis=dict(title="商品名"),
        yaxis=dict(title="参考スコア", range=[0, 100], showgrid=True, gridcolor=GRID_COLOR),
        margin=dict(l=30, r=20, t=50, b=90),
        height=420,
        plot_bgcolor=PLOT_BG,
        paper_bgcolor=PLOT_BG,
        font=dict(
            family="-apple-system, BlinkMacSystemFont, 'Hiragino Sans', 'Yu Gothic', sans-serif",
            color=TEXT_COLOR,
        ),
    )
    return fig

db_df = load_product_db()

st.title("日焼け止め 紫外線防御剤チェッカー")
st.markdown(
    '<div class="soft-card">OCRなし版です。辞書から見る、手入力で解析する、辞書同士を比較する、の3つを入れています。</div>',
    unsafe_allow_html=True,
)

tab_dict, tab_manual, tab_compare = st.tabs(["辞書", "手入力解析", "比較"])

with tab_dict:
    st.subheader("辞書")
    if db_df.empty:
        st.info("まだ辞書データがありません。products.csv に商品を追加するとここに並びます。")
    else:
        search_query = st.text_input("商品名 / ブランドで検索", key="dict_search")
        filtered_df = filter_product_db(db_df, search_query)

        if filtered_df.empty:
            st.warning("該当する商品がありません。")
        else:
            options = filtered_df["product_name"].tolist()
            selected_name = st.selectbox("商品を選ぶ", options, key="dict_select")
            selected_row = filtered_df[filtered_df["product_name"] == selected_name].iloc[0]
            render_analysis_block(
                product_name=selected_row["product_name"],
                brand=selected_row["brand"],
                spf=selected_row["spf"],
                pa=selected_row["pa"],
                ingredients=selected_row["ingredients"],
                notes=selected_row["notes"],
            )

with tab_manual:
    st.subheader("手入力解析")
    st.text_input("商品名（任意）", key="manual_product_name", placeholder="例: アネッサ パーフェクトUV")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.text_input("ブランド（任意）", key="manual_brand", placeholder="例: アネッサ")
    with c2:
        st.text_input("SPF（任意）", key="manual_spf", placeholder="例: SPF50+")
    with c3:
        st.text_input("PA（任意）", key="manual_pa", placeholder="例: PA++++")
    with c4:
        st.text_input("メモ（任意）", key="manual_notes", placeholder="例: ミルク")
    st.text_area(
        "全成分をここに貼ってください",
        key="manual_ingredients",
        height=200,
        placeholder="例: 水、エタノール、……",
    )

    b1, b2 = st.columns([1, 1])
    with b1:
        manual_parse = st.button("この内容で解析する", use_container_width=True)
    with b2:
        make_csv = st.button("辞書追加用の1行を作る", use_container_width=True)

    if manual_parse:
        render_analysis_block(
            product_name=st.session_state["manual_product_name"],
            brand=st.session_state["manual_brand"],
            spf=st.session_state["manual_spf"],
            pa=st.session_state["manual_pa"],
            ingredients=st.session_state["manual_ingredients"],
            notes=st.session_state["manual_notes"],
        )

    if make_csv:
        row_text = make_csv_row(
            st.session_state["manual_product_name"],
            st.session_state["manual_brand"],
            st.session_state["manual_spf"],
            st.session_state["manual_pa"],
            st.session_state["manual_ingredients"],
            st.session_state["manual_notes"],
        )
        st.code(row_text, language="text")
        st.caption("この1行を products.csv の末尾に追加すると、辞書タブと比較タブでも使えます。")

with tab_compare:
    st.subheader("比較")
    if db_df.empty:
        st.info("比較するには products.csv に2件以上の商品を入れてください。")
    else:
        options = db_df["product_name"].tolist()
        selected_names = st.multiselect(
            "比較したい商品を選ぶ",
            options=options,
            default=options[:2] if len(options) >= 2 else options,
        )

        if len(selected_names) < 2:
            st.info("2件以上選ぶと比較できます。")
        else:
            summary_df = make_comparison_summary(db_df, selected_names)
            st.dataframe(summary_df, use_container_width=True)

            compare_fig = make_comparison_chart(summary_df)
            st.plotly_chart(compare_fig, use_container_width=True, config={"displayModeBar": False})

st.caption("※ 参考スコアは配合量や実測SPF/PAを反映した絶対評価ではなく、配合されている防御剤の種類・担当帯域・安定性目安から作った簡易スコアです。")
st.caption("※ 辞書機能は products.csv の内容を表示しています。日本で売られている商品を全部自動取得する機能はまだ入っていません。")
