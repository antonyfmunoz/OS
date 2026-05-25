"""Fine-tuning harness — scaffolds LoRA fine-tuning for self-hosted models.

This is not a training loop — it's the infrastructure layer that:
  1. Validates and splits training data
  2. Generates LoRA configuration for the target model
  3. Produces a training script ready for execution on GPU hardware
  4. Evaluates fine-tuned model quality against held-out examples
  5. Packages the adapter for Ollama Modelfile deployment

Designed for:
  - Base model: Qwen 2.5 7B or Gemma 3 4B (fits on Beast GPU)
  - Training: LoRA rank 16, alpha 32 (parameter-efficient)
  - Evaluation: exact match + semantic similarity on held-out set
"""

from __future__ import annotations

import json
import logging
import math
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_DATA_PATH = Path("data/umh/training/training_data.jsonl")
DEFAULT_OUTPUT_DIR = Path("data/umh/training/finetune_output")

SUPPORTED_BASE_MODELS = {
    "qwen2.5:7b": {
        "hf_name": "Qwen/Qwen2.5-7B",
        "context_length": 4096,
        "recommended_lora_rank": 16,
        "recommended_epochs": 3,
        "gpu_memory_gb": 16,
    },
    "gemma3:4b": {
        "hf_name": "google/gemma-3-4b",
        "context_length": 4096,
        "recommended_lora_rank": 8,
        "recommended_epochs": 3,
        "gpu_memory_gb": 8,
    },
}


@dataclass
class LoRAConfig:
    """LoRA fine-tuning configuration."""

    base_model: str = "qwen2.5:7b"
    lora_rank: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    target_modules: list[str] = field(
        default_factory=lambda: ["q_proj", "v_proj", "k_proj", "o_proj"]
    )
    learning_rate: float = 2e-4
    epochs: int = 3
    batch_size: int = 4
    gradient_accumulation_steps: int = 4
    warmup_ratio: float = 0.03
    max_seq_length: int = 2048
    fp16: bool = True
    seed: int = 42

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_model": self.base_model,
            "lora_rank": self.lora_rank,
            "lora_alpha": self.lora_alpha,
            "lora_dropout": self.lora_dropout,
            "target_modules": self.target_modules,
            "learning_rate": self.learning_rate,
            "epochs": self.epochs,
            "batch_size": self.batch_size,
            "gradient_accumulation_steps": self.gradient_accumulation_steps,
            "warmup_ratio": self.warmup_ratio,
            "max_seq_length": self.max_seq_length,
            "fp16": self.fp16,
            "seed": self.seed,
        }


@dataclass
class DataSplit:
    """Train/validation/test split of training data."""

    train: list[dict[str, Any]] = field(default_factory=list)
    validation: list[dict[str, Any]] = field(default_factory=list)
    test: list[dict[str, Any]] = field(default_factory=list)
    total: int = 0


@dataclass
class EvalResult:
    """Evaluation of a fine-tuned model against held-out examples."""

    total_examples: int = 0
    exact_matches: int = 0
    avg_similarity: float = 0.0
    by_type: dict[str, dict[str, float]] = field(default_factory=dict)

    def accuracy(self) -> float:
        return self.exact_matches / self.total_examples if self.total_examples > 0 else 0.0


class FinetuneHarness:
    """Scaffolds LoRA fine-tuning and evaluation."""

    def __init__(
        self,
        data_path: Path | None = None,
        output_dir: Path | None = None,
        base_model: str = "qwen2.5:7b",
    ) -> None:
        self._data_path = data_path or DEFAULT_DATA_PATH
        self._output_dir = output_dir or DEFAULT_OUTPUT_DIR
        self._base_model = base_model
        self._config = self._build_config()

    def _build_config(self) -> LoRAConfig:
        """Build LoRA config from base model defaults."""
        model_info = SUPPORTED_BASE_MODELS.get(self._base_model, {})
        return LoRAConfig(
            base_model=self._base_model,
            lora_rank=model_info.get("recommended_lora_rank", 16),
            epochs=model_info.get("recommended_epochs", 3),
        )

    @property
    def config(self) -> LoRAConfig:
        return self._config

    def prepare_data(
        self,
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        seed: int = 42,
    ) -> DataSplit:
        """Load, validate, and split training data."""
        if not self._data_path.exists():
            logger.warning("Training data not found: %s", self._data_path)
            return DataSplit()

        examples: list[dict[str, Any]] = []
        with open(self._data_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ex = json.loads(line)
                    if self._validate_example(ex):
                        examples.append(ex)
                except json.JSONDecodeError:
                    continue

        random.seed(seed)
        random.shuffle(examples)

        n = len(examples)
        train_end = int(n * train_ratio)
        val_end = train_end + int(n * val_ratio)

        split = DataSplit(
            train=examples[:train_end],
            validation=examples[train_end:val_end],
            test=examples[val_end:],
            total=n,
        )

        self._output_dir.mkdir(parents=True, exist_ok=True)
        for name, data in [
            ("train", split.train),
            ("val", split.validation),
            ("test", split.test),
        ]:
            path = self._output_dir / f"{name}.jsonl"
            with open(path, "w") as f:
                for ex in data:
                    f.write(json.dumps(ex, separators=(",", ":")) + "\n")

        logger.info(
            "data split: train=%d, val=%d, test=%d (total=%d)",
            len(split.train),
            len(split.validation),
            len(split.test),
            n,
        )
        return split

    def _validate_example(self, ex: dict[str, Any]) -> bool:
        """Validate a training example has required fields and minimum content."""
        instruction = ex.get("instruction", "")
        input_text = ex.get("input", "")
        output_text = ex.get("output", "")

        if not instruction or not input_text or not output_text:
            return False
        if len(input_text) < 10 or len(output_text) < 5:
            return False
        return True

    def generate_training_script(self) -> str:
        """Generate a ready-to-run fine-tuning script for the Beast GPU."""
        model_info = SUPPORTED_BASE_MODELS.get(self._base_model, {})
        hf_name = model_info.get("hf_name", self._base_model)
        c = self._config

        script = f'''#!/usr/bin/env python3
"""UMH LoRA fine-tuning script — generated by FinetuneHarness.

Run on Beast GPU:
  python3 finetune.py

Requires: transformers, peft, datasets, bitsandbytes, accelerate
  pip install transformers peft datasets bitsandbytes accelerate
"""

import torch
from datasets import load_dataset
from peft import LoraConfig, get_peft_model, TaskType
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForSeq2Seq,
)

BASE_MODEL = "{hf_name}"
TRAIN_DATA = "{self._output_dir / "train.jsonl"}"
VAL_DATA = "{self._output_dir / "val.jsonl"}"
OUTPUT_DIR = "{self._output_dir / "lora_adapter"}"

tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    torch_dtype=torch.float16,
    device_map="auto",
    trust_remote_code=True,
)

lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r={c.lora_rank},
    lora_alpha={c.lora_alpha},
    lora_dropout={c.lora_dropout},
    target_modules={c.target_modules},
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

train_dataset = load_dataset("json", data_files=TRAIN_DATA, split="train")
val_dataset = load_dataset("json", data_files=VAL_DATA, split="train")


def format_example(example):
    text = (
        f"### Instruction:\\n{{example['instruction']}}\\n\\n"
        f"### Input:\\n{{example['input']}}\\n\\n"
        f"### Response:\\n{{example['output']}}"
    )
    tokens = tokenizer(text, truncation=True, max_length={c.max_seq_length}, padding="max_length")
    tokens["labels"] = tokens["input_ids"].copy()
    return tokens


train_dataset = train_dataset.map(format_example, remove_columns=train_dataset.column_names)
val_dataset = val_dataset.map(format_example, remove_columns=val_dataset.column_names)

training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs={c.epochs},
    per_device_train_batch_size={c.batch_size},
    gradient_accumulation_steps={c.gradient_accumulation_steps},
    learning_rate={c.learning_rate},
    warmup_ratio={c.warmup_ratio},
    fp16={str(c.fp16).lower() == "true"},
    logging_steps=10,
    eval_strategy="epoch",
    save_strategy="epoch",
    save_total_limit=2,
    seed={c.seed},
    report_to="none",
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    data_collator=DataCollatorForSeq2Seq(tokenizer, padding=True),
)

trainer.train()
model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print(f"LoRA adapter saved to {{OUTPUT_DIR}}")
'''
        script_path = self._output_dir / "finetune.py"
        self._output_dir.mkdir(parents=True, exist_ok=True)
        script_path.write_text(script)
        logger.info("training script written to %s", script_path)
        return str(script_path)

    def generate_modelfile(self, adapter_path: str = "") -> str:
        """Generate an Ollama Modelfile for serving the fine-tuned model."""
        if not adapter_path:
            adapter_path = str(self._output_dir / "lora_adapter")

        modelfile = f"""FROM {self._base_model}

ADAPTER {adapter_path}

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER stop "### Instruction:"
PARAMETER stop "### Input:"

SYSTEM You are UMH's proprietary intelligence engine. You process signals, make governance decisions, and predict outcomes based on operational history. Always respond with structured, actionable output.
"""
        modelfile_path = self._output_dir / "Modelfile"
        self._output_dir.mkdir(parents=True, exist_ok=True)
        modelfile_path.write_text(modelfile)
        logger.info("Ollama Modelfile written to %s", modelfile_path)
        return str(modelfile_path)

    def evaluate_model(self, test_data: list[dict[str, Any]] | None = None) -> EvalResult:
        """Evaluate model quality against held-out test data.

        Uses Ollama to run inference with the fine-tuned model, then
        compares against ground truth.
        """
        if test_data is None:
            test_path = self._output_dir / "test.jsonl"
            if not test_path.exists():
                return EvalResult()
            test_data = []
            with open(test_path) as f:
                for line in f:
                    if line.strip():
                        test_data.append(json.loads(line))

        result = EvalResult(total_examples=len(test_data))
        type_scores: dict[str, list[float]] = {}

        for ex in test_data:
            expected = ex.get("output", "")
            input_text = ex.get("input", "")
            ext_type = ex.get("extraction_type", "unknown")

            predicted = self._run_inference(ex.get("instruction", ""), input_text)

            if predicted.strip() == expected.strip():
                result.exact_matches += 1

            similarity = self._token_similarity(predicted, expected)
            type_scores.setdefault(ext_type, []).append(similarity)

        all_sims = [s for scores in type_scores.values() for s in scores]
        result.avg_similarity = sum(all_sims) / len(all_sims) if all_sims else 0.0

        for ext_type, scores in type_scores.items():
            result.by_type[ext_type] = {
                "count": len(scores),
                "avg_similarity": round(sum(scores) / len(scores), 3),
            }

        return result

    def _run_inference(self, instruction: str, input_text: str) -> str:
        """Run inference through Ollama with the fine-tuned model."""
        try:
            import subprocess

            prompt = (
                f"### Instruction:\n{instruction}\n\n### Input:\n{input_text}\n\n### Response:\n"
            )
            result = subprocess.run(
                ["ollama", "run", f"umh-{self._base_model.replace(':', '-')}", prompt],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return ""

    def _token_similarity(self, a: str, b: str) -> float:
        """Simple token overlap similarity."""
        tokens_a = set(a.lower().split())
        tokens_b = set(b.lower().split())
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        return len(intersection) / len(union) if union else 0.0

    def full_pipeline_status(self) -> dict[str, Any]:
        """Report status of each pipeline stage."""
        data_exists = self._data_path.exists()
        splits_exist = (self._output_dir / "train.jsonl").exists()
        script_exists = (self._output_dir / "finetune.py").exists()
        adapter_exists = (self._output_dir / "lora_adapter").exists()
        modelfile_exists = (self._output_dir / "Modelfile").exists()

        data_count = 0
        if data_exists:
            with open(self._data_path) as f:
                data_count = sum(1 for line in f if line.strip())

        return {
            "base_model": self._base_model,
            "stages": {
                "1_training_data": {
                    "ready": data_exists,
                    "example_count": data_count,
                    "path": str(self._data_path),
                },
                "2_data_split": {
                    "ready": splits_exist,
                    "path": str(self._output_dir),
                },
                "3_training_script": {
                    "ready": script_exists,
                    "path": str(self._output_dir / "finetune.py"),
                },
                "4_lora_adapter": {
                    "ready": adapter_exists,
                    "path": str(self._output_dir / "lora_adapter"),
                },
                "5_ollama_modelfile": {
                    "ready": modelfile_exists,
                    "path": str(self._output_dir / "Modelfile"),
                },
            },
            "lora_config": self._config.to_dict(),
        }
