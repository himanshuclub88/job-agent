from __future__ import annotations

import html
from datetime import date
from pathlib import Path

from models import DailySummary


def esc(value: object | None) -> str:
    """Safely escape text for HTML."""
    if value is None:
        return ""

    return html.escape(str(value))


def gmail_url(thread_id: str | None) -> str | None:
    """Build a Gmail conversation URL from a thread ID."""
    if not thread_id:
        return None

    return f"https://mail.google.com/mail/u/0/#all/{thread_id}"


def action_button(
    label: str,
    url: str | None,
    css_class: str = "action",
) -> str:
    """Render a clickable external link."""
    if not url:
        return ""

    return f"""
    <a class="{css_class}"
       href="{esc(url)}"
       target="_blank"
       rel="noopener noreferrer">
        {esc(label)}
    </a>
    """


def email_button(thread_id: str | None) -> str:
    """Render View Email button when a Gmail thread is available."""
    url = gmail_url(thread_id)

    if not url:
        return ""

    return f"""
    <a class="email-action"
       href="{esc(url)}"
       target="_blank"
       rel="noopener noreferrer">
        View Email
    </a>
    """


def render_responsibility(item) -> str:
    buttons = ""

    if item.link:
        buttons += action_button("Open", item.link)

    buttons += email_button(item.thread_id)

    deadline = ""

    if item.deadline:
        deadline = f"""
        <div class="meta">
            <span class="badge badge-danger">
                Due: {esc(item.deadline)}
            </span>
        </div>
        """

    recruiter = ""

    if item.recruiter:
        recruiter = f"""
        <div class="recruiter">
            Recruiter: {esc(item.recruiter)}
        </div>
        """

    job_title = ""

    if item.job_title:
        job_title = f"""
        <div class="job-title">
            {esc(item.job_title)}
        </div>
        """

    return f"""
    <div class="card">

        <div class="card-header">
            <div>
                <div class="company">
                    {esc(item.company or "Unknown company")}
                </div>

                {job_title}
            </div>
        </div>

        <div class="card-text">
            {esc(item.text)}
        </div>

        {deadline}

        {recruiter}

        <div class="actions">
            {buttons}
        </div>

    </div>
    """


def render_upcoming(item) -> str:
    date_value = esc(item.date or "Upcoming")
    time_value = esc(item.time or "")

    buttons = ""

    if item.link:
        buttons += action_button("Open", item.link)

    buttons += email_button(item.thread_id)

    job_title = ""

    if item.job_title:
        job_title = f" — {esc(item.job_title)}"

    return f"""
    <div class="timeline-item">

        <div class="timeline-date">
            {date_value}
        </div>

        <div class="timeline-content">

            <div class="timeline-company">
                {esc(item.company or "Unknown company")}
                {job_title}
            </div>

            <div class="timeline-text">
                {esc(item.text)}
            </div>

        </div>

        <div class="timeline-actions">

            <div class="timeline-time">
                {time_value}
            </div>

            {buttons}

        </div>

    </div>
    """


def render_update(item) -> str:
    button = email_button(item.thread_id)

    return f"""
    <div class="update">

        <div class="update-content">
            {esc(item.text)}
        </div>

        {button}

    </div>
    """


def render_opportunity(item) -> str:
    buttons = ""

    if item.url:
        buttons += action_button("View Job", item.url)

    buttons += email_button(item.thread_id)

    location = ""

    if item.location:
        location = f"""
        <div class="opportunity-location">
            {esc(item.location)}
        </div>
        """

    source = ""

    if item.source:
        source = f"""
        <div class="opportunity-source">
            Source: {esc(item.source)}
        </div>
        """

    return f"""
    <div class="opportunity">

        <div class="opportunity-company">
            {esc(item.company or "Unknown company")}
        </div>

        <div class="opportunity-title">
            {esc(item.job_title or "")}
        </div>

        {location}

        {source}

        <div class="actions">
            {buttons}
        </div>

    </div>
    """


def render_empty(text: str) -> str:
    return f"""
    <div class="empty">
        {esc(text)}
    </div>
    """


def generate_html(
    daily: DailySummary,
    today: date,
    output_file: Path,
) -> None:

    responsibilities = "".join(
        render_responsibility(item)
        for item in daily.responsibilities
    )

    if not responsibilities:
        responsibilities = render_empty(
            "No responsibilities for today."
        )

    upcoming = "".join(
        render_upcoming(item)
        for item in daily.upcoming
    )

    if not upcoming:
        upcoming = render_empty(
            "No upcoming events."
        )

    updates = "".join(
        render_update(item)
        for item in daily.updates
    )

    if not updates:
        updates = render_empty(
            "No important updates."
        )

    opportunities = "".join(
        render_opportunity(item)
        for item in daily.opportunities
    )

    if not opportunities:
        opportunities = render_empty(
            "No new opportunities."
        )

    dont_miss = "".join(
        f"""
        <div class="dont-miss-item">
            {esc(item)}
        </div>
        """
        for item in daily.dont_miss
    )

    if not dont_miss:
        dont_miss = render_empty(
            "Nothing critical to highlight."
        )

    html_document = f"""<!DOCTYPE html>
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

.badge-danger {{
    background: var(--danger-light);
    color: var(--danger);
}}


/* BUTTONS */

.actions {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 15px;
}}

.action,
.email-action {{
    display: inline-block;
    padding: 8px 13px;
    border-radius: 7px;
    text-decoration: none;
    font-size: 12px;
    font-weight: 600;
}}

.action {{
    background: var(--primary);
    color: white;
}}

.email-action {{
    background: #f3f4f6;
    color: #374151;
    border: 1px solid var(--border);
}}

.action:hover,
.email-action:hover {{
    opacity: 0.88;
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

.timeline-actions {{
    text-align: right;
}}

.timeline-time {{
    color: var(--muted);
    font-size: 12px;
    margin-bottom: 7px;
}}


/* UPDATES */

.update-list {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    box-shadow: var(--shadow);
}}

.update {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 15px;
    padding: 15px 20px;
    border-bottom: 1px solid var(--border);
    font-size: 14px;
}}

.update:last-child {{
    border-bottom: none;
}}

.update-content {{
    flex: 1;
}}

.update-content::before {{
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

    .timeline-actions {{
        grid-column: 2;
        text-align: left;
    }}

    .header {{
        align-items: flex-start;
        flex-direction: column;
        gap: 8px;
    }}

    .update {{
        align-items: flex-start;
        flex-direction: column;
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

    .timeline-actions {{
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
        {today.strftime("%d %B %Y")}
    </div>

</header>


<!-- RESPONSIBILITIES -->

<section class="section">

    <div class="section-title">
        <h2>Today's Responsibilities</h2>
        <span class="section-count">
            {len(daily.responsibilities)}
        </span>
    </div>

    <div class="grid">
        {responsibilities}
    </div>

</section>


<!-- UPCOMING -->

<section class="section">

    <div class="section-title">
        <h2>Upcoming</h2>
        <span class="section-count">
            {len(daily.upcoming)}
        </span>
    </div>

    <div class="timeline">
        {upcoming}
    </div>

</section>


<!-- UPDATES -->

<section class="section">

    <div class="section-title">
        <h2>Important Updates</h2>
        <span class="section-count">
            {len(daily.updates)}
        </span>
    </div>

    <div class="update-list">
        {updates}
    </div>

</section>


<!-- OPPORTUNITIES -->

<section class="section">

    <div class="section-title">
        <h2>Opportunities</h2>
        <span class="section-count">
            {len(daily.opportunities)}
        </span>
    </div>

    <div class="opportunity-grid">
        {opportunities}
    </div>

</section>


<!-- DON'T MISS -->

<section class="section">

    <div class="section-title">
        <h2>Don't Miss</h2>
        <span class="section-count">
            {len(daily.dont_miss)}
        </span>
    </div>

    <div class="dont-miss">
        {dont_miss}
    </div>

</section>


<div class="footer">
    Generated by Job Search Agent
</div>

</div>

</body>

</html>
"""

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file.write_text(
        html_document,
        encoding="utf-8",
    )