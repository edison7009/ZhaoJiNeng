import json, os, math

def main():
    base_dir = os.path.dirname(__file__)
    skills_path = os.path.join(base_dir, 'skills.json')
    pages_dir = os.path.join(base_dir, 'public', 'skills_pages')
    os.makedirs(pages_dir, exist_ok=True)
    
    with open(skills_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    all_skills = data.get('skills', [])
    # 按照 downloads 排序，确保最热门在前面
    all_skills.sort(key=lambda x: (x.get('stars', 0), x.get('downloads', 0)), reverse=True)
    
    page_size = 50
    total_pages = math.ceil(len(all_skills) / page_size)
    
    for page in range(1, total_pages + 1):
        start = (page - 1) * page_size
        end = start + page_size
        page_skills = all_skills[start:end]
        
        page_data = {
            'page': page,
            'total_pages': total_pages,
            'total': len(all_skills),
            'skills': page_skills
        }
        
        out_file = os.path.join(pages_dir, f'{page}.json')
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(page_data, f, ensure_ascii=False)
            
    print(f"Generated {total_pages} pages in {pages_dir}")

if __name__ == '__main__':
    main()
