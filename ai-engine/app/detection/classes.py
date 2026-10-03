from typing import Dict, List


def resolve_class_ids(model_names: Dict[int, str], wanted: List[str]) -> List[int]:
    """Convert class names from config into the model's integer class IDs."""
    name_to_id = {name: idx for idx, name in model_names.items()}
    missing = [w for w in wanted if w not in name_to_id]
    if missing:
        raise ValueError(f"Classes not supported by this model: {missing}")
    return [name_to_id[w] for w in wanted]
