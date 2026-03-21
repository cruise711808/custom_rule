#!/usr/bin/env python3
import os
import re
import configparser
from datetime import datetime
from pathlib import Path
import sys

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    yaml = None
    YAML_AVAILABLE = False

SCRIPT_DIR = Path(__file__).parent
TEMPLATE_DIR = SCRIPT_DIR.parent / "template"
OUTPUT_DIR = SCRIPT_DIR / "output"
CONFIG_FILE = SCRIPT_DIR / "provider.cfg"

VERSION_PREFIX = datetime.now().strftime("%m%d")

VALID_PROXY_GROUP_TYPES = {'select', 'url-test', 'fallback', 'load-balance', 'consistent-hashing', 'static'}
VALID_RULE_TYPES = {
    'DOMAIN', 'DOMAIN-SUFFIX', 'DOMAIN-KEYWORD', 'DOMAIN-REGEX',
    'GEOIP', 'GEOSITE',
    'IP-CIDR', 'IP-CIDR6', 'SRC-IP-CIDR',
    'SRC-PORT', 'DST-PORT', 'PROCESS-NAME',
    'RULE-SET', 'RULE-SET-RETURN',
    'MATCH', 'DEFAULT'
}
RULE_MODIFIERS = {'no-resolve', 'no-rule'}

def validate_yaml_syntax(config_text):
    if not YAML_AVAILABLE:
        print("[Warning] PyYAML not installed, skipping YAML syntax validation")
        return True, None
    try:
        yaml.safe_load(config_text)  # type: ignore
        return True, None
    except yaml.YAMLError as e:  # type: ignore
        return False, f"YAML Syntax Error: {e}"

def validate_proxy_providers(providers):
    errors = []
    for pid, info in providers.items():
        p_type = info.get('type', '')
        if not p_type:
            errors.append(f"Provider '{pid}' missing required field 'type'")
        if p_type == 'http':
            p_url = info.get('url', '')
            if not p_url:
                errors.append(f"Provider '{pid}' (type=http) missing required field 'url'")
    return errors

def validate_proxy_groups_structure(groups, provider_names, provider_sections=None):
    errors = []
    if not groups or not isinstance(groups, list):
        errors.append("Missing or invalid 'proxy-groups' section")
        return errors
        
    defined_providers = set(provider_names)
    provider_sections = set(provider_sections) if provider_sections else set()
    
    all_group_names = set()
    for group in groups:
        if not isinstance(group, dict):
            continue
        name = group.get('name', '')
        if name:
            all_group_names.add(name)
    
    for group in groups:
        if not isinstance(group, dict):
            errors.append(f"Invalid group structure: {group}")
            continue
                
        name = group.get('name', '')
        g_type = group.get('type', '')
        proxies = group.get('proxies', [])
        use = group.get('use', [])
            
        if not name:
            errors.append(f"Group missing name: {group}")
            continue
            
        if g_type not in VALID_PROXY_GROUP_TYPES:
            errors.append(f"Group '{name}' has invalid type '{g_type}'")
            
        if use:
            for p in use:
                p_clean = p.replace('[', '').replace(']', '')
                if p_clean not in defined_providers and p_clean not in provider_sections:
                    errors.append(f"Group '{name}' references undefined provider '{p}'")
            
        if proxies:
            for p in proxies:
                p_clean = p.replace('[', '').replace(']', '')
                if p_clean not in all_group_names and p_clean not in ('DIRECT', 'REJECT', 'URL-TEST', 'FALLBACK', 'LOAD-BALANCE'):
                    if p_clean not in defined_providers:
                        errors.append(f"Group '{name}' references undefined proxy '{p_clean}'")
    
    return errors

def validate_rules_format(rules_text, group_names, provider_names):
    errors = []
    all_proxy_refs = group_names | {'DIRECT', 'REJECT'} | set(provider_names)
    
    def get_target(parts):
        for i in range(len(parts) - 1, 0, -1):
            candidate = parts[i].strip()
            if candidate.lower() not in RULE_MODIFIERS:
                return candidate
        return ''
    
    for line_num, line in enumerate(rules_text.strip().split('\n'), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
            
        if line.startswith('- '):
            line = line[2:]
        
        parts = line.split(',')
        if not parts:
            continue
            
        rule_type = parts[0].strip()
        if rule_type in ('GEOSITE', 'GEOIP', 'RULE-SET'):
            if len(parts) < 3:
                errors.append(f"Line {line_num}: Invalid rule format '{line}', expected RULE_TYPE,VALUE,GROUP")
                continue
            target = get_target(parts)
            if target and target not in all_proxy_refs:
                errors.append(f"Line {line_num}: Rule references undefined group/provider '{target}'")
        elif rule_type == 'MATCH':
            if len(parts) < 2:
                errors.append(f"Line {line_num}: Invalid MATCH rule format '{line}'")
                continue
            target = get_target(parts)
            if target and target not in all_proxy_refs:
                errors.append(f"Line {line_num}: MATCH rule references undefined target '{target}'")
        elif rule_type in VALID_RULE_TYPES:
            if len(parts) < 2:
                errors.append(f"Line {line_num}: Invalid rule format '{line}'")
                continue
            if len(parts) >= 3:
                target = get_target(parts)
                if target and target not in all_proxy_refs:
                    errors.append(f"Line {line_num}: Rule references undefined group/provider '{target}'")
        else:
            errors.append(f"Line {line_num}: Unknown rule type '{rule_type}'")
    
    return errors

def validate_config(config_text, provider_names, providers=None):
    errors = []
    providers = providers or {}
    
    is_valid, yaml_error = validate_yaml_syntax(config_text)
    if not is_valid:
        return [yaml_error]
    
    if not YAML_AVAILABLE:
        return []
    
    try:
        data = yaml.safe_load(config_text)  # type: ignore
        
        if 'proxy-providers' in data:
            pp_errors = validate_proxy_providers(data.get('proxy-providers', {}))
            errors.extend(pp_errors)
        
        if 'proxy-groups' in data:
            g_errors = validate_proxy_groups_structure(data['proxy-groups'], provider_names, list(providers.keys()))
            errors.extend(g_errors)
        
        if 'rules' in data:
            rules_list = data.get('rules', [])
            if isinstance(rules_list, list):
                rules_text = '\n'.join(str(r) for r in rules_list)
                group_names = set()
                if 'proxy-groups' in data:
                    for g in data['proxy-groups']:
                        if isinstance(g, dict):
                            group_names.add(g.get('name', ''))
                r_errors = validate_rules_format(rules_text, group_names, provider_names)
                errors.extend(r_errors)
                
    except yaml.YAMLError as e:  # type: ignore
        errors.append(f"YAML parse error: {e}")
    
    return errors

def get_next_version():
    if not OUTPUT_DIR.exists():
        OUTPUT_DIR.mkdir(parents=True)
    
    existing_files = list(OUTPUT_DIR.glob("Clash_Router_*.yaml"))
    if not existing_files:
        return f"{VERSION_PREFIX}a"
    
    suffixes = []
    for f in existing_files:
        name = f.stem
        match = re.match(rf'Clash_Router_{VERSION_PREFIX}([a-z]+)', name)
        if match:
            suffixes.append(match.group(1))
    
    if not suffixes:
        return f"{VERSION_PREFIX}a"
    
    suffixes.sort()
    last_suffix = suffixes[-1]
    
    CHARS = 'abcdefghijklmnopqrstuvwxyz'
    
    def base26_to_num(s):
        num = 0
        for c in s:
            num = num * 26 + CHARS.index(c)
        return num
    
    def num_to_base26(num):
        if num == 0:
            return 'a'
        result = ''
        while num > 0:
            num, rem = divmod(num, 26)
            result = CHARS[rem] + result
        return result
    
    next_num = base26_to_num(last_suffix) + 1
    return f"{VERSION_PREFIX}{num_to_base26(next_num)}"

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

def merge_template_configs(type_name, providers):
    # 定义标准模板文件顺序
    template_suffixes = [
        "general",
        "inbound",
        "dns",
        "proxy-providers",
        "proxy-groups",
        "rule-providers",
        "rules"
    ]
    
    merged_content = ""
    for suffix in template_suffixes:
        filename = f"{type_name}_{suffix}.yaml"
        file_path = TEMPLATE_DIR / filename
        if file_path.exists():
            content = file_path.read_text(encoding='utf-8')
            merged_content += content + "\n\n"
        else:
            # 只有 router 类型是必须的，其他类型如果文件不存在可以跳过
            if type_name == "router":
                print(f"Warning: Template file {filename} not found.")
    
    lines = merged_content.split('\n')
    
    for pid, info in providers.items():
        p_url = info['url']
        p_name = info['name']
        
        in_provider = False
        provider_indent = 0
        
        for i, line in enumerate(lines):
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            
            if stripped == f'{pid}:':
                in_provider = True
                provider_indent = indent
                continue
            
            if in_provider:
                if stripped and indent <= provider_indent:
                    in_provider = False
                    continue
                
                if stripped.startswith('url:'):
                    parts = line.split('"')
                    if len(parts) >= 2:
                        lines[i] = f'{parts[0]}"{p_url}"'
                    in_provider = False
        
    merged_content = '\n'.join(lines)
    
    for pid, info in providers.items():
        p_name = info['name']
        merged_content = re.sub(rf'\b{pid}\b', p_name, merged_content)
        
    return merged_content

def main():
    if len(sys.argv) < 2:
        print("\n[!] 提示: 请提供配置类型名称。")
        print("用法: python build.py <类型>")
        print("例如: python build.py router")
        print("      python build.py android (后续支持)")
        print("      python build.py windows (后续支持)\n")
        return

    config_type = sys.argv[1].lower()
    
    print(f"Reading provider config for type: {config_type}...")
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
    
    print(f"\nMerging {config_type} templates...")
    final_config = merge_template_configs(config_type, providers)
    
    if not final_config.strip():
        print(f"Error: No template files found for type '{config_type}'")
        return

    print(f"\nValidating generated configuration...")
    validation_errors = validate_config(final_config, provider_names, providers)
    
    if validation_errors:
        print(f"\n[ERROR] Configuration validation failed:")
        for err in validation_errors:
            print(f"  - {err}")
        print(f"\nPlease fix the issues above and try again.")
        return
    
    print(f"[OK] Configuration validation passed!")

    # 自动转换首字母大写作为输出前缀
    prefix = f"Clash_{config_type.capitalize()}"
    output_file = OUTPUT_DIR / f"{prefix}_{version}.yaml"
    output_file.write_text(final_config, encoding='utf-8')
    
    print(f"\nDone! Output: {output_file}")

if __name__ == "__main__":
    main()
