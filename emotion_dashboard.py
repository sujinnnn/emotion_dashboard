import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import smtplib
import io
import os
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

st.set_page_config(layout="wide", page_title="Food & Mood Dashboard", page_icon="🍽️")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; background-color: #f7f5f2; }
.main { background-color: #f7f5f2; }
.block-container { padding-top: 2rem; }
.dashboard-title {
    font-family: 'DM Serif Display', serif;
    font-size: 2.2rem; color: #f8fafc; text-align: center; margin-bottom: 4px;
}
.dashboard-subtitle {
    font-size: 0.95rem; color: #cbd5e1; text-align: center; margin-bottom: 28px; font-weight: 300;
}
.chart-card {
    background: white; border-radius: 16px; padding: 20px 22px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.07); border: 1px solid #e8e4df; margin-bottom: 20px;
}
.chart-title { font-size: 1rem; font-weight: 600; color: #1a1a2e; margin-bottom: 2px; }
.chart-sub { font-size: 0.78rem; color: #9ca3af; margin-bottom: 10px; font-weight: 300; }
.info-card {
    background: white; border-radius: 16px; padding: 18px 22px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06); border: 1px solid #e8e4df;
    text-align: center; margin-bottom: 16px;
}
.info-label { font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: #9ca3af; }
.info-value { font-family: 'DM Serif Display', serif; font-size: 1.4rem; color: #1a1a2e; line-height: 1.3; }
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────────
FOOD_GROUPS  = ['Simple Carbs', 'Complex Carbs', 'Fats', 'Fiber', 'Proteins']
NUT_COLS     = ['Simple Carb Rating', 'Complex Carb Rating', 'Fat Rating', 'Fiber Rating', 'Protein Rating']
GROUP_COLORS = ['#f87171', '#60a5fa', '#fbbf24', '#a78bfa', '#34d399']
RADAR_FILLS  = ['rgba(248,113,113,0.1)','rgba(96,165,250,0.1)',
                'rgba(251,191,36,0.1)','rgba(167,139,250,0.1)','rgba(52,211,153,0.1)']
EMOTIONS = ['Emotional balance', 'Ease of mind', 'Stressload', 'Activation', 'Drive']
EMOTION_COLORS = {
    'Emotional balance': '#10b981',
    'Ease of mind': '#60a5fa',
    'Stressload': '#ef4444',
    'Activation': '#fbbf24',
    'Drive': '#a78bfa',
}
EXTRA_EMOTIONS = [
    ('Emotional balance', '#10b981', 'Avg emotional balance after meal by food group'),
    ('Ease of mind', '#60a5fa', 'Avg ease of mind after meal by food group'),
    ('Stressload', '#ef4444', 'Avg stressload after meal by food group'),
    ('Activation', '#fbbf24', 'Avg activation after meal by food group'),
    ('Drive', '#a78bfa', 'Avg drive after meal by food group'),
]

def safe(v):
    try: return float(v)
    except: return 0.0

# ── Build figures for one participant ─────────────────────────────────────────
def build_figures(post, pre, nut_vals, emotion_vals):
    figs = {}

    # Radar
    radar_axes = EMOTIONS
    fig_radar = go.Figure()
    for fg, nv, color, fill in zip(FOOD_GROUPS, nut_vals, GROUP_COLORS, RADAR_FILLS):
        w = nv / 10
        r = [post[e] * w for e in radar_axes] + [post[radar_axes[0]] * w]
        fig_radar.add_trace(go.Scatterpolar(
            r=r, theta=radar_axes + [radar_axes[0]],
            fill='toself', name=fg, line=dict(color=color, width=1.5),
            fillcolor=fill, opacity=0.8,
        ))
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(range=[0,5], tickfont=dict(size=8, color='#9ca3af'), gridcolor='#e5e7eb'),
            angularaxis=dict(tickfont=dict(size=10, color='#374151')),
            bgcolor='white',
        ),
        height=450, paper_bgcolor='white', margin=dict(l=80,r=140,t=40,b=80),
        legend=dict(orientation='h', y=-0.18, xanchor='center', x=0.5,
                    font=dict(size=11, color='#374151'), bgcolor='rgba(0,0,0,0)'),
        showlegend=True,
    )
    figs['radar'] = fig_radar

    # 5 emotion bar charts
    for emotion, color, _ in EXTRA_EMOTIONS:
        fig_e = go.Figure(go.Bar(
            x=FOOD_GROUPS, y=emotion_vals[emotion],
            marker_color=GROUP_COLORS, marker_line_width=0, width=0.6,
        ))
        fig_e.update_layout(
            height=250, paper_bgcolor='white', plot_bgcolor='white',
            margin=dict(l=10,r=10,t=30,b=80),
            title=dict(text=emotion, font=dict(size=13, color='#1a1a2e'), x=0.5),
            yaxis=dict(range=[0,5], showgrid=True, gridcolor='#f3f4f6',
                       tickfont=dict(color='#9ca3af', size=10)),
            xaxis=dict(tickangle=-35, tickfont=dict(color='#374151', size=9)),
            showlegend=False,
        )
        figs[f'emotion_{emotion}'] = fig_e

    # Before vs After
    fig_ba = go.Figure()
    fig_ba.add_trace(go.Bar(
        name='Before (avg)', x=EMOTIONS, y=[pre[e] for e in EMOTIONS],
        marker_color='#e2e8f0', marker_line_width=0,
        text=[f"{pre[e]:.1f}" for e in EMOTIONS],
        textposition='outside', textfont=dict(size=10, color='#94a3b8'),
    ))
    fig_ba.add_trace(go.Bar(
        name='After (avg)', x=EMOTIONS, y=[post[e] for e in EMOTIONS],
        marker_color='#38bdf8', marker_line_width=0,
        text=[f"{post[e]:.1f}" for e in EMOTIONS],
        textposition='outside', textfont=dict(size=10, color='#0ea5e9'),
    ))
    fig_ba.update_layout(
        barmode='group', height=320, paper_bgcolor='white', plot_bgcolor='white',
        margin=dict(l=0,r=0,t=30,b=10),
        yaxis=dict(range=[0,7], showgrid=True, gridcolor='#f1f5f9',
                   tickfont=dict(color='#cbd5e1', size=10), zeroline=False),
        xaxis=dict(tickfont=dict(color='#374151', size=11), tickangle=0),
        legend=dict(orientation='h', y=1.0, xanchor='right', x=1,
                    font=dict(size=12, color='#374151'), bgcolor='rgba(0,0,0,0)'),
        bargap=0.28, bargroupgap=0.04,
    )
    figs['before_after'] = fig_ba
    return figs

# ── Generate PDF for one participant ──────────────────────────────────────────
def generate_pdf(email, n_meals, meal_type_str, how_str, date_str, post, pre, nut_vals, emotion_vals):
    figs = build_figures(post, pre, nut_vals, emotion_vals)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    styles = getSampleStyleSheet()
    title_style  = ParagraphStyle('title',  fontSize=22, fontName='Helvetica-Bold',
                                   textColor=colors.HexColor('#1a1a2e'), alignment=TA_CENTER, spaceAfter=4)
    sub_style    = ParagraphStyle('sub',    fontSize=10, fontName='Helvetica',
                                   textColor=colors.HexColor('#6b7280'), alignment=TA_CENTER, spaceAfter=16)
    heading_style= ParagraphStyle('heading',fontSize=14, fontName='Helvetica-Bold',
                                   textColor=colors.HexColor('#1a1a2e'), spaceBefore=14, spaceAfter=4)
    label_style  = ParagraphStyle('label',  fontSize=8,  fontName='Helvetica-Bold',
                                   textColor=colors.HexColor('#9ca3af'), spaceAfter=2)
    value_style  = ParagraphStyle('value',  fontSize=13, fontName='Helvetica-Bold',
                                   textColor=colors.HexColor('#1a1a2e'))

    W = 180*mm  # usable width

    def fig_to_image(fig, width, height):
        img_bytes = fig.to_image(format='png', width=int(width*3.78), height=int(height*3.78), scale=2)
        return Image(io.BytesIO(img_bytes), width=width, height=height)

    story = []

    # Title
    story.append(Paragraph("🍽️ Food & Mood Breakdown", title_style))
    story.append(Paragraph(f"Personal report for {email}", sub_style))
    story.append(HRFlowable(width=W, thickness=1, color=colors.HexColor('#e8e4df')))
    story.append(Spacer(1, 8*mm))

    # Summary cards as a table
    card_data = [
        [Paragraph('TOTAL MEALS', label_style), Paragraph('MEAL TYPES', label_style),
         Paragraph('HOW EATEN', label_style),   Paragraph('DATE RANGE', label_style)],
        [Paragraph(str(n_meals), value_style),  Paragraph(meal_type_str, value_style),
         Paragraph(how_str, value_style),        Paragraph(date_str, value_style)],
    ]
    card_table = Table(card_data, colWidths=[W/4]*4)
    card_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.white),
        ('BOX',        (0,0), (-1,-1), 0.5, colors.HexColor('#e8e4df')),
        ('INNERGRID',  (0,0), (-1,-1), 0.5, colors.HexColor('#e8e4df')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING',(0,0),(-1,-1),8),
        ('LEFTPADDING',(0,0),(-1,-1),10),
    ]))
    story.append(card_table)
    story.append(Spacer(1, 8*mm))

    # Radar
    story.append(Paragraph("Emotional Profile by Food Group", heading_style))
    story.append(Paragraph("Avg post-meal emotional response weighted by food group — across all meals", sub_style))
    story.append(fig_to_image(figs['radar'], W, 90*mm))
    story.append(Spacer(1, 6*mm))

    # 5 emotion bars — 2 rows: 3 then 2
    story.append(Paragraph("Emotion Breakdown by Food Group", heading_style))
    story.append(HRFlowable(width=W, thickness=1, color=colors.HexColor('#e8e4df')))
    story.append(Spacer(1, 4*mm))

    row1 = [fig_to_image(figs[f'emotion_{e}'], W/2 - 2*mm, 55*mm)
            for e, _, _ in EXTRA_EMOTIONS[:2]]
    row2 = [fig_to_image(figs[f'emotion_{e}'], W/2 - 2*mm, 55*mm)
            for e, _, _ in EXTRA_EMOTIONS[2:4]]
    row3_img = fig_to_image(figs[f'emotion_{EXTRA_EMOTIONS[4][0]}'], W/2 - 2*mm, 55*mm)
    row3 = [row3_img, Spacer(W/2, 1)]  # Last emotion centered

    t1 = Table([row1], colWidths=[W/2]*2)
    t2 = Table([row2], colWidths=[W/2]*2)
    t3 = Table([row3], colWidths=[W/2]*2)
    story += [t1, Spacer(1, 3*mm), t2, Spacer(1, 3*mm), t3, Spacer(1, 6*mm)]

    # Before vs After
    story.append(Paragraph("Before vs. After Meal (Avg)", heading_style))
    story.append(Paragraph("Average pre and post-meal emotional scores across all meals (0–5 scale)", sub_style))
    story.append(fig_to_image(figs['before_after'], W, 75*mm))
    story.append(Spacer(1, 6*mm))

    # Emotion change summary table
    changes   = [(e, post[e] - pre[e]) for e in EMOTIONS]
    increased = sorted([(e,d) for e,d in changes if d > 0],       key=lambda x: -x[1])
    decreased = sorted([(e,d) for e,d in changes if d < 0],       key=lambda x:  x[1])
    unchanged = [e for e,d in changes if round(d,2) == 0]

    def change_rows(items, fmt):
        return [f"{e} ({fmt(d)})" for e,d in items] if items else ['None']

    inc_rows = change_rows(increased, lambda d: f'+{d:.2f}')
    dec_rows = change_rows(decreased, lambda d: f'{d:.2f}')
    unc_rows = unchanged if unchanged else ['None']
    max_rows = max(len(inc_rows), len(dec_rows), len(unc_rows))

    def pad(lst, n): return lst + [''] * (n - len(lst))

    chg_style = ParagraphStyle('chg', fontSize=9, fontName='Helvetica', textColor=colors.HexColor('#374151'))
    chg_head  = ParagraphStyle('chgh',fontSize=10,fontName='Helvetica-Bold', textColor=colors.HexColor('#1a1a2e'))

    chg_data = [[Paragraph('↑ Increased', chg_head),
                 Paragraph('↓ Decreased', chg_head),
                 Paragraph('— Unchanged', chg_head)]]
    for i in range(max_rows):
        chg_data.append([
            Paragraph(pad(inc_rows, max_rows)[i], chg_style),
            Paragraph(pad(dec_rows, max_rows)[i], chg_style),
            Paragraph(pad(unc_rows, max_rows)[i], chg_style),
        ])
    chg_table = Table(chg_data, colWidths=[W/3]*3)
    chg_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.white),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f8fafc')),
        ('BOX',        (0,0), (-1,-1), 0.5, colors.HexColor('#e8e4df')),
        ('INNERGRID',  (0,0), (-1,-1), 0.5, colors.HexColor('#f1f5f9')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('LEFTPADDING',(0,0),(-1,-1),10),
    ]))
    story.append(chg_table)

    doc.build(story)
    buf.seek(0)
    return buf

# ── Send email with PDF attachment ────────────────────────────────────────────
def send_email(gmail_user, gmail_password, to_email, pdf_buf, participant_name):
    msg = MIMEMultipart()
    msg['From']    = gmail_user
    msg['To']      = to_email
    msg['Subject'] = '🍽️ Your Food & Mood Report'

    body = f"""Hi {participant_name},

Please find attached your personal Food & Mood Breakdown report, summarising how the foods you eat shape the way you feel across all your recorded meals.

Best,
The Food & Mood Team
"""
    msg.attach(MIMEText(body, 'plain'))

    part = MIMEBase('application', 'octet-stream')
    part.set_payload(pdf_buf.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename="food_mood_report_{participant_name}.pdf"')
    msg.attach(part)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, to_email, msg.as_string())

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="dashboard-title">🍽️ Food & Mood Breakdown</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="dashboard-subtitle">Discover how the foods you eat shape the way you feel — averaged across all your meals</div>',
    unsafe_allow_html=True
)

uploaded = st.file_uploader("Upload CSV File", type=["csv"])

if uploaded:
    df = pd.read_csv(uploaded)
    df.columns = df.columns.str.strip()

    # Map pre and post emotion columns (pre=cols 2-6, post=cols 15-19)
    pre_emotion_cols = df.columns[2:7].tolist()  # Emotional balance through Drive (pre)
    post_emotion_cols = df.columns[15:20].tolist()  # Emotional balance through Drive (post)
    
    for i, e in enumerate(EMOTIONS):
        df[f'pre_{e}'] = df.iloc[:, i+2].apply(safe)  # Pre emotions start at column 2
        df[f'post_{e}'] = df.iloc[:, i+15].apply(safe)  # Post emotions start at column 15
    
    for nc, fg in zip(NUT_COLS, FOOD_GROUPS):
        df[f'nut_{fg}'] = df[nc].apply(safe)

    emails = df['Email Address'].dropna().unique()
    selected_email = st.selectbox("👤 Select Participant", emails)
    person_rows = df[df['Email Address'] == selected_email]
    n_meals = len(person_rows)

    post     = {e: person_rows[f'post_{e}'].mean() for e in EMOTIONS}
    pre      = {e: person_rows[f'pre_{e}'].mean()  for e in EMOTIONS}
    nut_vals = [person_rows[f'nut_{fg}'].mean() for fg in FOOD_GROUPS]
    emotion_vals = {e: [nv / 10 * post[e] for nv in nut_vals] for e in EMOTIONS}

    meal_types = person_rows['What type of meal did you consume?'].value_counts()
    how_eaten  = person_rows['How did you consume this meal?'].value_counts()
    date_range_vals = person_rows['What day is this meal for?'].dropna()
    meal_type_str = ', '.join([f"{k} ({v})" for k,v in meal_types.items()])
    how_str       = ', '.join([f"{k} ({v})" for k,v in how_eaten.items()])
    date_str      = (f"{date_range_vals.min()} – {date_range_vals.max()}"
                     if len(date_range_vals) > 1 else
                     (date_range_vals.iloc[0] if len(date_range_vals) else 'N/A'))

    # ── Info cards ────────────────────────────────────────────────────────────
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    for col, lbl, val in zip([c1,c2,c3,c4],
                              ['Total Meals','Meal Types','How Eaten','Date Range'],
                              [str(n_meals), meal_type_str, how_str, date_str]):
        with col:
            st.markdown(
                f'<div class="info-card"><div class="info-label">{lbl}</div>'
                f'<div class="info-value" style="font-size:1.1rem">{val}</div></div>',
                unsafe_allow_html=True
            )

    st.markdown("---")

    # ── Radar ─────────────────────────────────────────────────────────────────
    radar_axes = EMOTIONS
    with st.container():
        st.markdown(
            '<div class="chart-card">'
            '<div class="chart-title">❄️ Emotional Profile by Food Group</div>'
            '<div class="chart-sub">Avg post-meal emotional response weighted by food group — across all meals</div>',
            unsafe_allow_html=True
        )
        fig3 = go.Figure()
        for fg, nv, color, fill in zip(FOOD_GROUPS, nut_vals, GROUP_COLORS, RADAR_FILLS):
            w = nv / 10
            r = [post[e] * w for e in radar_axes] + [post[radar_axes[0]] * w]
            fig3.add_trace(go.Scatterpolar(
                r=r, theta=radar_axes+[radar_axes[0]], fill='toself', name=fg,
                line=dict(color=color, width=1.5), fillcolor=fill, opacity=0.8,
            ))
        fig3.update_layout(
            polar=dict(
                radialaxis=dict(range=[0,5], tickfont=dict(size=8,color='#9ca3af'), gridcolor='#e5e7eb'),
                angularaxis=dict(tickfont=dict(size=10,color='#374151')),
                bgcolor='white',
            ),
            height=450, paper_bgcolor='white', margin=dict(l=80,r=140,t=40,b=80),
            legend=dict(orientation='h', y=-0.18, xanchor='center', x=0.5,
                        font=dict(size=11,color='#374151'), bgcolor='rgba(0,0,0,0)'),
            showlegend=True,
        )
        st.plotly_chart(fig3, use_container_width=True, key="radar")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ── 5 Emotion bars ────────────────────────────────────────────────────────
    e_cols = st.columns(5)
    for col, (emotion, color, subtitle) in zip(e_cols, EXTRA_EMOTIONS):
        with col:
            st.markdown(
                f'<div class="chart-card"><div class="chart-title">{emotion}</div>'
                f'<div class="chart-sub">{subtitle}</div>',
                unsafe_allow_html=True
            )
            fig_e = go.Figure(go.Bar(
                x=FOOD_GROUPS, y=emotion_vals[emotion],
                marker_color=GROUP_COLORS, marker_line_width=0, width=0.6,
            ))
            fig_e.update_layout(
                height=250, paper_bgcolor='white', plot_bgcolor='white',
                margin=dict(l=10,r=10,t=10,b=80),
                yaxis=dict(range=[0,5], showgrid=True, gridcolor='#f3f4f6',
                           tickfont=dict(color='#9ca3af', size=10)),
                xaxis=dict(tickangle=-35, tickfont=dict(color='#374151', size=9)),
                showlegend=False,
            )
            st.plotly_chart(fig_e, use_container_width=True, key=f"emotion_{emotion}")
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ── Before vs After ───────────────────────────────────────────────────────
    st.markdown(
        '<div style="background:white;border-radius:20px;padding:28px 32px 8px 32px;'
        'border:1px solid #e8e4df;margin-bottom:24px;">'
        '<div style="font-family:DM Serif Display,serif;font-size:1.5rem;color:#1a1a2e;margin-bottom:2px;">'
        '📊 Before vs. After Meal</div>'
        '<div style="font-size:0.82rem;color:#9ca3af;font-weight:300;margin-bottom:4px;">'
        'Average pre and post-meal emotional scores across all meals (0–5 scale)</div>',
        unsafe_allow_html=True
    )
    fig_ba = go.Figure()
    fig_ba.add_trace(go.Bar(
        name='Before (avg)', x=EMOTIONS, y=[pre[e] for e in EMOTIONS],
        marker_color='#e2e8f0', marker_line_width=0,
        text=[f"{pre[e]:.1f}" for e in EMOTIONS],
        textposition='outside', textfont=dict(size=10, color='#94a3b8'),
    ))
    fig_ba.add_trace(go.Bar(
        name='After (avg)', x=EMOTIONS, y=[post[e] for e in EMOTIONS],
        marker_color='#38bdf8', marker_line_width=0,
        text=[f"{post[e]:.1f}" for e in EMOTIONS],
        textposition='outside', textfont=dict(size=10, color='#0ea5e9'),
    ))
    fig_ba.update_layout(
        barmode='group', height=320, paper_bgcolor='white', plot_bgcolor='white',
        margin=dict(l=0,r=0,t=30,b=10),
        yaxis=dict(range=[0,7], showgrid=True, gridcolor='#f1f5f9',
                   tickfont=dict(color='#cbd5e1', size=10), zeroline=False),
        xaxis=dict(tickfont=dict(color='#374151', size=12), tickangle=0),
        legend=dict(orientation='h', y=1.0, xanchor='right', x=1,
                    font=dict(size=12,color='#374151'), bgcolor='rgba(0,0,0,0)'),
        bargap=0.28, bargroupgap=0.04,
    )
    st.plotly_chart(fig_ba, use_container_width=True, key="before_after")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Emotion change cards ──────────────────────────────────────────────────
    changes   = [(e, post[e]-pre[e]) for e in EMOTIONS]
    increased = sorted([(e,d) for e,d in changes if d>0],          key=lambda x: -x[1])
    decreased = sorted([(e,d) for e,d in changes if d<0],          key=lambda x:  x[1])
    unchanged = [e for e,d in changes if round(d,2)==0]

    c1, c2, c3 = st.columns(3)
    SECTION_META = {
        '↑ Increased': ('#16a34a','#22c55e'),
        '↓ Decreased': ('#dc2626','#ef4444'),
        '— Unchanged': ('#64748b','#94a3b8'),
    }
    for col, title, items, dfmt in [
        (c1,'↑ Increased', increased,                   lambda d: f'+{d:.2f}'),
        (c2,'↓ Decreased', decreased,                   lambda d: f'{d:.2f}'),
        (c3,'— Unchanged', [(e,0) for e in unchanged],  lambda d: ''),
    ]:
        heading_color, badge_color = SECTION_META[title]
        with col:
            rows_html = ''
            if items:
                for e,d in items:
                    delta = dfmt(d) if d!=0 else ''
                    badge = (f"<span style='background:{badge_color}22;color:{badge_color};"
                             f"padding:2px 9px;border-radius:10px;font-size:0.78rem;font-weight:700'>{delta}</span>"
                             ) if delta else ''
                    rows_html += (f"<div style='display:flex;justify-content:space-between;align-items:center;"
                                  f"padding:9px 0;border-bottom:1px solid #f1f5f9;'>"
                                  f"<span style='color:{EMOTION_COLORS[e]};font-weight:600;font-size:0.92rem'>{e}</span>"
                                  f"{badge}</div>")
            else:
                rows_html = "<div style='color:#9ca3af;font-size:0.88rem;padding:8px 0'>None</div>"
            st.markdown(
                f'<div style="background:white;border-radius:16px;padding:22px 26px;border:1px solid #e8e4df;">'
                f'<div style="font-family:DM Serif Display,serif;font-size:1.1rem;color:{heading_color};"'
                f' style="margin-bottom:14px;padding-bottom:10px;border-bottom:2px solid {badge_color}33;">'
                f'{title}</div>{rows_html}</div>',
                unsafe_allow_html=True
            )

    # ── Email section ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        '<div style="font-family:DM Serif Display,serif;font-size:1.5rem;color:#1a1a2e;margin-bottom:4px;">'
        '📧 Email Reports to All Participants</div>'
        '<div style="font-size:0.82rem;color:#9ca3af;font-weight:300;margin-bottom:20px;">'
        'Generates a PDF report for every participant and sends it to their email address</div>',
        unsafe_allow_html=True
    )

    with st.expander("⚙️ Gmail Settings", expanded=False):
        st.markdown("Use a Gmail **App Password** — not your regular password. "
                    "[Generate one here](https://myaccount.google.com/apppasswords) "
                    "(requires 2FA to be enabled on your Google account).")
        gmail_user = st.text_input("Your Gmail address", placeholder="you@gmail.com")
        gmail_pass = st.text_input("App Password (16 chars, no spaces)", type="password")

    if st.button("📤 Send PDF Reports to All Participants", type="primary"):
        if not gmail_user or not gmail_pass:
            st.error("Please fill in your Gmail address and App Password above.")
        else:
            all_emails = df['Email Address'].dropna().unique()
            progress   = st.progress(0)
            status     = st.empty()
            success_count, fail_count = 0, 0

            for i, participant_email in enumerate(all_emails):
                status.info(f"Generating report for {participant_email}...")
                rows = df[df['Email Address'] == participant_email]

                p_post     = {e: rows[f'post_{e}'].mean() for e in EMOTIONS}
                p_pre      = {e: rows[f'pre_{e}'].mean()  for e in EMOTIONS}
                p_nut_vals = [rows[f'nut_{fg}'].mean() for fg in FOOD_GROUPS]
                p_emotion_vals = {e: [nv/10*p_post[e] for nv in p_nut_vals] for e in EMOTIONS}

                p_meal_types = rows['What type of meal did you consume?'].value_counts()
                p_how        = rows['How did you consume this meal?'].value_counts()
                p_dates      = rows['What day is this meal for?'].dropna()
                p_meal_str   = ', '.join([f"{k} ({v})" for k,v in p_meal_types.items()])
                p_how_str    = ', '.join([f"{k} ({v})" for k,v in p_how.items()])
                p_date_str   = (f"{p_dates.min()} – {p_dates.max()}"
                                if len(p_dates)>1 else (p_dates.iloc[0] if len(p_dates) else 'N/A'))

                try:
                    pdf_buf = generate_pdf(
                        participant_email, len(rows),
                        p_meal_str, p_how_str, p_date_str,
                        p_post, p_pre, p_nut_vals, p_emotion_vals
                    )
                    send_email(gmail_user, gmail_pass, participant_email, pdf_buf,
                               participant_email.split('@')[0])
                    success_count += 1
                    status.success(f"✅ Sent to {participant_email}")
                except Exception as ex:
                    fail_count += 1
                    status.error(f"❌ Failed for {participant_email}: {ex}")

                progress.progress((i+1) / len(all_emails))

            status.empty()
            if success_count:
                st.success(f"✅ Successfully sent {success_count} report(s).")
            if fail_count:
                st.error(f"❌ {fail_count} report(s) failed. Check your App Password and try again.")
    # ── Reminder email section ────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        '<div style="font-family:DM Serif Display,serif;font-size:1.5rem;color:#1a1a2e;margin-bottom:4px;">'
        '⏰ Send Daily Meal Reminder</div>'
        '<div style="font-size:0.82rem;color:#9ca3af;font-weight:300;margin-bottom:20px;">'
        'Sends a quick reminder to all participants to log at least one meal today</div>',
        unsafe_allow_html=True
    )

    if st.button("📬 Send Reminder to All Participants"):
        if not gmail_user or not gmail_pass:
            st.error("Please fill in your Gmail address and App Password in Gmail Settings above.")
        else:
            import datetime
            today = datetime.date.today().strftime("%B %d, %Y")
            all_emails = df['Email Address'].dropna().unique()
            progress2  = st.progress(0)
            status2    = st.empty()
            s_count, f_count = 0, 0

            for i, participant_email in enumerate(all_emails):
                status2.info(f"Sending reminder to {participant_email}...")
                name = participant_email.split('@')[0]
                try:
                    msg = MIMEMultipart()
                    msg['From']    = gmail_user
                    msg['To']      = participant_email
                    msg['Subject'] = f"🍽️ Don't forget to log your meal today! ({today})"
                    body = f"""Hi {name},

Just a friendly reminder to log at least one meal for today ({today}) in the Food & Mood study.

Tracking your meals helps build a clearer picture of how the foods you eat affect your emotions over time. Even a quick entry makes a difference!

Thanks for participating,
The Food & Mood Team
"""
                    msg.attach(MIMEText(body, 'plain'))
                    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                        server.login(gmail_user, gmail_pass)
                        server.sendmail(gmail_user, participant_email, msg.as_string())
                    s_count += 1
                    status2.success(f"✅ Reminder sent to {participant_email}")
                except Exception as ex:
                    f_count += 1
                    status2.error(f"❌ Failed for {participant_email}: {ex}")

                progress2.progress((i + 1) / len(all_emails))

            status2.empty()
            if s_count:
                st.success(f"✅ Reminders sent to {s_count} participant(s).")
            if f_count:
                st.error(f"❌ {f_count} reminder(s) failed. Check your App Password and try again.")