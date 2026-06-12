"""Generate Module 14 — Fine-Tuning & Distillation.

Distilled from the upstream reference 15-fine-tune (15-00-fine-tune.md,
15-01-data-preparation, 15-02-fine-tune, 15-03-evaluate, 15-04-local-inference),
simplified to a single Foundry project + DefaultAzureCredential.

This lab is deliberately **concept-forward**. The real pipeline needs heavy ML
deps (torch, transformers<5, peft, olive-ai) and a GPU, so the cells *illustrate*
the distillation pipeline rather than run end-to-end in the workshop kernel — a
prominent warning says so and points at the optional `finetune` extra.

The reference: gpt-4.1-mini (teacher, via APIM) generates synthetic ISS
incident-severity training data; Phi-4-mini (student) is LoRA-fine-tuned with
Olive on a serverless ACA A100 GPU; teacher/base/fine-tuned accuracies are
compared; the adapter is loaded locally with PEFT. We strip APIM (teacher is this
project's CHAT_MODEL) and ACA/Bicep (the Olive job is shown as its real CLI
invocation, with a note that orchestration is a Platform concern).

Real shapes taken verbatim from the reference:
  - distillation: teacher writes a report then classifies it -> {system,user,assistant} jsonl
  - olive finetune --method lora --model_name_or_path microsoft/Phi-4-mini-instruct
      --data_name json --data_files train.jsonl
      --target_modules qkv_proj,o_proj,gate_up_proj,down_proj
  - eval: teacher vs base (~45.7%) vs fine-tuned (~51%) accuracy + matplotlib chart
  - local: AutoModelForCausalLM + PeftModel.from_pretrained(base, adapter); apply_chat_template
"""
from nbbuild import md, code, write_notebook, next_link, sibling_link, page_link

KERNEL = "foundry-workshop"
KERNEL_DISPLAY = "Microsoft Foundry: End-to-End Workshop"

cells = [
    md("""\
# M14 · Fine-Tuning & Distillation

> **Goal:** shrink a big model into a small, cheap one that mimics it — use a `gpt-4.1-mini` **teacher** to generate training data, then **LoRA-fine-tune** a small **student** (Phi-4-mini) with Olive/PEFT, and compare teacher vs. base vs. fine-tuned accuracy.
> **You'll use:** the **Responses/chat** API for distillation, **Olive** (`olive finetune --method lora`), and **PEFT** (`PeftModel`) for local adapter inference.

---

Big models are accurate but expensive; small models are cheap but generic.
**Knowledge distillation** gets you both: a strong **teacher** labels training
data, and a small **student** learns to imitate it on *your* narrow task. The
student then runs **offline on the edge** — no API bill, no network.

The pipeline you'll walk through (a real task: classifying ISS station-status
reports by incident severity):

```
teacher (gpt-4.1-mini) ──generates labelled data──▶ train.jsonl
                                                        │
                          Olive LoRA fine-tune (GPU) ◀──┘
                                  │
                          LoRA adapter  ──▶  evaluate: teacher vs base vs student
                                  │
                          load locally with PEFT  ──▶  offline inference
```

!!! warning "This lab is concept-forward — read before running"
    The full pipeline needs heavy ML dependencies (`torch`, `transformers<5`,
    `peft`, `olive-ai`) and a **GPU** for the fine-tune step. Those aren't in the base
    install — they live in an optional extra:
    ```bash
    pip install -e ".[finetune]"     # ~3 GB: torch + transformers + peft + olive
    ```
    The cells below **illustrate the key steps** so you understand the pipeline
    end-to-end. The data-prep and inference cells run on CPU; the **Olive fine-tune
    job needs a GPU** (the reference runs it on a serverless A100). Treat the GPU
    cells as a recipe, not something to execute in the workshop kernel."""),

    md("""\
## 1. Configure

Same `.env` as every lab. The **teacher** is this project's `CHAT_MODEL`; the
**student** is a small open-weights model we'll fine-tune (Phi-4-mini). Open
models matter here — their licences permit training derivative models on their
outputs."""),
    code("""\
import os, json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()  # reads .env from the repo root

PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]
TEACHER_MODEL    = os.environ.get("CHAT_MODEL", "gpt-4.1-mini")
STUDENT_MODEL    = os.environ.get("STUDENT_MODEL", "microsoft/Phi-4-mini-instruct")

DATA_DIR  = Path("finetune_data"); DATA_DIR.mkdir(exist_ok=True)
TRAIN_FILE = DATA_DIR / "train.jsonl"

print("Teacher :", TEACHER_MODEL, "(labels the data)")
print("Student :", STUDENT_MODEL, "(gets fine-tuned)")
print("Train   :", TRAIN_FILE)"""),
    md("""\
!!! note "Expected output"
    ```
    Teacher : gpt-4.1-mini (labels the data)
    Student : microsoft/Phi-4-mini-instruct (gets fine-tuned)
    Train   : finetune_data/train.jsonl
    ```
    Only the teacher is called over the API; the student is a local model id that
    Olive and PEFT download from Hugging Face."""),

    md("""\
## 2. The task: a domain classifier

Distillation needs a **narrow, well-defined task** the student can specialise in.
Ours: read an ISS daily status report and classify its severity
(`CRITICAL` / `WARNING` / `CAUTION` / `ADVISORY` / `NOMINAL`). A shared **prompt
builder** encodes the rubric — the teacher uses it to label data, and the student
learns to reproduce its output format exactly."""),
    code("""\
def create_classification_prompt(report_text: str) -> dict:
    \"\"\"System rubric + user report -> the messages the teacher (and student) see.\"\"\"
    system = (
        "You are an expert ISS Flight Controller. Classify the daily station status "
        "report into exactly one severity level.\\n\\n"
        "SEVERITY (highest to lowest):\\n"
        "1. CRITICAL  - immediate threat to crew safety or vehicle integrity.\\n"
        "2. WARNING   - loss of a critical system function or redundancy.\\n"
        "3. CAUTION   - degraded component performance or localized failure.\\n"
        "4. ADVISORY  - minor off-nominal condition, no impact.\\n"
        "5. NOMINAL   - normal operations.\\n\\n"
        "Respond in the format:\\nSEVERITY: <level>\\nREASON: <one sentence>"
    )
    return {"system": system, "user": f"Classify this report:\\n\\n{report_text}"}

example = create_classification_prompt("Coolant loop B pump showing degraded flow; crew swapped to backup. No crew impact.")
print(example["system"][:120], "...")
print("\\nUSER:", example["user"][:90], "...")"""),
    md("""\
!!! note "Expected output"
    ```
    You are an expert ISS Flight Controller. Classify the daily station status report ...
    USER: Classify this report:

    Coolant loop B pump showing degraded flow; crew swapped to backup. No ...
    ```
    The rubric *is* the task definition. A tight, deterministic output format
    (`SEVERITY: ...`) makes both labelling and scoring trivial."""),

    md("""\
## 3. Distillation — the teacher generates training data

This is the heart of distillation. For each scenario the teacher does **two
passes**: first *write* a realistic report (high temperature, for variety), then
*classify* it with the rubric (low temperature, for consistency). The `{system,
user, assistant}` triple it produces is one training example — synthetic data,
labelled by the strong model, in the exact format the student must learn."""),
    code("""\
openai_client = None  # set in a real run: AIProjectClient(...).get_openai_client()

def make_training_example(scenario: str) -> dict:
    \"\"\"Teacher writes a report for `scenario`, then labels it -> one training row.\"\"\"
    # Pass 1 — generate a synthetic report (creative).
    report = openai_client.chat.completions.create(
        model=TEACHER_MODEL, temperature=0.8, max_tokens=400,
        messages=[{"role": "system", "content": "Write a realistic 1-paragraph ISS daily status report."},
                  {"role": "user",   "content": f"Scenario: {scenario}"}],
    ).choices[0].message.content

    # Pass 2 — teacher classifies its own report (deterministic).
    p = create_classification_prompt(report)
    label = openai_client.chat.completions.create(
        model=TEACHER_MODEL, temperature=0.1, max_tokens=120,
        messages=[{"role": "system", "content": p["system"]},
                  {"role": "user",   "content": p["user"]}],
    ).choices[0].message.content

    return {"system": p["system"], "user": p["user"], "assistant": label}

SCENARIOS = ["routine maintenance day", "ammonia coolant leak detected",
             "thruster misfire during reboost", "science payload software crash"]

# In a real run, loop make_training_example over hundreds of scenarios. Here we
# write a couple of hand-labelled rows so the file format is concrete.
demo_rows = [
    {**create_classification_prompt("Nominal ops; all systems green; routine filter swap completed."),
     "assistant": "SEVERITY: NOMINAL\\nREASON: Routine maintenance with all systems nominal."},
    {**create_classification_prompt("External ammonia coolant leak on loop A; isolated; redundancy lost."),
     "assistant": "SEVERITY: WARNING\\nREASON: Loss of cooling redundancy from an external coolant leak."},
]
with TRAIN_FILE.open("w") as fh:
    for row in demo_rows:
        fh.write(json.dumps(row) + "\\n")

print(f"Wrote {len(demo_rows)} example rows -> {TRAIN_FILE}")
print("Real distillation: loop make_training_example over 500+ scenarios.")"""),
    md("""\
!!! note "Expected output"
    ```
    Wrote 2 example rows -> finetune_data/train.jsonl
    Real distillation: loop make_training_example over 500+ scenarios.
    ```
    Each line is `{"system", "user", "assistant"}` — the chat-format jsonl Olive
    consumes. The reference generates **500+** rows this way; more (balanced) data is
    the single biggest lever on student accuracy."""),

    md("""\
## 4. LoRA fine-tune with Olive

You don't retrain all of Phi-4-mini — that's billions of weights. **LoRA**
(Low-Rank Adaptation, a **PEFT** method) freezes the base model and trains tiny
adapter matrices on a few attention/MLP projections. **Olive** drives it from one
CLI call. `--target_modules` names the projections LoRA adapts."""),
    code("""\
# ── GPU REQUIRED — illustrative; run where an A100/CUDA GPU is available. ──────
# Needs the `finetune` extra: pip install -e ".[finetune]"
olive_command = [
    "olive", "finetune",
    "--method", "lora",
    "--model_name_or_path", STUDENT_MODEL,
    "--trust_remote_code",
    "--data_name", "json",
    "--data_files", str(TRAIN_FILE),
    "--text_template", "{system}\\n{user}\\n{assistant}",
    "--target_modules", "qkv_proj,o_proj,gate_up_proj,down_proj",
    "--max_steps", "100",
    "--output_path", "finetune_data/adapter",
]
print("Fine-tune command (run on a GPU host):\\n")
print("  " + " ".join(olive_command))

# On a GPU box you'd execute it:
# import subprocess; subprocess.run(olive_command, check=True)
print("\\n(Not executed here — see the GPU warning at the top.)")"""),
    md("""\
!!! note "Expected output"
    ```
    Fine-tune command (run on a GPU host):

      olive finetune --method lora --model_name_or_path microsoft/Phi-4-mini-instruct \\
        --trust_remote_code --data_name json --data_files finetune_data/train.jsonl \\
        --text_template {system}\\n{user}\\n{assistant} \\
        --target_modules qkv_proj,o_proj,gate_up_proj,down_proj \\
        --max_steps 100 --output_path finetune_data/adapter

    (Not executed here — see the GPU warning at the top.)
    ```
    Olive writes a small **LoRA adapter** (tens of MB) to `--output_path` — not a full
    model copy. Training 100 steps on an A100 takes ~15–20 min.

!!! note "Where the GPU comes from is a Platform concern"
    The reference submits this exact command as a **serverless GPU job** on Azure
    Container Apps (NC24-A100) so nobody manages a GPU box. That orchestration
    (provisioning + blob I/O) is enterprise plumbing we've stripped — see the Platform
    docs. The *fine-tuning* itself is the one `olive finetune` call above."""),

    md("""\
## 5. Evaluate: teacher vs. base vs. student

Did distillation work? Run the **same** held-out reports through three models and
compare accuracy: the **teacher** (ceiling), the **base** student (before
fine-tuning), and the **fine-tuned** student. The win condition is the fine-tuned
student beating its base self."""),
    code("""\
# Accuracies from an evaluation run (see the reference's ACA eval job). Plug your
# own numbers in here after fine-tuning.
results = {
    "gpt-4.1-mini (teacher)":   0.80,
    "Phi-4-mini (base)":        0.457,
    "Phi-4-mini (fine-tuned)":  0.514,
}

print(f"{'model':<28}{'accuracy':>9}")
print("-" * 37)
for name, acc in results.items():
    bar = "█" * round(acc * 20)
    print(f"{name:<28}{acc:>8.1%}  {bar}")

gain = results["Phi-4-mini (fine-tuned)"] - results["Phi-4-mini (base)"]
print(f"\\nFine-tuning gain: {gain:+.1%}  (base {results['Phi-4-mini (base)']:.1%} "
      f"-> {results['Phi-4-mini (fine-tuned)']:.1%})")

# With matplotlib (in the finetune extra) you'd draw the bar chart:
# import matplotlib.pyplot as plt
# plt.bar(results.keys(), results.values()); plt.ylabel("accuracy"); plt.show()"""),
    md("""\
!!! note "Expected output"
    ```
    model                        accuracy
    -------------------------------------
    gpt-4.1-mini (teacher)          80.0%  ████████████████
    Phi-4-mini (base)               45.7%  █████████
    Phi-4-mini (fine-tuned)         51.4%  ██████████

    Fine-tuning gain: +5.7%  (base 45.7% -> fine-tuned 51.4%)
    ```
    The student gains ~6 points and closes part of the gap to the teacher — a real
    win for a tiny adapter. It won't *match* the teacher; the goal is **good enough,
    cheap, and offline**. More balanced data and more steps push it higher (your
    turn)."""),

    md("""\
## 6. Load the adapter for local inference

The payoff: the fine-tuned student runs **completely offline**. Load the base
model, apply the **LoRA adapter** with `PeftModel.from_pretrained`, and classify a
report on your laptop's CPU/GPU — no API call. The adapter is what shipped; the
base weights are public."""),
    code("""\
# ── Needs the `finetune` extra (torch + transformers + peft). Runs on CPU/MPS/CUDA. ──
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

ADAPTER_PATH = "finetune_data/adapter"
device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"

tokenizer  = AutoTokenizer.from_pretrained(STUDENT_MODEL, trust_remote_code=True)
base_model = AutoModelForCausalLM.from_pretrained(STUDENT_MODEL, trust_remote_code=True).to(device)
ft_model   = PeftModel.from_pretrained(base_model, ADAPTER_PATH)   # apply LoRA adapter
ft_model.eval()

prompt   = create_classification_prompt("Cabin pressure dropping rapidly; crew donned masks; leak unisolated.")
messages = [{"role": "system", "content": prompt["system"]},
            {"role": "user",   "content": prompt["user"]}]
inputs   = tokenizer.apply_chat_template(messages, add_generation_prompt=True,
                                         return_tensors="pt", return_dict=True).to(device)
with torch.no_grad():
    out = ft_model.generate(**inputs, max_new_tokens=80, do_sample=False)
print(tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True))"""),
    md("""\
!!! note "Expected output"
    ```
    SEVERITY: CRITICAL
    REASON: Rapid cabin depressurization is an immediate threat to crew safety.
    ```
    A 4 GB model, fine-tuned on your task, classifying with the teacher's rubric —
    running on-device with zero API cost. That's the whole point of distillation:
    **cloud-scale training, edge-scale inference.**

!!! warning "API is evolving"
    Olive flags (`--method lora`, `--target_modules`) and the `transformers`/`peft`
    loading API shift across releases — the reference pins `transformers==4.53.3`.
    This lab targets the `finetune` extra; pin those versions in `pyproject.toml` and
    check them if a flag or argument differs."""),

    md("""\
## 🧪 Your turn

1. **Grow the dataset.** Loop `make_training_example` over a longer, **balanced**
   `SCENARIOS` list (equal counts per severity) and write a real `train.jsonl` — the
   reference notes the student over-predicts `CAUTION` when classes are imbalanced.
2. **Train longer.** Bump `--max_steps` to `200–300` in section 4 and re-evaluate —
   does the fine-tuning gain widen, or does it plateau / overfit?
3. **Swap the student.** Point `STUDENT_MODEL` at another small open model and re-run
   sections 4–6 — compare its fine-tuned accuracy and adapter size to Phi-4-mini.

---

✅ **You walked the full distillation pipeline: a teacher generated labelled data, a
LoRA adapter fine-tuned a small student with Olive, and the adapter loaded locally for
offline inference — beating the base model on your task.** Next: bring it all together
in the capstone.
""" + next_link("15-capstone", "M15 · Capstone")),
]

write_notebook(
    "docs/modules/14-fine-tuning-distillation.ipynb",
    cells,
    kernel_name=KERNEL,
    kernel_display=KERNEL_DISPLAY,
)
