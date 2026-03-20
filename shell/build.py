#!/usr/bin/env python3
import os
import re
import configparser
from datetime import datetime
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).parent
TEMPLATE_DIR = SCRIPT_DIR.parent / "template"
OUTPUT_DIR = SCRIPT_DIR / "output"
CONFIG_FILE = SCRIPT_DIR / "provider.cfg"

VERSION_PREFIX = datetime.now().strftime("%m%d")

def get_next_version():
    if not OUTPUT_DIR.exists():
        OUTPUT_DIR.mkdir(parents=True)
    
    existing_files = list(OUTPUT_DIR.glob("Clash_Router_*.yaml"))
    if not existing_files:
        return f"{VERSION_PREFIX}a"
    
    suffixes = []
    for f in existing_files:
        name = f.stem
        # 匹配 Clash_Router_0320a 格式
        match = re.match(rf'Clash_Router_{VERSION_PREFIX}([a-z]+)', name)
        if match:
            suffixes.append(match.group(1))
    
    if not suffixes:
        return f"{VERSION_PREFIX}a"
    
    suffixes.sort()
    last_suffix = suffixes[-1]
    
    # 简单的后缀递增逻辑 a -> b -> ... -> z
    if last_suffix == 'z':
        return f"{VERSION_PREFIX}za" # 超过26次后的处理
    else:
        next_suffix = chr(ord(last_suffix[-1]) + 1)
        return f"{VERSION_PREFIX}{last_suffix[:-1]}{next_suffix}"

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
            
    # Replacement logic
    for pid, info in providers.items():
        p_name = info['name']
        p_url = info['url']
        
        # 1. 替换 Provider 定义块中的 URL
        url_pattern = rf'({pid}:(?:(?!\n  \S).)*?\s+url:\s*)"[^"]*"'
        merged_content = re.sub(url_pattern, rf'\1"{p_url}"', merged_content, flags=re.DOTALL)
        
        # 2. 将所有的占位符 ID 替换为真实的名称
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

    # 自动转换首字母大写作为输出前缀
    prefix = f"Clash_{config_type.capitalize()}"
    output_file = OUTPUT_DIR / f"{prefix}_{version}.yaml"
    output_file.write_text(final_config, encoding='utf-8')
    
    print(f"\nDone! Output: {output_file}")

if __name__ == "__main__":
    main()
