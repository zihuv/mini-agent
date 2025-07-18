import json

def load_workflow_from_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['workflow'] 