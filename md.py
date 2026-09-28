import markdown
from pathlib import Path


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>Job Search Responsibility</title>

    <style>
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            padding: 40px 20px;
            background: #f5f7fa;
            color: #1f2937;
            font-family:
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                Roboto,
                Arial,
                sans-serif;
            line-height: 1.6;
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
        }

        h1 {
            margin-bottom: 6px;
            font-size: 32px;
            color: #111827;
        }

        h2 {
            margin-top: 36px;
            margin-bottom: 16px;
            font-size: 21px;
            color: #111827;
            border-bottom: 1px solid #e5e7eb;
            padding-bottom: 8px;
        }

        h3 {
            margin-bottom: 6px;
            color: #111827;
        }

        p {
            margin: 8px 0;
        }

        ul,
        ol {
            padding-left: 24px;
        }

        li {
            margin: 8px 0;
        }

        a {
            color: #2563eb;
            text-decoration: none;
        }

        a:hover {
            text-decoration: underline;
        }

        blockquote {
            margin: 16px 0;
            padding: 12px 18px;
            border-left: 4px solid #2563eb;
            background: #f8fafc;
            color: #4b5563;
        }

        code {
            padding: 2px 6px;
            border-radius: 5px;
            background: #f1f5f9;
            font-family: monospace;
        }

        pre {
            padding: 16px;
            overflow-x: auto;
            border-radius: 8px;
            background: #111827;
            color: #f9fafb;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            border-radius: 8px;
            overflow: hidden;
        }

        th,
        td {
            padding: 12px 14px;
            text-align: left;
            border-bottom: 1px solid #e5e7eb;
        }

        th {
            background: #f8fafc;
            font-weight: 600;
        }

        .header {
            background: white;
            padding: 28px 30px;
            margin-bottom: 24px;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
        }

        .content {
            background: white;
            padding: 30px;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
        }

        @media (max-width: 600px) {
            body {
                padding: 20px 12px;
            }

            .header,
            .content {
                padding: 20px;
            }

            h1 {
                font-size: 26px;
            }

            h2 {
                font-size: 19px;
            }
        }
    </style>
</head>

<body>

<div class="container">

    <div class="header">
        <h1>Job Search Responsibility</h1>
        <p>Daily job-search overview</p>
    </div>

    <div class="content">
        {content}
    </div>

</div>

</body>
</html>
"""


def md_to_html(md_file: Path, html_file: Path) -> None:

    with open(md_file, "r", encoding="utf-8") as f:
        md_content = f.read()

    content = markdown.markdown(
        md_content,
        extensions=[
            "tables",
            "fenced_code",
            "toc"
        ]
    )

    html_content = HTML_TEMPLATE.format(
        content=content
    )

    html_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)