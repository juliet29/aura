import polars as pl

CSET = "construction_set"
DOOR_VENT = "door_vent_schedule"
WIN_DIM = "window_dimension"

ORDER = "order"
CATEGORY_NAMES = "categ_names"

nice_category_names = {
    CSET: "Construction Type",
    DOOR_VENT: "Door Ventilation Schedule",
    WIN_DIM: "Window Dimension",
}


def edit_cset(df: pl.DataFrame):
    expr = (
        pl.when(pl.col.option == "Light").then(0)
        .when(pl.col.option == "Default").then(1)
        .otherwise(2).alias(ORDER)
    )
    return df.filter(pl.col.category == CSET).with_columns(expr)


def edit_win_dim(df: pl.DataFrame):
    expr = (
        pl.when(pl.col.option == "+30%").then(0)
        .when(pl.col.option == "Default").then(1)
        .otherwise(2).alias(ORDER)
    )
    return df.filter(pl.col.category == WIN_DIM).with_columns(expr)


def edit_door_vent(df: pl.DataFrame):
    expr = (
        pl.when(pl.col.option == "Default").then(1)
        .when(pl.col.option == "Dynamic").then(0)
        .otherwise(2).alias(ORDER)
    )
    return df.filter(pl.col.category == DOOR_VENT).with_columns(expr)


def add_order_to_temp_df(df: pl.DataFrame):
    parts = [edit_cset(df), edit_win_dim(df), edit_door_vent(df)]
    return pl.concat(parts).with_columns(
        pl.col.category.replace_strict(nice_category_names).alias(CATEGORY_NAMES)
    )
