"""
VIDOCQ - Model Fine-Tuning Infrastructure
Ready to train Mistral once enough feedback data is collected.

NOT USED YET - Waiting for 100+ feedback examples.

Usage (when ready):
    python -m src.core.training --check   # Check if enough data
    python -m src.core.training --train   # Launch fine-tuning
"""

import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel

from src.core.logging import get_logger

logger = get_logger(__name__)


class TrainingConfig(BaseModel):
    """Configuration for model fine-tuning"""
    
    # Data paths
    training_data_path: str = "data/feedback/training_data.jsonl"
    output_model_path: str = "models/vidocq-fine-tuned"
    
    # Training parameters (for Mistral LoRA fine-tuning)
    base_model: str = "mistralai/Mistral-7B-Instruct-v0.2"
    learning_rate: float = 2e-5
    batch_size: int = 4
    num_epochs: int = 3
    max_length: int = 2048
    
    # LoRA config (efficient fine-tuning)
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    
    # Minimum data requirements
    min_examples: int = 100
    min_corrections: int = 50  # At least 50 actual corrections, not just validations


class TrainingDataFormatter:
    """
    Formats feedback data for Mistral fine-tuning.
    
    Output format (Mistral Instruct):
    <s>[INST] Extract entities and relations from: {text} [/INST]
    {expected_output}</s>
    """
    
    SYSTEM_PROMPT = """Tu es un agent de renseignement spécialisé dans l'extraction d'entités et de relations 
depuis des textes sur les entreprises, personnes et chaînes d'approvisionnement.
Réponds UNIQUEMENT en JSON valide avec les clés: entities, relation, confidence."""
    
    def format_for_mistral(self, input_text: str, expected_output: Dict) -> str:
        """Format a single example for Mistral fine-tuning"""
        
        output_json = json.dumps(expected_output, ensure_ascii=False)
        
        return f"""<s>[INST] {self.SYSTEM_PROMPT}

Texte à analyser:
{input_text}
[/INST]
{output_json}</s>"""
    
    def load_and_format_training_data(self, filepath: str) -> List[Dict[str, str]]:
        """Load training data and format for fine-tuning"""
        
        if not os.path.exists(filepath):
            logger.error("training_data_not_found", path=filepath)
            return []
        
        formatted_examples = []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    example = json.loads(line)
                    formatted = self.format_for_mistral(
                        input_text=example.get("input_text", ""),
                        expected_output=example.get("expected_output", {})
                    )
                    formatted_examples.append({
                        "text": formatted,
                        "source": example.get("source", "feedback")
                    })
                except Exception as e:
                    logger.warning("format_error", error=str(e))
                    continue
        
        return formatted_examples


class VidocqTrainer:
    """
    Fine-tunes Mistral on Vidocq feedback data.
    
    Uses LoRA (Low-Rank Adaptation) for efficient training.
    Requires: transformers, peft, bitsandbytes, accelerate
    
    NOT ACTIVE - Infrastructure ready for when data is collected.
    """
    
    def __init__(self, config: Optional[TrainingConfig] = None):
        self.config = config or TrainingConfig()
        self.formatter = TrainingDataFormatter()
    
    def check_readiness(self) -> Dict[str, Any]:
        """Check if we have enough data for training"""
        
        # Check doctrine
        doctrine_count = self._count_doctrine_examples()
        
        # Check feedback/corrections
        feedback_count = 0
        corrections_count = 0
        training_path = self.config.training_data_path
        
        if os.path.exists(training_path):
            with open(training_path, 'r', encoding='utf-8') as f:
                examples = [json.loads(line) for line in f]
            feedback_count = len(examples)
            corrections_count = sum(
                1 for ex in examples 
                if ex.get("expected_output", {}).get("relation") not in [None, ""]
            )
        
        # Check graph examples
        graph_count = self._count_graph_examples()
        
        total = doctrine_count + feedback_count + graph_count
        
        ready = total >= self.config.min_examples
        
        return {
            "ready": ready,
            "data_sources": {
                "doctrine_examples": doctrine_count,
                "feedback_examples": feedback_count,
                "graph_examples": graph_count,
                "corrections": corrections_count
            },
            "total_examples": total,
            "min_required": self.config.min_examples,
            "progress_percent": min(100, total / self.config.min_examples * 100),
            "message": "Ready for training!" if ready else f"Need {self.config.min_examples - total} more examples"
        }
    
    def _count_doctrine_examples(self) -> int:
        """Count examples from French doctrine"""
        try:
            from src.core.doctrine import DOCTRINE
            return len(DOCTRINE.generate_training_examples())
        except:
            return 0
    
    def _count_graph_examples(self) -> int:
        """Count examples extractable from Neo4j graph"""
        try:
            from src.storage.graph import GraphStore
            store = GraphStore()
            with store.driver.session() as session:
                result = session.run("""
                    MATCH (s:Entity)-[r]->(t:Entity)
                    WHERE r.validated = true OR r.corrected = true
                    RETURN count(*) as count
                """)
                record = result.single()
                return record["count"] if record else 0
        except:
            return 0
    
    def _generate_doctrine_examples(self) -> List[Dict]:
        """Generate training examples from French doctrine"""
        from src.core.doctrine import DOCTRINE
        
        examples = []
        for ex in DOCTRINE.generate_training_examples():
            formatted = self.formatter.format_for_mistral(
                input_text=ex.input_text,
                expected_output=ex.expected_output
            )
            examples.append({
                "text": formatted,
                "source": "doctrine_fr",
                "category": ex.category
            })
        
        logger.info("doctrine_examples_generated", count=len(examples))
        return examples
    
    def _generate_graph_examples(self) -> List[Dict]:
        """Generate training examples from validated/corrected Neo4j data"""
        try:
            from src.storage.graph import GraphStore
            store = GraphStore()
            
            query = """
            MATCH (s:Entity)-[r]->(t:Entity)
            WHERE r.validated = true OR r.corrected = true
            RETURN s.canonical_name as source,
                   type(r) as relation,
                   t.canonical_name as target,
                   r.source_text as context
            LIMIT 500
            """
            
            examples = []
            with store.driver.session() as session:
                result = session.run(query)
                for record in result:
                    input_text = record["context"] or f"{record['source']} {record['relation']} {record['target']}"
                    expected = {
                        "entities": [record["source"], record["target"]],
                        "relation": record["relation"],
                        "confidence": 1.0  # Validated = high confidence
                    }
                    
                    formatted = self.formatter.format_for_mistral(input_text, expected)
                    examples.append({
                        "text": formatted,
                        "source": "graph_validated"
                    })
            
            logger.info("graph_examples_generated", count=len(examples))
            return examples
            
        except Exception as e:
            logger.warning("graph_examples_failed", error=str(e))
            return []
    
    def prepare_dataset(self) -> str:
        """
        Prepare COMBINED dataset from all sources:
        1. French Doctrine (pre-training base)
        2. Graph validated/corrected data
        3. Analyst feedback
        """
        all_examples = []
        
        # 1. DOCTRINE (Base knowledge)
        logger.info("loading_doctrine_examples")
        doctrine_examples = self._generate_doctrine_examples()
        all_examples.extend(doctrine_examples)
        
        # 2. GRAPH (Validated data from Neo4j)
        logger.info("loading_graph_examples")
        graph_examples = self._generate_graph_examples()
        all_examples.extend(graph_examples)
        
        # 3. FEEDBACK (Analyst corrections)
        logger.info("loading_feedback_examples")
        feedback_examples = self.formatter.load_and_format_training_data(
            self.config.training_data_path
        )
        all_examples.extend(feedback_examples)
        
        if not all_examples:
            raise ValueError("No training data available from any source")
        
        # Save combined dataset
        output_path = "data/training/combined_training.jsonl"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for example in all_examples:
                f.write(json.dumps(example, ensure_ascii=False) + '\n')
        
        logger.info(
            "dataset_prepared",
            total=len(all_examples),
            doctrine=len(doctrine_examples),
            graph=len(graph_examples),
            feedback=len(feedback_examples),
            path=output_path
        )
        
        return output_path
    
    def train(self) -> Dict[str, Any]:
        """
        Launch fine-tuning.
        
        REQUIRES THESE PACKAGES (not installed by default):
        - pip install transformers peft bitsandbytes accelerate
        - GPU with 16GB+ VRAM recommended
        
        For now: Returns instructions on how to run when ready.
        """
        
        readiness = self.check_readiness()
        
        if not readiness["ready"]:
            return {
                "status": "not_ready",
                "message": readiness["message"],
                "readiness": readiness
            }
        
        # Prepare dataset
        dataset_path = self.prepare_dataset()
        
        # Generate training script
        training_script = self._generate_training_script(dataset_path)
        
        script_path = "scripts/train_vidocq.py"
        os.makedirs(os.path.dirname(script_path), exist_ok=True)
        
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(training_script)
        
        return {
            "status": "ready",
            "message": "Training script generated. Run when ready.",
            "dataset_path": dataset_path,
            "script_path": script_path,
            "command": f"python {script_path}",
            "requirements": [
                "pip install transformers peft bitsandbytes accelerate",
                "GPU with 16GB+ VRAM",
                "~2-4 hours training time"
            ]
        }
    
    def _generate_training_script(self, dataset_path: str) -> str:
        """Generate the actual training script"""
        
        return f'''"""
VIDOCQ Fine-Tuning Script
Auto-generated on {datetime.now().isoformat()}

Run this when you have enough feedback data and GPU access.
"""

from transformers import (
    AutoModelForCausalLM, 
    AutoTokenizer, 
    TrainingArguments,
    Trainer
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from datasets import load_dataset
import torch

# Config
MODEL_NAME = "{self.config.base_model}"
DATASET_PATH = "{dataset_path}"
OUTPUT_DIR = "{self.config.output_model_path}"

# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
tokenizer.pad_token = tokenizer.eos_token

# Load model in 4-bit for memory efficiency
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    load_in_4bit=True,
    torch_dtype=torch.float16,
    device_map="auto"
)

# Prepare for training
model = prepare_model_for_kbit_training(model)

# LoRA config
lora_config = LoraConfig(
    r={self.config.lora_r},
    lora_alpha={self.config.lora_alpha},
    lora_dropout={self.config.lora_dropout},
    target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
    bias="none",
    task_type="CAUSAL_LM"
)

model = get_peft_model(model, lora_config)

# Load dataset
dataset = load_dataset("json", data_files=DATASET_PATH, split="train")

def tokenize(example):
    return tokenizer(
        example["text"], 
        truncation=True, 
        max_length={self.config.max_length},
        padding="max_length"
    )

dataset = dataset.map(tokenize)

# Training arguments
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs={self.config.num_epochs},
    per_device_train_batch_size={self.config.batch_size},
    learning_rate={self.config.learning_rate},
    fp16=True,
    logging_steps=10,
    save_strategy="epoch",
    report_to="none"
)

# Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset,
)

# Train!
print("Starting Vidocq fine-tuning...")
trainer.train()

# Save
model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

print(f"Model saved to {{OUTPUT_DIR}}")
print("Vidocq is now smarter!")
'''


# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Vidocq Model Training")
    parser.add_argument("--check", action="store_true", help="Check training readiness")
    parser.add_argument("--train", action="store_true", help="Prepare training (generate script)")
    
    args = parser.parse_args()
    
    trainer = VidocqTrainer()
    
    if args.check:
        result = trainer.check_readiness()
        print(json.dumps(result, indent=2))
    
    elif args.train:
        result = trainer.train()
        print(json.dumps(result, indent=2))
    
    else:
        parser.print_help()
