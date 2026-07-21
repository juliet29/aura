import polars as pl

from aura2.validation.p2ep.paths import NORM_BY, QOIS, VALIDATE


def rmse():
    cols = ["datetimes", "room"] + [q.nickname for q in QOIS]
    ref = pl.read_parquet(VALIDATE.qois("reference")).select(cols)
    built = pl.read_parquet(VALIDATE.qois("built")).select(cols)
    j = ref.join(built, on=["datetimes", "room"], suffix="_built")

    rows = []
    for room in sorted(j["room"].unique().to_list()):
        d = j.filter(pl.col("room") == room)
        row = {"room": room}
        for q in QOIS:
            n = q.nickname
            err = d[n] - d[f"{n}_built"]
            rms = float((err**2).mean() ** 0.5)
            denom = (
                float(d[n].max() - d[n].min())
                if NORM_BY[n] == "range"
                else float(d[n].max())
            )
            row[f"{n}_rmse"] = round(rms, 2)
            row[f"{n}_n%"] = round(100 * rms / denom, 1) if abs(denom) > 1e-9 else None
        rows.append(row)

    table = pl.DataFrame(rows)
    with pl.Config(tbl_rows=-1, tbl_cols=-1, tbl_width_chars=200):
        print(table)
    return table
