"""Australia ODI World Cup 2027 - Domestic Player Scouting Report.

A Streamlit app that presents a five-batter / five-fast-bowler shortlist
from two supporting CSV files.

Run with:  streamlit run app.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
ROOT = Path(__file__).resolve().parent

BATTER_FILE = "top_5_batters.csv"
BOWLER_FILE = "final_bowler_comparison.csv"

# Optional absolute paths on the project owner's machine (checked first).
LOCAL_DATA_PATHS = {
    BATTER_FILE: Path(r"C:\Cricket_Analysis\Project\Scouting Analysis\data\final_batting_data\top_5_batters.csv"),
    BOWLER_FILE: Path(r"C:\Cricket_Analysis\Project\Scouting_Bowler\Data\Clean_data\final_bowler_comparison.csv"),
}

# Alternative file names produced by browser downloads (e.g. "name(2).csv").
FILE_ALIASES = {
    BATTER_FILE: ["top_5_batters(2).csv", "top_5_batters(1).csv"],
    BOWLER_FILE: [
        "final_bowler_comparison(3).csv",
        "final_bowler_comparison(2).csv",
        "final_bowler_comparison(1).csv",
    ],
}

REQUIRED_BATTER_COLS = ["Player", "Runs", "Batting_Average", "Strike_Rate", "Innings"]
REQUIRED_BOWLER_COLS = ["Bowler", "Matches", "Wickets", "Economy", "Bowling_Average", "Strike_Rate"]

BOWLING_PHASES = ["Powerplay", "Middle Overs", "Death Overs"]
CHART_HEIGHT = 400
NOT_AVAILABLE = "N/A"

# --------------------------------------------------------------------------- #
# Page setup and styling
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="Australia ODI 2027 | Scouting Report",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
        [data-testid="stMetric"] {border: 1px solid rgba(128,128,128,.25); padding: 14px; border-radius: 10px;}
        .hero {padding: 1.4rem 1.6rem; border-radius: 12px; background: #1f3d33; color: #ffffff; margin-bottom: 1rem;}
        .hero h1 {color: #ffffff; margin-bottom: .3rem; font-size: 1.9rem;}
        .hero p {color: #dfece5; font-size: 1rem; margin-bottom: .2rem;}
        .hero .note {font-size: .85rem; opacity: .8;}
    </style>
    """,
    unsafe_allow_html=True,
)


def render_header() -> None:
    st.markdown(
        """
        <div class="hero">
          <h1>Australia ODI World Cup 2027</h1>
          <p>Domestic Player Scouting Report · Five batters · Five fast-bowling prospects</p>
          <div class="note">Evidence-led shortlist based on the supplied performance and phase-comparison datasets.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner=False)
def read_csv_cached(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def find_data_file(filename: str) -> Optional[Path]:
    """Return the first existing location for a data file, or None."""
    candidates = [LOCAL_DATA_PATHS.get(filename)]
    for folder in (ROOT, Path.cwd()):
        candidates.append(folder / filename)
        candidates.extend(folder / alias for alias in FILE_ALIASES.get(filename, []))
    for path in candidates:
        if path is not None and path.exists():
            return path

    # Fall back to searching sub-folders of the app directory (e.g. Data/Clean_data/).
    for name in [filename] + FILE_ALIASES.get(filename, []):
        matches = sorted(ROOT.rglob(name))
        if matches:
            return matches[0]
    return None


def load_csv(filename: str, uploaded) -> Optional[pd.DataFrame]:
    """Load from an uploaded file if given, otherwise from known locations."""
    if uploaded is not None:
        return pd.read_csv(uploaded)
    path = find_data_file(filename)
    return read_csv_cached(str(path)) if path else None


def validate_columns(df: pd.DataFrame, required: Iterable[str], label: str) -> None:
    """Stop the app with a clear message if required columns are missing."""
    missing = [col for col in required if col not in df.columns]
    if missing:
        st.error(f"The {label} file is missing required column(s): {', '.join(missing)}")
        st.stop()


# --------------------------------------------------------------------------- #
# Formatting and generic helpers
# --------------------------------------------------------------------------- #
def fmt_num(value, digits: int = 1) -> str:
    """Format a number with thousands separators; return N/A for missing values."""
    try:
        if pd.isna(value):
            return NOT_AVAILABLE
        return f"{float(value):,.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def existing(df: pd.DataFrame, columns: Iterable[str]) -> list[str]:
    """Return only the columns that are present in the dataframe."""
    return [col for col in columns if col in df.columns]


def has_all(df: pd.DataFrame, columns: Iterable[str]) -> bool:
    return all(col in df.columns for col in columns)


def show_table(data, **kwargs) -> None:
    st.dataframe(data, use_container_width=True, **kwargs)


def show_chart(fig: go.Figure, height: int = CHART_HEIGHT) -> None:
    """Apply a consistent, minimal layout and render the figure."""
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=10, r=10, t=50, b=10),
        legend_title_text="",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_metric_grid(row: pd.Series, specs: list[tuple[str, str, int]], n_cols: int = 3) -> None:
    """Render a grid of st.metric cards from (label, column, digits) specs."""
    columns = st.columns(n_cols)
    shown = 0
    for label, col, digits in specs:
        if col in row.index:
            columns[shown % n_cols].metric(label, fmt_num(row[col], digits))
            shown += 1


# --------------------------------------------------------------------------- #
# Static content
# --------------------------------------------------------------------------- #
WORKFLOW_STEPS = """1. Load match/delivery data and standardise player/team names.
2. Validate data types, missing values, duplicates and impossible values.
3. Separate batting and bowling records; distinguish legal balls from wides/no-balls where relevant.
4. Aggregate player performance across matches and innings.
5. Split performance by Powerplay, middle overs and death overs.
6. Evaluate output, efficiency, repeatability and role/phase contribution.
7. Compare candidates and shortlist five batters plus five fast bowlers.
8. Review results against eligibility and role requirements before recommending players."""

METRIC_DICTIONARY = {
    "Batting": [
        ("Runs", "Total runs credited to the batter in the dataset."),
        ("Balls_Faced", "Balls counted as faced under the project's ball-counting rules; wides are normally excluded, while no-ball handling should be checked."),
        ("Strike_Rate", "Runs per 100 balls faced: runs ÷ balls faced × 100."),
        ("Batting_Average", "Runs ÷ dismissals."),
        ("Dot_Ball_Pct", "Percentage of counted balls on which the batter scores no runs off the bat, depending on the project definition."),
        ("Boundary_Run_Pct", "Boundary runs as a percentage of total runs: boundary runs ÷ runs × 100."),
        ("Innings_30Plus / 50Plus / 100Plus", "Count of innings reaching at least 30 / 50 / 100 runs."),
        ("Mean_Innings_Runs", "Arithmetic mean of innings scores."),
        ("Median_Innings_Runs", "Middle innings score; less affected by extreme high scores than the mean."),
        ("Runs_Powerplay / Middle_Overs / Death_Overs", "Runs attributed to deliveries in the named match phase."),
        ("Strike_Rate_[phase]", "Runs in that phase per 100 balls faced in that phase."),
        ("Scouting_Score / Final_Performance_Score", "Custom composite score. Explain the exact formula, normalisation, weights and missing-data handling from the notebook."),
        ("Phase_Concentration / Phase_Versatility", "Custom phase-distribution indicators; explain the formula and scale from the notebook."),
        ("Recent_Form_Score / Adjusted_Recent_Form", "Recent-match indicators if available; missing values and reliability adjustments must be disclosed."),
    ],
    "Bowling": [
        ("Matches", "Matches in which the bowler appears in the supplied dataset."),
        ("Legal_Balls", "Legal deliveries bowled; wides and no-balls are excluded from this count."),
        ("Economy", "Runs conceded per six legal balls: runs conceded ÷ legal balls × 6."),
        ("Bowling_Average", "Runs conceded per wicket: runs conceded ÷ wickets."),
        ("Strike_Rate", "Legal balls per wicket: legal balls ÷ wickets."),
        ("[Phase]_Economy", "Runs conceded per six legal balls in that phase."),
        ("[Phase]_Wickets", "Wickets attributed to the bowler in that phase, according to the project's wicket-credit rules."),
        ("[Phase]_Bowling_Average", "Runs conceded in the phase ÷ wickets credited in that phase; undefined when no wickets are taken."),
        ("[Phase]_Strike_Rate", "Legal balls in the phase ÷ wickets in the phase; undefined when no wickets are taken."),
        ("[Phase]_Dot_Ball_Pct", "Percentage of deliveries in that phase that qualify as dot balls under the project's definition."),
        ("[Phase]_Boundary_Pct", "Percentage of deliveries or outcomes classed as boundaries in that phase; verify denominator in the notebook."),
        ("Avg_Wickets / Median_Wickets", "Mean and median wickets per match."),
        ("Matches_With_Wickets_Pct", "Percentage of matches in which the bowler took at least one wicket."),
        ("Avg_Economy / Median_Economy / Economy_SD", "Mean, median and standard deviation of match-level economy rates; standard deviation indicates variability."),
        ("Wicketless_Matches", "Number of matches in which the bowler took no wickets."),
    ],
}

BATTER_PROFILE_SPECS = [
    ("Total runs", "Runs", 0), ("Balls faced", "Balls_Faced", 0),
    ("Fours", "Fours", 0), ("Sixes", "Sixes", 0),
    ("Dot-ball %", "Dot_Ball_Pct", 2), ("Boundary-run %", "Boundary_Run_Pct", 2),
    ("30+ innings", "Innings_30Plus", 0), ("50+ innings", "Innings_50Plus", 0),
    ("100+ innings", "Innings_100Plus", 0), ("Mean innings runs", "Mean_Innings_Runs", 2),
    ("Median innings runs", "Median_Innings_Runs", 2), ("Final performance score", "Final_Performance_Score", 3),
]

BOWLER_PROFILE_SPECS = [
    ("Powerplay economy", "Powerplay_Economy", 2), ("Middle-overs economy", "Middle Overs_Economy", 2),
    ("Death-overs economy", "Death Overs_Economy", 2), ("Powerplay wickets", "Powerplay_Wickets", 0),
    ("Middle-overs wickets", "Middle Overs_Wickets", 0), ("Death-overs wickets", "Death Overs_Wickets", 0),
    ("Matches with wickets %", "Matches_With_Wickets_Pct", 2), ("Economy std. deviation", "Economy_SD", 2),
    ("Wicketless matches", "Wicketless_Matches", 0),
]


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #
def page_executive_summary(bat: pd.DataFrame, bowl: pd.DataFrame) -> None:
    st.subheader("Executive summary")
    st.write(
        "This report turns two supporting CSV files into a scouting presentation. "
        "The shortlist is based on the performance data supplied for five batters and five bowlers. "
        "The scores are decision-support indicators, not a guarantee of international success."
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Shortlisted players", len(bat) + len(bowl))
    c2.metric("Batters", len(bat))
    c3.metric("Fast bowlers", len(bowl))
    c4.metric("Data fields (bat / bowl)", f"{len(bat.columns)} / {len(bowl.columns)}")

    st.markdown("### The shortlist")
    left, right = st.columns(2)
    with left:
        st.markdown("#### Batters")
        cols = existing(bat, ["Player", "Runs", "Batting_Average", "Strike_Rate", "Scouting_Tier"])
        show_table(bat[cols].rename(columns=lambda c: c.replace("_", " ")), hide_index=True)
    with right:
        st.markdown("#### Bowlers")
        cols = existing(bowl, ["Bowler", "Matches", "Wickets", "Economy", "Bowling_Average"])
        show_table(bowl[cols].rename(columns=lambda c: c.replace("_", " ")), hide_index=True)

    st.info(
        "Interpretation note: these files provide the final shortlist and performance summaries, but do not include "
        "the full source-delivery dataset or a complete written scoring specification. Any scoring formula, "
        "eligibility check, or data-cleaning step should be backed by the project notebook/source code in the "
        "final submission."
    )


def page_methodology(bat: pd.DataFrame, bowl: pd.DataFrame) -> None:
    st.subheader("Data and methodology")
    st.markdown("### Data supplied")
    st.write(f"- Batter dataset: **{len(bat):,} players × {len(bat.columns):,} fields**.")
    st.write(f"- Bowler dataset: **{len(bowl):,} players × {len(bowl.columns):,} fields**.")

    st.markdown("### Analysis workflow")
    st.code(WORKFLOW_STEPS, language="text")

    st.markdown("### Selection principles")
    st.write(
        "- **Batters:** run production, batting average, strike rate, boundary and dot-ball profile, "
        "innings milestones, consistency and phase contribution."
    )
    st.write(
        "- **Bowlers:** wickets, economy, bowling average, strike rate, phase-wise wickets/economy, "
        "dot-ball and boundary percentages, plus match-to-match consistency."
    )
    st.write(
        "- **Context matters:** a high strike rate, low economy or high wicket count should not be used alone. "
        "Consider sample size, role, phase and trade-offs."
    )
    st.warning(
        "Transparency requirement: the CSVs contain scouting scores but not the complete formulas/weights behind "
        "every score. Add the actual notebook methodology here before presenting this as a reproducible scoring "
        "model; do not claim weights that are not documented."
    )

    st.markdown("### Important eligibility check")
    st.write(
        "If the project requirement is 'internationally uncapped', verify each player's senior men's international "
        "appearances across all formats using a reliable source and record the check date/source. "
        "The two CSVs alone cannot prove international eligibility."
    )


def page_batter_scouting(bat: pd.DataFrame, bowl: pd.DataFrame) -> None:
    st.subheader("Batter scouting")
    st.caption(
        "Select a batter to inspect the supplied profile. Charts compare the five shortlisted batters; "
        "they are descriptive, not proof of causation."
    )

    selected = st.selectbox("Select batter", bat["Player"].tolist())
    row = bat.loc[bat["Player"] == selected].iloc[0]

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Runs", fmt_num(row["Runs"], 0))
    k2.metric("Batting average", fmt_num(row["Batting_Average"], 2))
    k3.metric("Strike rate", fmt_num(row["Strike_Rate"], 2))
    k4.metric("Innings", fmt_num(row["Innings"], 0))

    # Row 1: phase runs and efficiency
    left, right = st.columns(2)
    with left:
        phase_cols = existing(bat, ["Runs_Powerplay", "Runs_Middle_Overs", "Runs_Death_Overs"])
        if phase_cols:
            data = bat[["Player"] + phase_cols].melt(id_vars="Player", var_name="Phase", value_name="Phase_Runs")
            data["Phase"] = data["Phase"].str.replace("Runs_", "", regex=False).str.replace("_", " ")
            fig = px.bar(data, x="Player", y="Phase_Runs", color="Phase", barmode="group",
                         title="Phase-wise runs", labels={"Phase_Runs": "Runs"})
            show_chart(fig)
    with right:
        hover = existing(bat, ["Innings", "Innings_50Plus", "Innings_100Plus"])
        fig = px.scatter(
            bat, x="Strike_Rate", y="Batting_Average", size="Runs", color="Player",
            hover_data=hover, title="Batting average vs strike rate",
        )
        show_chart(fig)

    # Row 2: innings milestones and consistency
    left, right = st.columns(2)
    with left:
        milestone_cols = {
            "Innings_30Plus": "30+", "Innings_50Plus": "50+", "Innings_100Plus": "100+",
        }
        available = [c for c in milestone_cols if c in bat.columns]
        if available:
            data = bat[["Player", "Innings"] + available].copy()
            for col in available:
                data[col] = data[col] / data["Innings"].where(data["Innings"] > 0) * 100
            data = data.melt(id_vars=["Player", "Innings"], value_vars=available,
                             var_name="Milestone", value_name="Share_of_innings")
            data["Milestone"] = data["Milestone"].map(milestone_cols)
            fig = px.bar(
                data, x="Player", y="Share_of_innings", color="Milestone", barmode="group",
                hover_data=["Innings"], title="Innings milestones (% of innings)",
                labels={"Share_of_innings": "% of innings"},
            )
            show_chart(fig)
    with right:
        if has_all(bat, ["Mean_Innings_Runs", "Median_Innings_Runs"]):
            data = bat[["Player", "Mean_Innings_Runs", "Median_Innings_Runs"]].melt(
                id_vars="Player", var_name="Measure", value_name="Innings_Score")
            data["Measure"] = data["Measure"].str.replace("_Innings_Runs", "", regex=False)
            fig = px.bar(data, x="Player", y="Innings_Score", color="Measure", barmode="group",
                         title="Mean vs median innings score", labels={"Innings_Score": "Runs per innings"})
            show_chart(fig)
            st.caption("A large gap between mean and median suggests reliance on a few big innings.")

    st.markdown("#### Selected player's profile")
    render_metric_grid(row, BATTER_PROFILE_SPECS)

    st.markdown("#### Phase and scouting labels")
    st.write(f"**Primary phase:** {row.get('Primary_Phase', 'Not supplied')}")
    st.write(f"**Phase role:** {row.get('Phase_Role', 'Not supplied')}")
    st.write(f"**Scouting tier:** {row.get('Scouting_Tier', 'Not supplied')}")

    with st.expander("All supplied metrics for this batter"):
        show_table(row.astype(str).to_frame("Value"))


def page_bowler_scouting(bat: pd.DataFrame, bowl: pd.DataFrame) -> None:
    st.subheader("Fast-bowler scouting")
    st.caption(
        "Select a bowler to inspect the supplied profile. Charts compare the five shortlisted bowlers; "
        "they are descriptive, not proof of causation."
    )

    selected = st.selectbox("Select bowler", bowl["Bowler"].tolist())
    row = bowl.loc[bowl["Bowler"] == selected].iloc[0]

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Wickets", fmt_num(row["Wickets"], 0))
    k2.metric("Economy", fmt_num(row["Economy"], 2))
    k3.metric("Bowling average", fmt_num(row["Bowling_Average"], 2))
    k4.metric("Bowling strike rate", fmt_num(row["Strike_Rate"], 2))

    wicket_cols = [f"{p}_Wickets" for p in BOWLING_PHASES]
    economy_cols = [f"{p}_Economy" for p in BOWLING_PHASES]

    # Row 1: phase wickets and overall effectiveness
    left, right = st.columns(2)
    with left:
        if has_all(bowl, wicket_cols):
            data = bowl[["Bowler"] + wicket_cols].melt(id_vars="Bowler", var_name="Phase", value_name="Phase_Wickets")
            data["Phase"] = data["Phase"].str.replace("_Wickets", "", regex=False)
            fig = px.bar(data, x="Bowler", y="Phase_Wickets", color="Phase", barmode="group",
                         title="Wickets by phase", labels={"Phase_Wickets": "Wickets"})
            show_chart(fig)
    with right:
        hover = existing(bowl, ["Bowling_Average", "Strike_Rate", "Matches_With_Wickets_Pct"])
        fig = px.scatter(bowl, x="Economy", y="Wickets", size="Matches", color="Bowler",
                         hover_data=hover, title="Wickets vs economy (lower economy is better)")
        show_chart(fig)

    # Row 2: new visualisations
    left, right = st.columns(2)
    with left:
        if has_all(bowl, economy_cols):
            data = bowl[["Bowler"] + economy_cols].melt(id_vars="Bowler", var_name="Phase", value_name="Phase_Economy")
            data["Phase"] = data["Phase"].str.replace("_Economy", "", regex=False)
            fig = px.bar(data, x="Bowler", y="Phase_Economy", color="Phase", barmode="group",
                         title="Economy by phase (lower is better)", labels={"Phase_Economy": "Economy"})
            show_chart(fig)
        else:
            st.info("Phase economy columns are not available in the supplied file.")
    with right:
        if has_all(bowl, ["Economy_SD", "Matches_With_Wickets_Pct"]):
            fig = px.scatter(
                bowl, x="Economy_SD", y="Matches_With_Wickets_Pct", size="Matches", color="Bowler",
                title="Consistency: wicket-taking reliability vs economy variability",
                labels={"Economy_SD": "Economy std. deviation (lower = steadier)",
                        "Matches_With_Wickets_Pct": "Matches with a wicket (%)"},
            )
            show_chart(fig)
            st.caption("Upper-left is the preferred zone: takes wickets regularly with a steady economy.")
        else:
            st.info("Consistency columns are not available in the supplied file.")

    st.markdown("#### Selected bowler's phase profile")
    render_metric_grid(row, BOWLER_PROFILE_SPECS)

    with st.expander("All supplied metrics for this bowler"):
        show_table(row.astype(str).to_frame("Value"))


def page_metric_dictionary(bat: pd.DataFrame, bowl: pd.DataFrame) -> None:
    st.subheader("Metric dictionary")
    st.write(
        "Definitions below describe the standard interpretation of the field names. Confirm them against the "
        "calculation code/notebook before final submission, especially custom scores and any dataset-specific "
        "dismissal or ball-count rules."
    )
    for section, items in METRIC_DICTIONARY.items():
        st.markdown(f"### {section} metrics")
        show_table(pd.DataFrame(items, columns=["Metric", "Meaning / interpretation"]), hide_index=True)
    st.warning(
        "Do not replace undefined average/strike-rate values with zero when the denominator is zero. "
        "'Undefined' means the metric cannot be calculated, not that the player performed at zero."
    )


def page_recommendations(bat: pd.DataFrame, bowl: pd.DataFrame) -> None:
    st.subheader("Final recommendations")
    st.write(
        "Use the shortlist as a group of candidates for further review, not as an automatic final World Cup squad. "
        "A recommendation should combine statistical evidence with role requirements, opposition/context, "
        "fitness, fielding, and eligibility checks."
    )

    st.markdown("### Batters: what the supplied data indicates")
    sort_col = "Final_Performance_Score" if "Final_Performance_Score" in bat.columns else "Runs"
    for _, r in bat.sort_values(sort_col, ascending=False).iterrows():
        st.markdown(
            f"**{r['Player']}**: {fmt_num(r['Runs'], 0)} runs, average {fmt_num(r['Batting_Average'], 2)}, "
            f"strike rate {fmt_num(r['Strike_Rate'], 2)}. "
            f"Phase label: {r.get('Phase_Role', 'not supplied')}; tier: {r.get('Scouting_Tier', 'not supplied')}."
        )

    st.markdown("### Bowlers: what the supplied data indicates")
    phase_wicket_cols = [f"{p}_Wickets" for p in BOWLING_PHASES]
    for _, r in bowl.sort_values("Wickets", ascending=False).iterrows():
        text = (
            f"**{r['Bowler']}**: {fmt_num(r['Wickets'], 0)} wickets in {fmt_num(r['Matches'], 0)} matches; "
            f"economy {fmt_num(r['Economy'], 2)}, bowling average {fmt_num(r['Bowling_Average'], 2)}, "
            f"strike rate {fmt_num(r['Strike_Rate'], 2)}."
        )
        if has_all(bowl, phase_wicket_cols):
            phase_text = " / ".join(fmt_num(r[c], 0) for c in phase_wicket_cols)
            text += f" Phase wickets (Powerplay / middle / death): {phase_text}."
        st.markdown(text)

    st.markdown("### Before final submission")
    for step in [
        "Attach the Jupyter Notebook and any Excel workbooks used.",
        "Document every custom score's formula, normalisation, weights and treatment of missing values.",
        "Show source-data dates, competition coverage, exclusions and validation checks.",
        "Verify senior men's international caps and record sources for every candidate.",
        "Add role-fit conclusions that follow from the evidence, including trade-offs and sample-size caveats.",
    ]:
        st.write(f"- {step}")


def page_data_explorer(bat: pd.DataFrame, bowl: pd.DataFrame) -> None:
    st.subheader("Data explorer and supporting files")
    for title, df, filename, key in [
        ("Batter CSV", bat, BATTER_FILE, "dl_bat"),
        ("Bowler CSV", bowl, BOWLER_FILE, "dl_bowl"),
    ]:
        st.markdown(f"### {title}")
        show_table(df, hide_index=True)
        st.download_button(
            f"Download {title.lower()}", df.to_csv(index=False).encode("utf-8"),
            filename, "text/csv", key=key,
        )
    st.caption(
        "The CSV files are supporting materials. The presentation, reproducible notebook, and any workbook used "
        "should be submitted alongside them."
    )


PAGES: dict[str, Callable[[pd.DataFrame, pd.DataFrame], None]] = {
    "Executive Summary": page_executive_summary,
    "Data & Methodology": page_methodology,
    "Batter Scouting": page_batter_scouting,
    "Bowler Scouting": page_bowler_scouting,
    "Metric Dictionary": page_metric_dictionary,
    "Final Recommendations": page_recommendations,
    "Data Explorer & Downloads": page_data_explorer,
}


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    render_header()

    with st.sidebar:
        st.title("Scouting navigation")
        page = st.radio("Go to", list(PAGES.keys()))
        st.divider()
        st.caption("Use the upload controls below if the CSV files are stored elsewhere.")
        bat_upload = st.file_uploader("Upload final batter CSV", type="csv", key="bat_csv")
        bowl_upload = st.file_uploader("Upload final bowler CSV", type="csv", key="bowl_csv")

    bat = load_csv(BATTER_FILE, bat_upload)
    bowl = load_csv(BOWLER_FILE, bowl_upload)

    if bat is None or bowl is None:
        st.warning(
            f"One or both CSV files were not found. Place {BATTER_FILE} and {BOWLER_FILE} "
            "beside app.py, or upload them in the sidebar."
        )
        st.stop()

    validate_columns(bat, REQUIRED_BATTER_COLS, "batter")
    validate_columns(bowl, REQUIRED_BOWLER_COLS, "bowler")

    bat = bat.copy()
    bowl = bowl.copy()
    bat["Player"] = bat["Player"].astype(str)
    bowl["Bowler"] = bowl["Bowler"].astype(str)

    PAGES[page](bat, bowl)


main()
