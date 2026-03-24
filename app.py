import re
import unicodedata
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
import easyocr

st.set_page_config(page_title="UV防御剤チェッカー", layout="wide")

# =========================
# デザイン
# =========================
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg, #fcfaf7 0%, #f8f5f0 100%);
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 980px;
    }
    h1, h2, h3 {
        color: #3b3a36;
        letter-spacing: 0.01em;
    }
    [data-testid="stMetricValue"] {
        color: #4a4a46;
    }
    div[data-testid="stTextArea"] textarea {
        background-color: #fffdfa !important;
    }
    div[data-testid="stFileUploader"] section {
        background-color: #fffdfa;
    }
    .soft-note {
        padding: 0.8rem 1rem;
        background: rgba(255,255,255,0.6);
        border: 1px solid #ece6dc;
        border-radius: 14px;
        color: #5f5b55;
        font-size: 0.95rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================
# 帯域定義
# =========================
BAND_DEFS = [
    {"label": "UVB", "start": 280, "end": 320, "color": "rgba(98, 164, 255, 0.16)"},
    {"label": "UVA", "start": 320, "end": 340, "color": "rgba(255, 179, 102, 0.16)"},
    {"label": "ロングUVA", "start": 340, "end": 400, "color": "rgba(255, 107, 107, 0.14)"},
]

ABSORBER_FILL = "#7C838C"   # グレー
ABSORBER_LINE = "#666C74"

SCATTER_FILL = "#F6F2EA"    # 白っぽい
SCATTER_LINE = "#A9A39A"

PLOT_BG = "#FFFCF8"
GRID_COLOR = "rgba(120, 120, 120, 0.10)"
AXIS_COLOR = "#D8D1C6"
TEXT_COLOR = "#4A4741"

# =========================
# 紫外線防御剤辞書
# =========================
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

SAMPLE_TEXT = (
    "水、エタノール、メトキシケイヒ酸エチルヘキシル、"
    "ビスエチルヘキシルオキシフェノールメトキシフェニルトリアジン、"
    "ジエチルアミノヒドロキシベンゾイル安息香酸ヘキシル、"
    "オクトクリレン"
)

# =========================
# セッション初期化
# =========================
if "ingredients_text" not in st.session_state:
    st.session_state["ingredients_text"] = SAMPLE_TEXT

if "ocr_done" not in st.session_state:
    st.session_state["ocr_done"] = False

# =========================
# ユーティリティ
# =========================
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

def preprocess_image_for_ocr(image: Image.Image) -> np.ndarray:
    img = image.convert("RGB")

    # 大きすぎ/小さすぎ対策
    max_w = 1800
    if img.width > max_w:
        ratio = max_w / img.width
        img = img.resize((int(img.width * ratio), int(img.height * ratio)))

    if img.width < 1200:
        ratio = 1200 / img.width
        img = img.resize((int(img.width * ratio), int(img.height * ratio)))

    gray = ImageOps.grayscale(img)
    gray = ImageOps.autocontrast(gray)
    gray = ImageEnhance.Contrast(gray).enhance(1.8)
    gray = gray.filter(ImageFilter.SHARPEN)

    return np.array(gray)

@st.cache_resource
def get_ocr_reader():
    return easyocr.Reader(["ja", "en"], gpu=False, verbose=False)

def run_ocr(image: Image.Image) -> str:
    reader = get_ocr_reader()
    processed = preprocess_image_for_ocr(image)
    results = reader.readtext(processed, detail=0, paragraph=True)

    if not results:
        return ""

    text = "\n".join([r.strip() for r in results if str(r).strip()])
    text = re.sub(r"[ ]{2,}", " ", text)
    return text.strip()

def plot_filters(found):
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
            y=1.03,
            yref="paper",
            text=f"<b>{band['label']}</b>",
            showarrow=False,
            font=dict(size=12, color=TEXT_COLOR),
        )

    short_names = [item["short_label"] for item in found]

    for item in found:
        if item["kind"] == "紫外線吸収剤":
            fill_color = ABSORBER_FILL
            line_color = ABSORBER_LINE
        else:
            fill_color = SCATTER_FILL
            line_color = SCATTER_LINE

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

    # 凡例用ダミー
    fig.add_trace(
        go.Bar(
            x=[0],
            y=[None],
            name="紫外線吸収剤",
            marker=dict(
                color=ABSORBER_FILL,
                line=dict(color=ABSORBER_LINE, width=1.2),
            ),
            showlegend=True,
        )
    )
    fig.add_trace(
        go.Bar(
            x=[0],
            y=[None],
            name="紫外線散乱剤",
            marker=dict(
                color=SCATTER_FILL,
                line=dict(color=SCATTER_LINE, width=1.2),
            ),
            showlegend=True,
        )
    )

    fig.update_layout(
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

# =========================
# UI
# =========================
st.title("日焼け止め 紫外線防御剤チェッカー")
st.markdown(
    '<div class="soft-note">成分テキストを貼るか、全成分表画像をアップしてOCRで読み取りできます。</div>',
    unsafe_allow_html=True,
)

st.write("")

product_name = st.text_input(
    "商品名（任意）",
    placeholder="例: アネッサ パーフェクトUV スキンケアミルク"
)

input_mode = st.radio(
    "入力方法",
    ["テキスト入力", "画像アップロード"],
    horizontal=True
)

if input_mode == "テキスト入力":
    st.text_area(
        "全成分をここに貼ってください",
        key="ingredients_text",
        height=180,
    )

else:
    uploaded_file = st.file_uploader(
        "全成分表の画像をアップロード",
        type=["png", "jpg", "jpeg", "webp"]
    )

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="アップロード画像", use_container_width=True)

        if st.button("画像から文字を読み取る"):
            with st.spinner("画像を読み取り中… 最初の1回は少し時間がかかることがあります"):
                ocr_text = run_ocr(image)
                st.session_state["ingredients_text"] = ocr_text
                st.session_state["ocr_done"] = True
                st.rerun()

    st.text_area(
        "OCR結果（必要ならここを直してから解析）",
        key="ingredients_text",
        height=220,
    )

col_a, col_b = st.columns([1, 1])

with col_a:
    parse_clicked = st.button("解析する", use_container_width=True)

with col_b:
    if st.button("サンプルを入れる", use_container_width=True):
        st.session_state["ingredients_text"] = SAMPLE_TEXT
        st.rerun()

if parse_clicked:
    ingredients = st.session_state.get("ingredients_text", "").strip()

    if not ingredients:
        st.warning("全成分テキストが空です。テキストを貼るか、画像を読み取ってください。")
    else:
        found = extract_uv_filters(ingredients)

        st.write("")
        if product_name.strip():
            st.subheader(f"{product_name.strip()} の解析結果")
        else:
            st.subheader("解析結果")

        st.write(f"**見つかった紫外線防御剤: {len(found)}種類**")

        if not found:
            st.warning("紫外線防御剤が見つかりませんでした。OCR誤認識の可能性もあるので、OCR結果を少し修正してみてください。")
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

            c1, c2 = st.columns(2)
            with c1:
                st.metric("紫外線吸収剤", absorber_count)
            with c2:
                st.metric("紫外線散乱剤", scatter_count)

            st.markdown("#### カバー領域")
            fig = plot_filters(found)
            st.plotly_chart(
                fig,
                use_container_width=True,
                config={"displayModeBar": False},
            )

st.caption("※ カバー領域は実務用の簡易表示です。厳密な吸収スペクトルそのものではありません。")
st.caption("※ 効果の強さは配合量・製剤設計・SPF/PA試験結果で大きく変わるため、この図だけでは断定できません。")
st.caption("※ OCRは画像の傾き・反射・ぼけで誤認識することがあります。")
