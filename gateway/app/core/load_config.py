import yaml

def load_config(path: str):
    with open(path) as f:
        raw = yaml.safe_load(f)
    return raw
