import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff
from datetime import datetime, timedelta

st.set_page_config(page_title="阀门生产计划看板", layout="wide")
st.title("⚙️ 阀门生产 & 外包进度管理看板")

# ----------------------
# 1. 读取数据
# ----------------------
df = pd.read_excel("生产数据.xlsx")
df["开始日期"] = pd.to_datetime(df["开始日期"])
df["结束日期"] = pd.to_datetime(df["结束日期"])
today = pd.to_datetime(datetime.now().date())

# 计算完成率
df["完成率"] = (df["已完成数量"] / df["数量"] * 100).round(2)

# ----------------------
# 2. 延期预警核心逻辑
# ----------------------
def get_status_row(row):
    if row["状态"] == "已完成":
        return "🟢 已完成"
    if row["结束日期"] < today and row["完成率"] < 100:
        return "🔴 已延期"
    if (row["结束日期"] - today).days <= 2 and row["完成率"] < 100:
        return "🟡 即将到期"
    return "🟢 正常"

df["预警状态"] = df.apply(get_status_row, axis=1)

# ----------------------
# 3. 交期冲突判断（插单/改期影响）
# ----------------------
def check_overlap(row):
    same_machine = df[
        (df["机台/外包商"] == row["机台/外包商"])
        & (df["订单号"] != row["订单号"])
    ]
    for _, r2 in same_machine.iterrows():
        start1, end1 = row["开始日期"], row["结束日期"]
        start2, end2 = r2["开始日期"], r2["结束日期"]
        if not (end1 < start2 or end2 < start1):
            return f"⚠️ 与 {r2['订单号']} 时间冲突"
    return "✅ 无冲突"

df["交期冲突"] = df.apply(check_overlap, axis=1)

# ----------------------
# 4. 筛选
# ----------------------
st.sidebar.header("🔍 筛选")
status = st.sidebar.multiselect("状态", options=df["状态"].unique())
supplier = st.sidebar.multiselect("机台/外包商", options=df["机台/外包商"].unique())
warn = st.sidebar.multiselect("预警状态", options=df["预警状态"].unique())

if status:
    df = df[df["状态"].isin(status)]
if supplier:
    df = df[df["机台/外包商"].isin(supplier)]
if warn:
    df = df[df["预警状态"].isin(warn)]

# ----------------------
# 5. 统计卡片
# ----------------------
st.subheader("📊 生产总览")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("总订单数", len(df))
with c2:
    st.metric("总数量", df["数量"].sum())
with c3:
    st.metric("已完成", df["已完成数量"].sum())
with c4:
    st.metric("整体完成率", f"{(df['已完成数量'].sum()/df['数量'].sum()*100).round(1)}%")

st.markdown("---")

# ----------------------
# 6. 甘特图
# ----------------------
st.subheader("📅 生产计划甘特图")
gantt_df = df.copy()
gantt_df["Task"] = gantt_df["订单号"] + " " + gantt_df["零件名称"]
gantt_df["Start"] = gantt_df["开始日期"]
gantt_df["Finish"] = gantt_df["结束日期"]

fig_gantt = ff.create_gantt(
    gantt_df,
    index_col="机台/外包商",
    show_colorbar=True,
    bar_width=0.4,
    title="生产/外协排程"
)
st.plotly_chart(fig_gantt, use_container_width=True)

st.markdown("---")

# ----------------------
# 7. 图表
# ----------------------
tab1, tab2, tab3 = st.tabs(["订单完成率", "外包/机台产量", "订单状态"])
with tab1:
    fig1 = px.bar(df, x="订单号", y="完成率", color="预警状态", title="订单完成率 & 预警")
    st.plotly_chart(fig1, use_container_width=True)
with tab2:
    sup_sum = df.groupby("机台/外包商")[["数量", "已完成数量"]].sum().reset_index()
    fig2 = px.bar(sup_sum, x="机台/外包商", y=["数量", "已完成数量"], barmode="group", title="产能对比")
    st.plotly_chart(fig2, use_container_width=True)
with tab3:
    fig3 = px.pie(df, names="预警状态", title="整体预警分布")
    st.plotly_chart(fig3, use_container_width=True)

st.markdown("---")

# ----------------------
# 8. 完整表格（含延期、插单、冲突）
# ----------------------
st.subheader("📋 生产明细（含预警/冲突）")
st.dataframe(df, use_container_width=True)

# ----------------------
# 9. 延期 & 插单 高亮提醒
# ----------------------
st.subheader("⚠️ 异常订单一览")
delay = df[df["预警状态"].str.contains("延期|到期")]
if len(delay) > 0:
    st.warning("以下订单即将到期或已延期，请加急处理！")
    st.dataframe(delay)
else:
    st.success("所有订单均正常！")
