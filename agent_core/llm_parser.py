import os
import google.generativeai as genai

def setup_llm():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[Warning] GEMINI_API_KEY not found. LLM parsing will return raw text.")
        return False
    genai.configure(api_key=api_key)
    return True

def _resolve_media(key, media_files):
    """Match an inline marker like 'instagram img' to a media file in the folder."""
    import re
    import os

    def norm(s):
        return re.sub(r'\s+', ' ', s).strip().lower()

    target = norm(key)
    # 1) exact match on filename without extension
    for mf in media_files:
        base = os.path.splitext(mf['name'])[0]
        if norm(base) == target:
            return mf
    # 2) fallback: one contains the other
    for mf in media_files:
        base = norm(os.path.splitext(mf['name'])[0])
        if target and (target in base or base in target):
            return mf
    return None


def rich_text_to_html(raw_text, media_files=None, root_path="../", base_path=""):
    import re
    import html

    media_files = media_files or []
    used_media = []
    url_pattern = re.compile(r'(https?://[^\s\n]+)')
    # Inline marker for a document link inside a folder, e.g. <링크 : 피부클리닉기획서.html>
    doc_pattern = re.compile(r'&lt;\s*링크\s*[:：]?\s*(.+?)\s*&gt;')

    def make_link(match):
        url = match.group(1)
        return f'<a href="{url}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center text-blue-600 hover:text-blue-800 hover:underline font-semibold break-all mt-1 gap-1"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>{url}</a>'

    image_exts = ('.jpg', '.jpeg', '.png', '.gif', '.webp')

    def make_doc_link(match):
        fname = html.unescape(match.group(1)).strip()
        label = html.escape(fname)
        ext = os.path.splitext(fname)[1].lower()

        # Image link -> open in the shared lightbox popup (defined in layout.html)
        if ext in image_exts:
            mf = _resolve_media(os.path.splitext(fname)[0], media_files)
            if mf:
                used_media.append(mf['name'])
                rel = mf['path']
                caption = mf['name']
            else:
                rel = f"{base_path}/{fname}" if base_path else fname
                caption = fname
            src = html.escape(f"{root_path}{rel}")
            cap = html.escape(caption)
            return (
                f'<a href="{src}" onclick="openLightbox(\'{src}\', \'{cap}\'); return false;" '
                f'class="inline-flex items-center text-blue-600 hover:text-blue-800 hover:underline font-semibold gap-1 cursor-pointer">'
                f'<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>{label}</a>'
            )

        # Non-image document link -> open in a new tab
        rel = f"{base_path}/{fname}" if base_path else fname
        href = html.escape(f"{root_path}{rel}")
        return f'<a href="{href}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center text-blue-600 hover:text-blue-800 hover:underline font-semibold gap-1"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>{label}</a>'

    def apply_inline(text):
        text = url_pattern.sub(make_link, text)
        text = doc_pattern.sub(make_doc_link, text)
        return text

    raw_lines = [line.strip() for line in raw_text.split('\n')]
    lines = [html.escape(line) for line in raw_lines]
    formatted_html = []
    last_url = None  # most recent URL, used as click target for inline images

    i = 0
    consecutive_empty = 0
    while i < len(lines):
        raw_line = raw_lines[i]

        # Marker: <br>  ->  line break / vertical gap
        if raw_line.lower() == '<br>':
            formatted_html.append('<div class="h-6"></div>')
            consecutive_empty = 0
            i += 1
            continue

        # Marker: <xxx img>  ->  insert matching image from the same folder
        marker_match = re.match(r'^<\s*(.+?)\s*>$', raw_line)
        if marker_match and media_files:
            mf = _resolve_media(marker_match.group(1), media_files)
            if mf:
                used_media.append(mf['name'])
                src = html.escape(f"{root_path}{mf['path']}")
                alt = html.escape(mf['name'])
                img_tag = (
                    f'<img src="{src}" alt="{alt}" loading="lazy" '
                    f'class="w-full max-w-2xl md:max-w-3xl h-auto rounded-xl shadow-md border border-gray-100">'
                )
                if last_url:
                    inner = (
                        f'<a href="{html.escape(last_url)}" target="_blank" rel="noopener noreferrer" '
                        f'class="block hover:opacity-90 transition-opacity">{img_tag}</a>'
                    )
                else:
                    inner = img_tag
                formatted_html.append(f'<div class="my-6 flex justify-center">{inner}</div>')
                consecutive_empty = 0
                i += 1
                continue

        line = lines[i]
        if not line:
            consecutive_empty += 1
            if consecutive_empty == 2 and i > 0 and i < len(lines) - 1:
                formatted_html.append('<div class="h-10"></div>')
            i += 1
            continue
        consecutive_empty = 0

        # Remember the most recent URL so a following image can link to it
        url_here = url_pattern.search(raw_line)
        if url_here:
            last_url = url_here.group(1)

        # Match top-level (1.) and nested (1-1., 1-2-3.) numbered list items
        list_match = re.match(r'^(\d+(?:-\d+)*)\.\s*(.*)', line)
        bullet_match = re.match(r'^([-●*])\s*(.*)', line)

        if list_match:
            num = list_match.group(1)
            title = list_match.group(2)
            is_sub = '-' in num

            next_url = ""
            j = i + 1
            while j < len(lines) and not lines[j]:
                j += 1
            if j < len(lines) and url_pattern.match(lines[j]):
                next_url = lines[j]
                i = j
                merged_url = url_pattern.search(next_url)
                if merged_url:
                    last_url = merged_url.group(1)

            title_with_links = apply_inline(title)
            link_html = url_pattern.sub(make_link, next_url) if next_url else ""
            inner_link = f'<div class="mt-1">{link_html}</div>' if next_url else ''

            if is_sub:
                wrapper_cls = "flex items-start gap-3 p-3.5 mb-2 ml-6 md:ml-10 bg-white border border-gray-100 rounded-lg hover:bg-gray-50 transition-all duration-300 shadow-sm"
                badge_cls = "flex items-center justify-center min-w-[2.25rem] h-6 px-2 rounded-full bg-blue-50/70 text-blue-500 font-bold text-xs flex-shrink-0"
                title_cls = "font-semibold text-gray-800 text-base leading-snug"
            else:
                wrapper_cls = "flex items-start gap-4 p-5 mb-4 bg-gray-50 border border-gray-100 rounded-xl hover:bg-gray-100/70 transition-all duration-300 shadow-sm hover:shadow"
                badge_cls = "flex items-center justify-center w-8 h-8 rounded-full bg-blue-50 text-blue-600 font-bold text-sm flex-shrink-0"
                title_cls = "font-bold text-gray-900 text-lg leading-snug"

            formatted_html.append(f'''
            <div class="{wrapper_cls}">
                <span class="{badge_cls}">{num}</span>
                <div class="flex-1">
                    <h4 class="{title_cls}">{title_with_links}</h4>
                    {inner_link}
                </div>
            </div>
            ''')
        elif bullet_match:
            bullet_char = bullet_match.group(1)
            content = bullet_match.group(2)
            content_with_links = apply_inline(content)
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
                line_with_links = apply_inline(line)
                if line.startswith('●') and line.endswith('●'):
                    title_text = line.strip('●')
                    formatted_html.append(f'<h3 class="text-xl font-bold text-gray-900 mt-6 mb-4 pb-2 border-b border-gray-100 flex items-center gap-2"><span class="w-1.5 h-6 bg-blue-600 rounded-full"></span>{title_text}</h3>')
                else:
                    formatted_html.append(f'<p class="text-base text-gray-700 leading-relaxed mb-4">{line_with_links}</p>')
        i += 1
        
    html_out = '<div class="space-y-1">' + "\n".join(formatted_html) + '</div>'
    return html_out, used_media

def parse_text_content(file_path, media_files=None, root_path="../", base_path=""):
    media_files = media_files or []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_text = f.read()

        if not setup_llm():
            filename = os.path.splitext(os.path.basename(file_path))[0]
            content, used_media = rich_text_to_html(raw_text, media_files, root_path, base_path)
            return {
                "title": filename,
                "content": content,
                "_used_media": used_media
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
        content, used_media = rich_text_to_html(raw_text, media_files, root_path, base_path)
        return {
            "title": filename,
            "content": content,
            "_used_media": used_media
        }
