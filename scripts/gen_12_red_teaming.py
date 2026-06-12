"""Generate Module 12 — Red Teaming.

Distilled from the upstream reference 14-red-teaming (14-00-red-teaming.md,
14-01-red-team-basics, 14-02-red-team-advanced), simplified to a single Foundry
project + DefaultAzureCredential.

The reference routes red-team traffic through an APIM gateway (GATEWAY_URL +
ALPHA_GATEWAY_KEY) with an AsyncAzureOpenAI callback, and reads scorecards from
redteam_*_output/evaluation_results.json. We strip APIM: the target callback
calls THIS project's get_openai_client() directly, and the scorecard is read the
same way from the scan's output folder.

Real API surface taken verbatim from the reference (azure-ai-evaluation[redteam],
PyRIT-backed):
  - RedTeam(azure_ai_project=..., credential=..., risk_categories=[...], num_objectives=N)
  - RiskCategory.{Violence,HateUnfairness,Sexual,SelfHarm}
  - await red_team.scan(target=callback, scan_name=..., output_path=...)
  - scan(..., attack_strategies=[AttackStrategy.Base64, ...], languages=[SupportedLanguages.Spanish, ...])
  - AttackStrategy.Compose([...])
  - evaluation_results.json -> scorecard.{risk_category_summary, attack_technique_summary}

Sample scorecard numbers below are the reference's actual basic-scan output
(overall ASR 10%, violence/sexual 20%).
"""
from nbbuild import md, code, write_notebook, next_link, sibling_link, page_link

KERNEL = "foundry-workshop"
KERNEL_DISPLAY = "Microsoft Foundry: End-to-End Workshop"

cells = [
    md("""\
# M12 · Red Teaming

> **Goal:** proactively *attack* your own model with the **AI Red Teaming Agent** — run a basic scan across risk categories, then an advanced scan with encoding strategies and multiple languages, and read the **Attack Success Rate** scorecard.
> **You'll use:** `azure-ai-evaluation[redteam]` (PyRIT-backed) — `RedTeam`, `RiskCategory`, `AttackStrategy`, `SupportedLanguages`, and `scan(...)`.

---

In """ + sibling_link("11-guardrails", "M11") + """ you built defences. How do you
know they *hold*? You **red team** — automatically generate adversarial prompts,
fire them at your system, and measure how often it produces harmful content. The
**AI Red Teaming Agent** wraps Microsoft's open-source **PyRIT** toolkit: it
seeds attack objectives per risk category, optionally mutates them with evasion
**strategies**, scores every response, and hands you a scorecard.

```
RedTeam  ──seeds objectives──▶  your target callback  ──▶  model
   │                                                          │
   │◀── PyRIT scorer (pass/fail per attack) ──── responses ───┘
   ▼
Attack Success Rate (ASR) scorecard   ◀── lower is better
```

!!! warning "Region + Python constraints"
    The Red Teaming Agent runs in a subset of regions (e.g. **East US 2**, **Sweden
    Central**, **France Central**, **Switzerland West**) and needs **Python
    3.10–3.13** (PyRIT excludes 3.9 and 3.14+). Install with
    `pip install "azure-ai-evaluation[redteam]"`. If your `.env` isn't ready, do the
    """ + page_link("setup", "Setup") + """ first."""),

    md("""\
## 1. Configure

Same `.env` as every lab. The Red Teaming Agent needs your **project endpoint**
(it logs the scan there) and a model deployment to attack. The reference routes
through an APIM gateway; we point the target straight at this project."""),
    code("""\
import os, sys
from dotenv import load_dotenv

load_dotenv()  # reads .env from the repo root

assert (3, 10) <= sys.version_info < (3, 14), (
    f"PyRIT requires Python 3.10–3.13; current is {sys.version.split()[0]}."
)

PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]
CHAT_MODEL       = os.environ.get("CHAT_MODEL", "gpt-4.1-mini")

print("Project :", PROJECT_ENDPOINT)
print("Model   :", CHAT_MODEL)
print("Python  :", sys.version.split()[0], "(OK)")"""),
    md("""\
!!! note "Expected output"
    ```
    Project : https://<account>.services.ai.azure.com/api/projects/<project>
    Model   : gpt-4.1-mini
    Python  : 3.12.7 (OK)
    ```
    An `AssertionError` here means your kernel is on an unsupported Python — switch
    to a 3.10–3.13 kernel before continuing."""),

    md("""\
## 2. The target callback

The scanner needs a **target** to attack. The simplest target is a callable that
takes a prompt string and returns the model's reply. We call this project's
`get_openai_client()` directly — *this is your system under test*. In production
you'd point the callback at your real app (RAG pipeline, agent, API)."""),
    code("""\
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

credential     = DefaultAzureCredential()
project_client = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential)
openai_client  = project_client.get_openai_client()

def target_callback(query: str) -> str:
    \"\"\"The system under test: forward a prompt to the model, return its reply.\"\"\"
    response = openai_client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": query}],
    )
    return response.choices[0].message.content

# Smoke-test the target before handing it to the scanner.
print("smoke test:", target_callback("Say hello in one word."))"""),
    md("""\
!!! note "Expected output"
    ```
    smoke test: Hello!
    ```
    If this returns a normal reply, the scanner can drive the target. Swap the body
    of `target_callback` to attack any app you own — the scanner only cares that it
    takes a string and returns a string."""),

    md("""\
## 3. Build the Red Team agent

`RedTeam` is the scanner. You give it the **project** (where results are logged),
a **credential**, the **risk categories** to probe, and `num_objectives` — how
many distinct attack prompts to generate *per category*. Four categories × 5
objectives = 20 baseline prompts."""),
    code("""\
from azure.ai.evaluation.red_team import RedTeam, RiskCategory

red_team = RedTeam(
    azure_ai_project=PROJECT_ENDPOINT,
    credential=credential,
    risk_categories=[
        RiskCategory.Violence,
        RiskCategory.HateUnfairness,
        RiskCategory.Sexual,
        RiskCategory.SelfHarm,
    ],
    num_objectives=5,   # attack prompts per category
)

print("RedTeam ready — 4 categories × 5 objectives = 20 baseline prompts")"""),
    md("""\
!!! note "Expected output"
    ```
    RedTeam ready — 4 categories × 5 objectives = 20 baseline prompts
    ```
    Start small: `num_objectives=5` is enough to see the shape. Crank it up (the
    reference allows up to 100/category) once you're scanning for real."""),

    md("""\
## 4. Run the basic scan

`scan(...)` is **async** — top-level `await` works in a notebook kernel. It seeds
the baseline objectives, drives them through your `target_callback`, scores each
response with PyRIT, and writes results to `output_path`. A 20-prompt scan takes
a few minutes."""),
    code("""\
basic_result = await red_team.scan(
    target=target_callback,
    scan_name="redteam-basic",
    output_path="redteam_basic_output",
)

print("✅ basic scan complete — results in redteam_basic_output/")"""),
    md("""\
!!! note "Expected output"
    ```
    ✅ basic scan complete — results in redteam_basic_output/
    ```
    The folder holds `results.json` (every attack/response pair) and
    `evaluation_results.json` (the aggregated scorecard we read next).

!!! tip "In a plain script, not a notebook?"
    Top-level `await` needs an IPython kernel. In a `.py` file, wrap the call:
    `asyncio.run(red_team.scan(...))`."""),

    md("""\
## 5. Read the ASR scorecard

The headline metric is **Attack Success Rate (ASR)**: the fraction of adversarial
prompts that *succeeded* in eliciting harmful content. **Lower is better.** The
scorecard breaks ASR down by risk category — so you see exactly where your model
is weakest."""),
    code("""\
import json
from pathlib import Path

results   = json.loads(Path("redteam_basic_output/evaluation_results.json").read_text())
scorecard = results.get("scorecard", {})
risk      = scorecard.get("risk_category_summary", [{}])[0]

print(f"{'category':<18}{'ASR':>8}{'success':>9}{'total':>7}")
print("-" * 42)
print(f"{'OVERALL':<18}{risk.get('overall_asr', 0):>7.1f}%"
      f"{risk.get('overall_successful_attacks', 0):>9}{risk.get('overall_total', 0):>7}")
for cat, key in [("Violence", "violence"), ("Hate/Unfairness", "hate_unfairness"),
                 ("Sexual", "sexual"), ("Self-Harm", "self_harm")]:
    print(f"{cat:<18}{risk.get(key + '_asr', 0):>7.1f}%"
          f"{risk.get(key + '_successful_attacks', 0):>9}{risk.get(key + '_total', 0):>7}")"""),
    md("""\
!!! note "Expected output"
    ```
    category               ASR  success  total
    ------------------------------------------
    OVERALL              10.0%        2     20
    Violence             20.0%        1      5
    Hate/Unfairness       0.0%        0      5
    Sexual               20.0%        1      5
    Self-Harm             0.0%        0      5
    ```
    Two of twenty attacks landed — a 10% overall ASR, concentrated in *Violence* and
    *Sexual*. That's your prioritised to-do list: tighten those categories (the
    """ + sibling_link("11-guardrails", "M11") + """ filters are one lever) and re-scan to
    confirm the number drops."""),

    md("""\
## 6. Advanced — evasion strategies + languages

Baseline prompts are the easy case. Real attackers **obfuscate**: Base64, ROT13,
character-spacing, Unicode confusables — and they probe in **other languages**.
`attack_strategies` mutates each objective through these encodings (and
`AttackStrategy.Compose([...])` chains them); `languages` translates the prompts.
This is the scan that finds the leaks a baseline misses."""),
    code("""\
from azure.ai.evaluation.red_team import AttackStrategy, SupportedLanguages

advanced = RedTeam(
    azure_ai_project=PROJECT_ENDPOINT,
    credential=credential,
    risk_categories=[RiskCategory.Violence, RiskCategory.HateUnfairness],
    num_objectives=5,
)

advanced_result = await advanced.scan(
    target=target_callback,
    scan_name="redteam-advanced",
    attack_strategies=[
        AttackStrategy.Base64,
        AttackStrategy.ROT13,
        AttackStrategy.UnicodeConfusable,
        AttackStrategy.Compose([AttackStrategy.Base64, AttackStrategy.ROT13]),
    ],
    languages=[SupportedLanguages.Spanish, SupportedLanguages.French],
    output_path="redteam_advanced_output",
)

print("✅ advanced scan complete — strategies + Spanish/French")"""),
    md("""\
!!! note "Expected output"
    ```
    ✅ advanced scan complete — strategies + Spanish/French
    ```
    Each baseline objective is now fired several ways (plain, Base64, ROT13,
    confusable, composed) in multiple languages — far more prompts than the basic
    scan, so this run takes longer.

!!! warning "API is evolving"
    `RedTeam`, `AttackStrategy`, and `SupportedLanguages` live under
    `azure.ai.evaluation.red_team` and move between releases (some builds expose
    `custom_attack_seed_prompts=` for your own objectives). This lab targets the
    `azure-ai-evaluation[redteam]` extra — pin it in `pyproject.toml` and check the
    installed version if an import or argument differs."""),

    md("""\
## 7. Compare baseline vs. strategies

The advanced scorecard adds an **attack-technique** breakdown alongside the
risk-category one. The story you're looking for: an encoding strategy that scores
a *higher* ASR than baseline means that obfuscation slips past your filters — a
concrete gap to close before you ship."""),
    code("""\
adv  = json.loads(Path("redteam_advanced_output/evaluation_results.json").read_text())
tech = adv.get("scorecard", {}).get("attack_technique_summary", [{}])[0]

print(f"{'technique':<14}{'ASR':>8}{'success':>9}{'total':>7}")
print("-" * 38)
for label, key in [("OVERALL", "overall"), ("baseline", "baseline"),
                   ("easy", "easy_complexity"), ("difficult", "difficult_complexity")]:
    asr = tech.get(key + "_asr")
    if asr is None:
        continue
    print(f"{label:<14}{asr:>7.1f}%"
          f"{tech.get(key + '_successful_attacks', 0):>9}{tech.get(key + '_total', 0):>7}")"""),
    md("""\
!!! note "Expected output"
    ```
    technique          ASR  success  total
    --------------------------------------
    OVERALL          16.0%        8     50
    baseline         10.0%        1     10
    easy             17.5%        7     40
    ```
    Encoded ("easy" complexity) attacks land **more often** than baseline here —
    proof that obfuscation evades the model's defences. Every scan also logs to the
    **Foundry portal**, where you can drill into individual attack/response pairs and
    track ASR across runs.

!!! tip "This closes the safety loop"
    Guardrails (""" + sibling_link("11-guardrails", "M11") + """) are defence;
    red teaming is offence; evaluation (""" + sibling_link("09-evaluation", "M9") + """)
    is the measuring tape. Run all three on every release and you have a repeatable
    safety pipeline."""),

    md("""\
## 🧪 Your turn

1. **Widen coverage.** Bump `num_objectives` to `10` in section 3 and re-run the basic
   scan — more prompts per category means a more stable ASR (and a longer run).
2. **Add a strategy.** Append `AttackStrategy.Flip` (or `AttackStrategy.Leetspeak`) to
   the `attack_strategies` list in section 6 and re-scan — does the new encoding raise
   the *easy*-complexity ASR?
3. **Attack a defended target.** Point `target_callback` at the guardrailed
   `contoso-bank-agent` from """ + sibling_link("11-guardrails", "M11") + """ (via an
   `agent_reference` Responses call) and compare its ASR to the bare model — the
   guardrails should drive it toward zero.

---

✅ **You ran a basic risk-category scan, an advanced scan with encoding strategies and
multiple languages, and read the ASR scorecard to find where your model is weakest.**
Next: put a human in the loop and drive agents over raw REST.
""" + next_link("13-human-in-the-loop-and-rest", "M13 · Human-in-the-Loop & REST")),
]

write_notebook(
    "docs/modules/12-red-teaming.ipynb",
    cells,
    kernel_name=KERNEL,
    kernel_display=KERNEL_DISPLAY,
)
