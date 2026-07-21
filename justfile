campaign-dag:
  uv run snakemake -n all

campaign cores="1":
  uv run snakemake -c {{cores}} all

campaign-clear:
  rm -rIv /scratch/users/jnwagwu/aura/4_temp/campaigns/*

# submit the full campaign to SLURM (apptainer, summer period); run from a login node
campaign-submit:
  sbatch workflow/run_campaign.sbatch

# monitor the submitted campaign job (queue state + log tail); pass -w to watch
campaign-monitor *args:
  workflow/monitor_campaign.sh {{args}}

# regenerate sensitivity/factor-spread tables (+ climate-split sections & SUMMARY.md)
campaign-tables out="/scratch/users/jnwagwu/aura/5_figures/real_plans/tables":
  uv run au campaign tables --split-climate --out {{out}}
