from __future__ import annotations

from datetime import date
from pathlib import Path
from html import escape

from models import DailySummary


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>Job Search Dashboard</title>

<style>

:root {{
    --bg: #f4f6f8;
    --card: #ffffff;
    --text: #17202a;
    --muted: #6b7280;
    --border: #e5e7eb;

    --primary: #2563eb;
    --primary-light: #eff6ff;

    --danger: #dc2626;
    --danger-light: #fef2f2;

    --warning: #d97706;
    --warning-light: #fffbeb;

    --success: #059669;
    --success-light: #ecfdf5;

    --purple: #7c3aed;
    --purple-light: #f5f3ff;

    --shadow: 0 2px 10px rgba(0,0,0,0.05);
}}

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        Roboto,
        Arial,
        sans-serif;
}}

.container {{
    width: min(1180px, calc(100% - 40px));
    margin: 0 auto;
    padding: 35px 0 60px;
}}

/* HEADER */

.header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-bottom: 28px;
}}

.header h1 {{
    margin: 0;
    font-size: 32px;
    font-weight: 700;
    letter-spacing: -0.5px;
}}

.subtitle {{
    margin-top: 6px;
    color: var(--muted);
    font-size: 14px;
}}

.date {{
    color: var(--muted);
    font-size: 14px;
}}

/* SECTION */

.section {{
    margin-top: 32px;
}}

.section-title {{
    display: flex;
    align-items: center;
    gap: 9px;
    margin-bottom: 14px;
}}

.section-title h2 {{
    margin: 0;
    font-size: 18px;
    font-weight: 650;
}}

.section-count {{
    font-size: 12px;
    color: var(--muted);
    background: #e5e7eb;
    padding: 3px 8px;
    border-radius: 20px;
}}

/* CARDS */

.grid {{
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 15px;
}}

.card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    box-shadow: var(--shadow);
}}

.card:hover {{
    border-color: #d1d5db;
}}

.card-header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 15px;
}}

.company {{
    font-size: 16px;
    font-weight: 650;
}}

.job-title {{
    color: var(--muted);
    font-size: 13px;
    margin-top: 3px;
}}

.card-text {{
    margin-top: 14px;
    font-size: 14px;
    line-height: 1.55;
}}

.meta {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 15px;
}}

.badge {{
    display: inline-flex;
    align-items: center;
    padding: 5px 9px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
}}

.badge-date {{
    background: var(--primary-light);
    color: var(--primary);
}}

.badge-danger {{
    background: var(--danger-light);
    color: var(--danger);
}}

.badge-warning {{
    background: var(--warning-light);
    color: var(--warning);
}}

.badge-success {{
    background: var(--success-light);
    color: var(--success);
}}

/* LINKS */

.action {{
    display: inline-block;
    margin-top: 15px;
    padding: 8px 13px;
    border-radius: 7px;
    background: var(--primary);
    color: white;
    text-decoration: none;
    font-size: 12px;
    font-weight: 600;
}}

.action:hover {{
    opacity: 0.9;
}}

.recruiter {{
    color: var(--muted);
    font-size: 12px;
    margin-top: 10px;
}}

/* UPCOMING */

.timeline {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    box-shadow: var(--shadow);
    overflow: hidden;
}}

.timeline-item {{
    display: grid;
    grid-template-columns: 105px 1fr auto;
    gap: 18px;
    align-items: center;
    padding: 17px 20px;
    border-bottom: 1px solid var(--border);
}}

.timeline-item:last-child {{
    border-bottom: none;
}}

.timeline-date {{
    font-size: 13px;
    font-weight: 650;
    color: var(--primary);
}}

.timeline-content {{
    min-width: 0;
}}

.timeline-company {{
    font-size: 14px;
    font-weight: 650;
}}

.timeline-text {{
    color: var(--muted);
    font-size: 13px;
    margin-top: 3px;
}}

.timeline-time {{
    color: var(--muted);
    font-size: 12px;
}}

/* UPDATES */

.update-list {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    box-shadow: var(--shadow);
}}

.update {{
    padding: 15px 20px;
    border-bottom: 1px solid var(--border);
    font-size: 14px;
}}

.update:last-child {{
    border-bottom: none;
}}

.update::before {{
    content: "•";
    color: var(--primary);
    font-weight: bold;
    margin-right: 10px;
}}

/* OPPORTUNITIES */

.opportunity-grid {{
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 15px;
}}

.opportunity {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 19px;
    box-shadow: var(--shadow);
}}

.opportunity-company {{
    font-size: 15px;
    font-weight: 650;
}}

.opportunity-title {{
    font-size: 13px;
    color: var(--muted);
    margin-top: 4px;
}}

.opportunity-location {{
    font-size: 12px;
    color: var(--muted);
    margin-top: 12px;
}}

.opportunity-source {{
    font-size: 11px;
    color: var(--muted);
    margin-top: 7px;
}}

/* DON'T MISS */

.dont-miss {{
    background: var(--danger-light);
    border: 1px solid #fecaca;
    border-radius: 12px;
    overflow: hidden;
}}

.dont-miss-item {{
    padding: 14px 18px;
    font-size: 14px;
    border-bottom: 1px solid #fee2e2;
}}

.dont-miss-item:last-child {{
    border-bottom: none;
}}

.dont-miss-item::before {{
    content: "!";
    display: inline-flex;
    justify-content: center;
    align-items: center;
    width: 19px;
    height: 19px;
    margin-right: 9px;
    border-radius: 50%;
    background: var(--danger);
    color: white;
    font-size: 11px;
    font-weight: bold;
}}

/* EMPTY */

.empty {{
    background: var(--card);
    border: 1px dashed var(--border);
    border-radius: 12px;
    padding: 25px;
    text-align: center;
    color: var(--muted);
    font-size: 13px;
}}

/* FOOTER */

.footer {{
    margin-top: 45px;
    text-align: center;
    color: #9ca3af;
    font-size: 11px;
}}

/* RESPONSIVE */

@media (max-width: 800px) {{

    .grid {{
        grid-template-columns: 1fr;
    }}

    .opportunity-grid {{
        grid-template-columns: 1fr;
    }}

    .timeline-item {{
        grid-template-columns: 85px 1fr;
    }}

    .timeline-time {{
        grid-column: 2;
    }}

    .header {{
        align-items: flex-start;
        flex-direction: column;
        gap: 8px;
    }}
}}

@media (max-width: 520px) {{

    .container {{
        width: min(100% - 24px, 1180px);
        padding-top: 22px;
    }}

    .header h1 {{
        font-size: 26px;
    }}

    .card {{
        padding: 17px;
    }}

    .timeline-item {{
        grid-template-columns: 1fr;
        gap: 5px;
    }}

    .timeline-time {{
        grid-column: auto;
    }}
}}

</style>
</head>

<body>

<div class="container">

    <header class="header">
        <div>
            <h1>Job Search Dashboard</h1>
            <div class="subtitle">
                Your daily job-search command center
            </div>
        </div>

        <div class="date">
            {date}
        </div>
    </header>

    {responsibilities}

    {upcoming}

    {updates}

    {opportunities}

    {dont_miss}

    <div class="footer">
        Generated by Job Search Agent
    </div>

</div>

</body>
</html>
"""


def _section_title(title: str, count: int) -> str:
    return f"""
    <div class="section-title">
        <h2>{escape(title)}</h2>
        <span class="section-count">{count}</span>
    </div>
    """


def _generate_responsibilities(daily: DailySummary) -> str:

    if not daily.responsibilities:
        return ""

    cards = []

    for item in daily.responsibilities:

        company = escape(item.company or "Unknown company")
        job_title = escape(item.job_title or "")
        text = escape(item.text)

        card = f"""
        <div class="card">

            <div class="card-header">
                <div>
                    <div class="company">{company}</div>
                    {f'<div class="job-title">{job_title}</div>' if job_title else ''}
                </div>
            </div>

            <div class="card-text">
                {text}
            </div>
        """

        if item.deadline:
            card += f"""
            <div class="meta">
                <span class="badge badge-danger">
                    Due: {escape(item.deadline)}
                </span>
            </div>
            """

        if item.recruiter:
            card += f"""
            <div class="recruiter">
                Recruiter: {escape(item.recruiter)}
            </div>
            """

        if item.link:
            card += f"""
            <a class="action"
               href="{escape(item.link, quote=True)}"
               target="_blank"
               rel="noopener noreferrer">
                Open
            </a>
            """

        card += "</div>"

        cards.append(card)

    return f"""
    <section class="section">

        {_section_title("Today's Responsibilities", len(cards))}

        <div class="grid">
            {''.join(cards)}
        </div>

    </section>
    """


def _generate_upcoming(daily: DailySummary) -> str:

    if not daily.upcoming:
        return ""

    items = []

    for item in daily.upcoming:

        company = escape(item.company or "Unknown company")
        job_title = escape(item.job_title or "")
        text = escape(item.text)

        date_text = escape(item.date or "Upcoming")
        time_text = escape(item.time or "")

        link = ""

        if item.link:
            link = f"""
            <a class="action"
               href="{escape(item.link, quote=True)}"
               target="_blank"
               rel="noopener noreferrer">
                Open
            </a>
            """

        items.append(f"""
        <div class="timeline-item">

            <div class="timeline-date">
                {date_text}
            </div>

            <div class="timeline-content">

                <div class="timeline-company">
                    {company}
                    {f" — {job_title}" if job_title else ""}
                </div>

                <div class="timeline-text">
                    {text}
                </div>

            </div>

            <div class="timeline-time">
                {time_text}
                {link}
            </div>

        </div>
        """)

    return f"""
    <section class="section">

        {_section_title("Upcoming", len(items))}

        <div class="timeline">
            {''.join(items)}
        </div>

    </section>
    """


def _generate_updates(daily: DailySummary) -> str:

    if not daily.updates:
        return ""

    items = []

    for update in daily.updates:
        items.append(
            f'<div class="update">{escape(update.text)}</div>'
        )

    return f"""
    <section class="section">

        {_section_title("Important Updates", len(items))}

        <div class="update-list">
            {''.join(items)}
        </div>

    </section>
    """


def _generate_opportunities(daily: DailySummary) -> str:

    if not daily.opportunities:
        return ""

    cards = []

    for item in daily.opportunities:

        company = escape(item.company or "Unknown company")
        job_title = escape(item.job_title or "")
        location = escape(item.location or "")
        source = escape(item.source or "")

        card = f"""
        <div class="opportunity">

            <div class="opportunity-company">
                {company}
            </div>

            {f'<div class="opportunity-title">{job_title}</div>' if job_title else ''}

            {f'<div class="opportunity-location">{location}</div>' if location else ''}

            {f'<div class="opportunity-source">Source: {source}</div>' if source else ''}
        """

        if item.url:
            card += f"""
            <a class="action"
               href="{escape(item.url, quote=True)}"
               target="_blank"
               rel="noopener noreferrer">
                View Job
            </a>
            """

        card += "</div>"

        cards.append(card)

    return f"""
    <section class="section">

        {_section_title("Opportunities", len(cards))}

        <div class="opportunity-grid">
            {''.join(cards)}
        </div>

    </section>
    """


def _generate_dont_miss(daily: DailySummary) -> str:

    if not daily.dont_miss:
        return ""

    items = []

    for item in daily.dont_miss:
        items.append(
            f'<div class="dont-miss-item">{escape(item)}</div>'
        )

    return f"""
    <section class="section">

        {_section_title("Don't Miss", len(items))}

        <div class="dont-miss">
            {''.join(items)}
        </div>

    </section>
    """


def generate_html(
    daily: DailySummary,
    today: date,
    output_file: Path,
) -> None:

    responsibilities = _generate_responsibilities(daily)
    upcoming = _generate_upcoming(daily)
    updates = _generate_updates(daily)
    opportunities = _generate_opportunities(daily)
    dont_miss = _generate_dont_miss(daily)

    html = HTML_TEMPLATE.format(
        date=today.strftime("%d %B %Y"),
        responsibilities=responsibilities,
        upcoming=upcoming,
        updates=updates,
        opportunities=opportunities,
        dont_miss=dont_miss,
    )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file.write_text(
        html,
        encoding="utf-8",
    )


if __name__ == "__main__":
    print("html_generator.py loaded successfully.")