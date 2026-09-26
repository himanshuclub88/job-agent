import markdown


def md_to_html(md_file, html_file):
    with open(md_file, "r", encoding="utf-8") as f:
        md_content = f.read()

    html_content = markdown.markdown(
        md_content,
        extensions=[
            "tables",
            "fenced_code",
            "toc"
        ]
    )

    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)