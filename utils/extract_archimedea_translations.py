"""
从翻译文件中提取深层科研(Archimedea)相关的翻译
"""
import json
import os

def extract_archimedea_translations(zh_json_path, output_path):
    """提取Archimedea相关翻译"""
    print(f"正在读取翻译文件: {zh_json_path}")
    with open(zh_json_path, 'r', encoding='utf-8') as f:
        translations = json.load(f)
    
    archimedea_translations = {}
    
    # 提取条件翻译
    for key, value in translations.items():
        if key.startswith('/Lotus/Language/Conquest/Condition_'):
            archimedea_translations[key] = value
            print(f"提取条件翻译: {key} = {value}")
    
    # 提取任务变体翻译
    for key, value in translations.items():
        if key.startswith('/Lotus/Language/Conquest/MissionVariant_'):
            archimedea_translations[key] = value
            print(f"提取任务变体翻译: {key} = {value}")
    
    print(f"\n共提取 {len(archimedea_translations)} 条翻译")
    
    # 保存到文件
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(archimedea_translations, f, ensure_ascii=False, indent=2)
    
    print(f"翻译已保存到: {output_path}")
    return archimedea_translations

if __name__ == '__main__':
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    zh_json_path = os.path.join(project_root, 'data', 'translations', 'zh.json')
    output_path = os.path.join(project_root, 'data', 'archimedea_tags.json')
    
    extract_archimedea_translations(zh_json_path, output_path)
