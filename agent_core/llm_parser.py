import os
import google.generativeai as genai

def setup_llm():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[Warning] GEMINI_API_KEY not found. LLM parsing will return raw text.")
        return False
    genai.configure(api_key=api_key)
    return True

def rich_text_to_html(raw_text):
    import re
    import html
    
    escaped_text = html.escape(raw_text)
    url_pattern = re.compile(r'(https?://[^\s\n]+)')
    
    def make_link(match):
        url = match.group(1)
        return f'<a href="{url}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center text-blue-600 hover:text-blue-800 hover:underline font-semibold break-all mt-1 gap-1"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>{url}</a>'
    
    lines = [line.strip() for line in escaped_text.split('\n')]
    formatted_html = []
    
    i = 0
    consecutive_empty = 0
    while i < len(lines):
        line = lines[i]
        if not line:
            consecutive_empty += 1
            if consecutive_empty == 2 and i > 0 and i < len(lines) - 1:
                formatted_html.append('<div class="h-10"></div>')
            i += 1
            continue
        consecutive_empty = 0
            
        list_match = re.match(r'^(\d+)\.\s*(.*)', line)
        bullet_match = re.match(r'^([-●*])\s*(.*)', line)
        
        if list_match:
            num = list_match.group(1)
            title = list_match.group(2)
            
            next_url = ""
            j = i + 1
            while j < len(lines) and not lines[j]:
                j += 1
            if j < len(lines) and url_pattern.match(lines[j]):
                next_url = lines[j]
                i = j
                
            title_with_links = url_pattern.sub(make_link, title)
            if next_url:
                link_html = url_pattern.sub(make_link, next_url)
                formatted_html.append(f'''
                <div class="flex items-start gap-4 p-5 mb-4 bg-gray-50 border border-gray-100 rounded-xl hover:bg-gray-100/70 transition-all duration-300 shadow-sm hover:shadow">
                    <span class="flex items-center justify-center w-8 h-8 rounded-full bg-blue-50 text-blue-600 font-bold text-sm flex-shrink-0">{num}</span>
                    <div class="flex-1">
                        <h4 class="font-bold text-gray-900 text-lg leading-snug">{title_with_links}</h4>
                        <div class="mt-1">{link_html}</div>
                    </div>
                </div>
                ''')
            else:
                formatted_html.append(f'''
                <div class="flex items-start gap-4 p-5 mb-4 bg-gray-50 border border-gray-100 rounded-xl hover:bg-gray-100/70 transition-all duration-300 shadow-sm hover:shadow">
                    <span class="flex items-center justify-center w-8 h-8 rounded-full bg-blue-50 text-blue-600 font-bold text-sm flex-shrink-0">{num}</span>
                    <div class="flex-1">
                        <h4 class="font-bold text-gray-900 text-lg leading-snug">{title_with_links}</h4>
                    </div>
                </div>
                ''')
        elif bullet_match:
            bullet_char = bullet_match.group(1)
            content = bullet_match.group(2)
            content_with_links = url_pattern.sub(make_link, content)
            formatted_html.append(f'''
            <div class="flex items-start gap-2 pl-4 mb-2 text-gray-700">
                <span class="text-blue-500 flex-shrink-0 mt-1.5">•</span>
                <span class="text-base leading-relaxed">{content_with_links}</span>
            </div>
            ''')
        else:
            if url_pattern.match(line):
                link_html = url_pattern.sub(make_link, line)
                formatted_html.append(f'<div class="mb-4 pl-4">{link_html}</div>')
            else:
                line_with_links = url_pattern.sub(make_link, line)
                if line.startswith('●') and line.endswith('●'):
                    title_text = line.strip('●')
                    formatted_html.append(f'<h3 class="text-xl font-bold text-gray-900 mt-6 mb-4 pb-2 border-b border-gray-100 flex items-center gap-2"><span class="w-1.5 h-6 bg-blue-600 rounded-full"></span>{title_text}</h3>')
                else:
                    formatted_html.append(f'<p class="text-base text-gray-700 leading-relaxed mb-4">{line_with_links}</p>')
        i += 1
        
    return '<div class="space-y-1">' + "\n".join(formatted_html) + '</div>'

def parse_text_content(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_text = f.read()
            
        if not setup_llm():
            filename = os.path.splitext(os.path.basename(file_path))[0]
            return {
                "title": filename,
                "content": rich_text_to_html(raw_text)
            }
            
        model = genai.GenerativeModel('gemini-1.5-pro')
        prompt = f"""
다음은 포트폴리오 블로그 뷰용 텍스트입니다. 이 텍스트를 분석하여 가장 핵심적인 요약 문장을 [제목]으로 도출하고, 
본문은 가독성이 좋은 HTML 태그(Tailwind CSS 클래스 포함)로 구성해주세요.

요구사항:
1. 반환 형식은 반드시 JSON 이어야 합니다.
2. JSON 키: "title", "content"
3. "title"은 문자열, "content"는 HTML 문자열입니다.
4. "content"에는 Tailwind 클래스(예: font-bold, text-base, leading-relaxed, mb-4 등)를 적절히 섞어 세련되게 만들어주세요.
5. 만약 텍스트 내에 URL 링크(예: https://...)가 포함되어 있다면, 클릭 시 새 창에서 열리도록 a 태그(`target='_blank' rel='noopener noreferrer'`)를 적용해 주시고 세련된 링크 스타일(예: text-blue-600 hover:text-blue-800 hover:underline font-semibold gap-1 inline-flex items-center)을 적용해주세요.
6. 리스트 형태의 텍스트인 경우 세로로 정렬된 예쁜 리스트 레이아웃(예: 여백 및 카드 스타일 테두리 등)으로 출력되도록 해주세요.

텍스트 내용:
{raw_text}
"""
        response = model.generate_content(prompt)
        text_resp = response.text
        start = text_resp.find('{')
        end = text_resp.rfind('}')
        if start != -1 and end != -1:
            json_str = text_resp[start:end+1]
            return eval(json_str)
            
    except Exception as e:
        print(f"[Error] LLM Parsing failed for {file_path}: {e}")
        filename = os.path.splitext(os.path.basename(file_path))[0]
        return {
            "title": filename,
            "content": rich_text_to_html(raw_text)
        }
