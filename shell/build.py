#!/usr/bin/env python3
import os
import re
import configparser
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
TEMPLATE_DIR = SCRIPT_DIR.parent / "template"
OUTPUT_DIR = SCRIPT_DIR / "output"
CONFIG_FILE = SCRIPT_DIR / "provider.cfg"

VERSION_PREFIX = datetime.now().strftime("%m%d")

def get_next_version():
    if not OUTPUT_DIR.exists():
        OUTPUT_DIR.mkdir(parents=True)
    
    existing_files = list(OUTPUT_DIR.glob("*.yaml"))
    if not existing_files:
        return f"01_{VERSION_PREFIX}a"
    
    versions = []
    for f in existing_files:
        name = f.stem
        match = re.match(r'Clash_Router_(\d+)_(\d+)([a-z])', name)
        if match and match.group(2) == VERSION_PREFIX:
            num = int(match.group(1))
            suffix = match.group(3)
            versions.append((num, suffix))
    
    if not versions:
        return f"01_{VERSION_PREFIX}a"
    
    versions.sort(key=lambda x: (x[0], x[1]))
    last_num, last_suffix = versions[-1]
    
    if last_suffix == 'z':
        return f"{last_num + 1:02d}_{VERSION_PREFIX}a"
    else:
        suffix_ord = ord(last_suffix)
        next_suffix = chr(suffix_ord + 1)
        return f"{last_num:02d}_{VERSION_PREFIX}{next_suffix}"

def parse_provider_config():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding='utf-8')
    
    providers = {}
    provider_names = []
    for section in config.sections():
        if section.startswith('provider'):
            name = config.get(section, 'name', fallback='')
            url = config.get(section, 'url', fallback='')
            if name and url:
                providers[section] = {'name': name, 'url': url}
                provider_names.append(name)
    return providers, provider_names

def generate_proxy_providers(providers):
    result = []
    for key, prov in providers.items():
        result.append(f"""  {prov['name']}:
    type: http
    url: "{prov['url']}"
    path: ./config/{prov['name']}.yaml
    interval: 604800
    health-check:
      enable: true
      url: https://www.gstatic.com/generate_204
      interval: 1200
    override:
      udp: true""")
    return "proxy-providers:\n" + "\n\n".join(result)

def load_yaml_section(file_path, key):
    content = file_path.read_text(encoding='utf-8')
    match = re.search(rf'^{key}:\s*$', content, re.MULTILINE)
    if not match:
        return None
    
    start = match.end()
    lines = content.split('\n')
    result = []
    indent = None
    
    for line in lines[start:]:
        if not line.strip():
            if indent is None:
                continue
            else:
                result.append(line)
                continue
        
        current_indent = len(line) - len(line.lstrip())
        
        if indent is None:
            indent = current_indent
        
        if current_indent < indent and line.strip():
            break
        
        result.append(line)
    
    return '\n'.join(result).strip()

def replace_provider_refs(content, provider_names):
    if len(provider_names) >= 1:
        p1 = provider_names[0]
    else:
        p1 = "provider1"
    
    if len(provider_names) >= 2:
        p2 = provider_names[1]
    else:
        p2 = "provider2"
    
    content = re.sub(r'use: \[provider1\]', f'use: [{p1}]', content)
    content = re.sub(r'use: \[provider2\]', f'use: [{p2}]', content)
    
    return content

def merge_configs(providers, provider_names):
    base_file = TEMPLATE_DIR / "Clash_Router_V2.yaml"
    base_content = base_file.read_text(encoding='utf-8')
    
    proxy_providers_yaml = generate_proxy_providers(providers)
    proxy_groups = load_yaml_section(TEMPLATE_DIR / "model_proxy-groups.yaml", "proxy-groups")
    proxy_groups = replace_provider_refs(proxy_groups, provider_names)
    
    lines = base_content.split('\n')
    result_lines = []
    state = 'base'
    providers_added = False
    groups_added = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        if stripped.startswith('proxy-providers:'):
            state = 'providers'
            result_lines.append(proxy_providers_yaml)
            providers_added = True
            continue
        elif state == 'providers' and stripped and not line.startswith(' '):
            state = 'base'
        
        if stripped.startswith('proxy-groups:') and not groups_added:
            result_lines.append(line)
            result_lines.append(proxy_groups)
            groups_added = True
            state = 'groups'
            continue
        elif state == 'groups' and stripped and not line.startswith(' '):
            state = 'base'
        
        if state == 'base':
            result_lines.append(line)
    
    if not providers_added:
        result_lines.append('')
        result_lines.append(proxy_providers_yaml)
    
    return '\n'.join(result_lines)

def main():
    print("Reading provider config...")
    providers, provider_names = parse_provider_config()
    
    if not providers:
        print("Error: No valid provider config found")
        return
    
    print(f"Found {len(providers)} providers:")
    for k, v in providers.items():
        print(f"  - {v['name']}: {v['url']}")
    
    print("\nGenerating version number...")
    version = get_next_version()
    
    print(f"Version: {version}")
    
    print("\nMerging configs...")
    final_config = merge_configs(providers, provider_names)
    
    output_file = OUTPUT_DIR / f"Clash_Router_{version}.yaml"
    output_file.write_text(final_config, encoding='utf-8')
    
    print(f"\nDone! Output: {output_file}")

if __name__ == "__main__":
    main()
