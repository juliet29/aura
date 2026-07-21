from aura2.pipeline.design import DefinitionDict, Option, Variable

CAMPAIGN_NAME = "real_plans"

campaign_defn = DefinitionDict(
    case_names=["a", "b", "c"],
    modifications=[
        Variable(
            name="window_dimension",
            options=[Option("-30%"), Option("Default", IS_DEFAULT=True), Option("+30%")],
        ),
        Variable(
            name="door_vent_schedule",
            options=[
                Option("Always Closed"),
                Option("Dynamic"),
                Option("Always Open", IS_DEFAULT=True),
            ],
        ),
        Variable(
            name="construction_set",
            options=[Option("Light"), Option("Medium", IS_DEFAULT=True), Option("Heavy")],
        ),
    ],
)
