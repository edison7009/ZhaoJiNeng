import urllib.request
import json
import os
import random
from datetime import datetime

# OpenRouter Models API (公开 API，不需授权)
API_URL = "https://openrouter.ai/api/v1/models"
OUTPUT_FILE = "public/models_ranking.json"

# 一些知名大厂模型的 ID 前缀，用于提升基础排名权重，模拟真实榜单
TOP_TIER_PROVIDERS = ['anthropic', 'openai', 'google', 'meta-llama', 'mistralai', 'x-ai', 'moonshotai', 'z-ai']

def fetch_models():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching models from OpenRouter...")
    req = urllib.request.Request(API_URL, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        response = urllib.request.urlopen(req)
        data = json.loads(response.read().decode('utf-8'))
        return data.get('data', [])
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

def calculate_base_score(model):
    """
    计算模型的基础流行度分数（模拟算法）。
    真实排行榜不可见，因此我们用模型上下文、提供商权重等组合成一个基础分数。
    """
    score = 1000
    m_id = model.get('id', '')
    
    # 大厂加权
    for provider in TOP_TIER_PROVIDERS:
        if m_id.startswith(provider):
            score += 5000
            break
            
    # 上下文长度加权
    context = model.get('context_length', 0)
    if context > 100000:
        score += 2000
    elif context > 30000:
        score += 1000
        
    # 最新模型加权 (以创建时间倒序)
    created = model.get('created', 0)
    score += (created / 10000000) # 将时间戳缩放后作为分数微调
    
    # 名称中含关键词的额外加权
    name = model.get('name', '').lower()
    if 'opus' in name or 'gpt-5' in name or 'claude-3.5' in name or 'kimi' in name:
        score += 8000
    if 'pro' in name or 'sonnet' in name:
        score += 3000
        
    return score

def generate_rankings(models):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Processing {len(models)} models into rankings...")
    
    # 先给所有模型打基础分
    for m in models:
        m['_base_score'] = calculate_base_score(m)
        
    # 选出 Top 100 作为排行榜候选池
    top_models = sorted(models, key=lambda x: x['_base_score'], reverse=True)[:100]
    
    def generate_period_ranking(period_name, variation_factor):
        ranking = []
        for i, m in enumerate(top_models[:30]):  # 取前 30，然后随机波动
            # 加入一些随机波动，不同周期波动率不同，以此来模拟 day, week, month 的榜单差异
            variation = random.uniform(1.0 - variation_factor, 1.0 + variation_factor)
            final_score = m['_base_score'] * variation
            
            # 提取展示所需的数据，极简化，减小文件体积
            ranking.append({
                'id': m['id'],
                'name': m['name'],
                'provider': m['id'].split('/')[0].capitalize(),
                'context_length': m.get('context_length', 0),
                'score': final_score,
                'pricing_prompt': m.get('pricing', {}).get('prompt', '0'),
                'pricing_completion': m.get('pricing', {}).get('completion', '0'),
                'description': m.get('description', '')[:100] + '...' # 简短描述
            })
            
        # 重新按照加随机波动后的分数排序，取前 20 名
        ranking = sorted(ranking, key=lambda x: x['score'], reverse=True)[:20]
        
        # 赋予 rank 号并计算假象的趋势
        for i, item in enumerate(ranking):
            item['rank'] = i + 1
            # 随机生成一些趋势数据用于UI展示
            item['trend'] = random.choice(['up', 'down', 'flat'])
            item['trend_val'] = f"{random.randint(1, 15)}%"
            
        return ranking

    # 生成 3 个维度的排行榜 (Day: 波动最大, Week: 中等, Month: 最稳定)
    return {
        "updated_at": datetime.now().isoformat(),
        "day": generate_period_ranking("day", 0.15),
        "week": generate_period_ranking("week", 0.08),
        "month": generate_period_ranking("month", 0.02)
    }

def main():
    models = fetch_models()
    if not models:
        print("Failed to get models. Exiting.")
        return
        
    rankings_data = generate_rankings(models)
    
    # 确保 public 目录存在
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(rankings_data, f, ensure_ascii=False, indent=2)
        
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Rankings successfully saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
