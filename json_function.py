import json

def dump_jsonl(data, output_path, append=False):
    """
    Write list of objects to a JSON lines file.
    """
    mode = 'a+' if append else 'w'
    with open(output_path, mode, encoding='utf-8') as f:
        for line in data:
            json_record = json.dumps(line, ensure_ascii=False)
            f.write(json_record + '\n')

def load_jsonl(input_path, has_index=True) -> list:
    """
    Read list of objects from a JSON lines file.
    """
    data = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            if has_index:
                json_l = json.loads(line.rstrip('\n|\r'))
                # hack ... 
                v = list(json_l.values())[0]
                data.append(v)
            else:
                data.append(json.loads(line.rstrip('\n|\r')))
    return data