from .yaml import dump_yaml


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
    <header id="header">
        <a class="/">Home</a>
        <a class="/archive">Archive</a>
    </header>
    <div id="container">
        <main id="content">
        {% block content %}
        {% endblock %}
        </main>
    </div>
    <footer id="footer">
        <p>Generated using Liara</p>
    </footer>
</body>
</html>
    """,
    'blog.jinja2': """
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
                    <a href="/blog/tags/{{ tag }}">{{ tag|capitalize }}</a>
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
    """,
    'archive.jinja2': """
{% extends "page.jinja2" %}
{% block content %}
<h1>Blog archive</h1>
{{ page.content }}
<ul>
    {% for page in
       node.select_children().sorted_by_tag('key',reverse=reverse) %}
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
</ul>
{% endblock %}
    """
}

__SCSS = """
"""

__THEME_CONFIG = {
    'backend': 'jinja2',
    'paths': {
        '/blog/*': 'blog.jinja2',
        '/': 'page.jinja2',
        '/archive': 'archive.jinja2'
    }
}


def generate_templates():
    for k, v in __TEMPLATES.items():
        open(f'templates/{k}', 'w').write(v)


def generate_css():
    open('templates/style.scss', 'w').write(__SCSS)


def generate_theme():
    import os
    os.makedirs('templates', exist_ok=True)
    generate_templates()
    generate_css()
    dump_yaml(__THEME_CONFIG, open('templates/default.yaml', 'w'))


def generate_content():
    import datetime
    import os
    page_template = """
---
title: %TITLE%
tags: %TAGS%
date: %DATE%
----

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
        os.makedirs(f'content/blog/{{ date.year }}', exist_ok=True)
        open(f'content/blog/{{ date.year }}/f{slug}.md', 'w').write(t)

    open('content/archive.md', 'w').write("""
---
title: The archive
---

The blog archive
    """)

    open('content/_index.md', 'w').write("""
---
title: Hello world
---

Welcome to the sample blog.""")


def generate():
    generate_theme()
    generate_content()
