import os
import glob

# 定义要处理的目录
template_dir = r'd:\Project\Immortal-Custom-Rules\template'
files = glob.glob(os.path.join(template_dir, '*.yaml'))

# 之前发现的所有 Emoji 和特殊图标 (包括可能带空格的)
emojis_to_remove = [
    '🔰 ', '🔰',
    '🔁 ', '🔁',
    '🇭🇰 ', '🇭🇰',
    '🇹🇼 ', '🇹🇼',
    '🇸🇬 ', '🇸🇬',
    '🇯🇵 ', '🇯🇵',
    '🇰🇷 ', '🇰🇷',
    '🇺🇸 ', '🇺🇸',
    '🇺🇲 ', '🇺🇲',
    '🇺🇳 ', '🇺🇳',
    '⬇️ ', '⬇️',
    '🤖 ', '🤖',
    '📲 ', '📲',
    '📹 ', '📹',
    '🎥 ', '🎥',
    '📺 ', '📺',
    '🐱 ', '🐱',
    '🔎 ', '🔎',
    '🎮 ', '🎮',
    '🛑 ', '🛑',
    '🛡️ ', '🛡️',
    '🎯 ', '🎯',
    '🫰 ', '🫰',
    '♻️ ', '♻️',
    '%F0%9F%94%B0%20', '%F0%9F%94%B0' # 🔰 的 URL 编码
]

for file_path in files:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = content
    for emoji in emojis_to_remove:
        new_content = new_content.replace(emoji, '')
    
    # 针对部分可能残留的 Unicode 变体选择符
    new_content = new_content.replace('\ufe0f', '')
    
    if content != new_content:
        with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(new_content)
        print(f'Processed: {os.path.basename(file_path)}')
    else:
        print(f'No emojis found in: {os.path.basename(file_path)}')
