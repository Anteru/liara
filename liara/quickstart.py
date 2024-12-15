from .yaml import dump_yaml
from .config import create_default_metadata


__TEMPLATES_JINJA2 = {
    'page.jinja2': r"""
<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <meta name=viewport content="width=device-width, initial-scale=1">
      <title>
      {% block title %}
          {% if page.metadata.title and page.url != '/' %}
            {{ page.metadata.title }}
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
    'blog.jinja2': r"""{% extends "page.jinja2" %}
{% block content %}
<article>
    <header>
        <h1>{{page.meta.title}}</h1>
        <div class="metadata">
            <div class="post-time">
              <time datetime="{{ page.metadata.date }}">{{
                  page.metadata.date.strftime("%Y-%m-%d, %H:%M") }}</time>
            </div>
            <div class="tags">
              <ul class="tags">
                {% for tag in page.metadata.tags|sort %}
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
    'archive.jinja2': r"""
{% extends "page.jinja2" %}
{% block content %}
<h1>Blog archive {% if page.metadata.key %}for {{ page.metadata.key }}{% endif %}</h1>
{{ page.content }}
<ul>
    {% if not page.metadata.top_level_index %}
        {% for ref in page.references %}
        <li>
            <a href="{{ ref.url }}">{{ ref.meta.title }}</a>
        </li>
        {% endfor %}
    {% else %}
        {% for child_page in
        page.children.sorted_by_metadata('key') %}
        <li>
            <a href="{{ child_page.url }}">{{ child_page.metadata.key }}</a>
            ({{ child_page.references|length }} posts)
            <ul>
                {% for ref in child_page.references.sorted_by_date(reverse=True) %}
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

__TEMPLATES_MAKO = {
    'page.mako': r"""
<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <meta name=viewport content="width=device-width, initial-scale=1">
      <title>
        <%block name="title">
          % if page.metadata.get('title') and page.url != '/':
            ${page.metadata['title']}
          % else:
            My blog
          % endif
        </%block>
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
        <%block name="content">
            ${page.content}
        </%block>
        </main>
        <footer id="footer">
            <p>Generated using Liara</p>
        </footer>
    </div>
</body>
</html>""",
    'blog.mako': r"""<%inherit file="page.mako"/>
<%block name="content">
<article>
    <header>
        <h1>${page.metadata["title"]}</h1>
        <div class="metadata">
            <div class="post-time">
              <time datetime="${page.metadata['date']}">
                  ${page.metadata['date'].strftime("%Y-%m-%d, %H:%M")}</time>
            </div>
            <div class="tags">
              <ul class="tags">
                % for tag in sorted(page.metadata['tags']):
                  <li>
                    <a href="/archive/by-tag/${tag}">
                        ${tag.capitalize()}
                    </a>
                   </li>
                % endfor
              </ul>
            </div>
        </div>
    </header>
    ${page.content}
    <aside>
        <div class="pagination">
            <%
                previous = site.get_previous_in_collection('blog', page)
                next = site.get_next_in_collection('blog', page)
            %>
            % if previous:
                <div class="previous">
                    <a href="${previous.url}">Previous post</a>
                </div>
            % endif
            % if next:
                <div class="next">
                    <a href="${next.url}">Next post</a>
                </div>
            % endif
        </div>
    </aside>
</article>
</%block>""",
    'archive.mako': r"""

<%inherit file="page.mako"/>
<%block name="content">
<h1>Blog archive
% if page.metadata.get('key'):
    for ${page.metadata['key']}
% endif
</h1>
${page.content}
<ul>
    % if not page.metadata.get('top_level_index', False):
        % for ref in page.references:
        <li>
            <a href="${ref.url}">${ref.metadata['title']}</a>
        </li>
        % endfor
    % else:
        % for child_page in page.children.sorted_by_metadata('key'):
        <li>
            <a href="${child_page.url}">${child_page.metadata['key']}</a>
            (${len(child_page.references)} posts)
            <ul>
                % for ref in child_page.references.sorted_by_date(reverse=True):
                <li>
                    <a href="${ref.url}">${ref.metadata['title']}</a>
                </li>
                % endfor
            </ul>
        </li>
        % endfor
    % endif
</ul>
</%block>"""
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

__THEME_CONFIG_JINJA2 = {
    'backend': 'jinja2',
    'paths': {
        '/blog/*?kind=document': 'blog.jinja2',
        '/archive/*': 'archive.jinja2',
        '/*': 'page.jinja2',
    },
    'resource_directory': 'resources'
}

__THEME_CONFIG_MAKO = {
    'backend': 'mako',
    'paths': {
        '/blog/*?kind=document': 'blog.mako',
        '/archive/*': 'archive.mako',
        '/*': 'page.mako',
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


class FileWriter:
    def __init__(self):
        pass

    def create_directory(self, path):
        import os
        os.makedirs(path, exist_ok=True)

    def write(self, filename, content):
        open(filename, 'w').write(content)


def _write_yaml(writer: FileWriter, path, yaml):
    import io
    stream = io.StringIO()
    dump_yaml(yaml, stream)
    writer.write(path, stream.getvalue())


def generate_templates(writer: FileWriter, backend):
    if backend == 'jinja2':
        templates = __TEMPLATES_JINJA2
    elif backend == 'mako':
        templates = __TEMPLATES_MAKO

    for k, v in templates.items():
        writer.write(f'templates/{k}', v)


def generate_css(writer: FileWriter):
    import os
    writer.create_directory('templates/resources')
    writer.write('templates/resources/style.scss', __SCSS)


def generate_theme(writer: FileWriter, backend):
    import io
    writer.create_directory('templates')
    generate_templates(writer, backend)
    generate_css(writer)

    if backend == 'jinja2':
        theme_config = __THEME_CONFIG_JINJA2
    elif backend == 'mako':
        theme_config = __THEME_CONFIG_MAKO
    _write_yaml(writer, 'templates/default.yaml', theme_config)


def generate_content(writer: FileWriter):
    import datetime
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

    writer.create_directory('content/blog')

    for date, title, tag, slug in zip(dates, titles, tags, slugs):
        t = page_template.replace("%TITLE%", title)
        t = t.replace("%TAGS%", ', '.join(tag))
        t = t.replace("%DATE%", str(date))
        writer.create_directory(f'content/blog/{date.year}')
        writer.write(f'content/blog/{date.year}/{slug}.md', t)

    writer.write('content/archive.md', """
---
title: The archive
---

The blog archive. Find blog posts [by year](/archive/by-year) or
[by tag](/archive/by-tag).""")

    writer.write('content/_index.md', """
---
title: Hello world
---

Welcome to the sample blog.""")


__DEFAULT_CONFIG = {
    'collections': 'collections.yaml',
    'indices': 'indices.yaml',
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


def generate_configs(writer: FileWriter):
    _write_yaml(writer, 'config.yaml', __DEFAULT_CONFIG)
    _write_yaml(writer, 'metadata.yaml', create_default_metadata())
    _write_yaml(writer, 'collections.yaml', __DEFAULT_COLLECTIONS)
    _write_yaml(writer, 'indices.yaml', __DEFAULT_INDICES)


def generate_generator(writer: FileWriter):
    writer.create_directory('generators')
    writer.write('generators/blog-post.py', __BLOG_POST_GENERATOR)


def generate(writer: FileWriter, template_backend):
    generate_theme(writer, template_backend)
    generate_content(writer)
    generate_configs(writer)
    generate_generator(writer)
