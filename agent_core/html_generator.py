import os
import json
from jinja2 import Environment, FileSystemLoader
from llm_parser import parse_text_content

def generate_site(tree_data, root_dir):
    templates_dir = os.path.join(root_dir, 'templates')
    out_dir = os.path.join(root_dir, '_site')
    os.makedirs(out_dir, exist_ok=True)
    
    env = Environment(loader=FileSystemLoader(templates_dir))
    layout_tpl = env.get_template('layout.html')
    
    # 1. Generate Index
    index_html = layout_tpl.render(
        tree_data=tree_data,
        current_node=None,
        content_html="<div class='flex items-center justify-center h-full'><h2 class='text-2xl text-gray-400'>Select a category from the menu.</h2></div>",
        root_path="../"
    )
    with open(os.path.join(out_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(index_html)
        
    # 2. Generate subpages
    _generate_subpages(env, tree_data, tree_data.get('categories', []), out_dir, root_dir)
    print("[Info] Site generation complete.")

def _generate_subpages(env, tree_data, categories, out_dir, root_dir):
    layout_tpl = env.get_template('layout.html')
    gallery_tpl = env.get_template('gallery.html')
    blog_tpl = env.get_template('blog.html')
    
    for cat in categories:
        # Create output path
        # Flatten path for HTML name
        path_name = cat['path'].replace('/', '_').replace(' ', '_')
        page_name = f"{path_name}.html"
        
        # Decide content (Gallery or Blog)
        # Separate media and text files
        media_files = [f for f in cat.get('files', []) if f['type'] == 'media']
        text_files = [f for f in cat.get('files', []) if f['type'] == 'text']
        
        # Parse text first so we know which images are placed inline via markers
        parsed_posts = []
        inline_media = set()
        for t_file in text_files:
            parsed = parse_text_content(
                os.path.join(root_dir, t_file['path']),
                media_files=media_files,
                root_path="../"
            )
            parsed_posts.append(parsed)
            inline_media.update(parsed.get('_used_media', []))

        # Images referenced inline are excluded from the gallery grid to avoid duplication
        gallery_media = [f for f in media_files if f['name'] not in inline_media]

        content_parts = []

        if gallery_media:
            content_parts.append(gallery_tpl.render(files=gallery_media, root_path="../"))

        for parsed in parsed_posts:
            content_parts.append(blog_tpl.render(post=parsed))
            
        if not content_parts and not cat.get('children'):
            content_html = "<div class='p-8 text-gray-500'>Empty category.</div>"
        else:
            content_html = "\n".join(content_parts)
            
        page_html = layout_tpl.render(
            tree_data=tree_data,
            current_node=cat,
            content_html=content_html,
            root_path="../" # Adjust relative paths
        )
        
        with open(os.path.join(out_dir, page_name), 'w', encoding='utf-8') as f:
            f.write(page_html)
            
        # Recursive
        if cat.get('children'):
            _generate_subpages(env, tree_data, cat['children'], out_dir, root_dir)
