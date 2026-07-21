configfile: "config/campaign.yaml"

from aura2.analysis.build import FIGURES
from aura2.pipeline.defn import CAMPAIGN_NAME, campaign_defn
from aura2.pipeline.design import enumerate_specs
from aura2.pipeline.paths import CampaignPaths, case_adj, case_geom

SPECS = enumerate_specs(campaign_defn)
SPEC = {s.id: s for s in SPECS}
IDS = list(SPEC)
BASE_IDS = [s.id for s in SPECS if s.modification is None]
CP = CampaignPaths(CAMPAIGN_NAME)
FIGURE_NAMES = list(FIGURES)
# pressure_geom(_alt) have their own rules (need baseline idfs, not just sql)
GEOM_FIGURES = ["pressure_geom", "pressure_geom_alt"]
CHART_FIGURES = [n for n in FIGURE_NAMES if n not in GEOM_FIGURES]


rule all:
    input:
        str(CP.dataset),
        expand(str(CP.figure("{name}")), name=FIGURE_NAMES),


rule manifest:
    output:
        str(CP.manifest),
    shell:
        "uv run au campaign manifest --out {output}"


rule transform:
    output:
        geom=str(case_geom("{case}")),
    shell:
        "uv run au campaign transform --case {wildcards.case}"


rule build:
    input:
        manifest=str(CP.manifest),
        geom=lambda wc: str(case_geom(SPEC[wc.id].case_name)),
        adj=lambda wc: str(case_adj(SPEC[wc.id].case_name)),
    output:
        str(CP.exp_idf("{id}")),
    shell:
        "uv run au campaign build --id {wildcards.id} --manifest {input.manifest} --idf-path {output}"


rule run:
    input:
        str(CP.exp_idf("{id}")),
    output:
        str(CP.exp_sql("{id}")),
    params:
        epw=config["epw"],
        ap=config["analysis_period"],
    shell:
        "uv run au campaign run --id {wildcards.id} --idf-path {input} --sql-path {output} "
        "--epw {params.epw} "
        "--period-name {params.ap[name]} --st-month {params.ap[st_month]} "
        "--end-month {params.ap[end_month]} --st-day {params.ap[st_day]} --end-day {params.ap[end_day]}"


rule qoi:
    input:
        idf=str(CP.exp_idf("{id}")),
        sql=str(CP.exp_sql("{id}")),
    output:
        str(CP.exp_qoi("{id}")),
    shell:
        "uv run au campaign qoi --id {wildcards.id} --idf-path {input.idf} --sql-path {input.sql} --out {output}"


rule dataset:
    input:
        q=expand(str(CP.exp_qoi("{id}")), id=IDS),
        manifest=str(CP.manifest),
    output:
        str(CP.dataset),
    shell:
        "uv run au campaign dataset --in-paths {input.q} --manifest {input.manifest} --out {output}"


rule figure:
    wildcard_constraints:
        name="|".join(CHART_FIGURES),
    input:
        expand(str(CP.exp_sql("{id}")), id=IDS),
    output:
        str(CP.figure("{name}")),
    shell:
        "uv run au campaign figure --name {wildcards.name} --out {output}"


rule pressure_geom:
    input:
        sql=expand(str(CP.exp_sql("{id}")), id=BASE_IDS),
        idf=expand(str(CP.exp_idf("{id}")), id=BASE_IDS),
    output:
        str(CP.figure("pressure_geom")),
    shell:
        "uv run au campaign figure --name pressure_geom --out {output}"


rule pressure_geom_alt:
    input:
        sql=expand(str(CP.exp_sql("{id}")), id=BASE_IDS),
        idf=expand(str(CP.exp_idf("{id}")), id=BASE_IDS),
    output:
        str(CP.figure("pressure_geom_alt")),
    shell:
        "uv run au campaign figure --name pressure_geom_alt --out {output}"
