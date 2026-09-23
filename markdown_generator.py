from __future__ import annotations

from datetime import date

from models import DailySummary


def _link(text: str, url: str | None) -> str:
    return f"[{text}]({url})" if url else text


def render_markdown(summary: DailySummary, today: date) -> str:
    lines = [f"# Job Search — {today.strftime('%d %B %Y')}", ""]

    lines += ["## 🔴 Today's Responsibilities", ""]
    if not summary.responsibilities:
        lines += ["Nothing requiring action today.", ""]
    else:
        for item in summary.responsibilities:
            heading = " — ".join(x for x in [item.company, item.job_title] if x) or "Job Search"
            lines += [f"### {heading}", item.text, ""]
            if item.deadline:
                lines.append(f"- Deadline: {item.deadline}")
            if item.link:
                lines.append(f"- Link: {_link(item.link, item.link)}")
            if item.recruiter:
                lines.append(f"- Recruiter: {item.recruiter}")
            lines.append("")

    if summary.upcoming:
        lines += ["## 🟠 Upcoming", ""]
        for item in summary.upcoming:
            heading = " — ".join(x for x in [item.company, item.job_title] if x) or "Upcoming"
            lines += [f"### {heading}", item.text, ""]
            if item.date:
                lines.append(f"- Date: {item.date}")
            if item.time:
                lines.append(f"- Time: {item.time}")
            if item.link:
                lines.append(f"- Join: {_link(item.link, item.link)}")
            lines.append("")

    if summary.updates:
        lines += ["## 🟢 Important Updates", ""]
        lines.extend(f"- {x.text}" for x in summary.updates)
        lines.append("")

    if summary.opportunities:
        lines += ["## 💼 Job Opportunities", ""]
        for item in summary.opportunities:
            heading = " — ".join(x for x in [item.job_title, item.company] if x) or "Opportunity"
            lines += [f"### {heading}"]
            if item.location:
                lines.append(f"- Location: {item.location}")
            if item.url:
                lines.append(f"- Apply: {_link(item.url, item.url)}")
            if item.source:
                lines.append(f"- Source: {item.source}")
            lines.append("")

    if summary.dont_miss:
        lines += ["## ⚠️ Don't Miss", ""]
        lines.extend(f"- {x}" for x in summary.dont_miss)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
