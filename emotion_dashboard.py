
import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

st.markdown("""
<style>
body { background-color: #0f172a; }

.card {
    background: #1e293b;
    padding: 25px;
    border-radius: 20px;
    margin-bottom: 25px;
    border: 1px solid #334155;
}

.emotion-title {
    font-size: 22px;
    font-weight: 600;
    margin-bottom: 10px;
}

.pre-bar {
    height: 14px;
    border-radius: 8px;
    background: #334155;
}

.pre-fill {
    height: 14px;
    border-radius: 8px;
    background: #64748b;
}

.post-fill {
    height: 14px;
    border-radius: 8px;
    background: #38bdf8;
}

.badge-positive {
    background: #064e3b;
    color: #34d399;
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 13px;
}

.badge-negative {
    background: #7f1d1d;
    color: #f87171;
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 13px;
}
</style>
""", unsafe_allow_html=True)



st.set_page_config(layout="wide")
st.title("Emotion Dashboard by Respondent")

uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

def safe_to_number(value):
    try:
        return float(value)
    except:
        return 0
    
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df.columns = df.columns.str.strip()

    # 🔹 첫 컬럼은 Timestamp (응답자 구분)
    respondent_col = df.columns[0]

    respondents = df[respondent_col].astype(str).unique()
    selected = st.selectbox("Select Respondent", respondents)

    person = df[df[respondent_col].astype(str) == selected].iloc[0]

    # -------------------------
    # 🔹 감정 분리
    # -------------------------

    pre_emotions = {}
    post_emotions = {}

    for col in df.columns[1:]:
        if col.endswith(" 2"):
            emotion = col.replace(" 2", "")
            post_emotions[emotion] = person[col]
        else:
            if col != respondent_col:
                pre_emotions[col] = person[col]

    # 공통 감정만 유지
    emotions = list(pre_emotions.keys())

    data = []

    for emotion in emotions:
        if emotion in post_emotions:
            pre = safe_to_number(pre_emotions[emotion])
            post = safe_to_number(post_emotions[emotion])
            change = post - pre
            data.append({
                "Emotion": emotion,
                "Pre": pre,
                "Post": post,
                "Change": change
            })

    emotion_df = pd.DataFrame(data)

    # ==============================
    # ⭐ Strong Emotions (≥4)
    # ==============================

    st.header("⭐ Strong Emotions (≥4)")

    strong = emotion_df[
        (emotion_df["Pre"] >= 4) | (emotion_df["Post"] >= 4)
    ]

    cols = st.columns(2)

    for i, (_, row) in enumerate(strong.iterrows()):

        percent_change = 0
        if row["Pre"] != 0:
            percent_change = (
                (row["Post"] - row["Pre"]) / row["Pre"]
            ) * 100

        badge_color = "#34d399" if percent_change > 0 else "#f87171"

        html_code = f"""
        <div style="
            background:#1e293b;
            padding:25px;
            border-radius:20px;
            margin-bottom:20px;
            color:white;
            font-family:Arial;
        ">
            <h3 style="margin-bottom:15px;">{row["Emotion"]}</h3>

            <div>Pre: {row["Pre"]}/5</div>
            <div style="background:#334155;height:14px;border-radius:8px;">
                <div style="
                    width:{row["Pre"]*20}%;
                    height:14px;
                    background:#64748b;
                    border-radius:8px;
                "></div>
            </div>

            <br>

            <div>Post: {row["Post"]}/5</div>
            <div style="background:#334155;height:14px;border-radius:8px;">
                <div style="
                    width:{row["Post"]*20}%;
                    height:14px;
                    background:#38bdf8;
                    border-radius:8px;
                "></div>
            </div>

            <br>

            <div style="
                background:#0f172a;
                color:{badge_color};
                padding:6px 12px;
                border-radius:20px;
                display:inline-block;
                font-size:13px;
            ">
                {percent_change:+.0f}% change
            </div>
        </div>
        """

        with cols[i % 2]:
            components.html(html_code, height=260)


    # ==============================
    # 🏆 Dominant Emotions
    # ==============================

    st.header("Dominant Emotions")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Before Meal")
        st.table(
            emotion_df.sort_values("Pre", ascending=False)[
                ["Emotion", "Pre"]
            ].head(3)
        )

    with col2:
        st.subheader("After Meal")
        st.table(
            emotion_df.sort_values("Post", ascending=False)[
                ["Emotion", "Post"]
            ].head(3)
        )


    # ==============================
    # 🔄 Emotion Changes
    # ==============================

    st.header("Emotion Changes")

    increased = emotion_df[emotion_df["Change"] > 0]
    decreased = emotion_df[emotion_df["Change"] < 0]
    unchanged = emotion_df[emotion_df["Change"] == 0]

    st.write("### ↑ Increased")
    st.write(increased[["Emotion", "Change"]])

    st.write("### ↓ Decreased")
    st.write(decreased[["Emotion", "Change"]])

    st.write("### — Unchanged")
    st.write(unchanged["Emotion"])

