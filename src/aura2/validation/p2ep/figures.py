import altair as alt
import polars as pl
from plyze.qoi.data.interfaces import CaseQOIandData

from aura2.validation.p2ep.paths import QOIS, VALIDATE


def timeseries():
    cases = [
        CaseQOIandData.read(VALIDATE.qois(name))
        for name in ("reference", "built")
    ]
    cols = ["datetimes", "room", "temp", "vent_vol", "mix_vol"]
    df = pl.concat(
        [c.dataframe.select(cols).with_columns(case=pl.lit(c.case_name)) for c in cases]
    )

    def qoi_chart(qoi):
        return (
            alt.Chart(df, title=qoi.label)
            .mark_line()
            .encode(
                x=alt.X("datetimes:T").title("Time"),
                y=alt.Y(f"{qoi.nickname}:Q").title(qoi.unit).scale(zero=False),
                color=alt.Color("case:N").title("Case"),
            )
            .properties(width=220, height=130)
            .facet(column=alt.Column("room:N").title(None))
        )

    chart = alt.vconcat(*[qoi_chart(q) for q in QOIS]).resolve_scale(color="independent")
    chart.save(str(VALIDATE.figure("validation")))
    return chart
