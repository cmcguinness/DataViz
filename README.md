# DataViz

A collection of small, self-contained data visualization projects. Each lives in its own
date-prefixed folder with its data, the scripts that produce the chart, and the output.

## Projects

| Folder | Description |
|---|---|
| [`20261001-measles`](20261001-measles/) | 2026 measles cases per 100,000 residents by state, colored relative to the national rate |

## Setup

All projects share one Python virtual environment at the repo root:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

PNG export uses [Kaleido](https://github.com/plotly/Kaleido), which needs Google Chrome installed.

## License

Code and derived data are dedicated to the public domain under [CC0 1.0](LICENSE).
Source data belongs to the agencies credited in each project.
