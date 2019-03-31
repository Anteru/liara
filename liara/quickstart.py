from .yaml import dump_yaml
from .config import create_default_metadata

__TEMPLATES = {
    'page.jinja2': """
<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <meta name=viewport content="width=device-width, initial-scale=1">
      <title>
      {% block title %}
          {% if page.meta.title and page.url != '/' %}
            {{ page.meta.title }}
        {% else %}
            My blog
        {% endif %}
        {% endblock %}
    </title>
    <link type="text/css" rel="stylesheet" href="/style.css" />
</head>
<body>
    <div class="container">
        <header id="header">
            <nav>
                <a href="/">Home</a>
                <a href="/archive">Archive</a>
            </nav>
        </header>
        <main id="content">
        {% block content %}
            {{ page.content }}
        {% endblock %}
        </main>
        <footer id="footer">
            <p>Generated using Liara</p>
        </footer>
    </div>
</body>
</html>
    """,
    'blog.jinja2': """{% extends "page.jinja2" %}
{% block content %}
<article>
    <header>
        <h1>{{page.meta.title}}</h1>
        <div class="metadata">
            <div class="post-time">
              <time datetime="{{ page.meta.date }}">{{
                  page.meta.date.strftime("%Y-%m-%d, %H:%M") }}</time>
            </div>
            <div class="tags">
              <ul class="tags">
                {% for tag in page.meta.tags|sort %}
                  <li>
                    <a href="/archive/by-tag/{{ tag }}">
                        {{ tag|capitalize }}
                    </a>
                   </li>
                {% endfor %}
              </ul>
            </div>
        </div>
    </header>
    {{ page.content }}
    <aside>
        <div class="pagination">
            {% set previous = site.get_previous_in_collection('blog', page) %}
            {% set next = site.get_next_in_collection('blog', page) %}
            {% if previous %}
                <div class="previous">
                    <a href="{{ previous.url }}">Previous post</a>
                </div>
            {% endif %}
            {% if next %}
                <div class="next">
                    <a href="{{ next.url }}">Next post</a>
                </div>
            {% endif %}
        </div>
    </aside>
</article>
{% endblock %}
    """,
    'archive.jinja2': """
{% extends "page.jinja2" %}
{% block content %}
<h1>Blog archive {% if page.meta.key %}for {{ page.meta.key }}{% endif %}</h1>
{{ page.content }}
<ul>
    {% if page.references %}
        {% for ref in page.references %}
        <li>
            <a href="{{ ref.url }}">{{ ref.meta.title }}</a>
        </li>
        {% endfor %}
    {% else %}
        {% for page in
        node.select_children().sorted_by_metadata('key') %}
        <li>
            <a href="{{ page.url }}">{{ page.meta.key }}</a>
            ({{ page.references|length }} posts)
            <ul>
                {% for ref in page.references.sorted_by_date(reverse=True) %}
                <li>
                    <a href="{{ ref.url }}">{{ ref.meta.title}}</a>
                </li>
                {% endfor %}
            </ul>
        </li>
        {% endfor %}
    {% endif %}
</ul>
{% endblock %}
    """
}

__SCSS = """
.container {
    max-width: 800px;

    margin: auto;

    header {
        background-color: #EEE;
        padding: 0.5em;
    }

    main {
        padding: 0.5em;

        header {
            padding: 0;
            background-color: unset;
        }
    }

    footer {
        font-size: 0.8em;
        padding: 0.5em;
        border-top: 1px solid #CCC;
    }
}
"""

__THEME_CONFIG = {
    'backend': 'jinja2',
    'paths': {
        '/blog/*?kind=document': 'blog.jinja2',
        '/archive/*': 'archive.jinja2',
        '/*': 'page.jinja2',
    },
    'resource_directory': 'resources'
}

__BLOG_POST_GENERATOR = r"""
import liara
import pathlib
import datetime


def generate(site: liara.site.Site, configuration) -> pathlib.Path:
    title = input("Blog title: ")
    slug = liara.util.create_slug(title)
    tags = input("Tags (comma separated): ")
    # need list to avoid YAML containing special tags
    tags = list(set(map(str.strip, tags.split(','))))
    now = liara.util.local_now()

    metadata = liara.yaml.dump_yaml({
        'title': title,
        'tags': tags,
        'date': now
    })

    content = '---\n'
    content += metadata
    content += '---\n'
    content += '\n'
    content += 'Blog post content goes here!'

    content_directory = configuration['content_directory']
    output_file = pathlib.Path(f"{content_directory}/blog/{now.year}/{slug}.md")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(content)
    return output_file
"""


def generate_templates():
    for k, v in __TEMPLATES.items():
        open(f'templates/{k}', 'w').write(v)


def generate_css():
    import os
    os.makedirs('templates/resources', exist_ok=True)
    open('templates/resources/style.scss', 'w').write(__SCSS)


def generate_theme():
    import os
    os.makedirs('templates', exist_ok=True)
    generate_templates()
    generate_css()
    dump_yaml(__THEME_CONFIG, open('templates/default.yaml', 'w'))


def generate_content():
    import datetime
    import os
    page_template = """---
title: %TITLE%
tags: [%TAGS%]
date: %DATE%
---

Sample post using _Markdown_
"""

    dates = [
        datetime.datetime(2019, 1, 3),
        datetime.datetime(2018, 1, 5),
        datetime.datetime(2017, 3, 1)
    ]

    titles = [
        'Newest post',
        'Old but not oldest post',
        'The beginning'
    ]

    tags = [
        ['new', 'featured'],
        ['old'],
        ['old', 'historic']
    ]

    slugs = [
        'newest-post',
        'old-but-not-oldest-post',
        'the-beginning'
    ]

    os.makedirs('content/blog', exist_ok=True)

    for date, title, tag, slug in zip(dates, titles, tags, slugs):
        t = page_template.replace("%TITLE%", title)
        t = t.replace("%TAGS%", ', '.join(tag))
        t = t.replace("%DATE%", str(date))
        os.makedirs(f'content/blog/{date.year}', exist_ok=True)
        open(f'content/blog/{date.year}/{slug}.md', 'w').write(t)

    open('content/archive.md', 'w').write("""
---
title: The archive
---

The blog archive. Find blog posts [by year](/archive/by-year) or
[by tag](/archive/by-tag).""")

    open('content/_index.md', 'w').write("""
---
title: Hello world
---

Welcome to the sample blog.""")


__DEFAULT_CONFIG = {
    'collections': 'collections.yaml',
    'indices': 'indices.yaml'
}

__DEFAULT_COLLECTIONS = {
    'blog': {
        'filter': '/blog/**',
        'order_by': 'date'
    }
}

__DEFAULT_INDICES = [
    {
        'collection': 'blog',
        'group_by': ['date.year'],
        'path': '/archive/by-year/%1',
        'create_top_level_index': True
    },
    {
        'collection': 'blog',
        'group_by': ['*tags'],
        'path': '/archive/by-tag/%1',
        'create_top_level_index': True
    }
]


def generate_configs():
    dump_yaml(__DEFAULT_CONFIG, open('config.yaml', 'w'))
    dump_yaml(create_default_metadata(), open('metadata.yaml', 'w'))
    dump_yaml(__DEFAULT_COLLECTIONS, open('collections.yaml', 'w'))
    dump_yaml(__DEFAULT_INDICES, open('indices.yaml', 'w'))


def generate_generator():
    import os
    os.makedirs('generators', exist_ok=True)
    output_file = os.path.join('generators', 'blog-post.py')
    open(output_file, 'w').write(__BLOG_POST_GENERATOR)


def generate():
    generate_theme()
    generate_content()
    generate_configs()
    generate_generator()
